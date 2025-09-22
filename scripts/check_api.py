#!/usr/bin/env python3
"""
Check API deployment script - verifies all deployment steps from deploy_lambda.py
Usage: python3 check_api.py <function_name>
"""
import sys
import json
import boto3
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from scripts/.env
load_dotenv()

# Configuration (should match deploy_lambda.py)
REGION = os.getenv("REGION", "us-east-2")
ACCOUNT_ID = "316490106381"
ROLE_NAME = "service-role/getPandaEntityTypes-role-cpdc7xv7"
LAYER_ARNS = ["arn:aws:lambda:us-east-2:316490106381:layer:PyMySql112Layer:2"]
TIMEOUT = 30
VPC_SUBNETS = [
    "subnet-0192ac9f05f3f701c",
    "subnet-057c823728ef78117",
    "subnet-0dc1aed15b037a940",
]
VPC_SECURITY_GROUPS = ["sg-0a5a4038d1f4307f2"]
ENV_VARS = {
    "SECRET_ARN": "arn:aws:secretsmanager:us-east-2:316490106381:secret:PandaDbSecretCache-pdzjei"
}
REST_API_ID = "zwkvk3lyl3"
AUTH_TYPE = "COGNITO_USER_POOLS"
AUTHORIZER_ID = "5tr2r9"
STAGE_NAME = "dev"

# Initialize clients
session = boto3.Session(region_name=REGION)
lambda_client = session.client("lambda")
apigw_client = session.client("apigateway")
iam_client = session.client("iam")


def check_status(description, condition, details=""):
    """Print status with checkmark or X"""
    status = "✅" if condition else "❌"
    print(f"{status} {description}")
    if details and not condition:
        print(f"   Details: {details}")
    return condition


def check_lambda_function(fn_name):
    """Check Lambda function configuration"""
    print(f"\n🔍 Checking Lambda Function: {fn_name}")
    print("=" * 50)

    try:
        response = lambda_client.get_function(FunctionName=fn_name)
        config = response['Configuration']

        # Basic function existence
        check_status("Function exists", True)

        # Function state
        state = config.get('State', 'Unknown')
        check_status(f"Function state: {state}",
                     state in ['Active', 'Inactive'],
                     f"Current state: {state}")

        # Runtime
        runtime = config.get('Runtime', '')
        check_status("Runtime is Python 3.12",
                     runtime == "python3.12",
                     f"Current: {runtime}")

        # Timeout
        timeout = config.get('Timeout', 0)
        check_status(f"Timeout is {TIMEOUT} seconds",
                     timeout == TIMEOUT,
                     f"Current: {timeout}")

        # Memory
        memory = config.get('MemorySize', 0)
        check_status("Memory is 128 MB",
                     memory == 128,
                     f"Current: {memory}")

        # Layers
        layers = [layer['Arn'] for layer in config.get('Layers', [])]
        has_correct_layers = all(layer in layers for layer in LAYER_ARNS)
        check_status("Correct layers attached",
                     has_correct_layers,
                     f"Expected: {LAYER_ARNS}, Current: {layers}")

        # Environment variables
        env_vars = config.get('Environment', {}).get('Variables', {})
        env_correct = all(env_vars.get(k) == v for k, v in ENV_VARS.items())
        check_status("Environment variables correct",
                     env_correct,
                     f"Expected: {ENV_VARS}, Current: {env_vars}")

        # VPC Configuration
        vpc_config = config.get('VpcConfig', {})
        vpc_subnets = set(vpc_config.get('SubnetIds', []))
        vpc_sgs = set(vpc_config.get('SecurityGroupIds', []))

        subnets_correct = vpc_subnets == set(VPC_SUBNETS)
        sgs_correct = vpc_sgs == set(VPC_SECURITY_GROUPS)

        check_status("VPC subnets correct",
                     subnets_correct,
                     f"Expected: {VPC_SUBNETS}, Current: {list(vpc_subnets)}")
        check_status("Security groups correct",
                     sgs_correct,
                     f"Expected: {VPC_SECURITY_GROUPS}, Current: {list(vpc_sgs)}")

        # Role (check if it contains the expected role name)
        role_arn = config.get('Role', '')
        role_contains_expected = ROLE_NAME in role_arn
        check_status("Execution role correct",
                     role_contains_expected,
                     f"Expected role containing: {ROLE_NAME}, Current: {role_arn}")

        return True, config

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            check_status("Function exists", False, "Function not found")
            return False, None
        else:
            check_status("Function accessible", False, str(e))
            return False, None


def lambda_to_path(fn_name):
    """Convert function name to API path (same logic as deploy_lambda.py)"""
    import re
    # Remove 'panda' from anywhere in the filename (case insensitive)
    base = re.sub("panda", "", fn_name, flags=re.IGNORECASE)
    # Convert CamelCase to snake_case
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", base)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    # Remove leading underscores
    return snake.lstrip("_")


def check_api_gateway(fn_name, fn_arn):
    """Check API Gateway configuration"""
    path_part = lambda_to_path(fn_name)
    print(f"\n🔍 Checking API Gateway: /{path_part}")
    print("=" * 50)

    try:
        # Check if API exists
        api_response = apigw_client.get_rest_api(restApiId=REST_API_ID)
        check_status(f"API Gateway {REST_API_ID} exists", True)

        # Get all resources
        resources_response = apigw_client.get_resources(restApiId=REST_API_ID)
        resources = resources_response['items']

        # Find our resource
        target_resource = None
        for resource in resources:
            if resource.get('pathPart') == path_part:
                target_resource = resource
                break

        if not target_resource:
            check_status(f"Resource /{path_part} exists",
                         False, "Resource not found")
            return False

        check_status(f"Resource /{path_part} exists", True)
        resource_id = target_resource['id']

        # Check if POST method exists
        try:
            method_response = apigw_client.get_method(
                restApiId=REST_API_ID,
                resourceId=resource_id,
                httpMethod='POST'
            )
            check_status("POST method exists", True)

            # Check authorization
            auth_type = method_response.get('authorizationType', '')
            auth_id = method_response.get('authorizerId', '')

            check_status("Authorization type is COGNITO_USER_POOLS",
                         auth_type == AUTH_TYPE,
                         f"Current: {auth_type}")
            check_status(f"Authorizer ID is {AUTHORIZER_ID}",
                         auth_id == AUTHORIZER_ID,
                         f"Current: {auth_id}")

        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                check_status("POST method exists", False, "Method not found")
                return False
            else:
                check_status("POST method accessible", False, str(e))
                return False

        # Check integration
        try:
            integration_response = apigw_client.get_integration(
                restApiId=REST_API_ID,
                resourceId=resource_id,
                httpMethod='POST'
            )
            check_status("Lambda integration exists", True)

            # Check integration details
            integration_type = integration_response.get('type', '')
            integration_method = integration_response.get('httpMethod', '')
            integration_uri = integration_response.get('uri', '')

            expected_uri = f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{fn_arn}/invocations"

            check_status("Integration type is AWS_PROXY",
                         integration_type == "AWS_PROXY",
                         f"Current: {integration_type}")
            check_status("Integration method is POST",
                         integration_method == "POST",
                         f"Current: {integration_method}")
            check_status("Integration URI correct",
                         integration_uri == expected_uri,
                         f"Expected: {expected_uri[:80]}..., Current: {integration_uri[:80]}...")

        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                check_status("Lambda integration exists",
                             False, "Integration not found")
                return False
            else:
                check_status("Lambda integration accessible", False, str(e))
                return False

        return True

    except ClientError as e:
        check_status(f"API Gateway {REST_API_ID} accessible", False, str(e))
        return False


def check_lambda_permissions(fn_name, path_part):
    """Check Lambda permissions for API Gateway"""
    print(f"\n🔍 Checking Lambda Permissions")
    print("=" * 50)

    try:
        policy_response = lambda_client.get_policy(FunctionName=fn_name)
        policy = json.loads(policy_response['Policy'])

        # Look for API Gateway permission more flexibly
        expected_principal = 'apigateway.amazonaws.com'
        expected_action = 'lambda:InvokeFunction'
        api_gateway_found = False

        for statement in policy.get('Statement', []):
            # Check if this is an API Gateway permission
            principal = statement.get('Principal', {})
            action = statement.get('Action', '')

            # Handle both string and dict principal formats
            principal_service = None
            if isinstance(principal, str):
                principal_service = principal
            elif isinstance(principal, dict):
                principal_service = principal.get('Service', '')

            if (principal_service == expected_principal and
                    action == expected_action):
                api_gateway_found = True
                break

        check_status("API Gateway invoke permission exists",
                     api_gateway_found,
                     f"Looking for principal: {expected_principal}, action: {expected_action}")

        return api_gateway_found

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            check_status("Lambda permissions accessible",
                         False, "No resource policy found")
            return False
        else:
            check_status("Lambda permissions accessible", False, str(e))
            return False


def check_deployment(fn_name):
    """Check if API is deployed to stage"""
    print(f"\n🔍 Checking API Deployment")
    print("=" * 50)

    try:
        # Check if stage exists
        stage_response = apigw_client.get_stage(
            restApiId=REST_API_ID,
            stageName=STAGE_NAME
        )
        check_status(f"Stage '{STAGE_NAME}' exists", True)

        # Check recent deployments
        deployments_response = apigw_client.get_deployments(
            restApiId=REST_API_ID)
        deployments = deployments_response.get('items', [])

        if deployments:
            latest_deployment = max(
                deployments, key=lambda x: x.get('createdDate', ''))
            check_status("Recent deployment exists", True,
                         f"Latest: {latest_deployment.get('createdDate', 'Unknown')}")
        else:
            check_status("Recent deployment exists",
                         False, "No deployments found")

        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'NotFoundException':
            check_status(f"Stage '{STAGE_NAME}' exists",
                         False, "Stage not found")
            return False
        else:
            check_status("API deployment accessible", False, str(e))
            return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 check_api.py <function_name>")
        print("Example: python3 check_api.py updatePandaUser")
        sys.exit(1)

    fn_name = sys.argv[1]
    path_part = lambda_to_path(fn_name)

    print(f"🔧 API Deployment Check for: {fn_name}")
    print(f"📍 Expected API path: /{path_part}")
    print(
        f"🌐 Expected endpoint: https://{REST_API_ID}.execute-api.{REGION}.amazonaws.com/{STAGE_NAME}/{path_part}")

    # Check Lambda function
    lambda_ok, config = check_lambda_function(fn_name)

    if lambda_ok and config:
        fn_arn = config['FunctionArn']

        # Check API Gateway
        api_ok = check_api_gateway(fn_name, fn_arn)

        # Check permissions
        perms_ok = check_lambda_permissions(fn_name, path_part)

        # Check deployment
        deploy_ok = check_deployment(fn_name)

        # Summary
        print(f"\n📊 Summary")
        print("=" * 50)
        all_good = lambda_ok and api_ok and perms_ok and deploy_ok

        if all_good:
            print("✅ All checks passed! API should be working correctly.")
            print(
                f"🚀 Endpoint: https://{REST_API_ID}.execute-api.{REGION}.amazonaws.com/{STAGE_NAME}/{path_part}")
        else:
            print("❌ Some checks failed. Review the issues above.")
            print(
                "💡 Consider running the deploy script again to fix missing configurations.")

    else:
        print("\n❌ Cannot proceed with further checks due to Lambda function issues.")


if __name__ == "__main__":
    main()
