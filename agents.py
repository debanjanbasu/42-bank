import os
from dotenv import load_dotenv
from typing import Optional, List, Protocol, Any, Sequence
from agent_framework import Agent, resolve_agent_id
from agent_framework.openai import OpenAIChatClient
from agent_framework.azure import AzureAIClient
from agent_framework.orchestrations import HandoffBuilder
from agent_framework._workflows._workflow import Workflow
from azure.identity.aio import DefaultAzureCredential

# Import modular agents
from bank_agents import triage, transaction, inquiry, advisor, manager
from tools import BankingTools
from ledger import LedgerEngine
from identity import IdentityManager

load_dotenv()


class ChatClientProtocol(Protocol):
    def as_agent(
        self,
        *,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[Sequence[Any]] = None,
    ) -> Agent: ...


def create_banking_workflow(
    ledger: LedgerEngine,
    identity: IdentityManager,
    username: str,
    session_token: str,
    model_name: Optional[str] = None,
    mode: str = "local",
) -> Workflow:
    """
    Creates a robust A2A banking workflow.
    """

    client: ChatClientProtocol

    if mode == "local":
        endpoint = os.getenv("FOUNDRY_LOCAL_ENDPOINT", "http://localhost:8080/v1")
        model_id = model_name or os.getenv("MODEL_NAME", "qwen2.5-14b")
        client = OpenAIChatClient(
            model_id=model_id, api_key="local-dev-key", base_url=endpoint
        )  # type: ignore
    else:
        project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        model_deployment_name = model_name or os.getenv(
            "AZURE_AI_MODEL_DEPLOYMENT_NAME"
        )
        if not project_endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT required.")
        client = AzureAIClient(
            project_endpoint=project_endpoint,
            model_deployment_name=model_deployment_name,
            credential=DefaultAzureCredential(),
        )  # type: ignore

    tools = BankingTools(ledger, identity, username, session_token)

    # Instantiate modular agents
    t_agent = triage.get_agent(client)
    tx_agent = transaction.get_agent(client, tools)
    iq_agent = inquiry.get_agent(client, tools)
    ad_agent = advisor.get_agent(client, tools)
    mg_agent = manager.get_agent(client, tools)

    # Build A2A graph
    return (
        HandoffBuilder(
            name="BankingWorkflow",
            participants=[t_agent, tx_agent, iq_agent, ad_agent, mg_agent],
        )
        .with_start_agent(t_agent)
        .add_handoff(t_agent, [tx_agent, iq_agent, ad_agent, mg_agent])
        .add_handoff(tx_agent, [t_agent])
        .add_handoff(iq_agent, [t_agent])
        .add_handoff(ad_agent, [t_agent])
        .add_handoff(mg_agent, [t_agent])
        # Disable autonomous mode for Triage to prevent loops on 14b
        .with_autonomous_mode(
            turn_limits={
                resolve_agent_id(t_agent): 10,
                resolve_agent_id(tx_agent): 10,
                resolve_agent_id(iq_agent): 10,
                resolve_agent_id(ad_agent): 10,
                resolve_agent_id(mg_agent): 10,
            }
        )
        .build()
    )
