#!/usr/bin/env python3
"""
Test the deployed frontend to ensure it's working correctly
"""

import requests
import time
import sys
import os
from dotenv import load_dotenv

# Load environment variables from scripts/.env
load_dotenv()


def test_deployment():
    """Test the deployed frontend"""
    url = "https://app.onebor.com"

    print(f"🧪 Testing deployment at {url}...")

    try:
        # Test the main page
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            print("✅ Main page loads successfully")

            # Check if it's the React app (look for typical React app content)
            content = response.text.lower()
            if "onebor" in content or "react" in content or "vite" in content:
                print("✅ App appears to be the onebor React application")
            else:
                print("⚠️  App loaded but may not be the correct onebor application")

        else:
            print(f"❌ Main page returned status code: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to {url}: {e}")
        return False

    # Test API connectivity (this will fail without auth, but we can check if the endpoint exists)
    api_url = "https://api.onebor.com/panda"
    try:
        # This should return 401 Unauthorized, which means the API is reachable
        api_response = requests.post(api_url, json={}, timeout=10)
        if api_response.status_code == 401:
            print("✅ API endpoint is reachable (401 Unauthorized is expected)")
        else:
            print(
                f"⚠️  API returned unexpected status: {api_response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Could not test API connectivity: {e}")

    return True


def main():
    """Main test function"""
    print("🧪 Testing onebor frontend deployment...")
    print("⏳ Waiting 10 seconds for CloudFront to propagate...")
    time.sleep(10)

    if test_deployment():
        print("\n🎉 Deployment test completed successfully!")
        print("🌐 Your app is live at: https://app.onebor.com")
    else:
        print("\n❌ Deployment test failed!")
        print("Please check the deployment and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
