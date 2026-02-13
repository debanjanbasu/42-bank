from typing import Protocol, List, Any, Optional, Sequence
from agent_framework import Agent


class ChatClientProtocol(Protocol):
    def as_agent(
        self,
        *,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[Sequence[Any]] = None,
    ) -> Agent: ...


def get_agent(client: ChatClientProtocol) -> Agent:
    return client.as_agent(
        name="TriageAgent",
        instructions=(
            "You are a routing tool. "
            "IF user wants balance/history/accounts -> CALL 'handoff_to_InquiryAgent'. "
            "IF user wants move/send/request/approve -> CALL 'handoff_to_TransactionAgent'. "
            "ONLY call tools. NO CHAT."
        ),
    )
