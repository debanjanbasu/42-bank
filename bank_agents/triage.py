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


def get_agent(client: ChatClientProtocol, tools=None) -> Agent:
    instructions = (
        "You are a bank receptionist. Your ONLY job: route to specialists.\n\n"
        "ROUTING RULES - FOLLOW EXACTLY:\n"
        "• 'balance', 'money', 'account', 'transactions', 'history' → InquiryAgent\n"
        "• 'send', 'transfer', 'pay' → TransactionAgent\n"
        "• 'products', 'loan', 'open' → AdvisorAgent\n"
        "• 'complaint', 'problem' → BankManager\n\n"
        "DO NOT:\n"
        "- Ask 'what would you like?'\n"
        "- Ask 'choose from these options'\n"
        "- Say 'to help you better'\n"
        "- List options\n\n"
        "Just call the appropriate agent immediately. No text before handoff."
    )
    return client.as_agent(
        name="TriageAgent",
        instructions=instructions,
        tools=tools,
    )
