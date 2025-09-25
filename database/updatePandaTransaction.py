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
    """Lambda handler for creating/updating transactions."""
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
        transaction_id = body.get("transaction_id")
        portfolio_entity_id = body.get("portfolio_entity_id")
        counterparty_entity_id = body.get("counterparty_entity_id")
        instrument_entity_id = body.get("instrument_entity_id")
        transaction_type_id = body.get("transaction_type_id")
        transaction_status_id = body.get("transaction_status_id")
        properties = body.get("properties")

        # Validate required fields
        if not user_id:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "user_id is required"})
            }

        if not transaction_id and not all([portfolio_entity_id, instrument_entity_id, transaction_type_id]):
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "portfolio_entity_id, instrument_entity_id, and transaction_type_id are required for new transactions"})
            }

        # Get database connection
        conn = get_db_connection()

        try:
            with conn.cursor() as cursor:
                if transaction_id:
                    # Update existing transaction
                    updates = []
                    params = []

                    if portfolio_entity_id is not None:
                        updates.append("portfolio_entity_id = %s")
                        params.append(portfolio_entity_id)
                    if counterparty_entity_id is not None:
                        updates.append("counterparty_entity_id = %s")
                        params.append(counterparty_entity_id)
                    if instrument_entity_id is not None:
                        updates.append("instrument_entity_id = %s")
                        params.append(instrument_entity_id)
                    if transaction_type_id is not None:
                        updates.append("transaction_type_id = %s")
                        params.append(transaction_type_id)
                    if transaction_status_id is not None:
                        updates.append("transaction_status_id = %s")
                        params.append(transaction_status_id)
                    if properties is not None:
                        # Convert properties to JSON string if it's a dict
                        if isinstance(properties, dict):
                            properties = json.dumps(properties)
                        updates.append("properties = %s")
                        params.append(properties)

                    if not updates:
                        return {
                            "statusCode": 400,
                            "headers": cors_headers,
                            "body": json.dumps({"error": "No fields to update"})
                        }

                    updates.append("updated_user_id = %s")
                    params.append(user_id)
                    params.append(transaction_id)

                    sql = f"""
                        UPDATE transactions 
                        SET {', '.join(updates)}
                        WHERE transaction_id = %s
                    """

                    print(f"DEBUG: Update SQL: {sql}")
                    print(f"DEBUG: Update params: {params}")

                    cursor.execute(sql, params)

                    if cursor.rowcount == 0:
                        return {
                            "statusCode": 404,
                            "headers": cors_headers,
                            "body": json.dumps({"error": f"Transaction with ID {transaction_id} not found"})
                        }

                    conn.commit()

                    return {
                        "statusCode": 200,
                        "headers": cors_headers,
                        "body": json.dumps({
                            "success": True,
                            "message": f"Transaction {transaction_id} updated successfully",
                            "transaction_id": transaction_id
                        })
                    }

                else:
                    # Insert new transaction
                    # Set default transaction_status_id if not provided
                    if not transaction_status_id:
                        # Get the first available transaction status
                        cursor.execute(
                            "SELECT transaction_status_id FROM transaction_statuses LIMIT 1")
                        result = cursor.fetchone()
                        if result:
                            transaction_status_id = result['transaction_status_id']
                        else:
                            return {
                                "statusCode": 400,
                                "headers": cors_headers,
                                "body": json.dumps({"error": "No transaction statuses available"})
                            }

                    # Convert properties to JSON string if it's a dict
                    properties_value = properties
                    if isinstance(properties, dict):
                        properties_value = json.dumps(properties)

                    sql = """
                        INSERT INTO transactions (
                            portfolio_entity_id, 
                            counterparty_entity_id, 
                            instrument_entity_id, 
                            transaction_type_id, 
                            transaction_status_id, 
                            properties, 
                            updated_user_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """

                    params = [
                        portfolio_entity_id,
                        counterparty_entity_id,
                        instrument_entity_id,
                        transaction_type_id,
                        transaction_status_id,
                        properties_value,
                        user_id
                    ]

                    print(f"DEBUG: Insert SQL: {sql}")
                    print(f"DEBUG: Insert params: {params}")

                    cursor.execute(sql, params)
                    new_transaction_id = cursor.lastrowid

                    conn.commit()

                    return {
                        "statusCode": 200,
                        "headers": cors_headers,
                        "body": json.dumps({
                            "success": True,
                            "message": "Transaction created successfully",
                            "transaction_id": new_transaction_id
                        })
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
