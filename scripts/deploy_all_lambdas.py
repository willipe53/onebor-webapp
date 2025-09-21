#!/usr/bin/env python3
"""
Deploy all Lambda functions with CORS headers
"""

import os
import subprocess
import glob

def deploy_lambda_file(filename):
    """Deploy a single Lambda function"""
    print(f"\n🚀 Deploying {filename}...")
    try:
        result = subprocess.run([
            "python3", "scripts/deploy_lambda.py", filename
        ], cwd="/Users/willipe/github/onebor-webapp", capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Successfully deployed {filename}")
            return True
        else:
            print(f"❌ Failed to deploy {filename}")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Exception deploying {filename}: {e}")
        return False

def main():
    """Deploy all Lambda functions"""
    
    database_dir = "database"
    lambda_files = glob.glob(f"{database_dir}/*.py")
    
    # Filter to only deployment-relevant files
    deploy_files = [f for f in lambda_files if os.path.basename(f).startswith(('get', 'update', 'manage', 'modify'))]
    
    print(f"📋 Found {len(deploy_files)} Lambda functions to deploy:")
    for file in deploy_files:
        print(f"  - {file}")
    
    print(f"\n🚀 Starting deployment...")
    
    success_count = 0
    for file_path in deploy_files:
        if deploy_lambda_file(file_path):
            success_count += 1
    
    print(f"\n📊 Deployment Summary:")
    print(f"✅ Successfully deployed: {success_count}/{len(deploy_files)}")
    print(f"❌ Failed deployments: {len(deploy_files) - success_count}")
    
    if success_count == len(deploy_files):
        print(f"\n🎉 All Lambda functions deployed successfully!")
        print(f"🌐 CORS headers should now be active for https://app.onebor.com")
    else:
        print(f"\n⚠️  Some deployments failed. Check the errors above.")

if __name__ == "__main__":
    main()
