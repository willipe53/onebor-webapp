#!/usr/bin/env python3
"""
Test script to verify the modifyClientGroupMembership API
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


def test_membership_api():
    """Test the client group membership API"""
    print("🧪 Testing Client Group Membership API")
    print("=" * 50)

    # Get authentication token
    token = get_cognito_token()
    if not token:
        print("❌ Failed to get auth token")
        return

    # Test parameters - using the values from your example
    test_params = {
        "client_group_id": 19,  # From your manual fix
        "user_id": 234,         # From your manual fix
        "add_or_remove": "add"
    }

    print(f"🔧 Testing with parameters: {json.dumps(test_params, indent=2)}")

    url = f"{API_BASE_URL}/modify_client_group_membership"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        print(f"📡 Making POST request to: {url}")
        response = requests.post(url, headers=headers,
                                 json=test_params, timeout=30)

        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success Response: {json.dumps(result, indent=2)}")

            # Check if rows were actually affected
            rows_affected = result.get("rows_affected", 0)
            if rows_affected > 0:
                print(f"✅ Database updated: {rows_affected} rows affected")
            else:
                print(f"⚠️  No rows affected - membership may already exist")

        else:
            print(f"❌ Error Response: {response.text}")

    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")


def test_remove_membership():
    """Test removing the membership to see if API works in reverse"""
    print("\n🧪 Testing Remove Membership (to verify API works)")
    print("=" * 50)

    token = get_cognito_token()
    if not token:
        return

    test_params = {
        "client_group_id": 19,
        "user_id": 234,
        "add_or_remove": "remove"
    }

    print(
        f"🔧 Testing REMOVE with parameters: {json.dumps(test_params, indent=2)}")

    url = f"{API_BASE_URL}/modify_client_group_membership"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.post(url, headers=headers,
                                 json=test_params, timeout=30)
        print(f"📊 Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Remove Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Remove Error: {response.text}")

    except Exception as e:
        print(f"❌ Remove failed: {str(e)}")


if __name__ == "__main__":
    test_membership_api()
    test_remove_membership()

    print("\n💡 Suggestions:")
    print("1. Check AWS CloudWatch logs for the Lambda function")
    print("2. Verify the client_group_users table structure")
    print("3. Check for any foreign key constraints")
    print("4. Test with different user_id and client_group_id values")
