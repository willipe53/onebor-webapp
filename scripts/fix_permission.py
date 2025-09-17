#!/usr/bin/env python3
"""
Quick fix script to add missing API Gateway permission to updatePandaUser
"""
import boto3
from botocore.exceptions import ClientError

REGION = "us-east-2"
ACCOUNT_ID = "316490106381"
REST_API_ID = "zwkvk3lyl3"

lambda_client = boto3.client("lambda", region_name=REGION)


def add_permission():
    fn_name = "updatePandaUser"
    path_part = "update_user"
    statement_id = f"apigateway-post-{path_part}"
    source_arn = f"arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{REST_API_ID}/*/POST/{path_part}"

    try:
        lambda_client.add_permission(
            FunctionName=fn_name,
            StatementId=statement_id,
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=source_arn,
        )
        print(f"✅ Added permission for API Gateway to invoke {fn_name}")
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceConflictException":
            print(f"✅ Permission already exists for {fn_name}")
            return True
        else:
            print(f"❌ Error adding permission: {e}")
            return False


if __name__ == "__main__":
    add_permission()
