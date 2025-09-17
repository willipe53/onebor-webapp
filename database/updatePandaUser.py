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
    conn = None
    try:
        body = event.get("body")
        if body and isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = event

        user_id, email, name = body.get(
            "user_id"), body.get("email"), body.get("name")
        s = get_db_secret()
        conn = get_connection(s)

        q = """INSERT INTO users (user_id,email,name) VALUES (%s,%s,%s)
             ON DUPLICATE KEY UPDATE email=VALUES(email), name=VALUES(name)"""
        with conn.cursor() as c:
            c.execute(q, [user_id, email, name])
            conn.commit()

        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"success": True})}
    except Exception as e:
        return {"statusCode": 500, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": str(e)})}
    finally:
        if conn:
            conn.close()
