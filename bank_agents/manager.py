"""Manager Agent - Handles escalations and oversight."""

from typing import Protocol, Any, Optional, Sequence

from agent_framework import Agent
from tools import BankingTools

INSTRUCTIONS = (
    "Bank Manager. Oversight only. "
    "1. Answer high-level questions clearly and STOP. "
    "2. For specific actions -> handoff_to_TriageAgent()."
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
        name="BankManager",
        instructions=INSTRUCTIONS,
        tools=[
            tools.check_balance,
            tools.view_history,
            tools.list_pending_requests,
            tools.list_products,
        ],
    )
