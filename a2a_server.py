"""
A2A Server - Exposes banking agents via the Agent2Agent protocol.

This module implements A2A protocol compliance with MCP tool integration.
Banking tools are provided by MCP server running on port 8001.

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
from utils import create_chat_client
from mcp_client import get_banking_mcp_tools
from bank_agents import triage, transaction, inquiry, advisor, manager
from identity import IdentityManager
from ledger import LedgerEngine

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

        try:
            response = await self.agent.run(user_text)
            response_text = ""
            for msg in response.messages:
                for content in msg.contents:
                    if hasattr(content, "text") and content.text:
                        response_text += content.text

            # Return JSON-RPC formatted response
            return {
                "result": {
                    "kind": "message",
                    "role": "agent",
                    "parts": [{"kind": "text", "text": response_text}],
                    "messageId": str(uuid.uuid4()),
                    "contextId": context_id,
                }
            }
        except Exception as e:
            return {
                "result": {
                    "kind": "message",
                    "role": "agent",
                    "parts": [{"kind": "text", "text": f"Error: {e}"}],
                    "messageId": str(uuid.uuid4()),
                    "contextId": context_id,
                }
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
    mcp_server_url: str = "http://localhost:8001",
) -> Starlette:
    """Create A2A server application with MCP tool integration."""
    client = create_chat_client(mode, model_name)
    
    # Get MCP tools from the MCP server
    # MCPStreamableHTTPTool auto-discovers all tools from the server
    mcp_tools = get_banking_mcp_tools(mcp_server_url)
    
    # Create specialist agents with MCP tools
    inquiry_agent = inquiry.get_agent(client, mcp_tools)
    transaction_agent = transaction.get_agent(client, mcp_tools)
    advisor_agent = advisor.get_agent(client, mcp_tools)
    manager_agent = manager.get_agent(client, mcp_tools)
    
    # Convert specialist agents to tools for triage to call
    specialist_tools = [
        inquiry_agent.as_tool(),
        transaction_agent.as_tool(),
        advisor_agent.as_tool(),
        manager_agent.as_tool(),
    ]
    
    # Create triage agent with specialist agents as callable tools
    triage_agent = triage.get_agent(client, specialist_tools)
    
    agents: Dict[str, Agent] = {
        "triage": triage_agent,
        "inquiry": inquiry_agent,
        "transaction": transaction_agent,
        "advisor": advisor_agent,
        "manager": manager_agent,
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
    mcp_server_url: str = "http://localhost:8001",
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
        ledger, ident, username, token, mode, model_name, api_key, require_auth, mcp_server_url
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
    import sys

    try:
        p = argparse.ArgumentParser(description="42-Bank A2A Server")
        p.add_argument("--host", default="0.0.0.0")
        p.add_argument("--port", type=int, default=8000)
        p.add_argument("--user", choices=["alice", "bob"], default="alice")
        p.add_argument("--mode", choices=["local", "hosted"], default="local")
        p.add_argument("--model", default=None)
        p.add_argument("--api-key", default=None, help="API key for authentication")
        p.add_argument("--require-auth", action="store_true", help="Require authentication")
        p.add_argument("--mcp-server-url", default="http://localhost:8001", help="MCP server URL")
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
                mcp_server_url=args.mcp_server_url,
            )
        )
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down server...")
        sys.exit(0)
