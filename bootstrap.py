"""Creates all Cosmos DB containers and seeds initial alice/bob accounts."""

import asyncio

from api.storage import APIStorage
from identity import IdentityManager
from ledger import LedgerEngine


async def bootstrap():
    print("--- 42 Bank Bootstrap (Cosmos DB) ---")

    # LedgerEngine._init_db creates: users, change_feed, products
    ledger = LedgerEngine()
    # APIStorage._init_db creates: auth_devices, key_backups, restore_challenges, token_blacklist
    APIStorage()

    identity = IdentityManager()

    # Setup Alice
    t_alice = identity.get_token("alice") or identity.create_identity("alice")
    pk_alice = identity.get_public_key("alice")
    if pk_alice:
        await ledger.register_user(t_alice, "alice", pk_alice.hex(), 1000.0)

    # Setup Bob
    t_bob = identity.get_token("bob") or identity.create_identity("bob")
    pk_bob = identity.get_public_key("bob")
    if pk_bob:
        await ledger.register_user(t_bob, "bob", pk_bob.hex(), 500.0)

    # Sample transactions
    await ledger.transfer(t_alice, "bob", 50.0, "Lunch money")
    await ledger.transfer(t_bob, "alice", 25.0, "Coffee")

    print(f"✅ Alice: ${await ledger.get_balance(t_alice, 'checking'):.2f} (checking)")
    print(f"✅ Bob: ${await ledger.get_balance(t_bob, 'checking'):.2f} (checking)")
    print("Bootstrap Complete!")


if __name__ == "__main__":
    asyncio.run(bootstrap())
