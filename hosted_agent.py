"""
42 Bank Hosted Agent - Entry point for Azure AI Foundry deployment.

Uses the hosting adapter (azure-ai-agentserver-agentframework) to expose
the banking agent as a REST API compatible with Foundry Responses API.

Usage:
    # Local testing (starts server on localhost:8088)
    uv run hosted_agent.py

    # Build container for Foundry deployment (must be linux/amd64)
    docker buildx build --platform linux/amd64 -t 42-bank-agent .
"""

import os
from dotenv import load_dotenv

load_dotenv()

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from azure.ai.agentserver.agentframework import from_agent_framework
from azure.identity import DefaultAzureCredential

from tools import BankingTools
from ledger import LedgerEngine
from identity import IdentityManager


def create_banking_agent() -> ChatAgent:
    """Create the banking agent with all tools."""

    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model_deployment_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "Phi-4-mini")
    username = os.getenv("BANK_USER", "alice")

    if not project_endpoint:
        raise ValueError("AZURE_AI_PROJECT_ENDPOINT required")

    ident = IdentityManager()
    ledger = LedgerEngine()
    token = ident.get_token(username)

    if not token:
        raise ValueError(f"User {username} not found. Run bootstrap.py first.")

    pk = ident.get_public_key(username)
    if pk:
        ledger.register_user(token, username, pk.hex())

    tools = BankingTools(ledger, ident, username, token)

    return ChatAgent(
        chat_client=AzureAIAgentClient(
            project_endpoint=project_endpoint,
            model_deployment_name=model_deployment_name,
            credential=DefaultAzureCredential(),
        ),
        instructions=(
            "You are the 42 Bank Assistant, a helpful banking agent. "
            "You can check balances, view history, send money, request payments, "
            "approve requests, list products, and open new accounts. "
            "Always be helpful and clear in your responses."
        ),
        tools=[
            tools.check_balance,
            tools.view_history,
            tools.list_my_accounts,
            tools.send_money,
            tools.request_money,
            tools.list_pending_requests,
            tools.approve_payment,
            tools.list_products,
            tools.open_new_account,
        ],
    )


agent = create_banking_agent()


if __name__ == "__main__":
    from_agent_framework(agent).run()
