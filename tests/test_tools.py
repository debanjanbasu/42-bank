import os
import pytest
import shutil
from ledger import LedgerEngine
from identity import IdentityManager
from tools import BankingTools


@pytest.fixture
def setup_bank():
    test_db = "data/test_bank_tools.db"
    test_keys = "data/test_keys_tools"
    if os.path.exists(test_db):
        os.remove(test_db)
    if os.path.exists(test_keys):
        shutil.rmtree(test_keys)

    ledger = LedgerEngine(db_path=test_db)
    identity = IdentityManager(keys_dir=test_keys)

    # Create Alice
    token = identity.create_identity("alice")
    pk = identity.get_public_key("alice")
    if pk:
        ledger.register_user(token, "alice", pk.hex(), 1000.0)

    tools = BankingTools(ledger, identity, "alice", token)
    yield tools, ledger, identity

    if os.path.exists(test_db):
        os.remove(test_db)
    if os.path.exists(test_keys):
        shutil.rmtree(test_keys)


def test_tool_balance(setup_bank):
    tools, _, _ = setup_bank
    res = tools.check_balance()
    assert "$1000.00" in res


def test_tool_transfer(setup_bank):
    tools, ledger, identity = setup_bank
    # Create Bob
    tB = identity.create_identity("bob")
    pkB = identity.get_public_key("bob")
    if pkB:
        ledger.register_user(tB, "bob", pkB.hex(), 0.0)

    # Payload in tools: f"{to}{amount}{note}"
    # Payload in ledger: f"{recipient_username}{amount}{description}"
    res = tools.send_money("bob", 100.0, "rent")
    assert "SUCCESS" in res
    assert ledger.get_balance(tools.session_token) == 900.0


def test_tool_products(setup_bank):
    tools, _, _ = setup_bank
    res = tools.list_products()
    assert "Bank Products" in res
    assert "Standard Checking" in res
