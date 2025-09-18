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

        # Extract user_id from the request (should be passed from frontend)
        user_id = body.get("user_id")
        if not user_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "user_id is required for data protection"})
            }

        print(f"DEBUG: Received user_id: {user_id}")

        entity_id = body.get("entity_id")
        name = body.get("name")
        entity_type_id = body.get("entity_type_id")
        parent_entity_id = body.get("parent_entity_id")

        secrets = get_db_secret()
        conn = get_connection(secrets)

        # Base query with security filtering - only show entities the user has access to
        query = """
            SELECT DISTINCT e.* FROM entities e
            JOIN client_group_entities cge ON e.entity_id = cge.entity_id
            JOIN client_group_users cgu ON cge.client_group_id = cgu.client_group_id
            WHERE cgu.user_id = %s
        """
        params = [user_id]

        print(f"DEBUG: Executing query with user_id: {user_id}")
        print(f"DEBUG: Query: {query}")
        print(f"DEBUG: Params: {params}")

        # Add additional filters
        if entity_id:
            query += " AND e.entity_id = %s"
            params.append(entity_id)

        elif name:
            if name.endswith("%"):  # partial match
                query += " AND e.name LIKE %s"
                params.append(name)
            else:  # exact match
                query += " AND e.name = %s"
                params.append(name)

        else:
            if entity_type_id:
                query += " AND e.entity_type_id = %s"
                params.append(entity_type_id)
            if parent_entity_id:
                query += " AND e.parent_entity_id = %s"
                params.append(parent_entity_id)

        with conn.cursor() as cursor:
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                print(
                    f"DEBUG: Query executed successfully, returned {len(rows)} rows")
            except Exception as query_error:
                print(f"DEBUG: Query execution failed: {str(query_error)}")
                raise query_error

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            # default=str for datetime compatibility
            "body": json.dumps(rows, default=str)
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
