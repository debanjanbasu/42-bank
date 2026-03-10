"""Error path and edge case tests for MCP tools and ledger.

These tests verify that failure conditions are handled correctly —
insufficient funds, invalid users, bad inputs, concurrent operations.
"""

import os
import uuid

import pytest

from ledger import LedgerEngine, AccountType

EMULATOR_CONN_STR = "AccountEndpoint=https://localhost:8081/;AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="


# ── Ledger unit tests (no server needed) ─────────────────────────────────────


@pytest.fixture
async def ledger():
    """Fresh isolated Cosmos ledger for each test."""
    import ledger as ledger_mod
    import db.cosmos as cosmos_mod

    db_name = f"banking_test_{uuid.uuid4().hex[:12]}"
    os.environ["COSMOS_DATABASE"] = db_name
    os.environ["AZURE_COSMOS_CONNECTION_STRING"] = EMULATOR_CONN_STR
    ledger_mod._ledger_instance = None
    cosmos_mod._cosmos_client = None

    engine = LedgerEngine()
    await engine.create_user("alice_tok", "alice", initial_balance=500.0)
    await engine.create_user("bob_tok", "bob", initial_balance=200.0)

    yield engine

    ledger_mod._ledger_instance = None
    cosmos_mod._cosmos_client = None
    try:
        from azure.cosmos import CosmosClient
        cosmos = CosmosClient.from_connection_string(EMULATOR_CONN_STR, connection_verify=False)
        cosmos.delete_database(db_name)
    except Exception:
        pass
    os.environ.pop("COSMOS_DATABASE", None)


class TestTransferErrors:
    async def test_insufficient_funds_returns_false(self, ledger):
        result = await ledger.transfer("alice_tok", "bob", 9999.0, "too much")
        assert result is False

    async def test_transfer_negative_amount(self, ledger):
        result = await ledger.transfer("alice_tok", "bob", -50.0, "negative")
        assert result is False

    async def test_transfer_zero_amount(self, ledger):
        result = await ledger.transfer("alice_tok", "bob", 0.0, "zero")
        assert result is False

    async def test_transfer_to_nonexistent_user(self, ledger):
        result = await ledger.transfer("alice_tok", "nonexistent", 10.0, "ghost")
        assert result is False

    async def test_transfer_with_invalid_sender_token(self, ledger):
        result = await ledger.transfer("bad_token", "bob", 10.0, "no sender")
        assert result is False

    async def test_transfer_to_self_same_account(self, ledger):
        result = await ledger.transfer("alice_tok", "alice", 10.0, "self transfer")
        assert result is False

    async def test_balance_unchanged_after_failed_transfer(self, ledger):
        initial = await ledger.get_balance("alice_tok")
        await ledger.transfer("alice_tok", "bob", 99999.0, "fail")
        assert await ledger.get_balance("alice_tok") == initial

    async def test_successful_transfer_debits_sender(self, ledger):
        await ledger.transfer("alice_tok", "bob", 100.0, "test")
        assert await ledger.get_balance("alice_tok") == 400.0

    async def test_successful_transfer_credits_recipient(self, ledger):
        await ledger.transfer("alice_tok", "bob", 100.0, "test")
        assert await ledger.get_balance("bob_tok") == 300.0


class TestUserErrors:
    async def test_get_nonexistent_user_returns_none(self, ledger):
        assert await ledger.get_user("no_such_token") is None

    async def test_create_duplicate_username_returns_false(self, ledger):
        assert await ledger.create_user("new_tok", "alice") is False

    async def test_get_balance_unknown_token_returns_zero(self, ledger):
        assert await ledger.get_balance("ghost_token") == 0.0

    async def test_get_history_unknown_account_type(self, ledger):
        result = await ledger.get_history("alice_tok", "nonexistent_account")
        assert "not found" in result.lower()


class TestPaymentRequests:
    async def test_approve_nonexistent_request(self, ledger):
        result = await ledger.approve_request("alice_tok", "bad_request_id")
        assert result is False

    async def test_request_from_nonexistent_user(self, ledger):
        result = await ledger.request_funds("alice_tok", "ghost", 50.0, "pay me")
        assert result is False

    async def test_request_negative_amount(self, ledger):
        result = await ledger.request_funds("alice_tok", "bob", -10.0, "negative")
        assert result is False

    async def test_approve_request_insufficient_funds(self, ledger):
        # Bob requests way more than alice has
        await ledger.request_funds("bob_tok", "alice", 50000.0, "huge request")
        requests = await ledger.get_pending_requests("alice_tok")
        assert len(requests) == 1
        result = await ledger.approve_request("alice_tok", requests[0]["id"])
        assert result is False
        # Alice's balance should be unchanged
        assert await ledger.get_balance("alice_tok") == 500.0


class TestAccountManagement:
    async def test_open_duplicate_account_returns_true_no_reset(self, ledger):
        await ledger.transfer("alice_tok", "bob", 100.0, "spend some")
        result = await ledger.open_account("alice_tok", AccountType.CHECKING)
        assert result is True
        # Balance should NOT reset to 0
        assert await ledger.get_balance("alice_tok") == 400.0

    async def test_open_account_unknown_token(self, ledger):
        result = await ledger.open_account("ghost", "savings")
        assert result is False


class TestConcurrentTransfers:
    async def test_concurrent_transfers_do_not_overdraw(self, ledger):
        """Verify atomic transfers prevent overdraft under concurrent async access."""
        import asyncio

        engine = ledger
        await engine.create_user("conc_alice", "conc_alice_user", initial_balance=100.0)
        await engine.create_user("conc_bob", "conc_bob_user", initial_balance=0.0)

        async def attempt_transfer():
            return await engine.transfer("conc_alice", "conc_bob_user", 60.0, "concurrent")

        results = await asyncio.gather(*[attempt_transfer() for _ in range(5)], return_exceptions=True)
        bool_results = [r for r in results if isinstance(r, bool)]

        successes = sum(bool_results)
        # Only 1 transfer of $60 can succeed from a $100 balance
        assert successes <= 1
        final_balance = await engine.get_balance("conc_alice")
        assert final_balance >= 0.0


# ── MCP tool error paths (via server) ────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_send_money_insufficient_funds(mcp_server, test_db):
    """Tool should return FAILED message, not raise."""
    from agent_framework import MCPStreamableHTTPTool

    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True,
    )
    async with mcp_tool:
        result = await mcp_tool.call_tool(
            "send_money", to="bob", amount=999999.0, note="too much"
        )
    assert "FAILED" in result or "insufficient" in result.lower()


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_send_money_nonexistent_recipient(mcp_server, test_db):
    """Tool should return FAILED for unknown recipient."""
    from agent_framework import MCPStreamableHTTPTool

    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True,
    )
    async with mcp_tool:
        result = await mcp_tool.call_tool(
            "send_money",
            to="ghost_user_xyz", amount=1.0, note="test",
        )
    assert "FAILED" in result or "not found" in result.lower()


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_send_money_negative_amount(mcp_server, test_db):
    """Tool should reject negative amount."""
    from agent_framework import MCPStreamableHTTPTool

    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True,
    )
    async with mcp_tool:
        result = await mcp_tool.call_tool(
            "send_money", to="bob", amount=-100.0, note="negative"
        )
    assert "FAILED" in result


@pytest.mark.asyncio
@pytest.mark.mcp
async def test_open_invalid_account_type(mcp_server, test_db):
    """Tool should reject unknown account type."""
    from agent_framework import MCPStreamableHTTPTool

    mcp_tool = MCPStreamableHTTPTool(
        name="banking-tools",
        url=f"{mcp_server}/mcp",
        load_tools=True,
    )
    async with mcp_tool:
        result = await mcp_tool.call_tool(
            "open_new_account", arguments={"account_type": "invalid_type_xyz"}
        )
    assert "FAILED" in result or "invalid" in result.lower()
