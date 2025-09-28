#!/usr/bin/env python3
"""
Debug script to test the position keeper step by step.
"""

import boto3
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

REGION = os.getenv("REGION", "us-east-2")
QUEUE_URL = "https://sqs.us-east-2.amazonaws.com/316490106381/pandatransactions.fifo"


def status_print(message, level="info"):
    """Print status message with appropriate formatting."""
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    print(f"{icons.get(level, 'ℹ️')} {message}")


def test_lock_api_directly():
    """Test the lock API directly."""
    status_print("Testing Lock API directly...", "info")

    lambda_client = boto3.client('lambda', region_name=REGION)

    # Test acquiring a lock
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'action': 'set',
            'holder': 'debug-test:debug-request-id'
        })
    }

    try:
        response = lambda_client.invoke(
            FunctionName='updateLambdaLocks',
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        result = json.loads(response['Payload'].read())
        print(f"Lock API response: {result}")

        if result.get('statusCode') == 200:
            status_print("✅ Lock API is working", "success")
            return True
        else:
            status_print(f"❌ Lock API failed: {result}", "error")
            return False

    except Exception as e:
        status_print(f"❌ Lock API error: {str(e)}", "error")
        return False


def test_sqs_directly():
    """Test SQS directly."""
    status_print("Testing SQS directly...", "info")

    sqs = boto3.client('sqs', region_name=REGION)

    try:
        # Check queue attributes
        response = sqs.get_queue_attributes(
            QueueUrl=QUEUE_URL,
            AttributeNames=['ApproximateNumberOfMessages',
                            'ApproximateNumberOfMessagesNotVisible']
        )

        attrs = response['Attributes']
        visible = attrs.get('ApproximateNumberOfMessages', '0')
        not_visible = attrs.get('ApproximateNumberOfMessagesNotVisible', '0')

        print(
            f"Queue status: {visible} visible, {not_visible} being processed")

        if int(visible) > 0:
            # Try to receive a message
            receive_response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=0
            )

            messages = receive_response.get('Messages', [])
            if messages:
                message = messages[0]
                print(f"Received message: {message['MessageId']}")
                print(f"Message body: {message['Body']}")

                # Delete the message to clean up
                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=message['ReceiptHandle']
                )
                status_print("✅ SQS is working", "success")
                return True
            else:
                status_print("⚠️ No messages received", "warning")
                return False
        else:
            status_print("⚠️ No messages in queue", "warning")
            return False

    except Exception as e:
        status_print(f"❌ SQS error: {str(e)}", "error")
        return False


def test_position_keeper_with_debug():
    """Test position keeper with debug information."""
    status_print("Testing position keeper with debug...", "info")

    lambda_client = boto3.client('lambda', region_name=REGION)

    # Create a test message first
    sqs = boto3.client('sqs', region_name=REGION)

    test_message = {
        "operation": "create",
        "transaction_id": 88888,
        "portfolio_entity_id": 1,
        "contra_entity_id": 2,
        "instrument_entity_id": 3,
        "transaction_type_id": 1,
        "transaction_status_id": 2,
        "properties": {
            "amount": 100,
            "price": 50.0,
            "trade_date": "2025-01-27",
            "settle_date": "2025-01-30",
            "currency_code": "USD"
        },
        "updated_user_id": 1,
        "timestamp": "2025-01-27T10:00:00Z"
    }

    try:
        # Send test message
        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(test_message),
            MessageGroupId="debug-test-group",
            MessageDeduplicationId="debug-test-dedup"
        )

        status_print(f"Test message sent: {response['MessageId']}", "success")

        # Wait a moment
        time.sleep(2)

        # Invoke position keeper
        lambda_response = lambda_client.invoke(
            FunctionName='positionKeeper',
            InvocationType='Event',
            Payload=json.dumps({
                "source": "debug_script",
                "trigger": "debug_test"
            })
        )

        status_print(
            f"Position keeper invoked: {lambda_response['StatusCode']}", "success")

        # Wait for processing
        time.sleep(15)

        # Check queue status
        queue_response = sqs.get_queue_attributes(
            QueueUrl=QUEUE_URL,
            AttributeNames=['ApproximateNumberOfMessages']
        )

        messages_left = queue_response['Attributes'].get(
            'ApproximateNumberOfMessages', '0')
        print(f"Messages left after processing: {messages_left}")

        return True

    except Exception as e:
        status_print(f"❌ Position keeper test error: {str(e)}", "error")
        return False


def main():
    """Main debug function."""
    status_print("Position Keeper Debug Script", "info")
    status_print("=" * 50, "info")

    # Test 1: Lock API
    lock_ok = test_lock_api_directly()
    print()

    # Test 2: SQS
    sqs_ok = test_sqs_directly()
    print()

    # Test 3: Position keeper
    if lock_ok and sqs_ok:
        test_position_keeper_with_debug()
    else:
        status_print(
            "Skipping position keeper test due to previous failures", "warning")

    status_print("=" * 50, "info")
    status_print("Debug complete", "info")


if __name__ == "__main__":
    main()
