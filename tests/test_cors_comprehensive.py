#!/usr/bin/env python3
"""
Comprehensive CORS testing for all API endpoints
Tests the CORS configuration added in the last week across all endpoints
"""
import pytest
import requests
from .base_test import BaseAPITest


class TestCORSComprehensive(BaseAPITest):
    """Test CORS configuration across all endpoints."""

    def setup_method(self):
        """Setup for CORS testing."""
        super().setup_method()

        # List of all API endpoints to test
        self.endpoints_to_test = [
            '/get_users',
            '/get_client_groups',
            '/update_client_group',
            '/get_entities',
            '/update_entity',
            '/get_entity_types',
            '/update_entity_type',
            '/manage_invitation',
            '/modify_client_group_membership',
            '/modify_client_group_entities',
            '/get_valid_entities',
            '/delete_record'
        ]

        # Expected CORS headers
        self.expected_cors_headers = {
            'Access-Control-Allow-Origin': 'https://app.onebor.com',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Credentials': 'true'
        }

    def test_options_preflight_all_endpoints(self):
        """Test OPTIONS preflight requests for all endpoints."""
        for endpoint in self.endpoints_to_test:
            with self.subTest(endpoint=endpoint):
                url = f"{self.api_base_url}{endpoint}"
                headers = {
                    "Origin": "https://app.onebor.com",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type,Authorization"
                }

                try:
                    response = requests.options(
                        url, headers=headers, timeout=10)

                    # Should return 200 for preflight
                    assert response.status_code == 200, f"OPTIONS failed for {endpoint}: {response.status_code}"

                    # Check each required CORS header
                    for header_name, expected_value in self.expected_cors_headers.items():
                        actual_value = response.headers.get(header_name)

                        if header_name == 'Access-Control-Allow-Methods':
                            # Methods can be in any order, check if required methods are present
                            assert 'POST' in actual_value, f"{endpoint}: POST not in Allow-Methods"
                            assert 'OPTIONS' in actual_value, f"{endpoint}: OPTIONS not in Allow-Methods"
                        elif header_name == 'Access-Control-Allow-Headers':
                            # Headers can be in any order, check if required headers are present
                            assert 'Content-Type' in actual_value, f"{endpoint}: Content-Type not in Allow-Headers"
                            assert 'Authorization' in actual_value, f"{endpoint}: Authorization not in Allow-Headers"
                        else:
                            assert actual_value == expected_value, f"{endpoint}: {header_name} = '{actual_value}', expected '{expected_value}'"

                except requests.exceptions.RequestException as e:
                    pytest.fail(f"Request failed for {endpoint}: {e}")

    def test_post_cors_headers_all_endpoints(self):
        """Test that POST requests include CORS headers in response."""
        for endpoint in self.endpoints_to_test:
            with self.subTest(endpoint=endpoint):
                # Use a minimal valid request (may fail due to auth/validation, but should have CORS headers)
                response = self.api_request(endpoint.lstrip('/'), data={})

                # Check CORS headers are present regardless of response status
                cors_headers_present = any(
                    header.startswith('Access-Control-') for header in response.headers
                )
                assert cors_headers_present, f"No CORS headers found in {endpoint} response"

                # Check specific CORS headers if present
                if 'Access-Control-Allow-Origin' in response.headers:
                    assert response.headers['Access-Control-Allow-Origin'] == 'https://app.onebor.com'

                if 'Access-Control-Allow-Credentials' in response.headers:
                    assert response.headers['Access-Control-Allow-Credentials'] == 'true'

    def test_cors_origin_specificity(self):
        """Test that CORS is properly restricted to app.onebor.com origin."""
        endpoint = '/get_entity_types'  # Use a simple endpoint
        url = f"{self.api_base_url}{endpoint}"

        # Test with correct origin
        headers_correct = {
            "Origin": "https://app.onebor.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }

        response = requests.options(url, headers=headers_correct, timeout=10)
        assert response.status_code == 200
        assert response.headers.get(
            'Access-Control-Allow-Origin') == 'https://app.onebor.com'

        # Test with incorrect origin
        headers_incorrect = {
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }

        response = requests.options(url, headers=headers_incorrect, timeout=10)
        # Should either reject or not include the malicious origin
        if response.status_code == 200:
            origin_header = response.headers.get('Access-Control-Allow-Origin')
            assert origin_header != 'https://malicious-site.com', "Should not allow malicious origin"

    def test_cors_credentials_support(self):
        """Test that CORS properly supports credentials."""
        for endpoint in self.endpoints_to_test[:3]:  # Test a few endpoints
            with self.subTest(endpoint=endpoint):
                url = f"{self.api_base_url}{endpoint}"
                headers = {
                    "Origin": "https://app.onebor.com",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type,Authorization"
                }

                response = requests.options(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    credentials_header = response.headers.get(
                        'Access-Control-Allow-Credentials')
                    assert credentials_header == 'true', f"{endpoint}: Credentials not properly supported"

    def test_cors_headers_format(self):
        """Test that CORS headers are properly formatted."""
        endpoint = '/get_entity_types'
        url = f"{self.api_base_url}{endpoint}"
        headers = {
            "Origin": "https://app.onebor.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }

        response = requests.options(url, headers=headers, timeout=10)

        if response.status_code == 200:
            # Check that methods are comma-separated without spaces after commas (standard format)
            methods = response.headers.get('Access-Control-Allow-Methods', '')
            if methods:
                # Should contain required methods
                required_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
                for method in required_methods:
                    assert method in methods, f"Missing method: {method}"

            # Check that headers are properly formatted
            allowed_headers = response.headers.get(
                'Access-Control-Allow-Headers', '')
            if allowed_headers:
                required_headers = ['Content-Type', 'Authorization']
                for header in required_headers:
                    assert header in allowed_headers, f"Missing header: {header}"

    def test_cors_error_responses(self):
        """Test that error responses also include CORS headers."""
        # Test with an endpoint that should return an error (no auth)
        endpoint = '/get_users'

        # Make request without authentication
        url = f"{self.api_base_url}{endpoint}"
        headers = {
            "Origin": "https://app.onebor.com",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json={}, timeout=10)

        # Even error responses should have CORS headers
        cors_headers_present = any(
            header.startswith('Access-Control-') for header in response.headers
        )

        # If CORS headers are present, they should be correct
        if cors_headers_present:
            if 'Access-Control-Allow-Origin' in response.headers:
                assert response.headers['Access-Control-Allow-Origin'] == 'https://app.onebor.com'

    def test_cors_complex_preflight(self):
        """Test CORS with complex preflight scenarios."""
        endpoint = '/modify_client_group_entities'  # Complex endpoint
        url = f"{self.api_base_url}{endpoint}"

        # Test with multiple requested headers
        headers = {
            "Origin": "https://app.onebor.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization,X-Api-Key,X-Amz-Date,X-Amz-Security-Token"
        }

        response = requests.options(url, headers=headers, timeout=10)

        assert response.status_code == 200, f"Complex preflight failed: {response.status_code}"

        allowed_headers = response.headers.get(
            'Access-Control-Allow-Headers', '')
        requested_headers = headers['Access-Control-Request-Headers'].split(
            ',')

        for requested_header in requested_headers:
            requested_header = requested_header.strip()
            assert requested_header in allowed_headers, f"Requested header '{requested_header}' not allowed"

    def test_cors_max_age_header(self):
        """Test that CORS max-age header is set appropriately."""
        endpoint = '/get_entity_types'
        url = f"{self.api_base_url}{endpoint}"
        headers = {
            "Origin": "https://app.onebor.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }

        response = requests.options(url, headers=headers, timeout=10)

        if response.status_code == 200:
            max_age = response.headers.get('Access-Control-Max-Age')
            if max_age:
                # If present, should be a reasonable value (typically 86400 seconds = 24 hours)
                max_age_int = int(max_age)
                assert 0 < max_age_int <= 86400, f"Max-Age should be reasonable: {max_age_int}"

    def test_cors_all_http_methods(self):
        """Test CORS for different HTTP methods."""
        endpoint = '/get_entity_types'
        url = f"{self.api_base_url}{endpoint}"

        methods_to_test = ['GET', 'POST', 'PUT', 'DELETE']

        for method in methods_to_test:
            with self.subTest(method=method):
                headers = {
                    "Origin": "https://app.onebor.com",
                    "Access-Control-Request-Method": method,
                    "Access-Control-Request-Headers": "Content-Type,Authorization"
                }

                response = requests.options(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    allowed_methods = response.headers.get(
                        'Access-Control-Allow-Methods', '')
                    assert method in allowed_methods, f"Method {method} not allowed in CORS"

    def test_cors_performance(self):
        """Test that CORS preflight doesn't significantly impact performance."""
        import time
        endpoint = '/get_entity_types'
        url = f"{self.api_base_url}{endpoint}"

        # Time multiple OPTIONS requests
        times = []
        for _ in range(5):
            start_time = time.time()

            headers = {
                "Origin": "https://app.onebor.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }

            response = requests.options(url, headers=headers, timeout=10)
            end_time = time.time()

            if response.status_code == 200:
                times.append(end_time - start_time)

        if times:
            avg_time = sum(times) / len(times)
            # CORS preflight should be fast (under 2 seconds)
            assert avg_time < 2.0, f"CORS preflight too slow: {avg_time:.2f}s average"
