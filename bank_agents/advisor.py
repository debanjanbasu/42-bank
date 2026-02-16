"""Advisor Agent - Assists with bank products and account opening."""

from typing import Protocol, Any, Optional, Sequence

from agent_framework import Agent
from tools import BankingTools

INSTRUCTIONS = (
    "Financial Advisor. "
    "1. Use list_products or open_new_account. "
    "2. Report result and STOP. "
    "3. For balance/transfers -> handoff_to_TriageAgent()."
)


class ChatClientProtocol(Protocol):
    def as_agent(
        self,
        *,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[Sequence[Any]] = None,
    ) -> Agent: ...


def get_agent(client: ChatClientProtocol, tools: BankingTools) -> Agent:
    return client.as_agent(
        name="AdvisorAgent",
        instructions=INSTRUCTIONS,
        tools=[tools.list_products, tools.open_new_account],
    )
