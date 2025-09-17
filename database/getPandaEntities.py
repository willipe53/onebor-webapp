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
        # Parse incoming request body
        body = event.get("body")
        if body and isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = event  # allow direct testing in Lambda console

        entity_id = body.get("entity_id")
        name = body.get("name")
        entity_type_id = body.get("entity_type_id")
        parent_entity_id = body.get("parent_entity_id")

        secrets = get_db_secret()
        conn = get_connection(secrets)

        query = "SELECT * FROM entities"
        params = []

        if entity_id:
            query += " WHERE entity_id = %s"
            params.append(entity_id)

        elif name:
            if name.endswith("%"):  # partial match
                query += " WHERE name LIKE %s"
                params.append(name)
            else:  # exact match
                query += " WHERE name = %s"
                params.append(name)

        else:
            filters = []
            if entity_type_id:
                filters.append("entity_type_id = %s")
                params.append(entity_type_id)
            if parent_entity_id:
                filters.append("parent_entity_id = %s")
                params.append(parent_entity_id)
            if filters:
                query += " WHERE " + " AND ".join(filters)

        with conn.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(rows, default=str)  # default=str for datetime compatibility
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
