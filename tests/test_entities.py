#!/usr/bin/env python3
"""
Comprehensive tests for Entity APIs.
Tests follow the pattern: modify -> validate -> revert -> validate -> cleanup
"""
import pytest
import json
from .base_test import BaseAPITest


class TestEntities(BaseAPITest):
    """Test Entity CRUD operations with validation and cleanup."""

    @pytest.mark.integration
    def test_entity_update_and_revert(self):
        """Test updating an existing entity and reverting changes."""
        # First, ensure we have an entity type to work with
        entity_types = self.get_entity_types()
        assert len(entity_types) > 0, "No entity types found for testing"
        test_entity_type_id = entity_types[0]['entity_type_id']

        # Get existing entities
        existing_entities = self.get_entities()
        if len(existing_entities) == 0:
            # Create a test entity if none exist
            create_result = self.create_entity(
                test_entity_name, test_entity_type_id)
            entity_id = create_result['entity_id']
            original_name = test_entity_name
            original_attributes = {}
        else:
            # Use existing entity
            test_entity = existing_entities[0]
            entity_id = test_entity['entity_id']
            original_name = test_entity['name']
            original_attributes = test_entity.get('attributes', {})

        # Store original values
        self.store_original_value(f"entity_{entity_id}_name", original_name)
        self.store_original_value(
            f"entity_{entity_id}_attributes", original_attributes)

        # Step 1: Update entity with "TEST" suffix and new attributes
        test_name = f"{original_name}TEST"
        test_attributes = {
            "test_field": "test_value",
            "test_number": 42,
            "test_boolean": True
        }

        self.update_entity(entity_id, name=test_name,
                           attributes=test_attributes)

        # Step 2: Validate the changes
        updated_entities = self.get_entities({'entity_id': entity_id})
        assert len(
            updated_entities) == 1, f"Expected 1 entity, got {len(updated_entities)}"
        updated_entity = updated_entities[0]
        assert updated_entity[
            'name'] == test_name, f"Expected name '{test_name}', got '{updated_entity['name']}'"
        assert updated_entity['name'].endswith(
            'TEST'), "Name should end with 'TEST'"

        # Validate attributes
        if isinstance(updated_entity.get('attributes'), str):
            updated_attrs = json.loads(updated_entity['attributes'])
        else:
            updated_attrs = updated_entity.get('attributes', {})

        assert updated_attrs.get(
            'test_field') == 'test_value', "Should have test_field attribute"
        assert updated_attrs.get(
            'test_number') == 42, "Should have test_number attribute"

        # Step 3: Revert to original values
        self.update_entity(entity_id, name=original_name,
                           attributes=original_attributes)

        # Step 4: Validate the revert
        reverted_entities = self.get_entities({'entity_id': entity_id})
        assert len(
            reverted_entities) == 1, f"Expected 1 entity, got {len(reverted_entities)}"
        reverted_entity = reverted_entities[0]
        assert reverted_entity[
            'name'] == original_name, f"Expected original name '{original_name}', got '{reverted_entity['name']}'"
        assert not reverted_entity['name'].endswith(
            'TEST'), "Name should not end with 'TEST' after revert"

    @pytest.mark.integration
    def test_entity_create_and_delete_cycle(self):
        """Test creating a new entity and then deleting it."""
        # Get an entity type to use
        entity_types = self.get_entity_types()
        assert len(entity_types) > 0, "No entity types available for testing"
        test_entity_type_id = entity_types[0]['entity_type_id']

        test_attributes = {
            "description": "Test entity for automated testing",
            "category": "test",
            "value": 100.50,
            "active": True
        }

        # Step 1: Create new entity
        create_result = self.create_entity(
            test_name, test_entity_type_id, attributes=test_attributes)
        assert 'entity_id' in create_result, "Create result should contain 'entity_id'"
        created_entity_id = create_result['entity_id']

        # Step 2: Validate creation by retrieving the entity
        created_entities = self.get_entities({'entity_id': created_entity_id})
        assert len(
            created_entities) == 1, f"Expected 1 entity with ID {created_entity_id}"
        created_entity = created_entities[0]
        assert created_entity['name'] == test_name, "Entity name should match"
        assert created_entity['entity_type_id'] == test_entity_type_id, "Entity type should match"

        # Validate attributes
        if isinstance(created_entity.get('attributes'), str):
            created_attrs = json.loads(created_entity['attributes'])
        else:
            created_attrs = created_entity.get('attributes', {})
        assert created_attrs.get(
            'description') == test_attributes['description'], "Description should match"
        assert created_attrs.get(
            'value') == test_attributes['value'], "Value should match"

        # Step 3: Delete the created entity
        delete_result = self.delete_record(created_entity_id, "Entity")
        assert delete_result['success'] is True, "Delete should be successful"
        assert "successfully deleted" in delete_result['message'], "Delete message should confirm success"

        # Step 4: Validate deletion
        deleted_entities = self.get_entities({'entity_id': created_entity_id})
        assert len(
            deleted_entities) == 0, f"Entity should be deleted, but found {len(deleted_entities)} entities"

        # Remove from cleanup list since we manually deleted it
        if created_entity_id in self.created_entities:
            self.created_entities.remove(created_entity_id)

    @pytest.mark.integration
    def test_entity_get_with_filters(self):
        """Test getting entities with various filter parameters."""
        # Create entity type and entities for filtering tests
        test_schema = {"filter_field": {"type": "string"}}
        type_result = self.create_entity_type(test_type_name, test_schema)
        test_entity_type_id = type_result['entity_type_id']

        # Create test entities
        test_entities = []
        for i in range(3):
            entity_result = self.create_entity(entity_name, test_entity_type_id,
                                               attributes={"filter_field": f"value_{i}"})
            test_entities.append({
                'id': entity_result['entity_id'],
                'name': entity_name
            })

        # Test 1: Get all entities (no filters)
        all_entities = self.get_entities()
        assert len(all_entities) >= len(
            test_entities), f"Should return at least {len(test_entities)} entities"

        # Test 2: Get by specific entity_id
        test_entity_id = test_entities[0]['id']
        id_filtered_entities = self.get_entities({'entity_id': test_entity_id})
        assert len(
            id_filtered_entities) == 1, f"Expected 1 entity for ID filter, got {len(id_filtered_entities)}"
        assert id_filtered_entities[0]['entity_id'] == test_entity_id

        # Test 3: Get by exact name
        test_entity_name = test_entities[1]['name']
        name_filtered_entities = self.get_entities({'name': test_entity_name})
        assert len(
            name_filtered_entities) >= 1, f"Expected at least 1 entity for name filter, got {len(name_filtered_entities)}"
        found_by_name = any(
            e['name'] == test_entity_name for e in name_filtered_entities)
        assert found_by_name, f"Should find entity with exact name '{test_entity_name}'"

        # Test 4: Get by partial name (LIKE search with %)
        partial_name = test_entity_name[:10] + "%"
        partial_filtered_entities = self.get_entities({'name': partial_name})
        assert len(
            partial_filtered_entities) >= 1, f"Expected at least 1 entity for partial name filter"

        # Test 5: Get by entity_type_id
        type_filtered_entities = self.get_entities(
            {'entity_type_id': test_entity_type_id})
        assert len(type_filtered_entities) >= len(
            test_entities), f"Should find at least {len(test_entities)} entities of this type"

        # Test 6: Get by non-existent ID
        nonexistent_entities = self.get_entities({'entity_id': 999999})
        assert len(
            nonexistent_entities) == 0, "Should return no entities for non-existent ID"

    @pytest.mark.integration
    def test_entity_parent_child_relationships(self):
        """Test entity parent-child relationships."""
        # Create entity type
        test_schema = {"level": {"type": "string"}}
        type_result = self.create_entity_type(test_type_name, test_schema)
        test_entity_type_id = type_result['entity_type_id']

        # Create parent entity
        parent_result = self.create_entity(parent_name, test_entity_type_id,
                                           attributes={"level": "parent"})
        parent_id = parent_result['entity_id']

        # Create child entity
        child_result = self.create_entity(child_name, test_entity_type_id,
                                          parent_entity_id=parent_id,
                                          attributes={"level": "child"})
        child_id = child_result['entity_id']

        # Validate parent-child relationship
        child_entities = self.get_entities({'entity_id': child_id})
        assert len(child_entities) == 1, "Should find child entity"
        child_entity = child_entities[0]
        assert child_entity['parent_entity_id'] == parent_id, "Child should reference correct parent"

        # Test getting entities by parent_entity_id
        children = self.get_entities({'parent_entity_id': parent_id})
        assert len(children) >= 1, "Should find at least one child"
        found_child = any(e['entity_id'] == child_id for e in children)
        assert found_child, "Should find our test child entity"

        # Test deleting parent with child (should fail due to constraints)
        try:
            delete_result = self.delete_record(parent_id, "Entity")
            if 'error' in delete_result:
                assert "referential integrity" in delete_result['error'].lower(
                ) or "constraint" in delete_result['error'].lower()
            elif delete_result.get('success') is True:
                print("Warning: Parent deletion succeeded despite child dependency")
        except Exception as e:
            # Expected failure due to constraints
            assert "constraint" in str(e).lower(
            ) or "referential" in str(e).lower()

        # Delete child first, then parent
        child_delete = self.delete_record(child_id, "Entity")
        assert child_delete['success'] is True, "Child deletion should succeed"

        parent_delete = self.delete_record(parent_id, "Entity")
        assert parent_delete['success'] is True, "Parent deletion should succeed after child removal"

        # Remove from cleanup lists
        if child_id in self.created_entities:
            self.created_entities.remove(child_id)
        if parent_id in self.created_entities:
            self.created_entities.remove(parent_id)

    @pytest.mark.integration
    def test_entity_attributes_operations(self):
        """Test entity attribute management."""
        # Create entity type with schema
        test_schema = {
            "string_field": {"type": "string"},
            "number_field": {"type": "number"},
            "boolean_field": {"type": "boolean"},
            "object_field": {"type": "object"}
        }
        type_result = self.create_entity_type(test_type_name, test_schema)
        test_entity_type_id = type_result['entity_type_id']

        # Create entity with initial attributes
        initial_attributes = {
            "string_field": "initial_value",
            "number_field": 100,
            "boolean_field": True,
            "object_field": {"nested": "data", "count": 5}
        }

        entity_result = self.create_entity(entity_name, test_entity_type_id,
                                           attributes=initial_attributes)
        entity_id = entity_result['entity_id']

        # Test 1: Update specific attributes
        updated_attributes = {
            "string_field": "updated_value",
            "number_field": 200,
            "new_field": "added_dynamically"
        }

        self.update_entity(entity_id, attributes=updated_attributes)

        # Verify attribute updates
        updated_entities = self.get_entities({'entity_id': entity_id})
        updated_entity = updated_entities[0]

        if isinstance(updated_entity.get('attributes'), str):
            current_attrs = json.loads(updated_entity['attributes'])
        else:
            current_attrs = updated_entity.get('attributes', {})

        assert current_attrs.get(
            'string_field') == 'updated_value', "String field should be updated"
        assert current_attrs.get(
            'number_field') == 200, "Number field should be updated"
        assert current_attrs.get(
            'new_field') == 'added_dynamically', "New field should be added"
        # Boolean field should remain unchanged
        assert current_attrs.get(
            'boolean_field') is True, "Boolean field should remain unchanged"

        # Test 2: Complex nested object updates
        complex_attributes = {
            "object_field": {
                "nested": "updated_nested_data",
                "count": 10,
                "new_nested": {"deep": "value"}
            }
        }

        self.update_entity(entity_id, attributes=complex_attributes)

        # Verify complex updates
        complex_entities = self.get_entities({'entity_id': entity_id})
        complex_entity = complex_entities[0]

        if isinstance(complex_entity.get('attributes'), str):
            complex_attrs = json.loads(complex_entity['attributes'])
        else:
            complex_attrs = complex_entity.get('attributes', {})

        object_field = complex_attrs.get('object_field', {})
        assert object_field.get(
            'nested') == 'updated_nested_data', "Nested string should be updated"
        assert object_field.get(
            'count') == 10, "Nested count should be updated"
        assert object_field.get('new_nested', {}).get(
            'deep') == 'value', "Deep nested value should be set"

    @pytest.mark.integration
    def test_entity_multiple_operations(self):
        """Test multiple entity operations in sequence."""
        # Create entity type
        test_schema = {"index": {"type": "number"}}
        type_result = self.create_entity_type(test_type_name, test_schema)
        test_entity_type_id = type_result['entity_type_id']

        # Create multiple test entities
        entity_count = 3
        test_entities = []

        for i in range(entity_count):
            entity_attributes = {"index": i,
                                 "description": f"Entity number {i}"}

            entity_result = self.create_entity(entity_name, test_entity_type_id,
                                               attributes=entity_attributes)
            test_entities.append({
                'id': entity_result['entity_id'],
                'name': entity_name,
                'attributes': entity_attributes
            })

        # Step 1: Verify all entities were created
        all_entities = self.get_entities(
            {'entity_type_id': test_entity_type_id})
        created_entity_ids = [e['id'] for e in test_entities]

        for entity_data in test_entities:
            found = any(e['entity_id'] == entity_data['id'] and e['name'] == entity_data['name']
                        for e in all_entities)
            assert found, f"Entity {entity_data['id']} with name {entity_data['name']} should exist"

        # Step 2: Update all entities
        for i, entity_data in enumerate(test_entities):
            new_name = f"{entity_data['name']}_UPDATED"
            new_attributes = entity_data['attributes'].copy()
            new_attributes['updated'] = True
            new_attributes['update_timestamp'] = self.get_test_timestamp()

            self.update_entity(
                entity_data['id'], name=new_name, attributes=new_attributes)

            # Update tracking data
            entity_data['name'] = new_name
            entity_data['attributes'] = new_attributes

        # Step 3: Verify all updates
        for entity_data in test_entities:
            entities = self.get_entities({'entity_id': entity_data['id']})
            assert len(
                entities) == 1, f"Should find exactly one entity with ID {entity_data['id']}"
            entity = entities[0]
            assert entity['name'] == entity_data[
                'name'], f"Entity {entity_data['id']} should have updated name"

            if isinstance(entity.get('attributes'), str):
                entity_attrs = json.loads(entity['attributes'])
            else:
                entity_attrs = entity.get('attributes', {})

            assert entity_attrs.get(
                'updated') is True, f"Entity {entity_data['id']} should have updated flag"

        # Step 4: Delete all entities
        for entity_data in test_entities:
            delete_result = self.delete_record(entity_data['id'], "Entity")
            assert delete_result[
                'success'] is True, f"Deletion of entity {entity_data['id']} should succeed"

        # Step 5: Verify all deletions
        for entity_data in test_entities:
            entities = self.get_entities({'entity_id': entity_data['id']})
            assert len(
                entities) == 0, f"Entity {entity_data['id']} should be deleted"
            # Remove from cleanup list since we manually deleted them
            if entity_data['id'] in self.created_entities:
                self.created_entities.remove(entity_data['id'])
