#!/usr/bin/env python3
"""
Test script to test position keeper logic directly without distributed locking.
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

def test_position_keeper_direct():
    """Test position keeper by directly invoking it with a message."""
    lambda_client = boto3.client('lambda', region_name=REGION)
    sqs = boto3.client('sqs', region_name=REGION)
    
    status_print("Testing Position Keeper Direct Processing", "info")
    status_print("=" * 60, "info")
    
    # Create a test message with a known transaction type
    test_message = {
        "operation": "create",
        "transaction_id": 99998,
        "portfolio_entity_id": 1,
        "contra_entity_id": 2,
        "instrument_entity_id": 3,
        "transaction_type_id": 1,  # Assuming this is a Buy transaction type
        "transaction_status_id": 2,
        "properties": {
            "amount": 1000,
            "price": 150.25,
            "trade_date": "2025-01-27",
            "settle_date": "2025-01-30",
            "currency_code": "USD",
            "settle_currency": "USD"
        },
        "updated_user_id": 1,
        "timestamp": "2025-01-27T10:00:00Z"
    }
    
    # Send message to SQS
    message_group_id = f"test-direct-{int(time.time())}"
    message_dedup_id = f"test-direct-{int(time.time())}"
    
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
        
        # Check queue status
        queue_response = sqs.get_queue_attributes(
            QueueUrl=QUEUE_URL,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        
        messages_before = queue_response['Attributes'].get('ApproximateNumberOfMessages', '0')
        print(f"Messages in queue before processing: {messages_before}")
        
        # Invoke position keeper
        status_print("Invoking position keeper...", "info")
        
        lambda_response = lambda_client.invoke(
            FunctionName='positionKeeper',
            InvocationType='Event',  # Asynchronous
            Payload=json.dumps({
                "source": "test_direct_script",
                "trigger": "direct_position_test"
            })
        )
        
        status_print(f"Position keeper invoked: {lambda_response['StatusCode']}", "success")
        
        # Wait for processing
        status_print("Waiting 15 seconds for processing...", "info")
        time.sleep(15)
        
        # Check queue status again
        queue_response = sqs.get_queue_attributes(
            QueueUrl=QUEUE_URL,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        
        messages_after = queue_response['Attributes'].get('ApproximateNumberOfMessages', '0')
        print(f"Messages in queue after processing: {messages_after}")
        
        status_print("=" * 60, "info")
        status_print("DIRECT TEST SUMMARY:", "info")
        print(f"  - Messages before: {messages_before}")
        print(f"  - Messages after: {messages_after}")
        
        if int(messages_after) < int(messages_before):
            status_print("✅ Position keeper processed messages successfully!", "success")
            status_print("Check CloudWatch logs for position keeping output", "info")
        else:
            status_print("⚠️ No messages were processed", "warning")
        
    except Exception as e:
        status_print(f"ERROR: {str(e)}", "error")
        return False
    
    return True

def main():
    """Main test function."""
    status_print("Position Keeper Direct Test", "info")
    
    test_position_keeper_direct()
    
    status_print("=" * 60, "info")
    status_print("Test completed!", "info")

if __name__ == "__main__":
    main()
