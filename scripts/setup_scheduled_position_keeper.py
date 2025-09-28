#!/usr/bin/env python3
"""
Script to set up a scheduled position keeper using EventBridge (CloudWatch Events).
This is much more cost-effective than continuous SQS polling.
"""

import boto3
import json
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

REGION = os.getenv("REGION", "us-east-2")
ACCOUNT_ID = "316490106381"

# Configuration
FUNCTION_NAME = "positionKeeper"
RULE_NAME = f"{FUNCTION_NAME}-scheduled-rule"


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


def get_events_client():
    """Get EventBridge (CloudWatch Events) client."""
    return boto3.client('events', region_name=REGION)


def create_scheduled_rule():
    """Create a scheduled rule to trigger the position keeper."""
    events_client = get_events_client()

    try:
        # Check if rule already exists
        try:
            events_client.describe_rule(Name=RULE_NAME)
            status_print(f"Rule {RULE_NAME} already exists", "info")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise

        # Create rule - run every 5 minutes
        response = events_client.put_rule(
            Name=RULE_NAME,
            Description="Scheduled trigger for position keeper",
            ScheduleExpression="rate(5 minutes)",  # Run every 5 minutes
            State="ENABLED"
        )

        rule_arn = response['RuleArn']
        status_print(f"Created scheduled rule: {rule_arn}", "success")
        return True

    except ClientError as e:
        status_print(f"Error creating rule: {str(e)}", "error")
        return False


def add_lambda_permission():
    """Add permission for EventBridge to invoke the Lambda function."""
    lambda_client = get_lambda_client()

    try:
        # Check if permission already exists
        try:
            lambda_client.get_policy(FunctionName=FUNCTION_NAME)
            status_print(
                f"Permission already exists for {FUNCTION_NAME}", "info")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Permission doesn't exist, create it
                pass
            else:
                raise

        # Add permission for EventBridge to invoke Lambda
        lambda_client.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId=f"scheduled-rule-{FUNCTION_NAME}",
            Action="lambda:InvokeFunction",
            Principal="events.amazonaws.com",
            SourceArn=f"arn:aws:events:{REGION}:{ACCOUNT_ID}:rule/{RULE_NAME}"
        )
        status_print(
            f"Added EventBridge permission for {FUNCTION_NAME}", "success")
        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            status_print(
                f"Permission already exists for {FUNCTION_NAME}", "warning")
            return True
        else:
            status_print(f"Error adding permission: {str(e)}", "error")
            return False


def add_lambda_target():
    """Add Lambda function as target for the EventBridge rule."""
    events_client = get_events_client()

    try:
        # Check if target already exists
        response = events_client.list_targets_by_rule(Rule=RULE_NAME)
        if response['Targets']:
            status_print(f"Target already exists for rule {RULE_NAME}", "info")
            return True

        # Add Lambda as target
        target_id = f"{FUNCTION_NAME}-target"
        events_client.put_targets(
            Rule=RULE_NAME,
            Targets=[
                {
                    'Id': target_id,
                    'Arn': f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{FUNCTION_NAME}",
                    'Input': json.dumps({"source": "scheduled_rule"})
                }
            ]
        )

        status_print(f"Added Lambda target to rule {RULE_NAME}", "success")
        return True

    except ClientError as e:
        status_print(f"Error adding target: {str(e)}", "error")
        return False


def remove_sqs_trigger():
    """Remove the existing SQS trigger to avoid conflicts."""
    lambda_client = get_lambda_client()

    try:
        # List existing event source mappings
        response = lambda_client.list_event_source_mappings(
            FunctionName=FUNCTION_NAME
        )

        mappings = response['EventSourceMappings']
        if not mappings:
            status_print("No SQS triggers found to remove", "info")
            return True

        # Delete each mapping
        for mapping in mappings:
            mapping_id = mapping['UUID']
            lambda_client.delete_event_source_mapping(UUID=mapping_id)
            status_print(f"Removed SQS trigger: {mapping_id}", "success")

        return True

    except ClientError as e:
        status_print(f"Error removing SQS triggers: {str(e)}", "error")
        return False


def main():
    """Main setup function for scheduled position keeper."""
    status_print(
        "Setting up scheduled position keeper (cost-effective solution)", "info")
    status_print(f"Function: {FUNCTION_NAME}", "info")
    status_print(f"Schedule: Every 5 minutes", "info")

    # Step 1: Remove SQS trigger
    status_print("Step 1: Removing existing SQS trigger...", "info")
    remove_sqs_trigger()

    # Step 2: Create scheduled rule
    status_print("Step 2: Creating scheduled rule...", "info")
    if not create_scheduled_rule():
        status_print("Failed to create scheduled rule", "error")
        return False

    # Step 3: Add Lambda permission
    status_print("Step 3: Adding EventBridge permission...", "info")
    if not add_lambda_permission():
        status_print("Failed to add permission", "error")
        return False

    # Step 4: Add Lambda target
    status_print("Step 4: Adding Lambda target...", "info")
    if not add_lambda_target():
        status_print("Failed to add target", "error")
        return False

    status_print("Scheduled position keeper setup completed!", "success")
    status_print(
        "The position keeper will now run every 5 minutes and process any queued messages", "info")
    status_print(
        "This is much more cost-effective than continuous polling", "success")

    return True


if __name__ == "__main__":
    main()
