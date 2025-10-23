#!/usr/bin/env python3
"""
Simple test to verify DEVONthink MCP connection works
"""

import asyncio
import os
from app.services.devonthink_mcp_client import DevonthinkMCPClient

async def test_connection():
    print("Testing DEVONthink MCP connection...")
    
    # Set environment variable for real MCP
    os.environ['DEVONTHINK_MCP_BACKEND'] = 'real'
    
    client = DevonthinkMCPClient()
    
    try:
        # Test 1: Check if DEVONthink is running
        print("\n1. Testing if DEVONthink is running...")
        is_running = await client.is_devonthink_running()
        print(f"   DEVONthink running: {is_running}")
        
        if not is_running:
            print("   ❌ DEVONthink not detected. Make sure DEVONthink is open.")
            return
        
        # Test 2: Get open databases
        print("\n2. Getting open databases...")
        databases = await client.get_open_databases()
        print(f"   Found {len(databases)} databases:")
        for db in databases:
            print(f"     - {db['name']} (ID: {db.get('id', 'N/A')})")
        
        # Test 3: Test searching for PDFs in Reference database
        print("\n3. Searching for PDFs in Reference database...")
        try:
            pdf_records = await client.search_records("kind:pdf", database_name="Reference", limit=5)
            print(f"   Found {len(pdf_records)} PDF records (showing first 5):")
            for i, record in enumerate(pdf_records[:5], 1):
                name = record.get('name', 'Unknown')
                path = record.get('path', 'Unknown path')
                print(f"     {i}. {name}")
                print(f"        Path: {path}")
        except Exception as e:
            print(f"   Error searching for PDFs: {str(e)}")
        
        print("\n✅ MCP connection test completed!")
        
    except Exception as e:
        print(f"❌ Error testing MCP connection: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection())