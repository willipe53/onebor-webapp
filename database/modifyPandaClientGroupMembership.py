import boto3
import json
import pymysql
import os
SECRET_ARN = os.environ["SECRET_ARN"]


def get_db_secret(): return json.loads(boto3.client(
    "secretsmanager").get_secret_value(SecretId=SECRET_ARN)["SecretString"])


def get_connection(s): return pymysql.connect(host=s["DB_HOST"], user=s["DB_USER"], password=s["DB_PASS"],
                                              database=s["DATABASE"], connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)


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

        client_group_id, user_id, action = body.get("client_group_id"), body.get(
            "user_id"), str(body.get("add_or_remove", "")).lower()

        print(
            f"DEBUG: Received parameters - client_group_id: {client_group_id}, user_id: {user_id}, action: {action}")

        s = get_db_secret()
        conn = get_connection(s)

        if action in ["add", "insert"]:
            q = "INSERT IGNORE INTO client_group_users (client_group_id,user_id) VALUES (%s,%s)"
            params = [client_group_id, user_id]
        elif action in ["del", "delete", "remove"]:
            q = "DELETE FROM client_group_users WHERE client_group_id=%s AND user_id=%s"
            params = [client_group_id, user_id]
        else:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Invalid add_or_remove value"})}

        print(f"DEBUG: Executing query: {q} with params: {params}")

        with conn.cursor() as c:
            c.execute(q, params)
            rows_affected = c.rowcount
            conn.commit()

        print(
            f"DEBUG: Query executed successfully, rows affected: {rows_affected}")

        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps({"success": True, "rows_affected": rows_affected})}
    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
    finally:
        if conn:
            conn.close()
