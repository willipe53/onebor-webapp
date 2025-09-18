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
    conn = None
    try:
        body = event.get("body")
        if body and isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = event

        user_id = body.get("user_id")
        email = body.get("email")
        name = body.get("name")
        preferences = body.get("preferences")
        primary_client_group_id = body.get("primary_client_group_id")

        s = get_db_secret()
        conn = get_connection(s)

        # Check if user exists in database
        user_exists = False
        if user_id:
            with conn.cursor() as check_cursor:
                check_cursor.execute(
                    "SELECT COUNT(*) as count FROM users WHERE user_id = %s", (user_id,))
                result = check_cursor.fetchone()
                user_exists = result['count'] > 0

        # Build dynamic query to handle optional fields
        if user_exists:
            # Update existing user
            updates = []
            params = []

            if email is not None:
                updates.append("email = %s")
                params.append(email)
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
            if primary_client_group_id is not None:
                updates.append("primary_client_group_id = %s")
                params.append(primary_client_group_id)

            if not updates:
                return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "No fields to update"})}

            q = f"UPDATE users SET {', '.join(updates)} WHERE user_id = %s"
            params.append(user_id)
        else:
            # Insert new user (user_id, email, name are required for new users)
            if not email or not name:
                return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "email and name are required for new users"})}

            # Generate new user_id if not provided, otherwise use the provided one
            if not user_id:
                import uuid
                user_id = str(uuid.uuid4())

            q = """INSERT INTO users (user_id, email, name, preferences, primary_client_group_id) 
                   VALUES (%s, %s, %s, %s, %s)"""

            preferences_json = None
            if preferences is not None:
                if isinstance(preferences, (dict, list)):
                    preferences_json = json.dumps(preferences)
                else:
                    preferences_json = preferences

            params = [user_id, email, name,
                      preferences_json, primary_client_group_id]

        with conn.cursor() as c:
            try:
                c.execute(q, params)
                rows_affected = c.rowcount
                conn.commit()

                # Return the user_id for reference
                return {"statusCode": 200, "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"success": True, "user_id": user_id})}
            except pymysql.IntegrityError as ie:
                # Handle duplicate key or other integrity constraint violations
                error_msg = str(ie)
                if "Duplicate entry" in error_msg and "PRIMARY" in error_msg:
                    # User already exists - this is actually OK for our use case
                    # Just return success with the existing user_id
                    return {"statusCode": 200, "headers": {"Content-Type": "application/json"},
                            "body": json.dumps({"success": True, "user_id": user_id, "note": "User already exists"})}
                else:
                    # Other integrity constraint violations
                    return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                            "body": json.dumps({"error": f"Database constraint violation: {error_msg}"})}
    except Exception as e:
        return {"statusCode": 500, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": str(e)})}
    finally:
        if conn:
            conn.close()
