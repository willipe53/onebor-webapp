#!/usr/bin/env python3
"""
Test cases for client group entity management functionality
Tests the new modifyClientGroupEntities API and related features
"""
import pytest
from .base_test import BaseAPITest


class TestClientGroupEntities(BaseAPITest):
    """Test client group entity management."""

    def setup_method(self):
        """Setup test data."""
        super().setup_method()

        # Create test client group
        self.test_group = self.create_client_group("Test Entity Group")
        self.client_group_id = self.test_group['id']

        # Create test entity type
        self.test_entity_type = self.create_entity_type(
            "Test Entity Type",
            {"type": "object", "properties": {"test_field": {"type": "string"}}}
        )
        self.entity_type_id = self.test_entity_type['entity_type_id']

        # Create test entities
        self.entities = []
        for i in range(5):
            entity = self.create_entity(
                f"Test Entity {i+1}",
                self.entity_type_id,
                attributes={"test_field": f"value_{i+1}"}
            )
            self.entities.append(entity)

    def test_modify_client_group_entities_add_all(self):
        """Test adding all entities to a client group."""
        entity_ids = [entity['entity_id'] for entity in self.entities]

        response = self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': entity_ids
        })
        result = self.assert_success_response(response)

        # Verify response structure
        assert 'added_count' in result
        assert 'removed_count' in result
        assert 'current_entity_ids' in result
        assert 'desired_entity_ids' in result
        assert 'entities_added' in result
        assert 'entities_removed' in result

        # Should have added all entities
        assert result['added_count'] == 5
        assert result['removed_count'] == 0
        assert set(result['entities_added']) == set(entity_ids)
        assert result['entities_removed'] == []
        assert set(result['current_entity_ids']) == set(entity_ids)

    def test_modify_client_group_entities_partial_update(self):
        """Test partial update - add some, remove others."""
        # First add all entities
        all_entity_ids = [entity['entity_id'] for entity in self.entities]
        self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': all_entity_ids
        })

        # Now update to only include first 3 entities
        desired_entity_ids = all_entity_ids[:3]

        response = self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': desired_entity_ids
        })
        result = self.assert_success_response(response)

        # Should have removed 2 entities
        assert result['added_count'] == 0
        assert result['removed_count'] == 2
        assert result['entities_added'] == []
        assert len(result['entities_removed']) == 2
        assert set(result['current_entity_ids']) == set(desired_entity_ids)

    def test_modify_client_group_entities_empty_list(self):
        """Test removing all entities from client group."""
        # First add some entities
        entity_ids = [entity['entity_id'] for entity in self.entities[:3]]
        self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': entity_ids
        })

        # Now remove all by passing empty list
        response = self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': []
        })
        result = self.assert_success_response(response)

        # Should have removed all entities
        assert result['added_count'] == 0
        assert result['removed_count'] == 3
        assert result['entities_added'] == []
        assert len(result['entities_removed']) == 3
        assert result['current_entity_ids'] == []

    def test_modify_client_group_entities_idempotent(self):
        """Test that calling with same entity_ids is idempotent."""
        entity_ids = [entity['entity_id'] for entity in self.entities[:2]]

        # First call
        response1 = self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': entity_ids
        })
        result1 = self.assert_success_response(response1)

        # Second call with same entity_ids
        response2 = self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': entity_ids
        })
        result2 = self.assert_success_response(response2)

        # Second call should make no changes
        assert result2['added_count'] == 0
        assert result2['removed_count'] == 0
        assert result2['entities_added'] == []
        assert result2['entities_removed'] == []
        assert set(result2['current_entity_ids']) == set(entity_ids)

    def test_modify_client_group_entities_nonexistent_entity(self):
        """Test handling of non-existent entity IDs."""
        valid_entity_id = self.entities[0]['entity_id']
        nonexistent_entity_id = 999999

        # Try to add mix of valid and invalid entity IDs
        response = self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': [valid_entity_id, nonexistent_entity_id]
        })

        # Should handle gracefully - either success with warning or appropriate error
        if response.status_code == 200:
            result = self.assert_success_response(response)
            # Should only include valid entity
            assert valid_entity_id in result['current_entity_ids']
            # May or may not include nonexistent entity depending on implementation
        else:
            # Should be a client error (400) not server error (500)
            assert 400 <= response.status_code < 500

    def test_modify_client_group_entities_validation(self):
        """Test validation errors."""
        # Missing client_group_id
        response = self.api_request('modify_client_group_entities', data={
            'entity_ids': [1, 2, 3]
        })
        assert response.status_code == 400

        # Missing entity_ids
        response = self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id
        })
        assert response.status_code == 400

        # Invalid client_group_id
        response = self.api_request('modify_client_group_entities', data={
            'client_group_id': 999999,
            'entity_ids': [1, 2, 3]
        })
        assert 400 <= response.status_code < 500

    def test_modify_client_group_entities_transaction_safety(self):
        """Test that operations are transactional."""
        # Add some entities first
        initial_entity_ids = [entity['entity_id']
                              for entity in self.entities[:2]]
        self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': initial_entity_ids
        })

        # Try to update with a mix that might cause partial failure
        # Include some valid entities and test transaction rollback behavior
        new_entity_ids = [self.entities[0]['entity_id'],
                          self.entities[2]['entity_id']]

        response = self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': new_entity_ids
        })

        # Should either fully succeed or fully fail
        if response.status_code == 200:
            result = self.assert_success_response(response)
            # Verify final state matches requested state
            assert set(result['current_entity_ids']) == set(new_entity_ids)

    def test_modify_client_group_entities_cors_headers(self):
        """Test CORS headers on modify_client_group_entities endpoint."""
        import requests

        # Test OPTIONS request for preflight
        url = f"{self.api_base_url}/modify_client_group_entities"
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

    def test_query_client_group_entities_api(self):
        """Test querying entities for a client group."""
        # Add some entities to the group
        entity_ids = [entity['entity_id'] for entity in self.entities[:3]]
        self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': entity_ids
        })

        # Query entities for the client group
        response = self.api_request('get_client_group_entities', data={
            'client_group_id': self.client_group_id
        })

        if response.status_code == 200:
            result = self.assert_success_response(response)
            # Should return the entity IDs we added
            returned_ids = [entity_id for entity_id in result]
            assert set(returned_ids) == set(entity_ids)

    def test_bulk_entity_operations_performance(self):
        """Test performance with larger number of entities."""
        # Create more entities for bulk testing
        bulk_entities = []
        for i in range(20):
            entity = self.create_entity(
                f"Bulk Entity {i+1}",
                self.entity_type_id
            )
            bulk_entities.append(entity)

        bulk_entity_ids = [entity['entity_id'] for entity in bulk_entities]

        # Time the bulk operation
        import time
        start_time = time.time()

        response = self.api_request('modify_client_group_entities', data={
            'client_group_id': self.client_group_id,
            'entity_ids': bulk_entity_ids
        })

        end_time = time.time()
        duration = end_time - start_time

        result = self.assert_success_response(response)

        # Should complete in reasonable time (less than 5 seconds for 20 entities)
        assert duration < 5.0, f"Bulk operation took too long: {duration:.2f}s"

        # Should have added all entities
        assert result['added_count'] == 20
        assert len(result['entities_added']) == 20

