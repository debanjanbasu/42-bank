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
        name="InquiryAgent",
        instructions=(
            "You are the Inquiry Specialist. "
            "1. REVIEW conversation history to see what user needs. "
            "2. USE 'check_balance' for balance, 'view_history' for history, or 'list_my_accounts'. "
            "3. REPORT the result and STOP. "
            "4. NEVER ask for account numbers. "
            "5. IF user wants to move money -> CALL 'handoff_to_TriageAgent()'."
        ),
        tools=[tools.check_balance, tools.view_history, tools.list_my_accounts],
    )
