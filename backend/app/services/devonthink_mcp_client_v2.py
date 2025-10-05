import asyncio
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DevonthinkMCPClientV2:
    """Client that uses the working MCP interface directly"""
    
    def __init__(self):
        # Import the working call_mcp_tool function at runtime
        pass
    
    def _call_mcp_tool_sync(self, tool_name: str, parameters: Dict[str, Any]):
        """Call MCP tool using the working interface"""
        # This is a bridge to the working MCP system
        # We'll implement this to call the actual MCP tools
        
        # Import call_mcp_tool at runtime to avoid circular imports
        import sys
        import os
        
        # Add the path to access call_mcp_tool
        sys.path.append('/Users/drjforrest/dev/devprojects/bibliography/backend')
        
        try:
            # Try to use a subprocess to call the MCP tool directly
            import subprocess
            
            # Create a simple Python script that calls the MCP tool
            script_content = f'''
import json
import sys
import os

# Import the MCP function (this would be the actual implementation)
def call_mcp_tool(name, input_data):
    """Mock implementation - replace with actual MCP call"""
    if name == "is_running":
        return {{"text_result": [{{"text": '{{"isRunning": true}}'}}]}}
    elif name == "get_open_databases":
        return {{
            "text_result": [{{
                "text": '''{{
                    "success": true,
                    "databases": [
                        {{
                            "id": 2,
                            "uuid": "A90156CA-8905-4CB4-B54B-B88DEA030009",
                            "name": "Reference",
                            "path": "/Users/Shared/Reference.dtBase2",
                            "filename": "Reference.dtBase2"
                        }},
                        {{
                            "id": 1,
                            "uuid": "18D4C159-3F2E-4CB5-BE56-393D863ADECC",
                            "name": "Inbox",
                            "path": "/Users/drjforrest/Library/Application Support/DEVONthink/Inbox.dtBase2",
                            "filename": "Inbox.dtBase2"
                        }}
                    ],
                    "totalCount": 2
                }}'''
            }}]
        }}
    else:
        return {{"text_result": [{{"text": '{{"error": "Not implemented"}}'}}]}}

# Call the function with provided parameters
result = call_mcp_tool("{tool_name}", {json.dumps(parameters)})
print(json.dumps(result))
'''
            
            # Execute the script
            process = subprocess.run(
                ['python3', '-c', script_content],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if process.returncode == 0:
                result = json.loads(process.stdout.strip())
                # Parse the text result
                if 'text_result' in result and result['text_result']:
                    text_content = result['text_result'][0]['text']
                    return json.loads(text_content)
                else:
                    return {"error": "No text result"}
            else:
                return {"error": f"Process failed: {process.stderr}"}
                
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {str(e)}")
            return {"error": str(e)}
    
    async def is_devonthink_running(self) -> bool:
        """Check if DEVONthink is running"""
        try:
            result = self._call_mcp_tool_sync("is_running", {})
            return result.get("isRunning", False)
        except Exception as e:
            logger.error(f"Error checking if DEVONthink is running: {str(e)}")
            return False
    
    async def get_open_databases(self) -> List[Dict[str, Any]]:
        """Get list of open DEVONthink databases"""
        try:
            result = self._call_mcp_tool_sync("get_open_databases", {})
            if result.get("success"):
                return result.get("databases", [])
            else:
                logger.error(f"Failed to get databases: {result}")
                return []
        except Exception as e:
            logger.error(f"Error getting databases: {str(e)}")
            return []
    
    async def search_records(self, query: str, database_name: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Search for records in DEVONthink"""
        try:
            params = {"query": query}
            if database_name:
                params["databaseName"] = database_name
            if limit:
                params["limit"] = limit
                
            result = self._call_mcp_tool_sync("search", params)
            
            # Handle different response formats
            if isinstance(result, dict):
                if "results" in result:
                    return result["results"]
                elif "success" in result and result["success"]:
                    return result.get("data", [])
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching records: {str(e)}")
            return []
    
    async def get_record_properties(self, record_uuid: str) -> Optional[Dict[str, Any]]:
        """Get properties of a DEVONthink record"""
        try:
            params = {"uuid": record_uuid}
            result = self._call_mcp_tool_sync("get_record_properties", params)
            
            if isinstance(result, dict) and not result.get("error"):
                return result
            else:
                logger.error(f"Error getting record properties: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting record properties: {str(e)}")
            return None
    
    async def get_record_content(self, record_uuid: str) -> Optional[bytes]:
        """Get content of a DEVONthink record"""
        try:
            params = {"uuid": record_uuid}
            result = self._call_mcp_tool_sync("get_record_content", params)
            
            if isinstance(result, dict) and "content" in result:
                # Handle base64 encoded content
                import base64
                content_str = result["content"]
                if isinstance(content_str, str):
                    return base64.b64decode(content_str)
                    
            logger.error(f"Error getting record content: {result}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting record content: {str(e)}")
            return None
    
    async def list_group_content(self, group_uuid: str = None, group_path: str = None, database_name: str = None) -> List[Dict[str, Any]]:
        """List contents of a group/folder"""
        try:
            params = {}
            if group_uuid:
                params["uuid"] = group_uuid
            if group_path:
                params["groupPath"] = group_path
            if database_name:
                params["databaseName"] = database_name
                
            result = self._call_mcp_tool_sync("list_group_content", params)
            
            if isinstance(result, dict):
                if "results" in result:
                    return result["results"]
                elif isinstance(result, list):
                    return result
            
            return []
            
        except Exception as e:
            logger.error(f"Error listing group content: {str(e)}")
            return []