"""Advisor Agent - Assists with bank products and account opening."""

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
    instructions = (
        "You are a financial advisor. User is authenticated. "
        "For product inquiries: IMMEDIATELY call list_products(). "
        "For opening accounts: IMMEDIATELY call open_new_account(account_type). "
        "DO NOT provide generic advice without calling tools first. "
        "Just call the appropriate tool immediately."
    )
    return client.as_agent(
        name="AdvisorAgent",
        instructions=instructions,
        tools=tools,
    )
