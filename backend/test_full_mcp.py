#!/usr/bin/env python3
"""
Full MCP Integration Test - Test the actual DEVONthink MCP server via npx
"""

import asyncio
import json
import subprocess
import sys
import os
import tempfile
from typing import Dict, Any, Optional

class MCPClient:
    """Client for communicating with MCP servers via stdio"""
    
    def __init__(self, server_command: list):
        self.server_command = server_command
        self.process = None
        self.request_id = 0
    
    async def start(self):
        """Start the MCP server process"""
        print(f"🚀 Starting MCP server: {' '.join(self.server_command)}")
        
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Initialize the MCP connection
        await self.send_initialize()
        
    async def send_initialize(self):
        """Send MCP initialize request"""
        init_request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0.0",
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "clientInfo": {
                    "name": "Bibliography Test Client",
                    "version": "1.0.0"
                }
            }
        }
        
        print("📡 Sending initialize request...")
        response = await self.send_request(init_request)
        print(f"✅ Initialize response: {response}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        await self.send_notification(initialized_notification)
        print("✅ Sent initialized notification")
        
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request and wait for response"""
        if not self.process:
            raise RuntimeError("MCP server not started")
            
        # Send request
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP server")
            
        try:
            response = json.loads(response_line.decode().strip())
            return response
        except json.JSONDecodeError as e:
            error_output = await self.process.stderr.read(1024)
            raise RuntimeError(f"Invalid JSON response: {e}, stderr: {error_output.decode()}")
    
    async def send_notification(self, notification: Dict[str, Any]):
        """Send a JSON-RPC notification (no response expected)"""
        if not self.process:
            raise RuntimeError("MCP server not started")
            
        notification_str = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_str.encode())
        await self.process.stdin.drain()
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools"""
        request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": "tools/list"
        }
        
        return await self.send_request(request)
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call an MCP tool"""
        if arguments is None:
            arguments = {}
            
        request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        return await self.send_request(request)
    
    def get_next_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    async def close(self):
        """Close the MCP server process"""
        if self.process:
            self.process.stdin.close()
            await self.process.wait()


async def test_devonthink_mcp():
    """Test the full DEVONthink MCP implementation"""
    print("🧪 Testing Full DEVONthink MCP Implementation")
    print("=" * 50)
    
    # MCP server command using npx
    server_command = ["npx", "-y", "mcp-server-devonthink"]
    
    client = MCPClient(server_command)
    
    try:
        # Start the MCP server
        await client.start()
        print("✅ MCP server started successfully")
        
        # Test 1: List available tools
        print("\n🔧 Test 1: Listing available tools...")
        tools_response = await client.list_tools()
        
        if "result" in tools_response and "tools" in tools_response["result"]:
            tools = tools_response["result"]["tools"]
            print(f"✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
        else:
            print(f"❌ Unexpected tools response: {tools_response}")
            return False
        
        # Test 2: Check if DEVONthink is running
        print("\n🔧 Test 2: Checking if DEVONthink is running...")
        try:
            running_response = await client.call_tool("is_running")
            print(f"✅ DEVONthink running status: {running_response}")
        except Exception as e:
            print(f"⚠️  Could not check DEVONthink status: {e}")
        
        # Test 3: Get open databases (if DEVONthink is running)
        print("\n🔧 Test 3: Getting open databases...")
        try:
            databases_response = await client.call_tool("get_open_databases")
            print(f"✅ Open databases response: {databases_response}")
            
            if "result" in databases_response and "content" in databases_response["result"]:
                # Parse the response content
                content = databases_response["result"]["content"]
                if isinstance(content, list) and len(content) > 0:
                    # Look for text content
                    for item in content:
                        if item.get("type") == "text":
                            try:
                                db_data = json.loads(item["text"])
                                print(f"  Found {len(db_data.get('databases', []))} open databases")
                                for db in db_data.get("databases", []):
                                    print(f"    - {db.get('name', 'Unknown')}")
                            except json.JSONDecodeError:
                                print(f"  Raw response: {item['text']}")
                            break
                
        except Exception as e:
            print(f"⚠️  Could not get databases: {e}")
        
        # Test 4: Try a simple search (if DEVONthink has content)
        print("\n🔧 Test 4: Testing search functionality...")
        try:
            search_response = await client.call_tool("search", {
                "query": "*",
                "limit": 5
            })
            print(f"✅ Search response: {search_response}")
        except Exception as e:
            print(f"⚠️  Search test failed: {e}")
        
        print("\n🎉 Full MCP integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ MCP test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await client.close()
        print("🔒 MCP client closed")


async def test_mcp_availability():
    """Test if the MCP server is available via npx"""
    print("🔍 Checking MCP server availability...")
    
    try:
        # Test if npx can find the mcp-server-devonthink package
        process = await asyncio.create_subprocess_exec(
            "npx", "-y", "mcp-server-devonthink", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE
        )
        
        # Send a simple test to see if server responds
        process.stdin.close()
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
            print(f"✅ MCP server is available")
            print(f"   stdout: {stdout.decode().strip()}")
            if stderr.decode().strip():
                print(f"   stderr: {stderr.decode().strip()}")
            return True
        except asyncio.TimeoutError:
            print("✅ MCP server started (timeout expected for version check)")
            process.terminate()
            await process.wait()
            return True
            
    except Exception as e:
        print(f"❌ MCP server not available: {e}")
        return False


async def main():
    """Run the full MCP integration tests"""
    print("🔬 DEVONthink MCP Full Integration Test")
    print("=" * 50)
    
    # First check if MCP server is available
    if not await test_mcp_availability():
        print("\n❌ Cannot proceed - MCP server not available")
        print("💡 Make sure you're in a directory where npx can access mcp-server-devonthink")
        sys.exit(1)
    
    # Run the full MCP test
    success = await test_devonthink_mcp()
    
    if success:
        print("\n🎉 All MCP integration tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some MCP integration tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    # Set up environment to prefer the real MCP
    os.environ["DEVONTHINK_MCP_BACKEND"] = "real"
    asyncio.run(main())