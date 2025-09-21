#!/usr/bin/env python3
"""
Panda Delete Record Lambda Function
Handles deletion of various record types with proper foreign key handling.
"""

import boto3
import json
import pymysql
import os
from typing import Dict, Any
import traceback


def get_db_secret():
    """Get database credentials from AWS Secrets Manager."""
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=os.environ["SECRET_ARN"])
    return json.loads(response["SecretString"])


def get_db_connection():
    """Get database connection with proper error handling."""
    try:
        secrets = get_db_secret()
        connection = pymysql.connect(
            host=secrets["DB_HOST"],
            user=secrets["DB_USER"],
            password=secrets["DB_PASS"],
            database=secrets["DATABASE"],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=5
        )
        return connection
    except Exception as e:
        print(f"Database connection error: {e}")
        raise


def delete_client_group(connection, record_id: int) -> Dict[str, Any]:
    """Delete a client group and handle foreign key constraints."""
    try:
        with connection.cursor() as cursor:
            # First, remove the client group from relationship tables
            # Remove all client_group_entities relationships
            cursor.execute("""
                DELETE FROM client_group_entities 
                WHERE client_group_id = %s
            """, (record_id,))

            # Remove all client_group_users relationships
            cursor.execute("""
                DELETE FROM client_group_users 
                WHERE client_group_id = %s
            """, (record_id,))

            # Update users to remove primary_client_group_id references
            cursor.execute("""
                UPDATE users 
                SET primary_client_group_id = NULL 
                WHERE primary_client_group_id = %s
            """, (record_id,))

            # Now delete the client group itself
            cursor.execute("""
                DELETE FROM client_groups 
                WHERE client_group_id = %s
            """, (record_id,))

            if cursor.rowcount == 0:
                return {
                    "success": False,
                    "message": f"Client group with ID {record_id} not found"
                }

            connection.commit()
            return {
                "success": True,
                "message": f"Client group {record_id} successfully deleted"
            }

    except Exception as e:
        connection.rollback()
        return {
            "success": False,
            "error": f"Failed to delete client group: {str(e)}"
        }


def delete_entity(connection, record_id: int) -> Dict[str, Any]:
    """Delete an entity and handle foreign key constraints."""
    try:
        with connection.cursor() as cursor:
            # Remove from client_group_entities relationship table
            cursor.execute("""
                DELETE FROM client_group_entities 
                WHERE entity_id = %s
            """, (record_id,))

            # Update child entities to remove parent references
            cursor.execute("""
                UPDATE entities 
                SET parent_entity_id = NULL 
                WHERE parent_entity_id = %s
            """, (record_id,))

            # Delete the entity itself
            cursor.execute("""
                DELETE FROM entities 
                WHERE entity_id = %s
            """, (record_id,))

            if cursor.rowcount == 0:
                return {
                    "success": False,
                    "message": f"Entity with ID {record_id} not found"
                }

            connection.commit()
            return {
                "success": True,
                "message": f"Entity {record_id} successfully deleted"
            }

    except Exception as e:
        connection.rollback()
        return {
            "success": False,
            "error": f"Failed to delete entity: {str(e)}"
        }


def delete_entity_type(connection, record_id: int) -> Dict[str, Any]:
    """Delete an entity type and handle foreign key constraints."""
    try:
        with connection.cursor() as cursor:
            # Check if any entities are using this entity type
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM entities 
                WHERE entity_type_id = %s
            """, (record_id,))

            result = cursor.fetchone()
            if result['count'] > 0:
                return {
                    "success": False,
                    "error": f"Cannot delete entity type {record_id}: {result['count']} entities are still using it"
                }

            # Delete the entity type
            cursor.execute("""
                DELETE FROM entity_types 
                WHERE entity_type_id = %s
            """, (record_id,))

            if cursor.rowcount == 0:
                return {
                    "success": False,
                    "message": f"Entity type with ID {record_id} not found"
                }

            connection.commit()
            return {
                "success": True,
                "message": f"Entity type {record_id} successfully deleted"
            }

    except Exception as e:
        connection.rollback()
        return {
            "success": False,
            "error": f"Failed to delete entity type: {str(e)}"
        }


def delete_user(connection, record_id: str) -> Dict[str, Any]:
    """Delete a user and handle foreign key constraints."""
    try:
        with connection.cursor() as cursor:
            # Remove from client_group_users relationship table
            cursor.execute("""
                DELETE FROM client_group_users 
                WHERE user_id = %s
            """, (record_id,))

            # Update client groups to remove user as owner if applicable
            cursor.execute("""
                UPDATE client_groups 
                SET user_id = NULL 
                WHERE user_id = %s
            """, (record_id,))

            # Delete the user
            cursor.execute("""
                DELETE FROM users 
                WHERE user_id = %s
            """, (record_id,))

            if cursor.rowcount == 0:
                return {
                    "success": False,
                    "message": f"User with ID {record_id} not found"
                }

            connection.commit()
            return {
                "success": True,
                "message": f"User {record_id} successfully deleted"
            }

    except Exception as e:
        connection.rollback()
        return {
            "success": False,
            "error": f"Failed to delete user: {str(e)}"
        }


def lambda_handler(event, context):
    """
    AWS Lambda handler for deleting records.

    Expected event structure:
    {
        "record_id": <id>,
        "record_type": "Client Group" | "Entity" | "Entity Type" | "User"
    }
    """

    # Add CORS headers
    headers = {
        'Access-Control-Allow-Origin': 'https://app.onebor.com',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Credentials': 'true'
    }

    try:
        # Handle OPTIONS request for CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight successful'})
            }

        # Parse the request body
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(
                event['body'], str) else event['body']
        else:
            body = event

        # Validate required fields
        record_id = body.get('record_id')
        record_type = body.get('record_type')

        if not record_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'error': 'record_id is required'
                })
            }

        if not record_type:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'success': False,
                    'error': 'record_type is required'
                })
            }

        # Get database connection
        connection = get_db_connection()

        try:
            # Route to appropriate delete function based on record type
            if record_type == "Client Group":
                result = delete_client_group(connection, int(record_id))
            elif record_type == "Entity":
                result = delete_entity(connection, int(record_id))
            elif record_type == "Entity Type":
                result = delete_entity_type(connection, int(record_id))
            elif record_type == "User":
                result = delete_user(connection, str(record_id))
            else:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'success': False,
                        'error': f'Unsupported record_type: {record_type}. Supported types: Client Group, Entity, Entity Type, User'
                    })
                }

            # Return appropriate status code
            status_code = 200 if result.get('success') else 400

            return {
                'statusCode': status_code,
                'headers': headers,
                'body': json.dumps(result)
            }

        finally:
            connection.close()

    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        print(f"Error in lambda_handler: {error_message}")
        print(f"Traceback: {traceback.format_exc()}")

        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'error': error_message
            })
        }


# For local testing
if __name__ == "__main__":
    # Test cases for local development
    test_events = [
        {
            "record_id": "test_user_123",
            "record_type": "User"
        },
        {
            "record_id": 999,
            "record_type": "Client Group"
        }
    ]

    for event in test_events:
        print(f"\nTesting with event: {event}")
        result = lambda_handler(event, None)
        print(f"Result: {result}")
