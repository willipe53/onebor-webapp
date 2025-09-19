# OneBor Frontend Deployment

This directory contains scripts for deploying the OneBor React frontend to AWS S3 with CloudFront distribution.

## Prerequisites

1. **Node.js and npm** - For building the React app
2. **AWS CLI** - For deploying to S3 and invalidating CloudFront
3. **AWS Credentials** - Configured with appropriate permissions

### AWS Permissions Required

Your AWS credentials need the following permissions:

- `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on `s3://onebor-app`
- `cloudfront:CreateInvalidation` on distribution `E3GH09JUCHC3AZ`

## Deployment Configuration

- **S3 Bucket**: `onebor-app`
- **CloudFront Distribution**: `E3GH09JUCHC3AZ`
- **Domain**: `app.onebor.com`
- **AWS Region**: `us-east-1`

## Deployment Scripts

### Option 1: Python Script (Recommended)

```bash
# Run the Python deployment script
python3 scripts/deploy_frontend.py
```

### Option 2: Shell Script

```bash
# Run the shell deployment script
./scripts/deploy_frontend.sh
```

### Option 3: Manual Deployment

```bash
# Build the app
npm install
npm run build

# Deploy to S3
aws s3 sync dist/ s3://onebor-app/ --delete --region us-east-1

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
    --distribution-id E3GH09JUCHC3AZ \
    --paths "/*" \
    --region us-east-1
```

## Testing Deployment

After deployment, test that everything is working:

```bash
# Run the test script
python3 scripts/test_deployment.py
```

Or manually visit: https://app.onebor.com

## What the Deployment Does

1. **Builds the React app** using `npm run build`
2. **Syncs files to S3** using `aws s3 sync` with `--delete` flag
3. **Invalidates CloudFront cache** to ensure new content is served immediately
4. **Tests the deployment** to verify it's working correctly

## Troubleshooting

### Build Issues

- Ensure all dependencies are installed: `npm install`
- Check for TypeScript/linting errors: `npm run build`
- Verify the `dist/` directory is created after build

### S3 Upload Issues

- Verify AWS credentials are configured: `aws sts get-caller-identity`
- Check S3 bucket permissions
- Ensure the bucket exists: `aws s3 ls s3://onebor-app`

### CloudFront Issues

- Verify the distribution ID is correct
- Check CloudFront distribution status: `aws cloudfront get-distribution --id E3GH09JUCHC3AZ`
- CloudFront cache invalidation can take 5-15 minutes

### App Not Loading

- Check CloudFront distribution status
- Verify S3 bucket has the correct files
- Check browser console for errors
- Ensure the API endpoint is accessible

## Environment Variables

The app is configured to use the production API at `https://api.onebor.com` when built for production. This is configured in `vite.config.ts`.

## Rollback

If you need to rollback to a previous version:

1. Revert your code changes
2. Run the deployment script again
3. The `--delete` flag will remove old files and upload new ones

## Monitoring

- **CloudFront Metrics**: Check AWS CloudWatch for distribution metrics
- **S3 Access Logs**: Enable S3 access logging if needed
- **Application Logs**: Check browser console for client-side errors

