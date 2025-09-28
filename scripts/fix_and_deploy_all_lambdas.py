#!/usr/bin/env python3
"""
Fix and deploy all Lambda functions with syntax issues.
"""

import os
import re
import subprocess
import zipfile


def fix_lambda_file(file_path):
    """Fix syntax issues in a Lambda function file."""
    print(f"Fixing {file_path}...")

    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    # Fix 1: Ensure log_request_response function is properly indented
    pattern1 = r'(def lambda_handler\(event, context\):\n)def log_request_response\(event, response_body, lambda_name\):'
    if re.search(pattern1, content):
        content = re.sub(
            pattern1,
            r'\1    def log_request_response(event, response_body, lambda_name):',
            content
        )

    # Fix 2: Fix the docstring and function body indentation
    logging_pattern = r'(    def log_request_response\(event, response_body, lambda_name\):\n)(    """Log request and response data in a format that can be parsed for OpenAPI generation\.\."""\n)(    try:\n)(        # Log request data\n)(        if \'body\' in event:\n)(            request_body = json\.loads\(event\[\'body\'\]\) if isinstance\(event\[\'body\'\], str\) else event\[\'body\'\]\n)(            print\(f"REQUEST_BODY: \{json\.dumps\(request_body\)\}"\)\n)(        \n)(        # Log response data\n)(        if response_body:\n)(            print\(f"RESPONSE_BODY: \{json\.dumps\(response_body\)\}"\)\n)(            \n)(    except Exception as e:\n)(        print\(f"ERROR logging request/response: \{str\(e\)\}"\)\n)'

    replacement = r'\1        """Log request and response data in a format that can be parsed for OpenAPI generation."""\n        try:\n            # Log request data\n            if \'body\' in event:\n                request_body = json.loads(event[\'body\']) if isinstance(event[\'body\'], str) else event[\'body\']\n                print(f"REQUEST_BODY: {json.dumps(request_body)}")\n            \n            # Log response data\n            if response_body:\n                print(f"RESPONSE_BODY: {json.dumps(response_body)}")\n                \n        except Exception as e:\n            print(f"ERROR logging request/response: {str(e)}")\n'

    content = re.sub(logging_pattern, replacement, content)

    # Fix 3: Add logging call at the beginning of lambda_handler
    # Look for the pattern: def lambda_handler(event, context):\n    def log_request_response...
    # and add a logging call after the function definition
    handler_pattern = r'(def lambda_handler\(event, context\):\n)(    def log_request_response\(event, response_body, lambda_name\):\n.*?\n    )'

    def add_logging_call(match):
        return f"{match.group(1)}{match.group(2)}    # Log the incoming request\n    log_request_response(event, None, \"{os.path.basename(file_path).replace('.py', '')}\")\n\n    "

    content = re.sub(handler_pattern, add_logging_call,
                     content, flags=re.DOTALL)

    # Write the fixed content back if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Fixed {file_path}")
        return True
    else:
        print(f"No issues found in {file_path}")
        return False


def deploy_lambda(function_name, file_path):
    """Deploy a Lambda function to AWS."""
    print(f"Deploying {function_name}...")

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
        print(f"✅ Successfully deployed {function_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to deploy {function_name}: {e.stderr}")
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

    # List of Lambda functions that need to be fixed
    lambda_functions = [
        'getPandaTransactions',
        'getPandaEntityTypes',
        'getPandaTransactionStatuses',
        'getPandaTransactionTypes',
        'getPandaUsers',
        'getPandaClientGroups',
        'updatePandaEntity',
        'updatePandaUser',
        'updatePandaPositions',
        'updatePandaTransaction',
        'updatePandaTransactionType',
        'updatePandaEntityType',
        'updatePandaClientGroup',
        'updatePandaTransactionStatuses',
        'deletePandaRecord',
        'modifyPandaClientGroupMembership',
        'modifyPandaClientGroupEntities',
        'managePandaInvitation'
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
