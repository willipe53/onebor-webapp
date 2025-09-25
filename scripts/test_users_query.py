#!/usr/bin/env python3
"""
Test script to debug the users query directly
"""
import os
import sys
import pymysql
import json
from dotenv import load_dotenv

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)


def get_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        database=os.getenv('DATABASE'),
        cursorclass=pymysql.cursors.DictCursor
    )


def test_queries():
    conn = get_connection()

    print("=== Testing Users Queries ===\n")

    try:
        with conn.cursor() as cursor:
            # Test 1: Check client_group_users table for client_group_id 19
            print("1. Users in client_group_users for client_group_id 19:")
            cursor.execute("""
                SELECT client_group_id, user_id 
                FROM client_group_users 
                WHERE client_group_id = 19
                ORDER BY user_id
            """)
            cgu_rows = cursor.fetchall()
            for row in cgu_rows:
                print(
                    f"   client_group_id: {row['client_group_id']}, user_id: {row['user_id']}")
            print(f"   Total: {len(cgu_rows)} users\n")

            # Test 2: Check users table for those user_ids
            if cgu_rows:
                user_ids = [str(row['user_id']) for row in cgu_rows]
                user_ids_str = ','.join(user_ids)
                print(f"2. Users table data for user_ids {user_ids_str}:")
                cursor.execute(f"""
                    SELECT user_id, email, primary_client_group_id 
                    FROM users 
                    WHERE user_id IN ({user_ids_str})
                    ORDER BY user_id
                """)
                user_rows = cursor.fetchall()
                for row in user_rows:
                    print(
                        f"   user_id: {row['user_id']}, email: {row['email']}, primary_client_group_id: {row['primary_client_group_id']}")
                print(f"   Total: {len(user_rows)} users\n")

            # Test 3: Test the actual query from the Lambda (simple client_group_id filter)
            print("3. Lambda query - client_group_id only:")
            cursor.execute("""
                SELECT DISTINCT u.user_id, u.email, u.primary_client_group_id
                FROM users u
                INNER JOIN client_group_users cgu ON u.user_id = cgu.user_id
                WHERE cgu.client_group_id = 19
                ORDER BY u.user_id
            """)
            lambda_rows = cursor.fetchall()
            for row in lambda_rows:
                print(
                    f"   user_id: {row['user_id']}, email: {row['email']}, primary_client_group_id: {row['primary_client_group_id']}")
            print(f"   Total: {len(lambda_rows)} users\n")

            # Test 4: Test the complex query (client_group_id + requesting_user_id)
            print("4. Lambda query - client_group_id + requesting_user_id (user 8):")
            cursor.execute("""
                SELECT DISTINCT u.user_id, u.email, u.primary_client_group_id
                FROM users u
                INNER JOIN client_group_users cgu1 ON u.user_id = cgu1.user_id
                INNER JOIN client_group_users cgu2 ON cgu1.client_group_id = cgu2.client_group_id
                WHERE cgu1.client_group_id = 19 AND cgu2.user_id = 8
                ORDER BY u.user_id
            """)
            complex_rows = cursor.fetchall()
            for row in complex_rows:
                print(
                    f"   user_id: {row['user_id']}, email: {row['email']}, primary_client_group_id: {row['primary_client_group_id']}")
            print(f"   Total: {len(complex_rows)} users\n")

    finally:
        conn.close()


if __name__ == "__main__":
    test_queries()
