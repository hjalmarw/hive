"""Simple MCP Protocol Implementation via stdio"""

import sys
import json
import logging
import inspect
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

    def tool(self):
        """Decorator to register a function as an MCP tool."""
        def decorator(func: Callable):
            # Extract function name
            tool_name = func.__name__

            # Extract description from docstring
            description = func.__doc__ or ""
            description = description.strip()

            # Extract parameters from function signature
            sig = inspect.signature(func)
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                # Get type annotation
                annotation = param.annotation
                param_type = "string"  # default

                if annotation != inspect.Parameter.empty:
                    if annotation == str:
                        param_type = "string"
                    elif annotation == int:
                        param_type = "integer"
                    elif annotation == float:
                        param_type = "number"
                    elif annotation == bool:
                        param_type = "boolean"

                # Check if parameter has a default value
                has_default = param.default != inspect.Parameter.empty

                properties[param_name] = {
                    "type": param_type,
                    "description": f"Parameter {param_name}"
                }

                # Add to required if no default value
                if not has_default:
                    required.append(param_name)

            # Create input schema
            input_schema = {
                "type": "object",
                "properties": properties,
                "required": required
            }

            # Register the tool
            self.add_tool(tool_name, description, input_schema, func)

            return func

        return decorator

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
                # Call handler with unpacked arguments
                result = await handler(**arguments)

                # Ensure result is in the correct format
                if isinstance(result, str):
                    content = [{"type": "text", "text": result}]
                elif isinstance(result, list):
                    content = result
                else:
                    content = [{"type": "text", "text": str(result)}]

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": content
                    }
                }

            elif method == "initialize":
                # Handle initialization
                client_protocol = params.get("protocolVersion", "2024-11-05")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": client_protocol,
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
