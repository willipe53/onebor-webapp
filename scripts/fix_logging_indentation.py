#!/usr/bin/env python3
"""
Fix indentation issues in Lambda functions caused by the add_logging_to_lambdas.py script.
"""

import os
import re


def fix_lambda_file(file_path):
    """Fix indentation issues in a Lambda function file."""
    print(f"Fixing {file_path}...")

    with open(file_path, 'r') as f:
        content = f.read()

    # Pattern to find the problematic insertion
    pattern = r'(def lambda_handler\(event, context\):\n)def log_request_response\(event, response_body, lambda_name\):'

    if re.search(pattern, content):
        # Fix the indentation
        content = re.sub(
            pattern,
            r'\1    def log_request_response(event, response_body, lambda_name):',
            content
        )

        # Fix the docstring and function body indentation
        # Pattern for the entire logging function that needs indentation fix
        logging_pattern = r'(    def log_request_response\(event, response_body, lambda_name\):\n)(    """Log request and response data in a format that can be parsed for OpenAPI generation\.\."""\n)(    try:\n)(        # Log request data\n)(        if \'body\' in event:\n)(            request_body = json\.loads\(event\[\'body\'\]\) if isinstance\(event\[\'body\'\], str\) else event\[\'body\'\]\n)(            print\(f"REQUEST_BODY: \{json\.dumps\(request_body\)\}"\)\n)(        \n)(        # Log response data\n)(        if response_body:\n)(            print\(f"RESPONSE_BODY: \{json\.dumps\(response_body\)\}"\)\n)(            \n)(    except Exception as e:\n)(        print\(f"ERROR logging request/response: \{str\(e\)\}"\)\n)'

        replacement = r'\1        """Log request and response data in a format that can be parsed for OpenAPI generation."""\n        try:\n            # Log request data\n            if \'body\' in event:\n                request_body = json.loads(event[\'body\']) if isinstance(event[\'body\'], str) else event[\'body\']\n                print(f"REQUEST_BODY: {json.dumps(request_body)}")\n            \n            # Log response data\n            if response_body:\n                print(f"RESPONSE_BODY: {json.dumps(response_body)}")\n                \n        except Exception as e:\n            print(f"ERROR logging request/response: {str(e)}")\n'

        content = re.sub(logging_pattern, replacement, content)

        # Write the fixed content back
        with open(file_path, 'w') as f:
            f.write(content)

        print(f"Fixed {file_path}")
        return True
    else:
        print(f"No indentation issues found in {file_path}")
        return False


def main():
    """Fix all Lambda function files."""
    database_dir = "database"
    fixed_count = 0

    for filename in os.listdir(database_dir):
        if filename.endswith('.py'):
            file_path = os.path.join(database_dir, filename)
            if fix_lambda_file(file_path):
                fixed_count += 1

    print(f"\nFixed {fixed_count} files with indentation issues.")


if __name__ == "__main__":
    main()
