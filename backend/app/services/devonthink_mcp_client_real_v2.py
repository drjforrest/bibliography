import asyncio
import json
import logging
import subprocess
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DevonthinkMCPClientRealV2:
    """Real MCP client that connects to the mcp-server-devonthink via subprocess"""
    
    def __init__(self, mcp_server_path: str = "/Users/drjforrest/dev/repos/mcp-server-devonthink/dist/index.js"):
        self.mcp_server_path = mcp_server_path
        self.process = None
        self.request_id = 0
        
    async def _get_next_request_id(self) -> int:
        """Get next request ID for MCP protocol"""
        self.request_id += 1
        return self.request_id
    
    @asynccontextmanager
    async def _mcp_connection(self):
        """Context manager for MCP server connection"""
        try:
            # Start the MCP server as a subprocess
            self.process = await asyncio.create_subprocess_exec(
                'node', self.mcp_server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Initialize the MCP connection
            await self._initialize_connection()
            
            yield self.process
            
        except Exception as e:
            logger.error(f"Error with MCP connection: {str(e)}")
            raise
        finally:
            if self.process:
                try:
                    self.process.terminate()
                    await self.process.wait()
                except:
                    pass
                self.process = None
    
    async def _initialize_connection(self):
        """Initialize the MCP connection with handshake"""
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": await self._get_next_request_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "bibliography-devonthink-client",
                    "version": "1.0.0"
                }
            }
        }
        
        await self._send_request(init_request)
        response = await self._read_response()
        
        if not response.get("result"):
            raise Exception(f"MCP initialization failed: {response}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        await self._send_request(initialized_notification)
        
    async def _send_request(self, request: Dict[str, Any]):
        """Send a request to the MCP server"""
        if not self.process or not self.process.stdin:
            raise Exception("MCP process not running")
            
        request_str = json.dumps(request) + '\n'
        self.process.stdin.write(request_str.encode())
        await self.process.stdin.drain()
        
    async def _read_response(self) -> Dict[str, Any]:
        """Read a response from the MCP server with improved buffering"""
        if not self.process or not self.process.stdout:
            raise Exception("MCP process not running")
        
        # Read with timeout and proper buffering
        try:
            # Try to read a complete line first (longer timeout for large files)
            line = await asyncio.wait_for(self.process.stdout.readline(), timeout=60.0)
            if not line:
                raise Exception("MCP server closed connection")
            
            response_text = line.decode().strip()
            
            # If the line seems incomplete (no closing brace), try to read more
            if response_text and not response_text.endswith('}'):
                # Read additional chunks until we have a complete JSON
                additional_chunks = []
                while True:
                    try:
                        chunk = await asyncio.wait_for(self.process.stdout.read(65536), timeout=10.0)
                        if not chunk:
                            break
                        chunk_text = chunk.decode()
                        additional_chunks.append(chunk_text)
                        if chunk_text.endswith('}'):
                            break
                    except asyncio.TimeoutError:
                        break
                
                if additional_chunks:
                    response_text += ''.join(additional_chunks)
            
            return json.loads(response_text)
            
        except asyncio.TimeoutError:
            raise Exception("MCP server response timeout")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode MCP response (length: {len(response_text) if 'response_text' in locals() else 'unknown'})")
            logger.error(f"Response preview: {response_text[:500] if 'response_text' in locals() else 'N/A'}...")
            raise Exception(f"Invalid JSON response from MCP server: {str(e)}")
    
    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        if arguments is None:
            arguments = {}
            
        async with self._mcp_connection():
            request = {
                "jsonrpc": "2.0",
                "id": await self._get_next_request_id(),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            await self._send_request(request)
            response = await self._read_response()
            
            if "error" in response:
                logger.error(f"MCP tool error: {response['error']}")
                return {"success": False, "error": response["error"]}
            
            if "result" in response:
                result = response["result"]
                # Handle MCP tool response format
                if "content" in result:
                    # Parse content if it's text
                    content = result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        if content[0].get("type") == "text":
                            try:
                                # Try to parse as JSON
                                parsed_content = json.loads(content[0]["text"])
                                return {"success": True, **parsed_content}
                            except:
                                # Return as text if not JSON
                                return {"success": True, "text": content[0]["text"]}
                
                return {"success": True, **result}
            
            return {"success": False, "error": "No result in response"}
    
    async def is_devonthink_running(self) -> bool:
        """Check if DEVONthink is running"""
        try:
            result = await self._call_tool("is_running")
            return result.get("isRunning", False)
        except Exception as e:
            logger.error(f"Error checking if DEVONthink is running: {str(e)}")
            return False
    
    async def get_open_databases(self) -> List[Dict[str, Any]]:
        """Get list of open DEVONthink databases"""
        try:
            result = await self._call_tool("get_open_databases")
            if result.get("success"):
                return result.get("databases", [])
            else:
                logger.error(f"Failed to get databases: {result}")
                return []
        except Exception as e:
            logger.error(f"Error getting databases: {str(e)}")
            return []
    
    async def search_records(self, query: str, database_name: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Search for records in DEVONthink with pagination support"""
        try:
            # Handle None limit by setting a reasonable default
            if limit is None:
                limit = 1000  # Default to 1000 if no limit specified
            
            # Use smaller batch sizes to prevent MCP response overflow
            batch_size = min(limit, 50)  # Limit to 50 records per batch
            all_results = []
            offset = 0
            
            while len(all_results) < limit:
                # Calculate how many more records we need
                remaining = limit - len(all_results)
                current_batch_size = min(batch_size, remaining)
                
                params = {"query": query}
                if database_name:
                    params["database"] = database_name
                params["limit"] = current_batch_size
                
                # Add offset for pagination if supported
                if offset > 0:
                    # Try to modify query to skip records we've already seen
                    # This is a simple approach - DEVONthink search might not support offset directly
                    pass
                
                result = await self._call_tool("search", params)
                
                if result.get("success"):
                    batch_results = result.get("results", [])
                    if not batch_results:
                        # No more results
                        break
                    
                    all_results.extend(batch_results)
                    
                    # If we got fewer results than requested, we've reached the end
                    if len(batch_results) < current_batch_size:
                        break
                    
                    offset += len(batch_results)
                else:
                    logger.error(f"Search failed: {result}")
                    break
            
            return all_results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching records: {str(e)}")
            return []
    
    async def get_record_properties(self, record_uuid: str = None, record_id: int = None) -> Optional[Dict[str, Any]]:
        """Get properties of a DEVONthink record"""
        try:
            params = {}
            if record_uuid:
                params["uuid"] = record_uuid
            elif record_id:
                params["id"] = record_id
            else:
                raise ValueError("Either record_uuid or record_id must be provided")
                
            result = await self._call_tool("get_record_properties", params)
            
            if result.get("success"):
                return result
            else:
                logger.error(f"Failed to get record properties: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting record properties: {str(e)}")
            return None
    
    async def get_record_content(self, record_uuid: str = None, record_id: int = None) -> Optional[bytes]:
        """Get content of a DEVONthink record"""
        try:
            params = {}
            if record_uuid:
                params["uuid"] = record_uuid
            elif record_id:
                params["id"] = record_id
            else:
                raise ValueError("Either record_uuid or record_id must be provided")
                
            result = await self._call_tool("get_record_content", params)
            
            if result.get("success") and "content" in result:
                import base64
                content_str = result["content"]
                if isinstance(content_str, str):
                    try:
                        return base64.b64decode(content_str)
                    except Exception as e:
                        logger.error(f"Error decoding base64 content: {str(e)}")
                        # Try with error handling for non-ASCII characters
                        try:
                            content_bytes = content_str.encode('utf-8', errors='ignore')
                            return base64.b64decode(content_bytes)
                        except Exception as e2:
                            logger.error(f"Error with UTF-8 encoding fallback: {str(e2)}")
                            return None
                else:
                    # Content might already be bytes
                    return content_str
            else:
                logger.error(f"Failed to get record content: {result}")
                return None
            
        except Exception as e:
            logger.error(f"Error getting record content: {str(e)}")
            return None
    
    async def list_group_content(self, group_uuid: str = None, group_path: str = None, 
                               database_name: str = None) -> List[Dict[str, Any]]:
        """List contents of a group/folder"""
        try:
            params = {}
            if group_uuid:
                params["uuid"] = group_uuid
            elif group_path:
                params["path"] = group_path
            else:
                # List root content
                params = {}
            
            if database_name:
                params["database"] = database_name
                
            result = await self._call_tool("list_group_content", params)
            
            if result.get("success"):
                return result.get("results", [])
            else:
                logger.error(f"Failed to list group content: {result}")
                return []
            
        except Exception as e:
            logger.error(f"Error listing group content: {str(e)}")
            return []
    
    async def search_recent_changes(self, days: int = 1, database_name: str = None) -> List[Dict[str, Any]]:
        """Search for recently modified records"""
        # Use DEVONthink search syntax for recent changes
        query = f"created:#{days}days OR modified:#{days}days"
        return await self.search_records(query, database_name)
    
    async def copy_record_to_path(self, record_uuid: str, destination_path: str, database_name: str = None) -> Optional[Dict[str, Any]]:
        """Copy a DEVONthink record directly to a filesystem path"""
        try:
            params = {"uuid": record_uuid, "destinationPath": destination_path}
            if database_name:
                params["databaseName"] = database_name
                
            result = await self._call_tool("copy_record_to_path", params)
            
            if result.get("success"):
                return result
            else:
                logger.error(f"Failed to copy record to path: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error copying record to path: {str(e)}")
            return None
    
    async def close(self):
        """Clean up resources"""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except:
                pass
            self.process = None