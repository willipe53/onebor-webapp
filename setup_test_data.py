#!/usr/bin/env python3
"""
Setup test data for client group security testing
"""
import json
import boto3
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('tests/.env')


def get_db_secret():
    client = boto3.client("secretsmanager", region_name='us-east-2')
    response = client.get_secret_value(
        SecretId="arn:aws:secretsmanager:us-east-2:316490106381:secret:PandaDbSecretCache-pdzjei")
    return json.loads(response["SecretString"])


def get_connection(secrets):
    return pymysql.connect(
        host=secrets["DB_HOST"],
        user=secrets["DB_USER"],
        password=secrets["DB_PASS"],
        database=secrets["DATABASE"],
        connect_timeout=5,
        cursorclass=pymysql.cursors.DictCursor
    )


def setup_test_data():
    """Setup test data for client group security"""
    conn = None
    try:
        secrets = get_db_secret()
        conn = get_connection(secrets)

        with conn.cursor() as cursor:
            # Check what data exists
            print("🔍 Checking existing data...")

            cursor.execute("SELECT COUNT(*) as count FROM entities")
            entities_count = cursor.fetchone()["count"]
            print(f"📊 Entities: {entities_count}")

            cursor.execute("SELECT COUNT(*) as count FROM client_groups")
            client_groups_count = cursor.fetchone()["count"]
            print(f"📊 Client Groups: {client_groups_count}")

            cursor.execute("SELECT COUNT(*) as count FROM users")
            users_count = cursor.fetchone()["count"]
            print(f"📊 Users: {users_count}")

            # Get sample data
            cursor.execute("SELECT * FROM entities LIMIT 3")
            entities = cursor.fetchall()
            print(f"📝 Sample entities: {entities}")

            cursor.execute("SELECT * FROM client_groups LIMIT 3")
            client_groups = cursor.fetchall()
            print(f"📝 Sample client groups: {client_groups}")

            cursor.execute("SELECT * FROM users LIMIT 3")
            users = cursor.fetchall()
            print(f"📝 Sample users: {users}")

            # If we have entities and client groups, associate them
            if entities and client_groups:
                print("\n🔗 Associating entities with client groups...")

                # Get the first client group
                client_group_id = client_groups[0]['client_group_id']
                print(f"Using client group ID: {client_group_id}")

                # Associate all entities with this client group
                for entity in entities:
                    entity_id = entity['entity_id']
                    try:
                        cursor.execute("""
                            INSERT IGNORE INTO client_group_entities (client_group_id, entity_id)
                            VALUES (%s, %s)
                        """, (client_group_id, entity_id))
                        print(
                            f"✅ Associated entity {entity_id} with client group {client_group_id}")
                    except Exception as e:
                        print(f"❌ Failed to associate entity {entity_id}: {e}")

                conn.commit()

                # If we have users, associate them with the client group too
                if users:
                    print("\n👥 Associating users with client groups...")
                    for user in users:
                        user_id = user['user_id']
                        try:
                            cursor.execute("""
                                INSERT IGNORE INTO client_group_users (client_group_id, user_id)
                                VALUES (%s, %s)
                            """, (client_group_id, user_id))
                            print(
                                f"✅ Associated user {user_id} with client group {client_group_id}")
                        except Exception as e:
                            print(f"❌ Failed to associate user {user_id}: {e}")

                    conn.commit()

            print("\n✅ Test data setup complete!")

    except Exception as e:
        print(f"❌ Error setting up test data: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    setup_test_data()
