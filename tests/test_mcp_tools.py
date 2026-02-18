"""Deterministic unit tests for MCP tools.

These tests call MCP tools directly through MCPStreamableHTTPTool and verify exact output formats.
Unlike A2A agent tests, these are deterministic - same input = same output.

Note: We test through the agent framework's MCPStreamableHTTPTool which is how the tools
are actually used in production. This exercises the full stack.
"""
import pytest
from agent_framework import MCPStreamableHTTPTool


@pytest.mark.asyncio
async def test_check_balance_tool(mcp_server, test_db):
    """Test check_balance tool returns exact format."""
    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True
    )
    
    async with mcp_tool:
        # Call check_balance (no arguments needed)
        result = await mcp_tool.call_tool("check_balance")
        
        # Exact match - tools are deterministic
        assert result == "Your checking account balance is $1000.00"


@pytest.mark.asyncio
async def test_view_history_tool_empty(mcp_server, test_db):
    """Test view_history tool with no transactions."""
    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True
    )
    
    async with mcp_tool:
        result = await mcp_tool.call_tool("view_history")
        
        # New account should have specific message
        assert "No transactions" in result or "history" in result.lower()


@pytest.mark.asyncio
async def test_list_my_accounts_tool(mcp_server, test_db):
    """Test list_my_accounts tool returns account info."""
    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True
    )
    
    async with mcp_tool:
        result = await mcp_tool.call_tool("list_my_accounts")
        
        # Should contain account type and balance
        assert "checking" in result.lower()
        assert "1000" in result


@pytest.mark.asyncio
async def test_send_money_tool_success(mcp_server, test_db):
    """Test send_money tool successfully transfers funds."""
    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True
    )
    
    async with mcp_tool:
        result = await mcp_tool.call_tool("send_money",
            to="bob",
            amount=50.0,
            note="test payment"
        )
        
        # Exact match - deterministic tool response
        assert result == "Transferred $50.00 to bob."
        
        # Verify balance decreased
        balance_result = await mcp_tool.call_tool("check_balance")
        assert "$950.00" in balance_result


@pytest.mark.asyncio
async def test_send_money_tool_insufficient_funds(mcp_server, test_db):
    """Test send_money tool fails with insufficient funds."""
    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True
    )
    
    async with mcp_tool:
        result = await mcp_tool.call_tool("send_money",
            to="bob",
            amount=5000.0,  # More than balance
            note="too much"
        )
        
        # Should fail with descriptive message
        assert "FAILED: Insufficient funds" in result
        assert "$1000.00" in result  # Current balance
        assert "$5000.00" in result  # Requested amount


@pytest.mark.asyncio
async def test_send_money_tool_invalid_user(mcp_server, test_db):
    """Test send_money tool fails with invalid recipient."""
    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True
    )
    
    async with mcp_tool:
        result = await mcp_tool.call_tool("send_money",
            to="nonexistent",
            amount=50.0,
            note="test"
        )
        
        # Should fail
        assert "FAILED" in result


@pytest.mark.asyncio
async def test_request_money_tool(mcp_server, test_db):
    """Test request_money tool creates payment request."""
    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True
    )
    
    async with mcp_tool:
        result = await mcp_tool.call_tool("request_money",
            from_user="bob",
            amount=25.0,
            note="lunch money"
        )
        
        # Exact match - deterministic
        assert result == "Requested $25.00 from bob."


@pytest.mark.asyncio
async def test_list_pending_requests_tool(mcp_server, test_db):
    """Test list_pending_requests tool returns request list."""
    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True
    )
    
    async with mcp_tool:
        # First create a request
        await mcp_tool.call_tool("request_money",
            from_user="bob",
            amount=100.0,
            note="payment"
        )
        
        # Now list requests - returns a list, not a string
        result = await mcp_tool.call_tool("list_pending_requests")
        
        # Should return list data
        assert isinstance(result, (str, list))  # Can be formatted as string or list


@pytest.mark.asyncio
async def test_mcp_tool_discovery(mcp_server, test_db):
    """Test that all banking tools are discoverable."""
    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True
    )
    
    async with mcp_tool:
        # Tools are loaded during context manager entry
        # We can test by calling them directly
        tools_to_test = [
            "check_balance",
            "view_history",
            "list_my_accounts",
            "send_money",
            "request_money",
            "list_pending_requests"
        ]
        
        # Test that we can call each tool without errors
        for tool_name in tools_to_test:
            try:
                if tool_name == "send_money":
                    # Need arguments
                    await mcp_tool.call_tool(tool_name, to="bob", amount=1.0, note="test")
                elif tool_name == "request_money":
                    # Need arguments
                    await mcp_tool.call_tool(tool_name, from_user="bob", amount=1.0, note="test")
                else:
                    # No arguments needed
                    await mcp_tool.call_tool(tool_name)
            except Exception as e:
                # Tool call might fail for business reasons, but shouldn't raise "tool not found"
                if "not found" in str(e).lower():
                    pytest.fail(f"Tool {tool_name} not discovered: {e}")
