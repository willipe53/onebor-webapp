#!/usr/bin/env python3
"""
Import transaction schemas from JSON files into the transaction_types table.

This script reads JSON schema files from the transaction_schemas directory
and inserts them into the database as transaction types.

Usage:
    python3 scripts/import_transaction_schemas.py

Requirements:
    - transaction_schemas/ directory with JSON files
    - Database connection configured in environment variables
"""

import os
import json
import pymysql
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_db_connection():
    """Get database connection using environment variables."""
    try:
        # Try to get from environment variables first
        db_host = os.getenv(
            'DB_HOST', 'panda-db.cnqay066ma0a.us-east-2.rds.amazonaws.com')
        db_port = int(os.getenv('DB_PORT', '3306'))
        db_user = os.getenv('DB_USER', 'admin')
        db_pass = os.getenv('DB_PASS', 'LiBoR45%')
        db_name = os.getenv('DATABASE', 'onebor')

        connection = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)


def convert_filename_to_name(filename: str) -> str:
    """
    Convert filename to transaction type name.
    Example: 'Capital_Call.json' -> 'Capital Call'
    """
    # Remove .json extension
    name = filename.replace('.json', '')
    # Replace underscores with spaces
    name = name.replace('_', ' ')
    return name


def read_schema_file(file_path: Path) -> Dict[str, Any]:
    """Read and parse a JSON schema file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        return content
    except Exception as e:
        print(f"❌ Failed to read {file_path}: {e}")
        return None


def insert_transaction_type(connection, name: str, properties: Dict[str, Any], updated_user_id: int = 10) -> bool:
    """Insert a transaction type into the database."""
    try:
        with connection.cursor() as cursor:
            # Check if transaction type already exists
            cursor.execute(
                "SELECT transaction_type_id FROM transaction_types WHERE name = %s",
                (name,)
            )
            existing = cursor.fetchone()

            if existing:
                print(
                    f"⚠️  Transaction type '{name}' already exists (ID: {existing['transaction_type_id']})")
                return False

            # Insert new transaction type
            cursor.execute(
                """
                INSERT INTO transaction_types (name, properties, updated_user_id)
                VALUES (%s, %s, %s)
                """,
                (name, json.dumps(properties), updated_user_id)
            )

            transaction_type_id = cursor.lastrowid
            connection.commit()
            print(
                f"✅ Inserted transaction type '{name}' with ID {transaction_type_id}")
            return True

    except Exception as e:
        print(f"❌ Failed to insert transaction type '{name}': {e}")
        connection.rollback()
        return False


def main():
    """Main function to import all transaction schemas."""
    print("🚀 Starting transaction schema import...")

    # Get the transaction_schemas directory
    schemas_dir = project_root / 'transaction_schemas'

    if not schemas_dir.exists():
        print(f"❌ Transaction schemas directory not found: {schemas_dir}")
        sys.exit(1)

    # Get database connection
    connection = get_db_connection()
    print("✅ Connected to database")

    # Get all JSON files in the directory
    json_files = list(schemas_dir.glob('*.json'))

    if not json_files:
        print("❌ No JSON files found in transaction_schemas directory")
        sys.exit(1)

    print(f"📁 Found {len(json_files)} JSON schema files")

    success_count = 0
    error_count = 0
    skipped_count = 0

    # Process each JSON file
    for json_file in sorted(json_files):
        print(f"\n📄 Processing {json_file.name}...")

        # Convert filename to transaction type name
        name = convert_filename_to_name(json_file.name)
        print(f"   Name: {name}")

        # Read the schema content
        properties = read_schema_file(json_file)
        if properties is None:
            error_count += 1
            continue

        # Insert into database
        if insert_transaction_type(connection, name, properties):
            success_count += 1
        else:
            skipped_count += 1

    # Close database connection
    connection.close()

    # Print summary
    print(f"\n📊 Import Summary:")
    print(f"   ✅ Successfully imported: {success_count}")
    print(f"   ⚠️  Skipped (already exists): {skipped_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📁 Total files processed: {len(json_files)}")

    if error_count > 0:
        print(f"\n❌ Import completed with {error_count} errors")
        sys.exit(1)
    else:
        print(f"\n🎉 Import completed successfully!")


if __name__ == "__main__":
    main()
