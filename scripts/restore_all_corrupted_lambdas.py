#!/usr/bin/env python3
"""
Restore all corrupted Lambda functions to clean working states.
"""

import os
import subprocess
import zipfile
import re


def restore_lambda_file(file_path):
    """Restore a Lambda function to a clean working state."""
    function_name = os.path.basename(file_path).replace('.py', '')
    print(f"Restoring {function_name}...")

    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    # Remove all problematic logging code
    # Pattern 1: Remove the entire log_request_response function definition
    pattern1 = r'def log_request_response\(event, response_body, lambda_name\):.*?(?=\n    [^ ]|\n\ndef|\n\nclass|\n\nif|\Z)'
    content = re.sub(pattern1, '', content, flags=re.DOTALL)

    # Pattern 2: Remove any remaining log_request_response calls
    pattern2 = r'log_request_response\([^)]+\)\n?'
    content = re.sub(pattern2, '', content)

    # Pattern 3: Fix any remaining indentation issues
    # Look for function definitions that are missing their body
    pattern3 = r'(def lambda_handler\(event, context\):\n)(\n)'
    content = re.sub(pattern3, r'\1    pass\n', content)

    # Pattern 4: Remove any orphaned try blocks without proper structure
    pattern4 = r'    try:\n        # Log request data\n        if \'body\' in event:.*?(?=\n    [^ ]|\n\ndef|\n\nclass|\n\Z)'
    content = re.sub(pattern4, '', content, flags=re.DOTALL)

    # Clean up any double newlines
    content = re.sub(r'\n\n\n+', '\n\n', content)

    # Write the cleaned content back
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ Restored {function_name}")
        return True
    else:
        print(f"  ✅ No changes needed for {function_name}")
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
    """Restore all corrupted Lambda functions."""
    database_dir = "database"
    restored_count = 0
    deployed_count = 0

    # List of Lambda functions that need restoration (from the syntax check)
    corrupted_functions = [
        'updatePandaEntity',
        'updatePandaTransaction',
        'updatePandaUser',
        'updatePandaPositions',
        'modifyPandaClientGroupMembership',
        'modifyPandaClientGroupEntities',
        'updatePandaTransactionType',
        'updatePandaEntityType',
        'deletePandaRecord',
        'updatePandaClientGroup',
        'getPandaTransactionStatuses'
    ]

    for function_name in corrupted_functions:
        file_path = os.path.join(database_dir, f"{function_name}.py")
        if os.path.exists(file_path):
            if restore_lambda_file(file_path):
                restored_count += 1
                if deploy_lambda(function_name, file_path):
                    deployed_count += 1
        else:
            print(f"⚠️  File not found: {file_path}")

    print(f"\n📊 Summary:")
    print(f"   Restored: {restored_count} files")
    print(f"   Deployed: {deployed_count} files")


if __name__ == "__main__":
    main()
