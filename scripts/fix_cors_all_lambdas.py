#!/usr/bin/env python3
"""
Script to fix CORS headers in all Lambda functions
"""

import os
import glob

# CORS headers definition
CORS_HEADERS_DEF = '''    # CORS headers for all responses
    cors_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "https://app.onebor.com",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Credentials": "true"
    }
    
    # Handle preflight OPTIONS requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": ""
        }
    '''

def fix_lambda_cors(file_path):
    """Fix CORS headers in a Lambda function"""
    
    print(f"📝 Processing {file_path}...")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Skip if CORS headers already exist
    if 'Access-Control-Allow-Origin' in content:
        print(f"✅ {file_path} already has CORS headers")
        return False
    
    # Find lambda_handler function and add CORS headers
    if 'def lambda_handler(event, context):' in content:
        # Add CORS headers after function definition
        old_pattern = 'def lambda_handler(event, context):\n    conn = None\n    try:'
        new_pattern = f'def lambda_handler(event, context):\n{CORS_HEADERS_DEF}\n    conn = None\n    try:'
        
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
        else:
            # Try alternative pattern
            old_pattern = 'def lambda_handler(event, context):\n    try:'
            new_pattern = f'def lambda_handler(event, context):\n{CORS_HEADERS_DEF}\n    try:'
            content = content.replace(old_pattern, new_pattern)
    
    # Replace all headers with cors_headers
    content = content.replace('"headers": {"Content-Type": "application/json"}', '"headers": cors_headers')
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {file_path}")
    return True

def main():
    """Fix CORS in all Lambda functions"""
    
    database_dir = "database"
    lambda_files = glob.glob(f"{database_dir}/*.py")
    
    updated_count = 0
    
    for file_path in lambda_files:
        if os.path.basename(file_path).startswith(('get', 'update', 'manage', 'modify')):
            if fix_lambda_cors(file_path):
                updated_count += 1
    
    print(f"\n📊 Summary: Updated {updated_count} Lambda functions")
    print(f"🚀 Next step: Deploy with python3 scripts/deploy_lambda.py")

if __name__ == "__main__":
    main()
