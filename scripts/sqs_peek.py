#!/usr/bin/env python3


import boto3

sqs = boto3.client("sqs", region_name="us-east-2")
queue_url = "https://sqs.us-east-2.amazonaws.com/316490106381/pandatransactions.fifo"

response = sqs.receive_message(
    QueueUrl=queue_url,
    MaxNumberOfMessages=10,
    VisibilityTimeout=0,
    WaitTimeSeconds=0
)

for msg in response.get("Messages", []):
    print("Message ID:", msg["MessageId"])
    print("Body:", msg["Body"])
