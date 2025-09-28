#!/usr/bin/env python3
"""
Check transaction statuses in the database
"""
from database_utils import get_db_connection
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))


def check_transaction_statuses():
    """Check what transaction statuses exist in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT transaction_status_id, name FROM transaction_statuses ORDER BY transaction_status_id")
        statuses = cursor.fetchall()

        print("Transaction Statuses:")
        for status in statuses:
            print(f"  ID {status['transaction_status_id']}: {status['name']}")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_transaction_statuses()
