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
        # Parse input
        body = event.get("body")
        if body and isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = event

        entity_id = body.get("entity_id")
        name = body.get("name")
        entity_type_id = body.get("entity_type_id")
        parent_entity_id = body.get("parent_entity_id")
        attributes = body.get("attributes")

        secrets = get_db_secret()
        conn = get_connection(secrets)

        with conn.cursor() as cursor:
            if entity_id:
                # --- UPDATE existing record ---
                updates = []
                params = []

                if name is not None:
                    updates.append("name = %s")
                    params.append(name)
                if entity_type_id is not None:
                    updates.append("entity_type_id = %s")
                    params.append(entity_type_id)
                if parent_entity_id is not None:
                    updates.append("parent_entity_id = %s")
                    params.append(parent_entity_id)

                if attributes:
                    # Build JSON_SET with alternating path/value pairs
                    paths_and_values = []
                    for key, value in attributes.items():
                        paths_and_values.append(f"$.{key}")
                        paths_and_values.append(
                            json.dumps(value) if isinstance(value, (dict, list)) else value
                        )
                    updates.append("attributes = JSON_SET(attributes, " + ", ".join(["%s"] * len(paths_and_values)) + ")")
                    params.extend(paths_and_values)

                if not updates:
                    return {"statusCode": 400, "body": json.dumps({"error": "No fields to update"})}

                sql = f"UPDATE entities SET {', '.join(updates)} WHERE entity_id = %s"
                params.append(entity_id)
                cursor.execute(sql, params)
                conn.commit()
                result = {"message": "Entity updated", "entity_id": entity_id}

            else:
                # --- INSERT new record ---
                sql = """
                    INSERT INTO entities (name, entity_type_id, parent_entity_id, attributes)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(
                    sql,
                    (
                        name,
                        entity_type_id,
                        parent_entity_id,
                        json.dumps(attributes) if attributes else None,
                    ),
                )
                conn.commit()
                new_id = cursor.lastrowid
                result = {"message": "Entity created", "entity_id": new_id}

        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps(result)}

    except Exception as e:
        return {"statusCode": 500, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": str(e)})}
    finally:
        if conn:
            conn.close()
