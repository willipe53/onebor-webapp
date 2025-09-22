#!/usr/bin/env python3
"""
Simple test runner with validation checks and output logging
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


class TeeLogger:
    """Logger that outputs to both console and file simultaneously."""

    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename, 'w', encoding='utf-8')
        self.original_stdout = sys.stdout

    def print(self, *args, **kwargs):
        """Print to both console and file."""
        # Print to console
        print(*args, **kwargs)
        # Print to file (temporarily redirect stdout)
        original_stdout = sys.stdout
        sys.stdout = self.file
        print(*args, **kwargs)
        self.file.flush()  # Ensure immediate write
        sys.stdout = original_stdout

    def close(self):
        """Close the log file."""
        if self.file:
            self.file.close()


def main():
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"test_results.{timestamp}.txt"

    # Initialize logger
    logger = TeeLogger(log_filename)

    try:
        logger.print("🚀 Simple Test Runner")
        logger.print("=" * 50)
        logger.print(f"📝 Saving output to: {log_filename}")
        logger.print(
            f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 1. Confirm we're in the tests directory
        logger.print("\n📁 Checking directory...")
        current_dir = Path.cwd()
        if current_dir.name != "tests":
            logger.print("❌ ERROR: Not running from tests directory")
            logger.print(f"   Current directory: {current_dir}")
            logger.print("   Please run this script from the tests/ directory")
            return 1
        logger.print(f"✅ Running from tests directory: {current_dir}")

        # 2. Confirm we can read the .env file
        logger.print("\n📄 Checking .env file...")
        env_file = Path(".env")
        if not env_file.exists():
            logger.print("❌ ERROR: .env file not found")
            logger.print("   Please create .env file in tests directory")
            return 1

        try:
            with open(env_file, 'r') as f:
                env_content = f.read()
            if len(env_content.strip()) == 0:
                logger.print("❌ ERROR: .env file is empty")
                return 1
            logger.print(
                f"✅ .env file found and readable ({len(env_content)} chars)")
        except Exception as e:
            logger.print(f"❌ ERROR: Cannot read .env file: {e}")
            return 1

        # 3. Confirm expected test scripts exist
        logger.print("\n🧪 Checking for test files...")

        # New functionality tests
        new_tests = [
            'test_invitations.py',
            'test_client_group_entities.py',
            'test_count_apis.py',
            'test_schema_changes.py',
            'test_cors_comprehensive.py'
        ]

        # Regression tests
        regression_tests = [
            'test_users.py',
            'test_client_groups.py',
            'test_entities.py',
            'test_entity_types.py',
            'test_client_group_membership.py',
            'test_valid_entities.py'
        ]

        expected_tests = new_tests + regression_tests

        logger.print(f"📋 New functionality tests ({len(new_tests)}):")
        for test in new_tests:
            logger.print(f"  • {test}")

        logger.print(f"\n📋 Regression tests ({len(regression_tests)}):")
        for test in regression_tests:
            logger.print(f"  • {test}")

        missing_tests = []
        for test_file in expected_tests:
            test_path = Path(test_file)
            if test_path.exists():
                logger.print(f"✅ Found: {test_file}")
            else:
                logger.print(f"❌ Missing: {test_file}")
                missing_tests.append(test_file)

        if missing_tests:
            logger.print(f"\n❌ ERROR: {len(missing_tests)} test files missing")
            return 1

        logger.print(f"\n✅ All {len(expected_tests)} test files found")

        # 4. Run all test scripts
        logger.print("\n🎯 Running all tests...")

        results = {}
        failed_tests = []
        timed_out_tests = []

        for i, test_file in enumerate(expected_tests, 1):
            logger.print(f"\n[{i}/{len(expected_tests)}] Running: {test_file}")
            logger.print("-" * 40)

            try:
                result = subprocess.run(
                    ['python3', '-m', 'pytest', test_file, '-v'],
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout per test
                )

                logger.print(f"Exit code: {result.returncode}")
                results[test_file] = result.returncode

                if result.returncode == 0:
                    logger.print("✅ PASSED")
                else:
                    logger.print("❌ FAILED")
                    failed_tests.append(test_file)

                    # Show detailed error information for failed tests
                    if result.stdout:
                        logger.print("\n--- DETAILED FAILURE OUTPUT ---")
                        # Show the full stdout for debugging
                        lines = result.stdout.split('\n')

                        # Find and show test failures
                        failure_lines = [
                            line for line in lines if 'FAILED' in line or 'ERROR' in line]
                        if failure_lines:
                            logger.print("Failed test cases:")
                            for line in failure_lines:
                                logger.print(f"  • {line}")

                        # Show assertion errors and other detailed error info
                        in_failure_section = False
                        failure_details = []
                        for line in lines:
                            if 'FAILURES' in line or 'ERRORS' in line:
                                in_failure_section = True
                            elif in_failure_section and line.strip() and not line.startswith('='):
                                failure_details.append(line)
                            elif in_failure_section and line.startswith('=') and len(failure_details) > 0:
                                break

                        if failure_details:
                            logger.print("\nDetailed error information:")
                            # Limit to 50 lines
                            for line in failure_details[:50]:
                                logger.print(f"  {line}")
                            if len(failure_details) > 50:
                                logger.print(
                                    f"  ... ({len(failure_details) - 50} more lines truncated)")

                    if result.stderr:
                        logger.print(f"\nSTDERR output:")
                        # First 1000 chars of stderr
                        logger.print(f"  {result.stderr[:1000]}")

            except subprocess.TimeoutExpired as e:
                logger.print("⏰ TIMED OUT (2 minutes)")
                timed_out_tests.append(test_file)
                results[test_file] = 'TIMEOUT'

                # Show partial output from timed out test
                logger.print("\n--- PARTIAL OUTPUT BEFORE TIMEOUT ---")
                if hasattr(e, 'stdout') and e.stdout:
                    logger.print("STDOUT (last 1000 chars):")
                    logger.print(f"  {e.stdout[-1000:]}")
                if hasattr(e, 'stderr') and e.stderr:
                    logger.print("STDERR (last 500 chars):")
                    logger.print(f"  {e.stderr[-500:]}")
                logger.print("--- END TIMEOUT DETAILS ---")

            except Exception as e:
                logger.print(f"💥 ERROR: {e}")
                failed_tests.append(test_file)
                results[test_file] = 'ERROR'

        # Summary Report
        logger.print("\n" + "=" * 60)
        logger.print("📊 TEST SUMMARY REPORT")
        logger.print("=" * 60)

        passed = sum(1 for r in results.values() if r == 0)
        failed = len(failed_tests)
        timeouts = len(timed_out_tests)

        logger.print(f"Total tests: {len(expected_tests)}")
        logger.print(f"✅ Passed: {passed}")
        logger.print(f"❌ Failed: {failed}")
        logger.print(f"⏰ Timed out: {timeouts}")

        if passed == len(expected_tests):
            logger.print("\n🎉 All tests passed!")
            final_result = 0
        else:
            logger.print(f"\n⚠️  {failed + timeouts} tests had issues")

            if failed_tests:
                logger.print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
                for test in failed_tests:
                    if results[test] != 'TIMEOUT':
                        logger.print(f"  • {test}")
                        logger.print(
                            f"    💡 Recommendation: Check detailed failure output above for specific errors")
                        logger.print(
                            f"    🔧 Common fixes: Authentication, API connectivity, test data conflicts")

            if timed_out_tests:
                logger.print(f"\n⏰ TIMED OUT TESTS ({len(timed_out_tests)}):")
                for test in timed_out_tests:
                    logger.print(f"  • {test}")
                    logger.print(
                        f"    💡 Recommendation: Check partial output above to see where it hung")
                    logger.print(
                        f"    🔧 Common fixes: API timeouts, hanging authentication, infinite loops")

            logger.print(f"\n🛠️  NEXT STEPS:")
            logger.print(
                f"  1. Review detailed failure output above for each failed test")
            logger.print(
                f"  2. Check API connectivity and authentication credentials")
            logger.print(f"  3. Run individual tests to isolate issues:")
            for test in (failed_tests + timed_out_tests)[:3]:  # Show first 3
                logger.print(f"     python3 -m pytest {test} -v -s")
            if len(failed_tests + timed_out_tests) > 3:
                logger.print(
                    f"     ... and {len(failed_tests + timed_out_tests) - 3} more")

            final_result = 1

        # Final summary
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.print(f"\n⏰ Completed at: {end_time}")
        logger.print(f"📝 Full output saved to: {log_filename}")

        return final_result

    except Exception as e:
        if 'logger' in locals():
            logger.print(f"\n💥 FATAL ERROR: {e}")
            logger.print(f"📝 Partial output saved to: {log_filename}")
        else:
            print(f"\n💥 FATAL ERROR: {e}")
        return 1

    finally:
        # Always close the logger
        if 'logger' in locals():
            logger.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
