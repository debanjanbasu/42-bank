"""Triage Agent - Routes user queries to appropriate banking specialists."""

from typing import Any, Optional

from agent_framework import Agent

from bank_agents._types import ChatClientProtocol


def get_agent(client: ChatClientProtocol, tools=None) -> Agent:
    instructions = (
        "You are TriageAgent. Analyze the user's request and respond with ONLY the target agent name.\n\n"
        "LANGUAGE: Always use ENGLISH.\n\n"
        "ROUTING RULES:\n"
        "- balance/account/money/history → InquiryAgent\n"
        "- send/transfer/pay/request money → TransactionAgent\n"
        "- product/loan/card/open account → AdvisorAgent\n"
        "- problem/complaint/escalate → BankManager\n\n"
        "RESPONSE FORMAT: Reply with ONLY the agent name, nothing else.\n\n"
        "Examples:\n"
        "User: 'What's my balance?'\n"
        "You: InquiryAgent\n\n"
        "User: 'Send $50 to Bob'\n"
        "You: TransactionAgent\n\n"
        "User: 'I want a loan'\n"
        "You: AdvisorAgent\n\n"
        "User: 'This is unacceptable!'\n"
        "You: BankManager"
    )
    return client.as_agent(
        name="TriageAgent",
        instructions=instructions,
        tools=tools,
    )
