#!/usr/bin/env python3
"""
Deploy OneBor frontend to S3 with CloudFront invalidation
"""

import subprocess
import sys
import os
import json
from pathlib import Path

# Configuration
S3_BUCKET = "onebor-app"
CLOUDFRONT_DISTRIBUTION_ID = "E3GH09JUCHC3AZ"
DIST_PATH = "dist"
AWS_REGION = "us-east-1"  # CloudFront distributions are always in us-east-1


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True,
                                check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        sys.exit(1)


def check_prerequisites():
    """Check if required tools are installed"""
    print("🔍 Checking prerequisites...")

    # Check if npm is available
    try:
        subprocess.run(["npm", "--version"], check=True, capture_output=True)
        print("✅ npm is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ npm is not installed or not in PATH")
        sys.exit(1)

    # Check if AWS CLI is available
    try:
        subprocess.run(["aws", "--version"], check=True, capture_output=True)
        print("✅ AWS CLI is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ AWS CLI is not installed or not in PATH")
        sys.exit(1)


def build_frontend():
    """Build the React frontend"""
    print("🏗️  Building frontend...")

    # Install dependencies
    run_command("npm install", "Installing dependencies")

    # Build the project
    run_command("npm run build", "Building React app")

    # Verify dist directory exists
    if not os.path.exists(DIST_PATH):
        print(f"❌ Build failed: {DIST_PATH} directory not found")
        sys.exit(1)

    print(f"✅ Frontend built successfully in {DIST_PATH}")


def deploy_to_s3():
    """Deploy the built files to S3"""
    print("🚀 Deploying to S3...")

    # Sync files to S3
    sync_command = f"aws s3 sync {DIST_PATH}/ s3://{S3_BUCKET}/ --delete --region {AWS_REGION}"
    run_command(sync_command, f"Syncing files to s3://{S3_BUCKET}")

    print(f"✅ Files deployed to s3://{S3_BUCKET}")


def invalidate_cloudfront():
    """Invalidate CloudFront cache"""
    print("🔄 Invalidating CloudFront cache...")

    # Create invalidation
    invalidation_command = f"aws cloudfront create-invalidation --distribution-id {CLOUDFRONT_DISTRIBUTION_ID} --paths '/*' --region {AWS_REGION}"
    result = run_command(invalidation_command,
                         "Creating CloudFront invalidation")

    # Parse the invalidation ID from the response
    try:
        response = json.loads(result.stdout)
        invalidation_id = response["Invalidation"]["Id"]
        print(f"✅ CloudFront invalidation created: {invalidation_id}")
        print(f"🌐 Your app will be available at: https://app.onebor.com")
        print(f"⏳ Cache invalidation may take 5-15 minutes to complete")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"⚠️  Could not parse invalidation response: {e}")
        print("✅ Invalidation was created, but couldn't extract ID")


def main():
    """Main deployment function"""
    print("🚀 Starting OneBor frontend deployment...")
    print(f"📦 S3 Bucket: {S3_BUCKET}")
    print(f"🌐 CloudFront Distribution: {CLOUDFRONT_DISTRIBUTION_ID}")
    print(f"🌍 Domain: app.onebor.com")
    print("-" * 50)

    # Change to project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    print(f"📁 Working directory: {project_root}")

    try:
        # Run deployment steps
        check_prerequisites()
        build_frontend()
        deploy_to_s3()
        invalidate_cloudfront()

        print("-" * 50)
        print("🎉 Deployment completed successfully!")
        print(f"🌐 Your app is now available at: https://app.onebor.com")
        print("⏳ Please wait 5-15 minutes for CloudFront cache invalidation to complete")

    except KeyboardInterrupt:
        print("\n❌ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

