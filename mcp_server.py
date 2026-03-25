"""
MCP Server - Exposes banking tools via the Model Context Protocol.

Transport modes:
- HTTP/SSE: For Azure Functions and remote hosting (recommended)
- stdio: For local development with Claude Desktop
"""

import contextvars
import os
import sys
import asyncio
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from ledger import LedgerEngine, AccountType
from identity import IdentityManager

load_dotenv()

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.requests import Request

mcp = FastMCP("42-bank-tools")


# Per-request user context (async-safe, works with concurrent requests)
_user_token_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user_token", default=None
)


def set_user_context(user_token: str) -> None:
    """Set the user token for the current request context.

    Call this before executing A2A agent tool calls so the MCP tools
    operate on the authenticated user's data.
    """
    _user_token_var.set(user_token)


def get_user_token() -> Optional[str]:
    """Get the user token from the current request context."""
    return _user_token_var.get()


# Add a simple health check endpoint
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "42-bank-mcp"})


_ledger: Optional[LedgerEngine] = None
_identity: Optional[IdentityManager] = None
_username: Optional[str] = None
_session_token: Optional[str] = None
_initialized = False


async def _ensure_initialized(username: str = "alice") -> None:
    """Ensure banking context is initialized in the current event loop.

    If a per-request user token is set via set_user_context(), that takes
    precedence over the default username-based initialization. This allows
    A2A agents to operate on the authenticated user's data.
    """
    global _ledger, _identity, _username, _session_token, _initialized

    # Check for per-request user context (set by A2A handler from JWT)
    ctx_token = get_user_token()
    if ctx_token:
        if not _ledger:
            _ledger = LedgerEngine()
        if not _identity:
            _identity = IdentityManager()
        # Use the token directly — it's the user's ledger token from their JWT
        _session_token = ctx_token
        _username = username
        _initialized = True
        return

    if _initialized:
        return

    print(
        f"[MCP SERVER DEBUG] Initializing context for user: {username}", file=sys.stderr
    )
    print(
        f"[MCP SERVER DEBUG] Current working directory: {os.getcwd()}", file=sys.stderr
    )

    _identity = IdentityManager()
    _ledger = LedgerEngine()
    _username = username
    _session_token = _identity.get_token(username)

    if not _session_token:
        raise ValueError(f"User {username} not found")

    existing_user = await _ledger._get_user(_session_token)
    if not existing_user:
        pk = _identity.get_public_key(username)
        if pk:
            await _ledger.register_user(_session_token, username, pk.hex())

    _initialized = True
    print(
        f"[MCP SERVER DEBUG] Context initialized for user: {username}", file=sys.stderr
    )


@mcp.tool()
async def check_balance() -> str:
    """View your checking account balance."""
    await _ensure_initialized()
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    balance = await _ledger.get_balance(_session_token, AccountType.CHECKING)
    return f"Your checking account balance is ${balance:.2f}"


@mcp.tool()
async def view_history() -> str:
    """View transaction history for your checking account."""
    await _ensure_initialized()
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    return await _ledger.get_history(_session_token, "checking")


@mcp.tool()
async def list_my_accounts() -> str:
    """List your checking account and balance."""
    await _ensure_initialized()
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    return await _ledger.list_user_accounts(_session_token)


@mcp.tool()
async def send_money(to: str, amount: float, note: str) -> str:
    """
    Send money from your checking account to another user.

    Args:
        to: Username of recipient
        amount: Amount to send (must be positive)
        note: Description of payment

    Returns:
        Success message or detailed error
    """
    await _ensure_initialized()
    if not _ledger or not _identity or not _username or not _session_token:
        return "ERROR: Service not initialized"

    # Validate inputs
    if not to:
        return "FAILED: Recipient username is required."
    if amount <= 0:
        return "FAILED: Amount must be positive."
    if amount > 1_000_000:
        return "FAILED: Amount exceeds maximum transfer limit of $1,000,000."

    # Check balance first for better error message
    balance = await _ledger.get_balance(_session_token, "checking")
    if balance < amount:
        return f"FAILED: Insufficient funds. Balance: ${balance:.2f}, Requested: ${amount:.2f}"

    # Verify recipient exists
    recipient_token = await _ledger.get_token_by_username(to)
    if not recipient_token:
        return f"FAILED: User '{to}' not found."

    # Sign and execute transfer (signing optional — mobile users sign on-device)
    sig_hex = ""
    try:
        sig = _identity.sign_message(_username, f"{to}{amount}{note}".encode())
        sig_hex = sig.hex()
    except Exception:
        pass  # Server-side signing not available for this user (mobile-only keys)

    success = await _ledger.transfer(
        _session_token, to, amount, note, "checking", "checking", signature=sig_hex
    )

    if success:
        return f"Transferred ${amount:.2f} to {to}."
    else:
        return "FAILED: Transfer could not be completed."


@mcp.tool()
async def request_money(from_user: str, amount: float, note: str) -> str:
    """
    Request payment from another user.

    Args:
        from_user: Username to request payment from
        amount: Amount to request (must be positive)
        note: Reason for request

    Returns:
        Success message or detailed error
    """
    await _ensure_initialized()
    if not _ledger or not _session_token:
        return "ERROR: Service not initialized"

    # Validate inputs
    if not from_user or not note:
        return "FAILED: Username and note are required."
    if amount <= 0:
        return "FAILED: Amount must be positive."

    # Check if user exists
    target_token = await _ledger.get_token_by_username(from_user)
    if not target_token:
        return f"FAILED: User '{from_user}' not found."

    success = await _ledger.request_funds(_session_token, from_user, amount, note)
    return (
        f"Requested ${amount:.2f} from {from_user}."
        if success
        else "FAILED: Request could not be created."
    )


@mcp.tool()
async def list_pending_requests() -> List[Dict[str, Any]]:
    """List pending payment requests."""
    await _ensure_initialized()
    if not _ledger or not _session_token:
        return [{"error": "Not initialized"}]
    return await _ledger.get_pending_requests(_session_token)


@mcp.tool()
async def approve_payment(request_id: str) -> str:
    """Approve a payment request."""
    await _ensure_initialized()
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    sig_hex = ""
    try:
        if _identity and _username:
            sig = _identity.sign_message(_username, f"APPROVE{request_id}".encode())
            sig_hex = sig.hex()
    except Exception:
        pass
    success = await _ledger.approve_request(
        _session_token, request_id, signature=sig_hex
    )
    return "Payment approved." if success else "FAILED: Check funds or ID."


@mcp.tool()
async def list_products() -> str:
    """List bank products."""
    await _ensure_initialized()
    if not _ledger:
        return "ERROR: Not initialized"
    prods = await _ledger.get_products()
    return "Products:\n" + "\n".join(
        f"- {p.name} ({p.type}): {p.interest_rate}%" for p in prods
    )


@mcp.tool()
async def open_new_account(account_type: str) -> str:
    """Open a new account."""
    await _ensure_initialized()
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    valid_types = {
        AccountType.CHECKING,
        AccountType.SAVINGS,
        "loan",
        "mortgage",
        "credit_card",
    }
    if account_type not in valid_types:
        return (
            f"FAILED: Invalid account type '{account_type}'. "
            f"Valid types: {', '.join(str(t) for t in valid_types)}"
        )
    return (
        f"Opened {account_type} account."
        if await _ledger.open_account(_session_token, account_type)
        else "FAILED."
    )


@mcp.resource("bank://accounts")
async def accounts_resource() -> str:
    """User accounts resource."""
    return (
        await _ledger.list_user_accounts(_session_token)
        if _ledger and _session_token
        else "ERROR"
    )


@mcp.resource("bank://products")
async def products_resource() -> str:
    """Bank products resource."""
    if not _ledger:
        return "ERROR"
    return "\n".join(
        f"{p.name}|{p.type}|{p.interest_rate}" for p in await _ledger.get_products()
    )


def run_http(host: str = "0.0.0.0", port: int = 8001, username: str = "alice") -> None:
    """Run MCP server with streamable HTTP transport (for Agent Framework)."""
    # Initialize in the async context via lifespan or first tool call
    print(f"MCP Streamable HTTP Server: http://{host}:{port}", file=sys.stderr)
    print(f"User: {username}", file=sys.stderr)
    # Use streamable-http transport which works with MCPStreamableHTTPTool
    import uvicorn

    app = mcp.streamable_http_app()
    uvicorn.run(app, host=host, port=port)


def run_stdio(username: str = "alice") -> None:
    """Run MCP server with stdio transport (for local development)."""
    # Initialize in the async context via lifespan or first tool call
    print(f"MCP stdio server initialized for: {username}", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    import argparse
    import sys

    p = argparse.ArgumentParser(description="42-Bank MCP Server")
    p.add_argument("--http", action="store_true", help="Use HTTP/SSE transport")
    p.add_argument("--stdio", action="store_true", help="Use stdio transport")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8001)
    p.add_argument("--user", choices=["alice", "bob"], default="alice")
    args = p.parse_args()

    try:
        if args.stdio or not args.http:
            run_stdio(args.user)
        else:
            run_http(args.host, args.port, args.user)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down MCP server...", file=sys.stderr)
        sys.exit(0)
