import os
import pytest
from ledger import LedgerEngine


@pytest.fixture
def ledger():
    test_db = "data/test_bank_multi.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    engine = LedgerEngine(db_path=test_db)
    yield engine
    if os.path.exists(test_db):
        os.remove(test_db)


def test_multi_account_registration(ledger):
    token = "token123"
    ledger.register_user(token, "alice", "pk1", 1000.0)
    ledger.open_account(token, "savings")

    assert ledger.get_balance(token, "checking") == 1000.0
    assert ledger.get_balance(token, "savings") == 0.0


def test_multi_account_transfer(ledger):
    t1, t2 = "t1", "t2"
    ledger.register_user(t1, "alice", "pkA", 100.0)
    ledger.register_user(t2, "bob", "pkB", 0.0)
    ledger.open_account(t2, "savings")

    # Alice checking -> Bob savings
    success = ledger.transfer(
        t1, "bob", 50.0, "gift", from_account="checking", to_account="savings"
    )
    assert success is True
    assert ledger.get_balance(t1, "checking") == 50.0
    assert ledger.get_balance(t2, "savings") == 50.0
    assert ledger.get_balance(t2, "checking") == 0.0


def test_request_and_approve_pqc(ledger):
    alice, bob = "A", "B"
    ledger.register_user(alice, "alice", "pkA", 100.0)
    ledger.register_user(bob, "bob", "pkB", 10.0)

    ledger.request_funds(alice, "bob", 5.0, "coffee")
    reqs = ledger.get_pending_requests(bob)
    rid = reqs[0]["id"]

    # Bob approves
    success = ledger.approve_request(bob, rid)
    assert success is True
    assert ledger.get_balance(bob) == 5.0
    assert ledger.get_balance(alice) == 105.0
