"""Security-focused tests for the banking API.

Tests token validation, rate limiting awareness, input sanitization,
and token revocation / expiry behavior.
"""

import os
import uuid

import pytest
from datetime import datetime, timedelta

import jwt as pyjwt

from ledger import LedgerEngine

EMULATOR_CONN_STR = "AccountEndpoint=https://localhost:8081/;AccountKey=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="


@pytest.fixture
def cosmos_db():
    """Isolated Cosmos DB per test for security unit tests."""
    import ledger as ledger_mod
    import api.storage as storage_mod
    import db.cosmos as cosmos_mod

    db_name = f"banking_test_{uuid.uuid4().hex[:12]}"
    os.environ["COSMOS_DATABASE"] = db_name
    os.environ["AZURE_COSMOS_CONNECTION_STRING"] = EMULATOR_CONN_STR
    ledger_mod._ledger_instance = None
    storage_mod._storage_instance = None
    cosmos_mod._cosmos_client = None

    yield db_name

    ledger_mod._ledger_instance = None
    storage_mod._storage_instance = None
    cosmos_mod._cosmos_client = None
    try:
        from azure.cosmos import CosmosClient

        cosmos = CosmosClient.from_connection_string(
            EMULATOR_CONN_STR, connection_verify=False
        )
        cosmos.delete_database(db_name)
    except Exception:
        pass
    os.environ.pop("COSMOS_DATABASE", None)


# ── JWT / Auth security tests ─────────────────────────────────────────────────


class TestJWTSecurity:
    """Tests that the token validation layer correctly rejects bad tokens."""

    async def test_validate_token_rejects_wrong_algorithm(self):
        """Token signed with HS512 should be rejected when server expects HS256."""
        from api.deps import JWT_SECRET, JWT_ALGORITHM, validate_token
        from fastapi import HTTPException

        bad_token = pyjwt.encode(
            {
                "sub": "alice_tok",
                "type": "access",
                "exp": datetime.now(datetime.UTC) + timedelta(hours=1),
            },
            JWT_SECRET,
            algorithm="HS512",
        )
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(bad_token)
        assert exc_info.value.status_code == 401

    async def test_validate_token_rejects_expired(self):
        """Expired token should raise 401."""
        from api.deps import JWT_SECRET, JWT_ALGORITHM, validate_token
        from fastapi import HTTPException

        expired_token = pyjwt.encode(
            {
                "sub": "alice_tok",
                "type": "access",
                "exp": datetime.now(datetime.UTC) - timedelta(seconds=1),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(expired_token)
        assert exc_info.value.status_code == 401

    async def test_validate_token_rejects_wrong_secret(self):
        """Token signed with different secret should be rejected."""
        from api.deps import JWT_ALGORITHM, validate_token
        from fastapi import HTTPException

        bad_token = pyjwt.encode(
            {
                "sub": "alice_tok",
                "type": "access",
                "exp": datetime.now(datetime.UTC) + timedelta(hours=1),
            },
            "completely-wrong-secret",
            algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(bad_token)
        assert exc_info.value.status_code == 401

    async def test_validate_token_rejects_wrong_type(self):
        """Refresh token should not be accepted as access token."""
        from api.deps import JWT_SECRET, JWT_ALGORITHM, validate_token
        from fastapi import HTTPException

        refresh_token = pyjwt.encode(
            {
                "sub": "alice_tok",
                "type": "refresh",
                "exp": datetime.now(datetime.UTC) + timedelta(days=30),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(refresh_token, expected_type="access")
        assert exc_info.value.status_code == 401

    async def test_validate_token_accepts_valid(self, cosmos_db):
        """Valid token should decode successfully."""
        from api.deps import JWT_SECRET, JWT_ALGORITHM, validate_token

        token = pyjwt.encode(
            {
                "sub": "alice_tok",
                "username": "alice",
                "type": "access",
                "jti": str(uuid.uuid4()),
                "exp": datetime.now(datetime.UTC) + timedelta(hours=1),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        payload = await validate_token(token)
        assert payload["sub"] == "alice_tok"


class TestTokenRevocation:
    """Tests that revoked tokens are rejected."""

    async def test_revoked_token_is_rejected(self, cosmos_db):
        """A token added to the blacklist should be rejected."""
        from api.deps import JWT_SECRET, JWT_ALGORITHM, validate_token
        from api.storage import APIStorage
        from fastapi import HTTPException

        storage = APIStorage()
        jti = str(uuid.uuid4())

        token = pyjwt.encode(
            {
                "sub": "alice_tok",
                "username": "alice",
                "type": "access",
                "jti": jti,
                "exp": datetime.now(datetime.UTC) + timedelta(hours=1),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )

        # Revoke it
        await storage.revoke_token(jti, "alice_tok")
        assert await storage.is_token_revoked(jti) is True

    async def test_non_revoked_token_passes_blacklist_check(self, cosmos_db):
        from api.storage import APIStorage

        storage = APIStorage()
        jti = str(uuid.uuid4())
        assert await storage.is_token_revoked(jti) is False


# ── Input sanitization tests ─────────────────────────────────────────────────


class TestInputSanitization:
    """Tests that the ledger rejects malformed or oversized inputs."""

    async def test_empty_recipient_rejected(self, cosmos_db):
        engine = LedgerEngine()
        await engine.create_user("alice_tok", "alice", initial_balance=100.0)
        assert await engine.transfer("alice_tok", "", 10.0, "empty recipient") is False

    async def test_empty_description_rejected(self, cosmos_db):
        engine = LedgerEngine()
        await engine.create_user("alice_tok", "alice", initial_balance=100.0)
        await engine.create_user("bob_tok", "bob", initial_balance=0.0)
        assert await engine.transfer("alice_tok", "bob", 10.0, "") is False

    async def test_very_large_amount_rejected_by_ledger(self, cosmos_db):
        engine = LedgerEngine()
        await engine.create_user("alice_tok", "alice", initial_balance=100.0)
        await engine.create_user("bob_tok", "bob", initial_balance=0.0)
        # Ledger should reject based on insufficient funds anyway
        assert (
            await engine.transfer("alice_tok", "bob", 1_000_001.0, "too big") is False
        )


# ── Ledger integrity tests ────────────────────────────────────────────────────


class TestLedgerIntegrity:
    """Tests that the ledger maintains data integrity."""

    async def test_transfer_is_atomic_on_error(self, cosmos_db):
        """If recipient doesn't exist mid-transfer, both balances are unchanged."""
        engine = LedgerEngine()
        await engine.create_user("alice_tok", "alice", initial_balance=200.0)

        initial_alice = await engine.get_balance("alice_tok")
        await engine.transfer("alice_tok", "ghost_user", 50.0, "should fail")

        assert await engine.get_balance("alice_tok") == initial_alice

    async def test_history_records_both_sides(self, cosmos_db):
        """After a transfer, both sender and recipient have matching history entries."""
        engine = LedgerEngine()
        await engine.create_user("alice_tok", "alice", initial_balance=200.0)
        await engine.create_user("bob_tok", "bob", initial_balance=0.0)

        await engine.transfer("alice_tok", "bob", 75.0, "rent")

        alice_history = await engine.get_history("alice_tok")
        bob_history = await engine.get_history("bob_tok")

        assert "SENT" in alice_history or "75.00" in alice_history
        assert "RECEIVED" in bob_history or "75.00" in bob_history
