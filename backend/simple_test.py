#!/usr/bin/env python3
"""Simple test of our DEVONthink components without ML dependencies"""

def test_basic_functionality():
    print("🧪 Testing basic DEVONthink integration components...")
    
    # Test 1: Basic imports
    try:
        import sys
        sys.path.insert(0, '.')
        print("✅ Path configured")
        
        # Test just the schema without importing the full app
        import importlib.util
        
        # Load schema module directly
        spec = importlib.util.spec_from_file_location(
            "devonthink_schemas", 
            "./app/schemas/devonthink_schemas.py"
        )
        schema_module = importlib.util.module_from_spec(spec)
        
        # Mock the dependencies for testing
        import sys
        from unittest.mock import MagicMock
        
        # Mock the db module
        mock_db = MagicMock()
        mock_db.DevonthinkSyncStatus = MagicMock()
        sys.modules['app.db'] = mock_db
        
        spec.loader.exec_module(schema_module)
        print("✅ DEVONthink schemas loaded successfully")
        
        # Test creating a sync request
        DevonthinkSyncRequest = schema_module.DevonthinkSyncRequest
        request = DevonthinkSyncRequest(
            database_name="Reference",
            search_space_id=1
        )
        print(f"✅ Sync request created: {request.database_name}")
        
        # Test MCP client basics
        spec2 = importlib.util.spec_from_file_location(
            "devonthink_mcp_client", 
            "./app/services/devonthink_mcp_client.py"
        )
        mcp_module = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(mcp_module)
        
        client = mcp_module.DevonthinkMCPClient()
        print("✅ MCP client created successfully")
        
        print("🎉 Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    exit(0 if success else 1)