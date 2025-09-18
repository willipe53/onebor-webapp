#!/usr/bin/env python3
"""
Test runner script for the API testing framework.
Provides convenient test execution with different options.
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Run API tests with various options")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--client-groups", action="store_true",
                        help="Run client group tests")
    parser.add_argument("--users", action="store_true", help="Run user tests")
    parser.add_argument("--entity-types", action="store_true",
                        help="Run entity type tests")
    parser.add_argument("--entities", action="store_true",
                        help="Run entity tests")
    parser.add_argument("--membership", action="store_true",
                        help="Run membership tests")
    parser.add_argument("--valid-entities", action="store_true",
                        help="Run valid entities tests")
    parser.add_argument("--verbose", "-v",
                        action="store_true", help="Verbose output")
    parser.add_argument("--slow", action="store_true",
                        help="Include slow tests")
    parser.add_argument("--specific", type=str,
                        help="Run specific test method (e.g., 'test_client_groups.py::TestClientGroups::test_client_group_update_and_revert')")
    parser.add_argument("--install-deps", action="store_true",
                        help="Install dependencies first")

    args = parser.parse_args()

    # Change to tests directory
    tests_dir = Path(__file__).parent
    print(f"📁 Working directory: {tests_dir}")

    # Install dependencies if requested
    if args.install_deps:
        if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                           "Installing dependencies"):
            print("❌ Failed to install dependencies")
            return 1

    # Build pytest command
    pytest_cmd = [sys.executable, "-m", "pytest"]

    if args.verbose:
        pytest_cmd.append("-v")

    # Add specific test selection
    if args.specific:
        pytest_cmd.append(args.specific)
    elif args.client_groups:
        pytest_cmd.append("test_client_groups.py")
    elif args.users:
        pytest_cmd.append("test_users.py")
    elif args.entity_types:
        pytest_cmd.append("test_entity_types.py")
    elif args.entities:
        pytest_cmd.append("test_entities.py")
    elif args.membership:
        pytest_cmd.append("test_client_group_membership.py")
    elif args.valid_entities:
        pytest_cmd.append("test_valid_entities.py")
    elif args.all or not any([args.client_groups, args.users, args.entity_types,
                             args.entities, args.membership, args.valid_entities, args.specific]):
        # Run all tests by default
        pytest_cmd.extend([
            "test_client_groups.py",
            "test_users.py",
            "test_entity_types.py",
            "test_entities.py",
            "test_client_group_membership.py",
            "test_valid_entities.py"
        ])

    # Add markers
    if not args.slow:
        pytest_cmd.extend(["-m", "not slow"])

    # Run tests
    success = run_command(pytest_cmd, "Running API tests")

    if success:
        print("\n✅ All tests completed successfully!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

