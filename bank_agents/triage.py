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
            "You are the 42 Bank Receptionist. YOUR ONLY JOB IS ROUTING. "
            "Follow these logic rules: "
            "1. IF query is about MONEY MOVEMENT (send, transfer, request, pay, approve) -> CALL 'handoff_to_TransactionAgent()'. "
            "2. IF query is about STATUS (balance, history, accounts) -> CALL 'handoff_to_InquiryAgent()'. "
            "3. IF query is about PRODUCTS (loans, cards, mortgages, advice) -> CALL 'handoff_to_AdvisorAgent()'. "
            "4. IF query is general help or oversight -> CALL 'handoff_to_BankManager()'. "
            "NEVER try to answer yourself. NEVER ask for more info. ALWAYS use a handoff tool immediately."
        ),
    )
