import boto3
import json
import pymysql
import os
import uuid
from typing import Dict, Any, List, Optional

# CORS headers
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}


def get_db_secret():
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


def send_to_sqs(transaction_data: Dict[str, Any], operation: str) -> bool:
    """Send transaction data to SQS FIFO queue."""
    try:
        sqs = boto3.client('sqs', region_name='us-east-2')
        queue_url = "https://sqs.us-east-2.amazonaws.com/316490106381/pandatransactions.fifo"

        # Prepare message body
        message_body = {
            "operation": operation,  # "create" or "update"
            "transaction_id": transaction_data.get("transaction_id"),
            "portfolio_entity_id": transaction_data.get("portfolio_entity_id"),
            "contra_entity_id": transaction_data.get("contra_entity_id"),
            "instrument_entity_id": transaction_data.get("instrument_entity_id"),
            "transaction_type_id": transaction_data.get("transaction_type_id"),
            "transaction_status_id": transaction_data.get("transaction_status_id"),
            "properties": transaction_data.get("properties"),
            "updated_user_id": transaction_data.get("updated_user_id"),
            "timestamp": transaction_data.get("timestamp")
        }

        # Generate unique message group ID and deduplication ID
        message_group_id = f"transaction-{transaction_data.get('transaction_id', 'new')}"
        message_deduplication_id = f"{operation}-{transaction_data.get('transaction_id', uuid.uuid4())}-{int(os.urandom(4).hex(), 16)}"

        print(
            f"DEBUG: Sending to SQS - Group ID: {message_group_id}, Dedup ID: {message_deduplication_id}")

        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body),
            MessageGroupId=message_group_id,
            MessageDeduplicationId=message_deduplication_id
        )

        print(f"DEBUG: SQS message sent successfully: {response['MessageId']}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to send message to SQS: {str(e)}")
        return False


def lambda_handler(event, context):
    """Lambda handler for creating/updating transactions."""
    print(f"DEBUG: Event: {event}")

    try:
        # Parse the request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        print(f"DEBUG: Parsed body: {body}")

        # Extract parameters
        user_id = body.get("user_id")
        transaction_id = body.get("transaction_id")
        portfolio_entity_id = body.get("portfolio_entity_id")
        contra_entity_id = body.get("contra_entity_id")
        instrument_entity_id = body.get("instrument_entity_id")
        transaction_type_id = body.get("transaction_type_id")
        transaction_status_id = body.get("transaction_status_id")
        properties = body.get("properties")

        print(
            f"DEBUG: Extracted transaction_status_id: {transaction_status_id} (type: {type(transaction_status_id)})")

        # Validate required fields
        if not user_id:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "user_id is required"})
            }

        if not transaction_id and not all([portfolio_entity_id, instrument_entity_id, transaction_type_id]):
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "portfolio_entity_id, instrument_entity_id, and transaction_type_id are required for new transactions"})
            }

        # Get database connection
        conn = get_db_connection()

        try:
            with conn.cursor() as cursor:
                if transaction_id:
                    # Update existing transaction
                    updates = []
                    params = []

                    if portfolio_entity_id is not None:
                        updates.append("portfolio_entity_id = %s")
                        params.append(portfolio_entity_id)
                    if contra_entity_id is not None:
                        updates.append("contra_entity_id = %s")
                        params.append(contra_entity_id)
                    if instrument_entity_id is not None:
                        updates.append("instrument_entity_id = %s")
                        params.append(instrument_entity_id)
                    if transaction_type_id is not None:
                        updates.append("transaction_type_id = %s")
                        params.append(transaction_type_id)
                    if transaction_status_id is not None:
                        updates.append("transaction_status_id = %s")
                        params.append(transaction_status_id)
                        print(
                            f"DEBUG: Adding transaction_status_id to update: {transaction_status_id} (type: {type(transaction_status_id)})")
                    if properties is not None:
                        # Convert properties to JSON string if it's a dict
                        if isinstance(properties, dict):
                            properties = json.dumps(properties)
                        updates.append("properties = %s")
                        params.append(properties)

                    if not updates:
                        return {
                            "statusCode": 400,
                            "headers": cors_headers,
                            "body": json.dumps({"error": "No fields to update"})
                        }

                    updates.append("updated_user_id = %s")
                    params.append(user_id)
                    params.append(transaction_id)

                    sql = f"""
                        UPDATE transactions 
                        SET {', '.join(updates)}
                        WHERE transaction_id = %s
                    """

                    print(f"DEBUG: Update SQL: {sql}")
                    print(f"DEBUG: Update params: {params}")
                    print(
                        f"DEBUG: transaction_status_id in params: {transaction_status_id in params}")
                    if transaction_status_id in params:
                        print(
                            f"DEBUG: transaction_status_id value in params: {params[params.index(transaction_status_id)]}")

                    cursor.execute(sql, params)

                    if cursor.rowcount == 0:
                        return {
                            "statusCode": 404,
                            "headers": cors_headers,
                            "body": json.dumps({"error": f"Transaction with ID {transaction_id} not found"})
                        }

                    conn.commit()

                    # Send to SQS after successful update (only for QUEUED transactions)
                    if transaction_status_id == 2:  # QUEUED status
                        transaction_data = {
                            "transaction_id": transaction_id,
                            "portfolio_entity_id": portfolio_entity_id,
                            "contra_entity_id": contra_entity_id,
                            "instrument_entity_id": instrument_entity_id,
                            "transaction_type_id": transaction_type_id,
                            "transaction_status_id": transaction_status_id,
                            "properties": properties,
                            "updated_user_id": user_id,
                            "timestamp": context.aws_request_id if context else None
                        }

                        sqs_success = send_to_sqs(transaction_data, "update")
                        if not sqs_success:
                            print(
                                "WARNING: Failed to send update message to SQS, but transaction was updated successfully")
                    else:
                        print(
                            f"DEBUG: Transaction {transaction_id} updated to status {transaction_status_id}, not sending to SQS")

                    return {
                        "statusCode": 200,
                        "headers": cors_headers,
                        "body": json.dumps({
                            "success": True,
                            "message": f"Transaction {transaction_id} updated successfully",
                            "transaction_id": transaction_id
                        })
                    }

                else:
                    # Insert new transaction
                    # Set default transaction_status_id if not provided
                    if not transaction_status_id:
                        # Get the first available transaction status
                        cursor.execute(
                            "SELECT transaction_status_id FROM transaction_statuses LIMIT 1")
                        result = cursor.fetchone()
                        if result:
                            transaction_status_id = result['transaction_status_id']
                        else:
                            return {
                                "statusCode": 400,
                                "headers": cors_headers,
                                "body": json.dumps({"error": "No transaction statuses available"})
                            }

                    # Convert properties to JSON string if it's a dict
                    properties_value = properties
                    if isinstance(properties, dict):
                        properties_value = json.dumps(properties)

                    sql = """
                        INSERT INTO transactions (
                            portfolio_entity_id, 
                            contra_entity_id, 
                            instrument_entity_id, 
                            transaction_type_id, 
                            transaction_status_id, 
                            properties, 
                            updated_user_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """

                    params = [
                        portfolio_entity_id,
                        contra_entity_id,
                        instrument_entity_id,
                        transaction_type_id,
                        transaction_status_id,
                        properties_value,
                        user_id
                    ]

                    print(f"DEBUG: Insert SQL: {sql}")
                    print(f"DEBUG: Insert params: {params}")

                    cursor.execute(sql, params)
                    new_transaction_id = cursor.lastrowid

                    conn.commit()

                    # Send to SQS after successful creation (only for QUEUED transactions)
                    if transaction_status_id == 2:  # QUEUED status
                        transaction_data = {
                            "transaction_id": new_transaction_id,
                            "portfolio_entity_id": portfolio_entity_id,
                            "contra_entity_id": contra_entity_id,
                            "instrument_entity_id": instrument_entity_id,
                            "transaction_type_id": transaction_type_id,
                            "transaction_status_id": transaction_status_id,
                            "properties": properties,
                            "updated_user_id": user_id,
                            "timestamp": context.aws_request_id if context else None
                        }

                        sqs_success = send_to_sqs(transaction_data, "create")
                        if not sqs_success:
                            print(
                                "WARNING: Failed to send create message to SQS, but transaction was created successfully")
                    else:
                        print(
                            f"DEBUG: Transaction {new_transaction_id} created with status {transaction_status_id}, not sending to SQS")

                    return {
                        "statusCode": 200,
                        "headers": cors_headers,
                        "body": json.dumps({
                            "success": True,
                            "message": "Transaction created successfully",
                            "transaction_id": new_transaction_id
                        })
                    }

        finally:
            conn.close()

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Database error: {str(e)}"})
        }
