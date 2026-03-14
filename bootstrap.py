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

    # Get or create users in ledger
    alice_user = await ledger.get_user_by_username("alice")
    bob_user = await ledger.get_user_by_username("bob")

    # If users don't exist, create them with initial balances
    if not alice_user:
        identity = IdentityManager()
        t_alice = identity.create_identity("alice")
        pk_alice = identity.get_public_key("alice")
        if pk_alice:
            await ledger.register_user(t_alice, "alice", pk_alice.hex(), 1000.0)
            alice_user = await ledger.get_user_by_username("alice")
            print("🆕 Created Alice with $1000")

    if not bob_user:
        identity = IdentityManager()
        t_bob = identity.create_identity("bob")
        pk_bob = identity.get_public_key("bob")
        if pk_bob:
            await ledger.register_user(t_bob, "bob", pk_bob.hex(), 500.0)
            bob_user = await ledger.get_user_by_username("bob")
            print("🆕 Created Bob with $500")

    # If users exist, skip creation message
    if alice_user and bob_user:
        print("👥 Users alice and bob already exist")

    # Sample transactions (only if both users exist)
    if alice_user and bob_user:
        await ledger.transfer(alice_user.token, "bob", 50.0, "Lunch money")
        await ledger.transfer(bob_user.token, "alice", 25.0, "Coffee")
        print("💸 Sample transactions completed")

    # Get final balances
    alice_balance = await ledger.get_balance(alice_user.token) if alice_user else 0
    bob_balance = await ledger.get_balance(bob_user.token) if bob_user else 0

    print(f"✅ Alice: ${alice_balance:.2f} (checking)")
    print(f"✅ Bob: ${bob_balance:.2f} (checking)")
    print("Bootstrap Complete!")


if __name__ == "__main__":
    asyncio.run(bootstrap())
