import boto3
import json
import pymysql
import os
from typing import Dict, Any

# CORS headers
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}


def get_db_secret():
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
    """Lambda handler for deleting transactions."""
    print(f"DEBUG: Event: {event}")

    try:
        # Parse the request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        print(f"DEBUG: Parsed body: {body}")

        # Extract parameters
        transaction_id = body.get("transaction_id")

        if not transaction_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({"error": "transaction_id is required"})
            }

        # Connect to database
        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                # Check if transaction exists and is INCOMPLETE
                check_sql = """
                    SELECT transaction_id, transaction_status_id 
                    FROM transactions 
                    WHERE transaction_id = %s
                """
                cursor.execute(check_sql, (transaction_id,))
                transaction = cursor.fetchone()

                if not transaction:
                    return {
                        'statusCode': 404,
                        'headers': cors_headers,
                        'body': json.dumps({"error": "Transaction not found"})
                    }

                # Only allow deletion of INCOMPLETE transactions (status_id = 1)
                if transaction['transaction_status_id'] != 1:
                    return {
                        'statusCode': 400,
                        'headers': cors_headers,
                        'body': json.dumps({"error": "Only INCOMPLETE transactions can be deleted"})
                    }

                # Delete the transaction
                delete_sql = "DELETE FROM transactions WHERE transaction_id = %s"
                cursor.execute(delete_sql, (transaction_id,))

                if cursor.rowcount == 0:
                    return {
                        'statusCode': 404,
                        'headers': cors_headers,
                        'body': json.dumps({"error": "Transaction not found or already deleted"})
                    }

                connection.commit()

                print(
                    f"DEBUG: Successfully deleted transaction {transaction_id}")

                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        "message": "Transaction deleted successfully",
                        "transaction_id": transaction_id
                    })
                }

        finally:
            connection.close()

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({"error": f"Internal server error: {str(e)}"})
        }
