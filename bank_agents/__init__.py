"""
42 Bank Agents - A2A/MCP Compliant Multi-Agent Banking System.

This module provides a modular multi-agent architecture with support for:
- A2A Protocol (Agent-to-Agent) for standardized inter-agent communication
- MCP (Model Context Protocol) for tool exposure
"""

from bank_agents._types import ChatClientProtocol

from bank_agents.triage import get_agent as get_triage_agent
from bank_agents.transaction import get_agent as get_transaction_agent
from bank_agents.inquiry import get_agent as get_inquiry_agent
from bank_agents.advisor import get_agent as get_advisor_agent
from bank_agents.manager import get_agent as get_manager_agent


__all__ = [
    "ChatClientProtocol",
    "get_triage_agent",
    "get_transaction_agent",
    "get_inquiry_agent",
    "get_advisor_agent",
    "get_manager_agent",
]
