#!/usr/bin/env python3
"""
Test CORS configuration for API endpoints
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables from scripts/.env
load_dotenv()

# Test endpoint
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.onebor.com/panda")
TEST_ENDPOINT = f"{API_BASE_URL}/get_entity_types"


def test_options_request():
    """Test OPTIONS preflight request"""
    print("🔍 Testing OPTIONS preflight request...")

    headers = {
        "Origin": "https://app.onebor.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,Authorization"
    }

    try:
        response = requests.options(TEST_ENDPOINT, headers=headers)
        print(f"📊 OPTIONS Response Status: {response.status_code}")
        print(f"📋 Response Headers:")

        cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers",
            "Access-Control-Allow-Credentials"
        ]

        for header in cors_headers:
            value = response.headers.get(header, "Not Present")
            print(f"  {header}: {value}")

        if response.status_code == 200:
            print("✅ OPTIONS request successful")
            return True
        else:
            print("❌ OPTIONS request failed")
            return False

    except Exception as e:
        print(f"❌ Error testing OPTIONS: {e}")
        return False


def test_post_request():
    """Test actual POST request"""
    print("\n🔍 Testing POST request...")

    headers = {
        "Origin": "https://app.onebor.com",
        "Content-Type": "application/json"
    }

    payload = {"count_only": True}

    try:
        response = requests.post(TEST_ENDPOINT, headers=headers, json=payload)
        print(f"📊 POST Response Status: {response.status_code}")

        cors_header = response.headers.get(
            "Access-Control-Allow-Origin", "Not Present")
        print(f"📋 Access-Control-Allow-Origin: {cors_header}")

        if response.status_code == 200:
            print("✅ POST request successful")
            try:
                data = response.json()
                print(f"📄 Response: {data}")
            except:
                print("📄 Response (text):", response.text[:100])
            return True
        else:
            print("❌ POST request failed")
            print(f"📄 Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error testing POST: {e}")
        return False


def main():
    """Main test function"""
    print("🚀 Testing CORS configuration for onebor API")
    print(f"🎯 Test endpoint: {TEST_ENDPOINT}")
    print(f"🌐 Origin: https://app.onebor.com")
    print("=" * 50)

    options_success = test_options_request()
    post_success = test_post_request()

    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"✅ OPTIONS test: {'PASS' if options_success else 'FAIL'}")
    print(f"✅ POST test: {'PASS' if post_success else 'FAIL'}")

    if options_success and post_success:
        print("\n🎉 All CORS tests passed! Your API should work from https://app.onebor.com")
    else:
        print("\n⚠️  Some tests failed. CORS may not be properly configured.")


if __name__ == "__main__":
    main()
