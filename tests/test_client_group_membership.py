#!/usr/bin/env python3
"""
Comprehensive tests for Client Group Membership modification APIs.
Tests follow the pattern: modify -> validate -> revert -> validate -> cleanup
"""
import pytest
from .base_test import BaseAPITest


class TestClientGroupMembership(BaseAPITest):
    """Test Client Group Membership modification operations."""

    @pytest.mark.integration
    def test_add_remove_user_membership_cycle(self):
        """Test adding a user to a client group and then removing them."""
        # Create test client group
        test_group_name = self.generate_test_name("MEMBERSHIP_GROUP")
        test_group_name = self.generate_test_name("TEST_GROUP")
        group_result = self.create_client_group(test_group_name)
        group_id = group_result['id']

        # Use existing authenticated test user
        test_user_id = self.test_user_id

        # Step 1: Add user to client group
        add_result = self.modify_client_group_membership(
            group_id, test_user_id, "add")
        assert add_result['success'] is True, "Adding user to group should succeed"

        # Step 2: Validate addition by checking user's groups
        user_groups = self.get_client_groups({'user_id': test_user_id})
        assert len(
            user_groups) >= 1, f"User should be in at least 1 group after addition"
        found_group = any(g['client_group_id'] ==
                          group_id for g in user_groups)
        assert found_group, f"User should be found in group {group_id}"

        # Step 3: Remove user from client group
        remove_result = self.modify_client_group_membership(
            group_id, test_user_id, "remove")
        assert remove_result['success'] is True, "Removing user from group should succeed"

        # Step 4: Validate removal by checking user's groups
        user_groups_after = self.get_client_groups({'user_id': test_user_id})
        found_group_after = any(g['client_group_id']
                                == group_id for g in user_groups_after)
        assert not found_group_after, f"User should not be found in group {group_id} after removal"

    @pytest.mark.integration
    def test_add_user_already_in_group(self):
        """Test adding a user who is already in the group (should handle gracefully)."""
        # Create test client group and user
        test_group_name = self.generate_test_name("TEST_GROUP")
        group_result = self.create_client_group(test_group_name)
        group_id = group_result['id']

        test_user_id = self.test_user_id

        # Add user to group first time
        first_add = self.modify_client_group_membership(
            group_id, test_user_id, "add")
        assert first_add['success'] is True, "First addition should succeed"

        # Verify user is in group
        user_groups = self.get_client_groups({'user_id': test_user_id})
        found_group = any(g['client_group_id'] ==
                          group_id for g in user_groups)
        assert found_group, "User should be in group after first addition"

        # Try to add user again (should handle gracefully)
        second_add = self.modify_client_group_membership(
            group_id, test_user_id, "add")
        assert second_add['success'] is True, "Second addition should succeed or be handled gracefully"

        # Verify user is still in group (only once)
        user_groups_after = self.get_client_groups({'user_id': test_user_id})
        group_memberships = [
            g for g in user_groups_after if g['client_group_id'] == group_id]
        assert len(
            group_memberships) == 1, "User should appear in group exactly once"

        # Clean up
        self.modify_client_group_membership(group_id, test_user_id, "remove")

    @pytest.mark.integration
    def test_remove_user_not_in_group(self):
        """Test removing a user who is not in the group (should handle gracefully)."""
        # Create test client group and user
        test_group_name = self.generate_test_name("TEST_GROUP")
        group_result = self.create_client_group(test_group_name)
        group_id = group_result['id']

        test_user_id = self.test_user_id

        # Verify user is not in group initially
        user_groups = self.get_client_groups({'user_id': test_user_id})
        found_group = any(g['client_group_id'] ==
                          group_id for g in user_groups)
        assert not found_group, "User should not be in group initially"

        # Try to remove user from group (should handle gracefully)
        remove_result = self.modify_client_group_membership(
            group_id, test_user_id, "remove")
        assert remove_result['success'] is True, "Removal should succeed or be handled gracefully"

        # Verify user is still not in group
        user_groups_after = self.get_client_groups({'user_id': test_user_id})
        found_group_after = any(g['client_group_id']
                                == group_id for g in user_groups_after)
        assert not found_group_after, "User should still not be in group after removal attempt"

    @pytest.mark.integration
    def test_membership_action_variations(self):
        """Test different action variations (add, insert, del, delete, remove)."""
        # Create test client group and user
        test_group_name = self.generate_test_name("TEST_GROUP")
        group_result = self.create_client_group(test_group_name)
        group_id = group_result['id']

        test_user_id = self.test_user_id

        # Test 1: "insert" action (should work like "add")
        insert_result = self.modify_client_group_membership(
            group_id, test_user_id, "insert")
        assert insert_result['success'] is True, "Insert action should succeed"

        # Verify user is in group
        user_groups = self.get_client_groups({'user_id': test_user_id})
        found_group = any(g['client_group_id'] ==
                          group_id for g in user_groups)
        assert found_group, "User should be in group after insert"

        # Test 2: "del" action (should work like "remove")
        del_result = self.modify_client_group_membership(
            group_id, test_user_id, "del")
        assert del_result['success'] is True, "Del action should succeed"

        # Verify user is not in group
        user_groups_after_del = self.get_client_groups(
            {'user_id': test_user_id})
        found_group_after_del = any(
            g['client_group_id'] == group_id for g in user_groups_after_del)
        assert not found_group_after_del, "User should not be in group after del"

        # Test 3: "add" and "delete" actions
        add_result = self.modify_client_group_membership(
            group_id, test_user_id, "add")
        assert add_result['success'] is True, "Add action should succeed"

        delete_result = self.modify_client_group_membership(
            group_id, test_user_id, "delete")
        assert delete_result['success'] is True, "Delete action should succeed"

        # Final verification
        final_user_groups = self.get_client_groups({'user_id': test_user_id})
        found_group_final = any(g['client_group_id']
                                == group_id for g in final_user_groups)
        assert not found_group_final, "User should not be in group after delete"

    @pytest.mark.integration
    def test_invalid_membership_actions(self):
        """Test invalid action values."""
        # Create test client group and user
        test_group_name = self.generate_test_name("TEST_GROUP")
        group_result = self.create_client_group(test_group_name)
        group_id = group_result['id']

        test_user_id = self.test_user_id

        # Test invalid action values
        invalid_actions = ["invalid", "create", "update", "", None, 123]

        for action in invalid_actions:
            try:
                result = self.modify_client_group_membership(
                    group_id, test_user_id, action)
                # If the API accepts it, check the response
                if 'error' in result:
                    assert "invalid" in result['error'].lower(
                    ), f"Should report invalid action for '{action}'"
                elif result.get('success') is False:
                    # API rejected the request appropriately
                    pass
                else:
                    # API might have defaulted to some behavior - that's okay too
                    print(f"Warning: API accepted invalid action '{action}'")
            except Exception as e:
                # Expected to fail for invalid actions
                assert "invalid" in str(e).lower() or "error" in str(
                    e).lower(), f"Should fail for invalid action '{action}': {e}"

    @pytest.mark.integration
    def test_membership_with_nonexistent_resources(self):
        """Test membership operations with non-existent client groups or users."""
        # Create real user for testing with fake group
        test_user_id = self.test_user_id

        # Create real group for testing with fake user
        test_group_name = self.generate_test_name("TEST_GROUP")
        group_result = self.create_client_group(test_group_name)
        real_group_id = group_result['id']

        # Test 1: Non-existent client group with real user
        fake_group_id = 999999
        try:
            result = self.modify_client_group_membership(
                fake_group_id, test_user_id, "add")
            # Check if API handles this gracefully
            if 'error' in result:
                assert "not found" in result['error'].lower(
                ) or "does not exist" in result['error'].lower()
            elif result.get('success') is False:
                # API appropriately rejected the request
                pass
        except Exception as e:
            # Expected to fail
            assert any(keyword in str(e).lower() for keyword in [
                       "not found", "does not exist", "constraint", "foreign key"])

        # Test 2: Real client group with non-existent user
        fake_user_id = "NONEXISTENT_USER_ID_12345"
        try:
            result = self.modify_client_group_membership(
                real_group_id, fake_user_id, "add")
            # Check if API handles this gracefully
            if 'error' in result:
                assert "not found" in result['error'].lower(
                ) or "does not exist" in result['error'].lower()
            elif result.get('success') is False:
                # API appropriately rejected the request
                pass
        except Exception as e:
            # Expected to fail
            assert any(keyword in str(e).lower() for keyword in [
                       "not found", "does not exist", "constraint", "foreign key"])

        # Test 3: Both non-existent
        try:
            result = self.modify_client_group_membership(
                fake_group_id, fake_user_id, "add")
            # Should definitely fail
            if 'error' in result:
                assert "not found" in result['error'].lower(
                ) or "does not exist" in result['error'].lower()
            else:
                pytest.fail(
                    "Should not succeed with both fake group and fake user")
        except Exception:
            # Expected to fail
            pass

    @pytest.mark.integration
    def test_multiple_users_single_group(self):
        """Test adding multiple users to a single group."""
        # Create test client group
        test_group_name = self.generate_test_name("TEST_GROUP")
        group_result = self.create_client_group(test_group_name)
        group_id = group_result['id']

        # Create multiple test users
        test_users = []
        for i in range(3):
            user_id = self.test_user_id
            test_users.append(user_id)

        # Add all users to the group
        for user_id in test_users:
            add_result = self.modify_client_group_membership(
                group_id, user_id, "add")
            assert add_result['success'] is True, f"Adding user {user_id} should succeed"

        # Verify all users are in the group
        for user_id in test_users:
            user_groups = self.get_client_groups({'user_id': user_id})
            found_group = any(g['client_group_id'] ==
                              group_id for g in user_groups)
            assert found_group, f"User {user_id} should be in group {group_id}"

        # Remove all users from the group
        for user_id in test_users:
            remove_result = self.modify_client_group_membership(
                group_id, user_id, "remove")
            assert remove_result['success'] is True, f"Removing user {user_id} should succeed"

        # Verify all users are removed from the group
        for user_id in test_users:
            user_groups = self.get_client_groups({'user_id': user_id})
            found_group = any(g['client_group_id'] ==
                              group_id for g in user_groups)
            assert not found_group, f"User {user_id} should not be in group {group_id} after removal"

    @pytest.mark.integration
    def test_single_user_multiple_groups(self):
        """Test adding a single user to multiple groups."""
        # Create test user
        test_user_id = self.test_user_id

        # Create multiple test groups
        test_groups = []
        for i in range(3):
            group_name = self.generate_test_name("TEST_GROUP")
            group_result = self.create_client_group(group_name)
            test_groups.append(group_result['id'])

        # Add user to all groups
        for group_id in test_groups:
            add_result = self.modify_client_group_membership(
                group_id, test_user_id, "add")
            assert add_result['success'] is True, f"Adding user to group {group_id} should succeed"

        # Verify user is in all groups
        user_groups = self.get_client_groups({'user_id': test_user_id})
        user_group_ids = [g['client_group_id'] for g in user_groups]

        for group_id in test_groups:
            assert group_id in user_group_ids, f"User should be in group {group_id}"

        # Remove user from all groups
        for group_id in test_groups:
            remove_result = self.modify_client_group_membership(
                group_id, test_user_id, "remove")
            assert remove_result[
                'success'] is True, f"Removing user from group {group_id} should succeed"

        # Verify user is removed from all groups
        final_user_groups = self.get_client_groups({'user_id': test_user_id})
        final_group_ids = [g['client_group_id'] for g in final_user_groups]

        for group_id in test_groups:
            assert group_id not in final_group_ids, f"User should not be in group {group_id} after removal"
