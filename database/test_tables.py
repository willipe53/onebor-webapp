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

        with conn.cursor() as cursor:
            # Check what tables exist
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

            # Check if client_group_entities and client_group_users exist
            table_names = [list(table.values())[0] for table in tables]

            result = {
                "all_tables": table_names,
                "client_group_entities_exists": "client_group_entities" in table_names,
                "client_group_users_exists": "client_group_users" in table_names,
                "users_exists": "users" in table_names,
                "client_groups_exists": "client_groups" in table_names,
                "entities_exists": "entities" in table_names
            }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result)
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
