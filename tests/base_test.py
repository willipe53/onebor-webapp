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
load_dotenv()


class BaseAPITest:
    """Base class for API testing with authentication and utilities."""

    def setup_method(self):
        """Setup before each test method."""
        self.api_base_url = os.getenv(
            'API_BASE_URL', 'https://zwkvk3lyl3.execute-api.us-east-2.amazonaws.com/dev')
        self.cognito_user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
        self.cognito_client_id = os.getenv('COGNITO_CLIENT_ID')
        self.test_username = os.getenv('TEST_USERNAME')
        self.test_password = os.getenv('TEST_PASSWORD')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-2')

        self.access_token = None
        self.cognito_client = boto3.client(
            'cognito-idp', region_name=self.aws_region)

        # Track created resources for cleanup
        self.created_client_groups: List[int] = []
        self.created_users: List[str] = []
        self.created_entities: List[int] = []
        self.created_entity_types: List[int] = []
        self.original_values: Dict[str, Any] = {}

        self.authenticate()

    def teardown_method(self):
        """Cleanup after each test method."""
        self.cleanup_created_resources()

    def authenticate(self) -> str:
        """Authenticate with Cognito and get access token."""
        try:
            # Try ADMIN_NO_SRP_AUTH first (requires ALLOW_ADMIN_USER_PASSWORD_AUTH)
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
            return self.access_token
        except Exception as admin_auth_error:
            # If ADMIN_NO_SRP_AUTH fails, try USER_PASSWORD_AUTH
            try:
                response = self.cognito_client.initiate_auth(
                    ClientId=self.cognito_client_id,
                    AuthFlow='USER_PASSWORD_AUTH',
                    AuthParameters={
                        'USERNAME': self.test_username,
                        'PASSWORD': self.test_password
                    }
                )
                self.access_token = response['AuthenticationResult']['IdToken']
                return self.access_token
            except Exception as user_auth_error:
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

    def api_request(self, endpoint: str, method: str = 'POST', data: Optional[Dict] = None) -> requests.Response:
        """Make an authenticated API request."""
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        headers = self.get_headers()

        if method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data or {})
        elif method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=data or {})
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        return response

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

    # Client Group Methods
    def create_client_group(self, name: str) -> Dict[str, Any]:
        """Create a client group and track for cleanup."""
        response = self.api_request('update_client_group', data={'name': name})
        result = self.assert_success_response(response)

        if 'id' in result:
            self.created_client_groups.append(result['id'])
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

    # User Methods
    def create_user(self, user_id: str, email: str, name: str) -> Dict[str, Any]:
        """Create a user and track for cleanup."""
        response = self.api_request('update_user', data={
            'user_id': user_id,
            'email': email,
            'name': name
        })
        result = self.assert_success_response(response)
        self.created_users.append(user_id)
        return result

    def get_users(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get users with optional filters."""
        response = self.api_request('get_users', data=filters or {})
        result = self.assert_success_response(response)
        return result if isinstance(result, list) else []

    def update_user(self, user_id: str, email: str = None, name: str = None) -> Dict[str, Any]:
        """Update a user."""
        data = {'user_id': user_id}
        if email:
            data['email'] = email
        if name:
            data['name'] = name

        response = self.api_request('update_user', data=data)
        return self.assert_success_response(response)

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
        data = {'entity_type_id': entity_type_id}
        if name:
            data['name'] = name
        if attributes_schema:
            data['attributes_schema'] = attributes_schema
        if short_label is not None:
            data['short_label'] = short_label
        if label_color is not None:
            data['label_color'] = label_color

        response = self.api_request('update_entity_type', data=data)
        return self.assert_success_response(response)

    # Entity Methods
    def create_entity(self, name: str, entity_type_id: int, parent_entity_id: Optional[int] = None, attributes: Optional[Dict] = None) -> Dict[str, Any]:
        """Create an entity and track for cleanup."""
        data = {
            'name': name,
            'entity_type_id': entity_type_id
        }
        if parent_entity_id:
            data['parent_entity_id'] = parent_entity_id
        if attributes:
            data['attributes'] = attributes

        response = self.api_request('update_entity', data=data)
        result = self.assert_success_response(response)

        if 'entity_id' in result:
            self.created_entities.append(result['entity_id'])
        return result

    def get_entities(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get entities with optional filters."""
        response = self.api_request('get_entities', data=filters or {})
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
        # Delete entities first (due to foreign key constraints)
        for entity_id in self.created_entities[:]:
            try:
                self.delete_record(entity_id, "Entity")
                self.created_entities.remove(entity_id)
            except Exception as e:
                print(f"Warning: Failed to cleanup entity {entity_id}: {e}")

        # Delete entity types
        for entity_type_id in self.created_entity_types[:]:
            try:
                self.delete_record(entity_type_id, "Entity Type")
                self.created_entity_types.remove(entity_type_id)
            except Exception as e:
                print(
                    f"Warning: Failed to cleanup entity type {entity_type_id}: {e}")

        # Delete users
        for user_id in self.created_users[:]:
            try:
                self.delete_record(user_id, "User")
                self.created_users.remove(user_id)
            except Exception as e:
                print(f"Warning: Failed to cleanup user {user_id}: {e}")

        # Delete client groups
        for client_group_id in self.created_client_groups[:]:
            try:
                self.delete_record(client_group_id, "Client Group")
                self.created_client_groups.remove(client_group_id)
            except Exception as e:
                print(
                    f"Warning: Failed to cleanup client group {client_group_id}: {e}")

        # Clear original values
        self.original_values.clear()

    def store_original_value(self, key: str, value: Any):
        """Store an original value for later restoration."""
        self.original_values[key] = value

    def get_original_value(self, key: str) -> Any:
        """Get a stored original value."""
        return self.original_values.get(key)
