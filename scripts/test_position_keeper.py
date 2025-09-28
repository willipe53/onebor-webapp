#!/usr/bin/env python3
"""
Test script for the position keeper by sending a test message to the SQS queue.
"""

import boto3
import json
import uuid
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
            "transaction_id": 99999,  # Test transaction ID
            "portfolio_entity_id": 1,
            "contra_entity_id": 2,
            "instrument_entity_id": 3,
            "transaction_type_id": 1,
            "transaction_status_id": 2,  # QUEUED status
            "properties": {"amount": 1000000, "currency": "USD"},
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
        
        status_print(f"Test message sent successfully: {response['MessageId']}", "success")
        status_print(f"Message Group ID: {message_group_id}", "info")
        status_print(f"Deduplication ID: {message_deduplication_id}", "info")
        
        return True
        
    except Exception as e:
        status_print(f"Error sending test message: {str(e)}", "error")
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
        print(f"  - Messages Available: {attributes.get('ApproximateNumberOfMessages', '0')}")
        print(f"  - Messages In Flight: {attributes.get('ApproximateNumberOfMessagesNotVisible', '0')}")
        print(f"  - Messages Delayed: {attributes.get('ApproximateNumberOfMessagesDelayed', '0')}")
        
        return True
        
    except Exception as e:
        status_print(f"Error checking queue status: {str(e)}", "error")
        return False

def main():
    """Main test function."""
    status_print("Testing Position Keeper", "info")
    
    # Check initial queue status
    status_print("Step 1: Checking initial queue status...", "info")
    check_queue_status()
    
    # Send test message
    status_print("Step 2: Sending test message...", "info")
    if send_test_message():
        # Wait a moment for processing
        status_print("Step 3: Waiting 10 seconds for processing...", "info")
        import time
        time.sleep(10)
        
        # Check queue status again
        status_print("Step 4: Checking queue status after processing...", "info")
        check_queue_status()
        
        status_print("Test completed! Check the queue status above to see if the message was processed.", "success")
    else:
        status_print("Test failed to send message", "error")

if __name__ == "__main__":
    main()
