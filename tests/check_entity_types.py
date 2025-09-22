#!/usr/bin/env python3
"""
Quick check of entity types and their schemas
"""

import json
import requests
from dotenv import load_dotenv
import os
import boto3

# Load environment variables
load_dotenv()


def get_cognito_token():
    username = os.getenv('TEST_USERNAME')
    password = os.getenv('TEST_PASSWORD')
    user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
    client_id = os.getenv('COGNITO_CLIENT_ID')

    if not all([username, password, user_pool_id, client_id]):
        print("Error: Missing credentials in .env file")
        return None

    try:
        client = boto3.client('cognito-idp', region_name='us-east-2')
        response = client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={'USERNAME': username, 'PASSWORD': password}
        )

        if 'AuthenticationResult' in response:
            return response['AuthenticationResult']['IdToken']
    except Exception as e:
        print(f"Auth error: {str(e)}")
    return None


def main():
    print("🔍 Checking Entity Types and Schemas")
    print("=" * 50)

    token = get_cognito_token()
    if not token:
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.post(
            "https://api.onebor.com/panda/get_entity_types", headers=headers, json={})

        if response.status_code == 200:
            entity_types = response.json()
            print(f"✅ Found {len(entity_types)} entity types")

            for i, et in enumerate(entity_types[:5]):  # Show first 5
                print(
                    f"\n{i+1}. {et.get('name', 'Unnamed')} (ID: {et.get('entity_type_id', 'None')})")

                schema = et.get('attributes_schema')
                if schema:
                    if isinstance(schema, str):
                        try:
                            schema = json.loads(schema)
                        except:
                            print(
                                f"   ❌ Invalid JSON schema: {schema[:100]}...")
                            continue

                    if isinstance(schema, dict) and 'properties' in schema:
                        props = schema['properties']
                        if props:
                            print(f"   ✅ Properties: {list(props.keys())}")
                            # Show first property details
                            first_prop = list(props.items())[0]
                            print(
                                f"   📋 Example: {first_prop[0]} -> {first_prop[1]}")
                        else:
                            print(f"   ⚠️  Empty properties object")
                    else:
                        print(f"   ❌ No 'properties' in schema: {schema}")
                else:
                    print(f"   ❌ No attributes_schema")
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {str(e)}")


if __name__ == "__main__":
    main()
