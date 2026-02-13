from typing import Protocol, List, Any, Optional, Sequence
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
        name="TransactionAgent",
        instructions=(
            "You are the Transaction Specialist. "
            "1. REVIEW conversation history to see what user needs to move. "
            "2. USE 'send_money', 'request_money', or 'approve_payment'. "
            "3. REPORT the result and STOP. "
            "4. IF user wants balance or history -> CALL 'handoff_to_TriageAgent()'."
        ),
        tools=[
            tools.send_money,
            tools.request_money,
            tools.approve_payment,
            tools.list_pending_requests,
        ],
    )
