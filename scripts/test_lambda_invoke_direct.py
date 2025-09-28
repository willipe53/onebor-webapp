#!/usr/bin/env python3
"""
Test script to verify Lambda-to-Lambda invocation works
"""
import boto3
import json


def test_lambda_invoke():
    """Test if updatePandaTransaction can invoke positionKeeper"""
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-2')

        print("🧪 Testing Lambda-to-Lambda invocation...")

        # Test invoking positionKeeper directly
        response = lambda_client.invoke(
            FunctionName='positionKeeper',
            InvocationType='RequestResponse',  # Synchronous for testing
            Payload=json.dumps({
                "source": "test_script",
                "trigger": "manual_test"
            })
        )

        print(f"✅ Lambda invoke successful!")
        print(f"   Status Code: {response['StatusCode']}")

        # Read the response payload
        payload = json.loads(response['Payload'].read())
        print(f"   Response: {payload}")

        return True

    except Exception as e:
        print(f"❌ Lambda invoke failed: {str(e)}")
        return False


if __name__ == "__main__":
    test_lambda_invoke()
