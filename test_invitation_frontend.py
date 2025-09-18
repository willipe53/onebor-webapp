#!/usr/bin/env python3
"""
Test the invitation functionality via API Gateway
"""
import requests
import json
from datetime import datetime, timedelta


def test_invitation_api():
    """Test the invitation API via API Gateway"""
    api_base_url = 'https://api.onebor.com/panda'

    # Test data
    test_email = 'test-invite@example.com'
    test_name = 'Test Invite User'
    expires_at = (datetime.now() + timedelta(days=7)).isoformat()
    primary_client_group_id = 11

    print(f"🧪 Testing invitation API via API Gateway")
    print(f"📧 Email: {test_email}")
    print(f"👤 Name: {test_name}")
    print(f"⏰ Expires: {expires_at}")
    print(f"🏢 Client Group ID: {primary_client_group_id}")

    # Test create invitation
    create_payload = {
        'action': 'create',
        'email': test_email,
        'name': test_name,
        'expires_at': expires_at,
        'primary_client_group_id': primary_client_group_id
    }

    print(f"\n📤 Creating invitation...")
    try:
        response = requests.post(
            f"{api_base_url}/manage_invitation",
            json=create_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        print(f"📊 Status Code: {response.status_code}")
        print(f"📝 Response: {response.text}")

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, dict) and 'code' in result:
                invitation_code = result['code']
                print(f"✅ Invitation created successfully!")
                print(f"🎫 Invitation Code: {invitation_code}")

                # Test get invitation
                print(f"\n🔍 Testing get invitation...")
                get_payload = {
                    'action': 'get',
                    'email': test_email
                }

                get_response = requests.post(
                    f"{api_base_url}/manage_invitation",
                    json=get_payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )

                print(f"📊 Get Status Code: {get_response.status_code}")
                print(f"📝 Get Response: {get_response.text}")

                if get_response.status_code == 200:
                    print("✅ Get invitation successful!")
                else:
                    print("❌ Get invitation failed!")
            else:
                print("❌ Invalid response format!")
        else:
            print("❌ Create invitation failed!")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_invitation_api()
