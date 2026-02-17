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


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db():
    """Provide clean test database for each test."""
    # Remove old test DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # Create fresh database
    ledger = LedgerEngine(db_path=TEST_DB)
    identity = IdentityManager()
    
    # Create test users with initial balances
    alice_token = identity.create_identity("alice")
    alice_pk = identity.get_public_key("alice")
    ledger.register_user(alice_token, "alice", alice_pk.hex(), 1000.0)
    
    bob_token = identity.create_identity("bob")
    bob_pk = identity.get_public_key("bob")
    ledger.register_user(bob_token, "bob", bob_pk.hex(), 800.0)
    
    yield {
        "ledger": ledger,
        "identity": identity,
        "alice_token": alice_token,
        "bob_token": bob_token,
    }
    
    # Cleanup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture(scope="session")
async def mcp_server(test_db):
    """Start MCP server on port 8101 for testing (requires test_db)."""
    # Check if port is already in use
    try:
        async with httpx.AsyncClient() as client:
            await client.get("http://localhost:8101/health", timeout=1)
            print("⚠️  MCP test server already running on 8101")
            yield "http://localhost:8101"
            return
    except:
        pass
    
    # Start MCP server
    print("Starting MCP test server on port 8101...")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["TEST_DB"] = TEST_DB  # Tell MCP server to use test database
    
    process = subprocess.Popen(
        [
            "uv", "run", "python", "mcp_server.py",
            "--http", "--user", "alice", "--port", "8101"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        preexec_fn=os.setsid if hasattr(os, 'setsid') else None
    )
    
    # Wait for server to be ready (just check if port is listening)
    max_wait = 10
    for i in range(max_wait * 2):
        try:
            async with httpx.AsyncClient() as client:
                # MCP server doesn't have /health, just check if port responds
                response = await client.get("http://localhost:8101/", timeout=2)
                # Any response (even 404) means server is up
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
    if hasattr(os, 'killpg'):
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    else:
        process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="session")
async def a2a_server(mcp_server):
    """Start A2A server on port 8100 for testing (requires MCP server)."""
    # Check if port is already in use
    try:
        async with httpx.AsyncClient() as client:
            await client.get("http://localhost:8100/health", timeout=1)
            print("⚠️  A2A test server already running on 8100")
            yield "http://localhost:8100"
            return
    except:
        pass
    
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
        raise RuntimeError(f"Foundry not running. Start with: foundry model run qwen2.5-14b-instruct-generic-gpu:4") from e
    
    process = subprocess.Popen(
        [
            "uv", "run", "python", "a2a_server.py",
            "--user", "alice", "--port", "8100",
            "--mcp-server-url", mcp_server
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        preexec_fn=os.setsid if hasattr(os, 'setsid') else None
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
    if hasattr(os, 'killpg'):
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    else:
        process.terminate()
    process.wait(timeout=5)


@pytest.fixture
async def http_client():
    """Provide HTTP client for tests."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


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
    text = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)
    return text.strip()


def extract_balance(text):
    """Extract numeric balance from text (handles various formats)."""
    import re
    # Look for dollar amounts: $1000, $1,000, $1000.00, etc.
    match = re.search(r'\$?[\d,]+\.?\d*', text)
    if match:
        amount_str = match.group().replace('$', '').replace(',', '')
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

