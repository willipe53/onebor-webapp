#!/usr/bin/env python3
"""
Test script to check available transaction reference data
"""

import boto3
import json
import os
from dotenv import load_dotenv

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)


def test_entities():
    """Get some existing entities"""
    print("🔍 Checking available entities...")

    lambda_client = boto3.client('lambda', region_name='us-east-2')

    try:
        response = lambda_client.invoke(
            FunctionName='getPandaEntities',
            Payload=json.dumps({"user_id": 10})  # Basic query
        )

        payload = json.loads(response['Payload'].read())

        if response['StatusCode'] == 200 and 'body' in payload:
            entities = json.loads(payload['body'])
            print(f"✅ Found {len(entities)} entities")

            # Show first few entities
            for i, entity in enumerate(entities[:5]):
                print(
                    f"   {i+1}. ID: {entity.get('entity_id')}, Name: {entity.get('name')}")

            return entities[:5] if entities else []
        else:
            print(f"❌ Failed to get entities: {payload}")
            return []

    except Exception as e:
        print(f"❌ Error getting entities: {str(e)}")
        return []


def test_with_real_data():
    """Test insertPandaTransaction with real entity IDs"""

    entities = test_entities()

    if len(entities) < 3:
        print("❌ Need at least 3 entities for testing")
        return False

    print(f"\n🧪 Testing insertPandaTransaction with real entity IDs...")

    # Use the first 3 entities
    test_payload = {
        "party_entity_id": entities[0]['entity_id'],
        "counterparty_entity_id": entities[1]['entity_id'],
        "unit_entity_id": entities[2]['entity_id'],
        "quantity": 50.0,
        "price": 100.25,
        "transaction_type_id": 1,  # Assuming this exists
        "properties": {
            "notes": "Test transaction with real entity IDs",
            "source": "test_script"
        }
    }

    print(f"📡 Using entities:")
    print(f"   Party: {entities[0]['name']} (ID: {entities[0]['entity_id']})")
    print(
        f"   Counterparty: {entities[1]['name']} (ID: {entities[1]['entity_id']})")
    print(f"   Unit: {entities[2]['name']} (ID: {entities[2]['entity_id']})")
    print()

    lambda_client = boto3.client('lambda', region_name='us-east-2')

    try:
        print("⏳ Invoking insertPandaTransaction...")

        response = lambda_client.invoke(
            FunctionName='insertPandaTransaction',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )

        status_code = response['StatusCode']
        payload = json.loads(response['Payload'].read())

        print(f"📊 Response Status: {status_code}")
        print(f"📄 Response:")
        print(json.dumps(payload, indent=2))

        if status_code == 200 and 'body' in payload:
            body = json.loads(payload['body']) if isinstance(
                payload['body'], str) else payload['body']

            if body.get('success'):
                print(f"\n🎉 Transaction inserted successfully!")
                print(f"   Transaction ID: {body.get('transaction_id')}")
                return True
            else:
                print(f"\n❌ Transaction failed: {body.get('message')}")
        else:
            print(f"\n❌ Lambda execution failed")

        return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 Testing Transaction Data and Insert Function")
    print("=" * 60)

    success = test_with_real_data()

    print("\n" + "=" * 60)
    if success:
        print("✅ Transaction insert test PASSED!")
    else:
        print("❌ Transaction insert test FAILED!")
        print("\n💡 Common issues:")
        print("   • Foreign key constraints (entity IDs don't exist)")
        print("   • Missing transaction_status_id or transaction_type_id")
        print("   • Database connection timeout")
        print("   • SQS permissions")
