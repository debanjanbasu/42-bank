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


def init_context(username: str, db_path: Optional[str] = None) -> None:
    """Initialize banking context."""
    global _ledger, _identity, _username, _session_token
    _identity = IdentityManager()
    _ledger = LedgerEngine(db_path=db_path) if db_path else LedgerEngine()
    _username = username
    _session_token = _identity.get_token(username)
    if not _session_token:
        raise ValueError(f"User {username} not found")
    
    # Only register user if they don't already exist in the ledger
    existing_user = _ledger._get_user(_session_token)
    if not existing_user:
        pk = _identity.get_public_key(username)
        if pk:
            _ledger.register_user(_session_token, username, pk.hex())


@mcp.tool()
def check_balance() -> str:
    """View your checking account balance."""
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    balance = _ledger.get_balance(_session_token, "checking")
    return f"Your checking account balance is ${balance:.2f}"


@mcp.tool()
def view_history() -> str:
    """View transaction history for your checking account."""
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    return _ledger.get_history(_session_token, "checking")


@mcp.tool()
def list_my_accounts() -> str:
    """List your checking account and balance."""
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    return _ledger.list_user_accounts(_session_token)


@mcp.tool()
def send_money(to: str, amount: float, note: str) -> str:
    """
    Send money from your checking account to another user.
    
    Args:
        to: Username of recipient
        amount: Amount to send (must be positive)
        note: Description of payment
        
    Returns:
        Success message or detailed error
    """
    if not _ledger or not _identity or not _username or not _session_token:
        return "ERROR: Service not initialized"
    
    # Validate inputs
    if not to or not note:
        return "FAILED: Recipient username and note are required."
    if amount <= 0:
        return "FAILED: Amount must be positive."
    
    # Check balance first for better error message
    balance = _ledger.get_balance(_session_token, "checking")
    if balance < amount:
        return f"FAILED: Insufficient funds. Balance: ${balance:.2f}, Requested: ${amount:.2f}"
    
    # Verify recipient exists
    recipient_token = _ledger.get_token_by_username(to)
    if not recipient_token:
        return f"FAILED: User '{to}' not found."
    
    # Sign and execute transfer
    sig = _identity.sign_message(_username, f"{to}{amount}{note}".encode())
    success = _ledger.transfer(
        _session_token, to, amount, note, "checking", "checking", signature=sig.hex()
    )
    
    if success:
        return f"Transferred ${amount:.2f} to {to}."
    else:
        return "FAILED: Transfer could not be completed."


@mcp.tool()
def request_money(from_user: str, amount: float, note: str) -> str:
    """
    Request payment from another user.
    
    Args:
        from_user: Username to request payment from
        amount: Amount to request (must be positive)
        note: Reason for request
        
    Returns:
        Success message or detailed error
    """
    if not _ledger or not _session_token:
        return "ERROR: Service not initialized"
    
    # Validate inputs
    if not from_user or not note:
        return "FAILED: Username and note are required."
    if amount <= 0:
        return "FAILED: Amount must be positive."
    
    # Check if user exists
    target_token = _ledger.get_token_by_username(from_user)
    if not target_token:
        return f"FAILED: User '{from_user}' not found."
    
    success = _ledger.request_funds(_session_token, from_user, amount, note)
    return (
        f"Requested ${amount:.2f} from {from_user}."
        if success
        else "FAILED: Request could not be created."
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
    """Run MCP server with streamable HTTP transport (for Agent Framework)."""
    db_path = os.getenv("TEST_DB")  # Allow tests to specify database
    init_context(username, db_path=db_path)
    print(f"MCP Streamable HTTP Server: http://{host}:{port}", file=sys.stderr)
    print(f"User: {username}", file=sys.stderr)
    if db_path:
        print(f"Database: {db_path}", file=sys.stderr)
    
    # Use streamable-http transport which works with MCPStreamableHTTPTool
    import uvicorn
    app = mcp.streamable_http_app()
    uvicorn.run(app, host=host, port=port)



def run_stdio(username: str = "alice") -> None:
    """Run MCP server with stdio transport (for local development)."""
    db_path = os.getenv("TEST_DB")
    init_context(username, db_path=db_path)
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
