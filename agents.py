import os
import re
import subprocess
from dotenv import load_dotenv
from typing import Optional, Protocol, Any, Sequence
from agent_framework import Agent, resolve_agent_id, InMemoryCheckpointStorage
from agent_framework.openai import OpenAIChatClient
from agent_framework.azure import AzureAIClient
from agent_framework.orchestrations import HandoffBuilder
from agent_framework._workflows._workflow import Workflow
from azure.identity.aio import DefaultAzureCredential

from bank_agents import triage, transaction, inquiry, advisor, manager
from tools import BankingTools
from ledger import LedgerEngine
from identity import IdentityManager

load_dotenv()


def create_chat_client(mode: str = "local", model_name: Optional[str] = None) -> Any:
    """Create a chat client for local or hosted mode."""
    if mode == "local":
        endpoint = get_foundry_local_endpoint()
        model_id = model_name or os.getenv("MODEL_NAME", "Phi-4-mini-instruct-generic-gpu:5")
        return OpenAIChatClient(
            model_id=model_id, api_key="local-dev-key", base_url=endpoint
        )
    else:
        project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        if not project_endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT required for hosted mode")
        model_deployment_name = model_name or os.getenv(
            "AZURE_AI_MODEL_DEPLOYMENT_NAME", "Phi-4-mini"
        )
        return AzureAIClient(
            project_endpoint=project_endpoint,
            model_deployment_name=model_deployment_name,
            credential=DefaultAzureCredential(),
        )


class ChatClientProtocol(Protocol):
    def as_agent(
        self,
        *,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[Sequence[Any]] = None,
    ) -> Agent: ...


def get_foundry_local_endpoint() -> str:
    """Detect Foundry Local endpoint from service status."""
    try:
        result = subprocess.run(
            ["foundry", "service", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        match = re.search(r"http://127\.0\.0\.1:(\d+)", result.stdout + result.stderr)
        if match:
            return f"http://127.0.0.1:{match.group(1)}/v1"
    except Exception:
        pass

    raise RuntimeError(
        "Foundry Local not running. Start with: foundry model run Phi-4-mini-instruct-generic-gpu:5"
    )


def create_banking_workflow(
    ledger: LedgerEngine,
    identity: IdentityManager,
    username: str,
    session_token: str,
    model_name: Optional[str] = None,
    mode: str = "local",
) -> Workflow:
    """Creates a robust A2A banking workflow."""
    client = create_chat_client(mode=mode, model_name=model_name)
    tools = BankingTools(ledger, identity, username, session_token)

    t_agent = triage.get_agent(client)
    tx_agent = transaction.get_agent(client, tools)
    iq_agent = inquiry.get_agent(client, tools)
    ad_agent = advisor.get_agent(client, tools)
    mg_agent = manager.get_agent(client, tools)

    return (
        HandoffBuilder(
            name="BankingWorkflow",
            participants=[t_agent, tx_agent, iq_agent, ad_agent, mg_agent],
            checkpoint_storage=InMemoryCheckpointStorage(),
        )
        .with_start_agent(t_agent)
        .add_handoff(t_agent, [tx_agent, iq_agent, ad_agent, mg_agent])
        .add_handoff(tx_agent, [t_agent])
        .add_handoff(iq_agent, [t_agent])
        .add_handoff(ad_agent, [t_agent])
        .add_handoff(mg_agent, [t_agent])
        .with_autonomous_mode(
            turn_limits={
                resolve_agent_id(t_agent): 2,
                resolve_agent_id(tx_agent): 10,
                resolve_agent_id(iq_agent): 10,
                resolve_agent_id(ad_agent): 10,
                resolve_agent_id(mg_agent): 10,
            },
            require_user_confirmation=False,  # No confirmation needed for simple queries
        )
        .build()
    )
