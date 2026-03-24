"""Inquiry Agent - Provides balance and transaction history."""

from typing import Any, Optional

from agent_framework import Agent

from bank_agents._types import ChatClientProtocol


def get_agent(client: ChatClientProtocol, tools) -> Agent:
    """
    Create InquiryAgent with MCP tools.

    Args:
        client: Chat client
        tools: MCP tools (single MCPStreamableHTTPTool or list)
    """
    instructions = (
        "CRITICAL: You MUST respond ONLY in English. Never use Thai or any other language.\n"
        "English only. English only. English only.\n\n"
        "You are InquiryAgent. You handle balance and transaction history requests.\n\n"
        "ALWAYS read the user's request carefully and call the appropriate tool:\n"
        "- If user asks about balance/money/how much → call check_balance()\n"
        "- If user asks about history/transactions/activity → call view_history()\n"
        "- If user asks about accounts/list accounts → call list_my_accounts()\n\n"
        "Always call a tool first, then report the results clearly.\n"
        "Remember: Respond in English only."
    )
    return client.as_agent(
        name="InquiryAgent",
        instructions=instructions,
        tools=tools,
    )
