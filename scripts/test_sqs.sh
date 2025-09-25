#!/bin/bash
set -euo pipefail

AWS_REGION="us-east-2"
SQS_FIFO_QUEUE="https://sqs.us-east-2.amazonaws.com/316490106381/pandatransactions.fifo"

echo "📤 Sending test message..."
aws sqs send-message \
  --region "$AWS_REGION" \
  --queue-url "$SQS_FIFO_QUEUE" \
  --message-body '{"test":"hello"}' \
  --message-group-id "test-group" \
  --message-deduplication-id "test-$(date +%s)"

echo "⏳ Receiving message..."
RECEIPT_HANDLE=$(aws sqs receive-message \
  --region "$AWS_REGION" \
  --queue-url "$SQS_FIFO_QUEUE" \
  --max-number-of-messages 1 \
  --query 'Messages[0].ReceiptHandle' \
  --output text)

BODY=$(aws sqs receive-message \
  --region "$AWS_REGION" \
  --queue-url "$SQS_FIFO_QUEUE" \
  --max-number-of-messages 1 \
  --query 'Messages[0].Body' \
  --output text)

echo "✅ Got message body: $BODY"
echo "🗑️ Deleting message..."
aws sqs delete-message \
  --region "$AWS_REGION" \
  --queue-url "$SQS_FIFO_QUEUE" \
  --receipt-handle "$RECEIPT_HANDLE"

echo "🎉 Done!"
