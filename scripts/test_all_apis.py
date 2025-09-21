#!/usr/bin/env python3
"""
Comprehensive API testing script for onebor APIs
Tests all endpoints with authentication and CORS verification
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

# Add tests directory to path to import base_test
sys.path.append('tests')


class APITester(BaseAPITest):
    """Extended API tester with CORS and comprehensive endpoint testing."""

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
    print("🚀 onebor API Comprehensive Testing")
    print("=" * 60)

    # Initialize tester
    tester = APITester()
    tester.setup_method()

    print(
        f"🔑 Authentication: {'✅ SUCCESS' if tester.access_token else '❌ FAILED'}")
    print(f"🌐 API Base URL: {tester.api_base_url}")
    print(f"👤 Test User: {tester.test_username}")
    print("=" * 60)

    if not tester.access_token:
        print("❌ Cannot proceed without authentication")
        return

    # Define all API endpoints to test
    api_endpoints = [
        # User Management
        {
            'name': 'Get Users',
            'endpoint': 'get_users',
            'data': {},
            'description': 'Retrieve all users'
        },
        {
            'name': 'Update User',
            'endpoint': 'update_user',
            'data': {
                'sub': 'test-sub-12345',
                'email': 'test@example.com'
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
            'name': 'Update Client Group',
            'endpoint': 'update_client_group',
            'data': {
                'name': f'Test Group {datetime.now().strftime("%Y%m%d_%H%M%S")}'
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

        # Entities
        {
            'name': 'Get Entities',
            'endpoint': 'get_entities',
            'data': {},
            'description': 'Retrieve all entities'
        },
        {
            'name': 'Get Entities Count',
            'endpoint': 'get_entities',
            'data': {'count_only': True},
            'description': 'Get count of entities'
        },

        # Invitations
        {
            'name': 'Get Invitations',
            'endpoint': 'manage_invitation',
            'data': {'action': 'get'},
            'description': 'Retrieve invitations'
        },

        # Client Group Membership
        {
            'name': 'Get Valid Entities',
            'endpoint': 'get_valid_entities',
            'data': {},
            'description': 'Get entities valid for user'
        }
    ]

    # Test results storage
    results = []

    print("\n🧪 Testing API Endpoints:")
    print("-" * 60)

    for i, api_test in enumerate(api_endpoints, 1):
        print(f"\n{i}. {api_test['name']}")
        print(f"   📝 {api_test['description']}")
        print(f"   🎯 Endpoint: {api_test['endpoint']}")

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
                        preview = f"Object with keys: {list(response_data.keys())[:3]}"
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
        time.sleep(0.5)  # Rate limiting

    # Summary Report
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY REPORT")
    print("=" * 60)

    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['overall_success'])
    failed_tests = total_tests - successful_tests

    print(f"🎯 Total Tests: {total_tests}")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📈 Success Rate: {(successful_tests/total_tests)*100:.1f}%")

    # Failed tests details
    if failed_tests > 0:
        print(f"\n❌ Failed Tests:")
        for result in results:
            if not result['overall_success']:
                print(f"   • {result['name']} ({result['endpoint']})")
                if 'error' in result['api_test']:
                    print(f"     Error: {result['api_test']['error']}")

    # CORS Summary
    print(f"\n🌐 CORS Configuration Status:")
    options_passing = sum(1 for r in results if r['options_test']['success'])
    cors_headers_passing = sum(1 for r in results if r.get('api_test', {}).get('cors_headers') and
                               all(h['status'] == 'PASS' for h in r['api_test']['cors_headers'].values()))

    print(f"   OPTIONS Preflight: {options_passing}/{total_tests} passing")
    print(f"   CORS Headers: {cors_headers_passing}/{total_tests} passing")

    if options_passing == total_tests and cors_headers_passing == total_tests:
        print(f"   🎉 CORS fully configured and working!")
    else:
        print(f"   ⚠️  CORS needs attention")

    # Cleanup
    print(f"\n🧹 Cleaning up test resources...")
    tester.teardown_method()
    print(f"✅ Cleanup completed")

    print(f"\n🎉 Testing completed!")
    return successful_tests == total_tests


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
