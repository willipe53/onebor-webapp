#!/usr/bin/env python3
import boto3
import time
from botocore.exceptions import ClientError

region = "us-east-2"
queue_url = "https://sqs.us-east-2.amazonaws.com/316490106381/pandatransactions.fifo"

sqs = boto3.client("sqs", region_name=region)


def purge_queue():
    try:
        print(f"Purging queue: {queue_url}")
        sqs.purge_queue(QueueUrl=queue_url)
        print("✅ Queue purge requested. May take up to 60 seconds.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "PurgeQueueInProgress":
            print("⚠️ Purge already in progress. Try manual drain instead.")
        else:
            raise


def manual_drain():
    print(f"Draining queue manually: {queue_url}")
    while True:
        messages = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=0
        ).get("Messages", [])

        if not messages:
            print("✅ Queue is empty.")
            break

        entries = [{"Id": msg["MessageId"],
                    "ReceiptHandle": msg["ReceiptHandle"]} for msg in messages]

        sqs.delete_message_batch(QueueUrl=queue_url, Entries=entries)
        print(f"🗑️ Deleted {len(entries)} messages...")

        # Optional sleep to avoid throttling
        time.sleep(0.2)


if __name__ == "__main__":
    # Try purge first
    try:
        purge_queue()
    except Exception as e:
        print(f"❌ Purge failed: {e}")
        print("Falling back to manual drain...")
        manual_drain()
