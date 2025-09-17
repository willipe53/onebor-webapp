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

        record_id = body.get("record_id")
        record_type = body.get("record_type")

        if not record_id or not record_type:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing required fields: record_id and record_type"})
            }

        # Map record types to table names and primary key columns
        table_mapping = {
            "Client Group": {"table": "client_groups", "pk": "client_group_id"},
            "User": {"table": "users", "pk": "user_id"},
            "Entity": {"table": "entities", "pk": "entity_id"},
            "Entity Type": {"table": "entity_types", "pk": "entity_type_id"}
        }

        if record_type not in table_mapping:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "error": f"Invalid record_type. Valid types are: {', '.join(table_mapping.keys())}"
                })
            }

        table_info = table_mapping[record_type]
        table_name = table_info["table"]
        primary_key = table_info["pk"]

        secrets = get_db_secret()
        conn = get_connection(secrets)

        with conn.cursor() as cursor:
            # First, check if the record exists
            check_sql = f"SELECT {primary_key} FROM {table_name} WHERE {primary_key} = %s"
            cursor.execute(check_sql, (record_id,))
            existing_record = cursor.fetchone()

            if not existing_record:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "error": f"{record_type} with ID {record_id} not found"
                    })
                }

            # Check for referential integrity constraints before deletion
            referential_checks = []

            if record_type == "Client Group":
                # Check if any users are assigned to this client group
                cursor.execute(
                    "SELECT COUNT(*) as count FROM client_group_users WHERE client_group_id = %s", (record_id,))
                user_count = cursor.fetchone()["count"]
                if user_count > 0:
                    referential_checks.append(
                        f"{user_count} user(s) are assigned to this client group")

            elif record_type == "User":
                # Check if user is assigned to any client groups
                cursor.execute(
                    "SELECT COUNT(*) as count FROM client_group_users WHERE user_id = %s", (record_id,))
                group_count = cursor.fetchone()["count"]
                if group_count > 0:
                    referential_checks.append(
                        f"User is assigned to {group_count} client group(s)")

            elif record_type == "Entity Type":
                # Check if any entities use this entity type
                cursor.execute(
                    "SELECT COUNT(*) as count FROM entities WHERE entity_type_id = %s", (record_id,))
                entity_count = cursor.fetchone()["count"]
                if entity_count > 0:
                    referential_checks.append(
                        f"{entity_count} entity/entities use this entity type")

            elif record_type == "Entity":
                # Check if any other entities have this as their parent
                cursor.execute(
                    "SELECT COUNT(*) as count FROM entities WHERE parent_entity_id = %s", (record_id,))
                child_count = cursor.fetchone()["count"]
                if child_count > 0:
                    referential_checks.append(
                        f"{child_count} child entity/entities reference this entity as parent")

            # If there are referential integrity violations, return error
            if referential_checks:
                return {
                    "statusCode": 409,  # Conflict
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "error": "Cannot delete record due to referential integrity constraints",
                        "details": referential_checks
                    })
                }

            # Perform the deletion
            delete_sql = f"DELETE FROM {table_name} WHERE {primary_key} = %s"
            cursor.execute(delete_sql, (record_id,))
            conn.commit()

            # Verify deletion was successful
            if cursor.rowcount == 0:
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Failed to delete record"})
                }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "message": f"{record_type} with ID {record_id} has been successfully deleted",
                "deleted_record": {
                    "record_type": record_type,
                    "record_id": record_id,
                    "table": table_name
                }
            })
        }

    except pymysql.err.IntegrityError as e:
        # This catches any remaining foreign key constraint violations
        return {
            "statusCode": 409,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Cannot delete record due to database referential integrity constraints",
                "details": str(e)
            })
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
