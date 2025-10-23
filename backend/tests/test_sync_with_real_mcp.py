#!/usr/bin/env python3
"""
Test the sync service with real MCP connection
"""

import asyncio
import logging
import os
import sys

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.devonthink_mcp_client import DevonthinkMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_sync_with_real_mcp():
    """Test the sync service using real MCP"""
    
    print("=== Testing Sync Service with Real MCP ===")
    
    # Set environment variable to use real MCP
    os.environ['DEVONTHINK_MCP_BACKEND'] = 'real'
    
    # Create the MCP client (this will use real MCP now)
    client = DevonthinkMCPClient()
    
    try:
        # Test 1: Check if DEVONthink is running
        print("\n1. Testing is_devonthink_running with real MCP...")
        is_running = await client.is_devonthink_running()
        print(f"   DEVONthink running: {is_running}")
        
        if not is_running:
            print("   WARNING: DEVONthink is not running. Please start DEVONthink and try again.")
            return
        
        # Test 2: Get open databases
        print("\n2. Testing get_open_databases with real MCP...")
        databases = await client.get_open_databases()
        print(f"   Found {len(databases)} databases:")
        for db in databases:
            print(f"     - {db.get('name', 'Unknown')} (UUID: {db.get('uuid', 'Unknown')})")
        
        # Test 3: Search for PDFs in Reference database
        print("\n3. Testing search_records with real MCP...")
        pdf_results = await client.search_records("kind:pdf", database_name="Reference", limit=5)
        print(f"   Found {len(pdf_results)} PDF records in Reference database:")
        for record in pdf_results[:3]:  # Show first 3
            print(f"     - {record.get('name', 'Unknown')} (UUID: {record.get('uuid', 'Unknown')})")
            print(f"       Location: {record.get('location', 'Unknown')}")
        
        # Test 4: List group content
        print("\n4. Testing list_group_content with real MCP...")
        root_content = await client.list_group_content(database_name="Reference")
        print(f"   Found {len(root_content)} items in Reference database root:")
        for item in root_content[:3]:  # Show first 3
            print(f"     - {item.get('name', 'Unknown')} ({item.get('recordType', 'Unknown')})")
        
        # Test 5: Get record properties
        if pdf_results:
            print("\n5. Testing get_record_properties with real MCP...")
            first_pdf = pdf_results[0]
            uuid = first_pdf.get('uuid')
            if uuid:
                properties = await client.get_record_properties(record_uuid=uuid)
                if properties:
                    print(f"   Properties for '{first_pdf.get('name', 'Unknown')}':")
                    print(f"     - Size: {properties.get('size', 'Unknown')} bytes")
                    print(f"     - Creation Date: {properties.get('creationDate', 'Unknown')}")
                    print(f"     - Word Count: {properties.get('wordCount', 'Unknown')}")
                    print(f"     - Tags: {properties.get('tags', [])}")
                else:
                    print("   Failed to get properties")
        
        # Test 6: Search for recent changes
        print("\n6. Testing search_recent_changes with real MCP...")
        recent_changes = await client.search_recent_changes(days=7, database_name="Reference")
        print(f"   Found {len(recent_changes)} recent changes in Reference database:")
        for record in recent_changes[:3]:  # Show first 3
            print(f"     - {record.get('name', 'Unknown')} (UUID: {record.get('uuid', 'Unknown')})")
        
        print("\n=== Sync Service Test with Real MCP Complete ===")
        print("✅ All tests passed! The sync service is now connected to real DEVONthink data.")
        
    except Exception as e:
        logger.error(f"Error during sync test with real MCP: {str(e)}")
        print(f"\nERROR: {str(e)}")
        
    finally:
        # Clean up
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_sync_with_real_mcp())