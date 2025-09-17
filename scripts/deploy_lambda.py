#!/usr/bin/env python3
"""
Deploy Lambda script for creating AWS Lambda functions and API Gateway endpoints.
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

REGION = "us-east-2"
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


def role_arn_from_name(role_name: str) -> str:
    # Try the exact role name first
    try:
        resp = iam_client.get_role(RoleName=role_name)
        return resp["Role"]["Arn"]
    except ClientError:
        # Try with service-role prefix
        try:
            service_role_name = f"service-role/{role_name}"
            resp = iam_client.get_role(RoleName=service_role_name)
            return resp["Role"]["Arn"]
        except ClientError:
            # Original error is more informative
            resp = iam_client.get_role(RoleName=role_name)
            return resp["Role"]["Arn"]


def zip_single_py(filepath: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(filepath, arcname=os.path.basename(filepath))
    return buf.getvalue()


def function_exists(fn_name: str) -> bool:
    try:
        lambda_client.get_function(FunctionName=fn_name)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def update_lambda_code(fn_name: str, zip_bytes: bytes):
    return lambda_client.update_function_code(
        FunctionName=fn_name, ZipFile=zip_bytes, Publish=True
    )


def create_lambda(fn_name: str, role_arn: str, zip_bytes: bytes, handler_file: str):
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


def update_lambda_config(fn_name: str):
    lambda_client.update_function_configuration(
        FunctionName=fn_name,
        Timeout=TIMEOUT,
        Layers=LAYER_ARNS,
        Environment={"Variables": ENV_VARS},
        VpcConfig={"SubnetIds": VPC_SUBNETS,
                   "SecurityGroupIds": VPC_SECURITY_GROUPS},
        Runtime="python3.12",
        MemorySize=128,
    )
    waiter = lambda_client.get_waiter("function_updated")
    waiter.wait(FunctionName=fn_name)


def test_invoke(fn_name: str):
    resp = lambda_client.invoke(
        FunctionName=fn_name,
        InvocationType="RequestResponse",
        Payload=json.dumps({"body": "{}"}).encode("utf-8"),
    )
    body = resp["Payload"].read().decode("utf-8")
    print(f"[test] {fn_name} -> {resp.get('StatusCode')} {body[:200]}")


def lambda_to_path(filename: str) -> str:
    """Convert filename to API path by removing 'panda' and converting to snake_case."""
    base = os.path.splitext(os.path.basename(filename))[0]
    # Remove 'panda' from anywhere in the filename (case insensitive)
    base = re.sub("panda", "", base, flags=re.IGNORECASE)
    # Convert CamelCase to snake_case
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", base)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    # Remove leading underscores
    return snake.lstrip("_")


def get_root_resource_id(api_id: str) -> str:
    resources = apigw_client.get_resources(restApiId=api_id)["items"]
    for r in resources:
        if r["path"] == "/":
            return r["id"]
    raise RuntimeError("Root resource not found")


def ensure_resource(api_id: str, parent_id: str, path_part: str) -> str:
    resources = apigw_client.get_resources(restApiId=api_id)["items"]
    for r in resources:
        if r.get("pathPart") == path_part:
            return r["id"]
    resp = apigw_client.create_resource(
        restApiId=api_id, parentId=parent_id, pathPart=path_part
    )
    return resp["id"]


def ensure_method(api_id: str, resource_id: str, http_method: str):
    try:
        apigw_client.get_method(
            restApiId=api_id, resourceId=resource_id, httpMethod=http_method
        )
        return
    except ClientError as e:
        if e.response["Error"]["Code"] != "NotFoundException":
            raise
    apigw_client.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod=http_method,
        authorizationType=AUTH_TYPE,
        authorizerId=AUTHORIZER_ID,
    )


def ensure_integration(api_id: str, resource_id: str, http_method: str, fn_arn: str):
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


def ensure_permission_for_apig(fn_name: str, path_part: str, http_method: str):
    statement_id = f"apigateway-{http_method.lower()}-{path_part}"
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
            return
        raise


def deploy_stage(api_id: str, stage_name: str):
    apigw_client.create_deployment(restApiId=api_id, stageName=stage_name)


def main():
    if len(sys.argv) != 2:
        print("Usage: python deploy_lambda.py <filename.py>")
        print("Example: python deploy_lambda.py pandaGetEntities.py")
        sys.exit(1)

    filename = sys.argv[1]
    if not os.path.isfile(filename):
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)

    if not filename.endswith('.py'):
        print(
            f"Error: File '{filename}' must be a Python file (.py extension).")
        sys.exit(1)

    fn_name = os.path.splitext(os.path.basename(filename))[0]
    handler_file = fn_name
    zip_bytes = zip_single_py(filename)

    try:
        role_arn = role_arn_from_name(ROLE_NAME)
    except ClientError as e:
        print(f"Error: Could not find IAM role '{ROLE_NAME}': {e}")
        sys.exit(1)

    try:
        if function_exists(fn_name):
            print(f"= Updating Lambda {fn_name}")
            update_lambda_code(fn_name, zip_bytes)
            update_lambda_config(fn_name)
        else:
            print(f"+ Creating Lambda {fn_name}")
            create_lambda(fn_name, role_arn, zip_bytes, handler_file)
    except ClientError as e:
        print(f"Error deploying Lambda function: {e}")
        sys.exit(1)

    fn_conf = lambda_client.get_function(FunctionName=fn_name)
    fn_arn = fn_conf["Configuration"]["FunctionArn"]

    path_part = lambda_to_path(filename)
    if not path_part:
        print(
            f"Error: Could not generate valid API path from filename '{filename}'")
        sys.exit(1)

    print(f"-> API path /{path_part} (POST) for {fn_name}")

    try:
        root_id = get_root_resource_id(REST_API_ID)
        res_id = ensure_resource(REST_API_ID, root_id, path_part)
        ensure_method(REST_API_ID, res_id, "POST")
        ensure_integration(REST_API_ID, res_id, "POST", fn_arn)
        ensure_permission_for_apig(fn_name, path_part, "POST")
    except ClientError as e:
        print(f"Error setting up API Gateway: {e}")
        sys.exit(1)

    try:
        test_invoke(fn_name)
    except Exception as e:
        print(f"Warning: Test invocation failed: {e}")

    try:
        print(f"# Deploying API {REST_API_ID} stage {STAGE_NAME}")
        deploy_stage(REST_API_ID, STAGE_NAME)
        print("Done.")
        print(
            f"API endpoint: https://{REST_API_ID}.execute-api.{REGION}.amazonaws.com/{STAGE_NAME}/{path_part}")
    except ClientError as e:
        print(f"Error deploying API stage: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
