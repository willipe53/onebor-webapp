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
        body = event.get("body")
        if body and isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = event

        user_id = body.get("user_id")
        sub = body.get("sub")  # Cognito user ID
        email = body.get("email")
        requesting_user_id = body.get(
            "requesting_user_id")  # User making the request
        # Filter by specific client group
        client_group_id = body.get("client_group_id")
        count_only = body.get("count_only", False)  # Default to False

        secrets = get_db_secret()
        conn = get_connection(secrets)

        if client_group_id:
            # Filter by specific client group membership
            if count_only:
                query = """
                SELECT COUNT(DISTINCT u.user_id) as user_count
                FROM users u
                INNER JOIN client_group_users cgu ON u.user_id = cgu.user_id
                WHERE cgu.client_group_id = %s
                """
            else:
                query = """
                SELECT DISTINCT u.* 
                FROM users u
                INNER JOIN client_group_users cgu ON u.user_id = cgu.user_id
                WHERE cgu.client_group_id = %s
                """
            params = [client_group_id]
        elif requesting_user_id:
            # Apply access control - only show users in shared client groups
            if count_only:
                query = """
                SELECT COUNT(DISTINCT u.user_id) as user_count
                FROM users u
                INNER JOIN client_group_users cgu1 ON u.user_id = cgu1.user_id
                INNER JOIN client_group_users cgu2 ON cgu1.client_group_id = cgu2.client_group_id
                WHERE cgu2.user_id = %s
                """
            else:
                query = """
                SELECT DISTINCT u.* 
                FROM users u
                INNER JOIN client_group_users cgu1 ON u.user_id = cgu1.user_id
                INNER JOIN client_group_users cgu2 ON cgu1.client_group_id = cgu2.client_group_id
                WHERE cgu2.user_id = %s
                """
            params = [requesting_user_id]
        else:
            # No access control - allow system-level lookups (login/onboarding)
            if count_only:
                query = "SELECT COUNT(*) as user_count FROM users WHERE 1=1"
            else:
                query = "SELECT * FROM users WHERE 1=1"
            params = []

        # Add specific filters if provided
        if user_id:
            if client_group_id or requesting_user_id:
                query += " AND u.user_id = %s"
            else:
                query += " AND user_id = %s"
            params.append(user_id)

        if sub:
            if client_group_id or requesting_user_id:
                query += " AND u.sub = %s"
            else:
                query += " AND sub = %s"
            params.append(sub)

        if email:
            if email.endswith("%"):
                if client_group_id or requesting_user_id:
                    query += " AND u.email LIKE %s"
                else:
                    query += " AND email LIKE %s"
            else:
                if client_group_id or requesting_user_id:
                    query += " AND u.email = %s"
                else:
                    query += " AND email = %s"
            params.append(email)

        with conn.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

            if count_only:
                # Return just the count as an integer
                count = rows[0]['user_count'] if rows else 0
                return {
                    "statusCode": 200,
                    "headers": cors_headers,
                    "body": json.dumps(count)
                }
            else:
                # Return the full user records
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
