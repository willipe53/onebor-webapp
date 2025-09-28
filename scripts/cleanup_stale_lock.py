#!/usr/bin/env python3
"""
Script to manually cleanup stale locks in the lambda_locks table.
"""

import boto3
import json
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


def cleanup_stale_lock():
    """Clean up the stale lock."""
    lambda_client = boto3.client('lambda', region_name=REGION)

    status_print("Cleaning up stale lock...", "info")

    # Delete the lock
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'action': 'delete',
            'holder': 'manual-cleanup'
        })
    }

    try:
        response = lambda_client.invoke(
            FunctionName='updateLambdaLocks',
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        result = json.loads(response['Payload'].read())
        print(f"Cleanup response: {result}")

        if result.get('statusCode') == 200:
            status_print("✅ Stale lock cleaned up successfully", "success")
            return True
        else:
            status_print(f"❌ Failed to clean up lock: {result}", "error")
            return False

    except Exception as e:
        status_print(f"❌ Error cleaning up lock: {str(e)}", "error")
        return False


def test_lock_acquisition():
    """Test acquiring a fresh lock."""
    lambda_client = boto3.client('lambda', region_name=REGION)

    status_print("Testing fresh lock acquisition...", "info")

    # Try to acquire a lock
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'action': 'set',
            'holder': 'test-cleanup:test-request-id'
        })
    }

    try:
        response = lambda_client.invoke(
            FunctionName='updateLambdaLocks',
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )

        result = json.loads(response['Payload'].read())
        print(f"Lock acquisition response: {result}")

        if result.get('statusCode') == 200:
            status_print("✅ Fresh lock acquired successfully", "success")

            # Clean it up immediately
            cleanup_event = {
                'httpMethod': 'POST',
                'body': json.dumps({
                    'action': 'delete',
                    'holder': 'test-cleanup:test-request-id'
                })
            }

            cleanup_response = lambda_client.invoke(
                FunctionName='updateLambdaLocks',
                InvocationType='RequestResponse',
                Payload=json.dumps(cleanup_event)
            )

            cleanup_result = json.loads(cleanup_response['Payload'].read())
            print(f"Cleanup response: {cleanup_result}")

            return True
        else:
            status_print(f"❌ Failed to acquire fresh lock: {result}", "error")
            return False

    except Exception as e:
        status_print(f"❌ Error acquiring fresh lock: {str(e)}", "error")
        return False


def main():
    """Main function."""
    status_print("Stale Lock Cleanup Script", "info")
    status_print("=" * 40, "info")

    # Step 1: Clean up stale lock
    cleanup_success = cleanup_stale_lock()
    print()

    # Step 2: Test fresh lock acquisition
    if cleanup_success:
        test_lock_acquisition()

    status_print("=" * 40, "info")
    status_print("Cleanup complete", "info")


if __name__ == "__main__":
    main()
