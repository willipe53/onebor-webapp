import boto3
import json
import pymysql
import os
SECRET_ARN = os.environ["SECRET_ARN"]


def get_db_secret():
    return json.loads(boto3.client("secretsmanager").get_secret_value(SecretId=SECRET_ARN)["SecretString"])


def get_connection(s): return pymysql.connect(
    host=s["DB_HOST"], user=s["DB_USER"], password=s["DB_PASS"], database=s["DATABASE"],
    connect_timeout=5, cursorclass=pymysql.cursors.DictCursor
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

        client_group_id = body.get("client_group_id")
        user_id = body.get("user_id")

        if not client_group_id and not user_id:
            return {"statusCode": 400, "headers": cors_headers, "body": json.dumps({"error": "Must pass client_group_id or user_id"})}

        s = get_db_secret()
        conn = get_connection(s)
        params = []
        if client_group_id and user_id:
            q = """SELECT DISTINCT e.entity_id FROM entities e
                 JOIN client_group_entities cge ON e.entity_id=cge.entity_id
                 JOIN client_group_users cgu ON cge.client_group_id=cgu.client_group_id
                 WHERE cge.client_group_id=%s AND cgu.user_id=%s"""
            params = [client_group_id, user_id]
        elif client_group_id:
            q = """SELECT e.entity_id FROM entities e
                 JOIN client_group_entities cge ON e.entity_id=cge.entity_id
                 WHERE cge.client_group_id=%s"""
            params = [client_group_id]
        else:
            q = """SELECT DISTINCT e.entity_id FROM entities e
                 JOIN client_group_entities cge ON e.entity_id=cge.entity_id
                 JOIN client_group_users cgu ON cge.client_group_id=cgu.client_group_id
                 WHERE cgu.user_id=%s"""
            params = [user_id]

        with conn.cursor() as c:
            c.execute(q, params)
            rows = c.fetchall()
        return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(rows, default=str)}
    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
    finally:
        if conn:
            conn.close()
