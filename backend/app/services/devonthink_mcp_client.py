import asyncio
import json
import logging
import os
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DevonthinkMCPClient:
    """Client for communicating with the DEVONthink MCP server"""
    
    def __init__(self):
        # Use the MCP tools directly via the same interface available in terminal
        self.available_tools = [
            'is_running', 'get_open_databases', 'list_group_content', 
            'get_record_properties', 'get_record_content', 'search', 
            'create_record', 'update_record_content', 'move_record',
            'add_tags', 'remove_tags', 'delete_record'
        ]
    
    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a DEVONthink MCP tool and return the result"""
        if parameters is None:
            parameters = {}
            
        try:
            logger.info(f"Calling DEVONthink MCP tool: {tool_name} with params: {parameters}")
            
            # Call the MCP tool through the terminal interface
            # This assumes the MCP server is available in the current environment
            result = await self._call_mcp_via_terminal(tool_name, parameters)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing MCP tool {tool_name}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _call_mcp_via_terminal(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool using environment-based configuration"""
        # Check environment variable to determine MCP backend
        mcp_backend = os.environ.get('DEVONTHINK_MCP_BACKEND', 'simulated')
        
        if mcp_backend == 'real':
            return await self._call_real_mcp(tool_name, parameters)
        else:
            # Use simulated responses for development
            logger.info(f"Using simulated MCP responses (set DEVONTHINK_MCP_BACKEND=real for actual MCP)")
            return await self._simulate_tool_call(tool_name, parameters)
    
    async def _call_real_mcp(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call real MCP tool using the proper MCP client"""
        try:
            # Import and use the real MCP client
            from .devonthink_mcp_client_real_v2 import DevonthinkMCPClientRealV2
            
            # Create a real MCP client instance
            real_client = DevonthinkMCPClientRealV2()
            
            # Map our tool calls to the real client methods
            try:
                if tool_name == 'is_running':
                    result = await real_client.is_devonthink_running()
                    return {"isRunning": result}
                    
                elif tool_name == 'get_open_databases':
                    databases = await real_client.get_open_databases()
                    return {
                        "success": True,
                        "databases": databases,
                        "totalCount": len(databases)
                    }
                    
                elif tool_name == 'search':
                    query = parameters.get("query", "")
                    database_name = parameters.get("databaseName")
                    limit = parameters.get("limit", None)  # Remove limit to allow all records
                    results = await real_client.search_records(query, database_name, limit)
                    return {
                        "success": True,
                        "results": results,
                        "totalCount": len(results)
                    }
                    
                elif tool_name == 'list_group_content':
                    group_uuid = parameters.get("uuid")
                    group_path = parameters.get("groupPath")
                    database_name = parameters.get("databaseName")
                    results = await real_client.list_group_content(group_uuid, group_path, database_name)
                    return {
                        "success": True,
                        "results": results
                    }
                    
                elif tool_name == 'get_record_properties':
                    record_uuid = parameters.get("uuid")
                    record_id = parameters.get("recordId")
                    result = await real_client.get_record_properties(record_uuid, record_id)
                    if result:
                        return {"success": True, **result}
                    else:
                        return {"success": False, "error": "Record not found"}
                        
                elif tool_name == 'get_record_content':
                    record_uuid = parameters.get("uuid")
                    record_id = parameters.get("recordId")
                    content = await real_client.get_record_content(record_uuid, record_id)
                    if content:
                        import base64
                        return {
                            "success": True,
                            "content": base64.b64encode(content).decode('utf-8'),
                            "contentType": "application/pdf"
                        }
                    else:
                        return {"success": False, "error": "Content not found"}
                
                elif tool_name == 'copy_record_to_path':
                    record_uuid = parameters.get("uuid")
                    destination_path = parameters.get("destinationPath")
                    database_name = parameters.get("databaseName")
                    result = await real_client.copy_record_to_path(record_uuid, destination_path, database_name)
                    if result:
                        return result
                    else:
                        return {"success": False, "error": "Failed to copy record"}
                        
                else:
                    logger.warning(f"Tool {tool_name} not implemented in real MCP mode, using simulation")
                    return await self._simulate_tool_call(tool_name, parameters)
                    
            finally:
                # Clean up the client
                await real_client.close()
                
        except Exception as e:
            logger.error(f"Error calling real MCP for {tool_name}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _simulate_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate MCP tool calls for development and testing"""
        logger.debug(f"Simulating MCP tool call: {tool_name}")
        
        if tool_name == "is_running":
            return {"isRunning": True}
        
        elif tool_name == "get_open_databases":
            return {
                "success": True,
                "databases": [
                    {
                        "id": 2,
                        "uuid": "A90156CA-8905-4CB4-B54B-B88DEA030009",
                        "name": "Reference",
                        "path": "/Users/Shared/Reference.dtBase2",
                        "filename": "Reference.dtBase2"
                    },
                    {
                        "id": 1,
                        "uuid": "18D4C159-3F2E-4CB5-BE56-393D863ADECC",
                        "name": "Inbox",
                        "path": "/Users/drjforrest/Library/Application Support/DEVONthink/Inbox.dtBase2",
                        "filename": "Inbox.dtBase2"
                    }
                ],
                "totalCount": 2
            }
        
        elif tool_name == "list_group_content":
            # Simulate folder structure based on parameters
            return {
                "success": True,
                "results": [
                    {
                        "id": 12345,
                        "uuid": "FOLDER-UUID-1",
                        "name": "Academic Papers",
                        "recordType": "group",
                        "location": "/Academic Papers"
                    },
                    {
                        "id": 12346,
                        "uuid": "PAPER-UUID-1", 
                        "name": "Sample Research Paper.pdf",
                        "recordType": "PDF document",
                        "location": "/Academic Papers",
                        "tags": ["research", "ai"],
                        "size": 1024000
                    }
                ]
            }
        
        elif tool_name == "get_record_properties":
            record_uuid = parameters.get("uuid", "PAPER-UUID-1")
            return {
                "success": True,
                "id": 12346,
                "uuid": record_uuid,
                "name": "Sample Research Paper.pdf",
                "path": "/Users/Shared/Reference.dtBase2/Files.noindex/pdf/sample.pdf",
                "location": "/Academic Papers",
                "recordType": "PDF document",
                "kind": "PDF+Text",
                "creationDate": "2024-01-01T10:00:00Z",
                "modificationDate": "2024-01-01T10:00:00Z", 
                "additionDate": "2024-01-01T10:00:00Z",
                "size": 1024000,
                "tags": ["research", "ai"],
                "comment": "Sample research paper for testing",
                "url": "https://example.com/paper",
                "wordCount": 5000,
                "characterCount": 35000
            }
        
        elif tool_name == "get_record_content":
            # Simulate PDF content - return base64 encoded dummy PDF
            import base64
            # This is a minimal PDF header - in real usage this would be actual PDF content
            dummy_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000125 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n205\n%%EOF"
            return {
                "success": True,
                "content": base64.b64encode(dummy_pdf).decode('utf-8'),
                "contentType": "application/pdf"
            }
        
        elif tool_name == "search":
            query = parameters.get("query", "")
            database_name = parameters.get("databaseName")
            limit = parameters.get("limit", None)  # Remove limit to allow all records
            
            # Simulate search results
            return {
                "success": True,
                "results": [
                    {
                        "id": 12346,
                        "uuid": "PAPER-UUID-1",
                        "name": "Sample Research Paper.pdf",
                        "path": "/Users/Shared/Reference.dtBase2/Files.noindex/pdf/sample.pdf",
                        "location": "/Academic Papers",
                        "recordType": "PDF document",
                        "kind": "PDF+Text",
                        "tags": ["research", "ai"],
                        "size": 1024000,
                        "score": 1.0
                    },
                    {
                        "id": 12347,
                        "uuid": "PAPER-UUID-2",
                        "name": "Another Research Paper.pdf",
                        "path": "/Users/Shared/Reference.dtBase2/Files.noindex/pdf/another.pdf",
                        "location": "/Academic Papers",
                        "recordType": "PDF document",
                        "kind": "PDF+Text", 
                        "tags": ["machine learning"],
                        "size": 2048000,
                        "score": 0.8
                    }
                ][:limit],
                "totalCount": 2
            }
        
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    async def is_devonthink_running(self) -> bool:
        """Check if DEVONthink is running"""
        result = await self._execute_tool("is_running")
        # Handle both simulated and real response formats
        if "isRunning" in result:
            return result["isRunning"]
        return result.get("success", False) and result.get("running", False)
    
    async def get_open_databases(self) -> List[Dict[str, Any]]:
        """Get list of open DEVONthink databases"""
        result = await self._execute_tool("get_open_databases")
        if result.get("success", False):
            return result.get("databases", [])
        return []
    
    async def list_group_content(self, group_uuid: str = None, group_path: str = None, 
                                database_name: str = None) -> List[Dict[str, Any]]:
        """List contents of a DEVONthink group/folder"""
        params = {}
        if group_uuid:
            params["uuid"] = group_uuid  # Updated parameter name
        elif group_path:
            params["groupPath"] = group_path
        if database_name:
            params["databaseName"] = database_name
            
        result = await self._execute_tool("list_group_content", params)
        if result.get("success", False):
            # Handle both 'records' and 'results' keys
            return result.get("records", result.get("results", []))
        return []
    
    async def get_record_properties(self, record_uuid: str = None, record_id: int = None,
                                  record_path: str = None, database_name: str = None) -> Optional[Dict[str, Any]]:
        """Get detailed properties of a DEVONthink record"""
        params = {}
        if record_uuid:
            params["uuid"] = record_uuid  # Updated parameter name
        elif record_id and database_name:
            params["recordId"] = record_id
            params["databaseName"] = database_name
        elif record_path:
            params["recordPath"] = record_path
            
        result = await self._execute_tool("get_record_properties", params)
        if result.get("success", False):
            # For simulated responses, the data is directly in the result
            record_data = result.get("record", result)
            # Remove success flag if present in record data
            if "success" in record_data:
                record_data = {k: v for k, v in record_data.items() if k != "success"}
            return record_data
        return None
    
    async def get_record_content(self, record_uuid: str = None, record_id: int = None,
                               record_path: str = None, database_name: str = None) -> Optional[bytes]:
        """Get binary content of a DEVONthink record"""
        params = {}
        if record_uuid:
            params["uuid"] = record_uuid  # Updated parameter name
        elif record_id and database_name:
            params["recordId"] = record_id
            params["databaseName"] = database_name
        elif record_path:
            params["recordPath"] = record_path
            
        result = await self._execute_tool("get_record_content", params)
        if result.get("success", False):
            # The MCP server should return base64 encoded content
            import base64
            content_b64 = result.get("content", "")
            if content_b64:
                return base64.b64decode(content_b64)
        return None
    
    async def search_records(self, query: str, database_name: str = None, 
                           group_uuid: str = None, comparison: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Search for records in DEVONthink"""
        params = {
            "query": query
        }
        if database_name:
            params["databaseName"] = database_name  # Updated parameter name
        if group_uuid:
            params["groupUuid"] = group_uuid
        if comparison:
            params["comparison"] = comparison
        if limit:
            params["limit"] = limit
            
        result = await self._execute_tool("search", params)
        if result.get("success", False):
            return result.get("results", [])
        return []
    
    async def search_recent_changes(self, days: int = 1, database_name: str = None) -> List[Dict[str, Any]]:
        """Search for recently modified records"""
        query = f"created:#{days}days OR modified:#{days}days"
        return await self.search_records(query, database_name)
    
    async def copy_record_to_path(self, record_uuid: str, destination_path: str, database_name: str = None) -> Optional[Dict[str, Any]]:
        """Copy a DEVONthink record directly to a filesystem path"""
        params = {"uuid": record_uuid, "destinationPath": destination_path}
        if database_name:
            params["databaseName"] = database_name
            
        result = await self._execute_tool("copy_record_to_path", params)
        if result.get("success", False):
            return result
        return None
    
    async def close(self):
        """Clean up any resources"""
        # No persistent connections to clean up in current implementation
        pass
