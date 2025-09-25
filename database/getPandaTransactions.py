import boto3
import json
import pymysql
import os
from typing import Dict, Any, List, Optional

# CORS headers
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}


def get_db_secret():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=os.environ["SECRET_ARN"])
    return json.loads(response["SecretString"])


def get_db_connection():
    """Get database connection using AWS Secrets Manager."""
    secrets = get_db_secret()
    return pymysql.connect(
        host=secrets["DB_HOST"],
        user=secrets["DB_USER"],
        password=secrets["DB_PASS"],
        database=secrets["DATABASE"],
        connect_timeout=5,
        cursorclass=pymysql.cursors.DictCursor
    )


def lambda_handler(event, context):
    """Lambda handler for getting transactions."""
    print(f"DEBUG: Event: {event}")

    try:
        # Parse the request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        print(f"DEBUG: Parsed body: {body}")

        # Extract parameters
        user_id = body.get("user_id")
        client_group_id = body.get("client_group_id")
        transaction_id = body.get("transaction_id")
        portfolio_entity_id = body.get("portfolio_entity_id")
        counterparty_entity_id = body.get("counterparty_entity_id")
        instrument_entity_id = body.get("instrument_entity_id")
        transaction_type_id = body.get("transaction_type_id")
        transaction_status_id = body.get("transaction_status_id")
        count_only = body.get("count_only", False)

        # Validate required fields
        if not user_id:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "user_id is required"})
            }

        # Get database connection
        conn = get_db_connection()

        try:
            with conn.cursor() as cursor:
                # Build the query
                if count_only:
                    query = """
                        SELECT COUNT(*) as count
                        FROM transactions t
                        JOIN entities e ON t.portfolio_entity_id = e.entity_id
                        JOIN client_group_entities cge ON e.entity_id = cge.entity_id
                        JOIN client_group_users cgu ON cge.client_group_id = cgu.client_group_id
                        WHERE cgu.user_id = %s
                    """
                    params = [user_id]
                else:
                    query = """
                        SELECT t.*
                        FROM transactions t
                        JOIN entities e ON t.portfolio_entity_id = e.entity_id
                        JOIN client_group_entities cge ON e.entity_id = cge.entity_id
                        JOIN client_group_users cgu ON cge.client_group_id = cgu.client_group_id
                        WHERE cgu.user_id = %s
                    """
                    params = [user_id]

                # Add filters
                if transaction_id:
                    query += " AND t.transaction_id = %s"
                    params.append(transaction_id)
                if portfolio_entity_id:
                    query += " AND t.portfolio_entity_id = %s"
                    params.append(portfolio_entity_id)
                if counterparty_entity_id:
                    query += " AND t.counterparty_entity_id = %s"
                    params.append(counterparty_entity_id)
                if instrument_entity_id:
                    query += " AND t.instrument_entity_id = %s"
                    params.append(instrument_entity_id)
                if transaction_type_id:
                    query += " AND t.transaction_type_id = %s"
                    params.append(transaction_type_id)
                if transaction_status_id:
                    query += " AND t.transaction_status_id = %s"
                    params.append(transaction_status_id)
                if client_group_id:
                    query += " AND cge.client_group_id = %s"
                    params.append(client_group_id)

                # Add ordering
                if not count_only:
                    query += " ORDER BY t.transaction_id DESC"

                print(f"DEBUG: Query: {query}")
                print(f"DEBUG: Params: {params}")

                cursor.execute(query, params)

                if count_only:
                    result = cursor.fetchone()
                    return {
                        "statusCode": 200,
                        "headers": cors_headers,
                        "body": json.dumps({"count": result['count']})
                    }
                else:
                    rows = cursor.fetchall()
                    return {
                        "statusCode": 200,
                        "headers": cors_headers,
                        "body": json.dumps(rows, default=str)
                    }

        finally:
            conn.close()

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Database error: {str(e)}"})
        }
