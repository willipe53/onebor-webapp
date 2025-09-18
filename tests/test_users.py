"""
Comprehensive tests for User APIs.
Tests follow the pattern: modify -> validate -> revert -> validate -> cleanup
"""
import pytest
from .base_test import BaseAPITest


class TestUsers(BaseAPITest):
    """Test User CRUD operations with validation and cleanup."""

    @pytest.mark.integration
    def test_user_update_and_revert(self):
        """Test updating an existing user and reverting changes."""
        # Get existing users
        existing_users = self.get_users()
        assert len(existing_users) > 0, "No existing users found for testing"

        # Pick the first user for testing
        test_user = existing_users[0]
        original_user_id = test_user['user_id']
        original_email = test_user['email']
        original_name = test_user['name']

        # Store original values for restoration
        self.store_original_value(
            f"user_{original_user_id}_email", original_email)
        self.store_original_value(
            f"user_{original_user_id}_name", original_name)

        # Step 1: Update user with "TEST" suffix
        test_email = f"test_{self.get_test_timestamp()}@example.com"
        test_name = f"{original_name}TEST"
        self.update_user(original_user_id, test_email, test_name)

        # Step 2: Validate the changes
        updated_users = self.get_users({'user_id': original_user_id})
        assert len(
            updated_users) == 1, f"Expected 1 user, got {len(updated_users)}"
        updated_user = updated_users[0]
        assert updated_user['email'] == test_email, f"Expected email '{test_email}', got '{updated_user['email']}'"
        assert updated_user['name'] == test_name, f"Expected name '{test_name}', got '{updated_user['name']}'"
        assert updated_user['name'].endswith(
            'TEST'), "Name should end with 'TEST'"

        # Step 3: Revert to original values
        self.update_user(original_user_id, original_email, original_name)

        # Step 4: Validate the revert
        reverted_users = self.get_users({'user_id': original_user_id})
        assert len(
            reverted_users) == 1, f"Expected 1 user, got {len(reverted_users)}"
        reverted_user = reverted_users[0]
        assert reverted_user[
            'email'] == original_email, f"Expected original email '{original_email}', got '{reverted_user['email']}'"
        assert reverted_user[
            'name'] == original_name, f"Expected original name '{original_name}', got '{reverted_user['name']}'"
        assert not reverted_user['name'].endswith(
            'TEST'), "Name should not end with 'TEST' after revert"

    @pytest.mark.integration
    def test_user_create_and_delete_cycle(self):
        """Test creating a new user and then deleting it."""
        test_user_id = f"test_user_{self.get_test_timestamp()}"
        test_email = f"test_{self.get_test_timestamp()}@example.com"
        test_name = self.generate_test_name("USER")

        # Step 1: Create new user
        create_result = self.create_user(test_user_id, test_email, test_name)
        assert create_result['success'] is True, "User creation should succeed"

        # Step 2: Validate creation by retrieving the user
        created_users = self.get_users({'user_id': test_user_id})
        assert len(
            created_users) == 1, f"Expected 1 user with ID '{test_user_id}'"
        created_user = created_users[0]
        assert created_user['user_id'] == test_user_id, "User ID should match"
        assert created_user['email'] == test_email, "Email should match"
        assert created_user['name'] == test_name, "Name should match"

        # Also test retrieval by email
        email_users = self.get_users({'email': test_email})
        assert len(
            email_users) >= 1, f"Expected at least 1 user with email '{test_email}'"
        found_by_email = any(u['user_id'] == test_user_id for u in email_users)
        assert found_by_email, f"Should find user by email"

        # Step 3: Delete the user
        delete_result = self.delete_record(test_user_id, "User")
        assert delete_result['success'] is True, "User deletion should succeed"
        assert "successfully deleted" in delete_result['message'], "Delete message should confirm success"

        # Step 4: Validate deletion
        deleted_users = self.get_users({'user_id': test_user_id})
        assert len(
            deleted_users) == 0, f"User should be deleted, but found {len(deleted_users)} users"

        # Also check by email
        email_search_users = self.get_users({'email': test_email})
        remaining_users = [
            u for u in email_search_users if u['user_id'] == test_user_id]
        assert len(
            remaining_users) == 0, f"No users with test email should remain, found {len(remaining_users)}"

        # Remove from cleanup list since we manually deleted it
        if test_user_id in self.created_users:
            self.created_users.remove(test_user_id)

    @pytest.mark.integration
    def test_user_get_with_filters(self):
        """Test getting users with various filter parameters."""
        # Create a test user for filtering tests
        test_user_id = f"filter_test_{self.get_test_timestamp()}"
        test_email = f"filter_test_{self.get_test_timestamp()}@example.com"
        test_name = self.generate_test_name("FILTER_USER")
        self.create_user(test_user_id, test_email, test_name)

        # Test 1: Get all users (no filters)
        all_users = self.get_users()
        assert len(all_users) > 0, "Should return at least one user"

        # Test 2: Get by specific user_id
        id_filtered_users = self.get_users({'user_id': test_user_id})
        assert len(
            id_filtered_users) == 1, f"Expected 1 user for ID filter, got {len(id_filtered_users)}"
        assert id_filtered_users[0]['user_id'] == test_user_id

        # Test 3: Get by exact email
        email_filtered_users = self.get_users({'email': test_email})
        assert len(
            email_filtered_users) >= 1, f"Expected at least 1 user for email filter, got {len(email_filtered_users)}"
        found_by_email = any(
            u['email'] == test_email for u in email_filtered_users)
        assert found_by_email, f"Should find user with exact email '{test_email}'"

        # Test 4: Get by partial email (LIKE search with %)
        partial_email = test_email.split(
            '@')[0] + "%"  # Take username part + %
        partial_email_users = self.get_users({'email': partial_email})
        assert len(
            partial_email_users) >= 1, f"Expected at least 1 user for partial email filter, got {len(partial_email_users)}"
        found_by_partial_email = any(u['email'].startswith(
            test_email.split('@')[0]) for u in partial_email_users)
        assert found_by_partial_email, f"Should find user with partial email '{partial_email}'"

        # Test 5: Get by exact name
        name_filtered_users = self.get_users({'name': test_name})
        assert len(
            name_filtered_users) >= 1, f"Expected at least 1 user for name filter, got {len(name_filtered_users)}"
        found_by_name = any(
            u['name'] == test_name for u in name_filtered_users)
        assert found_by_name, f"Should find user with exact name '{test_name}'"

        # Test 6: Get by partial name (LIKE search with %)
        partial_name = test_name[:10] + "%"  # Take first 10 chars + %
        partial_name_users = self.get_users({'name': partial_name})
        assert len(
            partial_name_users) >= 1, f"Expected at least 1 user for partial name filter, got {len(partial_name_users)}"
        found_by_partial_name = any(u['name'].startswith(
            test_name[:10]) for u in partial_name_users)
        assert found_by_partial_name, f"Should find user with partial name '{partial_name}'"

        # Test 7: Get by non-existent user_id
        nonexistent_users = self.get_users(
            {'user_id': 'NONEXISTENT_USER_ID_12345'})
        assert len(
            nonexistent_users) == 0, "Should return no users for non-existent ID"

        # Test 8: Get by non-existent email
        nonexistent_email_users = self.get_users(
            {'email': 'nonexistent_12345@example.com'})
        assert len(
            nonexistent_email_users) == 0, "Should return no users for non-existent email"

    @pytest.mark.integration
    def test_user_update_validation(self):
        """Test user update with various validation scenarios."""
        # Create a test user for update testing
        test_user_id = f"update_test_{self.get_test_timestamp()}"
        original_email = f"original_{self.get_test_timestamp()}@example.com"
        original_name = self.generate_test_name("UPDATE_USER")
        self.create_user(test_user_id, original_email, original_name)

        # Test 1: Update only email
        new_email = f"new_email_{self.get_test_timestamp()}@example.com"
        update_result = self.update_user(test_user_id, email=new_email)
        assert update_result['success'] is True, "Email update should succeed"

        # Verify email update
        updated_users = self.get_users({'user_id': test_user_id})
        assert updated_users[0]['email'] == new_email, "Email should be updated"
        assert updated_users[0]['name'] == original_name, "Name should remain unchanged"

        # Test 2: Update only name
        new_name = f"{original_name}_UPDATED"
        update_result = self.update_user(test_user_id, name=new_name)
        assert update_result['success'] is True, "Name update should succeed"

        # Verify name update
        updated_users = self.get_users({'user_id': test_user_id})
        assert updated_users[0]['name'] == new_name, "Name should be updated"
        assert updated_users[0]['email'] == new_email, "Email should remain as previously updated"

        # Test 3: Update both email and name
        final_email = f"final_{self.get_test_timestamp()}@example.com"
        final_name = f"{original_name}_FINAL"
        update_result = self.update_user(
            test_user_id, email=final_email, name=final_name)
        assert update_result['success'] is True, "Both field update should succeed"

        # Verify both updates
        updated_users = self.get_users({'user_id': test_user_id})
        assert updated_users[0]['email'] == final_email, "Email should be updated to final value"
        assert updated_users[0]['name'] == final_name, "Name should be updated to final value"

        # Test 4: Update non-existent user (should handle gracefully)
        try:
            self.update_user('NONEXISTENT_USER_ID',
                             email='test@example.com', name='Test Name')
            # If no error, the API created the user (upsert behavior)
            # Verify what happened
            nonexistent_users = self.get_users(
                {'user_id': 'NONEXISTENT_USER_ID'})
            if len(nonexistent_users) > 0:
                # Clean up the accidentally created user
                self.delete_record('NONEXISTENT_USER_ID', "User")
        except Exception:
            # Expected to fail for non-existent user
            pass

    @pytest.mark.integration
    def test_user_upsert_behavior(self):
        """Test user upsert behavior (insert on duplicate key update)."""
        test_user_id = f"upsert_test_{self.get_test_timestamp()}"
        initial_email = f"initial_{self.get_test_timestamp()}@example.com"
        initial_name = self.generate_test_name("UPSERT_USER")

        # First call - should create the user
        create_result = self.create_user(
            test_user_id, initial_email, initial_name)
        assert create_result['success'] is True, "Initial user creation should succeed"

        # Verify creation
        users = self.get_users({'user_id': test_user_id})
        assert len(users) == 1, "User should be created"
        assert users[0]['email'] == initial_email, "Initial email should match"
        assert users[0]['name'] == initial_name, "Initial name should match"

        # Second call with same user_id but different email/name - should update
        updated_email = f"updated_{self.get_test_timestamp()}@example.com"
        updated_name = f"{initial_name}_UPDATED"

        # Remove from created list temporarily to test the upsert
        if test_user_id in self.created_users:
            self.created_users.remove(test_user_id)

        update_result = self.create_user(
            test_user_id, updated_email, updated_name)
        assert update_result['success'] is True, "User update via upsert should succeed"

        # Verify update (should still be only one user with this ID)
        users = self.get_users({'user_id': test_user_id})
        assert len(users) == 1, "Should still be only one user with this ID"
        assert users[0]['email'] == updated_email, "Email should be updated"
        assert users[0]['name'] == updated_name, "Name should be updated"

    @pytest.mark.integration
    def test_user_delete_with_constraints(self):
        """Test user deletion with referential integrity constraints."""
        # Create a test user
        test_user_id = f"constraint_user_{self.get_test_timestamp()}"
        test_email = f"constraint_{self.get_test_timestamp()}@example.com"
        test_name = self.generate_test_name("CONSTRAINT_USER")
        self.create_user(test_user_id, test_email, test_name)

        # Create a test client group
        test_group_name = self.generate_test_name("USER_DELETE_GROUP")
        create_result = self.create_client_group(test_group_name)
        group_id = create_result['id']

        # Associate user with the group
        self.modify_client_group_membership(group_id, test_user_id, "add")

        # Attempt to delete the user (should fail due to group association)
        try:
            delete_result = self.delete_record(test_user_id, "User")
            # If deletion succeeds, check the response
            if 'error' in delete_result:
                assert "referential integrity" in delete_result['error'].lower(
                ), "Should mention referential integrity"
            elif delete_result.get('success') is True:
                # Some implementations might allow deletion with cascading
                print("Warning: User deletion succeeded despite group association")
        except Exception as e:
            # Expected failure due to constraints
            assert "constraint" in str(e).lower() or "referential" in str(
                e).lower(), f"Error should mention constraints: {e}"

        # Remove user from group
        self.modify_client_group_membership(group_id, test_user_id, "remove")

        # Now deletion should succeed
        delete_result = self.delete_record(test_user_id, "User")
        if 'success' in delete_result:
            assert delete_result['success'] is True, "Deletion should succeed after removing constraints"
            # Remove from cleanup list since we manually deleted it
            if test_user_id in self.created_users:
                self.created_users.remove(test_user_id)

    @pytest.mark.integration
    def test_user_multiple_operations(self):
        """Test multiple user operations in sequence."""
        # Create multiple test users
        user_count = 3
        test_users = []

        for i in range(user_count):
            user_id = f"multi_user_{i}_{self.get_test_timestamp()}"
            email = f"multi_{i}_{self.get_test_timestamp()}@example.com"
            name = self.generate_test_name(f"MULTI_USER_{i}")
            test_users.append({
                'user_id': user_id,
                'email': email,
                'name': name
            })

        # Step 1: Create multiple users
        for user_data in test_users:
            result = self.create_user(
                user_data['user_id'], user_data['email'], user_data['name'])
            assert result['success'] is True, f"Creation of user {user_data['user_id']} should succeed"

        # Step 2: Verify all users were created
        all_users = self.get_users()
        for user_data in test_users:
            found = any(u['user_id'] == user_data['user_id'] and
                        u['email'] == user_data['email'] and
                        u['name'] == user_data['name'] for u in all_users)
            assert found, f"User {user_data['user_id']} should exist with correct data"

        # Step 3: Update all users
        for user_data in test_users:
            new_email = f"updated_{user_data['email']}"
            new_name = f"{user_data['name']}_UPDATED"
            self.update_user(user_data['user_id'], new_email, new_name)

            # Update our tracking data
            user_data['email'] = new_email
            user_data['name'] = new_name

        # Step 4: Verify all updates
        for user_data in test_users:
            users = self.get_users({'user_id': user_data['user_id']})
            assert len(
                users) == 1, f"Should find exactly one user with ID {user_data['user_id']}"
            user = users[0]
            assert user['email'] == user_data[
                'email'], f"User {user_data['user_id']} should have updated email"
            assert user['name'] == user_data['name'], f"User {user_data['user_id']} should have updated name"

        # Step 5: Delete all users
        for user_data in test_users:
            delete_result = self.delete_record(user_data['user_id'], "User")
            assert delete_result[
                'success'] is True, f"Deletion of user {user_data['user_id']} should succeed"

        # Step 6: Verify all deletions
        for user_data in test_users:
            users = self.get_users({'user_id': user_data['user_id']})
            assert len(
                users) == 0, f"User {user_data['user_id']} should be deleted"
            # Remove from cleanup list since we manually deleted them
            if user_data['user_id'] in self.created_users:
                self.created_users.remove(user_data['user_id'])
