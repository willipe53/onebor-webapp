#!/usr/bin/env python3
"""
Generate curl commands for testing API endpoints.
Parses api.ts to find GET endpoints and generates curl commands with authentication.
"""

import os
import json
import re
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_BASE_URL = "https://api.onebor.com/panda"


def load_api_info():
    """Parse api.ts file to extract GET API information"""

    # Read the api.ts file
    api_file_path = "../src/services/api.ts"
    try:
        with open(api_file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find {api_file_path}")
        return []

    # Define the GET APIs we want to test
    get_apis = [
        {
            "name": "get_entity_types",
            "endpoint": "/get_entity_types",
            "description": "Query Entity Types",
            "parameters": [
                {"name": "count_only", "type": "boolean", "optional": True},
                {"name": "limit", "type": "number", "optional": True},
                {"name": "offset", "type": "number", "optional": True}
            ]
        },
        {
            "name": "get_entities",
            "endpoint": "/get_entities",
            "description": "Query Entities",
            "parameters": [
                {"name": "user_id", "type": "number", "optional": False},
                {"name": "entity_id", "type": "number", "optional": True},
                {"name": "name", "type": "string", "optional": True},
                {"name": "entity_type_id", "type": "number", "optional": True},
                {"name": "parent_entity_id", "type": "number", "optional": True},
                {"name": "client_group_id", "type": "number", "optional": True},
                {"name": "count_only", "type": "boolean", "optional": True}
            ]
        },
        {
            "name": "get_users",
            "endpoint": "/get_users",
            "description": "Query Users",
            "parameters": [
                {"name": "user_id", "type": "number", "optional": True},
                {"name": "sub", "type": "string", "optional": True},
                {"name": "email", "type": "string", "optional": True},
                {"name": "requesting_user_id", "type": "number", "optional": True},
                {"name": "count_only", "type": "boolean", "optional": True}
            ]
        },
        {
            "name": "get_client_groups",
            "endpoint": "/get_client_groups",
            "description": "Query Client Groups",
            "parameters": [
                {"name": "client_group_id", "type": "number", "optional": True},
                {"name": "user_id", "type": "number", "optional": True},
                {"name": "group_name", "type": "string", "optional": True},
                {"name": "count_only", "type": "boolean", "optional": True}
            ]
        },
        {
            "name": "manage_invitation_get",
            "endpoint": "/manage_invitation",
            "description": "Get Invitations",
            "parameters": [
                {"name": "action", "type": "string",
                    "optional": False, "fixed_value": "get"},
                {"name": "code", "type": "string", "optional": True},
                {"name": "client_group_id", "type": "number", "optional": True},
                {"name": "count_only", "type": "boolean", "optional": True}
            ]
        }
    ]

    return get_apis


def get_cognito_token():
    """Get Cognito authentication token using boto3"""
    username = os.getenv('TEST_USERNAME')
    password = os.getenv('TEST_PASSWORD')
    user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
    client_id = os.getenv('COGNITO_CLIENT_ID')

    if not all([username, password, user_pool_id, client_id]):
        print("Error: TEST_USERNAME, TEST_PASSWORD, COGNITO_USER_POOL_ID, and COGNITO_CLIENT_ID must be set in .env file")
        return None

    try:
        # Create Cognito client
        client = boto3.client('cognito-idp', region_name='us-east-2')

        print(f"🔑 Authenticating with Cognito as {username}...")

        # Initiate authentication
        response = client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )

        # Extract the JWT token
        if 'AuthenticationResult' in response:
            id_token = response['AuthenticationResult']['IdToken']
            print("✅ Successfully authenticated with Cognito")
            return id_token
        else:
            print("❌ Authentication failed: No AuthenticationResult in response")
            return None

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(
            f"❌ Cognito authentication failed: {error_code} - {error_message}")

        if error_code == 'NotAuthorizedException':
            print("💡 Check your username and password in .env file")
        elif error_code == 'UserNotFoundException':
            print("💡 User not found - check username in .env file")
        elif error_code == 'InvalidParameterException':
            print("💡 Check your Cognito configuration (User Pool ID, Client ID)")

        return None
    except Exception as e:
        print(f"❌ Unexpected error during authentication: {str(e)}")
        return None


def generate_parameter_combinations(parameters):
    """Generate different parameter combinations for testing"""
    combinations = []

    # 1. Empty parameters (only optional params)
    required_params = [p for p in parameters if not p["optional"]]
    if not required_params:
        combinations.append({})

    # 2. Only required parameters
    if required_params:
        required_combo = {}
        for param in required_params:
            if param.get("fixed_value"):
                required_combo[param["name"]] = param["fixed_value"]
            elif param["type"] == "number":
                required_combo[param["name"]] = 1
            elif param["type"] == "string":
                required_combo[param["name"]] = "test"
            elif param["type"] == "boolean":
                required_combo[param["name"]] = True
        combinations.append(required_combo)

    # 3. Required + some optional parameters
    optional_params = [p for p in parameters if p["optional"]]
    if required_params and optional_params:
        # Add combinations with different optional parameters
        # Limit to first 2 optional params
        for opt_param in optional_params[:2]:
            combo = required_combo.copy()
            if opt_param.get("fixed_value"):
                combo[opt_param["name"]] = opt_param["fixed_value"]
            elif opt_param["type"] == "number":
                combo[opt_param["name"]] = 1
            elif opt_param["type"] == "string":
                combo[opt_param["name"]] = "test"
            elif opt_param["type"] == "boolean":
                combo[opt_param["name"]] = True
            combinations.append(combo)

    # 4. Count only variations
    if any(p["name"] == "count_only" for p in parameters):
        count_combo = {}
        for param in required_params:
            if param.get("fixed_value"):
                count_combo[param["name"]] = param["fixed_value"]
            elif param["type"] == "number":
                count_combo[param["name"]] = 1
            elif param["type"] == "string":
                count_combo[param["name"]] = "test"
        count_combo["count_only"] = True
        combinations.append(count_combo)

    return combinations


def generate_curl_command(api, params, token):
    """Generate a curl command for the given API and parameters"""
    url = f"{API_BASE_URL}{api['endpoint']}"

    headers = [
        "Content-Type: application/json",
        f"Authorization: Bearer {token}"
    ]

    data = json.dumps(params, indent=2)

    curl_cmd = f"""curl -X POST "{url}" \\"""
    for header in headers:
        curl_cmd += f'\n  -H "{header}" \\'

    if params:
        curl_cmd += f"\n  -d '{data}'"
    else:
        curl_cmd += '\n  -d \'{}\''

    return curl_cmd


def main():
    """Generate curl commands for all GET APIs"""
    print("🚀 Generating curl commands for GET APIs...")
    print("=" * 60)

    # Get authentication token
    token = get_cognito_token()
    if not token:
        print("⚠️  Authentication failed. Using placeholder token.")
        print("📝 You'll need to replace 'COGNITO_JWT_TOKEN_HERE' with actual token.")
        token = "COGNITO_JWT_TOKEN_HERE"

    # Load API information
    apis = load_api_info()

    curl_commands = []

    for api in apis:
        print(f"\n📡 {api['description']} ({api['endpoint']})")
        print("-" * 40)

        # Generate parameter combinations
        param_combinations = generate_parameter_combinations(api['parameters'])

        for i, params in enumerate(param_combinations, 1):
            print(
                f"\n### Variation {i}: {json.dumps(params, indent=2) if params else 'Empty parameters'}")
            curl_cmd = generate_curl_command(api, params, token)
            print(curl_cmd)
            curl_commands.append({
                "api": api['name'],
                "variation": i,
                "params": params,
                "curl": curl_cmd
            })

    print(f"\n✅ Generated {len(curl_commands)} curl commands")
    print("\n📝 Note: Replace 'COGNITO_JWT_TOKEN_HERE' with your actual Cognito JWT token")
    print("🔗 Get token by authenticating with AWS Cognito using TEST_USERNAME and TEST_PASSWORD from .env")


if __name__ == "__main__":
    main()
