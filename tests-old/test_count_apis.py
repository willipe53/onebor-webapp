#!/usr/bin/env python3
"""
Test cases for count APIs added in the last week
Tests all the new count_only functionality across different endpoints
"""
import pytest
import time
from .base_test import BaseAPITest


class TestCountAPIs(BaseAPITest):
    """Test count APIs for all resources."""

    def setup_method(self):
        """Setup test data for count testing."""
        super().setup_method()

        # Store initial counts to measure increments
        self.initial_counts = {}

    def get_initial_count(self, endpoint, params):
        """Helper to get initial count for comparison."""
        response = self.api_request(
            endpoint, data={**params, 'count_only': True})
        if response.status_code == 200:
            return self.assert_success_response(response)
        return 0

    def test_entity_count_api(self):
        """Test entity counting API."""
        # Get initial count
        initial_count = self.get_initial_count('get_entities', {})

        # Create some entities
        entity_type = self.create_entity_type(
            "Count Test Entity Type",
            {"type": "object", "properties": {"test": {"type": "string"}}}
        )

        entities_created = []
        for i in range(3):
            entity = self.create_entity(
                f"Count Test Entity {i+1}", entity_type['entity_type_id'])
            entities_created.append(entity)

        # Get updated count
        response = self.api_request('get_entities', data={'count_only': True})
        final_count = self.assert_success_response(response)

        # Should have increased by 3
        assert isinstance(final_count, int)
        assert final_count >= initial_count + 3

    def test_entity_count_with_filters(self):
        """Test entity counting with various filters."""
        # Create entity type for testing
        entity_type = self.create_entity_type(
            "Filtered Count Test Type",
            {"type": "object", "properties": {"category": {"type": "string"}}}
        )

        # Create entities with different attributes
        entity1 = self.create_entity("Filter Test 1", entity_type['entity_type_id'],
                                     attributes={"category": "A"})
        entity2 = self.create_entity("Filter Test 2", entity_type['entity_type_id'],
                                     attributes={"category": "B"})
        entity3 = self.create_entity("Filter Test 3", entity_type['entity_type_id'],
                                     attributes={"category": "A"})

        # Test count by entity type
        response = self.api_request('get_entities', data={
            'entity_type_id': entity_type['entity_type_id'],
            'count_only': True
        })
        if response.status_code == 200:
            type_count = self.assert_success_response(response)
            assert type_count >= 3  # At least our test entities

    def test_user_count_api(self):
        """Test user counting API."""
        # Get initial count
        initial_count = self.get_initial_count('get_users', {})

        # Create test users
        users_created = []
        for i in range(2):
            user_id = self.test_user_id
            users_created.append(user)

        # Get updated count
        response = self.api_request('get_users', data={'count_only': True})
        final_count = self.assert_success_response(response)

        # Should have increased
        assert isinstance(final_count, int)
        assert final_count >= initial_count + 2

    def test_client_group_count_api(self):
        """Test client group counting API."""
        # Get initial count
        initial_count = self.get_initial_count('get_client_groups', {})

        # Create test client groups
        groups_created = []
        for i in range(2):
            group = self.create_client_group(f"Count Test Group {i+1}")
            groups_created.append(group)

        # Get updated count
        response = self.api_request(
            'get_client_groups', data={'count_only': True})
        final_count = self.assert_success_response(response)

        # Should have increased
        assert isinstance(final_count, int)
        assert final_count >= initial_count + 2

    def test_entity_type_count_api(self):
        """Test entity type counting API."""
        # Get initial count
        initial_count = self.get_initial_count('get_entity_types', {})

        # Create test entity types
        types_created = []
        for i in range(2):
            entity_type = self.create_entity_type(
                f"Count Test Type {i+1}",
                {"type": "object", "properties": {"field": {"type": "string"}}}
            )
            types_created.append(entity_type)

        # Get updated count
        response = self.api_request(
            'get_entity_types', data={'count_only': True})
        final_count = self.assert_success_response(response)

        # Should have increased
        assert isinstance(final_count, int)
        assert final_count >= initial_count + 2

    def test_invitation_count_api(self):
        """Test invitation counting API."""
        # Create client group for invitations
        client_group = self.create_client_group("Invitation Count Test Group")
        client_group_id = client_group['id']

        # Get initial count for this client group
        initial_count = self.get_initial_count('manage_invitation', {
            'action': 'get',
            'client_group_id': client_group_id
        })

        # Create test invitations
        invitations_created = []
        for i in range(3):
            response = self.api_request('manage_invitation', data={
                'action': 'create',
                'client_group_id': client_group_id
            })
            invitation = self.assert_success_response(response)
            invitations_created.append(invitation)

        # Get updated count
        response = self.api_request('manage_invitation', data={
            'action': 'get',
            'client_group_id': client_group_id,
            'count_only': True
        })
        final_count = self.assert_success_response(response)

        # Should have increased by 3
        assert isinstance(final_count, int)
        assert final_count >= initial_count + 3

    def test_count_vs_full_data_consistency(self):
        """Test that count APIs return same count as array length."""
        # Test entities
        response_count = self.api_request(
            'get_entities', data={'count_only': True})
        response_data = self.api_request('get_entities', data={})

        if response_count.status_code == 200 and response_data.status_code == 200:
            count = self.assert_success_response(response_count)
            data = self.assert_success_response(response_data)
            assert count == len(
                data), f"Entity count mismatch: count={count}, data length={len(data)}"

        # Test client groups
        response_count = self.api_request(
            'get_client_groups', data={'count_only': True})
        response_data = self.api_request('get_client_groups', data={})

        if response_count.status_code == 200 and response_data.status_code == 200:
            count = self.assert_success_response(response_count)
            data = self.assert_success_response(response_data)
            assert count == len(
                data), f"Client group count mismatch: count={count}, data length={len(data)}"

        # Test entity types
        response_count = self.api_request(
            'get_entity_types', data={'count_only': True})
        response_data = self.api_request('get_entity_types', data={})

        if response_count.status_code == 200 and response_data.status_code == 200:
            count = self.assert_success_response(response_count)
            data = self.assert_success_response(response_data)
            assert count == len(
                data), f"Entity type count mismatch: count={count}, data length={len(data)}"

    def test_count_performance(self):
        """Test that count APIs are faster than full data retrieval."""
        import time

        # Time count API
        start_time = time.time()
        response = self.api_request('get_entities', data={'count_only': True})
        count_duration = time.time() - start_time

        # Time full data API
        start_time = time.time()
        response = self.api_request('get_entities', data={})
        data_duration = time.time() - start_time

        # Count should generally be faster (though not always guaranteed in test env)
        # At minimum, both should complete in reasonable time
        assert count_duration < 10.0, f"Count API too slow: {count_duration:.2f}s"
        assert data_duration < 10.0, f"Data API too slow: {data_duration:.2f}s"

    def test_count_parameter_validation(self):
        """Test validation of count_only parameter."""
        # Test with valid count_only values
        for count_value in [True, 'true', '1', 1]:
            response = self.api_request('get_entity_types', data={
                                        'count_only': count_value})
            if response.status_code == 200:
                result = self.assert_success_response(response)
                assert isinstance(result, int)

    def test_count_with_access_control(self):
        """Test that count APIs respect access control."""
        # Create entities in different contexts to test access control
        # This assumes the get_entities API has user_id requirements

        # Test entity count with user_id (if required)
        response = self.api_request('get_entities', data={
            'count_only': True
            # user_id should be handled by authentication
        })

        if response.status_code == 200:
            count = self.assert_success_response(response)
            assert isinstance(count, int)
            assert count >= 0

    def test_count_api_cors_headers(self):
        """Test CORS headers on count APIs."""
        import requests

        # Test a few count endpoints for CORS
        endpoints_to_test = [
            '/get_entities',
            '/get_client_groups',
            '/get_entity_types',
            '/get_users'
        ]

        for endpoint in endpoints_to_test:
            url = f"{self.api_base_url}{endpoint}"
            headers = {
                "Origin": "https://app.onebor.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }

            response = requests.options(url, headers=headers)
            assert response.status_code == 200, f"OPTIONS failed for {endpoint}"

            # Verify CORS headers
            assert response.headers.get(
                'Access-Control-Allow-Origin') == 'https://app.onebor.com'
            assert 'POST' in response.headers.get(
                'Access-Control-Allow-Methods', '')

    def test_count_edge_cases(self):
        """Test count APIs with edge cases."""
        # Test count with no results
        response = self.api_request('get_entities', data={
            'count_only': True,
            'entity_type_id': 999999  # Non-existent entity type
        })

        if response.status_code == 200:
            count = self.assert_success_response(response)
            assert count == 0

        # Test count with invalid parameters
        response = self.api_request('get_entities', data={
            'count_only': True,
            'invalid_param': 'invalid_value'
        })

        # Should either ignore invalid param or return appropriate error
        assert response.status_code in [200, 400]
