#!/usr/bin/env python3
"""
Comprehensive fix for all Lambda functions with logging issues.
"""

import os
import re
import subprocess
import zipfile


def fix_lambda_file(file_path):
    """Fix syntax issues in a Lambda function file."""
    function_name = os.path.basename(file_path).replace('.py', '')
    print(f"Fixing {function_name}...")

    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    # Fix 1: Fix the main indentation issue
    # Pattern: def lambda_handler(event, context):\n    def log_request_response(event, response_body, lambda_name):\n    """Log request...
    pattern1 = r'(def lambda_handler\(event, context\):\n)(    def log_request_response\(event, response_body, lambda_name\):\n)(    """Log request and response data in a format that can be parsed for OpenAPI generation\.\."""\n)(        # Log the incoming request\n)(    log_request_response\(event, None, "[^"]+"\)\n)(\n)(    try:\n)(        # Log request data\n)(        if \'body\' in event:\n)(            request_body = json\.loads\(event\[\'body\'\]\) if isinstance\(event\[\'body\'\], str\) else event\[\'body\'\]\n)(            print\(f"REQUEST_BODY: \{json\.dumps\(request_body\)\}"\)\n)(        \n)(        # Log response data\n)(        if response_body:\n)(            print\(f"RESPONSE_BODY: \{json\.dumps\(response_body\)\}"\)\n)(            \n)(    except Exception as e:\n)(        print\(f"ERROR logging request/response: \{str\(e\)\}"\)\n)'

    replacement1 = r'\1    def log_request_response(event, response_body, lambda_name):\n        """Log request and response data in a format that can be parsed for OpenAPI generation."""\n        try:\n            # Log request data\n            if \'body\' in event:\n                request_body = json.loads(event[\'body\']) if isinstance(event[\'body\'], str) else event[\'body\']\n                print(f"REQUEST_BODY: {json.dumps(request_body)}")\n            \n            # Log response data\n            if response_body:\n                print(f"RESPONSE_BODY: {json.dumps(response_body)}")\n                \n        except Exception as e:\n            print(f"ERROR logging request/response: {str(e)}")\n\n    # Log the incoming request\n    log_request_response(event, None, "' + function_name + r'")\n\n    '

    content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)

    # Fix 2: Handle cases where the pattern might be slightly different
    # Look for any remaining improper indentation
    pattern2 = r'(def lambda_handler\(event, context\):\n)(def log_request_response\(event, response_body, lambda_name\):)'
    if re.search(pattern2, content):
        content = re.sub(
            pattern2, r'\1    def log_request_response(event, response_body, lambda_name):', content)

    # Write the fixed content back if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ Fixed {function_name}")
        return True
    else:
        print(f"  ✅ No issues found in {function_name}")
        return False


def deploy_lambda(function_name, file_path):
    """Deploy a Lambda function to AWS."""
    print(f"  Deploying {function_name}...")

    # Create zip file
    zip_path = f"{function_name}.zip"
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        zip_file.write(file_path, os.path.basename(file_path))

    # Deploy to AWS
    try:
        result = subprocess.run([
            'aws', 'lambda', 'update-function-code',
            '--function-name', function_name,
            '--zip-file', f'fileb://{zip_path}'
        ], capture_output=True, text=True, check=True)
        print(f"  ✅ Successfully deployed {function_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to deploy {function_name}: {e.stderr}")
        return False
    finally:
        # Clean up zip file
        if os.path.exists(zip_path):
            os.remove(zip_path)


def main():
    """Fix and deploy all Lambda function files."""
    database_dir = "database"
    fixed_count = 0
    deployed_count = 0

    # List of Lambda functions that need fixing
    lambda_functions = [
        'getPandaTransactionStatuses',
        'getPandaTransactionTypes',
        'updatePandaEntity',
        'updatePandaUser',
        'updatePandaPositions',
        'updatePandaTransaction',
        'updatePandaTransactionType',
        'updatePandaEntityType',
        'updatePandaClientGroup',
        'deletePandaRecord',
        'modifyPandaClientGroupMembership',
        'modifyPandaClientGroupEntities'
    ]

    for function_name in lambda_functions:
        file_path = os.path.join(database_dir, f"{function_name}.py")
        if os.path.exists(file_path):
            if fix_lambda_file(file_path):
                fixed_count += 1
                if deploy_lambda(function_name, file_path):
                    deployed_count += 1
        else:
            print(f"⚠️  File not found: {file_path}")

    print(f"\n📊 Summary:")
    print(f"   Fixed: {fixed_count} files")
    print(f"   Deployed: {deployed_count} files")


if __name__ == "__main__":
    main()
