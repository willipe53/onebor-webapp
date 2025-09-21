#!/bin/bash

# onebor Frontend Deployment Script
# Deploys the React app to S3 and invalidates CloudFront cache

set -e  # Exit on any error

# Change to project root directory
cd "$(dirname "$0")/.."

# Configuration
S3_BUCKET="onebor-app"
CLOUDFRONT_DISTRIBUTION_ID="E3GH09JUCHC3AZ"
DIST_PATH="dist"
AWS_REGION="us-east-1"

echo "🚀 Starting onebor frontend deployment..."
echo "📦 S3 Bucket: $S3_BUCKET"
echo "🌐 CloudFront Distribution: $CLOUDFRONT_DISTRIBUTION_ID"
echo "🌍 Domain: app.onebor.com"
echo "----------------------------------------"

# Check prerequisites
echo "🔍 Checking prerequisites..."
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed or not in PATH"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed or not in PATH"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Build frontend
echo "🏗️  Building frontend..."
echo "🔄 Cleaning previous build..."
rm -rf "$DIST_PATH"

echo "🔄 Installing dependencies..."
if ! npm install; then
    echo "❌ npm install failed"
    exit 1
fi

echo "🔄 Building React app..."
if ! npm run build; then
    echo "❌ npm run build failed"
    exit 1
fi

if [ ! -d "$DIST_PATH" ]; then
    echo "❌ Build failed: $DIST_PATH directory not found"
    echo "This could happen if:"
    echo "  - TypeScript compilation failed"
    echo "  - Vite build process failed"
    echo "  - Out of disk space"
    echo "  - Permission issues"
    exit 1
fi

echo "✅ Frontend built successfully in $DIST_PATH"

# Deploy to S3
echo "🚀 Deploying to S3..."
echo "🔄 Syncing files to s3://$S3_BUCKET..."
aws s3 sync "$DIST_PATH"/ "s3://$S3_BUCKET/" --delete --region "$AWS_REGION"

echo "✅ Files deployed to s3://$S3_BUCKET"

# Invalidate CloudFront
echo "🔄 Invalidating CloudFront cache..."
echo "🔄 Creating CloudFront invalidation..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --paths "/*" \
    --region "$AWS_REGION" \
    --query 'Invalidation.Id' \
    --output text)

echo "✅ CloudFront invalidation created: $INVALIDATION_ID"

echo "----------------------------------------"
echo "🎉 Deployment completed successfully!"
echo "🌐 Your app is now available at: https://app.onebor.com"
echo "⏳ Please wait 5-15 minutes for CloudFront cache invalidation to complete"

