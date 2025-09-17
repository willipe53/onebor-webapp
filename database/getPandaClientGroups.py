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

        s = get_db_secret()
        conn = get_connection(s)
        params = []

        if user_id:
            query = """SELECT cg.client_group_id,cg.name
                     FROM client_groups cg
                     JOIN client_group_users cgu ON cg.client_group_id=cgu.client_group_id
                     WHERE cgu.user_id=%s"""
            params = [user_id]
            if group_name:
                query += " AND cg.name " + \
                    ("LIKE %s" if group_name.endswith("%") else "= %s")
                params.append(group_name)
        else:
            query = "SELECT client_group_id,name FROM client_groups WHERE 1=1"
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
        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps(rows, default=str)}
    except Exception as e:
        return {"statusCode": 500, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": str(e)})}
    finally:
        if conn:
            conn.close()
