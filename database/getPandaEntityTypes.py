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
        connect_timeout=5
    )


def lambda_handler(event, context):
    conn = None
    try:
        secrets = get_db_secret()
        conn = get_connection(secrets)
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM entity_types")
            rows = cursor.fetchall()
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(rows, default=str)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()
