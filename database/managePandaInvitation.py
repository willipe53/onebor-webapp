import boto3
import json
import pymysql
import os
import uuid
from datetime import datetime

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

        action = body.get("action")
        expires_at = body.get("expires_at")
        client_group_id = body.get("client_group_id")
        code = body.get("code")  # For get and redeem actions

        if not action:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "action is required"})
            }

        secrets = get_db_secret()
        conn = get_connection(secrets)

        with conn.cursor() as cursor:
            if action == "get":
                # Get invitations by client_group_id or code
                if not client_group_id and not code:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "client_group_id or code is required for get action"})
                    }

                query = "SELECT * FROM invitations WHERE 1=1"
                params = []

                if client_group_id:
                    query += " AND client_group_id = %s"
                    params.append(client_group_id)

                if code:
                    query += " AND code = %s"
                    params.append(code)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(rows, default=str)
                }

            elif action == "create":
                # Create new invitation
                if not expires_at or not client_group_id:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "expires_at and client_group_id are required for create action"})
                    }

                # Parse expires_at to ensure it's in correct format
                try:
                    if isinstance(expires_at, str):
                        # Try to parse the datetime string
                        datetime.fromisoformat(
                            expires_at.replace('Z', '+00:00'))
                except ValueError:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "expires_at must be a valid ISO datetime string"})
                    }

                # Let database auto-generate invitation_id and code
                query = """
                    INSERT INTO invitations (expires_at, client_group_id)
                    VALUES (%s, %s)
                """
                params = [expires_at, client_group_id]

                cursor.execute(query, params)
                invitation_id = cursor.lastrowid
                conn.commit()

                # Get the generated code
                cursor.execute(
                    "SELECT code FROM invitations WHERE invitation_id = %s", (invitation_id,))
                result = cursor.fetchone()
                generated_code = result['code'] if result else None

                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "success": True,
                        "invitation_id": invitation_id,
                        "code": generated_code
                    })
                }

            elif action == "redeem":
                # Redeem invitation by code (set expires_at to now)
                if not code:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "code is required for redeem action"})
                    }

                # Check if invitation exists and is not already expired
                cursor.execute("""
                    SELECT * FROM invitations 
                    WHERE code = %s AND expires_at > NOW()
                """, (code,))
                invitation = cursor.fetchone()

                if not invitation:
                    return {
                        "statusCode": 404,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Invalid or expired invitation code"})
                    }

                # Mark as redeemed by setting expires_at to now
                cursor.execute("""
                    UPDATE invitations 
                    SET expires_at = NOW() 
                    WHERE code = %s
                """, (code,))
                conn.commit()

                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "success": True,
                        "invitation_id": invitation['invitation_id'],
                        "client_group_id": invitation['client_group_id']
                    })
                }

            else:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid action. Must be 'get', 'create', or 'redeem'"})
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
