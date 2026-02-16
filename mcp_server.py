"""
MCP Server - Exposes banking tools via the Model Context Protocol.

Transport modes:
- HTTP/SSE: For Azure Functions and remote hosting (recommended)
- stdio: For local development with Claude Desktop
"""

import os
import sys
import asyncio
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from ledger import LedgerEngine
from identity import IdentityManager

load_dotenv()

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("42-bank-tools")

_ledger: Optional[LedgerEngine] = None
_identity: Optional[IdentityManager] = None
_username: Optional[str] = None
_session_token: Optional[str] = None


def init_context(username: str) -> None:
    """Initialize banking context."""
    global _ledger, _identity, _username, _session_token
    _identity = IdentityManager()
    _ledger = LedgerEngine()
    _username = username
    _session_token = _identity.get_token(username)
    if not _session_token:
        raise ValueError(f"User {username} not found")
    pk = _identity.get_public_key(username)
    if pk:
        _ledger.register_user(_session_token, username, pk.hex())


@mcp.tool()
def check_balance(account_type: str = "checking") -> str:
    """View account balance."""
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    return f"Your {account_type} balance is ${_ledger.get_balance(_session_token, account_type):.2f}"


@mcp.tool()
def view_history(account_type: str = "checking") -> str:
    """View transaction history."""
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    return _ledger.get_history(_session_token, account_type)


@mcp.tool()
def list_my_accounts() -> str:
    """List all your accounts."""
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    return _ledger.list_user_accounts(_session_token)


@mcp.tool()
def send_money(
    to: str,
    amount: float,
    note: str,
    from_account: str = "checking",
    to_account: str = "checking",
) -> str:
    """Send money to another user."""
    if not _ledger or not _identity or not _username or not _session_token:
        return "ERROR: Not initialized"
    sig = _identity.sign_message(_username, f"{to}{amount}{note}".encode())
    success = _ledger.transfer(
        _session_token, to, amount, note, from_account, to_account, signature=sig.hex()
    )
    return (
        f"Transferred ${amount:.2f} to {to}."
        if success
        else "FAILED: Check funds or username."
    )


@mcp.tool()
def request_money(from_user: str, amount: float, note: str) -> str:
    """Request payment from another user."""
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    success = _ledger.request_funds(_session_token, from_user, amount, note)
    return (
        f"Requested ${amount:.2f} from {from_user}."
        if success
        else "FAILED: User not found."
    )


@mcp.tool()
def list_pending_requests() -> List[Dict[str, Any]]:
    """List pending payment requests."""
    if not _ledger or not _session_token:
        return [{"error": "Not initialized"}]
    return _ledger.get_pending_requests(_session_token)


@mcp.tool()
def approve_payment(request_id: str) -> str:
    """Approve a payment request."""
    if not _ledger or not _identity or not _username or not _session_token:
        return "ERROR: Not initialized"
    sig = _identity.sign_message(_username, f"APPROVE{request_id}".encode())
    success = _ledger.approve_request(_session_token, request_id, signature=sig.hex())
    return "Payment approved." if success else "FAILED: Check funds or ID."


@mcp.tool()
def list_products() -> str:
    """List bank products."""
    if not _ledger:
        return "ERROR: Not initialized"
    prods = _ledger.get_products()
    return "Products:\n" + "\n".join(
        f"- {p.name} ({p.type}): {p.interest_rate}%" for p in prods
    )


@mcp.tool()
def open_new_account(account_type: str) -> str:
    """Open a new account."""
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    return (
        f"Opened {account_type} account."
        if _ledger.open_account(_session_token, account_type)
        else "FAILED."
    )


@mcp.resource("bank://accounts")
def accounts_resource() -> str:
    """User accounts resource."""
    return (
        _ledger.list_user_accounts(_session_token)
        if _ledger and _session_token
        else "ERROR"
    )


@mcp.resource("bank://products")
def products_resource() -> str:
    """Bank products resource."""
    if not _ledger:
        return "ERROR"
    return "\n".join(
        f"{p.name}|{p.type}|{p.interest_rate}" for p in _ledger.get_products()
    )


def run_http(host: str = "0.0.0.0", port: int = 8001, username: str = "alice") -> None:
    """Run MCP server with HTTP/SSE transport (for Azure Functions)."""
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    from starlette.requests import Request
    from mcp.server.sse import SseServerTransport

    init_context(username)
    sse = SseServerTransport("/messages")

    async def handle_sse(request: Request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as (
            reader,
            writer,
        ):
            await mcp._mcp_server.run(
                reader, writer, mcp._mcp_server.create_initialization_options()
            )

    async def health(request: Request) -> JSONResponse:
        return JSONResponse(
            {"status": "healthy", "protocol": "MCP", "server": "42-bank-tools"}
        )

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_sse, methods=["POST"]),
            Route("/health", endpoint=health),
        ]
    )

    print(f"MCP HTTP Server: http://{host}:{port}", file=sys.stderr)
    print(f"SSE endpoint: /sse", file=sys.stderr)
    uvicorn.run(app, host=host, port=port)


def run_stdio(username: str = "alice") -> None:
    """Run MCP server with stdio transport (for local development)."""
    init_context(username)
    print(f"MCP stdio server initialized for: {username}", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="42-Bank MCP Server")
    p.add_argument("--http", action="store_true", help="Use HTTP/SSE transport")
    p.add_argument("--stdio", action="store_true", help="Use stdio transport")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8001)
    p.add_argument("--user", choices=["alice", "bob"], default="alice")
    args = p.parse_args()

    if args.stdio or not args.http:
        run_stdio(args.user)
    else:
        run_http(args.host, args.port, args.user)
