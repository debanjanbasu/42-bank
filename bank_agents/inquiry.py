"""Inquiry Agent - Provides balance and transaction history."""

from typing import Protocol, Any, Optional, Sequence

from agent_framework import Agent


class ChatClientProtocol(Protocol):
    def as_agent(
        self,
        *,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[Sequence[Any]] = None,
    ) -> Agent: ...


def get_agent(client: ChatClientProtocol, tools) -> Agent:
    """
    Create InquiryAgent with MCP tools.
    
    Args:
        client: Chat client
        tools: MCP tools (single MCPStreamableHTTPTool or list)
    """
    instructions = (
        "You are an inquiry specialist. User is authenticated.\n\n"
        "RULES - FOLLOW EXACTLY:\n"
        "1. For 'balance' or 'what's my balance': call check_balance() - NO QUESTIONS\n"
        "2. For 'transactions' or 'history': call view_history() - NO QUESTIONS\n"
        "3. For 'accounts' or 'list accounts': call list_my_accounts() - NO QUESTIONS\n\n"
        "NEVER say: 'could you please', 'what would you like', 'specify', 'choose from'\n"
        "NEVER ask: which account, what information, what option\n\n"
        "CORRECT: User says 'show transactions' → You call view_history() → Return results\n"
        "WRONG: User says 'show transactions' → You ask 'which option do you prefer?'\n\n"
        "Call the tool FIRST. Talk AFTER you have results."
    )
    return client.as_agent(
        name="InquiryAgent",
        instructions=instructions,
        tools=tools,
    )
