"""Transaction Agent - Handles money transfers and payment requests."""

from typing import Protocol, Any, Optional, Sequence

from agent_framework import Agent
from tools import BankingTools

INSTRUCTIONS = (
    "Transaction Specialist. "
    "1. Use send_money, request_money, or approve_payment. "
    "2. Report result and STOP. "
    "3. For balance/history -> handoff_to_TriageAgent()."
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
        name="TransactionAgent",
        instructions=INSTRUCTIONS,
        tools=[
            tools.send_money,
            tools.request_money,
            tools.approve_payment,
            tools.list_pending_requests,
        ],
    )
