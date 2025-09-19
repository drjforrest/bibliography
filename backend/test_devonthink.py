#!/usr/bin/env python3
"""
Simple test script for DEVONthink integration without starting the full server
"""

import sys
import os
sys.path.insert(0, '.')

def test_imports():
    """Test if our DEVONthink modules can be imported"""
    try:
        print("Testing DEVONthink schema imports...")
        from app.schemas.devonthink_schemas import DevonthinkSyncRequest, DevonthinkSyncResponse
        print("✅ DEVONthink schemas imported successfully")
        
        print("Testing MCP client import...")
        from app.services.devonthink_mcp_client import DevonthinkMCPClient
        print("✅ DEVONthink MCP client imported successfully")
        
        print("Testing database models...")
        from app.db import DevonthinkSync, DevonthinkFolder, DevonthinkSyncStatus
        print("✅ DEVONthink database models imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_mcp_client():
    """Test MCP client basic functionality"""
    try:
        print("Testing MCP client instantiation...")
        from app.services.devonthink_mcp_client import DevonthinkMCPClient
        client = DevonthinkMCPClient()
        print("✅ MCP client created successfully")
        
        print("Testing simulated tool call...")
        # This should work with our simulation
        import asyncio
        
        async def test_simulation():
            result = await client.is_devonthink_running()
            print(f"✅ is_devonthink_running() returned: {result}")
            
            databases = await client.get_open_databases()
            print(f"✅ get_open_databases() returned: {databases}")
            
            await client.close()
        
        asyncio.run(test_simulation())
        return True
    except Exception as e:
        print(f"❌ MCP client error: {e}")
        return False

def test_sync_request():
    """Test creating a sync request"""
    try:
        print("Testing sync request creation...")
        from app.schemas.devonthink_schemas import DevonthinkSyncRequest
        
        request = DevonthinkSyncRequest(
            database_name="Reference",
            search_space_id=1
        )
        print(f"✅ Sync request created: {request.database_name}")
        return True
    except Exception as e:
        print(f"❌ Sync request error: {e}")
        return False

def main():
    """Run all tests"""
    print("🔧 Testing DEVONthink Integration Components")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("MCP Client Tests", test_mcp_client), 
        ("Sync Request Tests", test_sync_request)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! DEVONthink integration is ready.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)