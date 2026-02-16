"""
42 Bank Agents - A2A/MCP Compliant Multi-Agent Banking System.

This module provides a modular multi-agent architecture with support for:
- Microsoft Agent Framework Handoff orchestration
- A2A Protocol (Agent-to-Agent) for standardized inter-agent communication
- MCP (Model Context Protocol) for tool exposure
"""

from typing import Protocol, Any, Optional, Sequence

from agent_framework import Agent


class ChatClientProtocol(Protocol):
    """Protocol for chat clients that can create agents."""

    def as_agent(
        self,
        *,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[Sequence[Any]] = None,
    ) -> Agent: ...


AGENT_CONFIGS = {
    "triage": {
        "name": "TriageAgent",
        "instructions": (
            "You are the 42 Bank Receptionist. YOUR ONLY JOB IS ROUTING. "
            "1. IF query is about MONEY MOVEMENT (send, transfer, request, pay, approve) -> CALL 'handoff_to_TransactionAgent()'. "
            "2. IF query is about STATUS (balance, history, accounts) -> CALL 'handoff_to_InquiryAgent()'. "
            "3. IF query is about PRODUCTS (loans, cards, mortgages, advice) -> CALL 'handoff_to_AdvisorAgent()'. "
            "4. IF query is general help or oversight -> CALL 'handoff_to_BankManager()'. "
            "NEVER try to answer yourself. NEVER ask for more info. ALWAYS use a handoff tool immediately."
        ),
        "tools": None,
    },
    "transaction": {
        "name": "TransactionAgent",
        "instructions": (
            "You are the Transaction Specialist. "
            "1. REVIEW conversation history to see what user needs to move. "
            "2. USE 'send_money', 'request_money', or 'approve_payment'. "
            "3. REPORT the result and STOP. "
            "4. IF user wants balance or history -> CALL 'handoff_to_TriageAgent()'."
        ),
        "tools": [
            "send_money",
            "request_money",
            "approve_payment",
            "list_pending_requests",
        ],
    },
    "inquiry": {
        "name": "InquiryAgent",
        "instructions": (
            "You are the Inquiry Specialist. "
            "1. REVIEW conversation history to see what user needs. "
            "2. USE 'check_balance' for balance, 'view_history' for history, or 'list_my_accounts'. "
            "3. REPORT the result and STOP. "
            "4. NEVER ask for account numbers. "
            "5. IF user wants to move money -> CALL 'handoff_to_TriageAgent()'."
        ),
        "tools": ["check_balance", "view_history", "list_my_accounts"],
    },
    "advisor": {
        "name": "AdvisorAgent",
        "instructions": (
            "You are the Financial Advisor. "
            "1. IF user wants products -> CALL 'list_products()'. "
            "2. IF user wants new account -> CALL 'open_new_account(account_type)'. "
            "3. After answering, STOP. DO NOT CHAT. "
            "IF they want balance, history, or to move money -> CALL 'handoff_to_TriageAgent()'."
        ),
        "tools": ["list_products", "open_new_account"],
    },
    "manager": {
        "name": "BankManager",
        "instructions": (
            "You are the Bank Manager. Oversight only. "
            "1. IF user asks high-level questions -> answer clearly and STOP. "
            "2. IF user needs specific actions (balance, transfer) -> CALL 'handoff_to_TriageAgent()'. "
            "DO NOT CHAT. DO NOT ASK FOR INFO."
        ),
        "tools": [
            "check_balance",
            "view_history",
            "list_pending_requests",
            "list_products",
        ],
    },
}

A2A_AGENT_SKILLS = {
    "triage": [
        {
            "id": "route",
            "name": "Route Queries",
            "description": "Route user queries to appropriate banking specialists",
            "tags": ["routing", "triage"],
        }
    ],
    "transaction": [
        {
            "id": "send_money",
            "name": "Send Money",
            "description": "Transfer funds to another user",
            "tags": ["transfer", "payment"],
        },
        {
            "id": "request_money",
            "name": "Request Money",
            "description": "Request payment from another user",
            "tags": ["request", "payment"],
        },
        {
            "id": "approve_payment",
            "name": "Approve Payment",
            "description": "Approve pending payment requests",
            "tags": ["approval", "payment"],
        },
    ],
    "inquiry": [
        {
            "id": "check_balance",
            "name": "Check Balance",
            "description": "View account balance",
            "tags": ["balance", "inquiry"],
        },
        {
            "id": "view_history",
            "name": "View History",
            "description": "View transaction history",
            "tags": ["history", "inquiry"],
        },
    ],
    "advisor": [
        {
            "id": "list_products",
            "name": "List Products",
            "description": "List available bank products",
            "tags": ["products", "advisory"],
        },
        {
            "id": "open_account",
            "name": "Open Account",
            "description": "Open a new bank account",
            "tags": ["account", "onboarding"],
        },
    ],
    "manager": [
        {
            "id": "oversight",
            "name": "Bank Oversight",
            "description": "Handle escalations and complex queries",
            "tags": ["oversight", "escalation"],
        }
    ],
}

A2A_AGENT_DESCRIPTIONS = {
    "triage": "42 Bank Receptionist - Routes queries to appropriate banking specialists",
    "transaction": "Transaction Specialist - Handles money transfers and payment requests",
    "inquiry": "Account Inquiry Specialist - Provides balance and transaction history",
    "advisor": "Financial Advisor - Assists with products and account opening",
    "manager": "Bank Manager - Handles escalations and oversight",
}


def get_agent_tools(tools, banking_tools):
    """Resolve tool names to actual tool functions."""
    if tools is None:
        return None

    tool_map = {
        "check_balance": banking_tools.check_balance,
        "view_history": banking_tools.view_history,
        "list_my_accounts": banking_tools.list_my_accounts,
        "send_money": banking_tools.send_money,
        "request_money": banking_tools.request_money,
        "list_pending_requests": banking_tools.list_pending_requests,
        "approve_payment": banking_tools.approve_payment,
        "list_products": banking_tools.list_products,
        "open_new_account": banking_tools.open_new_account,
    }

    return [tool_map[t] for t in tools if t in tool_map]


from bank_agents.triage import get_agent as get_triage_agent
from bank_agents.transaction import get_agent as get_transaction_agent
from bank_agents.inquiry import get_agent as get_inquiry_agent
from bank_agents.advisor import get_agent as get_advisor_agent
from bank_agents.manager import get_agent as get_manager_agent


__all__ = [
    "ChatClientProtocol",
    "AGENT_CONFIGS",
    "A2A_AGENT_SKILLS",
    "A2A_AGENT_DESCRIPTIONS",
    "get_agent_tools",
    "get_triage_agent",
    "get_transaction_agent",
    "get_inquiry_agent",
    "get_advisor_agent",
    "get_manager_agent",
]
