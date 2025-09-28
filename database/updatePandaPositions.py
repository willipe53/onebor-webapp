import boto3
import json
import pymysql
import os
import time
import threading
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

# CORS headers
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}

# Configuration
_queue_url = "https://sqs.us-east-2.amazonaws.com/316490106381/pandatransactions.fifo"
_lock_table_name = "position-keeper-locks"
_lock_key = "position-keeper-running"
_lock_ttl = 60  # seconds - lock expires after 60 seconds if not refreshed

# Global cache for transaction types (fetched once at startup)
_transaction_types_cache = {}
_entities_cache = {}


def get_db_secret():
    """Get database credentials from AWS Secrets Manager."""
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=os.environ["SECRET_ARN"])
    return json.loads(response["SecretString"])


def get_db_connection():
    """Get database connection using AWS Secrets Manager."""
    secrets = get_db_secret()
    return pymysql.connect(
        host=secrets["DB_HOST"],
        user=secrets["DB_USER"],
        password=secrets["DB_PASS"],
        database=secrets["DATABASE"],
        connect_timeout=5,
        cursorclass=pymysql.cursors.DictCursor
    )


def get_sqs_client():
    """Get SQS client."""
    return boto3.client('sqs', region_name='us-east-2')


def get_lambda_client():
    """Get Lambda client."""
    return boto3.client('lambda', region_name='us-east-2')


def load_transaction_types_cache():
    """Load all transaction types into cache at startup."""
    global _transaction_types_cache

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT transaction_type_id, name, properties 
            FROM transaction_types
        """)

        transaction_types = cursor.fetchall()

        for tt in transaction_types:
            transaction_type_id = tt['transaction_type_id']
            transaction_type_name = tt['name']
            properties = tt['properties']

            # Parse JSON properties
            if isinstance(properties, str):
                try:
                    properties = json.loads(properties)
                except json.JSONDecodeError:
                    print(
                        f"WARNING: Invalid JSON in transaction type {transaction_type_id}")
                    properties = {}

            _transaction_types_cache[transaction_type_id] = {
                'name': transaction_type_name,
                'properties': properties
            }

        print(
            f"Loaded {len(_transaction_types_cache)} transaction types into cache")

    except Exception as e:
        print(f"ERROR loading transaction types cache: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


def load_entities_cache():
    """Load all entities into cache at startup."""
    global _entities_cache

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT entity_id, name 
            FROM entities
        """)

        entities = cursor.fetchall()

        for entity in entities:
            entity_id = entity['entity_id']
            entity_name = entity['name']
            # Store both string and int versions of the key to handle both cases
            _entities_cache[entity_id] = entity_name
            _entities_cache[str(entity_id)] = entity_name

        print(
            f"Loaded {len(entities)} entities into cache (with string/int keys)")

    except Exception as e:
        print(f"ERROR loading entities cache: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


def initialize_caches():
    """Initialize all caches at startup."""
    print("Initializing position keeper caches...")
    load_transaction_types_cache()
    load_entities_cache()
    print("Cache initialization complete")


def acquire_distributed_lock(context) -> bool:
    """Acquire a distributed lock using the lambda_locks table."""
    try:
        lambda_client = get_lambda_client()

        holder = f"{context.log_stream_name}:{context.aws_request_id}"

        # Create a proper Lambda event structure
        lambda_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'action': 'set',
                'holder': holder
            })
        }

        response = lambda_client.invoke(
            FunctionName='updatePandaLocks',
            InvocationType='RequestResponse',
            Payload=json.dumps(lambda_event)
        )

        result = json.loads(response['Payload'].read())

        if result.get('statusCode') == 200:
            return True
        elif result.get('statusCode') == 409:
            return False
        else:
            print(f"ERROR: Failed to acquire lock: {result}")
            return False

    except Exception as e:
        print(f"ERROR: Exception while acquiring lock: {str(e)}")
        return False


def release_distributed_lock(context) -> bool:
    """Release the distributed lock."""
    try:
        lambda_client = get_lambda_client()

        holder = f"{context.log_stream_name}:{context.aws_request_id}"

        # Create a proper Lambda event structure
        lambda_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'action': 'delete',
                'holder': holder
            })
        }

        response = lambda_client.invoke(
            FunctionName='updatePandaLocks',
            InvocationType='RequestResponse',
            Payload=json.dumps(lambda_event)
        )

        result = json.loads(response['Payload'].read())

        if result.get('statusCode') == 200:
            return True
        else:
            print(f"ERROR: Failed to release lock: {result}")
            return False

    except Exception as e:
        print(f"ERROR: Exception while releasing lock: {str(e)}")
        return False


def process_transaction_message(message_body: Dict[str, Any]) -> bool:
    """
    Process a single transaction message from SQS by creating positions
    based on transaction type rules.

    Args:
        message_body: The parsed message body from SQS

    Returns:
        bool: True if processing was successful, False otherwise
    """
    try:
        operation = message_body.get("operation")
        transaction_id = message_body.get("transaction_id")
        transaction_type_id = message_body.get("transaction_type_id")
        portfolio_entity_id = message_body.get("portfolio_entity_id")
        contra_entity_id = message_body.get("contra_entity_id")
        instrument_entity_id = message_body.get("instrument_entity_id")
        properties = message_body.get("properties", {})

        # Parse properties if it's a JSON string
        if isinstance(properties, str):
            try:
                properties = json.loads(properties)
            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to parse properties JSON: {str(e)}")
                return False
        updated_user_id = message_body.get("updated_user_id")

        print(
            f"Processing {operation} operation for transaction ID: {transaction_id}")
        print(f"Transaction Type ID: {transaction_type_id}")

        # Get transaction type from cache (no database lookup needed!)
        transaction_type = _transaction_types_cache.get(transaction_type_id)
        if not transaction_type:
            print(
                f"ERROR: Transaction type {transaction_type_id} not found in cache")
            return False

        transaction_type_name = transaction_type['name']
        type_properties = transaction_type['properties']

        print(f"Transaction Type: {transaction_type_name}")

        # Extract position keeping rules
        current_position_date_field = type_properties.get("current_position")
        forecast_position_date_field = type_properties.get("forecast_position")
        position_keeping_actions = type_properties.get(
            "position_keeping_actions", [])

        if not current_position_date_field or not forecast_position_date_field:
            print(
                f"ERROR: Missing current_position or forecast_position in transaction type rules")
            return False

        if not position_keeping_actions:
            print(f"ERROR: No position_keeping_actions defined for transaction type")
            return False

        print(f"Current position date field: {current_position_date_field}")
        print(f"Forecast position date field: {forecast_position_date_field}")
        print(f"Position keeping actions: {position_keeping_actions}")

        # Get portfolio and instrument names from cache (no database lookup needed!)
        portfolio_name = _entities_cache.get(portfolio_entity_id)
        if not portfolio_name:
            portfolio_name = f"Portfolio {portfolio_entity_id} (name not found)"

        if instrument_entity_id:
            instrument_name = _entities_cache.get(instrument_entity_id)
            if not instrument_name:
                instrument_name = f"Instrument {instrument_entity_id} (name not found)"
        else:
            instrument_name = "Cash"

        print(f"Portfolio: {portfolio_name}")
        print(f"Instrument: {instrument_name}")

        # Process position keeping
        process_position_keeping(
            transaction_type_name,
            properties,
            current_position_date_field,
            forecast_position_date_field,
            position_keeping_actions,
            portfolio_name,
            instrument_name
        )

        # Update transaction status to PROCESSED
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            update_sql = """
            UPDATE transactions 
            SET transaction_status_id = 3, 
                updated_user_id = %s
            WHERE transaction_id = %s
            """
            cursor.execute(update_sql, (updated_user_id, transaction_id))
            connection.commit()

            print(
                f"Successfully processed {operation} for transaction {transaction_id}")
            return True

        except Exception as e:
            print(
                f"Database error processing transaction {transaction_id}: {str(e)}")
            connection.rollback()
            return False

        finally:
            cursor.close()
            connection.close()

    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return False


def process_position_keeping(
    transaction_type_name: str,
    properties: Dict[str, Any],
    current_position_date_field: str,
    forecast_position_date_field: str,
    position_keeping_actions: List[str],
    portfolio_name: str,
    instrument_name: str
) -> None:
    """
    Process position keeping rules and log the positions that would be created.

    Args:
        transaction_type_name: Name of the transaction type (e.g., "Buy")
        properties: Transaction properties containing amounts, dates, etc.
        current_position_date_field: Field name for current position date
        forecast_position_date_field: Field name for forecast position date
        position_keeping_actions: List of position keeping action strings
        portfolio_name: Name of the portfolio
        instrument_name: Name of the instrument
    """
    try:
        # Get dates from properties
        current_date = properties.get(current_position_date_field)
        forecast_date = properties.get(forecast_position_date_field)

        if not current_date or not forecast_date:
            print(
                f"ERROR: Missing date fields - current: {current_date}, forecast: {forecast_date}")
            return

        # Get amount and other key properties
        amount = properties.get("amount", 0)
        price = properties.get("price", 0)
        currency_code = properties.get("currency_code", "USD")

        # Create a summary for logging
        if price and price > 0:
            summary = f"{transaction_type_name} {amount} shares of {instrument_name} at price {price}"
        else:
            summary = f"{transaction_type_name} {amount} {instrument_name}"

        print(f"\nProcessing positions for a {summary}")
        # current + forecast for each action
        print(f"Need to create {len(position_keeping_actions) * 2} positions")

        # Process each position keeping action
        for i, action in enumerate(position_keeping_actions):
            print(f"\nAction {i+1}: {action}")

            # Parse the action string
            parsed_action = parse_position_action(action)
            if not parsed_action:
                print(f"ERROR: Could not parse action: {action}")
                continue

            # Calculate amounts for current and forecast positions
            current_amount = calculate_position_amount(
                parsed_action, properties, amount, price)
            forecast_amount = calculate_position_amount(
                parsed_action, properties, amount, price)

            # Determine currency/instrument for the position
            position_currency = get_position_currency(
                parsed_action, properties, currency_code, instrument_name)

            # Log current position
            direction_symbol = "+" if parsed_action["direction"] == "up" else "-"
            print(f"  {direction_symbol}{abs(current_amount)} {position_currency} will be applied to {portfolio_name} for {current_date} ({current_position_date_field})")

            # Log forecast position
            print(f"  {direction_symbol}{abs(forecast_amount)} {position_currency} will be applied to {portfolio_name} for {forecast_date} ({forecast_position_date_field})")

        print()  # Add spacing

    except Exception as e:
        print(f"ERROR in process_position_keeping: {str(e)}")


def parse_position_action(action: str) -> Dict[str, Any]:
    """
    Parse a position keeping action string into components.

    Examples:
    - "contra amount*price settle_currency down" -> {"entity": "contra", "calculation": "amount*price", "currency_field": "settle_currency", "direction": "down"}
    - "portfolio amount instrument up" -> {"entity": "portfolio", "calculation": "amount", "currency_field": "instrument", "direction": "up"}

    Args:
        action: The position keeping action string

    Returns:
        Dict with parsed components or None if parsing fails
    """
    try:
        parts = action.strip().split()
        if len(parts) != 4:
            print(
                f"ERROR: Action must have 4 parts, got {len(parts)}: {action}")
            return None

        entity = parts[0]  # contra, portfolio
        calculation = parts[1]  # amount, amount*price, ratio*position
        currency_field = parts[2]  # settle_currency, instrument, currency_code
        direction = parts[3]  # up, down

        return {
            "entity": entity,
            "calculation": calculation,
            "currency_field": currency_field,
            "direction": direction
        }

    except Exception as e:
        print(f"ERROR parsing action '{action}': {str(e)}")
        return None


def calculate_position_amount(parsed_action: Dict[str, Any], properties: Dict[str, Any], amount: float, price: float) -> float:
    """
    Calculate the position amount based on the parsed action and transaction properties.

    Args:
        parsed_action: Parsed action components
        properties: Transaction properties
        amount: Base amount from transaction
        price: Price from transaction (if applicable)

    Returns:
        Calculated position amount
    """
    try:
        calculation = parsed_action["calculation"]

        if calculation == "amount":
            return amount
        elif calculation == "amount*price":
            if price > 0:
                return amount * price
            else:
                print(f"WARNING: Price is 0 or missing for amount*price calculation")
                return amount
        elif calculation == "ratio*position":
            ratio = properties.get("ratio", 1.0)
            current_position = properties.get("current_position", 0)
            return ratio * current_position
        else:
            print(f"ERROR: Unknown calculation type: {calculation}")
            return amount

    except Exception as e:
        print(f"ERROR calculating position amount: {str(e)}")
        return amount


def get_position_currency(parsed_action: Dict[str, Any], properties: Dict[str, Any], default_currency: str, instrument_name: str) -> str:
    """
    Get the currency/instrument name for the position based on the parsed action.

    Args:
        parsed_action: Parsed action components
        properties: Transaction properties
        default_currency: Default currency code
        instrument_name: Name of the instrument

    Returns:
        Currency or instrument name for the position
    """
    try:
        currency_field = parsed_action["currency_field"]

        if currency_field == "instrument":
            return instrument_name
        elif currency_field == "currency_code":
            return properties.get("currency_code", default_currency)
        elif currency_field == "settle_currency":
            return properties.get("settle_currency", default_currency)
        else:
            # Try to get the value from properties
            return properties.get(currency_field, currency_field)

    except Exception as e:
        print(f"ERROR getting position currency: {str(e)}")
        return default_currency


def receive_and_process_messages(queue_url: str, max_messages: int = 10) -> int:
    """
    Receive messages from SQS queue and process them.

    Args:
        queue_url: The SQS queue URL
        max_messages: Maximum number of messages to receive in one batch

    Returns:
        int: Number of messages processed
    """
    sqs = get_sqs_client()
    processed_count = 0

    try:
        # First, check if there are any messages to avoid unnecessary processing
        queue_attrs = get_queue_attributes(queue_url)
        messages_available = int(queue_attrs.get(
            'ApproximateNumberOfMessages', 0))

        if messages_available == 0:
            print("No messages available in queue")
            return 0

        print(f"Found {messages_available} messages in queue, processing...")

        # Receive messages from the queue
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=0,  # No long polling - process and exit
            VisibilityTimeout=30,  # 30 seconds visibility timeout
            AttributeNames=['All'],
            MessageAttributeNames=['All']
        )

        messages = response.get('Messages', [])
        print(f"Received {len(messages)} messages from queue")

        if not messages:
            print("No messages to process")
            return 0

        # Process each message
        successful_messages = []

        for message in messages:
            try:
                # Parse message body
                message_body = json.loads(message['Body'])
                print(f"Processing message ID: {message['MessageId']}")

                # Process the transaction
                if process_transaction_message(message_body):
                    successful_messages.append({
                        'Id': message['MessageId'],
                        'ReceiptHandle': message['ReceiptHandle']
                    })
                    processed_count += 1
                else:
                    print(f"Failed to process message {message['MessageId']}")

            except json.JSONDecodeError as e:
                print(f"Error parsing message body: {str(e)}")
                # Delete malformed messages to prevent infinite reprocessing
                successful_messages.append({
                    'Id': message['MessageId'],
                    'ReceiptHandle': message['ReceiptHandle']
                })
            except Exception as e:
                print(
                    f"Error processing message {message['MessageId']}: {str(e)}")

        # Delete successfully processed messages
        if successful_messages:
            try:
                sqs.delete_message_batch(
                    QueueUrl=queue_url,
                    Entries=successful_messages
                )
                print(
                    f"Deleted {len(successful_messages)} processed messages from queue")
            except ClientError as e:
                print(f"Error deleting messages: {str(e)}")

    except ClientError as e:
        print(f"SQS error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

    return processed_count


def get_queue_attributes(queue_url: str) -> Dict[str, Any]:
    """
    Get queue attributes to monitor queue health.

    Args:
        queue_url: The SQS queue URL

    Returns:
        Dict containing queue attributes
    """
    sqs = get_sqs_client()

    try:
        response = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=[
                'ApproximateNumberOfMessages',
                'ApproximateNumberOfMessagesNotVisible',
                'ApproximateNumberOfMessagesDelayed'
            ]
        )
        return response.get('Attributes', {})
    except ClientError as e:
        print(f"Error getting queue attributes: {str(e)}")
        return {}


def start_position_keeper_loop(context):
    """
    Start the position keeper processing loop.
    Processes all available messages and then exits.
    Simplified version without distributed locking for testing.
    """
    try:
        print("Starting position keeper processing...")
        total_processed = 0

        # Process messages in batches until queue is empty
        while True:
            processed_count = receive_and_process_messages(
                _queue_url, max_messages=10)
            total_processed += processed_count

            if processed_count > 0:
                print(f"Processed {processed_count} messages in this batch")
            else:
                # No messages available, we're done
                print("No more messages to process")
                break

        print(f"Position keeper completed. Total processed: {total_processed}")
        return True

    except Exception as e:
        print(f"Error in position keeper loop: {str(e)}")
        return False


def refresh_transaction_statuses():
    """
    Refresh transaction statuses to ensure UI accuracy.
    Sets QUEUED transactions that aren't in the queue to UNKNOWN status.
    """
    print("Refreshing transaction statuses...")

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Get all QUEUED transactions
        cursor.execute("""
            SELECT transaction_id FROM transactions 
            WHERE transaction_status_id = 2
        """)
        queued_transactions = cursor.fetchall()

        if not queued_transactions:
            print("No QUEUED transactions found")
            return

        print(f"Found {len(queued_transactions)} QUEUED transactions")

        # Check which transactions are actually in the SQS queue
        sqs_client = boto3.client('sqs', region_name='us-east-2')

        # Get approximate number of messages in queue
        try:
            response = sqs_client.get_queue_attributes(
                QueueUrl=_queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            queue_count = int(response['Attributes']
                              ['ApproximateNumberOfMessages'])
            print(f"SQS queue has {queue_count} messages")

            if queue_count == 0:
                # No messages in queue, set all QUEUED transactions to UNKNOWN
                print(
                    "No messages in queue - setting all QUEUED transactions to UNKNOWN")
                cursor.execute("""
                    UPDATE transactions 
                    SET transaction_status_id = 4  -- UNKNOWN status
                    WHERE transaction_status_id = 2  -- QUEUED status
                """)
                connection.commit()
                print(
                    f"Updated {cursor.rowcount} transactions to UNKNOWN status")
            else:
                print("Messages exist in queue - QUEUED transactions remain valid")

        except Exception as e:
            print(f"Error checking SQS queue: {str(e)}")
            # If we can't check the queue, don't change any statuses
            print("Skipping status refresh due to SQS error")

        connection.close()

    except Exception as e:
        print(f"Error refreshing transaction statuses: {str(e)}")


def lambda_handler(event, context):
    """
    Lambda handler for the position keeper.

    This function handles manual triggers, scheduled invocations, and on-demand processing.
    """
    # Initialize caches at startup (only once per Lambda instance)
    initialize_caches()

    # Check if this is a manual trigger from the API
    if event.get("httpMethod") == "POST":
        print("Manual trigger via API - processing messages")
        try:
            processed_count = receive_and_process_messages(_queue_url)
            refresh_transaction_statuses()

            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': f'Position keeper processed {processed_count} messages',
                    'processed_count': processed_count,
                    'source': 'manual_api'
                })
            }
        except Exception as e:
            print(f"Error in manual position keeper execution: {str(e)}")
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': f'Position keeper execution failed: {str(e)}'
                })
            }

    # Check if this is a scheduled invocation or manual invocation
    source = event.get("source", "unknown")

    if source == "scheduled_rule":
        print("Scheduled invocation - running single batch processing")
        # For scheduled invocations, just run once
        processed_count = receive_and_process_messages(_queue_url)

        # Refresh transaction statuses after processing
        refresh_transaction_statuses()

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': f'Position Keeper processed {processed_count} messages (scheduled)',
                'processed_count': processed_count,
                'source': source
            })
        }
    else:
        print("On-demand invocation - starting processing loop")
        # For on-demand invocations, start the processing loop
        started = start_position_keeper_loop(context)

        # Always refresh transaction statuses after processing
        refresh_transaction_statuses()

        if started:
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Position Keeper started processing loop',
                    'source': source
                })
            }
        else:
            return {
                'statusCode': 409,  # Conflict
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Position Keeper already running in another instance',
                    'source': source
                })
            }


# For local testing
if __name__ == "__main__":
    # Simulate a Lambda event
    test_event = {"test": "position_keeper"}
    test_context = type('Context', (), {
        'function_name': 'position-keeper',
        'function_version': '$LATEST',
        'invoked_function_arn': 'arn:aws:lambda:us-east-2:123456789012:function:position-keeper',
        'memory_limit_in_mb': 128,
        'remaining_time_in_millis': lambda: 30000
    })()

    result = lambda_handler(test_event, test_context)
    print(f"Test result: {result}")
