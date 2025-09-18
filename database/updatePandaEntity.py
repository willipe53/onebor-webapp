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

        # Extract user_id from the request (should be passed from frontend)
        user_id = body.get("user_id")
        if not user_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "user_id is required for data protection"})
            }

        entity_id = body.get("entity_id")
        name = body.get("name")
        entity_type_id = body.get("entity_type_id")
        parent_entity_id = body.get("parent_entity_id")
        attributes = body.get("attributes")

        # Debug logging
        print(
            f"DEBUG: user_id={user_id}, entity_id={entity_id}, name={name}, entity_type_id={entity_type_id}")
        print(
            f"DEBUG: parent_entity_id={parent_entity_id}, attributes={attributes}")

        secrets = get_db_secret()
        conn = get_connection(secrets)

        with conn.cursor() as cursor:
            if entity_id:
                # --- UPDATE existing record ---
                # First check if entity exists AND user has access to it
                cursor.execute("""
                    SELECT e.* FROM entities e
                    JOIN client_group_entities cge ON e.entity_id = cge.entity_id
                    JOIN client_group_users cgu ON cge.client_group_id = cgu.client_group_id
                    WHERE e.entity_id = %s AND cgu.user_id = %s
                """, (entity_id, user_id))
                existing_entity = cursor.fetchone()
                print(f"DEBUG: Existing entity with access: {existing_entity}")

                if not existing_entity:
                    return {
                        "statusCode": 404,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": f"Entity with ID {entity_id} not found or access denied"})
                    }
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
                    # Replace entire attributes JSON instead of using JSON_SET
                    # This avoids JSON path issues with special characters in keys
                    updates.append("attributes = %s")
                    # Check if attributes is already a JSON string
                    if isinstance(attributes, str):
                        # It's already a JSON string, use as-is
                        params.append(attributes)
                        print(f"DEBUG: attributes is string: {attributes}")
                    else:
                        # It's an object, convert to JSON string
                        json_string = json.dumps(attributes)
                        params.append(json_string)
                        print(
                            f"DEBUG: attributes converted to JSON: {json_string}")

                if not updates:
                    return {"statusCode": 400, "body": json.dumps({"error": "No fields to update"})}

                sql = f"UPDATE entities SET {', '.join(updates)} WHERE entity_id = %s"
                params.append(entity_id)

                # Debug logging for SQL execution
                print(f"DEBUG: Executing SQL: {sql}")
                print(f"DEBUG: Parameters: {params}")

                cursor.execute(sql, params)
                rows_affected = cursor.rowcount
                conn.commit()

                print(f"DEBUG: Rows affected: {rows_affected}")

                if rows_affected == 0:
                    print(
                        f"WARNING: No rows updated for entity_id={entity_id}")
                    return {"statusCode": 404, "body": json.dumps({"error": f"Entity with ID {entity_id} not found or no changes made"})}

                result = {"message": "Entity updated",
                          "entity_id": entity_id, "rows_affected": rows_affected}

            else:
                # --- INSERT new record ---
                # For new entities, we need a client_group_id to associate the entity with
                client_group_id = body.get("client_group_id")
                if not client_group_id:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "client_group_id is required for creating new entities"})
                    }

                # Validate that the user belongs to the specified client group
                cursor.execute("""
                    SELECT COUNT(*) as count FROM client_group_users 
                    WHERE client_group_id = %s AND user_id = %s
                """, (client_group_id, user_id))
                access_check = cursor.fetchone()

                if access_check['count'] == 0:
                    return {
                        "statusCode": 403,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Access denied: User does not belong to the specified client group"})
                    }

                sql = """
                    INSERT INTO entities (name, entity_type_id, parent_entity_id, attributes)
                    VALUES (%s, %s, %s, %s)
                """
                # Handle attributes for INSERT
                attributes_value = None
                if attributes:
                    if isinstance(attributes, str):
                        attributes_value = attributes
                        print(
                            f"DEBUG: INSERT attributes is string: {attributes}")
                    else:
                        attributes_value = json.dumps(attributes)
                        print(
                            f"DEBUG: INSERT attributes converted to JSON: {attributes_value}")

                cursor.execute(
                    sql,
                    (
                        name,
                        entity_type_id,
                        parent_entity_id,
                        attributes_value,
                    ),
                )
                conn.commit()
                new_id = cursor.lastrowid

                # Associate the new entity with the client group
                cursor.execute("""
                    INSERT INTO client_group_entities (client_group_id, entity_id)
                    VALUES (%s, %s)
                """, (client_group_id, new_id))
                conn.commit()

                result = {"message": "Entity created", "entity_id": new_id}

        return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": json.dumps(result)}

    except Exception as e:
        return {"statusCode": 500, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": str(e)})}
    finally:
        if conn:
            conn.close()
