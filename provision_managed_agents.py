import os
import asyncio
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from bank_agents import triage, transaction, inquiry, advisor, manager
from tools import BankingTools
from ledger import LedgerEngine
from identity import IdentityManager

load_dotenv()


def provision_managed_agents():
    """
    Provisions managed agents in Azure AI Agent Service.
    This replaces the A2A/MCP server approach with a simpler managed one.
    """
    project_connection_string = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
    if not project_connection_string:
        print("Error: AZURE_AI_PROJECT_CONNECTION_STRING not set in .env")
        return

    model_deployment_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "Phi-4-mini")

    # Mock data for tool registration
    ident, ledger = IdentityManager(), LedgerEngine()
    tools = BankingTools(ledger, ident, "alice", "mock-token")

    credential = DefaultAzureCredential()
    client = AIProjectClient.from_connection_string(
        connection_string=project_connection_string,
        credential=credential,
    )

    with client:
        print(f"Provisioning agents using model: {model_deployment_name}...")

        # 1. Triage Agent
        t_agent = client.agents.create_agent(
            model=model_deployment_name,
            name="TriageAgent",
            instructions=triage.INSTRUCTIONS,
        )
        print(f"Created Triage Agent: {t_agent.id}")

        # 2. Transaction Agent
        tx_agent = client.agents.create_agent(
            model=model_deployment_name,
            name="TransactionAgent",
            instructions=transaction.INSTRUCTIONS,
        )
        print(f"Created Transaction Agent: {tx_agent.id}")

        # 3. Inquiry Agent
        iq_agent = client.agents.create_agent(
            model=model_deployment_name,
            name="InquiryAgent",
            instructions=inquiry.INSTRUCTIONS,
        )
        print(f"Created Inquiry Agent: {iq_agent.id}")

        # 4. Advisor Agent
        ad_agent = client.agents.create_agent(
            model=model_deployment_name,
            name="AdvisorAgent",
            instructions=advisor.INSTRUCTIONS,
        )
        print(f"Created Advisor Agent: {ad_agent.id}")

        # 5. Manager Agent
        mg_agent = client.agents.create_agent(
            model=model_deployment_name,
            name="ManagerAgent",
            instructions=manager.INSTRUCTIONS,
        )
        print(f"Created Manager Agent: {mg_agent.id}")

        print("\nAll agents provisioned successfully!")
        print(
            "Note: In a production environment, you would store these IDs and use them in main.py"
        )


if __name__ == "__main__":
    provision_managed_agents()
