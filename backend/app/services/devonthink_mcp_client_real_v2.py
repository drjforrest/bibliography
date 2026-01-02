import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DevonthinkMCPClientRealV2:
    """Real MCP client that connects to the mcp-server-devonthink via subprocess"""

    def __init__(
        self,
        mcp_server_path: str = None,
    ):
        # Find MCP server path dynamically if not provided
        if mcp_server_path is None:
            mcp_server_path = self._find_mcp_server()

        self.mcp_server_path = mcp_server_path
        self.process = None
        self.request_id = 0
        self._connection_initialized = False

    def _find_mcp_server(self) -> str:
        """Find the MCP server installation path"""
        # Try to find global npm installation first
        try:
            # Check npm global prefix for installed packages
            npm_prefix_result = subprocess.run(
                ["npm", "config", "get", "prefix"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if npm_prefix_result.returncode == 0:
                npm_prefix = npm_prefix_result.stdout.strip()
                global_node_modules = os.path.join(npm_prefix, "lib", "node_modules")
                mcp_path = os.path.join(
                    global_node_modules, "mcp-server-devonthink", "dist", "index.js"
                )
                if os.path.exists(mcp_path):
                    logger.info(f"Found global npm MCP server at: {mcp_path}")
                    return mcp_path
        except Exception as e:
            logger.debug(f"Could not check npm global prefix: {e}")

        # Try checking npx cache (where npx stores downloaded packages)
        try:
            npx_cache_dir = os.path.expanduser("~/.npm/_npx")
            if os.path.exists(npx_cache_dir):
                # Search for mcp-server-devonthink in npx cache
                for item in os.listdir(npx_cache_dir):
                    item_path = os.path.join(
                        npx_cache_dir,
                        item,
                        "node_modules",
                        "mcp-server-devonthink",
                        "dist",
                        "index.js",
                    )
                    if os.path.exists(item_path):
                        logger.info(f"Found npx cached MCP server at: {item_path}")
                        return item_path
        except Exception as e:
            logger.debug(f"Could not check npx cache: {e}")

        # Try common local paths
        user_home = os.path.expanduser("~")
        common_paths = [
            f"{user_home}/mcp-server-devonthink/dist/index.js",
            "/Users/jforrest/mcp-server-devonthink/dist/index.js",  # Production server
            os.path.join(
                os.path.dirname(__file__),
                "../../../mcp-server-devonthink/dist/index.js",
            ),
        ]

        for path in common_paths:
            if os.path.exists(path):
                logger.info(f"Found local MCP server at: {path}")
                return path

        # Fallback to npx (slower but works)
        if shutil.which("npx"):
            logger.warning(
                "MCP server not found locally, will use npx (slower - consider installing globally: npm install -g mcp-server-devonthink)"
            )
            return "npx"
        else:
            raise FileNotFoundError(
                "MCP server not found and npx is not available. "
                "Please install it globally: npm install -g mcp-server-devonthink"
            )

    async def _get_next_request_id(self) -> int:
        """Get next request ID for MCP protocol"""
        self.request_id += 1
        return self.request_id

    def _find_node_executable(self) -> str:
        """Find Node.js executable path dynamically"""
        # Try to find node in PATH first
        node_path = shutil.which("node")
        if node_path:
            return node_path

        # Check common nvm locations for current user
        user_home = os.path.expanduser("~")
        nvm_paths = [
            f"{user_home}/.nvm/versions/node/v22.21.1/bin/node",
            f"{user_home}/.nvm/versions/node/v22/bin/node",
            f"{user_home}/.nvm/versions/node/v20/bin/node",
            f"{user_home}/.nvm/versions/node/v18/bin/node",
            # Also check system-wide nvm (for production server)
            "/Users/jforrest/.nvm/versions/node/v22.21.1/bin/node",
        ]

        for path in nvm_paths:
            if os.path.exists(path):
                return path

        # Check common system paths
        system_paths = [
            "/usr/local/bin/node",
            "/opt/homebrew/bin/node",
            "/usr/bin/node",
        ]

        for path in system_paths:
            if os.path.exists(path):
                return path

        # Fallback: try to use 'node' and hope it's in PATH
        logger.warning(
            "Could not find Node.js in common locations, trying 'node' from PATH"
        )
        return "node"

    async def _ensure_connection(self):
        """Ensure MCP server connection is established (persistent connection)"""
        if self.process and self._connection_initialized:
            # Check if process is still alive
            if self.process.returncode is None:
                return
            else:
                logger.warning("MCP process died, restarting...")
                self.process = None
                self._connection_initialized = False

        # Start the MCP server as a subprocess
        # Find node executable dynamically for cross-platform support
        node_path = self._find_node_executable()

        if not os.path.exists(node_path) and node_path != "node":
            raise FileNotFoundError(
                f"Node.js not found at {node_path}. "
                f"Please install Node.js or set NODE_PATH environment variable."
            )

        # If mcp_server_path is "npx", use npx to run the server
        if self.mcp_server_path == "npx":
            # Use npx directly - it will find node itself
            npx_path = shutil.which("npx")
            if not npx_path:
                raise FileNotFoundError("npx not found in PATH")

            logger.info(f"Starting MCP server via npx: {npx_path}")
            self.process = await asyncio.create_subprocess_exec(
                npx_path,
                "--yes",
                "mcp-server-devonthink",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            # Use node to run the MCP server file
            if not os.path.exists(self.mcp_server_path):
                raise FileNotFoundError(
                    f"MCP server file not found at: {self.mcp_server_path}"
                )

            logger.info(f"Starting MCP server: {node_path} {self.mcp_server_path}")
            self.process = await asyncio.create_subprocess_exec(
                node_path,
                self.mcp_server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        # Initialize the MCP connection
        await self._initialize_connection()
        self._connection_initialized = True

    async def _initialize_connection(self):
        """Initialize the MCP connection with handshake"""
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": await self._get_next_request_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                "clientInfo": {
                    "name": "bibliography-devonthink-client",
                    "version": "1.0.0",
                },
            },
        }

        await self._send_request(init_request)
        response = await self._read_response()

        if not response.get("result"):
            raise Exception(f"MCP initialization failed: {response}")

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }

        await self._send_request(initialized_notification)

    async def _send_request(self, request: Dict[str, Any]):
        """Send a request to the MCP server"""
        if not self.process or not self.process.stdin:
            raise Exception("MCP process not running")

        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode())
        await self.process.stdin.drain()

    async def _read_response(self) -> Dict[str, Any]:
        """Read a response from the MCP server with improved buffering for large responses"""
        if not self.process or not self.process.stdout:
            raise Exception("MCP process not running")

        # Read with timeout and proper buffering
        try:
            # Read response in chunks, accumulating until we have complete JSON
            # MCP protocol uses newline-delimited JSON, but responses can be very large
            response_chunks = []
            buffer = b""
            max_size = 10 * 1024 * 1024  # 10MB max response size
            chunk_size = 1024 * 1024  # 1MB chunks
            total_read = 0
            timeout = 120.0  # 2 minute timeout for large responses

            start_time = asyncio.get_event_loop().time()

            while True:
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise Exception(f"MCP server response timeout after {timeout}s")

                # Check size limit
                if total_read > max_size:
                    raise Exception(
                        f"MCP response exceeds maximum size ({max_size} bytes)"
                    )

                # Try to read a chunk
                try:
                    chunk = await asyncio.wait_for(
                        self.process.stdout.read(chunk_size), timeout=10.0
                    )
                    if not chunk:
                        # EOF reached
                        break

                    buffer += chunk
                    total_read += len(chunk)

                    # Try to decode and find complete JSON
                    try:
                        text = buffer.decode("utf-8")
                        # Look for complete JSON objects (ending with })
                        # Count braces to find complete JSON
                        brace_count = 0
                        json_start = -1
                        json_end = -1

                        for i, char in enumerate(text):
                            if char == "{":
                                if json_start == -1:
                                    json_start = i
                                brace_count += 1
                            elif char == "}":
                                brace_count -= 1
                                if brace_count == 0 and json_start != -1:
                                    json_end = i + 1
                                    break

                        if json_end > 0:
                            # Found complete JSON
                            response_text = text[json_start:json_end]
                            # Keep any remaining data in buffer for next response
                            buffer = text[json_end:].encode("utf-8")
                            return json.loads(response_text)

                    except (UnicodeDecodeError, json.JSONDecodeError):
                        # Not complete JSON yet, continue reading
                        pass

                except asyncio.TimeoutError:
                    # If we have data, try to parse it anyway
                    if buffer:
                        try:
                            text = buffer.decode("utf-8")
                            # Look for complete JSON
                            brace_count = 0
                            json_start = -1
                            json_end = -1

                            for i, char in enumerate(text):
                                if char == "{":
                                    if json_start == -1:
                                        json_start = i
                                    brace_count += 1
                                elif char == "}":
                                    brace_count -= 1
                                    if brace_count == 0 and json_start != -1:
                                        json_end = i + 1
                                        break

                            if json_end > 0:
                                response_text = text[json_start:json_end]
                                buffer = text[json_end:].encode("utf-8")
                                return json.loads(response_text)
                        except:
                            pass
                    # Continue reading if timeout but no complete JSON yet
                    continue

            # If we get here, try to parse whatever we have
            if buffer:
                try:
                    text = buffer.decode("utf-8").strip()
                    # Remove any leading text before first {
                    json_start = text.find("{")
                    if json_start >= 0:
                        text = text[json_start:]
                    return json.loads(text)
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    logger.error(
                        f"Failed to decode MCP response. Buffer length: {len(buffer)}"
                    )
                    logger.error(
                        f"Buffer preview: {text[:1000] if 'text' in locals() else buffer[:1000]}"
                    )
                    raise Exception(f"Invalid JSON response from MCP server: {str(e)}")

            raise Exception("MCP server closed connection without sending response")

        except Exception as e:
            if "timeout" in str(e).lower() or "exceed" in str(e).lower():
                raise
            logger.error(f"Error reading MCP response: {str(e)}")
            raise Exception(f"Error reading MCP response: {str(e)}")

    async def _call_tool(
        self, tool_name: str, arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call a tool on the MCP server (uses persistent connection)"""
        if arguments is None:
            arguments = {}

        # Ensure connection is established (persistent across calls)
        await self._ensure_connection()

        request = {
            "jsonrpc": "2.0",
            "id": await self._get_next_request_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
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
                            # Return as text if not JSON - might be base64 content
                            # Check if this is the content field we're looking for
                            text_content = content[0]["text"]
                            # If it looks like base64, preserve it in content field
                            if len(text_content) > 100 and re.match(
                                r"^[A-Za-z0-9+/=\s]*$", text_content[:200]
                            ):
                                return {"success": True, "content": text_content}
                            return {"success": True, "text": text_content}

                # If content is directly a string (base64), return it
                if isinstance(content, str):
                    return {"success": True, "content": content}

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

    async def search_records(
        self, query: str, database_name: str = None, limit: int = None
    ) -> List[Dict[str, Any]]:
        """Search for records in DEVONthink with pagination support"""
        try:
            # Handle None limit by setting a reasonable default
            if limit is None:
                limit = 1000  # Default to 1000 if no limit specified

            # MCP server has stdout buffer limits, so we need to use smaller batches
            # Batch size that works reliably with DEVONthink MCP server
            batch_size = 100  # Smaller batches to avoid stdout maxBuffer exceeded
            all_results = []
            seen_uuids = set()  # Track unique records by UUID
            consecutive_empty_batches = 0
            max_empty_batches = 3  # Stop after 3 empty batches

            while len(all_results) < limit:
                # Calculate how many more records we need
                remaining = limit - len(all_results)
                current_batch_size = min(batch_size, remaining)

                params = {"query": query}
                if database_name:
                    params["database"] = database_name
                params["limit"] = current_batch_size

                result = await self._call_tool("search", params)

                if result.get("success"):
                    batch_results = result.get("results", [])

                    if not batch_results:
                        # No more results
                        consecutive_empty_batches += 1
                        if consecutive_empty_batches >= max_empty_batches:
                            logger.debug(
                                f"Reached end of results after {consecutive_empty_batches} empty batches"
                            )
                            break
                        continue
                    else:
                        consecutive_empty_batches = 0

                    # De-duplicate by UUID
                    unique_in_batch = []
                    for record in batch_results:
                        uuid = record.get("uuid") or str(record.get("id", ""))
                        if uuid and uuid not in seen_uuids:
                            seen_uuids.add(uuid)
                            unique_in_batch.append(record)

                    all_results.extend(unique_in_batch)

                    logger.debug(
                        f"Batch returned {len(batch_results)} records, {len(unique_in_batch)} unique (total unique: {len(all_results)})"
                    )

                    # If we got fewer unique results than requested, we might be getting duplicates
                    # Continue anyway since we're deduplicating
                    if len(batch_results) < current_batch_size:
                        # Got fewer than requested - likely reached the end
                        logger.debug(
                            f"Got fewer results than requested ({len(batch_results)} < {current_batch_size}), stopping"
                        )
                        break
                else:
                    logger.error(f"Search failed: {result}")
                    break

            logger.info(
                f"Search completed: {len(all_results)} unique records found (requested up to {limit})"
            )
            return all_results[:limit]

        except Exception as e:
            logger.error(f"Error searching records: {str(e)}")
            return []

    async def get_record_properties(
        self, record_uuid: str = None, record_id: int = None
    ) -> Optional[Dict[str, Any]]:
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

    async def get_record_content(
        self, record_uuid: str = None, record_id: int = None
    ) -> Optional[bytes]:
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

                content_val = result["content"]

                # Check if content is already bytes
                if isinstance(content_val, bytes):
                    logger.debug("Content is already bytes, returning directly")
                    return content_val

                # Handle string content
                if isinstance(content_val, str):
                    # Log the actual content format for debugging
                    logger.debug(f"Content type: string, length: {len(content_val)}")

                    # Check if it's already a file path (unlikely but handle it)
                    if content_val.startswith("/") or content_val.startswith("~"):
                        logger.warning(
                            f"Content appears to be a file path: {content_val}"
                        )
                        return None

                    # Remove any whitespace/newlines from the string
                    content_str = "".join(content_val.split())

                    # Check if the string is pure ASCII (required for base64)
                    try:
                        # This will fail if there are non-ASCII characters
                        content_str.encode("ascii")
                        is_ascii = True
                    except UnicodeEncodeError:
                        is_ascii = False
                        logger.warning(
                            "Content string contains non-ASCII characters, attempting to handle"
                        )

                    if is_ascii:
                        # Fix padding if needed
                        missing_padding = len(content_str) % 4
                        if missing_padding:
                            content_str += "=" * (4 - missing_padding)

                        # Check if it looks like base64
                        if re.match(r"^[A-Za-z0-9+/=]*$", content_str):
                            try:
                                decoded = base64.b64decode(content_str, validate=False)
                                if len(decoded) > 0:
                                    logger.debug(
                                        f"Successfully decoded {len(decoded)} bytes from base64"
                                    )
                                    return decoded
                                else:
                                    logger.error("Decoded content is empty")
                                    return None
                            except Exception as e:
                                logger.error(
                                    f"Base64 decode failed even though string looks valid: {str(e)}"
                                )
                                return None
                        else:
                            logger.error(
                                f"Content doesn't match base64 pattern. First 100 chars: {content_str[:100]}"
                            )
                            return None
                    else:
                        # Non-ASCII content - this suggests the MCP server is returning text content, not binary
                        # This is expected behavior - MCP's get_record_content returns text, not binary PDF
                        # We use file path method instead, so this is not an error, just expected behavior
                        logger.debug(
                            f"MCP server returned text content (expected - not binary PDF). "
                            f"First 200 chars: {content_val[:200]}"
                        )
                        logger.debug(
                            "Note: PDFs are retrieved via file path method, not via MCP get_record_content. "
                            "This is expected and handled by the sync service."
                        )
                        return None
                else:
                    logger.error(f"Unexpected content type: {type(content_val)}")
                    return None
            else:
                error_msg = (
                    result.get("error", "Unknown error") if result else "No result"
                )
                logger.error(f"Failed to get record content: {error_msg}")
                return None

        except Exception as e:
            logger.error(f"Error getting record content: {str(e)}")
            return None

    async def list_group_content(
        self, group_uuid: str = None, group_path: str = None, database_name: str = None
    ) -> List[Dict[str, Any]]:
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

    async def search_recent_changes(
        self, days: int = 1, database_name: str = None
    ) -> List[Dict[str, Any]]:
        """Search for recently modified records"""
        # Use DEVONthink search syntax for recent changes
        query = f"created:#{days}days OR modified:#{days}days"
        return await self.search_records(query, database_name)

    async def copy_record_to_path(
        self, record_uuid: str, destination_path: str, database_name: str = None
    ) -> Optional[Dict[str, Any]]:
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
        """Clean up resources and close persistent connection"""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("MCP process didn't terminate gracefully, killing it")
                try:
                    self.process.kill()
                    await self.process.wait()
                except:
                    pass
            except Exception as e:
                logger.debug(f"Error closing MCP process: {e}")
            finally:
                self.process = None
                self._connection_initialized = False
