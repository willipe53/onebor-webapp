# API Testing Framework

This comprehensive testing framework provides automated tests for all Panda API endpoints with validation and cleanup capabilities.

## Overview

The testing framework follows the pattern you specified:

1. **Modify** - Make changes to data (create/update)
2. **Validate** - Verify the changes took effect
3. **Revert** - Restore original state
4. **Validate** - Confirm revert was successful
5. **Cleanup** - Remove any test data created

## Test Structure

### Base Test Class

- `base_test.py` - Provides authentication, utilities, and automatic cleanup
- Handles AWS Cognito authentication
- Tracks created resources for automatic cleanup
- Provides helper methods for all API operations

### Test Files

- `test_client_groups.py` - Client Group CRUD operations
- `test_users.py` - User CRUD operations
- `test_entity_types.py` - Entity Type CRUD operations
- `test_entities.py` - Entity CRUD operations
- `test_client_group_membership.py` - User-Group association management
- `test_valid_entities.py` - Valid entities retrieval
- `test_delete_record.py` - Record deletion with referential integrity

## Setup

1. **Install dependencies:**

   ```bash
   cd tests
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   Copy `env_example.txt` to `.env` and update with your values:

   ```bash
   cp env_example.txt .env
   ```

   Required environment variables:

   ```
   COGNITO_USER_POOL_ID=us-east-2_yourpoolid
   COGNITO_CLIENT_ID=yourclientid
   TEST_USERNAME=test@example.com
   TEST_PASSWORD=TestPassword123!
   API_BASE_URL=https://zwkvk3lyl3.execute-api.us-east-2.amazonaws.com/dev
   AWS_REGION=us-east-2
   ```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
pytest test_client_groups.py
pytest test_users.py
pytest test_entities.py
```

### Run Specific Test Methods

```bash
pytest test_client_groups.py::TestClientGroups::test_client_group_update_and_revert
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Integration Tests Only

```bash
pytest -m integration
```

## Test Examples

### Client Groups Test Example

Following your specified pattern:

```python
def test_client_group_update_and_revert(self):
    # Get existing client group
    existing_groups = self.get_client_groups()
    test_group = existing_groups[0]
    original_name = test_group['name']

    # Step 1: Update name with "TEST" suffix
    test_name = f"{original_name}TEST"
    self.update_client_group(test_group['client_group_id'], test_name)

    # Step 2: Validate change
    updated_groups = self.get_client_groups({'client_group_id': test_group['client_group_id']})
    assert updated_groups[0]['name'].endswith('TEST')

    # Step 3: Revert to original
    self.update_client_group(test_group['client_group_id'], original_name)

    # Step 4: Validate revert
    reverted_groups = self.get_client_groups({'client_group_id': test_group['client_group_id']})
    assert not reverted_groups[0]['name'].endswith('TEST')
```

### Create and Delete Cycle Example

```python
def test_entity_type_create_and_delete_cycle(self):
    # Step 1: Create new entity type
    test_name = self.generate_test_name("ENTITY_TYPE")
    test_schema = {"name": {"type": "string", "required": True}}
    create_result = self.create_entity_type(test_name, test_schema)

    # Step 2: Validate creation
    all_types = self.get_entity_types()
    found = any(t['entity_type_id'] == create_result['entity_type_id'] for t in all_types)
    assert found

    # Step 3: Delete
    delete_result = self.delete_record(create_result['entity_type_id'], "Entity Type")
    assert delete_result['success'] is True

    # Step 4: Validate deletion
    deleted_types = self.get_entity_types()
    found_after = any(t['entity_type_id'] == create_result['entity_type_id'] for t in deleted_types)
    assert not found_after
```

## API Coverage

### Client Groups (`/get_client_groups`, `/update_client_group`)

- ✅ Update existing group and revert
- ✅ Create new group and delete
- ✅ Filter by ID, name, user_id with exact and partial matches
- ✅ Referential integrity constraints
- ✅ Multiple operations in sequence

### Users (`/get_users`, `/update_user`)

- ✅ Update existing user and revert
- ✅ Create new user (upsert) and delete
- ✅ Filter by user_id, email, name with exact and partial matches
- ✅ Upsert behavior testing
- ✅ Referential integrity constraints

### Entity Types (`/get_entity_types`, `/update_entity_type`)

- ✅ Update existing type and revert
- ✅ Create new type and delete
- ✅ Complex JSON schema validation
- ✅ Schema format testing (simple and complex)
- ✅ Referential integrity with entities

### Entities (`/get_entities`, `/update_entity`)

- ✅ Update existing entity and revert
- ✅ Create new entity and delete
- ✅ Filter by entity_id, name, entity_type_id, parent_entity_id
- ✅ Parent-child relationships
- ✅ JSON attributes management
- ✅ Complex attribute updates

### Client Group Membership (`/modify_client_group_membership`)

- ✅ Add/remove user membership cycle
- ✅ Handle duplicate additions gracefully
- ✅ Handle removal of non-members gracefully
- ✅ Action variations (add, insert, del, delete, remove)
- ✅ Invalid action handling
- ✅ Multiple users per group
- ✅ Single user in multiple groups

### Valid Entities (`/get_valid_entities`)

- ✅ Filter by client_group_id
- ✅ Filter by user_id
- ✅ Combined filters
- ✅ Response format consistency
- ✅ Non-existent resource handling

### Delete Record (`/delete_record`)

- ✅ All record types (Client Group, User, Entity, Entity Type)
- ✅ Referential integrity constraints
- ✅ Cascading deletion prevention
- ✅ Error handling for constraints

## Features

### Automatic Cleanup

- All created resources are automatically tracked and cleaned up after each test
- Handles cleanup order to respect foreign key constraints
- Warns about cleanup failures without stopping test execution

### Authentication

- Automatic AWS Cognito authentication using ID tokens
- Token refresh handling
- Configurable test user credentials

### Robust Error Handling

- Graceful handling of API errors
- Detailed assertion messages
- Support for various API response formats

### Flexible Filtering

- Tests all documented filter parameters
- Validates exact and partial (LIKE) matching
- Tests edge cases and invalid parameters

### Data Validation

- Comprehensive response structure validation
- JSON schema validation for complex attributes
- Type checking and format validation

## Best Practices

1. **Test Isolation** - Each test is independent and cleans up after itself
2. **Unique Test Data** - Uses timestamps to ensure unique test data
3. **Comprehensive Coverage** - Tests normal operations, edge cases, and error conditions
4. **Clear Assertions** - Descriptive error messages for failed assertions
5. **Resource Management** - Automatic tracking and cleanup of created resources

## Troubleshooting

### Authentication Issues

- Verify Cognito pool ID and client ID are correct
- Ensure test user exists and password is correct
- Check AWS region setting

### API Connection Issues

- Verify API base URL is correct
- Check network connectivity
- Ensure API Gateway is deployed and accessible

### Test Failures

- Check if test data conflicts with existing data
- Verify API responses match expected format
- Review cleanup warnings for resource management issues

## Extending Tests

To add new test cases:

1. Inherit from `BaseAPITest`
2. Use `self.generate_test_name()` for unique names
3. Track created resources using the provided methods
4. Follow the modify→validate→revert→validate pattern
5. Mark tests with `@pytest.mark.integration`

Example:

```python
class TestNewFeature(BaseAPITest):
    @pytest.mark.integration
    def test_new_operation(self):
        # Your test implementation
        pass
```

