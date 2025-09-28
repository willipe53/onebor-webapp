#!/usr/bin/env python3
"""
Comprehensive check and fix for all remaining Lambda functions.
"""

import os
import subprocess
import zipfile


def check_lambda_syntax(file_path):
    """Check if a Lambda function has syntax errors."""
    function_name = os.path.basename(file_path).replace('.py', '')
    print(f"Checking {function_name}...")

    try:
        # Try to compile the Python file to check for syntax errors
        with open(file_path, 'r') as f:
            content = f.read()

        compile(content, file_path, 'exec')
        print(f"  ✅ No syntax errors found")
        return True
    except SyntaxError as e:
        print(f"  ❌ Syntax error found: {e}")
        return False
    except Exception as e:
        print(f"  ⚠️  Error checking file: {e}")
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
    """Check all Lambda function files."""
    database_dir = "database"
    checked_count = 0
    syntax_errors_count = 0

    # Get all Python files in the database directory
    python_files = [f for f in os.listdir(database_dir) if f.endswith('.py')]

    print(f"Found {len(python_files)} Python files to check:")

    for filename in python_files:
        file_path = os.path.join(database_dir, filename)
        function_name = filename.replace('.py', '')

        checked_count += 1
        if not check_lambda_syntax(file_path):
            syntax_errors_count += 1
            print(f"  ⚠️  {function_name} needs manual fixing")

    print(f"\n📊 Summary:")
    print(f"   Checked: {checked_count} files")
    print(f"   Syntax errors: {syntax_errors_count} files")

    if syntax_errors_count > 0:
        print(
            f"\n⚠️  {syntax_errors_count} files have syntax errors and need manual fixing.")


if __name__ == "__main__":
    main()
