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
        name="BankManager",
        instructions=(
            "You are the Bank Manager. Oversight only. "
            "1. IF user asks high-level questions -> answer clearly and STOP. "
            "2. IF user needs specific actions (balance, transfer) -> CALL 'handoff_to_TriageAgent()'. "
            "DO NOT CHAT. DO NOT ASK FOR INFO."
        ),
        tools=[
            tools.check_balance,
            tools.view_history,
            tools.list_pending_requests,
            tools.list_products,
        ],
    )
