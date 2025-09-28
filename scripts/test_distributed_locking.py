#!/usr/bin/env python3
"""
Test script for the distributed locking mechanism.
This tests that multiple Lambda instances cannot run simultaneously.
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


def test_lock_api():
    """Test the lock API directly."""
    lambda_client = boto3.client('lambda', region_name=REGION)

    status_print("Testing lock API directly...", "info")

    # Test 1: Acquire lock
    status_print("Test 1: Acquiring lock...", "info")
    event1 = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'action': 'set',
            'holder': 'test-stream-1:test-request-1'
        })
    }
    response1 = lambda_client.invoke(
        FunctionName='updateLambdaLocks',
        InvocationType='RequestResponse',
        Payload=json.dumps(event1)
    )

    result1 = json.loads(response1['Payload'].read())
    print(f"Response 1: {result1}")

    # Test 2: Try to acquire same lock (should fail)
    status_print(
        "Test 2: Trying to acquire same lock (should fail)...", "info")
    event2 = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'action': 'set',
            'holder': 'test-stream-2:test-request-2'
        })
    }
    response2 = lambda_client.invoke(
        FunctionName='updateLambdaLocks',
        InvocationType='RequestResponse',
        Payload=json.dumps(event2)
    )

    result2 = json.loads(response2['Payload'].read())
    print(f"Response 2: {result2}")

    # Test 3: Release lock
    status_print("Test 3: Releasing lock...", "info")
    event3 = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'action': 'delete',
            'holder': 'test-stream-1:test-request-1'
        })
    }
    response3 = lambda_client.invoke(
        FunctionName='updateLambdaLocks',
        InvocationType='RequestResponse',
        Payload=json.dumps(event3)
    )

    result3 = json.loads(response3['Payload'].read())
    print(f"Response 3: {result3}")

    # Test 4: Try to acquire lock again (should succeed)
    status_print(
        "Test 4: Trying to acquire lock again (should succeed)...", "info")
    event4 = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'action': 'set',
            'holder': 'test-stream-3:test-request-3'
        })
    }
    response4 = lambda_client.invoke(
        FunctionName='updateLambdaLocks',
        InvocationType='RequestResponse',
        Payload=json.dumps(event4)
    )

    result4 = json.loads(response4['Payload'].read())
    print(f"Response 4: {result4}")

    # Test 5: Clean up
    status_print("Test 5: Cleaning up...", "info")
    event5 = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'action': 'delete',
            'holder': 'test-stream-3:test-request-3'
        })
    }
    response5 = lambda_client.invoke(
        FunctionName='updateLambdaLocks',
        InvocationType='RequestResponse',
        Payload=json.dumps(event5)
    )

    result5 = json.loads(response5['Payload'].read())
    print(f"Response 5: {result5}")

    # Summary
    status_print("=" * 50, "info")
    status_print("LOCK API TEST SUMMARY:", "info")

    # Parse the body JSON for each result
    body1 = json.loads(result1.get('body', '{}'))
    body2 = json.loads(result2.get('body', '{}'))
    body3 = json.loads(result3.get('body', '{}'))
    body4 = json.loads(result4.get('body', '{}'))
    body5 = json.loads(result5.get('body', '{}'))

    if result1.get('statusCode') == 200 and body1.get('message') == 'Lock acquired successfully':
        status_print("✅ Test 1 PASSED: Lock acquired successfully", "success")
    else:
        status_print(f"❌ Test 1 FAILED: {result1}", "error")

    if result2.get('statusCode') == 409 and body2.get('message') == 'Lock already exists - another process is running':
        status_print("✅ Test 2 PASSED: Duplicate lock prevented", "success")
    else:
        status_print(f"❌ Test 2 FAILED: {result2}", "error")

    if result3.get('statusCode') == 200 and body3.get('message') == 'Lock released successfully':
        status_print("✅ Test 3 PASSED: Lock released successfully", "success")
    else:
        status_print(f"❌ Test 3 FAILED: {result3}", "error")

    if result4.get('statusCode') == 200 and body4.get('message') == 'Lock acquired successfully':
        status_print("✅ Test 4 PASSED: Lock acquired after release", "success")
    else:
        status_print(f"❌ Test 4 FAILED: {result4}", "error")

    if result5.get('statusCode') == 200 and body5.get('message') == 'Lock released successfully':
        status_print("✅ Test 5 PASSED: Cleanup successful", "success")
    else:
        status_print(f"❌ Test 5 FAILED: {result5}", "error")


def test_concurrent_position_keepers():
    """Test concurrent position keeper invocations."""
    lambda_client = boto3.client('lambda', region_name=REGION)

    status_print("Testing concurrent position keeper invocations...", "info")

    # Send a test message first
    status_print("Sending test message to queue...", "info")
    sqs = boto3.client('sqs', region_name=REGION)

    test_message = {
        "operation": "create",
        "transaction_id": 77777,
        "portfolio_entity_id": 1,
        "contra_entity_id": 2,
        "instrument_entity_id": 3,
        "transaction_type_id": 1,
        "transaction_status_id": 2,
        "properties": {"amount": 750000, "currency": "USD"},
        "updated_user_id": 1,
        "timestamp": "2024-01-01T00:00:00Z"
    }

    response = sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(test_message),
        MessageGroupId=f"test-concurrent-{uuid.uuid4()}",
        MessageDeduplicationId=f"test-concurrent-{uuid.uuid4()}"
    )

    status_print(f"Test message sent: {response['MessageId']}", "success")

    # Now try to invoke position keeper multiple times rapidly
    status_print("Invoking position keeper multiple times rapidly...", "info")

    responses = []
    for i in range(5):
        try:
            response = lambda_client.invoke(
                FunctionName='positionKeeper',
                InvocationType='Event',  # Asynchronous
                Payload=json.dumps({
                    "source": "test_script",
                    "trigger": f"concurrent_test_{i}"
                })
            )
            responses.append((i, response['StatusCode']))
            status_print(
                f"Invocation {i+1} sent: {response['StatusCode']}", "info")
        except Exception as e:
            status_print(f"Invocation {i+1} failed: {str(e)}", "error")

    # Wait for processing
    status_print("Waiting 15 seconds for processing...", "info")
    time.sleep(15)

    # Check queue status
    queue_response = sqs.get_queue_attributes(
        QueueUrl=QUEUE_URL,
        AttributeNames=['ApproximateNumberOfMessages']
    )

    messages_left = queue_response['Attributes'].get(
        'ApproximateNumberOfMessages', '0')

    status_print("=" * 50, "info")
    status_print("CONCURRENT TEST SUMMARY:", "info")
    print(f"  - Invocations sent: {len(responses)}")
    print(f"  - Messages left in queue: {messages_left}")

    if int(messages_left) == 0:
        status_print("✅ All messages processed successfully!", "success")
    else:
        status_print(f"⚠️ {messages_left} messages still in queue", "warning")


def main():
    """Main test function."""
    status_print("Testing Distributed Locking Mechanism", "info")
    status_print("=" * 50, "info")

    # Test 1: Direct lock API testing
    status_print("PART 1: Testing Lock API", "info")
    test_lock_api()

    print("\n")

    # Test 2: Concurrent position keeper testing
    status_print("PART 2: Testing Concurrent Position Keepers", "info")
    test_concurrent_position_keepers()

    status_print("=" * 50, "info")
    status_print("All tests completed!", "success")


if __name__ == "__main__":
    main()
