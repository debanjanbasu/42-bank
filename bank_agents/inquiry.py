"""Inquiry Agent - Provides balance and transaction history."""

from typing import Protocol, Any, Optional, Sequence

from agent_framework import Agent
from tools import BankingTools


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
        name="InquiryAgent",
        instructions=(
            "Inquiry Specialist. "
            "1. Use check_balance, view_history, or list_my_accounts. "
            "2. Report result and STOP. "
            "3. For money transfers -> handoff_to_TriageAgent()."
        ),
        tools=[tools.check_balance, tools.view_history, tools.list_my_accounts],
    )
