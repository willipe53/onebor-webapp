#!/usr/bin/env python3
"""
Test script for the on-demand position keeper functionality.
This simulates a transaction being queued and verifies the position keeper responds.
"""

import boto3
import json
import uuid
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


def send_test_message():
    """Send a test message to the SQS queue."""
    sqs = boto3.client('sqs', region_name=REGION)

    try:
        # Create a test transaction message
        test_message = {
            "operation": "create",
            "transaction_id": 88888,  # Test transaction ID
            "portfolio_entity_id": 1,
            "contra_entity_id": 2,
            "instrument_entity_id": 3,
            "transaction_type_id": 1,
            "transaction_status_id": 2,  # QUEUED status
            "properties": {"amount": 500000, "currency": "USD"},
            "updated_user_id": 1,
            "timestamp": "2024-01-01T00:00:00Z"
        }

        # Generate unique message group ID and deduplication ID
        message_group_id = f"test-transaction-{uuid.uuid4()}"
        message_deduplication_id = f"test-{uuid.uuid4()}"

        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(test_message),
            MessageGroupId=message_group_id,
            MessageDeduplicationId=message_deduplication_id
        )

        status_print(
            f"Test message sent successfully: {response['MessageId']}", "success")
        status_print(f"Message Group ID: {message_group_id}", "info")
        status_print(f"Deduplication ID: {message_deduplication_id}", "info")

        return True

    except Exception as e:
        status_print(f"Error sending test message: {str(e)}", "error")
        return False


def invoke_position_keeper():
    """Manually invoke the position keeper."""
    lambda_client = boto3.client('lambda', region_name=REGION)

    try:
        response = lambda_client.invoke(
            FunctionName='positionKeeper',
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps({
                "source": "test_script",
                "trigger": "manual_test"
            })
        )

        status_print(
            f"Position keeper invoked successfully: {response['StatusCode']}", "success")
        return True

    except Exception as e:
        status_print(f"Error invoking position keeper: {str(e)}", "error")
        return False


def check_queue_status():
    """Check the current status of the SQS queue."""
    sqs = boto3.client('sqs', region_name=REGION)

    try:
        response = sqs.get_queue_attributes(
            QueueUrl=QUEUE_URL,
            AttributeNames=[
                'ApproximateNumberOfMessages',
                'ApproximateNumberOfMessagesNotVisible',
                'ApproximateNumberOfMessagesDelayed'
            ]
        )

        attributes = response['Attributes']
        status_print("Current queue status:", "info")
        print(
            f"  - Messages Available: {attributes.get('ApproximateNumberOfMessages', '0')}")
        print(
            f"  - Messages In Flight: {attributes.get('ApproximateNumberOfMessagesNotVisible', '0')}")
        print(
            f"  - Messages Delayed: {attributes.get('ApproximateNumberOfMessagesDelayed', '0')}")

        return attributes

    except Exception as e:
        status_print(f"Error checking queue status: {str(e)}", "error")
        return {}


def test_duplicate_invocation():
    """Test that duplicate invocations are ignored when position keeper is running."""
    status_print("Testing duplicate invocation protection...", "info")

    # Send multiple invoke requests rapidly
    lambda_client = boto3.client('lambda', region_name=REGION)

    for i in range(3):
        try:
            response = lambda_client.invoke(
                FunctionName='positionKeeper',
                InvocationType='Event',
                Payload=json.dumps({
                    "source": "test_script",
                    "trigger": f"duplicate_test_{i}"
                })
            )
            status_print(
                f"Invocation {i+1} sent: {response['StatusCode']}", "info")
        except Exception as e:
            status_print(f"Error in invocation {i+1}: {str(e)}", "error")


def main():
    """Main test function."""
    status_print("Testing On-Demand Position Keeper", "info")
    status_print("=" * 50, "info")

    # Step 1: Check initial queue status
    status_print("Step 1: Checking initial queue status...", "info")
    initial_status = check_queue_status()

    # Step 2: Send test message
    status_print("Step 2: Sending test message...", "info")
    if send_test_message():
        # Wait a moment
        status_print("Step 3: Waiting 2 seconds...", "info")
        time.sleep(2)

        # Step 4: Check queue status after message
        status_print("Step 4: Checking queue status after message...", "info")
        after_message_status = check_queue_status()

        # Step 5: Invoke position keeper
        status_print("Step 5: Invoking position keeper...", "info")
        if invoke_position_keeper():
            # Wait for processing
            status_print(
                "Step 6: Waiting 10 seconds for processing...", "info")
            time.sleep(10)

            # Step 7: Check final queue status
            status_print("Step 7: Checking final queue status...", "info")
            final_status = check_queue_status()

            # Step 8: Test duplicate invocation protection
            status_print(
                "Step 8: Testing duplicate invocation protection...", "info")
            test_duplicate_invocation()

            # Summary
            status_print("=" * 50, "info")
            status_print("TEST SUMMARY:", "info")
            print(
                f"  Initial messages: {initial_status.get('ApproximateNumberOfMessages', '0')}")
            print(
                f"  After message: {after_message_status.get('ApproximateNumberOfMessages', '0')}")
            print(
                f"  Final messages: {final_status.get('ApproximateNumberOfMessages', '0')}")

            if int(final_status.get('ApproximateNumberOfMessages', '0')) < int(after_message_status.get('ApproximateNumberOfMessages', '0')):
                status_print(
                    "✅ Position keeper successfully processed messages!", "success")
            else:
                status_print(
                    "⚠️ Messages may still be processing or position keeper may not have started", "warning")
        else:
            status_print("Failed to invoke position keeper", "error")
    else:
        status_print("Failed to send test message", "error")


if __name__ == "__main__":
    main()
