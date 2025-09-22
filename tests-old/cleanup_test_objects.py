#!/usr/bin/env python3
"""
Emergency cleanup script for orphaned test objects
Removes any objects with TESTNEW prefix and reverts TESTMOD modifications
Run this if tests fail and leave behind test data
"""

import os
import sys
import re
from datetime import datetime
from typing import List, Dict, Any
from base_test import BaseAPITest


class TestCleanupService(BaseAPITest):
    """Service for cleaning up orphaned test objects."""

    def __init__(self):
        """Initialize cleanup service."""
        # Initialize parent class which sets up authentication
        super().setup_method()
        self.cleanup_stats = {
            'relationships_cleaned': 0,
            'client_groups_deleted': 0,
            'entities_deleted': 0,
            'entity_types_deleted': 0,
            'users_deleted': 0,
            'modifications_reverted': 0,
            'errors': []
        }

    def is_test_name(self, name: str) -> bool:
        """Check if a name represents a test object."""
        if not name or not isinstance(name, str):
            return False
        return name.startswith("TESTNEW") or "TESTMOD" in name

    def extract_testmod_pattern(self, text: str) -> str:
        """Extract TESTMOD prefix from text, leaving the original value."""
        if not text or not isinstance(text, str):
            return text

        # Pattern: TESTMOD<timestamp>_<original_value>
        pattern = r'TESTMOD\d{8}_\d{6}_'
        return re.sub(pattern, '', text)

    def cleanup_client_groups(self):
        """Find and delete test client groups."""
        print("\n🔍 Scanning for test client groups...")

        try:
            print("   Fetching client groups list...")
            groups = self.get_client_groups()
            test_groups = [
                g for g in groups if self.is_test_name(g.get('name', ''))]

            print(f"Found {len(test_groups)} test client groups to delete")
            if len(test_groups) == 0:
                return

            for i, group in enumerate(test_groups, 1):
                try:
                    group_id = group.get('client_group_id') or group.get('id')
                    group_name = group.get('name', 'Unknown')

                    print(
                        f"   [{i}/{len(test_groups)}] Deleting client group: {group_name}")

                    # Try to delete the group using the delete_record API with shorter timeout
                    response = self.api_request('delete_record', data={
                        'record_id': group_id,
                        'record_type': 'Client Group'
                    }, timeout=15)

                    if response.status_code == 200:
                        print(f"   ✅ Deleted")
                        self.cleanup_stats['client_groups_deleted'] += 1
                    else:
                        error_msg = f"Failed to delete client group {group_name}: {response.status_code}"
                        print(f"   ❌ {error_msg}")
                        self.cleanup_stats['errors'].append(error_msg)

                except Exception as e:
                    error_msg = f"Error deleting client group {group.get('name', 'Unknown')}: {e}"
                    print(f"   ❌ {error_msg}")
                    self.cleanup_stats['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"Error scanning client groups: {e}"
            print(f"❌ {error_msg}")
            self.cleanup_stats['errors'].append(error_msg)

    def cleanup_entities(self):
        """Find and delete test entities."""
        print("\n🔍 Scanning for test entities...")

        try:
            print("   Fetching entities list...")
            entities = self.get_entities()
            test_entities = [
                e for e in entities if self.is_test_name(e.get('name', ''))]

            print(f"Found {len(test_entities)} test entities to delete")
            if len(test_entities) == 0:
                return

            for i, entity in enumerate(test_entities, 1):
                try:
                    entity_id = entity.get('entity_id')
                    entity_name = entity.get('name', 'Unknown')

                    print(
                        f"   [{i}/{len(test_entities)}] Deleting entity: {entity_name}")

                    response = self.api_request('delete_record', data={
                        'record_id': entity_id,
                        'record_type': 'Entity'
                    }, timeout=15)

                    if response.status_code == 200:
                        print(f"   ✅ Deleted")
                        self.cleanup_stats['entities_deleted'] += 1
                    else:
                        error_msg = f"Failed to delete entity {entity_name}: {response.status_code}"
                        print(f"   ❌ {error_msg}")
                        self.cleanup_stats['errors'].append(error_msg)

                except Exception as e:
                    error_msg = f"Error deleting entity {entity.get('name', 'Unknown')}: {e}"
                    print(f"   ❌ {error_msg}")
                    self.cleanup_stats['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"Error scanning entities: {e}"
            print(f"❌ {error_msg}")
            self.cleanup_stats['errors'].append(error_msg)

    def cleanup_entity_types(self):
        """Find and clean up test entity types."""
        print("\n🔍 Scanning for test entity types...")

        try:
            # First, check the total count to understand the scope
            try:
                print("   Getting entity types count...")
                count_response = self.api_request('get_entity_types', data={
                                                  'count_only': True}, timeout=15)
                if count_response.status_code == 200:
                    total_count = count_response.json()
                    print(
                        f"   📊 Total entity types in database: {total_count}")
                    if total_count > 1000:
                        print(
                            f"   ⚠️  Large number of entity types detected. This may be why the API is timing out.")
                        print(
                            f"   💡 Consider using direct SQL cleanup for bulk deletion")
                        raise Exception(
                            f"Too many entity types ({total_count}) - API cannot handle the load")
                else:
                    print(
                        f"   ❌ Count query failed: {count_response.status_code}")
            except Exception as count_error:
                print(f"   ❌ Failed to get count: {count_error}")

            print("   Attempting to fetch entity types list...")
            entity_types = self.get_entity_types()
            test_entity_types = [
                et for et in entity_types if self.is_test_name(et.get('name', ''))]

            print(
                f"Found {len(test_entity_types)} test entity types to delete")

            for entity_type in test_entity_types:
                try:
                    entity_type_id = entity_type.get('entity_type_id')
                    entity_type_name = entity_type.get('name', 'Unknown')

                    response = self.api_request('delete_record', data={
                        'record_id': entity_type_id,
                        'record_type': 'Entity Type'
                    }, timeout=15)

                    if response.status_code == 200:
                        print(f"✅ Deleted entity type: {entity_type_name}")
                        self.cleanup_stats['entity_types_deleted'] += 1
                    else:
                        error_msg = f"Failed to delete entity type {entity_type_name}: {response.status_code}"
                        print(f"❌ {error_msg}")
                        self.cleanup_stats['errors'].append(error_msg)

                except Exception as e:
                    error_msg = f"Error deleting entity type {entity_type.get('name', 'Unknown')}: {e}"
                    print(f"❌ {error_msg}")
                    self.cleanup_stats['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"Error scanning entity types: {e}"
            print(f"❌ {error_msg}")
            self.cleanup_stats['errors'].append(error_msg)

    def cleanup_users(self):
        """Skip user cleanup - users are only created by Cognito, not by tests."""
        print("\n🔍 Skipping user cleanup (users only created by Cognito)")
        print("Found 0 test users to delete")

    def revert_testmod_modifications(self):
        """Find and revert TESTMOD modifications."""
        print("\n🔍 Scanning for TESTMOD modifications...")

        modifications_found = 0

        # Check client groups for TESTMOD in names
        try:
            groups = self.get_client_groups()
            for group in groups:
                if "TESTMOD" in group.get('name', ''):
                    try:
                        original_name = self.extract_testmod_pattern(
                            group['name'])
                        response = self.api_request('update_client_group', data={
                            'client_group_id': group.get('client_group_id') or group.get('id'),
                            'name': original_name,
                            'user_id': self.test_user_id
                        })

                        if response.status_code == 200:
                            print(
                                f"✅ Reverted client group name: {group['name']} → {original_name}")
                            self.cleanup_stats['modifications_reverted'] += 1

                        modifications_found += 1
                    except Exception as e:
                        error_msg = f"Error reverting client group {group.get('name', 'Unknown')}: {e}"
                        print(f"❌ {error_msg}")
                        self.cleanup_stats['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"Error scanning client groups for modifications: {e}"
            print(f"❌ {error_msg}")
            self.cleanup_stats['errors'].append(error_msg)

        # Check entities for TESTMOD in names
        try:
            entities = self.get_entities()
            for entity in entities:
                if "TESTMOD" in entity.get('name', ''):
                    try:
                        original_name = self.extract_testmod_pattern(
                            entity['name'])
                        response = self.api_request('update_entity', data={
                            'entity_id': entity.get('entity_id'),
                            'name': original_name,
                            'user_id': self.test_user_id
                        })

                        if response.status_code == 200:
                            print(
                                f"✅ Reverted entity name: {entity['name']} → {original_name}")
                            self.cleanup_stats['modifications_reverted'] += 1

                        modifications_found += 1
                    except Exception as e:
                        error_msg = f"Error reverting entity {entity.get('name', 'Unknown')}: {e}"
                        print(f"❌ {error_msg}")
                        self.cleanup_stats['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"Error scanning entities for modifications: {e}"
            print(f"❌ {error_msg}")
            self.cleanup_stats['errors'].append(error_msg)

        print(f"Found {modifications_found} TESTMOD modifications")

    def cleanup_client_group_relationships(self):
        """Clean up relationship tables first to respect foreign keys."""
        print("\n🔍 Cleaning up relationship tables (client_group_entities, client_group_users)...")

        # Clean up client_group_entities for test entities
        try:
            print("   Fetching entities for relationship cleanup...")
            entities = self.get_entities()
            test_entities = [
                e for e in entities if self.is_test_name(e.get('name', ''))]

            if len(test_entities) > 0:
                print(
                    f"   Found {len(test_entities)} test entities with potential relationships")
                for i, entity in enumerate(test_entities, 1):
                    try:
                        entity_id = entity.get('entity_id')
                        entity_name = entity.get('name', 'Unknown')
                        print(
                            f"   [{i}/{len(test_entities)}] Cleaning relationships for: {entity_name}")

                        # Remove from client_group_entities table with timeout
                        response = self.api_request('modify_client_group_entities', data={
                            'client_group_id': entity.get('client_group_id', 0),
                            'entity_ids': []  # Empty list removes the entity
                        }, timeout=10)

                        if response.status_code == 200:
                            print(f"   ✅ Cleaned")
                            self.cleanup_stats['relationships_cleaned'] += 1

                    except Exception as e:
                        print(
                            f"   ❌ Error removing entity {entity.get('name', 'Unknown')} from relationships: {e}")
            else:
                print("   No test entities found with relationships to clean")

        except Exception as e:
            print(f"❌ Error cleaning client_group_entities: {e}")

        # Simplified cleanup for client_group_users - only clean test groups
        try:
            print("   Fetching client groups for user relationship cleanup...")
            groups = self.get_client_groups()
            test_groups = [
                g for g in groups if self.is_test_name(g.get('name', ''))]

            if len(test_groups) > 0:
                print(
                    f"   Found {len(test_groups)} test client groups to clean user relationships")
                for i, group in enumerate(test_groups, 1):
                    try:
                        group_id = group.get(
                            'client_group_id') or group.get('id')
                        group_name = group.get('name', 'Unknown')
                        print(
                            f"   [{i}/{len(test_groups)}] Cleaning user relationships for: {group_name}")

                        # Note: We'll let the delete_record API handle cleaning up relationships
                        # when the group is deleted, rather than trying to remove all users manually
                        print(f"   ✅ Will be cleaned during group deletion")

                    except Exception as e:
                        print(
                            f"   ❌ Error preparing group {group.get('name', 'Unknown')} for cleanup: {e}")
            else:
                print("   No test client groups found with user relationships to clean")

        except Exception as e:
            print(f"❌ Error cleaning client_group_users: {e}")

    def run_cleanup(self):
        """Run the complete cleanup process."""
        start_time = datetime.now()
        print("🧹 Starting emergency test object cleanup...")
        print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n🔗 Respecting foreign key constraints:")
        print("   1. client_group_entities (references client_groups + entities)")
        print("   2. client_group_users (references client_groups + users)")
        print("   3. entities (references entity_types + other entities)")
        print("   4. client_groups")
        print("   5. users")
        print("   6. entity_types")
        print("\n⏰ Each API request has a 30-second timeout to prevent hanging")

        # Run cleanup in proper order to respect foreign key constraints
        try:
            print("\n🔄 Step 1/6: Cleaning up relationships...")
            self.cleanup_client_group_relationships()

            print("\n🔄 Step 2/6: Cleaning up entities...")
            self.cleanup_entities()

            print("\n🔄 Step 3/6: Cleaning up client groups...")
            self.cleanup_client_groups()

            print("\n🔄 Step 4/6: Cleaning up users...")
            self.cleanup_users()

            print("\n🔄 Step 5/6: Cleaning up entity types...")
            self.cleanup_entity_types()

            print("\n🔄 Step 6/6: Reverting test modifications...")
            self.revert_testmod_modifications()

        except Exception as e:
            error_msg = f"Fatal error during cleanup: {e}"
            print(f"\n❌ {error_msg}")
            self.cleanup_stats['errors'].append(error_msg)

        # Print summary
        end_time = datetime.now()
        elapsed = end_time - start_time
        print("\n" + "="*60)
        print("📊 CLEANUP SUMMARY")
        print("="*60)
        print(
            f"✅ Relationships Cleaned: {self.cleanup_stats['relationships_cleaned']}")
        print(
            f"✅ Client Groups Deleted: {self.cleanup_stats['client_groups_deleted']}")
        print(f"✅ Entities Deleted: {self.cleanup_stats['entities_deleted']}")
        print(
            f"✅ Entity Types Deleted: {self.cleanup_stats['entity_types_deleted']}")
        print(f"✅ Users Deleted: {self.cleanup_stats['users_deleted']}")
        print(
            f"✅ Modifications Reverted: {self.cleanup_stats['modifications_reverted']}")
        print(f"❌ Errors: {len(self.cleanup_stats['errors'])}")

        total_cleaned = (self.cleanup_stats['relationships_cleaned'] +
                         self.cleanup_stats['client_groups_deleted'] +
                         self.cleanup_stats['entities_deleted'] +
                         self.cleanup_stats['entity_types_deleted'] +
                         self.cleanup_stats['users_deleted'] +
                         self.cleanup_stats['modifications_reverted'])

        if total_cleaned > 0:
            print(f"\n🎉 Successfully cleaned {total_cleaned} test objects!")
        else:
            print(f"\n✨ No test objects found to clean")

        if self.cleanup_stats['errors']:
            print(f"\n❌ Errors encountered:")
            # Limit to first 10 errors
            for error in self.cleanup_stats['errors'][:10]:
                print(f"   • {error}")
            if len(self.cleanup_stats['errors']) > 10:
                print(
                    f"   ... and {len(self.cleanup_stats['errors']) - 10} more errors")

        print(f"\nCompleted at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Total time: {elapsed.total_seconds():.1f} seconds")
        return total_cleaned > 0 or len(self.cleanup_stats['errors']) > 0


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        print("\nUsage:")
        print("  python3 cleanup_test_objects.py          # Run cleanup")
        print("  python3 cleanup_test_objects.py --help   # Show this help")
        return

    try:
        cleanup_service = TestCleanupService()
        cleanup_service.run_cleanup()
    except Exception as e:
        print(f"❌ Fatal error during cleanup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
