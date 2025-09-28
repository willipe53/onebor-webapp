#!/usr/bin/env python3
import boto3
import json
import time
import sys
from genson import SchemaBuilder
from collections import defaultdict
from botocore.exceptions import ClientError, NoCredentialsError

# ---------- CONFIG ----------
LOG_GROUPS = [
    "/aws/lambda/deletePandaRecord",
    "/aws/lambda/getPandaClientGroups",
    "/aws/lambda/getPandaEntities",
    "/aws/lambda/getPandaEntityTypes",
    "/aws/lambda/getPandaTransactions",
    "/aws/lambda/getPandaTransactionStatuses",
    "/aws/lambda/getPandaTransactionTypes",
    "/aws/lambda/getPandaUsers",
    "/aws/lambda/managePandaInvitation",
    "/aws/lambda/modifyPandaClientGroupEntities",
    "/aws/lambda/modifyPandaClientGroupMembership",
    "/aws/lambda/updatePandaClientGroup",
    "/aws/lambda/updatePandaEntity",
    "/aws/lambda/updatePandaEntityType",
    "/aws/lambda/updatePandaPositions",
    "/aws/lambda/updatePandaTransaction",
    "/aws/lambda/updatePandaTransactionStatuses",
    "/aws/lambda/updatePandaTransactionType",
    "/aws/lambda/updatePandaUser"
]

# Map Lambda function names to actual API endpoints
LAMBDA_TO_API_PATH = {
    "deletePandaRecord": "/delete_record",
    "getPandaClientGroups": "/get_client_groups",
    "getPandaEntities": "/get_entities",
    "getPandaEntityTypes": "/get_entity_types",
    "getPandaTransactions": "/get_transactions",
    "getPandaTransactionStatuses": "/get_transaction_statuses",
    "getPandaTransactionTypes": "/get_transaction_types",
    "getPandaUsers": "/get_users",
    "managePandaInvitation": "/manage_invitation",
    "modifyPandaClientGroupEntities": "/modify_client_group_entities",
    "modifyPandaClientGroupMembership": "/modify_client_group_membership",
    "updatePandaClientGroup": "/update_client_group",
    "updatePandaEntity": "/update_entity",
    "updatePandaEntityType": "/update_entity_type",
    "updatePandaPositions": "/update_positions",
    "updatePandaTransaction": "/update_transaction",
    "updatePandaTransactionStatuses": "/update_transaction_statuses",
    "updatePandaTransactionType": "/update_transaction_type",
    "updatePandaUser": "/update_user"
}

# Map Lambda function names to HTTP methods (most are POST, but some might be GET)
LAMBDA_TO_HTTP_METHOD = {
    "getPandaClientGroups": "GET",
    "getPandaEntities": "GET",
    "getPandaEntityTypes": "GET",
    "getPandaTransactions": "GET",
    "getPandaTransactionStatuses": "GET",
    "getPandaTransactionTypes": "GET",
    "getPandaUsers": "GET",
    # All others default to POST
}

DAYS_BACK = 7   # Reduced from 21 for better performance
MAX_STREAMS_PER_LOG_GROUP = 10  # Limit streams to avoid API limits
MAX_EVENTS_PER_STREAM = 100     # Limit events per stream
DEBUG_MODE = False  # Set to True to see what logs are being processed
# ----------------------------

# Initialize AWS clients with error handling
try:
    logs = boto3.client("logs")
    # Test credentials
    logs.describe_log_groups(limit=1)
    print("✅ AWS credentials validated")
except NoCredentialsError:
    print("❌ AWS credentials not found. Please configure your credentials.")
    sys.exit(1)
except ClientError as e:
    print(f"❌ AWS error: {e}")
    sys.exit(1)

start_time = int((time.time() - DAYS_BACK*24*3600) * 1000)

# store schemas per API with deduplication
schemas = defaultdict(lambda: SchemaBuilder())
seen_requests = set()  # Track unique requests to avoid duplicates


def collect_events(log_group):
    """Collect events from a CloudWatch log group with improved error handling."""
    try:
        # Check if log group exists
        logs.describe_log_groups(logGroupNamePrefix=log_group)

        # Get log streams with pagination and limits
        streams = logs.describe_log_streams(
            logGroupName=log_group,
            orderBy="LastEventTime",
            descending=True,
            limit=MAX_STREAMS_PER_LOG_GROUP
        )["logStreams"]

        if not streams:
            print(f"⚠️  No log streams found for {log_group}")
            return

        print(f"📊 Processing {len(streams)} streams for {log_group}")

        for s in streams[:MAX_STREAMS_PER_LOG_GROUP]:
            try:
                # Use filter pattern to only get relevant logs
                filter_pattern = '{ $.message = "*Request body*" || $.message = "*Response body*" }'

                resp = logs.filter_log_events(
                    logGroupName=log_group,
                    logStreamNames=[s["logStreamName"]],
                    startTime=start_time,
                    filterPattern=filter_pattern,
                    limit=MAX_EVENTS_PER_STREAM
                )

                for e in resp["events"]:
                    msg = e["message"]

                    # Debug mode: show what logs we're finding
                    if DEBUG_MODE and ("body" in msg.lower() or "event" in msg.lower() or "request" in msg.lower() or "response" in msg.lower()):
                        print(f"  🔍 Found log: {msg[:100]}...")

                    # Look for the new standardized logging format
                    if "REQUEST_BODY:" in msg:
                        try:
                            json_part = msg.split("REQUEST_BODY:", 1)[
                                1].strip()
                            body = json.loads(json_part)
                            request_key = f"{log_group}_request_{hash(json_part)}"
                            if request_key not in seen_requests:
                                schemas[log_group+"_request"].add_object(body)
                                seen_requests.add(request_key)
                                print(
                                    f"  ✅ Collected request schema from REQUEST_BODY")
                        except (json.JSONDecodeError, IndexError) as e:
                            if DEBUG_MODE:
                                print(f"⚠️  Failed to parse REQUEST_BODY: {e}")
                            continue

                    elif "RESPONSE_BODY:" in msg:
                        try:
                            json_part = msg.split("RESPONSE_BODY:", 1)[
                                1].strip()
                            body = json.loads(json_part)
                            response_key = f"{log_group}_response_{hash(json_part)}"
                            if response_key not in seen_requests:
                                schemas[log_group+"_response"].add_object(body)
                                seen_requests.add(response_key)
                                print(
                                    f"  ✅ Collected response schema from RESPONSE_BODY")
                        except (json.JSONDecodeError, IndexError) as e:
                            if DEBUG_MODE:
                                print(
                                    f"⚠️  Failed to parse RESPONSE_BODY: {e}")
                            continue

                    # Legacy patterns for backward compatibility
                    elif "Request body:" in msg:
                        try:
                            # Extract JSON after "Request body:"
                            json_part = msg.split("Request body:", 1)[
                                1].strip()
                            body = json.loads(json_part)

                            # Create unique key for deduplication
                            request_key = f"{log_group}_request_{hash(json_part)}"
                            if request_key not in seen_requests:
                                schemas[log_group+"_request"].add_object(body)
                                seen_requests.add(request_key)

                        except (json.JSONDecodeError, IndexError) as e:
                            print(
                                f"⚠️  Failed to parse request body in {log_group}: {e}")
                            continue

                    elif "Response body:" in msg:
                        try:
                            # Extract JSON after "Response body:"
                            json_part = msg.split("Response body:", 1)[
                                1].strip()
                            body = json.loads(json_part)

                            # Create unique key for deduplication
                            response_key = f"{log_group}_response_{hash(json_part)}"
                            if response_key not in seen_requests:
                                schemas[log_group+"_response"].add_object(body)
                                seen_requests.add(response_key)

                        except (json.JSONDecodeError, IndexError) as e:
                            print(
                                f"⚠️  Failed to parse response body in {log_group}: {e}")
                            continue

                    # Fallback: Look for actual debug patterns from your Lambda functions
                    elif "DEBUG: Parsed body:" in msg:
                        try:
                            json_part = msg.split("DEBUG: Parsed body:", 1)[
                                1].strip()
                            body = json.loads(json_part)
                            request_key = f"{log_group}_request_{hash(json_part)}"
                            if request_key not in seen_requests:
                                schemas[log_group+"_request"].add_object(body)
                                seen_requests.add(request_key)
                                print(
                                    f"  ✅ Collected request schema from DEBUG log")
                        except (json.JSONDecodeError, IndexError) as e:
                            if DEBUG_MODE:
                                print(f"⚠️  Failed to parse DEBUG body: {e}")
                            continue

                    elif "DEBUG: Event:" in msg:
                        try:
                            json_part = msg.split("DEBUG: Event:", 1)[
                                1].strip()
                            event_data = json.loads(json_part)
                            if 'body' in event_data:
                                body = json.loads(event_data['body']) if isinstance(
                                    event_data['body'], str) else event_data['body']
                                request_key = f"{log_group}_request_{hash(str(body))}"
                                if request_key not in seen_requests:
                                    schemas[log_group +
                                            "_request"].add_object(body)
                                    seen_requests.add(request_key)
                                    print(
                                        f"  ✅ Collected request schema from DEBUG Event")
                        except (json.JSONDecodeError, IndexError, KeyError) as e:
                            if DEBUG_MODE:
                                print(f"⚠️  Failed to parse DEBUG Event: {e}")
                            continue

            except ClientError as e:
                print(f"⚠️  Error processing stream {s['logStreamName']}: {e}")
                continue

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"⚠️  Log group {log_group} not found")
        else:
            print(f"❌ Error accessing {log_group}: {e}")
        return


def get_lambda_name_from_log_group(log_group):
    """Extract Lambda function name from log group path."""
    return log_group.split("/")[-1]


def main():
    """Main function to collect logs and generate OpenAPI spec."""
    print(
        f"🚀 Starting log collection for {len(LOG_GROUPS)} Lambda functions...")
    print(f"📅 Looking back {DAYS_BACK} days")
    print(
        f"⚡ Processing max {MAX_STREAMS_PER_LOG_GROUP} streams per log group")
    print()

    successful_collections = 0
    failed_collections = 0

    for g in LOG_GROUPS:
        print(f"📋 Collecting from {g}...")
        try:
            collect_events(g)
            successful_collections += 1
        except Exception as e:
            print(f"❌ Failed to collect from {g}: {e}")
            failed_collections += 1
        print()

    print(f"✅ Successfully processed: {successful_collections}")
    print(f"❌ Failed: {failed_collections}")
    print()

    if not schemas:
        print("⚠️  No schemas collected. Check your log groups and time range.")
        return

    # Generate comprehensive OpenAPI spec
    print("📝 Generating OpenAPI specification...")

    openapi = {
        "openapi": "3.0.1",
        "info": {
            "title": "OneBor Financial API",
            "description": "Auto-generated API specification from Lambda logs",
            "version": "1.0.0",
            "contact": {
                "name": "OneBor API Support",
                "email": "support@onebor.com"
            }
        },
        "servers": [
            {
                "url": "https://api.onebor.com/panda",
                "description": "Production server"
            },
            {
                "url": "https://zwkvk3lyl3.execute-api.us-east-2.amazonaws.com/dev",
                "description": "Development server"
            }
        ],
        "paths": {},
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    }

    # Process collected schemas
    for key, builder in schemas.items():
        if not builder.to_schema().get("properties"):
            continue  # Skip empty schemas

        schema = builder.to_schema()
        lambda_name = key.replace("_request", "").replace("_response", "")
        lambda_function_name = get_lambda_name_from_log_group(lambda_name)

        # Get API path and HTTP method
        api_path = LAMBDA_TO_API_PATH.get(lambda_function_name)
        http_method = LAMBDA_TO_HTTP_METHOD.get(lambda_function_name, "POST")

        if not api_path:
            print(f"⚠️  No API path mapping for {lambda_function_name}")
            continue

        # Initialize path if not exists
        if api_path not in openapi["paths"]:
            openapi["paths"][api_path] = {}

        if key.endswith("_request"):
            # Add request schema
            if http_method == "GET":
                # For GET requests, add query parameters
                openapi["paths"][api_path][http_method.lower()] = {
                    "summary": f"{api_path} endpoint",
                    "description": f"Auto-generated from {lambda_function_name} logs",
                    "parameters": [
                        {
                            "name": "body",
                            "in": "query",
                            "description": "Query parameters",
                            "schema": schema
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        },
                        "400": {
                            "description": "Bad Request",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        },
                        "500": {
                            "description": "Internal Server Error",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    },
                    "security": [{"bearerAuth": []}]
                }
            else:
                # For POST/PUT requests, add request body
                openapi["paths"][api_path][http_method.lower()] = {
                    "summary": f"{api_path} endpoint",
                    "description": f"Auto-generated from {lambda_function_name} logs",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": schema
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        },
                        "400": {
                            "description": "Bad Request",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        },
                        "500": {
                            "description": "Internal Server Error",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    },
                    "security": [{"bearerAuth": []}]
                }

        elif key.endswith("_response"):
            # Update response schema
            if api_path in openapi["paths"] and http_method.lower() in openapi["paths"][api_path]:
                openapi["paths"][api_path][http_method.lower(
                )]["responses"]["200"]["content"]["application/json"]["schema"] = schema

    # Add CORS options endpoints
    for path in openapi["paths"]:
        openapi["paths"][path]["options"] = {
            "summary": "CORS preflight",
            "description": "Handle CORS preflight requests",
            "responses": {
                "200": {
                    "description": "CORS preflight successful"
                }
            }
        }

    # Write the OpenAPI spec
    output_file = "openapi-from-logs.json"
    with open(output_file, "w") as f:
        json.dump(openapi, f, indent=2)

    print(f"✅ Generated OpenAPI spec with {len(openapi['paths'])} endpoints")
    print(f"📄 Saved to: {output_file}")

    # Print summary
    print("\n📊 Summary:")
    for path, methods in openapi["paths"].items():
        method_list = list(methods.keys())
        print(f"  {path}: {', '.join(method_list).upper()}")


if __name__ == "__main__":
    main()
