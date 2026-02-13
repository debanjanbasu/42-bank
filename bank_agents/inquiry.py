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
            "Review the conversation history to see what the user needs. "
            "1. IF user wants balance -> CALL 'check_balance(account_type)'. "
            "2. IF user wants history -> CALL 'view_history(account_type)'. "
            "3. IF user wants account list -> CALL 'list_my_accounts()'. "
            "PRO-ACTIVELY call the correct tool based on user intent in history. "
            "After calling, report the result and STOP."
        ),
        tools=[tools.check_balance, tools.view_history, tools.list_my_accounts],
    )
