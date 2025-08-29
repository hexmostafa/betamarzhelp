import asyncio
import sys
import os
from datetime import datetime
from typing import Optional
from database import db
from marzban_api import marzban_api
import config

async def test_database_init() -> tuple[bool, str]:
    try:
        await db.init_db()
        return True, "Database initialized successfully"
    except Exception as e:
        return False, f"Database init failed: {e}"

async def test_database_operations() -> tuple[bool, str]:
    try:
        test_admin = {
            "user_id": 999999999,
            "username": "test_admin",
            "max_users": 1,
            "max_total_time": 3600,
            "max_total_traffic": 1073741824,
            "is_active": True
        }
        await db.add_admin(test_admin)
        admin = await db.get_admin(999999999)
        if admin:
            await db.delete_admin(999999999)
            return True, "Database operations successful"
        return False, "Failed to retrieve admin"
    except Exception as e:
        return False, f"Database operations failed: {e}"

async def test_marzban_api() -> tuple[bool, str]:
    try:
        return await marzban_api.test_connection(), "API test completed"
    except Exception as e:
        return False, f"API test failed: {e}"

async def main():
    results = []
    
    print("\n=== Health Check ===")
    # Test 1: Database Init
    db_init_success, db_init_details = await test_database_init()
    print(f"Database Init: {'âœ…' if db_init_success else 'âŒ'} {db_init_details}")
    results.append(("Database Init", db_init_success))
    
    # Test 2: Database Operations
    if db_init_success:
        db_ops_success, db_ops_details = await test_database_operations()
        print(f"Database Operations: {'âœ…' if db_ops_success else 'âŒ'} {db_ops_details}")
        results.append(("Database Operations", db_ops_success))
    else:
        results.append(("Database Operations", False))
    
    # Test 3: Marzban API
    api_success, api_details = await test_marzban_api()
    print(f"Marzban API: {'âœ…' if api_success else 'âŒ'} {api_details}")
    results.append(("Marzban API", api_success))
    
    # Summary
    passed = sum(1 for _, success in results if success)
    print(f"\nResult: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("ðŸŽ‰ All tests passed!")
        return 0
    else:
        print("âš ï¸ Some tests failed.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
