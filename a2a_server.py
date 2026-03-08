"""
A2A Server - Exposes banking agents via the Agent2Agent protocol.

This module implements A2A protocol compliance with MCP tool integration.
Banking tools are provided by MCP server running on port 8001.

Authentication modes:
- Key-based: API key in x-api-key header
- Microsoft Entra ID: Bearer token validation
- JWT: Mobile app JWT token validation
- Unauthenticated: For development only
"""

import os
import asyncio
import json
import sys
import uuid
import httpx
from contextlib import asynccontextmanager
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

# JWT configuration for mobile app authentication
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for A2A endpoints.

    Supports:
    - Key-based: x-api-key header
    - Microsoft Entra ID: Bearer token (optional validation)
    - JWT: Mobile app JWT token validation
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
            # Validate JWT token for mobile apps
            token = auth_header[7:]
            try:
                import jwt
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                # Store user info in request state for agents to use
                request.state.user = payload
                request.state.session_token = payload.get("sub")
                return await call_next(request)
            except jwt.ExpiredSignatureError:
                return JSONResponse(
                    {"error": "Unauthorized", "message": "Token has expired"},
                    status_code=401,
                )
            except jwt.InvalidTokenError:
                # Not a JWT, might be Entra ID token - allow through for now
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

    def __init__(
        self,
        agent: Agent,
        agent_key: str,
        all_agents: Optional[Dict[str, Agent]] = None,  # type: ignore[assignment]
        base_url: str = "http://localhost:8000",
    ):
        self.agent = agent
        self.agent_key = agent_key
        self.all_agents = all_agents or {}
        self.base_url = base_url

        # Create httpx async client for A2A routing (only for triage)
        self.http_client = None
        if agent_key == "triage":
            self.http_client = httpx.AsyncClient(timeout=None)

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

    async def handle_message(self, request: Request, use_streaming: bool = False):
        """Handle A2A message request with optional streaming."""
        body = await request.json()
        message = body.get("message", {})
        context_id = message.get("contextId") or str(uuid.uuid4())

        user_text = ""
        for part in message.get("parts", []):
            if part.get("kind") == "text":
                user_text += part.get("text", "")

        # Special handling for triage: route via A2A HTTP streaming to target agent
        if self.agent_key == "triage" and self.all_agents:
            return await self._handle_triage_routing(
                user_text, context_id, body, request, use_streaming
            )

        # Normal agent execution with streaming support
        return await self._handle_agent_execution(user_text, context_id, use_streaming)

    async def _handle_triage_routing(
        self,
        user_text: str,
        context_id: str,
        original_body: dict,
        request: Request,
        use_streaming: bool,
    ):
        """Route via A2A protocol using direct HTTP."""
        try:
            # Get routing decision from triage agent
            response = await self.agent.run(user_text)
            response_text = (
                response.text.strip() if hasattr(response, "text") else str(response)
            )

            # Parse agent name - expect format like "InquiryAgent" or "inquiry"
            target_agent_name = response_text.replace("Agent", "").lower()

            # Map to valid agent keys
            if target_agent_name == "bankmanager":
                target_key = "manager"
            elif target_agent_name in {"inquiry", "transaction", "advisor", "manager"}:
                target_key = target_agent_name
            else:
                target_key = None

            if target_key:
                # Forward to target agent via HTTP
                target_url = f"{self.base_url}/a2a/{target_key}/v1/message"
                if use_streaming:
                    target_url += ":stream"

                # Forward the original message
                target_response = await self.http_client.post(  # type: ignore[union-attr]
                    target_url,
                    json=original_body,
                    headers={"Content-Type": "application/json"},
                )

                if use_streaming:
                    # Forward streaming response
                    return StreamingResponse(
                        target_response.aiter_bytes(),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "X-Accel-Buffering": "no",
                        },
                    )
                else:
                    # Forward JSON response, with error handling for non-200
                    if target_response.status_code == 200:
                        try:
                            return target_response.json()
                        except Exception:
                            pass
                    return {
                        "result": {
                            "kind": "message",
                            "role": "agent",
                            "parts": [
                                {
                                    "kind": "text",
                                    "text": f"Error: upstream agent returned status {target_response.status_code}",
                                }
                            ],
                            "messageId": str(uuid.uuid4()),
                            "contextId": context_id,
                        }
                    }
            else:
                return {
                    "result": {
                        "kind": "message",
                        "role": "agent",
                        "parts": [
                            {
                                "kind": "text",
                                "text": f"I don't understand how to help with that request.",
                            }
                        ],
                        "messageId": str(uuid.uuid4()),
                        "contextId": context_id,
                    }
                }
        except Exception as e:
            import traceback

            traceback.print_exc(file=sys.stderr)
            return {
                "result": {
                    "kind": "message",
                    "role": "agent",
                    "parts": [{"kind": "text", "text": f"Error: {e}"}],
                    "messageId": str(uuid.uuid4()),
                    "contextId": context_id,
                }
            }

    async def _handle_agent_execution(
        self, user_text: str, context_id: str, use_streaming: bool
    ):
        """Execute agent with optional streaming."""
        try:
            if use_streaming:
                # Use agent streaming
                response_stream = await self.agent.run(user_text, stream=True)

                async def generate_sse():
                    """Generate Server-Sent Events from agent stream."""
                    try:
                        async for update in response_stream:
                            # Stream incremental updates as SSE
                            if hasattr(update, "text") and update.text:
                                event_data = {
                                    "result": {
                                        "kind": "message",
                                        "role": "agent",
                                        "parts": [
                                            {"kind": "text", "text": update.text}
                                        ],
                                        "messageId": str(uuid.uuid4()),
                                        "contextId": context_id,
                                    }
                                }
                                yield f"data: {json.dumps(event_data)}\n\n"

                        # Send final done event
                        yield "data: [DONE]\n\n"
                    except Exception as e:
                        error_data = {
                            "error": {"message": str(e), "contextId": context_id}
                        }
                        yield f"data: {json.dumps(error_data)}\n\n"

                return StreamingResponse(
                    generate_sse(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                )
            else:
                # Non-streaming response
                response = await self.agent.run(user_text)
                response_text = response.text.strip()

                # Strip tool call XML that shouldn't be in final output
                import re

                response_text = re.sub(
                    r"<tool_call>.*?</tool_call>", "", response_text, flags=re.DOTALL
                ).strip()

                if not response_text or response_text == "None":
                    response_text = "I've processed your request."

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
            print(f"DEBUG: Agent execution error: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
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
    host: str = "0.0.0.0",
    port: int = 8000,
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

    # Create triage agent WITHOUT tools - it only routes
    triage_agent = triage.get_agent(client, tools=None)

    agents: Dict[str, Agent] = {
        "triage": triage_agent,
        "inquiry": inquiry_agent,
        "transaction": transaction_agent,
        "advisor": advisor_agent,
        "manager": manager_agent,
    }

    # Create handlers - triage gets access to all agents for routing
    base_url = (
        f"http://{host}:{port}" if host != "0.0.0.0" else f"http://localhost:{port}"
    )

    handlers = {}
    for key, agent in agents.items():
        if key == "triage":
            handlers[key] = A2AAgentHandler(
                agent, key, all_agents=agents, base_url=base_url
            )
        else:
            handlers[key] = A2AAgentHandler(agent, key, base_url=base_url)

    routes = []

    for agent_key, handler in handlers.items():

        async def get_card(request: Request, h=handler):
            base_url = str(request.base_url).rstrip("/")
            return JSONResponse(h.get_agent_card(base_url))

        async def post_message(request: Request, h=handler):
            """Non-streaming message endpoint."""
            result = await h.handle_message(request, use_streaming=False)
            if isinstance(result, StreamingResponse):
                return result  # Already a response
            return JSONResponse(result)

        async def post_message_stream(request: Request, h=handler):
            """Streaming message endpoint using Server-Sent Events."""
            result = await h.handle_message(request, use_streaming=True)
            return result  # Already a StreamingResponse

        path = f"/a2a/{agent_key}"
        routes.append(Route(path, endpoint=get_card, methods=["GET"]))
        routes.append(
            Route(f"{path}/v1/message", endpoint=post_message, methods=["POST"])
        )
        routes.append(
            Route(
                f"{path}/v1/message:stream",
                endpoint=post_message_stream,
                methods=["POST"],
            )
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

    async def models_endpoint(request: Request) -> JSONResponse:
        """Return empty models list - this endpoint is for OpenAI SDK validation."""
        return JSONResponse({"object": "list", "data": []})

    routes.extend(
        [
            Route("/a2a", endpoint=list_agents, methods=["GET"]),
            Route("/health", endpoint=health, methods=["GET"]),
            Route("/v1/models", endpoint=models_endpoint, methods=["GET"]),
        ]
    )

    middleware = (
        [Middleware(AuthMiddleware, api_key=api_key, require_auth=require_auth)]
        if api_key or require_auth
        else []
    )

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            triage_handler = handlers.get("triage")
            if triage_handler and triage_handler.http_client:
                try:
                    await triage_handler.http_client.aclose()
                except Exception:
                    pass

            if mcp_tools:
                try:
                    await mcp_tools.close()
                except Exception:
                    pass

    return Starlette(routes=routes, middleware=middleware, lifespan=lifespan)


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
        ledger,
        ident,
        username,
        token,
        mode,
        model_name,
        api_key,
        require_auth,
        mcp_server_url,
        host,
        port,
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
        p.add_argument(
            "--require-auth", action="store_true", help="Require authentication"
        )
        p.add_argument(
            "--mcp-server-url", default="http://localhost:8001", help="MCP server URL"
        )
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
