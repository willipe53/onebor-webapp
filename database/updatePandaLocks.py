import boto3
import json
import pymysql
import os
from typing import Dict, Any, List, Optional

# CORS headers
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}


def get_db_secret():
    """Get database credentials from AWS Secrets Manager."""
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=os.environ["SECRET_ARN"])
    return json.loads(response["SecretString"])


def get_db_connection():
    """Get database connection using AWS Secrets Manager."""
    secrets = get_db_secret()
    return pymysql.connect(
        host=secrets["DB_HOST"],
        user=secrets["DB_USER"],
        password=secrets["DB_PASS"],
        database=secrets["DATABASE"],
        connect_timeout=5,
        cursorclass=pymysql.cursors.DictCursor
    )


def lambda_handler(event, context):
    """Lambda handler for managing lambda locks."""
    print(f"DEBUG: Event: {event}")
    print(f"DEBUG: Context: {context}")

    # Handle CORS preflight request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'CORS preflight successful'})
        }

    try:
        # Parse request body
        if event.get('httpMethod') == 'POST':
            body = json.loads(event.get('body', '{}'))
        else:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Only POST method is supported'})
            }

        # Extract parameters
        action = body.get('action')
        holder = body.get('holder')

        # Generate holder from context if not provided
        if not holder and context:
            holder = f"{context.log_stream_name}:{context.aws_request_id}"

        print(f"DEBUG: Action: {action}, Holder: {holder}")

        # Validate required parameters
        if not action:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'action parameter is required'})
            }

        if not holder:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'holder parameter is required'})
            }

        if action not in ['set', 'delete']:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'action must be "set" or "delete"'})
            }

        # Get database connection
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            lock_id = "Position Keeper"

            if action == 'set':
                # First, clean up stale locks
                print(f"DEBUG: Cleaning up stale locks for lock_id: {lock_id}")
                cleanup_sql = """
                DELETE FROM lambda_locks 
                WHERE lock_id = %s AND expires_at < NOW()
                """
                cursor.execute(cleanup_sql, (lock_id,))
                stale_deleted = cursor.rowcount
                print(f"DEBUG: Deleted {stale_deleted} stale locks")

                # Try to insert the new lock
                try:
                    insert_sql = """
                    INSERT INTO lambda_locks (lock_id, holder, expires_at)
                    VALUES (%s, %s, NOW() + INTERVAL 5 MINUTE)
                    """
                    cursor.execute(insert_sql, (lock_id, holder))
                    connection.commit()

                    print(
                        f"DEBUG: Successfully acquired lock for holder: {holder}")

                    return {
                        'statusCode': 200,
                        'headers': cors_headers,
                        'body': json.dumps({
                            'message': 'Lock acquired successfully',
                            'action': action,
                            'lock_id': lock_id,
                            'holder': holder,
                            'stale_deleted': stale_deleted
                        })
                    }

                except pymysql.IntegrityError as e:
                    if e.args[0] == 1062:  # ER_DUP_ENTRY
                        print(
                            f"DEBUG: Lock already exists - another process is running")
                        connection.rollback()

                        return {
                            'statusCode': 409,  # Conflict
                            'headers': cors_headers,
                            'body': json.dumps({
                                'message': 'Lock already exists - another process is running',
                                'action': action,
                                'lock_id': lock_id,
                                'holder': holder,
                                'stale_deleted': stale_deleted
                            })
                        }
                    else:
                        raise

            elif action == 'delete':
                # Delete the lock
                print(f"DEBUG: Deleting lock for lock_id: {lock_id}")
                delete_sql = """
                DELETE FROM lambda_locks 
                WHERE lock_id = %s
                """
                cursor.execute(delete_sql, (lock_id,))
                deleted_count = cursor.rowcount
                connection.commit()

                print(
                    f"DEBUG: Deleted {deleted_count} locks for lock_id: {lock_id}")

                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'message': 'Lock released successfully',
                        'action': action,
                        'lock_id': lock_id,
                        'holder': holder,
                        'deleted_count': deleted_count
                    })
                }

        except Exception as e:
            print(f"ERROR: Database operation failed: {str(e)}")
            connection.rollback()
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': f'Database operation failed: {str(e)}'
                })
            }
        finally:
            cursor.close()
            connection.close()

    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in request body: {str(e)}")
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({
                'error': f'Invalid JSON in request body: {str(e)}'
            })
        }
    except Exception as e:
        print(f"ERROR: Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': f'Unexpected error: {str(e)}'
            })
        }


# For local testing
if __name__ == "__main__":
    # Simulate a Lambda event and context
    test_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "action": "set",
            "holder": "test-stream:test-request-id"
        })
    }

    test_context = type('Context', (), {
        'log_stream_name': 'test-stream',
        'aws_request_id': 'test-request-id'
    })()

    result = lambda_handler(test_event, test_context)
    print(f"Test result: {result}")
