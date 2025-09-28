#!/usr/bin/env python3
"""
Generate OpenAPI specifications for all onebor API endpoints.

This script analyzes the codebase to extract API endpoint information
and generates OpenAPI 3.0 specifications for each Lambda function.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class APIEndpoint:
    """Represents an API endpoint with its request/response structure."""
    name: str
    path: str
    method: str
    description: str
    request_schema: Dict[str, Any]
    response_schema: Dict[str, Any]
    lambda_function: str


class OpenAPIGenerator:
    """Generates OpenAPI specifications for onebor APIs."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.database_dir = project_root / "database"
        self.src_dir = project_root / "src"
        self.endpoints: List[APIEndpoint] = []

    def analyze_frontend_api_calls(self) -> List[APIEndpoint]:
        """Analyze frontend API service to extract endpoint information."""
        api_file = self.src_dir / "services" / "api.ts"
        if not api_file.exists():
            return []

        with open(api_file, 'r') as f:
            content = f.read()

        endpoints = []

        # Extract API calls from the frontend
        api_call_pattern = r'apiCall<[^>]+>\("([^"]+)",\s*data\)'
        matches = re.findall(api_call_pattern, content)

        for match in matches:
            endpoint_path = match
            endpoint_name = endpoint_path.replace(
                '/', '').replace('_', ' ').title()

            # Try to extract request/response types from TypeScript interfaces
            request_type = self._extract_request_type(content, endpoint_path)
            response_type = self._extract_response_type(content, endpoint_path)

            endpoints.append(APIEndpoint(
                name=endpoint_name,
                path=endpoint_path,
                method="POST",
                description=f"API endpoint for {endpoint_name}",
                request_schema=request_type,
                response_schema=response_type,
                lambda_function=self._get_lambda_function_name(endpoint_path)
            ))

        return endpoints

    def _extract_request_type(self, content: str, endpoint_path: str) -> Dict[str, Any]:
        """Extract request schema from TypeScript interfaces."""
        # Look for function definitions that use this endpoint
        pattern = rf'export const \w+ = async \(\s*data: (\w+)\s*\)'
        matches = re.findall(pattern, content)

        if matches:
            interface_name = matches[0]
            return self._extract_interface_schema(content, interface_name)

        return {"type": "object", "properties": {}}

    def _extract_response_type(self, content: str, endpoint_path: str) -> Dict[str, Any]:
        """Extract response schema from TypeScript interfaces."""
        # Look for Promise return types
        pattern = rf'Promise<(\w+)>'
        matches = re.findall(pattern, content)

        if matches:
            interface_name = matches[0]
            return self._extract_interface_schema(content, interface_name)

        return {"type": "object", "properties": {}}

    def _extract_interface_schema(self, content: str, interface_name: str) -> Dict[str, Any]:
        """Extract schema from TypeScript interface."""
        pattern = rf'export interface {interface_name} \{{(.*?)\}}'
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            return {"type": "object", "properties": {}}

        interface_body = match.group(1)
        properties = {}
        required = []

        # Parse interface properties
        lines = interface_body.split('\n')
        for line in lines:
            line = line.strip()
            if ':' in line and not line.startswith('//'):
                # Extract property name and type
                prop_match = re.match(r'(\w+)(\?)?:\s*([^;]+)', line)
                if prop_match:
                    prop_name, optional, prop_type = prop_match.groups()
                    properties[prop_name] = self._convert_typescript_type(
                        prop_type.strip())
                    if not optional:
                        required.append(prop_name)

        schema = {
            "type": "object",
            "properties": properties
        }

        if required:
            schema["required"] = required

        return schema

    def _convert_typescript_type(self, ts_type: str) -> Dict[str, Any]:
        """Convert TypeScript type to JSON Schema type."""
        ts_type = ts_type.strip()

        # Handle union types
        if '|' in ts_type:
            return {"type": "string", "enum": [t.strip().strip("'\"") for t in ts_type.split('|')]}

        # Handle array types
        if ts_type.startswith('Array<') or ts_type.endswith('[]'):
            item_type = ts_type.replace('Array<', '').replace(
                '>', '').replace('[]', '')
            return {
                "type": "array",
                "items": self._convert_typescript_type(item_type)
            }

        # Handle basic types
        type_mapping = {
            'string': {"type": "string"},
            'number': {"type": "number"},
            'boolean': {"type": "boolean"},
            'any': {"type": "object"},
            'object': {"type": "object"},
            'void': {"type": "null"}
        }

        return type_mapping.get(ts_type, {"type": "string"})

    def _get_lambda_function_name(self, endpoint_path: str) -> str:
        """Map endpoint path to Lambda function name."""
        path_to_lambda = {
            '/get_users': 'getPandaUsers',
            '/update_user': 'updatePandaUser',
            '/get_client_groups': 'getPandaClientGroups',
            '/update_client_group': 'updatePandaClientGroup',
            '/get_entity_types': 'getPandaEntityTypes',
            '/update_entity_type': 'updatePandaEntityType',
            '/get_entities': 'getPandaEntities',
            '/update_entity': 'updatePandaEntity',
            '/get_transaction_types': 'getPandaTransactionTypes',
            '/update_transaction_type': 'updatePandaTransactionType',
            '/get_transaction_statuses': 'getPandaTransactionStatuses',
            '/update_transaction_status': 'updatePandaTransactionStatus',
            '/get_transactions': 'getPandaTransactions',
            '/update_transaction': 'updatePandaTransaction',
            '/update_positions': 'updatePandaPositions',
            '/manage_invitation': 'managePandaInvitation',
            '/modify_client_group_membership': 'modifyPandaClientGroupMembership',
            '/modify_client_group_entities': 'modifyPandaClientGroupEntities',
            '/get_valid_entities': 'getPandaValidEntities',
            '/delete_record': 'deletePandaRecord'
        }

        return path_to_lambda.get(endpoint_path, 'unknown')

    def analyze_lambda_functions(self) -> List[APIEndpoint]:
        """Analyze Lambda functions to extract detailed endpoint information."""
        endpoints = []

        lambda_files = list(self.database_dir.glob("*.py"))

        for lambda_file in lambda_files:
            if lambda_file.name.startswith('__'):
                continue

            endpoint = self._analyze_lambda_file(lambda_file)
            if endpoint:
                endpoints.append(endpoint)

        return endpoints

    def _analyze_lambda_file(self, lambda_file: Path) -> Optional[APIEndpoint]:
        """Analyze a single Lambda function file."""
        with open(lambda_file, 'r') as f:
            content = f.read()

        # Extract function name
        function_name = lambda_file.stem

        # Extract docstring for description
        docstring_match = re.search(
            r'def lambda_handler\(event, context\):\s*"""([^"]*)"""', content, re.DOTALL)
        description = docstring_match.group(1).strip(
        ) if docstring_match else f"Lambda function {function_name}"

        # Extract request parameters from body parsing
        request_schema = self._extract_lambda_request_schema(content)

        # Extract response structure
        response_schema = self._extract_lambda_response_schema(content)

        # Map function name to endpoint path
        endpoint_path = self._get_endpoint_path(function_name)

        return APIEndpoint(
            name=function_name.replace('Panda', '').replace('_', ' ').title(),
            path=endpoint_path,
            method="POST",
            description=description,
            request_schema=request_schema,
            response_schema=response_schema,
            lambda_function=function_name
        )

    def _extract_lambda_request_schema(self, content: str) -> Dict[str, Any]:
        """Extract request schema from Lambda function."""
        properties = {}
        required = []

        # First, try to extract from docstring
        docstring_schema = self._extract_docstring_schema(content)
        if docstring_schema:
            return docstring_schema

        # Look for body.get() calls
        get_pattern = r'body\.get\("([^"]+)"\)'
        matches = re.findall(get_pattern, content)

        for param in matches:
            # Determine parameter type based on usage
            param_type = self._determine_parameter_type(content, param)
            properties[param] = param_type

            # Check if it's required (not using .get() with default)
            if f'body.get("{param}")' in content and f'body.get("{param}",' not in content:
                required.append(param)

        # If we found parameters, return them
        if properties:
            return {
                "type": "object",
                "properties": properties,
                "required": required
            }

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def _extract_docstring_schema(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract request schema from Lambda function docstring."""
        # Look for docstring with expected event structure
        docstring_pattern = r'def lambda_handler\(event, context\):.*?"""(.*?)"""'
        match = re.search(docstring_pattern, content, re.DOTALL)

        if not match:
            return None

        docstring = match.group(1)

        # Look for JSON structure in docstring
        json_pattern = r'\{\s*"([^"]+)":\s*([^,}]+),?\s*"([^"]+)":\s*([^,}]+)'
        json_match = re.search(json_pattern, docstring)

        if json_match:
            param1, type1, param2, type2 = json_match.groups()
            properties = {}
            required = []

            # Parse first parameter
            properties[param1] = self._parse_docstring_type(type1.strip())
            required.append(param1)

            # Parse second parameter
            properties[param2] = self._parse_docstring_type(type2.strip())
            required.append(param2)

            return {
                "type": "object",
                "properties": properties,
                "required": required
            }

        return None

    def _parse_docstring_type(self, type_str: str) -> Dict[str, Any]:
        """Parse type from docstring."""
        type_str = type_str.strip()

        # Handle union types like "Client Group" | "Entity" | "Entity Type" | "User"
        if '|' in type_str:
            enum_values = [t.strip().strip('"\'') for t in type_str.split('|')]
            return {
                "type": "string",
                "enum": enum_values
            }

        # Handle basic types
        if type_str == '<id>':
            return {"type": "integer"}
        elif type_str.startswith('"') and type_str.endswith('"'):
            return {"type": "string"}
        else:
            return {"type": "string"}

    def _determine_parameter_type(self, content: str, param: str) -> Dict[str, Any]:
        """Determine parameter type based on usage in the code."""
        # Look for type hints or usage patterns
        if 'int(' in content and param in content:
            return {"type": "integer"}
        elif param in ['count_only']:
            return {"type": "boolean"}
        elif param in ['limit', 'offset']:
            return {"type": "integer"}
        else:
            return {"type": "string"}

    def _extract_lambda_response_schema(self, content: str) -> Dict[str, Any]:
        """Extract response schema from Lambda function."""
        # Look for return statements with JSON structure
        return_pattern = r'return \{\s*"statusCode":\s*(\d+),.*?"body":\s*json\.dumps\(([^)]+)\)'
        match = re.search(return_pattern, content, re.DOTALL)

        if match:
            status_code = int(match.group(1))
            response_body = match.group(2)

            # Try to determine response structure
            if 'success' in response_body:
                return {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "message": {"type": "string"}
                    }
                }
            elif 'error' in response_body:
                return {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"}
                    }
                }

        # Look for specific response patterns in the code
        if 'success' in content and 'False' in content:
            return {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "error": {"type": "string"}
                }
            }

        return {"type": "object", "properties": {}}

    def _get_endpoint_path(self, function_name: str) -> str:
        """Map Lambda function name to endpoint path."""
        function_to_path = {
            'getPandaUsers': '/get_users',
            'updatePandaUser': '/update_user',
            'getPandaClientGroups': '/get_client_groups',
            'updatePandaClientGroup': '/update_client_group',
            'getPandaEntityTypes': '/get_entity_types',
            'updatePandaEntityType': '/update_entity_type',
            'getPandaEntities': '/get_entities',
            'updatePandaEntity': '/update_entity',
            'getPandaTransactionTypes': '/get_transaction_types',
            'updatePandaTransactionType': '/update_transaction_type',
            'getPandaTransactionStatuses': '/get_transaction_statuses',
            'updatePandaTransactionStatus': '/update_transaction_status',
            'getPandaTransactions': '/get_transactions',
            'updatePandaTransaction': '/update_transaction',
            'updatePandaPositions': '/update_positions',
            'managePandaInvitation': '/manage_invitation',
            'modifyPandaClientGroupMembership': '/modify_client_group_membership',
            'modifyPandaClientGroupEntities': '/modify_client_group_entities',
            'getPandaValidEntities': '/get_valid_entities',
            'deletePandaRecord': '/delete_record'
        }

        return function_to_path.get(function_name, f'/{function_name.lower()}')

    def generate_openapi_spec(self, endpoint: APIEndpoint) -> Dict[str, Any]:
        """Generate OpenAPI specification for a single endpoint."""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": f"onebor {endpoint.name} API",
                "description": endpoint.description,
                "version": "1.0.0",
                "contact": {
                    "name": "onebor API Support",
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
            "paths": {
                endpoint.path: {
                    endpoint.method.lower(): {
                        "summary": endpoint.name,
                        "description": endpoint.description,
                        "operationId": endpoint.lambda_function,
                        "tags": [endpoint.name],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": endpoint.request_schema
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": endpoint.response_schema
                                    }
                                }
                            },
                            "400": {
                                "description": "Bad request",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "error": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            },
                            "500": {
                                "description": "Internal server error",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "error": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "security": [
                            {
                                "bearerAuth": []
                            }
                        ]
                    },
                    "options": {
                        "summary": "CORS preflight",
                        "description": "Handle CORS preflight requests",
                        "responses": {
                            "200": {
                                "description": "CORS preflight successful"
                            }
                        }
                    }
                }
            },
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

    def generate_all_specs(self) -> Dict[str, Dict[str, Any]]:
        """Generate OpenAPI specifications for all endpoints."""
        # Analyze frontend API calls
        frontend_endpoints = self.analyze_frontend_api_calls()

        # Analyze Lambda functions
        lambda_endpoints = self.analyze_lambda_functions()

        # Combine and deduplicate, prioritizing Lambda analysis
        all_endpoints = lambda_endpoints + frontend_endpoints  # Lambda first
        unique_endpoints = {}

        for endpoint in all_endpoints:
            key = f"{endpoint.path}:{endpoint.method}"
            if key not in unique_endpoints:
                unique_endpoints[key] = endpoint

        # Generate specs
        specs = {}
        for endpoint in unique_endpoints.values():
            specs[endpoint.lambda_function] = self.generate_openapi_spec(
                endpoint)

        return specs

    def save_specs(self, specs: Dict[str, Dict[str, Any]], output_dir: Path):
        """Save OpenAPI specifications to files."""
        output_dir.mkdir(exist_ok=True)

        for function_name, spec in specs.items():
            output_file = output_dir / f"{function_name}.json"
            with open(output_file, 'w') as f:
                json.dump(spec, f, indent=2)
            print(
                f"✅ Generated OpenAPI spec for {function_name}: {output_file}")

        # Generate a combined spec
        combined_spec = self._generate_combined_spec(specs)
        combined_file = output_dir / "onebor-api-combined.json"
        with open(combined_file, 'w') as f:
            json.dump(combined_spec, f, indent=2)
        print(f"✅ Generated combined OpenAPI spec: {combined_file}")

    def _generate_combined_spec(self, specs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a combined OpenAPI specification."""
        combined = {
            "openapi": "3.0.0",
            "info": {
                "title": "onebor API",
                "description": "Complete API specification for onebor platform",
                "version": "1.0.0",
                "contact": {
                    "name": "onebor API Support",
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

        # Merge all paths
        for spec in specs.values():
            if "paths" in spec:
                combined["paths"].update(spec["paths"])

        return combined


def main():
    """Main function to generate OpenAPI specifications."""
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "openapi_specs"

    print("🚀 Generating OpenAPI specifications for onebor APIs...")
    print(f"📁 Project root: {project_root}")
    print(f"📁 Output directory: {output_dir}")

    generator = OpenAPIGenerator(project_root)
    specs = generator.generate_all_specs()

    print(f"\n📊 Found {len(specs)} API endpoints:")
    for function_name in specs.keys():
        print(f"  - {function_name}")

    generator.save_specs(specs, output_dir)

    print(f"\n✅ OpenAPI specifications generated successfully!")
    print(f"📁 All specs saved to: {output_dir}")
    print(f"\n📋 Next steps:")
    print(f"  1. Review generated specifications")
    print(f"  2. Attach specs to API Gateway resources")
    print(f"  3. Enable request/response validation")
    print(f"  4. Generate client SDKs from specs")


if __name__ == "__main__":
    main()
