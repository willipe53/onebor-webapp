#!/usr/bin/env python3
"""
Test the Lambda function directly without API Gateway
"""
import json
import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('tests/.env')


def test_lambda_directly():
    """Test the Lambda function directly"""
    lambda_client = boto3.client('lambda', region_name='us-east-2')

    # Test payload with real user ID
    test_payload = {
        'user_id': '81fb55e0-e0b1-704a-3aad-791c0788d612'  # Real user from database
    }

    print(f"🧪 Testing Lambda function directly with payload: {test_payload}")

    try:
        response = lambda_client.invoke(
            FunctionName='getPandaEntities',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )

        status_code = response['StatusCode']
        payload = json.loads(response['Payload'].read())

        print(f"📊 Lambda Status Code: {status_code}")
        print(f"📝 Lambda Response: {json.dumps(payload, indent=2)}")

        if status_code == 200:
            print("✅ Lambda function executed successfully")
        else:
            print("❌ Lambda function failed")

    except Exception as e:
        print(f"❌ Lambda invocation failed: {e}")


if __name__ == "__main__":
    test_lambda_directly()
