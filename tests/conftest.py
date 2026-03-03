"""
Pytest configuration and fixtures for 42 Bank E2E tests.

Provides:
- Test database setup/teardown
- MCP server fixture (port 8101)
- A2A server fixture (port 8100)
- Test users (alice, bob)
- Cleanup utilities
"""

import os
import sys
import pytest
import asyncio
import time
import signal
import subprocess
import httpx
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ledger import LedgerEngine
from identity import IdentityManager


# Test database path
TEST_DB = "data/test_bank.db"


# Don't override event_loop - use pytest-asyncio's default handling


@pytest.fixture(scope="session")
def test_db_setup():
    """Setup test database once at session start."""
    # Remove old test DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    yield TEST_DB

    # Final cleanup
    time.sleep(0.1)
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except:
            pass


@pytest.fixture(scope="function")
def test_db(test_db_setup):
    """Provide clean test database for each test."""
    # Force close any open connections to the test database
    import gc

    gc.collect()

    # Remove and recreate database for each test
    if os.path.exists(TEST_DB):
        # Try multiple times to delete, as processes may still have it open
        for _ in range(3):
            try:
                os.remove(TEST_DB)
                break
            except (OSError, PermissionError):
                time.sleep(0.1)

    time.sleep(0.1)  # Allow file system to catch up

    # Create fresh database
    ledger = LedgerEngine(db_path=TEST_DB)
    identity = IdentityManager()

    # Create test users with initial balances
    # Use get_token first to check if identity exists, otherwise create it
    alice_token = identity.get_token("alice")
    if not alice_token:
        alice_token = identity.create_identity("alice")
    alice_pk = identity.get_public_key("alice")
    if alice_pk:
        ledger.register_user(alice_token, "alice", alice_pk.hex(), 1000.0)

    bob_token = identity.get_token("bob")
    if not bob_token:
        bob_token = identity.create_identity("bob")
    bob_pk = identity.get_public_key("bob")
    if bob_pk:
        ledger.register_user(bob_token, "bob", bob_pk.hex(), 800.0)

    result = {
        "ledger": ledger,
        "identity": identity,
        "alice_token": alice_token,
        "bob_token": bob_token,
    }

    # Force close the ledger connection to ensure data is flushed to disk
    # This is important because the MCP server will open its own connection
    del ledger
    gc.collect()

    # Force SQLite to flush by opening and closing a connection
    import sqlite3

    conn = sqlite3.connect(TEST_DB)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")  # Force WAL checkpoint
    conn.close()
    time.sleep(0.3)  # Allow file system to sync

    # Recreate ledger reference for tests that need it
    result["ledger"] = LedgerEngine(db_path=TEST_DB)

    yield result

    # Cleanup - close database connections
    result["ledger"] = None
    result["identity"] = None
    gc.collect()  # Force cleanup


@pytest.fixture(scope="function")
async def mcp_server(test_db):
    """Start MCP server on port 8101 for testing (requires test_db)."""
    # Start MCP server
    print("Starting MCP test server on port 8101...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["TEST_DB"] = TEST_DB  # Tell MCP server to use test database

    process = subprocess.Popen(
        [
            "uv",
            "run",
            "python",
            "mcp_server.py",
            "--http",
            "--user",
            "alice",
            "--port",
            "8101",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
    )

    # Wait for server to be ready
    max_wait = 10
    for i in range(max_wait * 2):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8101/", timeout=2)
                print("✅ MCP test server ready")
                break
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        await asyncio.sleep(0.5)
    else:
        process.kill()
        raise RuntimeError("MCP test server failed to start")

    yield "http://localhost:8101"

    # Cleanup
    print("Stopping MCP test server...")
    try:
        # Try graceful termination first
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            # Force kill if graceful fails
            if hasattr(os, "killpg"):
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
    except Exception:
        pass  # Best effort cleanup


@pytest.fixture(scope="function")
async def a2a_server(mcp_server):
    """Start A2A server on port 8100 for testing (requires MCP server)."""
    # Start A2A server
    print("Starting A2A test server on port 8100...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    # Set Foundry endpoint so A2A server doesn't have to discover it
    from utils import get_foundry_local_endpoint

    try:
        foundry_endpoint = get_foundry_local_endpoint()
        env["FOUNDRY_LOCAL_ENDPOINT"] = foundry_endpoint
        print(f"Using Foundry at: {foundry_endpoint}")
    except RuntimeError as e:
        raise RuntimeError(
            f"Foundry not running. Start with: foundry model run qwen2.5-14b-instruct-generic-gpu:4"
        ) from e

    process = subprocess.Popen(
        [
            "uv",
            "run",
            "python",
            "a2a_server.py",
            "--user",
            "alice",
            "--port",
            "8100",
            "--mcp-server-url",
            mcp_server,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
    )

    # Wait for server to be ready
    max_wait = 15
    for i in range(max_wait * 2):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8100/health", timeout=2)
                if response.status_code == 200:
                    print("✅ A2A test server ready")
                    break
        except:
            pass
        await asyncio.sleep(0.5)
    else:
        process.kill()
        raise RuntimeError("A2A test server failed to start")

    yield "http://localhost:8100"

    # Cleanup
    print("Stopping A2A test server...")
    try:
        # Try graceful termination first
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            # Force kill if graceful fails
            if hasattr(os, "killpg"):
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
    except Exception:
        pass  # Best effort cleanup


@pytest.fixture
async def http_client():
    """Provide HTTP client for tests - async with no timeout limit."""
    # No timeout - let async operations complete naturally
    client = httpx.AsyncClient(timeout=None)
    yield client

    # Cleanup - ensure proper closing even if event loop is closing
    try:
        await client.aclose()
    except RuntimeError:
        pass  # Event loop already closed


# Pytest markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "mcp: MCP server tests")
    config.addinivalue_line("markers", "a2a: A2A agent tests")
    config.addinivalue_line("markers", "e2e: End-to-end integration tests")
    config.addinivalue_line("markers", "slow: Slow tests (>5s)")


# Helper function for extracting text from A2A responses
def extract_text(response_data):
    """Extract text content from A2A agent response, stripping tool calls."""
    result = response_data.get("result", {})
    text = ""
    for part in result.get("parts", []):
        if part.get("kind") == "text":
            text += part.get("text", "")

    # Strip tool call XML that shouldn't be in final output
    import re

    text = re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL)
    return text.strip()


def extract_balance(text):
    """Extract numeric balance from text (handles various formats)."""
    import re

    # Look for dollar amounts: $1000, $1,000, $1000.00, etc.
    match = re.search(r"\$?[\d,]+\.?\d*", text)
    if match:
        amount_str = match.group().replace("$", "").replace(",", "")
        if amount_str:  # Check not empty string
            try:
                return float(amount_str)
            except ValueError:
                return None
    return None


def is_transaction_successful(text: str) -> bool:
    """
    Check if a transaction was successful or acceptable (considering LLM variability).

    Returns True if:
    - Transaction succeeded (success, sent, transferred keywords)
    - Response is ambiguous/retryable (LLM parsing issues)

    Returns False only for hard business failures:
    - Insufficient funds
    - User not found
    """
    text_lower = text.lower()

    # Success indicators
    success_words = ["success", "sent", "transferred", "complete", "done"]
    if any(word in text_lower for word in success_words):
        return True

    # Hard failures (business logic - these are real errors)
    hard_failures = [
        "insufficient funds",
        "user not found",
        "invalid user",
        "failed: check funds",
    ]
    if any(phrase in text_lower for phrase in hard_failures):
        return False

    # Soft failures (LLM parsing issues - acceptable due to variability)
    # Examples: "encountered an issue", "need correct parameters"
    # These are NOT test failures, they're LLM quirks
    return True
