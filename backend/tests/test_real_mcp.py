#!/usr/bin/env python3
"""
Test script for real MCP connection to DEVONthink
"""

import asyncio
import logging
import os
import sys

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.devonthink_mcp_client_real_v2 import DevonthinkMCPClientRealV2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_mcp_connection():
    """Test the MCP connection to DEVONthink"""
    
    print("=== Testing MCP Connection to DEVONthink ===")
    
    # Create the MCP client
    client = DevonthinkMCPClientRealV2()
    
    try:
        # Test 1: Check if DEVONthink is running
        print("\n1. Testing is_devonthink_running...")
        is_running = await client.is_devonthink_running()
        print(f"   DEVONthink running: {is_running}")
        
        if not is_running:
            print("   WARNING: DEVONthink is not running. Please start DEVONthink and try again.")
            return
        
        # Test 2: Get open databases
        print("\n2. Testing get_open_databases...")
        databases = await client.get_open_databases()
        print(f"   Found {len(databases)} databases:")
        for db in databases:
            print(f"     - {db.get('name', 'Unknown')} (UUID: {db.get('uuid', 'Unknown')})")
        
        # Test 3: Search for PDFs
        print("\n3. Testing search_records (looking for PDFs)...")
        pdf_results = await client.search_records("kind:pdf", limit=5)
        print(f"   Found {len(pdf_results)} PDF records:")
        for record in pdf_results[:3]:  # Show first 3
            print(f"     - {record.get('name', 'Unknown')} (UUID: {record.get('uuid', 'Unknown')})")
        
        # Test 4: List root content of Reference database
        print("\n4. Testing list_group_content (root of Reference database)...")
        reference_db = None
        for db in databases:
            if db.get('name') == 'Reference':
                reference_db = db
                break
        
        if reference_db:
            root_content = await client.list_group_content(database_name="Reference")
            print(f"   Found {len(root_content)} items in Reference database root:")
            for item in root_content[:3]:  # Show first 3
                print(f"     - {item.get('name', 'Unknown')} ({item.get('recordType', 'Unknown')})")
        else:
            print("   No 'Reference' database found")
        
        # Test 5: Get properties of first PDF if available
        if pdf_results:
            print("\n5. Testing get_record_properties...")
            first_pdf = pdf_results[0]
            uuid = first_pdf.get('uuid')
            if uuid:
                properties = await client.get_record_properties(record_uuid=uuid)
                if properties:
                    print(f"   Properties for '{first_pdf.get('name', 'Unknown')}':")
                    print(f"     - Size: {properties.get('size', 'Unknown')} bytes")
                    print(f"     - Creation Date: {properties.get('creationDate', 'Unknown')}")
                    print(f"     - Location: {properties.get('location', 'Unknown')}")
                else:
                    print("   Failed to get properties")
        
        print("\n=== MCP Connection Test Complete ===")
        
    except Exception as e:
        logger.error(f"Error during MCP test: {str(e)}")
        print(f"\nERROR: {str(e)}")
        
    finally:
        # Clean up
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_mcp_connection())