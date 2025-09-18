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
        secrets = get_db_secret()
        conn = get_connection(secrets)

        result = {}

        with conn.cursor() as cursor:
            # Check entities
            cursor.execute("SELECT COUNT(*) as count FROM entities")
            result["entities_count"] = cursor.fetchone()["count"]

            # Check client groups
            cursor.execute("SELECT COUNT(*) as count FROM client_groups")
            result["client_groups_count"] = cursor.fetchone()["count"]

            # Check users
            cursor.execute("SELECT COUNT(*) as count FROM users")
            result["users_count"] = cursor.fetchone()["count"]

            # Check client_group_users
            cursor.execute("SELECT COUNT(*) as count FROM client_group_users")
            result["client_group_users_count"] = cursor.fetchone()["count"]

            # Check client_group_entities
            cursor.execute(
                "SELECT COUNT(*) as count FROM client_group_entities")
            result["client_group_entities_count"] = cursor.fetchone()["count"]

            # Get sample data
            cursor.execute("SELECT * FROM entities LIMIT 3")
            result["sample_entities"] = cursor.fetchall()

            cursor.execute("SELECT * FROM client_groups LIMIT 3")
            result["sample_client_groups"] = cursor.fetchall()

            cursor.execute("SELECT * FROM users LIMIT 3")
            result["sample_users"] = cursor.fetchall()

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result, default=str)
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
