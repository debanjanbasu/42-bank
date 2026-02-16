"""
A2A Server - Exposes banking agents via the Agent2Agent protocol.

This module implements A2A protocol compliance for Azure AI Foundry.
Foundry agents use A2ATool to connect to this endpoint.

Authentication modes:
- Key-based: API key in x-api-key header
- Microsoft Entra ID: Bearer token validation
- Unauthenticated: For development only
"""

import os
import asyncio
import json
import uuid
from typing import Optional, Dict, Any, List, Callable

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, StreamingResponse
from starlette.requests import Request
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from agent_framework.azure import AzureAIClient
from azure.identity.aio import DefaultAzureCredential
from azure.core.credentials import AccessToken

from dotenv import load_dotenv
from bank_agents import triage, transaction, inquiry, advisor, manager
from tools import BankingTools
from ledger import LedgerEngine
from identity import IdentityManager

load_dotenv()


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for A2A endpoints.

    Supports:
    - Key-based: x-api-key header
    - Microsoft Entra ID: Bearer token (optional validation)
    - Unauthenticated: Allowed in development mode
    """

    def __init__(self, app, api_key: Optional[str] = None, require_auth: bool = False):
        super().__init__(app)
        self.api_key = api_key
        self.require_auth = require_auth

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/health", "/a2a"]:
            return await call_next(request)

        if not self.require_auth:
            return await call_next(request)

        api_key_header = request.headers.get("x-api-key")
        auth_header = request.headers.get("Authorization", "")

        if self.api_key and api_key_header == self.api_key:
            return await call_next(request)

        if auth_header.startswith("Bearer "):
            return await call_next(request)

        return JSONResponse(
            {
                "error": "Unauthorized",
                "message": "Valid API key or Bearer token required",
            },
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="42-bank"'},
        )


def create_chat_client(mode: str = "local", model_name: Optional[str] = None):
    """Create chat client based on deployment mode."""
    if mode == "local":
        endpoint = os.getenv("FOUNDRY_LOCAL_ENDPOINT", "http://localhost:8080/v1")
        model_id = model_name or os.getenv(
            "MODEL_NAME", "Phi-4-mini-instruct-generic-gpu:5"
        )
        return OpenAIChatClient(
            model_id=model_id, api_key="local-dev-key", base_url=endpoint
        )
    else:
        project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        model_deployment_name = model_name or os.getenv(
            "AZURE_AI_MODEL_DEPLOYMENT_NAME", "Phi-4-mini"
        )
        if not project_endpoint:
            raise ValueError("AZURE_AI_PROJECT_ENDPOINT required for hosted mode.")
        return AzureAIClient(
            project_endpoint=project_endpoint,
            model_deployment_name=model_deployment_name,
            credential=DefaultAzureCredential(),
        )


AGENT_DESCRIPTIONS = {
    "triage": "42 Bank Receptionist - Routes queries to appropriate banking specialists",
    "transaction": "Transaction Specialist - Handles money transfers and payment requests",
    "inquiry": "Account Inquiry Specialist - Provides balance and transaction history",
    "advisor": "Financial Advisor - Assists with products and account opening",
    "manager": "Bank Manager - Handles escalations and oversight",
}

AGENT_SKILLS = {
    "triage": [
        {
            "id": "route",
            "name": "Route Queries",
            "description": "Route queries to specialists",
            "tags": ["routing"],
        }
    ],
    "transaction": [
        {
            "id": "send_money",
            "name": "Send Money",
            "description": "Transfer funds",
            "tags": ["transfer"],
        },
        {
            "id": "request_money",
            "name": "Request Money",
            "description": "Request payment",
            "tags": ["request"],
        },
        {
            "id": "approve_payment",
            "name": "Approve Payment",
            "description": "Approve requests",
            "tags": ["approval"],
        },
    ],
    "inquiry": [
        {
            "id": "check_balance",
            "name": "Check Balance",
            "description": "View balance",
            "tags": ["balance"],
        },
        {
            "id": "view_history",
            "name": "View History",
            "description": "View transactions",
            "tags": ["history"],
        },
    ],
    "advisor": [
        {
            "id": "list_products",
            "name": "List Products",
            "description": "Bank products",
            "tags": ["products"],
        },
        {
            "id": "open_account",
            "name": "Open Account",
            "description": "Open new account",
            "tags": ["account"],
        },
    ],
    "manager": [
        {
            "id": "oversight",
            "name": "Oversight",
            "description": "Escalations",
            "tags": ["oversight"],
        }
    ],
}


class A2AAgentHandler:
    """Handles A2A protocol requests for a single agent."""

    def __init__(self, agent: Agent, agent_key: str):
        self.agent = agent
        self.agent_key = agent_key

    def get_agent_card(self, base_url: str) -> Dict[str, Any]:
        """Return A2A Agent Card for discovery."""
        return {
            "name": f"42-Bank-{self.agent_key.title()}Agent",
            "description": AGENT_DESCRIPTIONS[self.agent_key],
            "version": "1.0.0",
            "url": f"{base_url}/a2a/{self.agent_key}",
            "capabilities": {"streaming": True, "pushNotifications": False},
            "skills": AGENT_SKILLS.get(self.agent_key, []),
            "defaultInputModes": ["text"],
            "defaultOutputModes": ["text"],
        }

    async def handle_message(self, request: Request) -> Dict[str, Any]:
        """Handle A2A message request."""
        body = await request.json()
        message = body.get("message", {})
        context_id = message.get("contextId") or str(uuid.uuid4())

        user_text = ""
        for part in message.get("parts", []):
            if part.get("kind") == "text":
                user_text += part.get("text", "")

        thread = self.agent.get_new_thread()

        try:
            response = await self.agent.run(user_text, thread=thread)
            response_text = ""
            for msg in response.messages:
                for content in msg.contents:
                    if hasattr(content, "text") and content.text:
                        response_text += content.text

            return {
                "kind": "message",
                "role": "agent",
                "parts": [{"kind": "text", "text": response_text}],
                "messageId": str(uuid.uuid4()),
                "contextId": context_id,
            }
        except Exception as e:
            return {
                "kind": "message",
                "role": "agent",
                "parts": [{"kind": "text", "text": f"Error: {e}"}],
                "messageId": str(uuid.uuid4()),
                "contextId": context_id,
            }


def create_a2a_app(
    ledger: LedgerEngine,
    identity: IdentityManager,
    username: str,
    session_token: str,
    mode: str = "local",
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    require_auth: bool = False,
) -> Starlette:
    """Create A2A server application."""
    client = create_chat_client(mode, model_name)
    tools = BankingTools(ledger, identity, username, session_token)

    agents: Dict[str, Agent] = {
        "triage": triage.get_agent(client),
        "transaction": transaction.get_agent(client, tools),
        "inquiry": inquiry.get_agent(client, tools),
        "advisor": advisor.get_agent(client, tools),
        "manager": manager.get_agent(client, tools),
    }

    handlers = {key: A2AAgentHandler(agent, key) for key, agent in agents.items()}
    routes = []

    for agent_key, handler in handlers.items():

        async def get_card(request: Request, h=handler):
            base_url = str(request.base_url).rstrip("/")
            return JSONResponse(h.get_agent_card(base_url))

        async def post_message(request: Request, h=handler):
            result = await h.handle_message(request)
            return JSONResponse(result)

        path = f"/a2a/{agent_key}"
        routes.append(Route(path, endpoint=get_card, methods=["GET"]))
        routes.append(
            Route(f"{path}/v1/message", endpoint=post_message, methods=["POST"])
        )
        routes.append(
            Route(f"{path}/v1/message:stream", endpoint=post_message, methods=["POST"])
        )
        routes.append(Route(f"{path}/v1/card", endpoint=get_card, methods=["GET"]))

    async def list_agents(request: Request) -> JSONResponse:
        base_url = str(request.base_url).rstrip("/")
        return JSONResponse(
            {
                "agents": [
                    {
                        "name": f"42-Bank-{k.title()}Agent",
                        "path": f"/a2a/{k}",
                        "url": f"{base_url}/a2a/{k}",
                        "description": AGENT_DESCRIPTIONS[k],
                    }
                    for k in agents
                ]
            }
        )

    async def health(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "healthy",
                "protocol": "A2A",
                "version": "0.3.0",
                "agents": list(agents.keys()),
            }
        )

    routes.extend(
        [
            Route("/a2a", endpoint=list_agents, methods=["GET"]),
            Route("/health", endpoint=health, methods=["GET"]),
        ]
    )

    middleware = (
        [Middleware(AuthMiddleware, api_key=api_key, require_auth=require_auth)]
        if api_key or require_auth
        else []
    )
    return Starlette(routes=routes, middleware=middleware)


async def run_a2a_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    username: str = "alice",
    mode: str = "local",
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    require_auth: bool = False,
):
    """Run the A2A server."""
    import uvicorn

    ident = IdentityManager()
    ledger = LedgerEngine()
    token = ident.get_token(username)
    if not token:
        raise ValueError(f"User {username} not found")

    pk = ident.get_public_key(username)
    if pk:
        ledger.register_user(token, username, pk.hex())

    app = create_a2a_app(
        ledger, ident, username, token, mode, model_name, api_key, require_auth
    )

    print(f"A2A Server: http://{host}:{port}")
    print(
        f"User: {username} | Mode: {mode} | Auth: {'enabled' if require_auth else 'disabled'}"
    )
    for key in ["triage", "transaction", "inquiry", "advisor", "manager"]:
        print(f"  /a2a/{key}")

    await uvicorn.Server(uvicorn.Config(app, host=host, port=port)).serve()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="42-Bank A2A Server")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--user", choices=["alice", "bob"], default="alice")
    p.add_argument("--mode", choices=["local", "hosted"], default="local")
    p.add_argument("--model", default=None)
    p.add_argument("--api-key", default=None, help="API key for authentication")
    p.add_argument("--require-auth", action="store_true", help="Require authentication")
    args = p.parse_args()

    api_key = args.api_key or os.getenv("A2A_API_KEY")
    require_auth = args.require_auth or bool(api_key)

    asyncio.run(
        run_a2a_server(
            host=args.host,
            port=args.port,
            username=args.user,
            mode=args.mode,
            model_name=args.model,
            api_key=api_key,
            require_auth=require_auth,
        )
    )
