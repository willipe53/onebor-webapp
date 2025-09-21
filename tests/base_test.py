#!/usr/bin/env python3
"""
Base test class providing authentication and utility methods for API testing.
"""
import os
import json
import time
import boto3
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables
# Look for .env file in the tests directory
import pathlib
current_dir = pathlib.Path(__file__).parent
env_path = current_dir / '.env'
load_dotenv(env_path)


class BaseAPITest:
    """Base class for API testing with authentication and utilities."""

    def setup_method(self):
        """Setup before each test method with detailed progress tracking."""
        print("🔧 Setting up test environment...")

        print("   📝 Loading configuration...")
        self.api_base_url = os.getenv(
            'API_BASE_URL', 'https://zwkvk3lyl3.execute-api.us-east-2.amazonaws.com/dev')
        self.cognito_user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
        self.cognito_client_id = os.getenv('COGNITO_CLIENT_ID')
        self.test_username = os.getenv('TEST_USERNAME')
        self.test_password = os.getenv('TEST_PASSWORD')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-2')

        self.access_token = None

        print("   🌐 Configuring AWS client...")
        # Configure boto3 client with timeout settings to prevent hanging
        from botocore.config import Config
        config = Config(
            region_name=self.aws_region,
            retries={'max_attempts': 3, 'mode': 'standard'},
            read_timeout=30,
            connect_timeout=10
        )
        self.cognito_client = boto3.client('cognito-idp', config=config)

        print("   📋 Initializing tracking lists...")
        # Track created resources for cleanup
        self.created_client_groups: List[int] = []
        self.created_entities: List[int] = []
        self.created_entity_types: List[int] = []
        self.original_values: Dict[str, Any] = {}

        # Track test modifications for cleanup
        self.test_modifications: List[Dict[str, Any]] = []

        print("   🔐 Authenticating...")
        self.authenticate()

        print("   👤 Getting test user ID...")
        # Get the test user's database ID
        self.test_user_id = self.get_test_user_id()

        print("   ✅ Test setup completed successfully")

    def teardown_method(self):
        """Cleanup after each test method."""
        # Cleanup is now handled by the cleanup_test_objects.py script
        # This prevents issues with referential integrity during test runs
        pass

    def authenticate(self) -> str:
        """Authenticate with Cognito and get access token with timeout protection."""
        print("🔐 Authenticating with AWS Cognito...")

        try:
            # Try ADMIN_NO_SRP_AUTH first (requires ALLOW_ADMIN_USER_PASSWORD_AUTH)
            print("   Trying ADMIN_NO_SRP_AUTH flow...")
            response = self.cognito_client.admin_initiate_auth(
                UserPoolId=self.cognito_user_pool_id,
                ClientId=self.cognito_client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': self.test_username,
                    'PASSWORD': self.test_password
                }
            )
            self.access_token = response['AuthenticationResult']['IdToken']
            print("   ✅ Authentication successful")
            return self.access_token
        except Exception as admin_auth_error:
            print(f"   ❌ ADMIN_NO_SRP_AUTH failed: {admin_auth_error}")
            # If ADMIN_NO_SRP_AUTH fails, try USER_PASSWORD_AUTH
            try:
                print("   Trying USER_PASSWORD_AUTH flow...")
                response = self.cognito_client.initiate_auth(
                    ClientId=self.cognito_client_id,
                    AuthFlow='USER_PASSWORD_AUTH',
                    AuthParameters={
                        'USERNAME': self.test_username,
                        'PASSWORD': self.test_password
                    }
                )
                self.access_token = response['AuthenticationResult']['IdToken']
                print("   ✅ Authentication successful")
                return self.access_token
            except Exception as user_auth_error:
                print(f"   ❌ USER_PASSWORD_AUTH failed: {user_auth_error}")
                raise Exception(f"Authentication failed with both auth flows. "
                                f"ADMIN_NO_SRP_AUTH error: {admin_auth_error}. "
                                f"USER_PASSWORD_AUTH error: {user_auth_error}. "
                                f"Please enable ALLOW_ADMIN_USER_PASSWORD_AUTH or ALLOW_USER_PASSWORD_AUTH in your Cognito client settings.")

    def get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        if not self.access_token:
            self.authenticate()
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }

    def api_request(self, endpoint: str, method: str = 'POST', data: Optional[Dict] = None, timeout: int = 30) -> requests.Response:
        """Make an authenticated API request with timeout protection."""
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        headers = self.get_headers()

        try:
            if method.upper() == 'POST':
                response = requests.post(
                    url, headers=headers, json=data or {}, timeout=timeout)
            elif method.upper() == 'GET':
                response = requests.get(
                    url, headers=headers, params=data or {}, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            return response
        except requests.exceptions.Timeout:
            raise Exception(
                f"API request to {endpoint} timed out after {timeout} seconds")
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request to {endpoint} failed: {e}")

    def assert_success_response(self, response: requests.Response, expected_status: int = 200):
        """Assert that response is successful."""
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"

        try:
            response_data = response.json()
        except:
            response_data = response.text

        return response_data

    def get_test_timestamp(self) -> str:
        """Get a timestamp for test data uniqueness."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def generate_test_name(self, prefix: str = "TEST") -> str:
        """Generate a unique test name."""
        return f"{prefix}_{self.get_test_timestamp()}"

    def generate_test_create_name(self, base_name: str) -> str:
        """Generate a name for test objects that will be created (for cleanup)."""
        return f"TESTNEW{self.get_test_timestamp()}_{base_name}"

    def generate_test_modify_prefix(self) -> str:
        """Generate a prefix for test modifications (for cleanup)."""
        return f"TESTMOD{self.get_test_timestamp()}_"

    def is_test_object(self, name: str) -> bool:
        """Check if a name represents a test object."""
        return name.startswith("TESTNEW") or "TESTMOD" in name

    def track_modification(self, resource_type: str, resource_id: Any, field: str, original_value: Any, test_value: Any):
        """Track a modification made for testing purposes."""
        self.test_modifications.append({
            'resource_type': resource_type,
            'resource_id': resource_id,
            'field': field,
            'original_value': original_value,
            'test_value': test_value
        })

    def modify_for_test(self, resource_type: str, resource_id: Any, field: str, original_value: Any, new_base_value: str) -> str:
        """Modify a field with test prefix and track for cleanup."""
        test_prefix = self.generate_test_modify_prefix()
        test_value = f"{test_prefix}{new_base_value}"
        self.track_modification(
            resource_type, resource_id, field, original_value, test_value)
        return test_value

    def get_test_user_id(self) -> int:
        """Get the database user_id for the test user with timeout protection."""
        print("🔍 Looking up test user ID...")
        try:
            # Look up the test user by their email (since we know that)
            response = self.api_request('get_users', data={
                'email': self.test_username
            }, timeout=15)  # Shorter timeout for user lookup
            result = self.assert_success_response(response)

            if isinstance(result, list) and len(result) > 0:
                user_id = result[0]['user_id']
                print(f"   ✅ Found test user ID: {user_id}")
                return user_id
            else:
                print("   ⚠️  Test user not found, using default ID: 8")
                # If user doesn't exist, return a default test ID from the env
                # This matches the user ID from the comprehensive API test that worked
                return 8
        except Exception as e:
            print(f"   ❌ Failed to get test user ID: {e}")
            print("   ⚠️  Using fallback default ID: 8")
            return 8

    # Client Group Methods
    def create_client_group(self, base_name: str) -> Dict[str, Any]:
        """Create a client group and track for cleanup."""
        test_name = self.generate_test_create_name(base_name)
        response = self.api_request('update_client_group', data={
            'name': test_name,
            'user_id': self.test_user_id
        })
        result = self.assert_success_response(response)

        if 'id' in result:
            self.created_client_groups.append(result['id'])
            result['test_name'] = test_name  # Store for reference
        return result

    def get_client_groups(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get client groups with optional filters."""
        response = self.api_request('get_client_groups', data=filters or {})
        result = self.assert_success_response(response)
        return result if isinstance(result, list) else []

    def update_client_group(self, client_group_id: int, name: str) -> Dict[str, Any]:
        """Update a client group."""
        response = self.api_request('update_client_group', data={
            'client_group_id': client_group_id,
            'name': name
        })
        return self.assert_success_response(response)

    # User Methods (Read-only - users are only created by Cognito)
    def get_users(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get users with optional filters."""
        data = filters or {}
        if 'requesting_user_id' not in data:
            data['requesting_user_id'] = self.test_user_id
        response = self.api_request('get_users', data=data)
        result = self.assert_success_response(response)
        return result if isinstance(result, list) else []

    # Entity Type Methods
    def create_entity_type(self, name: str, attributes_schema: Dict) -> Dict[str, Any]:
        """Create an entity type and track for cleanup."""
        response = self.api_request('update_entity_type', data={
            'name': name,
            'attributes_schema': attributes_schema
        })
        result = self.assert_success_response(response)

        if 'entity_type_id' in result:
            self.created_entity_types.append(result['entity_type_id'])
        return result

    def get_entity_types(self) -> List[Dict]:
        """Get all entity types."""
        response = self.api_request('get_entity_types')
        result = self.assert_success_response(response)
        return result if isinstance(result, list) else []

    def parse_entity_type(self, entity_type_data) -> Dict[str, Any]:
        """Parse entity type data from array or object format to consistent object format."""
        if isinstance(entity_type_data, list):
            # Array format: [entity_type_id, name, attributes_schema, short_label, label_color]
            return {
                'entity_type_id': entity_type_data[0],
                'name': entity_type_data[1],
                'attributes_schema': entity_type_data[2],
                'short_label': entity_type_data[3] if len(entity_type_data) > 3 else None,
                'label_color': entity_type_data[4] if len(entity_type_data) > 4 else None,
            }
        else:
            # Already object format
            return entity_type_data

    def find_entity_type_by_id(self, entity_types: List, entity_type_id: int) -> Dict[str, Any]:
        """Find entity type by ID, handling both array and object formats."""
        for et in entity_types:
            parsed = self.parse_entity_type(et)
            if parsed['entity_type_id'] == entity_type_id:
                return parsed
        return None

    def update_entity_type(self, entity_type_id: int, name: str = None, attributes_schema: Dict = None, short_label: str = None, label_color: str = None) -> Dict[str, Any]:
        """Update an entity type."""
        # Get current entity type to provide required fields
        current_types = self.get_entity_types()
        current_type = self.find_entity_type_by_id(
            current_types, entity_type_id)

        if not current_type:
            raise ValueError(f"Entity type {entity_type_id} not found")

        data = {
            'entity_type_id': entity_type_id,
            'name': name or current_type.get('name'),
            'attributes_schema': attributes_schema or current_type.get('attributes_schema', {})
        }

        if short_label is not None:
            data['short_label'] = short_label
        if label_color is not None:
            data['label_color'] = label_color

        response = self.api_request('update_entity_type', data=data)
        return self.assert_success_response(response)

    # Entity Methods
    def create_entity(self, base_name: str, entity_type_id: int, parent_entity_id: Optional[int] = None, attributes: Optional[Dict] = None, client_group_id: Optional[int] = None) -> Dict[str, Any]:
        """Create an entity and track for cleanup."""
        test_name = self.generate_test_create_name(base_name)
        data = {
            'name': test_name,
            'entity_type_id': entity_type_id,
            'user_id': self.test_user_id
        }

        # Add client_group_id if provided, otherwise get first available group
        if client_group_id:
            data['client_group_id'] = client_group_id
        else:
            # Get user's first client group as default
            groups = self.get_client_groups({'user_id': self.test_user_id})
            if groups and len(groups) > 0:
                data['client_group_id'] = groups[0]['client_group_id']

        if parent_entity_id:
            data['parent_entity_id'] = parent_entity_id
        if attributes:
            data['attributes'] = attributes

        response = self.api_request('update_entity', data=data)
        result = self.assert_success_response(response)

        if 'entity_id' in result:
            self.created_entities.append(result['entity_id'])
            result['test_name'] = test_name
        return result

    def get_entities(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get entities with optional filters."""
        data = filters or {}
        if 'user_id' not in data:
            data['user_id'] = self.test_user_id
        response = self.api_request('get_entities', data=data)
        result = self.assert_success_response(response)
        return result if isinstance(result, list) else []

    def update_entity(self, entity_id: int, **kwargs) -> Dict[str, Any]:
        """Update an entity."""
        data = {'entity_id': entity_id}
        data.update(kwargs)

        response = self.api_request('update_entity', data=data)
        return self.assert_success_response(response)

    # Deletion Methods
    def delete_record(self, record_id: int, record_type: str) -> Dict[str, Any]:
        """Delete a record using the delete API."""
        response = self.api_request('delete_record', data={
            'record_id': record_id,
            'record_type': record_type
        })
        return self.assert_success_response(response)

    # Client Group Membership Methods
    def modify_client_group_membership(self, client_group_id: int, user_id: str, action: str) -> Dict[str, Any]:
        """Modify client group membership (add/remove)."""
        response = self.api_request('modify_client_group_membership', data={
            'client_group_id': client_group_id,
            'user_id': user_id,
            'add_or_remove': action
        })
        return self.assert_success_response(response)

    def get_valid_entities(self, client_group_id: Optional[int] = None, user_id: Optional[str] = None) -> List[Dict]:
        """Get valid entities for a client group or user."""
        data = {}
        if client_group_id:
            data['client_group_id'] = client_group_id
        if user_id:
            data['user_id'] = user_id

        response = self.api_request('get_valid_entities', data=data)
        result = self.assert_success_response(response)
        return result if isinstance(result, list) else []

    # Cleanup Methods
    def cleanup_created_resources(self):
        """Clean up all resources created during testing."""
        # Cleanup is now handled by cleanup_test_objects.py script
        # This ensures proper foreign key constraint handling
        print("⚠️  Cleanup is now handled by cleanup_test_objects.py script")
        print("   Run: ./cleanup_test_objects.py")

    def revert_test_modifications(self):
        """Revert all tracked test modifications."""
        # TESTMOD modifications are now handled by cleanup_test_objects.py script
        # This ensures proper handling of foreign key constraints
        print("⚠️  TESTMOD modifications are now handled by cleanup_test_objects.py script")
        print("   Run: ./cleanup_test_objects.py")

    def store_original_value(self, key: str, value: Any):
        """Store an original value for later restoration."""
        self.original_values[key] = value

    def get_original_value(self, key: str) -> Any:
        """Get a stored original value."""
        return self.original_values.get(key)
