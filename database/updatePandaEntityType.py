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
        short_label = body.get("short_label")
        label_color = body.get("label_color")

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
                # Build dynamic SQL based on provided fields
                set_fields = ["name = %s", "attributes_schema = %s"]
                params = [name, json.dumps(attributes_schema)]

                if short_label is not None:
                    set_fields.append("short_label = %s")
                    params.append(short_label)

                if label_color is not None:
                    set_fields.append("label_color = %s")
                    params.append(label_color)

                params.append(entity_type_id)  # WHERE clause parameter

                sql = f"""
                    UPDATE entity_types
                    SET {', '.join(set_fields)}
                    WHERE entity_type_id = %s
                """
                cursor.execute(sql, params)
                conn.commit()
                result = {"message": "Entity type updated",
                          "entity_type_id": entity_type_id}
            else:
                # Insert new record
                fields = ["name", "attributes_schema"]
                values = [name, json.dumps(attributes_schema)]
                placeholders = ["%s", "%s"]

                if short_label is not None:
                    fields.append("short_label")
                    values.append(short_label)
                    placeholders.append("%s")

                if label_color is not None:
                    fields.append("label_color")
                    values.append(label_color)
                    placeholders.append("%s")

                sql = f"""
                    INSERT INTO entity_types ({', '.join(fields)})
                    VALUES ({', '.join(placeholders)})
                """
                cursor.execute(sql, values)
                conn.commit()
                new_id = cursor.lastrowid
                result = {"message": "Entity type created",
                          "entity_type_id": new_id}

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
