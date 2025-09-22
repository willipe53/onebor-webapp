#!/usr/bin/env python3
"""
Comprehensive tests for Client Group APIs.
Tests follow the pattern: modify -> validate -> revert -> validate -> cleanup
"""
import pytest
from .base_test import BaseAPITest


class TestClientGroups(BaseAPITest):
    """Test Client Group CRUD operations with validation and cleanup."""

    @pytest.mark.integration
    def test_client_group_update_and_revert(self):
        """Test updating an existing client group name and reverting it."""
        # Get existing client groups
        existing_groups = self.get_client_groups()

        # If no existing groups, create one for testing
        if len(existing_groups) == 0:
            create_result = self.create_client_group(test_name)
            original_group_id = create_result['id']
            original_name = test_name
        else:
            # Pick the first group for testing
            test_group = existing_groups[0]
            original_group_id = test_group['client_group_id']
            original_name = test_group['name']

        # Store original value for potential restoration
        self.store_original_value(
            f"client_group_{original_group_id}_name", original_name)

        # Step 1: Update client group name to add "TEST" suffix
        test_name = f"{original_name}TEST"
        self.update_client_group(original_group_id, test_name)

        # Step 2: Validate the name change by retrieving and checking
        updated_groups = self.get_client_groups(
            {'client_group_id': original_group_id})
        assert len(
            updated_groups) == 1, f"Expected 1 group, got {len(updated_groups)}"
        assert updated_groups[0][
            'name'] == test_name, f"Expected name '{test_name}', got '{updated_groups[0]['name']}'"
        assert updated_groups[0]['name'].endswith(
            'TEST'), "Name should end with 'TEST'"

        # Step 3: Revert the name back to original
        self.update_client_group(original_group_id, original_name)

        # Step 4: Validate the revert by retrieving and checking
        reverted_groups = self.get_client_groups(
            {'client_group_id': original_group_id})
        assert len(
            reverted_groups) == 1, f"Expected 1 group, got {len(reverted_groups)}"
        assert reverted_groups[0][
            'name'] == original_name, f"Expected original name '{original_name}', got '{reverted_groups[0]['name']}'"
        assert not reverted_groups[0]['name'].endswith(
            'TEST'), "Name should not end with 'TEST' after revert"

    @pytest.mark.integration
    def test_client_group_create_and_delete_cycle(self):
        """Test creating a new client group and then deleting it."""

        # Step 1: Create new client group
        create_result = self.create_client_group(test_name)
        assert 'id' in create_result, "Create result should contain 'id'"
        created_group_id = create_result['id']

        # Step 2: Validate creation by retrieving the new group
        created_groups = self.get_client_groups({'group_name': test_name})
        assert len(
            created_groups) >= 1, f"Expected at least 1 group with name '{test_name}'"
        found_group = next(
            (g for g in created_groups if g['name'] == test_name), None)
        assert found_group is not None, f"Could not find created group with name '{test_name}'"
        assert found_group['client_group_id'] == created_group_id, "Group ID mismatch"

        # Step 3: Delete the created group
        delete_result = self.delete_record(created_group_id, "Client Group")
        assert delete_result['success'] is True, "Delete should be successful"
        assert "successfully deleted" in delete_result['message'], "Delete message should confirm success"

        # Step 4: Validate deletion by attempting to retrieve the group
        deleted_groups = self.get_client_groups(
            {'client_group_id': created_group_id})
        assert len(
            deleted_groups) == 0, f"Group should be deleted, but found {len(deleted_groups)} groups"

        # Also check by name
        name_search_groups = self.get_client_groups({'group_name': test_name})
        remaining_groups = [
            g for g in name_search_groups if g['name'] == test_name]
        assert len(
            remaining_groups) == 0, f"No groups with test name should remain, found {len(remaining_groups)}"

        # Remove from cleanup list since we manually deleted it
        if created_group_id in self.created_client_groups:
            self.created_client_groups.remove(created_group_id)

    @pytest.mark.integration
    def test_client_group_get_with_filters(self):
        """Test getting client groups with various filter parameters."""
        # Create a test group for filtering tests
        create_result = self.create_client_group(test_name)
        created_group_id = create_result['id']

        # Test 1: Get all groups (no filters)
        all_groups = self.get_client_groups()
        assert len(all_groups) > 0, "Should return at least one group"

        # Test 2: Get by specific ID
        id_filtered_groups = self.get_client_groups(
            {'client_group_id': created_group_id})
        assert len(
            id_filtered_groups) == 1, f"Expected 1 group for ID filter, got {len(id_filtered_groups)}"
        assert id_filtered_groups[0]['client_group_id'] == created_group_id

        # Test 3: Get by exact name
        name_filtered_groups = self.get_client_groups(
            {'group_name': test_name})
        assert len(
            name_filtered_groups) >= 1, f"Expected at least 1 group for name filter, got {len(name_filtered_groups)}"
        found_by_name = any(
            g['name'] == test_name for g in name_filtered_groups)
        assert found_by_name, f"Should find group with exact name '{test_name}'"

        # Test 4: Get by partial name (LIKE search with %)
        partial_name = test_name[:10] + "%"  # Take first 10 chars + %
        partial_filtered_groups = self.get_client_groups(
            {'group_name': partial_name})
        assert len(
            partial_filtered_groups) >= 1, f"Expected at least 1 group for partial name filter, got {len(partial_filtered_groups)}"
        found_by_partial = any(g['name'].startswith(test_name[:10])
                               for g in partial_filtered_groups)
        assert found_by_partial, f"Should find group with partial name '{partial_name}'"

        # Test 5: Get by non-existent ID
        nonexistent_groups = self.get_client_groups(
            {'client_group_id': 999999})
        assert len(
            nonexistent_groups) == 0, "Should return no groups for non-existent ID"

        # Test 6: Get by non-existent name
        nonexistent_name_groups = self.get_client_groups(
            {'group_name': 'NONEXISTENT_GROUP_NAME_12345'})
        assert len(
            nonexistent_name_groups) == 0, "Should return no groups for non-existent name"

    @pytest.mark.integration
    def test_client_group_get_by_user_id(self):
        """Test getting client groups filtered by user_id."""
        # First, we need to create a user and a client group, then associate them
        test_user_id = self.test_user_id
        test_user_name = f"Test User {self.get_test_timestamp()}"

        # Create test user

        # Create test client group
        create_result = self.create_client_group(test_group_name)
        created_group_id = create_result['id']

        # Associate user with client group
        self.modify_client_group_membership(
            created_group_id, test_user_id, "add")

        # Test: Get client groups for this user
        user_groups = self.get_client_groups({'user_id': test_user_id})
        assert len(
            user_groups) >= 1, f"Expected at least 1 group for user, got {len(user_groups)}"

        # Verify our test group is in the results
        found_test_group = any(g['client_group_id'] ==
                               created_group_id for g in user_groups)
        assert found_test_group, f"Should find test group {created_group_id} for user {test_user_id}"

        # Test with filters: user_id + group_name
        filtered_user_groups = self.get_client_groups({
            'user_id': test_user_id,
            'group_name': test_group_name
        })
        assert len(
            filtered_user_groups) >= 1, "Should find group with both user and name filter"

        # Cleanup: Remove user from group
        self.modify_client_group_membership(
            created_group_id, test_user_id, "remove")

    @pytest.mark.integration
    def test_client_group_update_validation(self):
        """Test client group update with various validation scenarios."""
        # Create a test group for update testing
        create_result = self.create_client_group(original_name)
        group_id = create_result['id']

        # Test 1: Valid update
        new_name = f"{original_name}_UPDATED"
        update_result = self.update_client_group(group_id, new_name)
        assert update_result['success'] is True, "Valid update should succeed"

        # Verify the update
        updated_groups = self.get_client_groups({'client_group_id': group_id})
        assert updated_groups[0]['name'] == new_name, "Name should be updated"

        # Test 2: Update with empty name (should handle gracefully)
        try:
            self.update_client_group(group_id, "")
            # If it doesn't raise an error, verify what happened
            empty_name_groups = self.get_client_groups(
                {'client_group_id': group_id})
            # The behavior depends on the API implementation
        except Exception:
            # Empty name might be rejected, which is acceptable
            pass

        # Test 3: Update non-existent group (should fail gracefully)
        try:
            self.update_client_group(999999, "Should Not Work")
            # If no error is raised, verify no changes occurred
            nonexistent_groups = self.get_client_groups(
                {'client_group_id': 999999})
            assert len(
                nonexistent_groups) == 0, "Non-existent group should remain non-existent"
        except Exception:
            # Expected to fail
            pass

        # Restore original name for cleanup
        self.update_client_group(group_id, original_name)

    @pytest.mark.integration
    def test_client_group_delete_with_constraints(self):
        """Test client group deletion with referential integrity constraints."""
        # Create a test group
        create_result = self.create_client_group(test_group_name)
        group_id = create_result['id']

        # Create a test user
        test_user_id = self.test_user_id
        test_user_name = f"Constraint User {self.get_test_timestamp()}"

        # Associate user with the group
        self.modify_client_group_membership(group_id, test_user_id, "add")

        # Attempt to delete the group (should fail due to user association)
        try:
            delete_result = self.delete_record(group_id, "Client Group")
            # If deletion succeeds, check the response
            if 'error' in delete_result:
                assert "referential integrity" in delete_result['error'].lower(
                ), "Should mention referential integrity"
            elif delete_result.get('success') is True:
                # Some implementations might allow deletion with cascading
                print("Warning: Group deletion succeeded despite user association")
        except Exception as e:
            # Expected failure due to constraints
            assert "constraint" in str(e).lower() or "referential" in str(
                e).lower(), f"Error should mention constraints: {e}"

        # Remove user association
        self.modify_client_group_membership(group_id, test_user_id, "remove")

        # Now deletion should succeed
        delete_result = self.delete_record(group_id, "Client Group")
        if 'success' in delete_result:
            assert delete_result['success'] is True, "Deletion should succeed after removing constraints"
            # Remove from cleanup list since we manually deleted it
            if group_id in self.created_client_groups:
                self.created_client_groups.remove(group_id)

    @pytest.mark.integration
    def test_client_group_multiple_operations(self):
        """Test multiple client group operations in sequence."""
        # Create multiple test groups
        group_names = [self.generate_test_name(
            f"MULTI_TEST_{i}") for i in range(3)]
        created_ids = []

        # Step 1: Create multiple groups
        for name in group_names:
            result = self.create_client_group(name)
            created_ids.append(result['id'])

        # Step 2: Verify all groups were created
        all_groups = self.get_client_groups()
        for i, group_id in enumerate(created_ids):
            found = any(g['client_group_id'] == group_id and g['name']
                        == group_names[i] for g in all_groups)
            assert found, f"Group {group_id} with name {group_names[i]} should exist"

        # Step 3: Update all groups
        updated_names = [f"{name}_UPDATED" for name in group_names]
        for group_id, new_name in zip(created_ids, updated_names):
            self.update_client_group(group_id, new_name)

        # Step 4: Verify all updates
        for i, group_id in enumerate(created_ids):
            groups = self.get_client_groups({'client_group_id': group_id})
            assert len(
                groups) == 1, f"Should find exactly one group with ID {group_id}"
            assert groups[0]['name'] == updated_names[
                i], f"Group {group_id} should have updated name {updated_names[i]}"

        # Step 5: Delete all groups
        for group_id in created_ids:
            delete_result = self.delete_record(group_id, "Client Group")
            assert delete_result['success'] is True, f"Deletion of group {group_id} should succeed"

        # Step 6: Verify all deletions
        for group_id in created_ids:
            groups = self.get_client_groups({'client_group_id': group_id})
            assert len(groups) == 0, f"Group {group_id} should be deleted"
            # Remove from cleanup list since we manually deleted them
            if group_id in self.created_client_groups:
                self.created_client_groups.remove(group_id)

    @pytest.mark.integration
    def test_client_group_preferences(self):
        """Test updating client group preferences field."""
        # Get existing client groups
        existing_groups = self.get_client_groups()
        if len(existing_groups) == 0:
            # Create a test group if none exist
            create_result = self.create_client_group(test_name)
            test_group_id = create_result['id']
            original_preferences = None
        else:
            test_group = existing_groups[0]
            test_group_id = test_group['client_group_id']
            original_preferences = test_group.get('preferences')

        # Store original value for restoration
        self.store_original_value(
            f"client_group_{test_group_id}_preferences", original_preferences)

        try:
            # Step 1: Update preferences with JSON object
            test_preferences = {
                "default_permissions": {
                    "read": True,
                    "write": False,
                    "admin": False
                },
                "ui_settings": {
                    "theme": "corporate",
                    "layout": "compact"
                },
                "notification_settings": {
                    "group_announcements": True,
                    "member_activities": False
                },
                "billing_preferences": {
                    "currency": "USD",
                    "auto_renew": True
                }
            }

            response = self.api_call("/update_client_group", {
                "client_group_id": test_group_id,
                "preferences": test_preferences
            })
            assert response.get(
                "success"), f"Failed to update client group preferences: {response}"

            # Validate preferences update
            updated_groups = self.get_client_groups(
                {'client_group_id': test_group_id})
            assert len(
                updated_groups) == 1, f"Expected 1 group, got {len(updated_groups)}"
            updated_group = updated_groups[0]

            # Check if preferences are properly stored and retrieved
            if updated_group.get('preferences'):
                if isinstance(updated_group['preferences'], str):
                    import json
                    stored_preferences = json.loads(
                        updated_group['preferences'])
                else:
                    stored_preferences = updated_group['preferences']

                assert stored_preferences['default_permissions']['read'] == test_preferences['default_permissions']['read']
                assert stored_preferences['ui_settings']['theme'] == test_preferences['ui_settings']['theme']
                assert stored_preferences['billing_preferences']['currency'] == test_preferences['billing_preferences']['currency']

            # Step 2: Update preferences with a different structure
            test_preferences_v2 = {
                "version": 2,
                "features": ["dashboard", "reporting", "analytics"],
                "limits": {
                    "max_users": 50,
                    "storage_gb": 100
                }
            }

            response = self.api_call("/update_client_group", {
                "client_group_id": test_group_id,
                "preferences": test_preferences_v2
            })
            assert response.get(
                "success"), f"Failed to update client group preferences v2: {response}"

            # Validate second preferences update
            updated_groups = self.get_client_groups(
                {'client_group_id': test_group_id})
            updated_group = updated_groups[0]

            if updated_group.get('preferences'):
                if isinstance(updated_group['preferences'], str):
                    import json
                    stored_preferences = json.loads(
                        updated_group['preferences'])
                else:
                    stored_preferences = updated_group['preferences']

                assert stored_preferences['version'] == 2
                assert "dashboard" in stored_preferences['features']
                assert stored_preferences['limits']['max_users'] == 50

            # Step 3: Test clearing preferences (set to null)
            response = self.api_call("/update_client_group", {
                "client_group_id": test_group_id,
                "preferences": None
            })
            assert response.get(
                "success"), f"Failed to clear client group preferences: {response}"

            # Validate preferences cleared
            updated_groups = self.get_client_groups(
                {'client_group_id': test_group_id})
            updated_group = updated_groups[0]
            # Should be null or empty
            assert updated_group.get('preferences') in [None, '', '{}']

        finally:
            # Step 4: Restore original values
            if original_preferences is not None:
                response = self.api_call("/update_client_group", {
                    "client_group_id": test_group_id,
                    "preferences": original_preferences
                })
                assert response.get(
                    "success"), f"Failed to restore client group preferences: {response}"

            # Final validation - ensure restoration
            final_groups = self.get_client_groups(
                {'client_group_id': test_group_id})
            if len(final_groups) > 0:
                final_group = final_groups[0]
                assert final_group.get('preferences') == original_preferences

            # Clean up test group if we created it
            if len(existing_groups) == 0:
                delete_result = self.delete_record(
                    test_group_id, "Client Group")
                assert delete_result[
                    'success'] is True, f"Cleanup deletion of group {test_group_id} should succeed"
                if test_group_id in self.created_client_groups:
                    self.created_client_groups.remove(test_group_id)
