"""Enhanced bootstrap for hackathon demo with 5 users and realistic transactions."""

import asyncio

from api.storage import APIStorage
from identity import IdentityManager
from ledger import LedgerEngine

# Users with varied balances for demo impact
USERS = [
    ("alice", 2500.0),
    ("bob", 1200.0),
    ("charlie", 5000.0),
    ("diana", 750.0),
    ("eve", 10000.0),
]

# Realistic transactions showing money flow
TRANSACTIONS = [
    # Alice sends money
    ("alice", "bob", 50.0, "Lunch at restaurant"),
    ("alice", "charlie", 100.0, "Concert tickets"),
    ("alice", "diana", 25.0, "Coffee"),
    # Bob sends money
    ("bob", "eve", 200.0, "Freelance payment"),
    ("bob", "alice", 30.0, "Coffee reimbursement"),
    # Charlie sends money
    ("charlie", "alice", 500.0, "Investment return"),
    ("charlie", "bob", 75.0, "Dinner split"),
    # Diana sends money
    ("diana", "eve", 150.0, "Textbook sale"),
    # Eve sends money
    ("eve", "charlie", 1000.0, "Consulting fee"),
    ("eve", "diana", 200.0, "Scholarship"),
]


async def bootstrap_hackathon():
    """Bootstrap hackathon demo data with 5 users and realistic transactions."""
    print("--- 42 Bank Hackathon Bootstrap ---")
    print("")

    # Initialize storage and ledger
    ledger = LedgerEngine()
    APIStorage()

    # Create users
    print("👥 Creating users...")
    for username, balance in USERS:
        user = await ledger.get_user_by_username(username)
        if not user:
            identity = IdentityManager()
            token = identity.create_identity(username)
            pk = identity.get_public_key(username)
            if pk:
                await ledger.register_user(token, username, pk.hex(), balance)
                print(f"  🆕 Created {username} with ${balance:.2f}")
        else:
            print(f"  👤 User {username} exists")

    # Create transactions
    print("\n💸 Creating transactions...")
    success_count = 0
    fail_count = 0

    for sender, recipient, amount, desc in TRANSACTIONS:
        sender_user = await ledger.get_user_by_username(sender)
        if sender_user:
            try:
                await ledger.transfer(sender_user.token, recipient, amount, desc)
                print(f"  ✅ ${amount:.2f} {sender} → {recipient}: {desc}")
                success_count += 1
            except Exception as e:
                print(f"  ⚠️  Failed: {sender} → {recipient} ({e})")
                fail_count += 1
        else:
            print(f"  ❌ Sender {sender} not found")
            fail_count += 1

    # Show final balances
    print("\n✅ Final Balances:")
    for username, _ in USERS:
        user = await ledger.get_user_by_username(username)
        if user:
            balance = await ledger.get_balance(user.token)
            print(f"  {username}: ${balance:.2f}")

    print(f"\n✨ Hackathon Bootstrap Complete!")
    print(f"   Success: {success_count} transactions")
    print(f"   Failed: {fail_count} transactions")


if __name__ == "__main__":
    asyncio.run(bootstrap_hackathon())
