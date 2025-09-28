#!/usr/bin/env python3
"""
Test script to verify the semaphore logic in updatePandaPositions.py
"""

import pymysql
from updatePandaPositions import acquire_distributed_lock, release_distributed_lock, get_db_connection
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))


def test_semaphore_logic():
    """Test the semaphore logic by simulating multiple Lambda contexts."""

    print("Testing semaphore logic...")

    # Create mock contexts
    context1 = type('Context', (), {
        'log_stream_name': 'test-stream-1',
        'aws_request_id': 'req-123'
    })()

    context2 = type('Context', (), {
        'log_stream_name': 'test-stream-2',
        'aws_request_id': 'req-456'
    })()

    try:
        # Clean up any existing locks first
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM lambda_locks WHERE lock_id = 'Position Keeper'")
        connection.commit()
        cursor.close()
        connection.close()
        print("Cleaned up existing locks")

        # Test 1: First context should acquire lock successfully
        print("\nTest 1: First context acquiring lock...")
        result1 = acquire_distributed_lock(context1)
        print(f"Context 1 acquired lock: {result1}")
        assert result1 == True, "First context should acquire lock successfully"

        # Test 2: Second context should fail to acquire lock
        print("\nTest 2: Second context trying to acquire lock...")
        result2 = acquire_distributed_lock(context2)
        print(f"Context 2 acquired lock: {result2}")
        assert result2 == False, "Second context should fail to acquire lock"

        # Test 3: First context should release lock successfully
        print("\nTest 3: First context releasing lock...")
        result3 = release_distributed_lock(context1)
        print(f"Context 1 released lock: {result3}")
        assert result3 == True, "First context should release lock successfully"

        # Test 4: Second context should now be able to acquire lock
        print("\nTest 4: Second context acquiring lock after release...")
        result4 = acquire_distributed_lock(context2)
        print(f"Context 2 acquired lock: {result4}")
        assert result4 == True, "Second context should now acquire lock successfully"

        # Test 5: Clean up
        print("\nTest 5: Cleaning up...")
        result5 = release_distributed_lock(context2)
        print(f"Context 2 released lock: {result5}")
        assert result5 == True, "Second context should release lock successfully"

        print("\n✅ All semaphore tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_semaphore_logic()
    sys.exit(0 if success else 1)
