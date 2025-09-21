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
        group_name = body.get("group_name")
        count_only = body.get("count_only", False)  # Default to False

        s = get_db_secret()
        conn = get_connection(s)
        params = []

        if user_id:
            if count_only:
                query = """SELECT COUNT(DISTINCT cg.client_group_id) as client_group_count
                         FROM client_groups cg
                         JOIN client_group_users cgu ON cg.client_group_id=cgu.client_group_id
                         WHERE cgu.user_id=%s"""
            else:
                query = """SELECT cg.client_group_id,cg.name,cg.preferences
                         FROM client_groups cg
                         JOIN client_group_users cgu ON cg.client_group_id=cgu.client_group_id
                         WHERE cgu.user_id=%s"""
            params = [user_id]
            if group_name:
                query += " AND cg.name " + \
                    ("LIKE %s" if group_name.endswith("%") else "= %s")
                params.append(group_name)
        else:
            if count_only:
                query = "SELECT COUNT(*) as client_group_count FROM client_groups WHERE 1=1"
            else:
                query = "SELECT client_group_id,name,preferences FROM client_groups WHERE 1=1"
            if client_group_id:
                query += " AND client_group_id=%s"
                params.append(client_group_id)
            if group_name:
                query += " AND name " + \
                    ("LIKE %s" if group_name.endswith("%") else "= %s")
                params.append(group_name)

        with conn.cursor() as c:
            c.execute(query, params)
            rows = c.fetchall()

            if count_only:
                # Return just the count as an integer
                count = rows[0]['client_group_count'] if rows else 0
                return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(count)}
            else:
                # Return the full client group records
                return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(rows, default=str)}
    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
    finally:
        if conn:
            conn.close()
