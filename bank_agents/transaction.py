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
            "Review the conversation history to see what user needs to move. "
            "1. TO SEND -> CALL 'send_money()'. "
            "2. TO REQUEST -> CALL 'request_money()'. "
            "3. TO APPROVE -> CALL 'approve_payment()'. "
            "4. TO SEE PENDING -> CALL 'list_pending_requests()'. "
            "PRO-ACTIVELY call the tool based on intent in history. "
            "After tool call, report result and STOP."
        ),
        tools=[
            tools.send_money,
            tools.request_money,
            tools.approve_payment,
            tools.list_pending_requests,
        ],
    )
