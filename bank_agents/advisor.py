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
        name="AdvisorAgent",
        instructions=(
            "You are the Financial Advisor. "
            "1. IF user wants products -> CALL 'list_products()'. "
            "2. IF user wants new account -> CALL 'open_new_account(account_type)'. "
            "3. After answering, STOP. DO NOT CHAT. "
            "IF they want balance, history, or to move money -> CALL 'handoff_to_TriageAgent()'."
        ),
        tools=[tools.list_products, tools.open_new_account],
    )
