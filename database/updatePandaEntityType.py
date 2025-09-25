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
        connect_timeout=5,
        cursorclass=pymysql.cursors.DictCursor
    )


def lambda_handler(event, context):
    # CORS headers for all responses
    cors_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "https://app.onebor.com",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Credentials": "true"
    }

    # Handle preflight OPTIONS requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": ""
        }

    conn = None
    try:
        # Parse incoming request body
        body = event.get("body")
        if body and isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = event  # allow direct testing in Lambda console

        # Extract parameters
        user_id = body.get("user_id")
        entity_type_id = body.get("entity_type_id")
        name = body.get("name")
        attributes_schema = body.get("attributes_schema")
        short_label = body.get("short_label")
        label_color = body.get("label_color")
        entity_category = body.get("entity_category")

        # Validate required fields
        if not user_id:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "user_id is required for data protection"})
            }

        # Debug logging
        print(f"DEBUG: entity_type_id={entity_type_id}, name={name}")
        print(f"DEBUG: short_label={short_label}, label_color={label_color}")
        print(f"DEBUG: entity_category={entity_category}")
        print(f"DEBUG: attributes_schema={attributes_schema}")

        # Get database connection
        secrets = get_db_secret()
        conn = get_connection(secrets)

        with conn.cursor() as cursor:
            if entity_type_id:
                # Update existing entity type
                updates = []
                params = []

                if name is not None:
                    updates.append("name = %s")
                    params.append(name)
                if attributes_schema is not None:
                    # Convert attributes_schema to JSON string if it's a dict
                    if isinstance(attributes_schema, dict):
                        attributes_schema = json.dumps(attributes_schema)
                    updates.append("attributes_schema = %s")
                    params.append(attributes_schema)
                if short_label is not None:
                    updates.append("short_label = %s")
                    params.append(short_label)
                if label_color is not None:
                    updates.append("label_color = %s")
                    params.append(label_color)
                if entity_category is not None:
                    updates.append("entity_category = %s")
                    params.append(entity_category)

                if not updates:
                    return {
                        "statusCode": 400,
                        "headers": cors_headers,
                        "body": json.dumps({"error": "No fields to update"})
                    }

                # Add entity_type_id to params
                params.append(entity_type_id)

                sql = f"UPDATE entity_types SET {', '.join(updates)} WHERE entity_type_id = %s"
                cursor.execute(sql, params)

                if cursor.rowcount == 0:
                    return {
                        "statusCode": 404,
                        "headers": cors_headers,
                        "body": json.dumps({"error": "Entity type not found"})
                    }

                conn.commit()

                return {
                    "statusCode": 200,
                    "headers": cors_headers,
                    "body": json.dumps({
                        "success": True,
                        "message": "Entity type updated successfully",
                        "entity_type_id": entity_type_id
                    })
                }
            else:
                # Create new entity type
                if not name:
                    return {
                        "statusCode": 400,
                        "headers": cors_headers,
                        "body": json.dumps({"error": "name is required for new entity types"})
                    }

                if not attributes_schema:
                    return {
                        "statusCode": 400,
                        "headers": cors_headers,
                        "body": json.dumps({"error": "attributes_schema is required for new entity types"})
                    }

                # Convert attributes_schema to JSON string if it's a dict
                if isinstance(attributes_schema, dict):
                    attributes_schema = json.dumps(attributes_schema)

                sql = """
                    INSERT INTO entity_types (name, attributes_schema, short_label, label_color, entity_category)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (name, attributes_schema,
                               short_label, label_color, entity_category))
                new_entity_type_id = cursor.lastrowid

                conn.commit()

                return {
                    "statusCode": 200,
                    "headers": cors_headers,
                    "body": json.dumps({
                        "success": True,
                        "message": "Entity type created successfully",
                        "entity_type_id": new_entity_type_id
                    })
                }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"})
        }
    finally:
        if conn:
            conn.close()


# For local testing
if __name__ == "__main__":
    # Test cases for local development
    test_events = [
        {
            "entity_type_id": 1,
            "name": "Updated Test Type",
            "attributes_schema": {"type": "object", "properties": {"test": {"type": "string"}}},
            "short_label": "UTT",
            "label_color": "ff5722",
            "entity_category": "Test Category"
        },
        {
            "name": "New Test Type",
            "attributes_schema": {"type": "object", "properties": {"new_field": {"type": "string"}}},
            "short_label": "NTT",
            "label_color": "2196f3",
            "entity_category": "New Category"
        }
    ]

    for test_event in test_events:
        print(f"\nTesting: {test_event}")
        result = lambda_handler(test_event, None)
        print(f"Result: {result}")
