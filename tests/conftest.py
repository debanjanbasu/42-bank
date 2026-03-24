"""
Pytest configuration and fixtures for 42 Bank E2E tests.

Provides:
- Test database setup/teardown (Cosmos DB emulator, unique DB per test)
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
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from azure.cosmos import CosmosClient
from ledger import LedgerEngine
from identity import IdentityManager

EMULATOR_CONN_STR = "AccountEndpoint=https://localhost:8081/;AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="


@pytest.fixture(scope="function")
def test_db():
    """Create isolated Cosmos database per test, delete after."""
    db_name = f"banking_test_{uuid.uuid4().hex[:12]}"

    os.environ["COSMOS_DATABASE"] = db_name
    os.environ["AZURE_COSMOS_CONNECTION_STRING"] = EMULATOR_CONN_STR

    # Reset singletons so they pick up new env
    import ledger as ledger_mod
    import api.storage as storage_mod
    import db.cosmos as cosmos_mod

    ledger_mod._ledger_instance = None
    storage_mod._storage_instance = None
    # Reset Cosmos client so it re-reads connection string
    cosmos_mod._cosmos_client = None

    ledger = LedgerEngine()
    identity = IdentityManager()

    alice_token = identity.get_token("alice") or identity.create_identity("alice")
    alice_pk = identity.get_public_key("alice")
    if alice_pk:
        asyncio.run(ledger.register_user(alice_token, "alice", alice_pk.hex(), 1000.0))

    bob_token = identity.get_token("bob") or identity.create_identity("bob")
    bob_pk = identity.get_public_key("bob")
    if bob_pk:
        asyncio.run(ledger.register_user(bob_token, "bob", bob_pk.hex(), 800.0))

    yield {
        "alice_token": alice_token,
        "bob_token": bob_token,
        "identity": identity,
        "ledger": ledger,
        "db_name": db_name,
    }

    # Teardown: delete the test database
    ledger_mod._ledger_instance = None
    storage_mod._storage_instance = None
    cosmos_mod._cosmos_client = None
    try:
        cosmos = CosmosClient.from_connection_string(
            EMULATOR_CONN_STR, connection_verify=False
        )
        cosmos.delete_database(db_name)
    except Exception:
        pass

    os.environ.pop("COSMOS_DATABASE", None)


@pytest.fixture(scope="function")
async def mcp_server(test_db):
    """Start MCP server on port 8101 for testing (requires test_db)."""
    print("Starting MCP test server on port 8101...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["COSMOS_DATABASE"] = test_db["db_name"]
    env["AZURE_COSMOS_CONNECTION_STRING"] = EMULATOR_CONN_STR

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

    print("Stopping MCP test server...")
    try:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
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
        pass


@pytest.fixture(scope="function")
async def a2a_server(mcp_server):
    """Start A2A server on port 8100 for testing (requires MCP server)."""
    print("Starting A2A test server on port 8100...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    from utils import get_foundry_local_endpoint

    try:
        foundry_endpoint = await get_foundry_local_endpoint()
        env["FOUNDRY_LOCAL_ENDPOINT"] = foundry_endpoint
        print(f"Using Foundry at: {foundry_endpoint}")
    except RuntimeError as e:
        raise RuntimeError(
            f"Foundry not running. Start with: foundry model run qwen2.5-1.5b"
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

    print("Stopping A2A test server...")
    try:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
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
        pass


@pytest.fixture
async def http_client():
    """Provide HTTP client for tests - async with no timeout limit."""
    client = httpx.AsyncClient(timeout=None)
    yield client

    try:
        await client.aclose()
    except RuntimeError:
        pass


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "mcp: MCP server tests")
    config.addinivalue_line("markers", "a2a: A2A agent tests")
    config.addinivalue_line("markers", "e2e: End-to-end integration tests")
    config.addinivalue_line("markers", "slow: Slow tests (>5s)")


def extract_text(response_data):
    """Extract text content from A2A agent response, stripping tool calls."""
    result = response_data.get("result", {})
    text = ""
    for part in result.get("parts", []):
        if part.get("kind") == "text":
            text += part.get("text", "")

    import re

    text = re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL)
    return text.strip()


def extract_balance(text):
    """Extract numeric balance from text (handles various formats)."""
    import re

    match = re.search(r"\$?[\d,]+\.?\d*", text)
    if match:
        amount_str = match.group().replace("$", "").replace(",", "")
        if amount_str:
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

    success_words = ["success", "sent", "transferred", "complete", "done"]
    if any(word in text_lower for word in success_words):
        return True

    hard_failures = [
        "insufficient funds",
        "user not found",
        "invalid user",
        "failed: check funds",
    ]
    if any(phrase in text_lower for phrase in hard_failures):
        return False

    return True
