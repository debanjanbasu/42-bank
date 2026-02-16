"""Triage Agent - Routes user queries to appropriate banking specialists."""

from typing import Protocol, Any, Optional, Sequence

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
            "1. MONEY MOVEMENT (send, transfer, request, pay, approve) -> handoff_to_TransactionAgent(). "
            "2. STATUS (balance, history, accounts) -> handoff_to_InquiryAgent(). "
            "3. PRODUCTS (loans, cards, mortgages) -> handoff_to_AdvisorAgent(). "
            "4. General help or oversight -> handoff_to_BankManager(). "
            "NEVER answer yourself. ALWAYS use a handoff tool immediately."
        ),
    )
