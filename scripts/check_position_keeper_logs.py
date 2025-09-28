#!/usr/bin/env python3
"""
Script to check CloudWatch logs for the position keeper Lambda function.
This helps verify that the position keeping logic is working correctly.
"""

import boto3
import json
import time
from datetime import datetime, timedelta


def status_print(message, level="info"):
    """Print status message with appropriate formatting."""
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    print(f"{icons.get(level, 'ℹ️')} {message}")


def check_position_keeper_logs():
    """Check CloudWatch logs for position keeper activity."""
    try:
        logs_client = boto3.client('logs', region_name='us-east-2')

        # Get log group name for position keeper
        log_group_name = '/aws/lambda/positionKeeper'

        status_print(f"Checking logs for: {log_group_name}", "info")

        # Calculate time range (last 10 minutes)
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=10)

        # Convert to milliseconds
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)

        status_print(f"Time range: {start_time} to {end_time}", "info")

        # Get log events
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time_ms,
            endTime=end_time_ms,
            limit=50
        )

        events = response.get('events', [])

        if not events:
            status_print("No recent log events found", "warning")
            return

        status_print(f"Found {len(events)} log events", "success")
        status_print("=" * 80, "info")

        # Display recent events
        for event in events[-10:]:  # Show last 10 events
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")

        status_print("=" * 80, "info")

        # Look for specific position keeping messages
        position_messages = []
        for event in events:
            message = event['message'].strip()
            if any(keyword in message.lower() for keyword in [
                'processing positions', 'need to create', 'will be applied',
                'position keeping', 'transaction type', 'action'
            ]):
                position_messages.append((event['timestamp'], message))

        if position_messages:
            status_print(
                f"Found {len(position_messages)} position-related messages:", "success")
            print()
            for timestamp, message in position_messages[-5:]:  # Show last 5
                dt = datetime.fromtimestamp(timestamp / 1000)
                print(f"[{dt.strftime('%H:%M:%S')}] {message}")
        else:
            status_print(
                "No position-related messages found in recent logs", "warning")

    except Exception as e:
        status_print(f"Error checking logs: {str(e)}", "error")


def check_queue_status():
    """Check SQS queue status."""
    try:
        sqs = boto3.client('sqs', region_name='us-east-2')
        queue_url = "https://sqs.us-east-2.amazonaws.com/316490106381/pandatransactions.fifo"

        response = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['ApproximateNumberOfMessages',
                            'ApproximateNumberOfMessagesNotVisible']
        )

        attrs = response['Attributes']
        visible = attrs.get('ApproximateNumberOfMessages', '0')
        not_visible = attrs.get('ApproximateNumberOfMessagesNotVisible', '0')

        status_print("Queue Status:", "info")
        print(f"  - Visible messages: {visible}")
        print(f"  - Messages being processed: {not_visible}")

    except Exception as e:
        status_print(f"Error checking queue: {str(e)}", "error")


def main():
    """Main function."""
    status_print("Position Keeper Logs Checker", "info")
    status_print("=" * 50, "info")

    # Check queue status first
    check_queue_status()
    print()

    # Check logs
    check_position_keeper_logs()


if __name__ == "__main__":
    main()
