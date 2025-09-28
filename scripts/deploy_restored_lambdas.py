#!/usr/bin/env python3
"""
Deploy all restored Lambda functions to AWS.
"""

import os
import subprocess
import zipfile

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
    """Deploy all Lambda functions."""
    database_dir = "database"
    deployed_count = 0
    
    # Get all Python files in the database directory
    python_files = [f for f in os.listdir(database_dir) if f.endswith('.py')]
    
    print(f"Deploying {len(python_files)} Lambda functions:")
    
    for filename in python_files:
        file_path = os.path.join(database_dir, filename)
        function_name = filename.replace('.py', '')
        
        if deploy_lambda(function_name, file_path):
            deployed_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   Deployed: {deployed_count} files")

if __name__ == "__main__":
    main()
