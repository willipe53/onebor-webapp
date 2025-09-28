#!/usr/bin/env python3
"""
Check and fix all Lambda functions with logging issues.
"""

import os
import subprocess
import zipfile


def check_and_fix_lambda(file_path):
    """Check if a Lambda function has syntax issues and fix them."""
    function_name = os.path.basename(file_path).replace('.py', '')
    print(f"Checking {function_name}...")

    with open(file_path, 'r') as f:
        content = f.read()

    # Check for common syntax issues
    issues_found = []

    # Check for improper indentation of log_request_response function
    if 'def log_request_response(event, response_body, lambda_name):\n    """Log request and response data' in content:
        issues_found.append("improper indentation")

    # Check for missing indentation in function calls
    if 'log_request_response(event, None, "' in content and '    log_request_response(event, None, "' not in content:
        issues_found.append("missing indentation in function call")

    if issues_found:
        print(f"  ❌ Issues found: {', '.join(issues_found)}")
        return True
    else:
        print(f"  ✅ No issues found")
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
    """Check and fix all Lambda function files."""
    database_dir = "database"
    checked_count = 0
    issues_count = 0
    deployed_count = 0

    # List of Lambda functions to check
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
            checked_count += 1
            if check_and_fix_lambda(file_path):
                issues_count += 1
                # For now, just report the issue - manual fixing might be needed
                print(f"  ⚠️  Manual fix required for {function_name}")
        else:
            print(f"⚠️  File not found: {file_path}")

    print(f"\n📊 Summary:")
    print(f"   Checked: {checked_count} files")
    print(f"   Issues found: {issues_count} files")
    print(f"   Deployed: {deployed_count} files")


if __name__ == "__main__":
    main()
