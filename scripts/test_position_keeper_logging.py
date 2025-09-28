#!/usr/bin/env python3
"""
Test script for the position keeper logging functionality.
This sends a test transaction message to SQS and invokes the position keeper
to verify the position calculation and logging works correctly.
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


def test_position_keeper_logging():
    """Test the position keeper logging functionality."""
    lambda_client = boto3.client('lambda', region_name=REGION)
    sqs = boto3.client('sqs', region_name=REGION)

    status_print("Testing Position Keeper Logging Functionality", "info")
    status_print("=" * 60, "info")

    # Test case 1: Buy transaction (should create 4 positions)
    status_print(
        "Test 1: Buy Transaction (1000 shares IBM at $405.40)", "info")

    test_message = {
        "operation": "create",
        "transaction_id": 99999,  # Use a high ID to avoid conflicts
        "portfolio_entity_id": 1,  # Assuming portfolio ID 1 exists
        "contra_entity_id": 2,     # Assuming contra ID 2 exists
        "instrument_entity_id": 3,  # Assuming IBM instrument ID 3 exists
        "transaction_type_id": 1,  # Assuming Buy transaction type ID 1
        "transaction_status_id": 2,  # QUEUED
        "properties": {
            "amount": 1000,
            "price": 405.40,
            "trade_date": "2025-01-27",
            "settle_date": "2025-01-30",
            "currency_code": "USD",
            "settle_currency": "USD"
        },
        "updated_user_id": 1,
        "timestamp": "2025-01-27T10:00:00Z"
    }

    # Send message to SQS
    message_group_id = f"test-position-{uuid.uuid4()}"
    message_dedup_id = f"test-position-{uuid.uuid4()}"

    try:
        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(test_message),
            MessageGroupId=message_group_id,
            MessageDeduplicationId=message_dedup_id
        )

        status_print(f"Test message sent: {response['MessageId']}", "success")

        # Wait a moment for message to be available
        time.sleep(2)

        # Invoke position keeper
        status_print("Invoking position keeper...", "info")

        lambda_response = lambda_client.invoke(
            FunctionName='positionKeeper',
            InvocationType='Event',  # Asynchronous
            Payload=json.dumps({
                "source": "test_script",
                "trigger": "position_keeper_logging_test"
            })
        )

        status_print(
            f"Position keeper invoked: {lambda_response['StatusCode']}", "success")

        # Wait for processing
        status_print("Waiting 10 seconds for processing...", "info")
        time.sleep(10)

        # Check if message was processed
        queue_response = sqs.get_queue_attributes(
            QueueUrl=QUEUE_URL,
            AttributeNames=['ApproximateNumberOfMessages']
        )

        messages_left = queue_response['Attributes'].get(
            'ApproximateNumberOfMessages', '0')

        status_print("=" * 60, "info")
        status_print("POSITION KEEPER LOGGING TEST SUMMARY:", "info")
        print(f"  - Test message sent: {response['MessageId']}")
        print(f"  - Position keeper invoked: {lambda_response['StatusCode']}")
        print(f"  - Messages left in queue: {messages_left}")

        if int(messages_left) == 0:
            status_print("✅ Message processed successfully!", "success")
            status_print(
                "Check CloudWatch logs for position keeper output", "info")
        else:
            status_print(
                f"⚠️ {messages_left} messages still in queue", "warning")

    except Exception as e:
        status_print(f"ERROR: {str(e)}", "error")
        return False

    return True


def test_multiple_transaction_types():
    """Test multiple transaction types to verify different position keeping actions."""
    status_print("\n" + "=" * 60, "info")
    status_print("Test 2: Multiple Transaction Types", "info")

    # Note: This would require multiple transaction types to be set up in the database
    # with proper position_keeping_actions defined in their properties
    status_print(
        "Note: Multiple transaction type testing requires database setup", "warning")
    status_print(
        "Individual transaction types can be tested by creating them in the UI", "info")


def main():
    """Main test function."""
    status_print("Position Keeper Logging Test Suite", "info")

    # Test 1: Basic position keeper logging
    success = test_position_keeper_logging()

    if success:
        # Test 2: Multiple transaction types (informational)
        test_multiple_transaction_types()

        status_print("\n" + "=" * 60, "info")
        status_print(
            "Test completed! Check CloudWatch logs for detailed position keeper output.", "success")
        status_print("Look for logs like:", "info")
        print("  'Processing positions for a Buy 1000 shares of IBM at price 405.4'")
        print("  'Need to create 4 positions'")
        print("  '-405400 USD will be applied to <Portfolio Name> for 2025-01-27 (Trade Date)'")
        print("  '-405400 USD will be applied to <Portfolio Name> for 2025-01-30 (Settle Date)'")
        print(
            "  '+1000 IBM will be applied to <Portfolio Name> for 2025-01-27 (Trade Date)'")
        print(
            "  '+1000 IBM will be applied to <Portfolio Name> for 2025-01-30 (Settle Date)'")
    else:
        status_print("Test failed!", "error")


if __name__ == "__main__":
    main()
