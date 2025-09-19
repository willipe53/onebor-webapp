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
        sub = body.get("sub")  # Cognito user ID
        email = body.get("email")
        preferences = body.get("preferences")
        primary_client_group_id = body.get("primary_client_group_id")

        s = get_db_secret()
        conn = get_connection(s)

        # Check if user exists in database
        # Try to find user by sub first (Cognito ID), then by user_id, then by email
        user_exists = False
        existing_user_id = None

        with conn.cursor() as check_cursor:
            if sub:
                check_cursor.execute(
                    "SELECT user_id FROM users WHERE sub = %s", (sub,))
                result = check_cursor.fetchone()
                if result:
                    user_exists = True
                    existing_user_id = result['user_id']
            elif user_id:
                check_cursor.execute(
                    "SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                result = check_cursor.fetchone()
                if result:
                    user_exists = True
                    existing_user_id = result['user_id']
            elif email:
                check_cursor.execute(
                    "SELECT user_id FROM users WHERE email = %s", (email,))
                result = check_cursor.fetchone()
                if result:
                    user_exists = True
                    existing_user_id = result['user_id']

        # Build dynamic query to handle optional fields
        if user_exists:
            # Update existing user
            updates = []
            params = []

            # Require sub and email for updates
            if sub is None or email is None:
                return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "sub and email are required fields"})}
            updates.append("sub = %s")
            params.append(sub)
            updates.append("email = %s")
            params.append(email)
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
            params.append(existing_user_id)
        else:
            # Insert new user (sub and email are required for new users)
            if not sub or not email:
                return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "sub and email are required for new users"})}

            # With auto-increment user_id, we don't need to generate one
            q = """INSERT INTO users (sub, email, preferences, primary_client_group_id) 
                   VALUES (%s, %s, %s, %s)"""

            preferences_json = None
            if preferences is not None:
                if isinstance(preferences, (dict, list)):
                    preferences_json = json.dumps(preferences)
                else:
                    preferences_json = preferences

            params = [sub, email, preferences_json, primary_client_group_id]

        with conn.cursor() as c:
            try:
                c.execute(q, params)
                rows_affected = c.rowcount
                conn.commit()

                # Return the user_id for reference
                # For new users, get the auto-generated user_id
                if not user_exists:
                    new_user_id = c.lastrowid
                    user_id = new_user_id
                else:
                    user_id = existing_user_id

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
