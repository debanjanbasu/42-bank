"""Manager Agent - Handles escalations and oversight."""

from typing import Any, Optional

from agent_framework import Agent

from bank_agents._types import ChatClientProtocol


def get_agent(client: ChatClientProtocol, tools) -> Agent:
    """
    Create BankManager agent with MCP tools.

    Args:
        client: Chat client
        tools: MCP tools (single MCPStreamableHTTPTool or list)
    """
    instructions = (
        "You are the Bank Manager. User is authenticated. "
        "LANGUAGE: Always respond in ENGLISH only. "
        "Tools automatically use their account - DO NOT ask for details. "
        "Handle complex issues with available tools:\n"
        "- check_balance, view_history\n"
        "- list_pending_requests, list_products\n"
        "Use tools as needed to resolve issues. Respond in English."
    )
    return client.as_agent(
        name="BankManager",
        instructions=instructions,
        tools=tools,
    )
