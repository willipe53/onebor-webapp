import boto3
import json
import pymysql
import os
SECRET_ARN = os.environ["SECRET_ARN"]


def get_db_secret(): return json.loads(boto3.client(
    "secretsmanager").get_secret_value(SecretId=SECRET_ARN)["SecretString"])


def get_connection(s): return pymysql.connect(host=s["DB_HOST"], user=s["DB_USER"], password=s["DB_PASS"],
                                              database=s["DATABASE"], connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)


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
        body = event.get("body")
        if body and isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = event

        client_group_id = body.get("client_group_id")
        # Array of entity_ids that should be in the group
        desired_entity_ids = body.get("entity_ids", [])

        print(
            f"DEBUG: Received parameters - client_group_id: {client_group_id}, desired entities count: {len(desired_entity_ids)}")
        print(f"DEBUG: Desired entity_ids: {desired_entity_ids}")

        if not client_group_id:
            return {"statusCode": 400, "headers": cors_headers,
                    "body": json.dumps({"error": "client_group_id is required"})}

        if not isinstance(desired_entity_ids, list):
            return {"statusCode": 400, "headers": cors_headers,
                    "body": json.dumps({"error": "entity_ids must be an array"})}

        s = get_db_secret()
        conn = get_connection(s)

        # Start transaction
        conn.begin()

        try:
            with conn.cursor() as c:
                # Get current entity_ids for this client group
                c.execute("SELECT entity_id FROM client_group_entities WHERE client_group_id = %s", [
                          client_group_id])
                current_results = c.fetchall()
                current_entity_ids = set(row['entity_id']
                                         for row in current_results)

                print(
                    f"DEBUG: Current entity_ids in group: {list(current_entity_ids)}")

                # Convert desired list to set for efficient comparison
                desired_entity_ids_set = set(desired_entity_ids)

                # Calculate what needs to be added and removed
                to_add = desired_entity_ids_set - current_entity_ids
                to_remove = current_entity_ids - desired_entity_ids_set

                print(f"DEBUG: Entities to add: {list(to_add)}")
                print(f"DEBUG: Entities to remove: {list(to_remove)}")

                added_count = 0
                removed_count = 0

                # Add new entities
                if to_add:
                    insert_query = "INSERT INTO client_group_entities (client_group_id, entity_id) VALUES (%s, %s)"
                    for entity_id in to_add:
                        c.execute(insert_query, [client_group_id, entity_id])
                        added_count += c.rowcount
                        print(
                            f"DEBUG: Added entity {entity_id} to client group {client_group_id}")

                # Remove entities that should no longer be in the group
                if to_remove:
                    delete_query = "DELETE FROM client_group_entities WHERE client_group_id = %s AND entity_id = %s"
                    for entity_id in to_remove:
                        c.execute(delete_query, [client_group_id, entity_id])
                        removed_count += c.rowcount
                        print(
                            f"DEBUG: Removed entity {entity_id} from client group {client_group_id}")

                # Commit all changes at once
                conn.commit()

                print(
                    f"DEBUG: Transaction completed successfully - added: {added_count}, removed: {removed_count}")

                result = {
                    "success": True,
                    "added_count": added_count,
                    "removed_count": removed_count,
                    "current_entity_ids": list(current_entity_ids),
                    "desired_entity_ids": desired_entity_ids,
                    "entities_added": list(to_add),
                    "entities_removed": list(to_remove)
                }

                return {"statusCode": 200, "headers": cors_headers, "body": json.dumps(result)}

        except Exception as e:
            print(f"ERROR: Transaction failed, rolling back: {str(e)}")
            conn.rollback()
            raise e

    except Exception as e:
        print(f"ERROR: Lambda execution failed: {str(e)}")
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
    finally:
        if conn:
            conn.close()
