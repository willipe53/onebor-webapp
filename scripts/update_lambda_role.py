#!/usr/bin/env python3
"""
Script to update the Lambda execution role to include SQS permissions.
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
FUNCTION_NAME = "positionKeeper"
ROLE_NAME = "getPandaEntityTypes-role-cpdc7xv7"
QUEUE_ARN = f"arn:aws:sqs:{REGION}:{ACCOUNT_ID}:pandatransactions.fifo"

def status_print(message, level="info"):
    """Print status message with appropriate formatting."""
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    print(f"{icons.get(level, 'ℹ️')} {message}")

def get_iam_client():
    """Get IAM client."""
    return boto3.client('iam', region_name=REGION)

def get_lambda_client():
    """Get Lambda client."""
    return boto3.client('lambda', region_name=REGION)

def get_role_arn():
    """Get the role ARN for the Lambda function."""
    lambda_client = get_lambda_client()
    
    try:
        response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
        role_arn = response['Configuration']['Role']
        return role_arn
    except ClientError as e:
        status_print(f"Error getting function role: {str(e)}", "error")
        return None

def create_sqs_policy():
    """Create SQS policy document."""
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes"
                ],
                "Resource": QUEUE_ARN
            }
        ]
    }
    return json.dumps(policy_document)

def attach_sqs_policy():
    """Attach SQS policy to the Lambda execution role."""
    iam_client = get_iam_client()
    
    # Get role ARN
    role_arn = get_role_arn()
    if not role_arn:
        return False
    
    role_name = role_arn.split('/')[-1]
    policy_name = f"{FUNCTION_NAME}-sqs-policy"
    
    try:
        # Check if policy already exists
        try:
            iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            status_print(f"SQS policy already exists for role {role_name}", "info")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchEntity':
                raise
        
        # Create and attach policy
        policy_document = create_sqs_policy()
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=policy_document
        )
        
        status_print(f"Attached SQS policy to role {role_name}", "success")
        return True
        
    except ClientError as e:
        status_print(f"Error attaching SQS policy: {str(e)}", "error")
        return False

def main():
    """Main function to update Lambda role."""
    status_print("Updating Lambda execution role for SQS permissions", "info")
    status_print(f"Function: {FUNCTION_NAME}", "info")
    status_print(f"Queue: {QUEUE_ARN}", "info")
    
    if attach_sqs_policy():
        status_print("Lambda role updated successfully!", "success")
        status_print("You can now retry the SQS trigger setup", "info")
        return True
    else:
        status_print("Failed to update Lambda role", "error")
        return False

if __name__ == "__main__":
    main()
