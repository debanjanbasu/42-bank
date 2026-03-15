"""MCP Client Helper - Connects agents to MCP server for tool execution."""

from agent_framework import MCPStreamableHTTPTool


def get_banking_mcp_tools(mcp_server_url: str = "http://localhost:8001/mcp"):
    """
    Get banking tools from MCP server as agent_framework MCPTools.

    Args:
        mcp_server_url: URL of the MCP HTTP server (should end with /mcp)

    Returns:
        Single MCPStreamableHTTPTool that auto-discovers all tools from the server
    """
    # Ensure URL ends with /mcp
    if not mcp_server_url.endswith("/mcp"):
        mcp_server_url = f"{mcp_server_url}/mcp"

    # Create a single MCP tool that will discover all tools from the server
    # The MCPStreamableHTTPTool will connect to the server and load all available tools
    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=mcp_server_url,
        load_tools=True,  # Auto-discover tools from server
        terminate_on_close=False,  # Don't terminate session on close
    )

    return mcp_tool
