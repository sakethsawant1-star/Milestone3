import os
import sys
import asyncio
from typing import Any, Dict, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client


class GrowwMCPClient:
    """
    MCP Client that connects to the Google Workspace MCP Server.

    Supports two modes:
      - LOCAL (stdio): Spawns mcp_server.py as a subprocess (default for development)
      - REMOTE (SSE):  Connects to a deployed Railway URL via Server-Sent Events

    Usage:
        # Local stdio mode (default)
        async with GrowwMCPClient() as client:
            tools = await client.list_tools()

        # Remote SSE mode (Railway deployment)
        async with GrowwMCPClient(sse_url="https://your-app.up.railway.app/sse") as client:
            tools = await client.list_tools()
    """

    def __init__(self, server_script_path: str = None, sse_url: str = None):
        """
        Args:
            server_script_path: Path to mcp_server.py for stdio mode. Ignored if sse_url is set.
            sse_url: Full URL to the remote SSE endpoint (e.g. https://your-app.up.railway.app/sse).
                     If set, the client connects over HTTP instead of spawning a subprocess.
                     Can also be set via the MCP_SERVER_URL environment variable.
        """
        # Resolve the SSE URL: explicit arg > env var > None (fallback to stdio)
        self.sse_url = sse_url or os.environ.get("MCP_SERVER_URL")

        if not self.sse_url:
            # Stdio mode: resolve the server script path
            if server_script_path is None:
                self.server_script_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "mcp_server.py"
                )
            else:
                self.server_script_path = server_script_path

        self._client_context = None
        self._session_context = None
        self.session: ClientSession = None
        self._mode = "sse" if self.sse_url else "stdio"

    async def connect(self):
        """Establish the connection and initialize the MCP session."""
        if self._mode == "sse":
            # Remote SSE connection
            self._client_context = sse_client(self.sse_url)
        else:
            # Local stdio connection
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[self.server_script_path]
            )
            self._client_context = stdio_client(server_params)

        read, write = await self._client_context.__aenter__()

        self._session_context = ClientSession(read, write)
        self.session = await self._session_context.__aenter__()

        await self.session.initialize()
        return self

    async def disconnect(self):
        """Clean up resources."""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
            self._session_context = None

        if self._client_context:
            await self._client_context.__aexit__(None, None, None)
            self._client_context = None

        self.session = None

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server."""
        if not self.session:
            raise RuntimeError("Client not connected")

        result = await self.session.list_tools()
        tools = []
        for tool in result.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            })
        return tools

    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server."""
        if not self.session:
            raise RuntimeError("Client not connected")

        result = await self.session.call_tool(name, arguments)
        return result

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    async def main():
        # Auto-detect mode based on environment
        sse_url = os.environ.get("MCP_SERVER_URL")
        mode_label = f"SSE ({sse_url})" if sse_url else "stdio (local)"
        print(f"Connecting to GoogleWorkspaceMCP Server via {mode_label}...")

        async with GrowwMCPClient() as client:
            print("Connected successfully.")
            tools = await client.list_tools()
            print("\nAvailable Tools:")
            for tool in tools:
                print(f" - {tool['name']}: {tool['description']}")

    asyncio.run(main())
