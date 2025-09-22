#!/usr/bin/env python3
"""
Script to add CORS headers to all onebor Lambda functions
"""

import os
import re
from dotenv import load_dotenv

# Load environment variables from scripts/.env
load_dotenv()

# CORS headers to add
CORS_HEADERS = '''
    # Add CORS headers
    headers = {
        'Access-Control-Allow-Origin': 'https://app.onebor.com',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Credentials': 'true'
    }
    
    # Handle preflight OPTIONS requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
'''


def add_cors_to_lambda(file_path):
    """Add CORS headers to a Lambda function file"""

    with open(file_path, 'r') as f:
        content = f.read()

    # Skip if CORS headers already exist
    if 'Access-Control-Allow-Origin' in content:
        print(f"✅ {file_path} already has CORS headers")
        return False

    # Find the lambda_handler function
    if 'def lambda_handler(event, context):' not in content:
        print(f"⚠️  {file_path} doesn't have lambda_handler function")
        return False

    # Insert CORS headers after the function definition
    pattern = r'(def lambda_handler\(event, context\):\s*\n)'
    replacement = r'\1' + CORS_HEADERS + '\n'

    new_content = re.sub(pattern, replacement, content)

    # Update return statements to include headers
    # Find all return statements with statusCode
    return_pattern = r'return\s*\{\s*["\']statusCode["\']\s*:\s*(\d+)\s*,\s*["\']body["\']\s*:\s*([^}]+)\s*\}'

    def replace_return(match):
        status_code = match.group(1)
        body = match.group(2)
        return f'''return {{
        'statusCode': {status_code},
        'headers': headers,
        'body': {body}
    }}'''

    new_content = re.sub(return_pattern, replace_return, new_content)

    # Write the updated content
    with open(file_path, 'w') as f:
        f.write(new_content)

    print(f"✅ Updated {file_path} with CORS headers")
    return True


def main():
    """Main function to update all Lambda functions"""

    database_dir = "database"

    if not os.path.exists(database_dir):
        print(f"❌ {database_dir} directory not found")
        return

    updated_files = []

    # Find all Python files in the database directory
    for filename in os.listdir(database_dir):
        if filename.endswith('.py') and filename.startswith('get') or filename.startswith('update') or filename.startswith('manage') or filename.startswith('modify'):
            file_path = os.path.join(database_dir, filename)

            if add_cors_to_lambda(file_path):
                updated_files.append(filename)

    print(f"\n📝 Summary:")
    print(f"Updated {len(updated_files)} files:")
    for filename in updated_files:
        print(f"  - {filename}")

    if updated_files:
        print(f"\n🚀 Next steps:")
        print(f"1. Review the changes in the updated files")
        print(f"2. Deploy the Lambda functions using deploy_lambda.py")
        print(f"3. Test the API endpoints")


if __name__ == "__main__":
    main()
