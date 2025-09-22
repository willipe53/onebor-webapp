#!/usr/bin/env python3
"""
Improved Lambda deployment script that handles existing resources gracefully.
Combines functionality from deploy_lambda.py and check_api.py.
"""
import os
import io
import sys
import json
import time
import zipfile
import re
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from scripts/.env
load_dotenv()

REGION = os.getenv("REGION", "us-east-2")
ACCOUNT_ID = "316490106381"

ROLE_NAME = "getPandaEntityTypes-role-cpdc7xv7"
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

session = boto3.Session(region_name=REGION)
lambda_client = session.client("lambda")
apigw_client = session.client("apigateway")
iam_client = session.client("iam")


def status_print(message, status="info"):
    """Print formatted status messages"""
    icons = {"info": "ℹ️", "success": "✅",
             "warning": "⚠️", "error": "❌", "update": "🔄"}
    print(f"{icons.get(status, 'ℹ️')} {message}")


def role_arn_from_name(role_name: str) -> str:
    """Get role ARN from name, trying both direct and service-role prefix"""
    try:
        resp = iam_client.get_role(RoleName=role_name)
        return resp["Role"]["Arn"]
    except ClientError:
        try:
            service_role_name = f"service-role/{role_name}"
            resp = iam_client.get_role(RoleName=service_role_name)
            return resp["Role"]["Arn"]
        except ClientError:
            resp = iam_client.get_role(RoleName=role_name)
            return resp["Role"]["Arn"]


def zip_single_py(filepath: str) -> bytes:
    """Create a zip file containing a single Python file"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Use the original filename to ensure correct module naming
        zf.write(filepath, arcname=os.path.basename(filepath))
    return buf.getvalue()


def function_exists(fn_name: str) -> bool:
    """Check if Lambda function exists"""
    try:
        lambda_client.get_function(FunctionName=fn_name)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def get_function_config(fn_name: str):
    """Get Lambda function configuration"""
    try:
        response = lambda_client.get_function(FunctionName=fn_name)
        return response["Configuration"]
    except ClientError:
        return None


def needs_config_update(fn_name: str) -> bool:
    """Check if function configuration needs updating"""
    config = get_function_config(fn_name)
    if not config:
        return True

    # Check key configuration values
    needs_update = False

    if config.get("Timeout") != TIMEOUT:
        status_print(
            f"Timeout differs: current={config.get('Timeout')}, expected={TIMEOUT}", "warning")
        needs_update = True

    current_runtime = config.get("Runtime", "")
    # Only update runtime if it's older than what we expect
    if current_runtime and not current_runtime.startswith("python3.1") or current_runtime < "python3.12":
        status_print(
            f"Runtime differs: current={current_runtime}, expected=python3.12+", "warning")
        needs_update = True

    current_layers = [layer["Arn"] for layer in config.get("Layers", [])]
    if set(current_layers) != set(LAYER_ARNS):
        status_print(f"Layers differ", "warning")
        needs_update = True

    current_env = config.get("Environment", {}).get("Variables", {})
    if current_env != ENV_VARS:
        status_print(f"Environment variables differ", "warning")
        needs_update = True

    vpc_config = config.get("VpcConfig", {})
    current_subnets = set(vpc_config.get("SubnetIds", []))
    current_sgs = set(vpc_config.get("SecurityGroupIds", []))

    if current_subnets != set(VPC_SUBNETS) or current_sgs != set(VPC_SECURITY_GROUPS):
        status_print(f"VPC configuration differs", "warning")
        needs_update = True

    return needs_update


def update_lambda_code(fn_name: str, zip_bytes: bytes):
    """Update Lambda function code"""
    status_print(f"Updating code for {fn_name}", "update")
    return lambda_client.update_function_code(
        FunctionName=fn_name, ZipFile=zip_bytes, Publish=True
    )


def create_lambda(fn_name: str, role_arn: str, zip_bytes: bytes, handler_file: str):
    """Create new Lambda function"""
    status_print(f"Creating new function {fn_name}", "success")
    return lambda_client.create_function(
        FunctionName=fn_name,
        Runtime="python3.12",
        Role=role_arn,
        Handler=f"{handler_file}.lambda_handler",
        Code={"ZipFile": zip_bytes},
        Description=f"Panda function {fn_name}",
        Timeout=TIMEOUT,
        MemorySize=128,
        Publish=True,
        Layers=LAYER_ARNS,
        Environment={"Variables": ENV_VARS},
        VpcConfig={
            "SubnetIds": VPC_SUBNETS,
            "SecurityGroupIds": VPC_SECURITY_GROUPS,
        },
        PackageType="Zip",
    )


def wait_for_function_ready(fn_name: str, max_attempts: int = 30):
    """Wait for Lambda function to be ready for updates"""
    status_print("Checking if function is ready for updates...", "info")
    for attempt in range(max_attempts):
        try:
            config = get_function_config(fn_name)
            if config and config.get("State") == "Active" and config.get("LastUpdateStatus") == "Successful":
                return True
            status_print(
                f"Function not ready, waiting... (attempt {attempt + 1}/{max_attempts})", "info")
            time.sleep(2)
        except Exception as e:
            status_print(f"Error checking function status: {e}", "warning")
            time.sleep(2)
    return False


def update_lambda_config(fn_name: str):
    """Update Lambda function configuration"""
    # Wait for function to be ready
    if not wait_for_function_ready(fn_name):
        status_print(
            "Function not ready for configuration update, skipping...", "warning")
        return

    status_print(f"Updating configuration for {fn_name}", "update")
    # Don't downgrade runtime if it's already a newer version
    config = get_function_config(fn_name)
    current_runtime = config.get("Runtime", "python3.12")
    target_runtime = "python3.12" if current_runtime.startswith(
        "python3.12") else current_runtime

    lambda_client.update_function_configuration(
        FunctionName=fn_name,
        Timeout=TIMEOUT,
        Layers=LAYER_ARNS,
        Environment={"Variables": ENV_VARS},
        VpcConfig={"SubnetIds": VPC_SUBNETS,
                   "SecurityGroupIds": VPC_SECURITY_GROUPS},
        Runtime=target_runtime,
        MemorySize=128,
    )
    status_print("Waiting for function update to complete...", "info")
    waiter = lambda_client.get_waiter("function_updated")
    waiter.wait(FunctionName=fn_name)


def test_invoke(fn_name: str):
    """Test invoke the Lambda function"""
    status_print(f"Testing function {fn_name}", "info")
    try:
        resp = lambda_client.invoke(
            FunctionName=fn_name,
            InvocationType="RequestResponse",
            Payload=json.dumps({"body": "{}"}).encode("utf-8"),
        )
        body = resp["Payload"].read().decode("utf-8")
        status_code = resp.get("StatusCode", 0)
        if status_code == 200:
            status_print(f"Test successful: {body[:100]}...", "success")
        else:
            status_print(
                f"Test returned {status_code}: {body[:100]}...", "warning")
    except Exception as e:
        status_print(f"Test failed: {e}", "error")


def lambda_to_path(filename: str) -> str:
    """Convert filename to API path by removing 'panda' and converting to snake_case"""
    base = os.path.splitext(os.path.basename(filename))[0]
    base = re.sub("panda", "", base, flags=re.IGNORECASE)
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", base)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    return snake.lstrip("_")


def get_root_resource_id(api_id: str) -> str:
    """Get the root resource ID for API Gateway"""
    resources = apigw_client.get_resources(restApiId=api_id)["items"]
    for r in resources:
        if r["path"] == "/":
            return r["id"]
    raise RuntimeError("Root resource not found")


def resource_exists(api_id: str, path_part: str) -> tuple[bool, str]:
    """Check if API Gateway resource exists, return (exists, resource_id)"""
    resources = apigw_client.get_resources(restApiId=api_id)["items"]
    for r in resources:
        if r.get("pathPart") == path_part:
            return True, r["id"]
    return False, ""


def ensure_resource(api_id: str, parent_id: str, path_part: str) -> str:
    """Ensure API Gateway resource exists"""
    exists, resource_id = resource_exists(api_id, path_part)
    if exists:
        status_print(f"Resource /{path_part} already exists", "info")
        return resource_id

    status_print(f"Creating resource /{path_part}", "success")
    resp = apigw_client.create_resource(
        restApiId=api_id, parentId=parent_id, pathPart=path_part
    )
    return resp["id"]


def method_exists(api_id: str, resource_id: str, http_method: str) -> bool:
    """Check if API Gateway method exists"""
    try:
        apigw_client.get_method(
            restApiId=api_id, resourceId=resource_id, httpMethod=http_method
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "NotFoundException":
            return False
        raise


def ensure_method(api_id: str, resource_id: str, http_method: str):
    """Ensure API Gateway method exists"""
    if method_exists(api_id, resource_id, http_method):
        status_print(f"{http_method} method already exists", "info")
        return

    status_print(f"Creating {http_method} method", "success")
    apigw_client.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod=http_method,
        authorizationType=AUTH_TYPE,
        authorizerId=AUTHORIZER_ID,
    )


def integration_exists(api_id: str, resource_id: str, http_method: str) -> bool:
    """Check if API Gateway integration exists"""
    try:
        apigw_client.get_integration(
            restApiId=api_id, resourceId=resource_id, httpMethod=http_method
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "NotFoundException":
            return False
        raise


def ensure_integration(api_id: str, resource_id: str, http_method: str, fn_arn: str):
    """Ensure API Gateway integration exists"""
    if integration_exists(api_id, resource_id, http_method):
        status_print(f"Integration for {http_method} already exists", "info")
        # Could add logic here to check if integration URI is correct
        return

    status_print(f"Creating integration for {http_method}", "success")
    uri = f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{fn_arn}/invocations"
    apigw_client.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod=http_method,
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=uri,
        timeoutInMillis=29000,
    )


def permission_exists(fn_name: str, statement_id: str) -> bool:
    """Check if Lambda permission exists"""
    try:
        policy_response = lambda_client.get_policy(FunctionName=fn_name)
        policy = json.loads(policy_response["Policy"])

        for statement in policy.get("Statement", []):
            if statement.get("Sid") == statement_id:
                return True
        return False
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def ensure_permission_for_apig(fn_name: str, path_part: str, http_method: str):
    """Ensure Lambda permission for API Gateway exists"""
    statement_id = f"apigateway-{http_method.lower()}-{path_part}"

    if permission_exists(fn_name, statement_id):
        status_print(f"API Gateway permission already exists", "info")
        return

    status_print(f"Adding API Gateway permission", "success")
    source_arn = f"arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{REST_API_ID}/*/{http_method}/{path_part}"
    try:
        lambda_client.add_permission(
            FunctionName=fn_name,
            StatementId=statement_id,
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=source_arn,
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceConflictException":
            status_print(
                f"Permission already exists (conflict detected)", "warning")
        else:
            raise


def ensure_options_method(api_id: str, resource_id: str):
    """Ensure OPTIONS method exists for CORS preflight"""
    if method_exists(api_id, resource_id, "OPTIONS"):
        status_print("OPTIONS method already exists", "info")
        return

    status_print("Creating OPTIONS method for CORS", "success")

    # Create OPTIONS method without authorization
    apigw_client.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod="OPTIONS",
        authorizationType="NONE",
    )

    # Create mock integration for OPTIONS
    apigw_client.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod="OPTIONS",
        type="MOCK",
        requestTemplates={
            "application/json": '{"statusCode": 200}'
        }
    )

    # Set up method response for OPTIONS
    apigw_client.put_method_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod="OPTIONS",
        statusCode="200",
        responseParameters={
            "method.response.header.Access-Control-Allow-Headers": False,
            "method.response.header.Access-Control-Allow-Methods": False,
            "method.response.header.Access-Control-Allow-Origin": False,
            "method.response.header.Access-Control-Allow-Credentials": False,
        }
    )

    # Set up integration response for OPTIONS
    apigw_client.put_integration_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod="OPTIONS",
        statusCode="200",
        responseParameters={
            "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
            "method.response.header.Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,OPTIONS'",
            "method.response.header.Access-Control-Allow-Origin": "'https://app.onebor.com'",
            "method.response.header.Access-Control-Allow-Credentials": "'true'",
        },
        responseTemplates={
            "application/json": ""
        }
    )


def deploy_stage(api_id: str, stage_name: str):
    """Deploy API Gateway stage"""
    status_print(f"Deploying API stage {stage_name}", "success")
    apigw_client.create_deployment(restApiId=api_id, stageName=stage_name)


def main():
    if len(sys.argv) != 2:
        print("Usage: python deploy_lambda_improved.py <filename.py>")
        print("Example: python deploy_lambda_improved.py updatePandaEntityType.py")
        sys.exit(1)

    filename = sys.argv[1]
    if not os.path.isfile(filename):
        status_print(f"File '{filename}' not found", "error")
        sys.exit(1)

    if not filename.endswith(".py"):
        status_print(
            f"File '{filename}' must be a Python file (.py extension)", "error")
        sys.exit(1)

    fn_name = os.path.splitext(os.path.basename(filename))[0]
    handler_file = fn_name

    status_print(f"Deploying Lambda function: {fn_name}", "info")
    status_print(f"Source file: {filename}", "info")

    # Prepare deployment package
    zip_bytes = zip_single_py(filename)
    status_print(
        f"Created deployment package ({len(zip_bytes)} bytes)", "info")

    # Get IAM role
    try:
        role_arn = role_arn_from_name(ROLE_NAME)
        status_print(f"Using IAM role: {role_arn}", "info")
    except ClientError as e:
        status_print(f"Could not find IAM role '{ROLE_NAME}': {e}", "error")
        sys.exit(1)

    # Deploy or update Lambda function
    try:
        if function_exists(fn_name):
            status_print(f"Function {fn_name} exists", "info")

            # Always update code
            update_lambda_code(fn_name, zip_bytes)

            # Check if configuration needs updating
            if needs_config_update(fn_name):
                update_lambda_config(fn_name)
            else:
                status_print("Configuration is up to date", "info")
        else:
            create_lambda(fn_name, role_arn, zip_bytes, handler_file)
    except ClientError as e:
        status_print(f"Error deploying Lambda function: {e}", "error")
        sys.exit(1)

    # Get function ARN
    fn_conf = lambda_client.get_function(FunctionName=fn_name)
    fn_arn = fn_conf["Configuration"]["FunctionArn"]

    # Determine API path
    path_part = lambda_to_path(filename)
    if not path_part:
        status_print(
            f"Could not generate valid API path from filename '{filename}'", "error")
        sys.exit(1)

    status_print(f"API path: /{path_part} (POST)", "info")

    # Set up API Gateway
    try:
        root_id = get_root_resource_id(REST_API_ID)
        res_id = ensure_resource(REST_API_ID, root_id, path_part)

        # Set up POST method
        ensure_method(REST_API_ID, res_id, "POST")
        ensure_integration(REST_API_ID, res_id, "POST", fn_arn)
        ensure_permission_for_apig(fn_name, path_part, "POST")

        # Set up OPTIONS method for CORS preflight
        ensure_options_method(REST_API_ID, res_id)

    except ClientError as e:
        status_print(f"Error setting up API Gateway: {e}", "error")
        sys.exit(1)

    # Test function
    test_invoke(fn_name)

    # Deploy API stage
    try:
        deploy_stage(REST_API_ID, STAGE_NAME)
        status_print("Deployment completed successfully", "success")
        endpoint = f"https://{REST_API_ID}.execute-api.{REGION}.amazonaws.com/{STAGE_NAME}/{path_part}"
        status_print(f"API endpoint: {endpoint}", "success")
    except ClientError as e:
        status_print(f"Error deploying API stage: {e}", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
