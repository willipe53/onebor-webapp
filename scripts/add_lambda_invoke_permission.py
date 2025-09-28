#!/usr/bin/env python3
"""
Script to add Lambda invoke permission to updatePandaTransaction so it can invoke positionKeeper.
"""

import os
import boto3
import json
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

REGION = os.getenv("REGION", "us-east-2")
ACCOUNT_ID = "316490106381"

# Configuration
SOURCE_FUNCTION_NAME = "updatePandaTransaction"
TARGET_FUNCTION_NAME = "positionKeeper"
ROLE_NAME = "getPandaEntityTypes-role-cpdc7xv7"


def status_print(message, level="info"):
    """Print status message with appropriate formatting."""
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    print(f"{icons.get(level, 'ℹ️')} {message}")


def get_lambda_client():
    """Get Lambda client."""
    return boto3.client('lambda', region_name=REGION)


def get_iam_client():
    """Get IAM client."""
    return boto3.client('iam', region_name=REGION)


def add_lambda_invoke_policy():
    """Add Lambda invoke policy to the execution role."""
    iam_client = get_iam_client()

    policy_name = f"{SOURCE_FUNCTION_NAME}-invoke-{TARGET_FUNCTION_NAME}"

    # Create policy document
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{TARGET_FUNCTION_NAME}"
            }
        ]
    }

    try:
        # Check if policy already exists
        try:
            iam_client.get_role_policy(
                RoleName=ROLE_NAME, PolicyName=policy_name)
            status_print(
                f"Lambda invoke policy already exists for role {ROLE_NAME}", "info")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchEntity':
                raise

        # Create and attach policy
        iam_client.put_role_policy(
            RoleName=ROLE_NAME,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )

        status_print(
            f"Added Lambda invoke policy to role {ROLE_NAME}", "success")
        return True

    except ClientError as e:
        status_print(f"Error adding Lambda invoke policy: {str(e)}", "error")
        return False


def main():
    """Main function to add Lambda invoke permission."""
    status_print(
        "Adding Lambda invoke permission to updatePandaTransaction", "info")
    status_print(f"Source: {SOURCE_FUNCTION_NAME}", "info")
    status_print(f"Target: {TARGET_FUNCTION_NAME}", "info")

    if add_lambda_invoke_policy():
        status_print("Lambda invoke permission added successfully!", "success")
        status_print(
            "updatePandaTransaction can now invoke positionKeeper", "info")
        return True
    else:
        status_print("Failed to add Lambda invoke permission", "error")
        return False


if __name__ == "__main__":
    main()
