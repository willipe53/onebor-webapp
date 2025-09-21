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

        with conn.cursor() as c:
            c.execute(q, params)
            new_client_group_id = c.lastrowid

            # If this is a new client group, automatically add the creator as a member
            if not client_group_id and user_id:
                membership_q = "INSERT INTO client_group_users (client_group_id, user_id) VALUES (%s, %s)"
                c.execute(membership_q, [new_client_group_id, user_id])

            conn.commit()

            # Return the client_group_id for reference
            result_id = client_group_id or new_client_group_id
            return {"statusCode": 200, "headers": cors_headers,
                    "body": json.dumps({"success": True, "id": result_id})}
    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers, "body": json.dumps({"error": str(e)})}
    finally:
        if conn:
            conn.close()
