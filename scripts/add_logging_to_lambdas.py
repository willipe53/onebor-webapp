#!/usr/bin/env python3
"""
Script to automatically add standardized request/response logging to all Lambda functions.
This will add the log_request_response function and calls to it before each return statement.
"""

import os
import re
from pathlib import Path

# Standardized logging function to add to each Lambda
LOGGING_FUNCTION = '''
def log_request_response(event, response_body, lambda_name):
    """Log request and response data in a format that can be parsed for OpenAPI generation."""
    try:
        # Log request data
        if 'body' in event:
            request_body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            print(f"REQUEST_BODY: {json.dumps(request_body)}")
        
        # Log response data
        if response_body:
            print(f"RESPONSE_BODY: {json.dumps(response_body)}")
            
    except Exception as e:
        print(f"ERROR logging request/response: {str(e)}")
'''


def add_logging_function(file_path):
    """Add the logging function to a Lambda file."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Check if logging function already exists
    if 'def log_request_response(' in content:
        print(f"  ⚠️  Logging function already exists in {file_path}")
        return False

    # Find where to insert the logging function (after get_db_connection or similar)
    insert_patterns = [
        r'(def get_db_connection\(\):.*?return pymysql\.connect\([^}]+}\))',
        r'(def get_db_secret\(\):.*?return json\.loads\([^}]+}\))',
        r'(def lambda_handler\(event, context\):)',
    ]

    insert_position = None
    for pattern in insert_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            insert_position = match.end()
            break

    if not insert_position:
        print(f"  ❌ Could not find insertion point in {file_path}")
        return False

    # Insert the logging function
    new_content = content[:insert_position] + \
        LOGGING_FUNCTION + content[insert_position:]

    with open(file_path, 'w') as f:
        f.write(new_content)

    print(f"  ✅ Added logging function to {file_path}")
    return True


def add_logging_calls(file_path):
    """Add logging calls before return statements."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Pattern to match return statements with JSON responses
    return_pattern = r'return\s*\{\s*"statusCode":\s*(\d+),\s*"headers":\s*cors_headers,\s*"body":\s*json\.dumps\(([^)]+)\)\s*\}'

    def replace_return(match):
        status_code = match.group(1)
        response_body = match.group(2)

        # Create the logging call
        logging_call = f'''response_body = {response_body}
        log_request_response(event, response_body, "{Path(file_path).stem}")
        return {{
            "statusCode": {status_code},
            "headers": cors_headers,
            "body": json.dumps(response_body)
        }}'''

        return logging_call

    # Replace return statements
    new_content = re.sub(return_pattern, replace_return,
                         content, flags=re.MULTILINE | re.DOTALL)

    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"  ✅ Added logging calls to {file_path}")
        return True
    else:
        print(f"  ⚠️  No return statements found to modify in {file_path}")
        return False


def process_lambda_file(file_path):
    """Process a single Lambda file to add logging."""
    print(f"📝 Processing {file_path}")

    success1 = add_logging_function(file_path)
    success2 = add_logging_calls(file_path)

    return success1 or success2


def main():
    """Main function to process all Lambda files."""
    database_dir = Path("database")

    if not database_dir.exists():
        print("❌ Database directory not found")
        return

    # Get all Python files in database directory
    lambda_files = list(database_dir.glob("*.py"))

    if not lambda_files:
        print("❌ No Python files found in database directory")
        return

    print(f"🚀 Found {len(lambda_files)} Lambda files to process")
    print()

    processed_count = 0
    for file_path in lambda_files:
        if process_lambda_file(file_path):
            processed_count += 1
        print()

    print(
        f"✅ Successfully processed {processed_count}/{len(lambda_files)} Lambda files")
    print()
    print("📋 Next steps:")
    print("1. Deploy the updated Lambda functions")
    print("2. Use your app to generate API calls")
    print("3. Run the log analysis script to generate OpenAPI spec")


if __name__ == "__main__":
    main()
