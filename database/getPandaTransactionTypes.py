import boto3
import json
import pymysql
import os


def get_db_secret():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=os.environ["SECRET_ARN"])
    return json.loads(response["SecretString"])


def get_connection(secrets):
    return pymysql.connect(
        host=secrets["DB_HOST"],
        user=secrets["DB_USER"],
        password=secrets["DB_PASS"],
        database=secrets["DATABASE"],
        connect_timeout=5,
        cursorclass=pymysql.cursors.DictCursor
    )


def lambda_handler(event, context):
    # CORS headers for all responses
    cors_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "https://app.onebor.com",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Credentials": "true"
    }

    # Handle preflight OPTIONS requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": ""
        }

    conn = None
    try:
        # Parse incoming request body
        body = event.get("body")
        if body and isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = event  # allow direct testing in Lambda console

        count_only = body.get("count_only", False)  # Default to False

        secrets = get_db_secret()
        conn = get_connection(secrets)

        with conn.cursor() as cursor:
            if count_only:
                cursor.execute(
                    "SELECT COUNT(*) as transaction_type_count FROM transaction_types")
                rows = cursor.fetchall()
                count = rows[0]['transaction_type_count'] if rows else 0
                return {
                    "statusCode": 200,
                    "headers": cors_headers,
                    "body": json.dumps(count)
                }
            else:
                cursor.execute(
                    "SELECT * FROM transaction_types ORDER BY transaction_type_id")
                rows = cursor.fetchall()

                return {
                    "statusCode": 200,
                    "headers": cors_headers,
                    "body": json.dumps(rows, default=str)
                }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": str(e)})
        }
    finally:
        if conn:
            conn.close()


# For local testing
if __name__ == "__main__":
    # Test cases for local development
    test_events = [
        {"count_only": True},
        {"count_only": False}
    ]

    for test_event in test_events:
        print(f"\nTesting: {test_event}")
        result = lambda_handler(test_event, None)
        print(f"Result: {result}")
