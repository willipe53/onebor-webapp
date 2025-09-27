#!/usr/bin/env python3
"""
Script to ensure transaction statuses exist in the database
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)


def ensure_transaction_statuses():
    """Ensure the required transaction statuses exist in the database"""

    # Database connection parameters
    db_config = {
        'host': os.getenv('DB_HOST'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'database': os.getenv('DB_NAME'),
        'charset': 'utf8mb4'
    }

    try:
        # Connect to database
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()

        print("=== Ensuring Transaction Statuses ===")

        # Check existing statuses
        cursor.execute(
            "SELECT transaction_status_id, name FROM transaction_statuses ORDER BY transaction_status_id")
        existing_statuses = cursor.fetchall()

        print(f"Existing statuses: {existing_statuses}")

        # Define required statuses
        required_statuses = [
            (1, 'INCOMPLETE'),
            (2, 'QUEUED'),
            (3, 'PROCESSED')
        ]

        # Insert missing statuses
        for status_id, status_name in required_statuses:
            cursor.execute(
                "INSERT IGNORE INTO transaction_statuses (transaction_status_id, name) VALUES (%s, %s)",
                (status_id, status_name)
            )
            if cursor.rowcount > 0:
                print(f"✅ Inserted status: {status_id} - {status_name}")
            else:
                print(
                    f"ℹ️  Status already exists: {status_id} - {status_name}")

        conn.commit()

        # Verify final statuses
        cursor.execute(
            "SELECT transaction_status_id, name FROM transaction_statuses ORDER BY transaction_status_id")
        final_statuses = cursor.fetchall()

        print(f"\nFinal statuses:")
        for status_id, name in final_statuses:
            print(f"  {status_id}: {name}")

        print(f"\n✅ Transaction statuses ensured successfully!")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

    return True


if __name__ == "__main__":
    ensure_transaction_statuses()
