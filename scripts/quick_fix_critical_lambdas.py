#!/usr/bin/env python3
"""
Quick fix for the most critical Lambda functions causing 502 errors.
"""

import os
import re
import subprocess
import zipfile


def quick_fix_lambda(file_path):
    """Quick fix for a Lambda function by removing the problematic logging code."""
    function_name = os.path.basename(file_path).replace('.py', '')
    print(f"Quick fixing {function_name}...")

    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    # Remove the problematic logging function and call
    # This is a temporary fix to get the APIs working again

    # Pattern 1: Remove the entire log_request_response function definition and call
    pattern1 = r'    def log_request_response\(event, response_body, lambda_name\):\n    """Log request and response data in a format that can be parsed for OpenAPI generation\.\."""\n        # Log the incoming request\n    log_request_response\(event, None, "[^"]+"\)\n\n    try:\n        # Log request data\n        if \'body\' in event:\n            request_body = json\.loads\(event\[\'body\'\]\) if isinstance\(event\[\'body\'\], str\) else event\[\'body\'\]\n            print\(f"REQUEST_BODY: \{json\.dumps\(request_body\)\}"\)\n        \n        # Log response data\n        if response_body:\n            print\(f"RESPONSE_BODY: \{json\.dumps\(response_body\)\}"\)\n            \n    except Exception as e:\n        print\(f"ERROR logging request/response: \{str\(e\)\}"\)\n\n    '

    content = re.sub(pattern1, '', content, flags=re.DOTALL)

    # Pattern 2: Remove any remaining improper indentation
    pattern2 = r'def log_request_response\(event, response_body, lambda_name\):\n    """Log request and response data'
    if re.search(pattern2, content):
        # Find the start and end of the problematic section and remove it
        start = content.find(
            'def log_request_response(event, response_body, lambda_name):')
        if start != -1:
            # Find the end of the function (look for the next function or significant indentation change)
            lines = content[start:].split('\n')
            end_line = 0
            for i, line in enumerate(lines[1:], 1):  # Skip the first line
                if line.strip() and not line.startswith('    ') and not line.startswith('\t'):
                    end_line = i
                    break
            if end_line > 0:
                end = start + len('\n'.join(lines[:end_line]))
                content = content[:start] + content[end:]

    # Write the fixed content back if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ Quick fixed {function_name}")
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
    """Quick fix the most critical Lambda functions."""

    database_dir = "database"
    fixed_count = 0
    deployed_count = 0

    # Most critical Lambda functions that are likely causing 502 errors
    critical_functions = [
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

    for function_name in critical_functions:
        file_path = os.path.join(database_dir, f"{function_name}.py")
        if os.path.exists(file_path):
            if quick_fix_lambda(file_path):
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
