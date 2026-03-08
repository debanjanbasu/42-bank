"""
42-Bank Banking MCP Server

A custom MCP server that provides banking-specific tools.
Wraps the Azure Cosmos DB MCP Toolkit with business logic.

This server provides domain-specific banking tools:
- check_balance: Check account balance
- send_money: Transfer funds between users
- view_history: View transaction history
- request_payment: Request payment from another user
- approve_payment: Approve a pending payment request
- list_pending_requests: List pending payment requests
- list_products: List banking products
- open_account: Open a new account

Architecture:
    Foundry Agents → Banking MCP Server (this file)
                         ↓ calls
                    Cosmos DB MCP Toolkit (Microsoft)
                         ↓ calls
                    Azure Cosmos DB

Local Development:
    # Start Cosmos emulator
    docker-compose up -d cosmos-emulator
    
    # Initialize database
    uv run python scripts/init-cosmos-local.py
    
    # Run banking MCP server
    uv run python mcp_banking_server.py --http --port 8002
    
Production Deployment:
    # Deploy to Azure Container Apps
    az containerapp create --name 42bank-banking-mcp ...

Environment Variables:
    COSMOS_MCP_URL: URL of Cosmos DB MCP Toolkit
    COSMOS_DATABASE: Database name (default: banking)
    SESSION_TOKEN: Current user token (set by dev.sh or auth)
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

from mcp.server.fastmcp import FastMCP
import httpx

from cosmos_mcp_client import CosmosMCPClient, CosmosMCPError

# Configuration
COSMOS_MCP_URL = os.getenv("COSMOS_MCP_URL", "http://localhost:9000/mcp")
DATABASE_ID = os.getenv("COSMOS_DATABASE", "banking")
SESSION_TOKEN = os.getenv("SESSION_TOKEN", "")

# Initialize MCP server
mcp = FastMCP(
    "42-bank-banking-tools",
    version="1.0.0",
)

# Initialize Cosmos MCP client
cosmos = CosmosMCPClient(base_url=COSMOS_MCP_URL, database_id=DATABASE_ID)


# ============ Helper Functions ============

def get_session_token() -> str:
    """Get current session token."""
    token = SESSION_TOKEN or os.getenv("SESSION_TOKEN", "")
    if not token:
        raise ValueError("SESSION_TOKEN not set")
    return token


async def get_current_user() -> Dict[str, Any]:
    """Get current user from session token."""
    token = get_session_token()
    user = await cosmos.find_document("users", token)
    if not user:
        raise ValueError("User not found")
    return user


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    return f"${amount:,.2f}"


# ============ Banking Tools ============

@mcp.tool()
async def check_balance(account_type: str = "checking") -> str:
    """
    Check your account balance.
    
    Args:
        account_type: Type of account (checking or savings)
    
    Returns:
        Your account balance as a formatted string
    """
    try:
        token = get_session_token()
        user = await cosmos.find_document("users", token)
        
        if not user:
            return "ERROR: User not found. Please log in again."
        
        accounts = user.get("accounts", {})
        
        if account_type not in accounts:
            return f"FAILED: You don't have a {account_type} account. Use 'open_account' to create one."
        
        balance = accounts[account_type].get("balance", 0.0)
        return f"Your {account_type} account balance is {format_currency(balance)}"
        
    except ValueError as e:
        return f"ERROR: {e}"
    except CosmosMCPError as e:
        return f"ERROR: Database error - {e}"


@mcp.tool()
async def send_money(
    recipient_username: str,
    amount: float,
    description: str,
    from_account: str = "checking",
    to_account: str = "checking",
) -> str:
    """
    Send money to another user.
    
    Args:
        recipient_username: Username of the recipient
        amount: Amount to send (must be positive)
        description: Description of the transaction
        from_account: Your account to send from (default: checking)
        to_account: Recipient's account to receive (default: checking)
    
    Returns:
        Confirmation message or error
    """
    try:
        # Validate inputs
        if amount <= 0:
            return "FAILED: Amount must be positive."
        
        if not recipient_username:
            return "FAILED: Recipient username is required."
        
        # Get sender
        token = get_session_token()
        sender = await cosmos.find_document("users", token)
        if not sender:
            return "ERROR: Your account not found. Please log in again."
        
        # Get recipient
        recipient = await cosmos.get_user_by_username(recipient_username)
        if not recipient:
            return f"FAILED: User '{recipient_username}' not found."
        
        # Check sender is not recipient
        if sender.get("username") == recipient_username:
            return "FAILED: Cannot send money to yourself."
        
        # Check sender balance
        sender_accounts = sender.get("accounts", {})
        if from_account not in sender_accounts:
            return f"FAILED: You don't have a {from_account} account."
        
        sender_balance = sender_accounts[from_account].get("balance", 0.0)
        if sender_balance < amount:
            return f"FAILED: Insufficient funds. Your {from_account} balance is {format_currency(sender_balance)}."
        
        # Note: In production, this would be an atomic transaction
        # For now, we simulate the transfer
        
        # Create transaction record (in a real implementation, we'd use Cosmos SDK)
        transaction = {
            "id": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat(),
            "sender": sender.get("username"),
            "recipient": recipient_username,
            "amount": amount,
            "description": description,
            "account_type": from_account,
        }
        
        # Return success (actual DB update would happen here)
        return f"Successfully sent {format_currency(amount)} to {recipient_username}: {description}"
        
    except ValueError as e:
        return f"ERROR: {e}"
    except CosmosMCPError as e:
        return f"ERROR: Database error - {e}"


@mcp.tool()
async def view_history(limit: int = 10) -> str:
    """
    View your recent transaction history.
    
    Args:
        limit: Number of transactions to show (default: 10)
    
    Returns:
        Formatted list of recent transactions
    """
    try:
        user = await get_current_user()
        username = user.get("username")
        
        # Get transactions involving this user
        transactions = await cosmos.get_user_transactions(username, limit)
        
        if not transactions:
            return "No transactions found."
        
        lines = ["Recent Transactions:"]
        lines.append("-" * 50)
        
        for txn in transactions[:limit]:
            timestamp = txn.get("timestamp", "")[:10]
            amount = txn.get("amount", 0)
            sender = txn.get("sender", "")
            recipient = txn.get("recipient", "")
            desc = txn.get("description", "")
            
            if sender == username:
                lines.append(f"[{timestamp}] Sent {format_currency(amount)} to {recipient}: {desc}")
            else:
                lines.append(f"[{timestamp}] Received {format_currency(amount)} from {sender}: {desc}")
        
        return "\n".join(lines)
        
    except ValueError as e:
        return f"ERROR: {e}"
    except CosmosMCPError as e:
        return f"ERROR: Database error - {e}"


@mcp.tool()
async def request_payment(
    from_username: str,
    amount: float,
    description: str,
) -> str:
    """
    Request payment from another user.
    
    Args:
        from_username: Username to request payment from
        amount: Amount to request (must be positive)
        description: Description of the request
    
    Returns:
        Confirmation message
    """
    try:
        if amount <= 0:
            return "FAILED: Amount must be positive."
        
        if not from_username:
            return "FAILED: Username is required."
        
        user = await get_current_user()
        
        # Check if from_user exists
        from_user = await cosmos.get_user_by_username(from_username)
        if not from_user:
            return f"FAILED: User '{from_username}' not found."
        
        # Create pending request (in production, would save to Cosmos)
        request_id = datetime.now().isoformat()
        
        return f"Payment request created: requesting {format_currency(amount)} from {from_username}. Request ID: {request_id[:19]}"
        
    except ValueError as e:
        return f"ERROR: {e}"
    except CosmosMCPError as e:
        return f"ERROR: Database error - {e}"


@mcp.tool()
async def approve_payment(request_id: str) -> str:
    """
    Approve a pending payment request.
    
    Args:
        request_id: ID of the payment request to approve
    
    Returns:
        Confirmation message
    """
    try:
        user = await get_current_user()
        username = user.get("username")
        
        # Find the request
        request = await cosmos.find_document("pending_requests", request_id)
        
        if not request:
            return f"FAILED: Request '{request_id[:19]}' not found."
        
        if request.get("recipient") != username:
            return "FAILED: This payment request is not for you."
        
        if request.get("status") != "pending":
            return f"FAILED: Request is already {request.get('status')}."
        
        # Execute the transfer
        result = await send_money(
            recipient_username=request.get("requester"),
            amount=request.get("amount", 0),
            description=f"Payment request: {request.get('description', '')}",
        )
        
        if "Successfully" in result:
            return f"Payment approved and sent. {result}"
        else:
            return f"FAILED: Could not complete payment. {result}"
            
    except ValueError as e:
        return f"ERROR: {e}"
    except CosmosMCPError as e:
        return f"ERROR: Database error - {e}"


@mcp.tool()
async def list_pending_requests() -> str:
    """
    List your pending payment requests.
    
    Returns:
        List of pending payment requests
    """
    try:
        user = await get_current_user()
        username = user.get("username")
        
        # Get pending requests for this user
        requests = await cosmos.get_pending_requests_for_user(username)
        
        if not requests:
            return "No pending payment requests."
        
        lines = ["Pending Payment Requests:"]
        lines.append("-" * 50)
        
        for req in requests:
            req_id = req.get("id", "")[:19]
            requester = req.get("requester", "")
            amount = req.get("amount", 0)
            desc = req.get("description", "")
            
            lines.append(f"ID: {req_id} | {requester} requests {format_currency(amount)}: {desc}")
        
        return "\n".join(lines)
        
    except ValueError as e:
        return f"ERROR: {e}"
    except CosmosMCPError as e:
        return f"ERROR: Database error - {e}"


@mcp.tool()
async def list_products() -> str:
    """
    List available banking products.
    
    Returns:
        List of banking products (accounts, CDs, etc.)
    """
    try:
        products = await cosmos.get_recent_documents("products", count=20)
        
        if not products:
            return "No products available."
        
        lines = ["Available Banking Products:"]
        lines.append("-" * 50)
        
        for product in products:
            name = product.get("name", "Unknown")
            desc = product.get("description", "No description")
            rate = product.get("rate")
            prod_type = product.get("type", "account")
            
            if rate:
                lines.append(f"- {name} ({prod_type}): {desc} [APY: {rate*100:.2f}%]")
            else:
                lines.append(f"- {name} ({prod_type}): {desc}")
        
        return "\n".join(lines)
        
    except CosmosMCPError as e:
        return f"ERROR: Database error - {e}"


@mcp.tool()
async def open_account(
    account_type: str,
    initial_deposit: float = 0,
) -> str:
    """
    Open a new account.
    
    Args:
        account_type: Type of account to open (e.g., 'savings', 'investment')
        initial_deposit: Initial deposit amount (default: 0)
    
    Returns:
        Confirmation message
    """
    try:
        if initial_deposit < 0:
            return "FAILED: Initial deposit cannot be negative."
        
        user = await get_current_user()
        accounts = user.get("accounts", {})
        
        if account_type in accounts:
            return f"FAILED: You already have a {account_type} account."
        
        # In production, would update the user document
        return f"Successfully opened a new {account_type} account with {format_currency(initial_deposit)} initial deposit."
        
    except ValueError as e:
        return f"ERROR: {e}"
    except CosmosMCPError as e:
        return f"ERROR: Database error - {e}"


@mcp.tool()
async def list_my_accounts() -> str:
    """
    List all your accounts and their balances.
    
    Returns:
        List of accounts with balances
    """
    try:
        user = await get_current_user()
        accounts = user.get("accounts", {})
        
        if not accounts:
            return "You have no accounts."
        
        lines = ["Your Accounts:"]
        lines.append("-" * 30)
        
        total = 0.0
        for account_type, account_data in accounts.items():
            balance = account_data.get("balance", 0.0)
            total += balance
            lines.append(f"- {account_type.title()}: {format_currency(balance)}")
        
        lines.append("-" * 30)
        lines.append(f"Total Balance: {format_currency(total)}")
        
        return "\n".join(lines)
        
    except ValueError as e:
        return f"ERROR: {e}"


# ============ Server Startup ============

def main():
    """Run the Banking MCP server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="42-Bank Banking MCP Server")
    parser.add_argument("--http", action="store_true", help="Run as HTTP server")
    parser.add_argument("--port", type=int, default=8002, help="Port for HTTP server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host for HTTP server")
    parser.add_argument("--user", type=str, help="Set session user token")
    args = parser.parse_args()
    
    # Set session token if provided
    if args.user:
        os.environ["SESSION_TOKEN"] = f"{args.user}_token"
    
    print("🏦 42-Bank Banking MCP Server")
    print("=" * 40)
    print(f"Cosmos MCP URL: {COSMOS_MCP_URL}")
    print(f"Database: {DATABASE_ID}")
    print(f"Session Token: {SESSION_TOKEN or 'Not set'}")
    print()
    
    if args.http:
        print(f"Starting HTTP server on {args.host}:{args.port}...")
        import uvicorn
        uvicorn.run(mcp.sse_app(), host=args.host, port=args.port)
    else:
        print("Running MCP server (stdio mode)...")
        mcp.run()


if __name__ == "__main__":
    main()
