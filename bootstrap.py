import os
import shutil
from identity import IdentityManager
from ledger import LedgerEngine


def bootstrap():
    print("--- 42 Bank Bootstrap (Quantum-Safe & SQLite) ---")

    # 1. Reset data
    if os.path.exists("data"):
        shutil.rmtree("data")
    os.makedirs("data/keys", exist_ok=True)

    identity = IdentityManager()
    ledger = LedgerEngine()

    # 2. Setup Alice
    t_alice = identity.create_identity("alice")
    pk_alice = identity.get_public_key("alice")
    if pk_alice:
        ledger.register_user(t_alice, "alice", pk_alice.hex(), 1000.0)
        ledger.open_account(t_alice, "savings")

    # 3. Setup Bob
    t_bob = identity.create_identity("bob")
    pk_bob = identity.get_public_key("bob")
    if pk_bob:
        ledger.register_user(t_bob, "bob", pk_bob.hex(), 500.0)

    # 4. Genesis Transactions
    ledger.transfer(t_alice, "bob", 10.0, "Initial coffee debt payment")
    ledger.transfer(t_bob, "alice", 5.0, "Cool 42 sticker")

    print(f"Alice's Token: {t_alice[:16]}...")
    print(f"Bob's Token: {t_bob[:16]}...")
    print("Bootstrap Complete!")


if __name__ == "__main__":
    bootstrap()
