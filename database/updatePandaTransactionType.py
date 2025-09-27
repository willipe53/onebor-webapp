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

        # Extract parameters
        transaction_type_id = body.get("transaction_type_id")
        name = body.get("name")
        properties = body.get("properties")

        # Debug logging
        print(f"DEBUG: transaction_type_id={transaction_type_id}, name={name}")
        print(f"DEBUG: properties={properties}")

        # Get database connection
        secrets = get_db_secret()
        conn = get_connection(secrets)

        with conn.cursor() as cursor:
            if transaction_type_id:
                # Update existing transaction type
                updates = []
                params = []

                if name is not None:
                    updates.append("name = %s")
                    params.append(name)
                if properties is not None:
                    # Convert properties to JSON string if it's a dict
                    if isinstance(properties, dict):
                        properties = json.dumps(properties)
                    updates.append("properties = %s")
                    params.append(properties)

                if not updates:
                    return {
                        "statusCode": 400,
                        "headers": cors_headers,
                        "body": json.dumps({"error": "No fields to update"})
                    }

                # Add transaction_type_id to params
                params.append(transaction_type_id)

                sql = f"UPDATE transaction_types SET {', '.join(updates)} WHERE transaction_type_id = %s"
                cursor.execute(sql, params)

                if cursor.rowcount == 0:
                    return {
                        "statusCode": 404,
                        "headers": cors_headers,
                        "body": json.dumps({"error": "Transaction type not found"})
                    }

                conn.commit()

                return {
                    "statusCode": 200,
                    "headers": cors_headers,
                    "body": json.dumps({
                        "success": True,
                        "message": "Transaction type updated successfully",
                        "transaction_type_id": transaction_type_id
                    })
                }
            else:
                # Create new transaction type
                if not name:
                    return {
                        "statusCode": 400,
                        "headers": cors_headers,
                        "body": json.dumps({"error": "name is required for new transaction types"})
                    }

                # Convert properties to JSON string if it's a dict
                if isinstance(properties, dict):
                    properties = json.dumps(properties)

                sql = """
                    INSERT INTO transaction_types (name, properties)
                    VALUES (%s, %s)
                """
                cursor.execute(sql, (name, properties))
                new_transaction_type_id = cursor.lastrowid

                conn.commit()

                return {
                    "statusCode": 200,
                    "headers": cors_headers,
                    "body": json.dumps({
                        "success": True,
                        "message": "Transaction type created successfully",
                        "transaction_type_id": new_transaction_type_id
                    })
                }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"})
        }
    finally:
        if conn:
            conn.close()


# For local testing
if __name__ == "__main__":
    # Test cases for local development
    test_events = [
        {
            "transaction_type_id": 1,
            "name": "Updated Test Transaction Type",
            "properties": {"test": "value"}
        },
        {
            "name": "New Test Transaction Type",
            "properties": {"new_field": "new_value"}
        }
    ]

    for test_event in test_events:
        print(f"\nTesting: {test_event}")
        result = lambda_handler(test_event, None)
        print(f"Result: {result}")
