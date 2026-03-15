"""
A2A Mount Wrapper for Consolidated API

This module creates a properly configured A2A app instance
that can be mounted in the main FastAPI application.
"""

import logging
import os
from typing import Optional

from starlette.applications import Starlette

from identity import IdentityManager
from ledger import LedgerEngine

logger = logging.getLogger("42bank.a2a_mount")


async def create_mounted_a2a_app(
    username: str = "alice",
    mode: str = "hosted",
    api_key: Optional[str] = None,
) -> Starlette:
    """
    Create and configure A2A app for mounting in main API.

    This wrapper initializes the required dependencies (ledger, identity)
    and creates a properly configured A2A app instance.

    Args:
        username: Default user for A2A context (default: "alice")
        mode: Operation mode - "hosted" for cloud deployment
        api_key: API key for authentication (optional for hackathon)

    Returns:
        Configured Starlette app ready to be mounted
    """
    from a2a_server import create_a2a_app

    # Initialize dependencies
    identity = IdentityManager()
    ledger = LedgerEngine()

    # Get session token for the default user
    # In production, this user should exist or be created via API first
    try:
        session_token = identity.get_token(username)
        if not session_token:
            # User doesn't exist locally - create a placeholder
            import hashlib

            session_token = hashlib.sha256(username.encode()).hexdigest()
            logger.info(
                f"⚠️ Using placeholder token for user '{username}' - create via API first"
            )
    except Exception as e:
        logger.warning(f"Could not get token for {username}: {e}")
        import hashlib

        session_token = hashlib.sha256(username.encode()).hexdigest()

    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.getenv("AZURE_API_KEY")

    # Get MCP server URL from environment
    # In single-container deployment, this should point to the MCP server if running
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")

    # Create A2A app with configuration
    a2a_app = await create_a2a_app(
        ledger=ledger,
        identity=identity,
        username=username,
        session_token=session_token,
        mode=mode,
        model_name=os.getenv("MODEL_NAME"),
        api_key=api_key,
        require_auth=False,  # Use API key auth at API level
        mcp_server_url=mcp_server_url,
        host="0.0.0.0",
        port=8000,  # Port is handled by main app
    )

    return a2a_app
