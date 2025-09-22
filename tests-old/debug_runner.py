#!/usr/bin/env python3
import time
import sys
import subprocess
print("DEBUG: Starting debug runner", flush=True)


print("DEBUG: Imports done", flush=True)


def main():
    print("DEBUG: In main function", flush=True)

    # Test files from the original runner
    test_files = ['test_invitations.py']

    print(f"DEBUG: About to test {test_files[0]}", flush=True)

    try:
        print(f"DEBUG: Running subprocess for {test_files[0]}", flush=True)
        result = subprocess.run(
            ['python3', '-m', 'pytest', test_files[0], '--tb=no'],
            capture_output=True, text=True, timeout=30)

        print(
            f"DEBUG: Subprocess completed with exit code {result.returncode}", flush=True)

        if result.returncode == 0:
            print(f"✅ {test_files[0]} PASSED")
        else:
            print(f"❌ {test_files[0]} FAILED")

    except subprocess.TimeoutExpired:
        print(f"⏰ {test_files[0]} TIMED OUT")
    except Exception as e:
        print(f"💥 Error: {e}")

    print("DEBUG: Main function completed", flush=True)
    return 0


if __name__ == "__main__":
    print("DEBUG: Script main block", flush=True)
    exit_code = main()
    print(f"DEBUG: Exiting with code {exit_code}", flush=True)
    sys.exit(exit_code)
