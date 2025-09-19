import boto3
import json
import pymysql
import os

SECRET_ARN = os.environ["SECRET_ARN"]


def get_db_secret():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=SECRET_ARN)
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
    conn = None
    try:
        body = event.get("body")
        if body and isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = event

        user_id = body.get("user_id")
        sub = body.get("sub")  # Cognito user ID
        email = body.get("email")

        secrets = get_db_secret()
        conn = get_connection(secrets)

        query = "SELECT * FROM users WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)

        if sub:
            query += " AND sub = %s"
            params.append(sub)

        if email:
            if email.endswith("%"):
                query += " AND email LIKE %s"
            else:
                query += " AND email = %s"
            params.append(email)

        with conn.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(rows, default=str)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
    finally:
        if conn:
            conn.close()
