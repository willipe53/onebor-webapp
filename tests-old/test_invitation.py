#!/usr/bin/env python3
"""
Test the managePandaInvitation Lambda function
"""
import boto3
import json
from datetime import datetime, timedelta


def test_invitation_lambda():
    """Test the invitation management Lambda function"""
    lambda_client = boto3.client('lambda', region_name='us-east-2')

    # Test payload for creating an invitation
    test_payload = {
        'action': 'create',
        'email': 'test@example.com',
        'name': 'Test User',
        'expires_at': (datetime.now() + timedelta(days=7)).isoformat(),
        'primary_client_group_id': 11
    }

    print(f"🧪 Testing create invitation with payload: {test_payload}")

    try:
        response = lambda_client.invoke(
            FunctionName='managePandaInvitation',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload).encode('utf-8')
        )

        status_code = response.get('StatusCode', 0)
        response_body = response['Payload'].read().decode('utf-8')

        print(f"📊 Lambda Status Code: {status_code}")
        print(f"📝 Lambda Response: {response_body}")

        if status_code == 200:
            result = json.loads(response_body)
            # The Lambda returns a nested structure, so we need to parse the body
            if isinstance(result, dict) and 'body' in result:
                body_result = json.loads(result['body'])
                if body_result.get('success'):
                    print("✅ Create invitation successful!")
                    invitation_code = body_result.get('code')

                # Test getting the invitation
                print(f"\n🔍 Testing get invitation by email...")
                get_payload = {
                    'action': 'get',
                    'email': 'test@example.com'
                }

                get_response = lambda_client.invoke(
                    FunctionName='managePandaInvitation',
                    InvocationType='RequestResponse',
                    Payload=json.dumps(get_payload).encode('utf-8')
                )

                get_body = get_response['Payload'].read().decode('utf-8')
                print(f"📝 Get Response: {get_body}")

                # Test redeeming the invitation
                if invitation_code:
                    print(
                        f"\n🎫 Testing redeem invitation with code: {invitation_code}")
                    redeem_payload = {
                        'action': 'redeem',
                        'code': invitation_code
                    }

                    redeem_response = lambda_client.invoke(
                        FunctionName='managePandaInvitation',
                        InvocationType='RequestResponse',
                        Payload=json.dumps(redeem_payload).encode('utf-8')
                    )

                    redeem_body = redeem_response['Payload'].read().decode(
                        'utf-8')
                    print(f"📝 Redeem Response: {redeem_body}")

                    redeem_result = json.loads(redeem_body)
                    if isinstance(redeem_result, dict) and 'body' in redeem_result:
                        redeem_body_result = json.loads(redeem_result['body'])
                        if redeem_body_result.get('success'):
                            print("✅ Redeem invitation successful!")
                        else:
                            print("❌ Redeem invitation failed!")
                    else:
                        print("❌ Redeem invitation failed!")
                else:
                    print("❌ No invitation code returned!")
            else:
                print("❌ Create invitation failed!")
        else:
            print("❌ Lambda function failed!")

    except Exception as e:
        print(f"❌ Error testing Lambda function: {e}")


if __name__ == "__main__":
    test_invitation_lambda()
