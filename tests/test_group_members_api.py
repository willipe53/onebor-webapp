#!/usr/bin/env python3
"""
Test script to verify the client group members API
"""

import json
import requests
from dotenv import load_dotenv
import os
import boto3
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()

API_BASE_URL = "https://api.onebor.com/panda"


def get_cognito_token():
    """Get Cognito authentication token"""
    username = os.getenv('TEST_USERNAME')
    password = os.getenv('TEST_PASSWORD')
    user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
    client_id = os.getenv('COGNITO_CLIENT_ID')

    if not all([username, password, user_pool_id, client_id]):
        print("Error: Missing credentials in .env file")
        return None

    try:
        client = boto3.client('cognito-idp', region_name='us-east-2')

        print(f"🔑 Authenticating with Cognito as {username}...")

        response = client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )

        if 'AuthenticationResult' in response:
            id_token = response['AuthenticationResult']['IdToken']
            print("✅ Successfully authenticated")
            return id_token
        else:
            print("❌ Authentication failed")
            return None

    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        return None


def test_group_members_api():
    """Test the new client group members API"""
    print("🧪 Testing Client Group Members API")
    print("=" * 50)

    # Get authentication token
    token = get_cognito_token()
    if not token:
        print("❌ Failed to get auth token")
        return

    # Test parameters - using client group 19 from your example
    test_params = {
        "client_group_id": 19
    }

    print(f"🔧 Testing with parameters: {json.dumps(test_params, indent=2)}")

    url = f"{API_BASE_URL}/get_users"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        print(f"📡 Making POST request to: {url}")
        response = requests.post(url, headers=headers,
                                 json=test_params, timeout=30)

        print(f"📊 Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success Response:")

            if isinstance(result, list):
                print(f"   📊 Found {len(result)} members in client group 19:")
                for i, user in enumerate(result, 1):
                    print(
                        f"   {i}. User ID: {user.get('user_id')}, Email: {user.get('email')}")

                if len(result) == 0:
                    print(
                        "   ⚠️  No members found - this might indicate the group has no members")
            else:
                print(f"   Unexpected response format: {result}")

        else:
            print(f"❌ Error Response: {response.text}")

    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")


def test_count_members():
    """Test counting members"""
    print("\n🧪 Testing Count Members")
    print("=" * 30)

    token = get_cognito_token()
    if not token:
        return

    test_params = {
        "client_group_id": 19,
        "count_only": True
    }

    url = f"{API_BASE_URL}/get_users"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.post(url, headers=headers,
                                 json=test_params, timeout=30)
        print(f"📊 Response Status: {response.status_code}")

        if response.status_code == 200:
            count = response.json()
            print(f"✅ Member Count: {count}")
        else:
            print(f"❌ Count Error: {response.text}")

    except Exception as e:
        print(f"❌ Count failed: {str(e)}")


if __name__ == "__main__":
    test_group_members_api()
    test_count_members()

    print("\n💡 Next Steps:")
    print("1. Open ClientGroupForm in the UI to test the membership display")
    print("2. Verify that existing group members are now properly shown")
    print("3. Test adding/removing members through the TransferList")
