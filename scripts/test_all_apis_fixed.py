#!/usr/bin/env python3
"""
Enhanced API testing script with proper parameters for all endpoints
"""

from base_test import BaseAPITest
import os
import sys
import json
import boto3
import requests
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from scripts/.env
load_dotenv()

# Add tests directory to path to import base_test
sys.path.append('tests')


class EnhancedAPITester(BaseAPITest):
    """Enhanced API tester with proper parameter handling."""

    def __init__(self):
        super().__init__()
        self.current_user_id = None
        self.current_client_group_id = None

    def setup_method(self):
        """Setup and get current user info."""
        super().setup_method()

        # Get current user info for subsequent tests
        try:
            response = self.api_request('get_users', data={})
            if response.status_code == 200:
                users = response.json()
                if users and len(users) > 0:
                    self.current_user_id = users[0].get('user_id')
                    print(f"📝 Current User ID: {self.current_user_id}")
        except Exception as e:
            print(f"⚠️  Could not get current user: {e}")

        # Get current client groups
        try:
            response = self.api_request('get_client_groups', data={})
            if response.status_code == 200:
                groups = response.json()
                if groups and len(groups) > 0:
                    self.current_client_group_id = groups[0].get(
                        'client_group_id')
                    print(
                        f"📝 Current Client Group ID: {self.current_client_group_id}")
        except Exception as e:
            print(f"⚠️  Could not get client groups: {e}")

    def test_cors_headers(self, response: requests.Response, endpoint: str):
        """Test that CORS headers are present and correct."""
        cors_checks = {
            'Access-Control-Allow-Origin': 'https://app.onebor.com',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Credentials': 'true'
        }

        cors_results = {}
        for header, expected in cors_checks.items():
            actual = response.headers.get(header)
            cors_results[header] = {
                'expected': expected,
                'actual': actual,
                'status': 'PASS' if actual == expected else 'FAIL'
            }

        return cors_results

    def test_options_request(self, endpoint: str):
        """Test OPTIONS preflight request for CORS."""
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Origin": "https://app.onebor.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }

        try:
            response = requests.options(url, headers=headers)
            cors_results = self.test_cors_headers(response, endpoint)

            return {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'cors_headers': cors_results
            }
        except Exception as e:
            return {
                'status_code': None,
                'success': False,
                'error': str(e),
                'cors_headers': {}
            }


def main():
    """Main testing function."""
    print("🚀 onebor API Enhanced Testing (with proper parameters)")
    print("=" * 70)

    # Initialize tester
    tester = EnhancedAPITester()
    tester.setup_method()

    print(
        f"🔑 Authentication: {'✅ SUCCESS' if tester.access_token else '❌ FAILED'}")
    print(f"🌐 API Base URL: {tester.api_base_url}")
    print(f"👤 Test User: {tester.test_username}")
    print("=" * 70)

    if not tester.access_token:
        print("❌ Cannot proceed without authentication")
        return

    # Define all API endpoints to test with proper parameters
    api_endpoints = [
        # User Management
        {
            'name': 'Get Users',
            'endpoint': 'get_users',
            'data': {},
            'description': 'Retrieve all users'
        },
        {
            'name': 'Get Users Count',
            'endpoint': 'get_users',
            'data': {'count_only': True},
            'description': 'Get count of users'
        },
        {
            'name': 'Update User',
            'endpoint': 'update_user',
            'data': {
                'sub': f'test-sub-{int(time.time())}',
                'email': f'test-{int(time.time())}@example.com'
            },
            'description': 'Create/update a user'
        },

        # Client Groups
        {
            'name': 'Get Client Groups',
            'endpoint': 'get_client_groups',
            'data': {},
            'description': 'Retrieve all client groups'
        },
        {
            'name': 'Get Client Groups Count',
            'endpoint': 'get_client_groups',
            'data': {'count_only': True},
            'description': 'Get count of client groups'
        },
        {
            'name': 'Update Client Group',
            'endpoint': 'update_client_group',
            'data': {
                'name': f'Test Group {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'user_id': None  # Will be set dynamically
            },
            'description': 'Create/update a client group'
        },

        # Entity Types
        {
            'name': 'Get Entity Types',
            'endpoint': 'get_entity_types',
            'data': {},
            'description': 'Retrieve all entity types'
        },
        {
            'name': 'Get Entity Types Count',
            'endpoint': 'get_entity_types',
            'data': {'count_only': True},
            'description': 'Get count of entity types'
        },
        {
            'name': 'Update Entity Type',
            'endpoint': 'update_entity_type',
            'data': {
                'name': f'Test Entity Type {datetime.now().strftime("%H%M%S")}',
                'short_label': 'TEST',
                'label_color': '#4caf50',
                'attributes_schema': {
                    'type': 'object',
                    'properties': {
                        'test_field': {'type': 'string'}
                    }
                }
            },
            'description': 'Create/update an entity type'
        },

        # Entities (with proper user_id)
        {
            'name': 'Get Entities',
            'endpoint': 'get_entities',
            'data': {'user_id': None},  # Will be set dynamically
            'description': 'Retrieve all entities'
        },
        {
            'name': 'Get Entities Count',
            'endpoint': 'get_entities',
            # Will be set dynamically
            'data': {'count_only': True, 'user_id': None},
            'description': 'Get count of entities'
        },

        # Invitations (with proper client_group_id)
        {
            'name': 'Get Invitations',
            'endpoint': 'manage_invitation',
            # Will be set dynamically
            'data': {'action': 'get', 'client_group_id': None},
            'description': 'Retrieve invitations'
        },
        {
            'name': 'Get Invitations Count',
            'endpoint': 'manage_invitation',
            # Will be set dynamically
            'data': {'action': 'get', 'count_only': True, 'client_group_id': None},
            'description': 'Get count of invitations'
        },

        # Client Group Membership
        {
            'name': 'Get Valid Entities',
            'endpoint': 'get_valid_entities',
            'data': {'user_id': None},  # Will be set dynamically
            'description': 'Get entities valid for user'
        },

        # Additional endpoints
        {
            'name': 'Modify Client Group Membership',
            'endpoint': 'modify_client_group_membership',
            'data': {
                'client_group_id': None,  # Will be set dynamically
                'user_id': None,  # Will be set dynamically
                'add_or_remove': 'add'
            },
            'description': 'Test client group membership modification'
        }
    ]

    # Set dynamic parameters
    for endpoint in api_endpoints:
        if endpoint['data'].get('user_id') is None and 'user_id' in endpoint['data']:
            endpoint['data']['user_id'] = tester.current_user_id
        if endpoint['data'].get('client_group_id') is None and 'client_group_id' in endpoint['data']:
            endpoint['data']['client_group_id'] = tester.current_client_group_id

    # Test results storage
    results = []

    print("\n🧪 Testing API Endpoints:")
    print("-" * 70)

    for i, api_test in enumerate(api_endpoints, 1):
        print(f"\n{i}. {api_test['name']}")
        print(f"   📝 {api_test['description']}")
        print(f"   🎯 Endpoint: {api_test['endpoint']}")

        # Show parameters
        if api_test['data']:
            params_str = json.dumps(api_test['data'], indent=None)[:100]
            print(f"   📋 Parameters: {params_str}")

        # Test OPTIONS request first
        print("   🔍 Testing CORS (OPTIONS)...", end=" ")
        options_result = tester.test_options_request(api_test['endpoint'])
        options_status = "✅ PASS" if options_result['success'] else "❌ FAIL"
        print(options_status)

        # Test actual API request
        print("   🔍 Testing API call...", end=" ")
        try:
            response = tester.api_request(
                api_test['endpoint'], data=api_test['data'])
            api_success = response.status_code in [200, 201]
            api_status = "✅ PASS" if api_success else f"❌ FAIL ({response.status_code})"
            print(api_status)

            # Test CORS headers on actual response
            cors_results = tester.test_cors_headers(
                response, api_test['endpoint'])
            cors_pass = all(result['status'] ==
                            'PASS' for result in cors_results.values())
            cors_status = "✅ PASS" if cors_pass else "❌ FAIL"
            print(f"   🔍 CORS headers: {cors_status}")

            # Store results
            result = {
                'name': api_test['name'],
                'endpoint': api_test['endpoint'],
                'options_test': options_result,
                'api_test': {
                    'status_code': response.status_code,
                    'success': api_success,
                    'cors_headers': cors_results
                },
                'overall_success': options_result['success'] and api_success and cors_pass
            }

            # Show response preview for successful requests
            if api_success:
                try:
                    response_data = response.json()
                    if isinstance(response_data, list):
                        preview = f"Array with {len(response_data)} items"
                    elif isinstance(response_data, dict):
                        keys = list(response_data.keys())[:3]
                        preview = f"Object with keys: {keys}"
                        # Show some key values for interesting responses
                        if 'user_id' in response_data:
                            preview += f" (user_id: {response_data['user_id']})"
                        elif 'success' in response_data:
                            preview += f" (success: {response_data['success']})"
                    else:
                        preview = str(response_data)[:50]
                    print(f"   📄 Response: {preview}")
                except:
                    print(f"   📄 Response: {response.text[:50]}")
            else:
                print(f"   ❌ Error: {response.text[:100]}")

        except Exception as e:
            print(f"❌ EXCEPTION")
            print(f"   ❌ Error: {str(e)}")
            result = {
                'name': api_test['name'],
                'endpoint': api_test['endpoint'],
                'options_test': options_result,
                'api_test': {
                    'status_code': None,
                    'success': False,
                    'error': str(e)
                },
                'overall_success': False
            }

        results.append(result)
        time.sleep(0.2)  # Rate limiting

    # Summary Report
    print("\n" + "=" * 70)
    print("📊 ENHANCED TEST SUMMARY REPORT")
    print("=" * 70)

    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['overall_success'])
    failed_tests = total_tests - successful_tests

    print(f"🎯 Total Tests: {total_tests}")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📈 Success Rate: {(successful_tests/total_tests)*100:.1f}%")

    # API Categories breakdown
    categories = {
        'User Management': ['Get Users', 'Get Users Count', 'Update User'],
        'Client Groups': ['Get Client Groups', 'Get Client Groups Count', 'Update Client Group'],
        'Entity Types': ['Get Entity Types', 'Get Entity Types Count', 'Update Entity Type'],
        'Entities': ['Get Entities', 'Get Entities Count'],
        'Invitations': ['Get Invitations', 'Get Invitations Count'],
        'Other': ['Get Valid Entities', 'Modify Client Group Membership']
    }

    print(f"\n📋 Results by Category:")
    for category, test_names in categories.items():
        category_results = [r for r in results if r['name'] in test_names]
        category_success = sum(
            1 for r in category_results if r['overall_success'])
        category_total = len(category_results)
        if category_total > 0:
            print(f"   {category}: {category_success}/{category_total} passing")

    # Failed tests details
    if failed_tests > 0:
        print(f"\n❌ Failed Tests Details:")
        for result in results:
            if not result['overall_success']:
                print(f"   • {result['name']} ({result['endpoint']})")
                if 'error' in result['api_test']:
                    print(f"     Error: {result['api_test']['error']}")
                elif result['api_test'].get('status_code'):
                    print(f"     Status: {result['api_test']['status_code']}")

    # CORS Summary
    print(f"\n🌐 CORS Configuration Status:")
    options_passing = sum(1 for r in results if r['options_test']['success'])
    cors_headers_passing = sum(1 for r in results if r.get('api_test', {}).get('cors_headers') and
                               all(h['status'] == 'PASS' for h in r['api_test']['cors_headers'].values()))

    print(f"   OPTIONS Preflight: {options_passing}/{total_tests} passing")
    print(f"   CORS Headers: {cors_headers_passing}/{total_tests} passing")

    if options_passing == total_tests and cors_headers_passing >= successful_tests:
        print(f"   🎉 CORS fully configured and working!")
        print(f"   ✅ https://app.onebor.com should work without CORS errors!")
    else:
        print(f"   ⚠️  CORS needs attention")

    # Cleanup
    print(f"\n🧹 Cleaning up test resources...")
    tester.teardown_method()
    print(f"✅ Cleanup completed")

    print(f"\n🎉 Enhanced testing completed!")
    return successful_tests >= total_tests * 0.8  # 80% success rate threshold


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
