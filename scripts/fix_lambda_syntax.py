#!/usr/bin/env python3
"""
Comprehensive fix for Lambda function syntax issues.
"""

import os
import re


def fix_lambda_file(file_path):
    """Fix syntax issues in a Lambda function file."""
    print(f"Fixing {file_path}...")

    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    # Fix 1: Ensure log_request_response function is properly indented
    pattern1 = r'(def lambda_handler\(event, context\):\n)def log_request_response\(event, response_body, lambda_name\):'
    if re.search(pattern1, content):
        content = re.sub(
            pattern1,
            r'\1    def log_request_response(event, response_body, lambda_name):',
            content
        )

    # Fix 2: Fix the docstring and function body indentation
    logging_pattern = r'(    def log_request_response\(event, response_body, lambda_name\):\n)(    """Log request and response data in a format that can be parsed for OpenAPI generation\.\."""\n)(    try:\n)(        # Log request data\n)(        if \'body\' in event:\n)(            request_body = json\.loads\(event\[\'body\'\]\) if isinstance\(event\[\'body\'\], str\) else event\[\'body\'\]\n)(            print\(f"REQUEST_BODY: \{json\.dumps\(request_body\)\}"\)\n)(        \n)(        # Log response data\n)(        if response_body:\n)(            print\(f"RESPONSE_BODY: \{json\.dumps\(response_body\)\}"\)\n)(            \n)(    except Exception as e:\n)(        print\(f"ERROR logging request/response: \{str\(e\)\}"\)\n)'

    replacement = r'\1        """Log request and response data in a format that can be parsed for OpenAPI generation."""\n        try:\n            # Log request data\n            if \'body\' in event:\n                request_body = json.loads(event[\'body\']) if isinstance(event[\'body\'], str) else event[\'body\']\n                print(f"REQUEST_BODY: {json.dumps(request_body)}")\n            \n            # Log response data\n            if response_body:\n                print(f"RESPONSE_BODY: {json.dumps(response_body)}")\n                \n        except Exception as e:\n            print(f"ERROR logging request/response: {str(e)}")\n'

    content = re.sub(logging_pattern, replacement, content)

    # Fix 3: Fix missing indentation in if statements that return early
    # Pattern for: if not user_id:\n            response_body = ...\n        log_request_response(...)\n        return {...}
    early_return_pattern = r'(\s+if not [^:]+:\s*\n)(\s+response_body = [^\n]+\n)(\s+log_request_response\([^\n]+\n)(\s+return \{[^\n]+\n)(\s+\}\n)'

    def fix_early_return(match):
        indent = match.group(1).rstrip()
        return f"{match.group(1)}{match.group(2)}{indent}{match.group(3)}{indent}{match.group(4)}{indent}{match.group(5)}"

    content = re.sub(early_return_pattern, fix_early_return,
                     content, flags=re.MULTILINE)

    # Write the fixed content back if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Fixed {file_path}")
        return True
    else:
        print(f"No issues found in {file_path}")
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

    print(f"\nFixed {fixed_count} files with syntax issues.")


if __name__ == "__main__":
    main()
