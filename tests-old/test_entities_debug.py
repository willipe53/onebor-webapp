#!/usr/bin/env python3
"""
Test script to debug the getPandaEntities function using credentials from tests/.env
"""
import os
import sys
import json
import boto3
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv('tests/.env')


def get_cognito_token():
    """Get Cognito access token using the credentials from .env"""
    cognito_client = boto3.client('cognito-idp', region_name='us-east-2')

    username = os.getenv('TEST_USERNAME')
    password = os.getenv('TEST_PASSWORD')
    client_id = os.getenv('COGNITO_CLIENT_ID')

    print(f"Authenticating user: {username}")

    try:
        # Try ADMIN_NO_SRP_AUTH first
        response = cognito_client.admin_initiate_auth(
            UserPoolId=os.getenv('COGNITO_USER_POOL_ID'),
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )

        access_token = response['AuthenticationResult']['AccessToken']
        print("✅ Authentication successful")
        return access_token

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None


def test_get_entities():
    """Test the getPandaEntities function"""
    access_token = get_cognito_token()
    if not access_token:
        return

    api_base_url = 'https://api.onebor.com/panda'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Test data
    test_data = {
        'user_id': 'test-user-123'  # This will be the Cognito user ID
    }

    print(f"\n🔍 Testing getPandaEntities with data: {test_data}")
    print(f"🌐 API URL: {api_base_url}/get_entities")

    try:
        response = requests.post(
            f"{api_base_url}/get_entities",
            headers=headers,
            json=test_data,
            timeout=30
        )

        print(f"📊 Status Code: {response.status_code}")
        print(f"📝 Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Error! Response: {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {e}")


if __name__ == "__main__":
    test_get_entities()
