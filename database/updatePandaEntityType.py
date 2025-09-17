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
        # Parse incoming request
        body = event.get("body")
        if body and isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = event  # allow direct testing in Lambda console

        entity_type_id = body.get("entity_type_id")
        name = body.get("name")
        attributes_schema = body.get("attributes_schema")

        if not name or attributes_schema is None:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required fields: name, attributes_schema"})
            }

        secrets = get_db_secret()
        conn = get_connection(secrets)

        with conn.cursor() as cursor:
            if entity_type_id:
                # Update existing record
                sql = """
                    UPDATE entity_types
                    SET name = %s, attributes_schema = %s
                    WHERE entity_type_id = %s
                """
                cursor.execute(sql, (name, json.dumps(attributes_schema), entity_type_id))
                conn.commit()
                result = {"message": "Entity type updated", "entity_type_id": entity_type_id}
            else:
                # Insert new record
                sql = """
                    INSERT INTO entity_types (name, attributes_schema)
                    VALUES (%s, %s)
                """
                cursor.execute(sql, (name, json.dumps(attributes_schema)))
                conn.commit()
                new_id = cursor.lastrowid
                result = {"message": "Entity type created", "entity_type_id": new_id}

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
