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

        # Read the SQL file
        with open('create_client_group_tables.sql', 'r') as f:
            sql_script = f.read()

        # Split by semicolon and execute each statement
        statements = [stmt.strip()
                      for stmt in sql_script.split(';') if stmt.strip()]

        with conn.cursor() as cursor:
            for statement in statements:
                if statement:
                    print(f"Executing: {statement[:100]}...")
                    cursor.execute(statement)

            conn.commit()

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Client group tables created successfully"})
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
