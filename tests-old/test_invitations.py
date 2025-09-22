#!/usr/bin/env python3
"""
Test cases for invitation management functionality
Tests new invitation features added in the last week:
- Simplified invitation schema (no email/name fields)
- Invitation expiration via expires_at timestamp
- Invitation count APIs
- CORS handling
"""
import pytest
import time
from datetime import datetime, timedelta
from .base_test import BaseAPITest


class TestInvitations(BaseAPITest):
    """Test invitation management functionality."""

    def setup_method(self):
        """Set up tracking for test objects that need cleanup."""
        super().setup_method()
        self.test_invitations = []  # Track invitation codes for cleanup
        # Track client groups created for invitation tests
        self.test_client_groups_for_invitations = []

    def teardown_method(self):
        """Clean up test invitations and associated client groups."""
        print(
            f"\n🧹 Cleaning up {len(self.test_invitations)} test invitations...")

        # Delete test invitations (if there's a delete action)
        for invitation_code in self.test_invitations:
            try:
                # Try to delete invitation - check if there's a delete action available
                response = self.api_request('manage_invitation', data={
                    'action': 'delete',
                    'code': invitation_code
                })
                if response.status_code == 200:
                    print(f"   ✅ Deleted invitation: {invitation_code}")
                else:
                    print(
                        f"   ⚠️  Could not delete invitation {invitation_code}: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error deleting invitation {invitation_code}: {e}")

        # Delete test client groups created for invitations
        print(
            f"🧹 Cleaning up {len(self.test_client_groups_for_invitations)} test client groups...")
        for group_id in self.test_client_groups_for_invitations:
            try:
                response = self.api_request('delete_record', data={
                    'record_id': group_id,
                    'record_type': 'Client Group'
                })
                if response.status_code == 200:
                    print(f"   ✅ Deleted client group: {group_id}")
                else:
                    print(
                        f"   ❌ Failed to delete client group {group_id}: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error deleting client group {group_id}: {e}")

        super().teardown_method()

    def test_create_invitation_simplified_schema(self):
        """Test creating invitations with simplified schema (no email/name)."""
        # Create a client group first
        client_group = self.create_client_group("Invitation_Group")
        client_group_id = client_group['id']
        self.test_client_groups_for_invitations.append(
            client_group_id)  # Track for cleanup

        # Create invitation with simplified schema
        expires_at = (datetime.utcnow() + timedelta(days=7)
                      ).strftime('%Y-%m-%d %H:%M:%S')

        response = self.api_request('manage_invitation', data={
            'action': 'create',
            'client_group_id': client_group_id,
            'expires_at': expires_at
        })
        result = self.assert_success_response(response)

        # Track invitation for cleanup
        if 'code' in result:
            self.test_invitations.append(result['code'])

        # Verify response structure
        assert 'invitation_id' in result
        assert 'code' in result
        assert 'success' in result
        assert result['success'] is True

        # Verify no deprecated fields
        assert 'email' not in result
        assert 'name' not in result
        assert 'redeemed' not in result

        return result

    def test_get_invitations_by_client_group(self):
        """Test retrieving invitations for a specific client group."""
        # Create invitation
        invitation = self.test_create_invitation_simplified_schema()
        client_group_id = invitation['client_group_id']

        # Get invitations for the client group
        response = self.api_request('manage_invitation', data={
            'action': 'get',
            'client_group_id': client_group_id
        })
        result = self.assert_success_response(response)

        # Verify response is array
        assert isinstance(result, list)
        assert len(result) >= 1

        # Find our invitation
        found_invitation = None
        for inv in result:
            if inv['invitation_id'] == invitation['invitation_id']:
                found_invitation = inv
                break

        assert found_invitation is not None
        assert found_invitation['code'] == invitation['code']
        assert found_invitation['client_group_id'] == client_group_id

    def test_get_invitation_by_code(self):
        """Test retrieving invitation by code."""
        # Create invitation
        invitation = self.test_create_invitation_simplified_schema()

        # Get invitation by code
        response = self.api_request('manage_invitation', data={
            'action': 'get',
            'code': invitation['code']
        })
        result = self.assert_success_response(response)

        # Verify response is array with one item
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['invitation_id'] == invitation['invitation_id']
        assert result[0]['code'] == invitation['code']

    def test_expire_invitation_via_redeem(self):
        """Test expiring invitation by setting expires_at to NOW()."""
        # Create invitation
        invitation = self.test_create_invitation_simplified_schema()

        # Store original expires_at
        original_expires_at = invitation['expires_at']

        # "Redeem" (expire) the invitation
        response = self.api_request('manage_invitation', data={
            'action': 'redeem',
            'code': invitation['code']
        })
        result = self.assert_success_response(response)

        # Verify response
        assert 'invitation_id' in result
        assert 'client_group_id' in result
        assert result['invitation_id'] == invitation['invitation_id']

        # Verify invitation is now expired by fetching it
        response = self.api_request('manage_invitation', data={
            'action': 'get',
            'code': invitation['code']
        })
        result = self.assert_success_response(response)

        # Should still return the invitation (no filtering by expiration in get)
        assert len(result) == 1
        updated_invitation = result[0]

        # expires_at should be much earlier than original
        original_time = datetime.fromisoformat(
            original_expires_at.replace('Z', '+00:00'))
        updated_time = datetime.fromisoformat(
            updated_invitation['expires_at'].replace('Z', '+00:00'))

        # Updated time should be significantly earlier (expired)
        assert updated_time < original_time

    def test_invitation_count_api(self):
        """Test counting invitations."""
        # Create a client group and some invitations
        client_group = self.create_client_group("Test Count Group")
        client_group_id = client_group['id']
        self.test_client_groups_for_invitations.append(
            client_group_id)  # Track for cleanup

        # Get initial count
        response = self.api_request('manage_invitation', data={
            'action': 'get',
            'client_group_id': client_group_id,
            'count_only': True
        })
        initial_count = self.assert_success_response(response)
        assert isinstance(initial_count, int)

        # Create some invitations
        invitation1 = self.api_request('manage_invitation', data={
            'action': 'create',
            'client_group_id': client_group_id
        })
        result1 = self.assert_success_response(invitation1)
        if 'code' in result1:
            self.test_invitations.append(result1['code'])

        invitation2 = self.api_request('manage_invitation', data={
            'action': 'create',
            'client_group_id': client_group_id
        })
        result2 = self.assert_success_response(invitation2)
        if 'code' in result2:
            self.test_invitations.append(result2['code'])

        # Get updated count
        response = self.api_request('manage_invitation', data={
            'action': 'get',
            'client_group_id': client_group_id,
            'count_only': True
        })
        final_count = self.assert_success_response(response)

        # Should have 2 more invitations
        assert final_count == initial_count + 2

    def test_invitation_cors_headers(self):
        """Test CORS headers on invitation endpoints."""
        import requests

        # Test OPTIONS request for preflight
        url = f"{self.api_base_url}/manage_invitation"
        headers = {
            "Origin": "https://app.onebor.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }

        response = requests.options(url, headers=headers)
        assert response.status_code == 200

        # Verify CORS headers
        assert response.headers.get(
            'Access-Control-Allow-Origin') == 'https://app.onebor.com'
        assert 'POST' in response.headers.get(
            'Access-Control-Allow-Methods', '')
        assert 'Content-Type' in response.headers.get(
            'Access-Control-Allow-Headers', '')
        assert response.headers.get(
            'Access-Control-Allow-Credentials') == 'true'

    def test_invitation_validation_errors(self):
        """Test validation errors for invitation API."""
        # Test missing action
        response = self.api_request('manage_invitation', data={})
        assert response.status_code == 400

        # Test invalid action
        response = self.api_request('manage_invitation', data={
            'action': 'invalid_action'
        })
        assert response.status_code == 400

        # Test get without client_group_id or code
        response = self.api_request('manage_invitation', data={
            'action': 'get'
        })
        assert response.status_code == 400

        # Test create without client_group_id
        response = self.api_request('manage_invitation', data={
            'action': 'create'
        })
        assert response.status_code == 400

        # Test redeem without code
        response = self.api_request('manage_invitation', data={
            'action': 'redeem'
        })
        assert response.status_code == 400

    def test_invitation_auto_generated_fields(self):
        """Test that invitation_id and code are auto-generated."""
        client_group = self.create_client_group("Test Auto Gen Group")
        self.test_client_groups_for_invitations.append(
            client_group['id'])  # Track for cleanup

        # Create multiple invitations
        invitations = []
        for i in range(3):
            response = self.api_request('manage_invitation', data={
                'action': 'create',
                'client_group_id': client_group['id']
            })
            invitation = self.assert_success_response(response)
            invitations.append(invitation)
            # Track invitation for cleanup
            if 'code' in invitation:
                self.test_invitations.append(invitation['code'])

        # Verify each has unique ID and code
        ids = [inv['invitation_id'] for inv in invitations]
        codes = [inv['code'] for inv in invitations]

        assert len(set(ids)) == 3  # All unique IDs
        assert len(set(codes)) == 3  # All unique codes

        # Verify codes are reasonable length (should be meaningful)
        for code in codes:
            assert len(code) >= 6  # Reasonable minimum length
            assert isinstance(code, str)

    def test_invitation_expires_at_format(self):
        """Test that expires_at is in proper UTC format."""
        invitation = self.test_create_invitation_simplified_schema()

        expires_at = invitation['expires_at']

        # Should be able to parse as ISO datetime
        try:
            # Handle both with and without Z suffix
            if expires_at.endswith('Z'):
                parsed_time = datetime.fromisoformat(
                    expires_at.replace('Z', '+00:00'))
            else:
                parsed_time = datetime.fromisoformat(expires_at)
        except ValueError:
            pytest.fail(
                f"expires_at '{expires_at}' is not in valid ISO format")

        # Should be in the future (reasonable expiration)
        now = datetime.now(
            parsed_time.tzinfo) if parsed_time.tzinfo else datetime.now()
        assert parsed_time > now, "Invitation should expire in the future"

        # Should be reasonable timeframe (not too far in future)
        max_future = now + timedelta(days=365)  # 1 year max
        assert parsed_time < max_future, "Invitation expiration too far in future"
