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
        name = body.get("name")
        preferences = body.get("preferences")
        # For new groups, need to add creator as member
        user_id = body.get("user_id")
        print(f"DEBUG: Extracted user_id: {user_id} (type: {type(user_id)})")
        if not user_id:
            print("DEBUG: user_id is missing or falsy")

        s = get_db_secret()
        conn = get_connection(s)

        if client_group_id:
            # Update existing client group
            updates = []
            params = []

            if name is not None:
                updates.append("name = %s")
                params.append(name)
            if preferences is not None:
                updates.append("preferences = %s")
                # Handle JSON serialization
                if isinstance(preferences, (dict, list)):
                    params.append(json.dumps(preferences))
                else:
                    params.append(preferences)

            if not updates:
                return {"statusCode": 400, "headers": cors_headers,
                        "body": json.dumps({"error": "No fields to update"})}

            # Always update the updated_user_id field
            updates.append("updated_user_id = %s")
            params.append(user_id)
            print(f"DEBUG: Adding updated_user_id = {user_id} to update")

            q = f"UPDATE client_groups SET {', '.join(updates)} WHERE client_group_id = %s"
            params.append(client_group_id)
        else:
            # Insert new client group (name and user_id are required)
            if not name:
                return {"statusCode": 400, "headers": cors_headers,
                        "body": json.dumps({"error": "name is required for new client groups"})}

            if not user_id:
                return {"statusCode": 400, "headers": cors_headers,
                        "body": json.dumps({"error": "user_id is required for new client groups"})}

            q = "INSERT INTO client_groups (name, preferences) VALUES (%s, %s)"

            preferences_json = None
            if preferences is not None:
                if isinstance(preferences, (dict, list)):
                    preferences_json = json.dumps(preferences)
                else:
                    preferences_json = preferences

            params = [name, preferences_json]

        print(f"DEBUG: Executing SQL: {q}")
        print(f"DEBUG: Parameters: {params}")

        with conn.cursor() as c:
            c.execute(q, params)

            if client_group_id:
                # This was an UPDATE operation
                rows_affected = c.rowcount
                print(f"DEBUG: Update affected {rows_affected} rows")

                # Check what was actually updated
                c.execute(
                    "SELECT client_group_id, updated_user_id, update_date FROM client_groups WHERE client_group_id = %s", (client_group_id,))
                result = c.fetchone()
                if result:
                    print(
                        f"DEBUG: After update - client_group_id: {result['client_group_id']}, updated_user_id: {result['updated_user_id']}, update_date: {result['update_date']}")
                else:
                    print("DEBUG: No result found after update")

                new_client_group_id = client_group_id
            else:
                # This was an INSERT operation
                new_client_group_id = c.lastrowid
                print(
                    f"DEBUG: Inserted new client group with ID: {new_client_group_id}")

            # If this is a new client group, automatically add the creator as a member
            if not client_group_id and user_id:
                membership_q = "INSERT INTO client_group_users (client_group_id, user_id) VALUES (%s, %s)"
                c.execute(membership_q, [new_client_group_id, user_id])

            conn.commit()
            print(f"DEBUG: Transaction committed")

            # Return the client_group_id for reference
            result_id = client_group_id or new_client_group_id
            return {"statusCode": 200, "headers": cors_headers,
                    "body": json.dumps({"success": True, "id": result_id})}
    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
    finally:
        if conn:
            conn.close()
