#!/usr/bin/env python3
print("Testing if run_all_tests.py can be imported...", flush=True)

try:
    print("About to import run_all_tests module...", flush=True)
    import run_all_tests
    print("✅ Module imported successfully", flush=True)
except Exception as e:
    print(f"❌ Import failed: {e}", flush=True)
