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


class ChatClientProtocol(Protocol):
    def as_agent(
        self,
        *,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[Sequence[Any]] = None,
    ) -> Agent: ...


def get_foundry_local_endpoint() -> str:
    """
    Get Foundry Local endpoint from 'foundry service status' output.
    Returns the endpoint URL or raises an error if not found.
    """
    env_endpoint = os.getenv("FOUNDRY_LOCAL_ENDPOINT")
    if env_endpoint:
        return env_endpoint

    try:
        result = subprocess.run(
            ["foundry", "service", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout + result.stderr
        match = re.search(r"http://[\d.]+:(\d+)", output)
        if match:
            return f"http://127.0.0.1:{match.group(1)}/v1"
    except Exception as e:
        raise RuntimeError(f"Failed to get Foundry Local endpoint: {e}")

    raise RuntimeError(
        "Foundry Local not running. Start with: foundry model run <model>"
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

    client: ChatClientProtocol

    if mode == "local":
        endpoint = get_foundry_local_endpoint()
        model_id = model_name or os.getenv(
            "MODEL_NAME", "Phi-4-mini-instruct-generic-gpu:5"
        )
        client = OpenAIChatClient(
            model_id=model_id, api_key="local-dev-key", base_url=endpoint
        )
    else:
        project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        model_deployment_name = model_name or os.getenv(
            "AZURE_AI_MODEL_DEPLOYMENT_NAME", "Phi-4-mini"
        )
        if not project_endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT required.")
        client = AzureAIClient(
            project_endpoint=project_endpoint,
            model_deployment_name=model_deployment_name,
            credential=DefaultAzureCredential(),
        )

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
                resolve_agent_id(t_agent): 1,
                resolve_agent_id(tx_agent): 5,
                resolve_agent_id(iq_agent): 5,
                resolve_agent_id(ad_agent): 5,
                resolve_agent_id(mg_agent): 5,
            }
        )
        .build()
    )
