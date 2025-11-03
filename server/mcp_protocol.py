"""Simple MCP Protocol Implementation via stdio"""

import sys
import json
import logging
from typing import Dict, List, Any, Callable, Optional

logger = logging.getLogger(__name__)


class MCPServer:
    """Simple MCP Server implementation using stdio."""

    def __init__(self, name: str):
        self.name = name
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.tool_handlers: Dict[str, Callable] = {}

    def add_tool(self, name: str, description: str, input_schema: Dict[str, Any], handler: Callable):
        """Register a tool with its handler."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
        }
        self.tool_handlers[name] = handler

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming MCP request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "tools/list":
                # Return list of available tools
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": list(self.tools.values())
                    }
                }

            elif method == "tools/call":
                # Call a tool
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                if tool_name not in self.tool_handlers:
                    raise ValueError(f"Unknown tool: {tool_name}")

                handler = self.tool_handlers[tool_name]
                result = await handler(arguments)

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": result
                    }
                }

            elif method == "initialize":
                # Handle initialization
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "0.1.0",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": self.name,
                            "version": "2.0.0"
                        }
                    }
                }

            elif method == "initialized":
                # Acknowledge initialization
                return None

            else:
                raise ValueError(f"Unknown method: {method}")

        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    async def run(self):
        """Run the MCP server on stdio."""
        logger.info(f"Starting {self.name} MCP server on stdio...")

        try:
            while True:
                # Read line from stdin
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    # Parse JSON-RPC request
                    request = json.loads(line)
                    logger.debug(f"Received request: {request}")

                    # Handle request
                    response = await self.handle_request(request)

                    # Send response if not None
                    if response is not None:
                        response_str = json.dumps(response)
                        sys.stdout.write(response_str + "\n")
                        sys.stdout.flush()
                        logger.debug(f"Sent response: {response}")

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    sys.stdout.write(json.dumps(error_response) + "\n")
                    sys.stdout.flush()

        except KeyboardInterrupt:
            logger.info("Server interrupted")
        finally:
            logger.info("MCP server stopped")


def text_content(text: str) -> List[Dict[str, str]]:
    """Create a text content response for MCP."""
    return [{"type": "text", "text": text}]
