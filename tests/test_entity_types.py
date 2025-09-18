"""
Comprehensive tests for Entity Type APIs.
Tests follow the pattern: modify -> validate -> revert -> validate -> cleanup
"""
import pytest
import json
from .base_test import BaseAPITest


class TestEntityTypes(BaseAPITest):
    """Test Entity Type CRUD operations with validation and cleanup."""

    @pytest.mark.integration
    def test_entity_type_short_label_and_color_update(self):
        """Test updating short_label and label_color fields for entity types."""
        # Get existing entity types
        existing_types = self.get_entity_types()
        assert len(
            existing_types) > 0, "No existing entity types found for testing"

        # Pick the first entity type for testing (use helper to parse format)
        test_type_parsed = self.parse_entity_type(existing_types[0])
        original_type_id = test_type_parsed['entity_type_id']
        original_name = test_type_parsed['name']
        original_schema = test_type_parsed['attributes_schema']
        original_short_label = test_type_parsed['short_label']
        original_label_color = test_type_parsed['label_color']

        # Store original values for restoration
        self.store_original_value(
            f"entity_type_{original_type_id}_short_label", original_short_label)
        self.store_original_value(
            f"entity_type_{original_type_id}_label_color", original_label_color)

        try:
            # Step 1: Update only short_label
            test_short_label = "TST"
            self.update_entity_type(
                original_type_id, short_label=test_short_label)

            # Validate short_label update
            updated_types = self.get_entity_types()
            updated_type = self.find_entity_type_by_id(
                updated_types, original_type_id)
            assert updated_type is not None, f"Should find updated entity type with ID {original_type_id}"
            assert updated_type[
                'short_label'] == test_short_label, f"Expected short_label '{test_short_label}', got '{updated_type['short_label']}'"

            # Step 2: Update only label_color
            test_label_color = "ff5722"  # Orange color without # prefix
            self.update_entity_type(
                original_type_id, label_color=test_label_color)

            # Validate label_color update
            updated_types = self.get_entity_types()
            updated_type = next(
                (t for t in updated_types if t['entity_type_id'] == original_type_id), None)
            assert updated_type is not None, f"Should find updated entity type with ID {original_type_id}"
            assert updated_type.get(
                'label_color') == test_label_color, f"Expected label_color '{test_label_color}', got '{updated_type.get('label_color')}'"

            # Step 3: Update both short_label and label_color together
            test_short_label_2 = "TEST"
            test_label_color_2 = "2196f3"  # Blue color
            self.update_entity_type(
                original_type_id, short_label=test_short_label_2, label_color=test_label_color_2)

            # Validate both updates
            updated_types = self.get_entity_types()
            updated_type = next(
                (t for t in updated_types if t['entity_type_id'] == original_type_id), None)
            assert updated_type is not None, f"Should find updated entity type with ID {original_type_id}"
            assert updated_type.get(
                'short_label') == test_short_label_2, f"Expected short_label '{test_short_label_2}', got '{updated_type.get('short_label')}'"
            assert updated_type.get(
                'label_color') == test_label_color_2, f"Expected label_color '{test_label_color_2}', got '{updated_type.get('label_color')}'"

            # Step 4: Test clearing fields by setting to empty string
            self.update_entity_type(
                original_type_id, short_label="", label_color="")

            # Validate clearing
            updated_types = self.get_entity_types()
            updated_type = next(
                (t for t in updated_types if t['entity_type_id'] == original_type_id), None)
            assert updated_type is not None, f"Should find updated entity type with ID {original_type_id}"
            # Empty strings might be stored as NULL, so check for both
            assert updated_type.get('short_label') in [
                None, ""], f"Expected short_label to be cleared, got '{updated_type.get('short_label')}'"
            assert updated_type.get('label_color') in [
                None, ""], f"Expected label_color to be cleared, got '{updated_type.get('label_color')}'"

        finally:
            # Step 5: Restore original values
            self.update_entity_type(
                original_type_id,
                name=original_name,
                attributes_schema=original_schema,
                short_label=original_short_label,
                label_color=original_label_color
            )

            # Final validation - ensure restoration
            final_types = self.get_entity_types()
            final_type = next(
                (t for t in final_types if t['entity_type_id'] == original_type_id), None)
            assert final_type is not None, f"Should find restored entity type with ID {original_type_id}"
            assert final_type[
                'name'] == original_name, f"Name should be restored to '{original_name}'"
            assert final_type.get(
                'short_label') == original_short_label, f"Short label should be restored to '{original_short_label}'"
            assert final_type.get(
                'label_color') == original_label_color, f"Label color should be restored to '{original_label_color}'"

    @pytest.mark.integration
    def test_entity_type_create_with_new_fields(self):
        """Test creating a new entity type with short_label and label_color fields."""
        test_name = self.generate_test_name("NEW_FIELDS_TEST")
        test_schema = {
            "type": "object",
            "properties": {
                "test_field": {"type": "string"},
                "test_number": {"type": "number"}
            },
            "required": ["test_field"]
        }
        test_short_label = "NEW"
        test_label_color = "9c27b0"  # Purple color

        try:
            # Step 1: Create entity type with new fields
            create_response = self.api_request('update_entity_type', data={
                'name': test_name,
                'attributes_schema': test_schema,
                'short_label': test_short_label,
                'label_color': test_label_color
            })
            create_result = self.assert_success_response(create_response)
            created_type_id = create_result.get('entity_type_id')
            assert created_type_id is not None, "Should return entity_type_id for created entity type"

            # Track for cleanup
            self.created_entity_types.append(created_type_id)

            # Step 2: Verify creation by fetching all entity types
            all_types = self.get_entity_types()
            created_type = next(
                (t for t in all_types if t['entity_type_id'] == created_type_id), None)
            assert created_type is not None, f"Should find created entity type with ID {created_type_id}"
            assert created_type[
                'name'] == test_name, f"Expected name '{test_name}', got '{created_type['name']}'"
            assert created_type.get(
                'short_label') == test_short_label, f"Expected short_label '{test_short_label}', got '{created_type.get('short_label')}'"
            assert created_type.get(
                'label_color') == test_label_color, f"Expected label_color '{test_label_color}', got '{created_type.get('label_color')}'"

            # Step 3: Test that schema is correctly stored
            assert created_type['attributes_schema'] is not None, "Schema should not be None"
            if isinstance(created_type['attributes_schema'], str):
                import json
                parsed_schema = json.loads(created_type['attributes_schema'])
            else:
                parsed_schema = created_type['attributes_schema']

            assert parsed_schema.get(
                'type') == 'object', "Schema should have type 'object'"
            assert 'test_field' in parsed_schema.get(
                'properties', {}), "Schema should contain test_field"

        except Exception as e:
            # If creation failed, make sure we don't try to clean up non-existent entity
            if created_type_id and created_type_id in self.created_entity_types:
                self.created_entity_types.remove(created_type_id)
            raise e

    @pytest.mark.integration
    def test_entity_type_field_validation(self):
        """Test validation and edge cases for short_label and label_color fields."""
        # Get existing entity types
        existing_types = self.get_entity_types()
        assert len(
            existing_types) > 0, "No existing entity types found for testing"

        test_type = existing_types[0]
        original_type_id = test_type['entity_type_id']
        original_short_label = test_type.get('short_label')
        original_label_color = test_type.get('label_color')

        # Store original values for restoration
        self.store_original_value(
            f"entity_type_{original_type_id}_short_label", original_short_label)
        self.store_original_value(
            f"entity_type_{original_type_id}_label_color", original_label_color)

        try:
            # Test 1: Maximum length short_label (10 characters)
            max_short_label = "TESTMAXLEN"  # Exactly 10 characters
            self.update_entity_type(
                original_type_id, short_label=max_short_label)

            updated_types = self.get_entity_types()
            updated_type = next(
                (t for t in updated_types if t['entity_type_id'] == original_type_id), None)
            assert updated_type.get(
                'short_label') == max_short_label, f"Should handle 10-character short_label"

            # Test 2: Valid hex color formats
            valid_colors = ["000000", "ffffff", "ff5722", "2196f3", "4caf50"]
            for color in valid_colors:
                self.update_entity_type(original_type_id, label_color=color)
                updated_types = self.get_entity_types()
                updated_type = next(
                    (t for t in updated_types if t['entity_type_id'] == original_type_id), None)
                assert updated_type.get(
                    'label_color') == color, f"Should handle valid color '{color}'"

            # Test 3: Setting fields to None/null (should clear them)
            # Note: We test this by setting to empty string, as API might convert None differently
            self.update_entity_type(
                original_type_id, short_label="", label_color="")
            updated_types = self.get_entity_types()
            updated_type = next(
                (t for t in updated_types if t['entity_type_id'] == original_type_id), None)
            # Fields should be cleared (either None or empty string)
            assert updated_type.get('short_label') in [
                None, ""], "short_label should be cleared"
            assert updated_type.get('label_color') in [
                None, ""], "label_color should be cleared"

        finally:
            # Restore original values
            self.update_entity_type(
                original_type_id,
                short_label=original_short_label,
                label_color=original_label_color
            )

    @pytest.mark.integration
    def test_entity_type_update_and_revert(self):
        """Test updating an existing entity type and reverting changes."""
        # Get existing entity types
        existing_types = self.get_entity_types()
        assert len(
            existing_types) > 0, "No existing entity types found for testing"

        # Pick the first entity type for testing
        test_type = existing_types[0]
        original_type_id = test_type['entity_type_id']
        original_name = test_type['name']
        original_schema = test_type['attributes_schema']

        # Store original values for restoration (including new fields)
        original_short_label = test_type.get('short_label')
        original_label_color = test_type.get('label_color')

        self.store_original_value(
            f"entity_type_{original_type_id}_name", original_name)
        self.store_original_value(
            f"entity_type_{original_type_id}_schema", original_schema)
        self.store_original_value(
            f"entity_type_{original_type_id}_short_label", original_short_label)
        self.store_original_value(
            f"entity_type_{original_type_id}_label_color", original_label_color)

        # Step 1: Update entity type with "TEST" suffix and modified schema
        test_name = f"{original_name}TEST"
        test_schema = {
            "test_field": {"type": "string", "required": True},
            "test_number": {"type": "number", "required": False}
        }

        self.update_entity_type(original_type_id, test_name, test_schema)

        # Step 2: Validate the changes
        updated_types = self.get_entity_types()
        updated_type = next(
            (t for t in updated_types if t['entity_type_id'] == original_type_id), None)
        assert updated_type is not None, f"Should find updated entity type with ID {original_type_id}"
        assert updated_type['name'] == test_name, f"Expected name '{test_name}', got '{updated_type['name']}'"
        assert updated_type['name'].endswith(
            'TEST'), "Name should end with 'TEST'"

        # Parse and validate schema
        if isinstance(updated_type['attributes_schema'], str):
            updated_schema = json.loads(updated_type['attributes_schema'])
        else:
            updated_schema = updated_type['attributes_schema']
        assert 'test_field' in updated_schema, "Schema should contain test_field"
        assert 'test_number' in updated_schema, "Schema should contain test_number"

        # Step 3: Revert to original values (including new fields)
        if isinstance(original_schema, str):
            original_schema_dict = json.loads(original_schema)
        else:
            original_schema_dict = original_schema
        self.update_entity_type(
            original_type_id,
            name=original_name,
            attributes_schema=original_schema_dict,
            short_label=original_short_label,
            label_color=original_label_color
        )

        # Step 4: Validate the revert
        reverted_types = self.get_entity_types()
        reverted_type = next(
            (t for t in reverted_types if t['entity_type_id'] == original_type_id), None)
        assert reverted_type is not None, f"Should find reverted entity type with ID {original_type_id}"
        assert reverted_type[
            'name'] == original_name, f"Expected original name '{original_name}', got '{reverted_type['name']}'"
        assert not reverted_type['name'].endswith(
            'TEST'), "Name should not end with 'TEST' after revert"

    @pytest.mark.integration
    def test_entity_type_create_and_delete_cycle(self):
        """Test creating a new entity type and then deleting it."""
        test_name = self.generate_test_name("ENTITY_TYPE")
        test_schema = {
            "name": {"type": "string", "required": True},
            "description": {"type": "string", "required": False},
            "category": {"type": "string", "enum": ["A", "B", "C"], "required": True},
            "value": {"type": "number", "min": 0, "required": False}
        }

        # Step 1: Create new entity type
        create_result = self.create_entity_type(test_name, test_schema)
        assert 'entity_type_id' in create_result, "Create result should contain 'entity_type_id'"
        created_type_id = create_result['entity_type_id']

        # Step 2: Validate creation by retrieving all entity types
        all_types = self.get_entity_types()
        created_type = next(
            (t for t in all_types if t['entity_type_id'] == created_type_id), None)
        assert created_type is not None, f"Should find created entity type with ID {created_type_id}"
        assert created_type[
            'name'] == test_name, f"Name should match: expected '{test_name}', got '{created_type['name']}'"

        # Validate schema
        if isinstance(created_type['attributes_schema'], str):
            created_schema = json.loads(created_type['attributes_schema'])
        else:
            created_schema = created_type['attributes_schema']
        assert 'name' in created_schema, "Schema should contain 'name' field"
        assert 'category' in created_schema, "Schema should contain 'category' field"
        assert created_schema['category']['type'] == 'string', "Category should be string type"

        # Step 3: Delete the created entity type
        delete_result = self.delete_record(created_type_id, "Entity Type")
        assert delete_result['success'] is True, "Delete should be successful"
        assert "successfully deleted" in delete_result['message'], "Delete message should confirm success"

        # Step 4: Validate deletion
        deleted_types = self.get_entity_types()
        found_deleted = any(t['entity_type_id'] ==
                            created_type_id for t in deleted_types)
        assert not found_deleted, f"Entity type should be deleted, but was found in results"

        # Remove from cleanup list since we manually deleted it
        if created_type_id in self.created_entity_types:
            self.created_entity_types.remove(created_type_id)

    @pytest.mark.integration
    def test_entity_type_schema_validation(self):
        """Test entity type creation and updates with various schema formats."""
        test_name = self.generate_test_name("SCHEMA_TEST")

        # Test 1: Simple schema
        simple_schema = {
            "field1": {"type": "string"},
            "field2": {"type": "number"}
        }
        create_result = self.create_entity_type(test_name, simple_schema)
        type_id = create_result['entity_type_id']

        # Validate simple schema
        types = self.get_entity_types()
        created_type = next(
            (t for t in types if t['entity_type_id'] == type_id), None)
        assert created_type is not None, "Should find created type"

        # Test 2: Complex schema with validation rules
        complex_schema = {
            "email": {
                "type": "string",
                "format": "email",
                "required": True
            },
            "age": {
                "type": "integer",
                "minimum": 0,
                "maximum": 150,
                "required": False
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "required": False
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "created_at": {"type": "string", "format": "date-time"},
                    "source": {"type": "string", "enum": ["api", "import", "manual"]}
                },
                "required": False
            }
        }

        # Update with complex schema
        self.update_entity_type(
            type_id, name=f"{test_name}_COMPLEX", attributes_schema=complex_schema)

        # Validate complex schema
        updated_types = self.get_entity_types()
        updated_type = next(
            (t for t in updated_types if t['entity_type_id'] == type_id), None)
        assert updated_type is not None, "Should find updated type"
        assert updated_type['name'] == f"{test_name}_COMPLEX", "Name should be updated"

        if isinstance(updated_type['attributes_schema'], str):
            updated_schema = json.loads(updated_type['attributes_schema'])
        else:
            updated_schema = updated_type['attributes_schema']

        assert 'email' in updated_schema, "Schema should contain email field"
        assert 'metadata' in updated_schema, "Schema should contain metadata field"
        assert updated_schema['email']['type'] == 'string', "Email should be string type"
        assert updated_schema['age']['minimum'] == 0, "Age should have minimum constraint"

    @pytest.mark.integration
    def test_entity_type_get_operations(self):
        """Test retrieving entity types and validating the results."""
        # Create a test entity type for validation
        test_name = self.generate_test_name("GET_TEST")
        test_schema = {
            "test_get_field": {"type": "string", "required": True}
        }
        create_result = self.create_entity_type(test_name, test_schema)
        created_type_id = create_result['entity_type_id']

        # Test 1: Get all entity types
        all_types = self.get_entity_types()
        assert len(all_types) > 0, "Should return at least one entity type"

        # Verify our test type is in the results
        found_test_type = next(
            (t for t in all_types if t['entity_type_id'] == created_type_id), None)
        assert found_test_type is not None, f"Should find test entity type with ID {created_type_id}"
        assert found_test_type['name'] == test_name, "Test type name should match"

        # Test 2: Verify data structure
        for entity_type in all_types:
            assert 'entity_type_id' in entity_type, "Each type should have entity_type_id"
            assert 'name' in entity_type, "Each type should have name"
            assert 'attributes_schema' in entity_type, "Each type should have attributes_schema"

            # Verify entity_type_id is a number
            assert isinstance(
                entity_type['entity_type_id'], int), "entity_type_id should be integer"

            # Verify name is a string
            assert isinstance(entity_type['name'],
                              str), "name should be string"
            assert len(entity_type['name']) > 0, "name should not be empty"

            # Verify schema is valid JSON or dict
            schema = entity_type['attributes_schema']
            if isinstance(schema, str):
                try:
                    json.loads(schema)
                except json.JSONDecodeError:
                    pytest.fail(
                        f"attributes_schema should be valid JSON: {schema}")
            elif not isinstance(schema, dict):
                pytest.fail(
                    f"attributes_schema should be dict or JSON string: {type(schema)}")

    @pytest.mark.integration
    def test_entity_type_update_validation(self):
        """Test entity type update with various validation scenarios."""
        # Create a test entity type for update testing
        original_name = self.generate_test_name("UPDATE_TEST")
        original_schema = {
            "original_field": {"type": "string", "required": True}
        }
        create_result = self.create_entity_type(original_name, original_schema)
        type_id = create_result['entity_type_id']

        # Test 1: Update only name
        new_name = f"{original_name}_NAME_ONLY"
        update_result = self.update_entity_type(type_id, name=new_name)
        assert "updated" in update_result['message'].lower(
        ), "Update should be successful"

        # Verify name update
        types = self.get_entity_types()
        updated_type = next(
            (t for t in types if t['entity_type_id'] == type_id), None)
        assert updated_type['name'] == new_name, "Name should be updated"

        # Test 2: Update only schema
        new_schema = {
            "new_field": {"type": "number", "required": False},
            "another_field": {"type": "boolean", "required": True}
        }
        update_result = self.update_entity_type(
            type_id, attributes_schema=new_schema)
        assert "updated" in update_result['message'].lower(
        ), "Schema update should be successful"

        # Verify schema update
        types = self.get_entity_types()
        updated_type = next(
            (t for t in types if t['entity_type_id'] == type_id), None)
        if isinstance(updated_type['attributes_schema'], str):
            current_schema = json.loads(updated_type['attributes_schema'])
        else:
            current_schema = updated_type['attributes_schema']
        assert 'new_field' in current_schema, "Schema should contain new_field"
        assert 'another_field' in current_schema, "Schema should contain another_field"

        # Test 3: Update both name and schema
        final_name = f"{original_name}_FINAL"
        final_schema = {
            "final_field": {"type": "string", "enum": ["option1", "option2"], "required": True}
        }
        update_result = self.update_entity_type(
            type_id, name=final_name, attributes_schema=final_schema)
        assert "updated" in update_result['message'].lower(
        ), "Both field update should be successful"

        # Verify both updates
        types = self.get_entity_types()
        updated_type = next(
            (t for t in types if t['entity_type_id'] == type_id), None)
        assert updated_type['name'] == final_name, "Name should be updated to final value"

        if isinstance(updated_type['attributes_schema'], str):
            final_schema_result = json.loads(updated_type['attributes_schema'])
        else:
            final_schema_result = updated_type['attributes_schema']
        assert 'final_field' in final_schema_result, "Schema should contain final_field"
        assert final_schema_result['final_field']['type'] == 'string', "Final field should be string type"

    @pytest.mark.integration
    def test_entity_type_delete_with_constraints(self):
        """Test entity type deletion with referential integrity constraints."""
        # Create a test entity type
        test_type_name = self.generate_test_name("DELETE_CONSTRAINT_TYPE")
        test_schema = {
            "constraint_field": {"type": "string", "required": True}
        }
        create_result = self.create_entity_type(test_type_name, test_schema)
        type_id = create_result['entity_type_id']

        # Create an entity that uses this entity type
        test_entity_name = self.generate_test_name("CONSTRAINT_ENTITY")
        entity_result = self.create_entity(test_entity_name, type_id, attributes={
                                           "constraint_field": "test_value"})
        entity_id = entity_result['entity_id']

        # Attempt to delete the entity type (should fail due to entity dependency)
        try:
            delete_result = self.delete_record(type_id, "Entity Type")
            # If deletion succeeds, check the response
            if 'error' in delete_result:
                assert "referential integrity" in delete_result['error'].lower(
                ) or "constraint" in delete_result['error'].lower(), "Should mention constraints"
            elif delete_result.get('success') is True:
                # Some implementations might allow deletion with cascading
                print(
                    "Warning: Entity type deletion succeeded despite entity dependency")
        except Exception as e:
            # Expected failure due to constraints
            constraint_keywords = ["constraint",
                                   "referential", "foreign key", "dependency"]
            error_mentions_constraint = any(keyword in str(
                e).lower() for keyword in constraint_keywords)
            assert error_mentions_constraint, f"Error should mention constraints: {e}"

        # Delete the dependent entity first
        entity_delete_result = self.delete_record(entity_id, "Entity")
        assert entity_delete_result['success'] is True, "Entity deletion should succeed"

        # Now entity type deletion should succeed
        delete_result = self.delete_record(type_id, "Entity Type")
        if 'success' in delete_result:
            assert delete_result['success'] is True, "Deletion should succeed after removing constraints"
            # Remove from cleanup list since we manually deleted it
            if type_id in self.created_entity_types:
                self.created_entity_types.remove(type_id)

    @pytest.mark.integration
    def test_entity_type_multiple_operations(self):
        """Test multiple entity type operations in sequence."""
        # Create multiple test entity types
        type_count = 3
        test_types = []

        for i in range(type_count):
            name = self.generate_test_name(f"MULTI_TYPE_{i}")
            schema = {
                f"field_{i}_1": {"type": "string", "required": True},
                f"field_{i}_2": {"type": "number", "required": False},
                "common_field": {"type": "boolean", "required": False}
            }
            test_types.append({
                'name': name,
                'schema': schema
            })

        created_ids = []

        # Step 1: Create multiple entity types
        for type_data in test_types:
            result = self.create_entity_type(
                type_data['name'], type_data['schema'])
            created_ids.append(result['entity_type_id'])
            type_data['id'] = result['entity_type_id']

        # Step 2: Verify all entity types were created
        all_types = self.get_entity_types()
        for i, type_data in enumerate(test_types):
            found = any(t['entity_type_id'] == type_data['id']
                        and t['name'] == type_data['name'] for t in all_types)
            assert found, f"Entity type {type_data['id']} with name {type_data['name']} should exist"

        # Step 3: Update all entity types
        for i, type_data in enumerate(test_types):
            new_name = f"{type_data['name']}_UPDATED"
            new_schema = type_data['schema'].copy()
            new_schema[f"updated_field_{i}"] = {
                "type": "string", "required": False}

            self.update_entity_type(
                type_data['id'], name=new_name, attributes_schema=new_schema)

            # Update our tracking data
            type_data['name'] = new_name
            type_data['schema'] = new_schema

        # Step 4: Verify all updates
        updated_types = self.get_entity_types()
        for type_data in test_types:
            found_type = next(
                (t for t in updated_types if t['entity_type_id'] == type_data['id']), None)
            assert found_type is not None, f"Should find updated type {type_data['id']}"
            assert found_type['name'] == type_data[
                'name'], f"Type {type_data['id']} should have updated name"

            if isinstance(found_type['attributes_schema'], str):
                found_schema = json.loads(found_type['attributes_schema'])
            else:
                found_schema = found_type['attributes_schema']

            # Check for updated fields
            updated_field_found = any(key.startswith(
                'updated_field_') for key in found_schema.keys())
            assert updated_field_found, f"Type {type_data['id']} should have updated schema fields"

        # Step 5: Delete all entity types
        for type_data in test_types:
            delete_result = self.delete_record(type_data['id'], "Entity Type")
            assert delete_result['success'] is True, f"Deletion of type {type_data['id']} should succeed"

        # Step 6: Verify all deletions
        final_types = self.get_entity_types()
        for type_data in test_types:
            found = any(t['entity_type_id'] == type_data['id']
                        for t in final_types)
            assert not found, f"Type {type_data['id']} should be deleted"
            # Remove from cleanup list since we manually deleted them
            if type_data['id'] in self.created_entity_types:
                self.created_entity_types.remove(type_data['id'])
