#!/usr/bin/env python3
"""
Script to set up SQS trigger for the position keeper Lambda function.
This will automatically invoke the position keeper when messages arrive in the SQS queue.
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
QUEUE_URL = "https://sqs.us-east-2.amazonaws.com/316490106381/pandatransactions.fifo"
QUEUE_ARN = f"arn:aws:sqs:{REGION}:{ACCOUNT_ID}:pandatransactions.fifo"
FUNCTION_ARN = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{FUNCTION_NAME}"

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

def get_sqs_client():
    """Get SQS client."""
    return boto3.client('sqs', region_name=REGION)

def add_sqs_permission():
    """Add permission for SQS to invoke the Lambda function."""
    lambda_client = get_lambda_client()
    
    try:
        # Check if permission already exists
        try:
            lambda_client.get_policy(FunctionName=FUNCTION_NAME)
            status_print(f"Permission already exists for {FUNCTION_NAME}", "info")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Permission doesn't exist, create it
                pass
            else:
                raise
        
        # Add permission for SQS to invoke Lambda
        lambda_client.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId=f"sqs-trigger-{FUNCTION_NAME}",
            Action="lambda:InvokeFunction",
            Principal="sqs.amazonaws.com",
            SourceArn=QUEUE_ARN
        )
        status_print(f"Added SQS permission for {FUNCTION_NAME}", "success")
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            status_print(f"Permission already exists for {FUNCTION_NAME}", "warning")
            return True
        else:
            status_print(f"Error adding permission: {str(e)}", "error")
            return False

def create_event_source_mapping():
    """Create event source mapping between SQS and Lambda."""
    lambda_client = get_lambda_client()
    
    try:
        # Check if event source mapping already exists
        response = lambda_client.list_event_source_mappings(
            FunctionName=FUNCTION_NAME,
            EventSourceArn=QUEUE_ARN
        )
        
        if response['EventSourceMappings']:
            status_print(f"Event source mapping already exists for {FUNCTION_NAME}", "info")
            return True
        
        # Create event source mapping (FIFO queues don't support batching window)
        response = lambda_client.create_event_source_mapping(
            EventSourceArn=QUEUE_ARN,
            FunctionName=FUNCTION_NAME,
            Enabled=True,
            BatchSize=10,  # Process up to 10 messages at a time
            FunctionResponseTypes=['ReportBatchItemFailures']
        )
        
        mapping_id = response['UUID']
        status_print(f"Created event source mapping {mapping_id} for {FUNCTION_NAME}", "success")
        return True
        
    except ClientError as e:
        status_print(f"Error creating event source mapping: {str(e)}", "error")
        return False

def get_queue_attributes():
    """Get SQS queue attributes to verify setup."""
    sqs_client = get_sqs_client()
    
    try:
        response = sqs_client.get_queue_attributes(
            QueueUrl=QUEUE_URL,
            AttributeNames=['All']
        )
        
        attributes = response['Attributes']
        status_print(f"Queue attributes retrieved:", "info")
        print(f"  - Queue Name: {attributes.get('QueueArn', '').split(':')[-1]}")
        print(f"  - Messages Available: {attributes.get('ApproximateNumberOfMessages', '0')}")
        print(f"  - Messages In Flight: {attributes.get('ApproximateNumberOfMessagesNotVisible', '0')}")
        print(f"  - Visibility Timeout: {attributes.get('VisibilityTimeoutSeconds', 'N/A')}")
        
        return True
        
    except ClientError as e:
        status_print(f"Error getting queue attributes: {str(e)}", "error")
        return False

def test_function():
    """Test the Lambda function."""
    lambda_client = get_lambda_client()
    
    try:
        response = lambda_client.invoke(
            FunctionName=FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps({"test": "trigger_setup"})
        )
        
        status_code = response['StatusCode']
        if status_code == 200:
            payload = json.loads(response['Payload'].read())
            status_print(f"Function test successful: {payload.get('body', 'No response body')}", "success")
            return True
        else:
            status_print(f"Function test failed with status {status_code}", "error")
            return False
            
    except ClientError as e:
        status_print(f"Error testing function: {str(e)}", "error")
        return False

def main():
    """Main setup function."""
    status_print("Setting up SQS trigger for position keeper", "info")
    status_print(f"Function: {FUNCTION_NAME}", "info")
    status_print(f"Queue: {QUEUE_URL}", "info")
    
    # Step 1: Add SQS permission
    status_print("Step 1: Adding SQS permission to Lambda function...", "info")
    if not add_sqs_permission():
        status_print("Failed to add SQS permission", "error")
        return False
    
    # Step 2: Create event source mapping
    status_print("Step 2: Creating event source mapping...", "info")
    if not create_event_source_mapping():
        status_print("Failed to create event source mapping", "error")
        return False
    
    # Step 3: Verify queue attributes
    status_print("Step 3: Verifying queue setup...", "info")
    if not get_queue_attributes():
        status_print("Failed to verify queue attributes", "warning")
    
    # Step 4: Test function
    status_print("Step 4: Testing Lambda function...", "info")
    if not test_function():
        status_print("Function test failed", "warning")
    
    status_print("SQS trigger setup completed!", "success")
    status_print("The position keeper will now automatically process messages from the SQS queue", "info")
    
    return True

if __name__ == "__main__":
    main()
