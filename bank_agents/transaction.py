"""Transaction Agent - Handles money transfers and payment requests."""

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


def get_agent(client: ChatClientProtocol, tools) -> Agent:
    instructions = (
        "You are a transaction specialist. User is authenticated.\n\n"
        "RULES - FOLLOW EXACTLY:\n"
        "1. For 'send $X to Y': call send_money(to=Y, amount=X, note='') - NO QUESTIONS\n"
        "2. For 'request $X from Y': call request_money(from_user=Y, amount=X, note='') - NO QUESTIONS\n"
        "3. For 'pending' or 'requests': call list_pending_requests() - NO QUESTIONS\n"
        "4. For 'approve request X': call approve_payment(request_id=X) - NO QUESTIONS\n\n"
        "NEVER ask for:\n"
        "- Account numbers (we only have checking)\n"
        "- Confirmation before calling\n"
        "- Additional details\n\n"
        "Extract username and amount from message. Call tool FIRST. Talk AFTER."
    )
    return client.as_agent(
        name="TransactionAgent",
        instructions=instructions,
        tools=tools,
    )
