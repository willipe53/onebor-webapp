#!/usr/bin/env python3
import argparse
import boto3
import json
import requests
import sys

# ---- CONFIG ----
REGION = "us-east-2"
USER_POOL_ID = "us-east-2_IJ1C0mWXW"
CLIENT_ID = "1lntksiqrqhmjea6obrrrrnmh1"
API_BASE_URL = "https://api.onebor.com/panda"
# ----------------


def get_token(username, password):
    client = boto3.client("cognito-idp", region_name=REGION)
    resp = client.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password
        },
        ClientId=CLIENT_ID
    )
    return resp["AuthenticationResult"]["IdToken"]


def invoke_api(token, function, payload):
    url = f"{API_BASE_URL}/{function}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    return resp.status_code, resp.text


def main():
    parser = argparse.ArgumentParser(
        description="Test Panda API Gateway functions")
    parser.add_argument("-u", "--user", required=True, help="Cognito username")
    parser.add_argument("-p", "--password", required=True,
                        help="Cognito password")
    parser.add_argument("-f", "--function", required=True,
                        help="Function path (e.g. update_entity)")
    parser.add_argument("-j", "--json", required=True,
                        help="JSON payload string")
    args = parser.parse_args()

    try:
        token = get_token(args.user, args.password)
    except Exception as e:
        print("Error authenticating:", e, file=sys.stderr)
        sys.exit(1)

    try:
        payload = json.loads(args.json)
    except Exception as e:
        print("Invalid JSON payload:", e, file=sys.stderr)
        sys.exit(1)

    code, body = invoke_api(token, args.function, payload)
    print("Status:", code)
    print("Response:", body)


if __name__ == "__main__":
    main()
