import os
import shutil
from identity import IdentityManager
from ledger import LedgerEngine


def bootstrap():
    print("--- 42 Bank Bootstrap (Checking Accounts Only) ---")

    # 1. Reset data
    if os.path.exists("data"):
        shutil.rmtree("data")
    os.makedirs("data/keys", exist_ok=True)

    identity = IdentityManager()
    ledger = LedgerEngine()

    # 2. Setup Alice (checking account only)
    t_alice = identity.create_identity("alice")
    pk_alice = identity.get_public_key("alice")
    if pk_alice:
        ledger.register_user(t_alice, "alice", pk_alice.hex(), 1000.0)

    # 3. Setup Bob (checking account only)
    t_bob = identity.create_identity("bob")
    pk_bob = identity.get_public_key("bob")
    if pk_bob:
        ledger.register_user(t_bob, "bob", pk_bob.hex(), 500.0)

    # 4. Sample Transactions
    ledger.transfer(t_alice, "bob", 50.0, "Lunch money")
    ledger.transfer(t_bob, "alice", 25.0, "Coffee")

    print(f"✅ Alice: ${ledger.get_balance(t_alice, 'checking'):.2f} (checking)")
    print(f"✅ Bob: ${ledger.get_balance(t_bob, 'checking'):.2f} (checking)")
    print("Bootstrap Complete!")


if __name__ == "__main__":
    bootstrap()
