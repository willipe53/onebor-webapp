#!/usr/bin/env python3
"""
Test the getPandaUsers Lambda directly
"""
import json
import boto3


def test_lambda():
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-east-2')

    # Test payload with both parameters
    test_payload = {
        "requesting_user_id": 8,
        "client_group_id": 19
    }

    print(f"Testing getPandaUsers Lambda with payload: {test_payload}")

    try:
        # Invoke the Lambda
        response = lambda_client.invoke(
            FunctionName='getPandaUsers',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )

        # Parse the response
        response_payload = response['Payload'].read()
        result = json.loads(response_payload)

        print(f"Lambda response status code: {response.get('StatusCode')}")
        print(f"Lambda response: {json.dumps(result, indent=2)}")

        # Parse the body if it's a string
        if 'body' in result:
            try:
                body_data = json.loads(result['body'])
                print(f"Response body data: {json.dumps(body_data, indent=2)}")
                if isinstance(body_data, list):
                    print(f"Number of users returned: {len(body_data)}")
                    for i, user in enumerate(body_data):
                        print(
                            f"  User {i+1}: ID={user.get('user_id')}, Email={user.get('email')}")
            except json.JSONDecodeError:
                print(f"Body is not JSON: {result['body']}")

    except Exception as e:
        print(f"Error invoking Lambda: {e}")


if __name__ == "__main__":
    test_lambda()






