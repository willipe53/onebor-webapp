#!/usr/bin/env python3
"""
Test script to verify Lambda-to-Lambda invocation works.
"""

import boto3
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

REGION = os.getenv("REGION", "us-east-2")


def status_print(message, level="info"):
    """Print status message with appropriate formatting."""
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    print(f"{icons.get(level, 'ℹ️')} {message}")


def test_lambda_invocation_from_lambda():
    """Test if one Lambda can invoke another Lambda."""
    lambda_client = boto3.client('lambda', region_name=REGION)

    status_print("Testing Lambda-to-Lambda invocation...", "info")

    # Create a simple test payload
    test_payload = {
        "test": "lambda_invocation_test",
        "timestamp": time.time()
    }

    try:
        # Try to invoke updateLambdaLocks from a test context
        response = lambda_client.invoke(
            FunctionName='updateLambdaLocks',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'httpMethod': 'POST',
                'body': json.dumps({
                    'action': 'set',
                    'holder': 'lambda-test:test-request-id'
                })
            })
        )

        result = json.loads(response['Payload'].read())
        print(f"Invocation result: {result}")

        if result.get('statusCode') == 200:
            status_print("✅ Lambda-to-Lambda invocation works", "success")

            # Clean up the test lock
            cleanup_response = lambda_client.invoke(
                FunctionName='updateLambdaLocks',
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'httpMethod': 'POST',
                    'body': json.dumps({
                        'action': 'delete',
                        'holder': 'lambda-test:test-request-id'
                    })
                })
            )

            cleanup_result = json.loads(cleanup_response['Payload'].read())
            print(f"Cleanup result: {cleanup_result}")

            return True
        else:
            status_print(f"❌ Lambda invocation failed: {result}", "error")
            return False

    except Exception as e:
        status_print(f"❌ Lambda invocation error: {str(e)}", "error")
        return False


def test_position_keeper_simple():
    """Test position keeper with a simple invocation."""
    lambda_client = boto3.client('lambda', region_name=REGION)

    status_print("Testing position keeper with simple invocation...", "info")

    try:
        # Invoke position keeper synchronously to see the response
        response = lambda_client.invoke(
            FunctionName='positionKeeper',
            InvocationType='RequestResponse',  # Synchronous this time
            Payload=json.dumps({
                "source": "test_script",
                "trigger": "simple_test"
            })
        )

        result = json.loads(response['Payload'].read())
        print(f"Position keeper response: {result}")

        if response['StatusCode'] == 200:
            status_print("✅ Position keeper invocation successful", "success")
            return True
        else:
            status_print(
                f"❌ Position keeper invocation failed: {result}", "error")
            return False

    except Exception as e:
        status_print(f"❌ Position keeper invocation error: {str(e)}", "error")
        return False


def main():
    """Main test function."""
    status_print("Lambda Invocation Test Suite", "info")
    status_print("=" * 50, "info")

    # Test 1: Direct Lambda-to-Lambda invocation
    lambda_ok = test_lambda_invocation_from_lambda()
    print()

    # Test 2: Position keeper synchronous invocation
    if lambda_ok:
        test_position_keeper_simple()

    status_print("=" * 50, "info")
    status_print("Test complete", "info")


if __name__ == "__main__":
    main()
