#!/usr/bin/env python3
"""
Test script for insertPandaTransaction Lambda function
"""

import boto3
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env in the same directory as this script
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)


def test_insert_transaction():
    """Test the insertPandaTransaction Lambda function"""

    print("🧪 Testing insertPandaTransaction Lambda Function")
    print("=" * 60)

    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-east-2')

    # Test payload
    test_payload = {
        "party_entity_id": 1,
        "contra_entity_id": 2,
        "unit_entity_id": 3,
        "quantity": 100.0,
        "price": 25.50,
        "transaction_type_id": 1,
        "properties": {
            "notes": "Test transaction from Python script",
            "source": "test_script"
        }
    }

    print(f"📡 Test Payload:")
    print(json.dumps(test_payload, indent=2))
    print()

    try:
        print("⏳ Invoking Lambda function...")

        response = lambda_client.invoke(
            FunctionName='insertPandaTransaction',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )

        # Parse response
        status_code = response['StatusCode']
        payload = json.loads(response['Payload'].read())

        print(f"📊 Lambda Response Status: {status_code}")
        print(f"📄 Lambda Response:")
        print(json.dumps(payload, indent=2))

        if status_code == 200:
            print("\n✅ Lambda function executed successfully!")

            # Parse the actual response body
            if 'body' in payload:
                body = json.loads(payload['body']) if isinstance(
                    payload['body'], str) else payload['body']

                if body.get('success'):
                    print(f"🎉 Transaction inserted successfully!")
                    print(f"   Transaction ID: {body.get('transaction_id')}")
                    print(f"   Party Entity ID: {body.get('party_entity_id')}")
                    print(
                        f"   contra Entity ID: {body.get('contra_entity_id')}")
                    print(f"   Unit Entity ID: {body.get('unit_entity_id')}")
                    print(f"   Quantity: {body.get('quantity')}")
                    print(f"   Price: {body.get('price')}")
                    print(
                        f"   Transaction Type ID: {body.get('transaction_type_id')}")
                else:
                    print(
                        f"❌ Transaction insertion failed: {body.get('message')}")

        else:
            print(f"❌ Lambda function failed with status code: {status_code}")

    except Exception as e:
        print(f"❌ Error invoking Lambda function: {str(e)}")
        return False

    return True


def test_sqs_queue():
    """Test if we can access the SQS queue"""
    print(f"\n🔍 Testing SQS Queue Access")
    print("=" * 30)

    sqs_url = "https://sqs.us-east-2.amazonaws.com/316490106381/pandatransactions.fifo"

    try:
        sqs = boto3.client('sqs', region_name='us-east-2')

        print(f"📡 Getting queue attributes for: {sqs_url}")

        response = sqs.get_queue_attributes(
            QueueUrl=sqs_url,
            AttributeNames=['QueueArn', 'VisibilityTimeout',
                            'MessageRetentionPeriod']
        )

        print("✅ SQS Queue accessible:")
        for attr, value in response['Attributes'].items():
            print(f"   {attr}: {value}")

    except Exception as e:
        print(f"❌ SQS Queue access error: {str(e)}")
        return False

    return True


if __name__ == "__main__":
    print("🚀 Starting insertPandaTransaction Tests")
    print()

    # Test SQS access first
    sqs_success = test_sqs_queue()

    # Test Lambda function
    lambda_success = test_insert_transaction()

    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"   SQS Access: {'✅ PASS' if sqs_success else '❌ FAIL'}")
    print(f"   Lambda Function: {'✅ PASS' if lambda_success else '❌ FAIL'}")

    if sqs_success and lambda_success:
        print("\n🎉 All tests passed! The insertPandaTransaction function is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Please check the output above for details.")
