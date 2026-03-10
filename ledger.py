import asyncio
import hashlib
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from azure.core import MatchConditions
from azure.core.exceptions import ResourceModifiedError
from azure.cosmos import PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from pydantic import BaseModel, Field

from audit_service import AuditLogger
from db.cosmos import get_async_container, get_container, get_database


class AccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"


class Transaction(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    sender: str
    recipient: str
    amount: float
    description: str
    account_type: str = AccountType.CHECKING


class AccountData(BaseModel):
    balance: float = 0.0
    history: List[Transaction] = Field(default_factory=list)


class UserAccount(BaseModel):
    token: str
    username: str
    public_key: Optional[str] = None
    accounts: Dict[str, AccountData] = Field(
        default_factory=lambda: {
            AccountType.CHECKING: AccountData(balance=0.0),
            AccountType.SAVINGS: AccountData(balance=0.0),
        }
    )
    pending_requests: List[Dict[str, Any]] = Field(default_factory=list)


class Product(BaseModel):
    id: str
    name: str
    type: str  # checking, saving, loan, mortgage, credit_card
    interest_rate: float
    description: str


_SEED_PRODUCTS = [
    {"id": "p0", "name": "Standard Checking", "type": "checking", "interest_rate": 0.0, "description": "Default everyday account."},
    {"id": "p1", "name": "High-Yield Savings", "type": "saving", "interest_rate": 4.5, "description": "Earn 4.5% interest."},
    {"id": "p2", "name": "Home Mortgage", "type": "mortgage", "interest_rate": 3.8, "description": "30-year fixed rate."},
    {"id": "p3", "name": "Express Auto Loan", "type": "loan", "interest_rate": 5.9, "description": "Instant car financing."},
    {"id": "p4", "name": "Infinite Rewards Card", "type": "credit_card", "interest_rate": 15.4, "description": "2% cashback."},
]


class LedgerEngine:
    def __init__(self) -> None:
        self._audit = AuditLogger()
        self._init_db()

    def _init_db(self) -> None:
        db = get_database()
        for container_name, partition_path in [
            ("users", "/username"),
            ("change_feed", "/event_type"),
            ("products", "/type"),
        ]:
            db.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path=partition_path),
                offer_throughput=400,
            )

        products_c = get_container("products")
        try:
            products_c.read_item(item="p0", partition_key="checking")
        except CosmosResourceNotFoundError:
            for product in _SEED_PRODUCTS:
                products_c.upsert_item(product)

    @staticmethod
    def _doc_to_user(doc: Dict[str, Any]) -> UserAccount:
        return UserAccount.model_validate({
            "token": doc["id"],
            "username": doc["username"],
            "public_key": doc.get("public_key"),
            "accounts": doc.get("accounts", {}),
            "pending_requests": doc.get("pending_requests", []),
        })

    @staticmethod
    def _user_to_doc(user: UserAccount) -> Dict[str, Any]:
        return {
            "id": user.token,
            "username": user.username,
            "public_key": user.public_key,
            "accounts": user.model_dump()["accounts"],
            "pending_requests": user.pending_requests,
        }

    async def _get_user(self, token: str) -> Optional[UserAccount]:
        if not token:
            return None
        container = get_async_container("users")
        items: list[Dict[str, Any]] = []
        async for item in container.query_items(
            query="SELECT * FROM c WHERE c.id = @token",
            parameters=[{"name": "@token", "value": token}],
            enable_cross_partition_query=True,
        ):
            items.append(item)
        return self._doc_to_user(items[0]) if items else None

    async def _get_user_doc(self, token: str) -> Optional[Dict[str, Any]]:
        """Return raw Cosmos document (includes _etag) for the given token."""
        if not token:
            return None
        container = get_async_container("users")
        items: list[Dict[str, Any]] = []
        async for item in container.query_items(
            query="SELECT * FROM c WHERE c.id = @token",
            parameters=[{"name": "@token", "value": token}],
            enable_cross_partition_query=True,
        ):
            items.append(item)
        return items[0] if items else None

    async def get_user(self, token: str) -> Optional[UserAccount]:
        return await self._get_user(token)

    async def get_user_by_username(self, username: str) -> Optional[UserAccount]:
        if not username:
            return None
        container = get_async_container("users")
        items: list[Dict[str, Any]] = []
        async for item in container.query_items(
            query="SELECT * FROM c WHERE c.username = @u",
            parameters=[{"name": "@u", "value": username}],
            enable_cross_partition_query=True,
        ):
            items.append(item)
        return self._doc_to_user(items[0]) if items else None

    async def _save_user(self, user: Optional[UserAccount]) -> None:
        if not user:
            return
        await get_async_container("users").upsert_item(self._user_to_doc(user))

    async def create_user(
        self,
        token: str,
        username: str,
        initial_balance: float = 0.0,
        public_key: Optional[str] = None,
    ) -> bool:
        if not token or not username:
            return False
        if await self.get_user_by_username(username):
            return False
        user = UserAccount(token=token, username=username, public_key=public_key)
        user.accounts["checking"].balance = max(initial_balance, 0.0)
        await self._save_user(user)
        return True

    async def register_user(
        self,
        token: str,
        username: str,
        public_key_hex: str,
        initial_balance: float = 0.0,
    ) -> None:
        user = await self._get_user(token)
        if not user:
            await self.create_user(
                token=token,
                username=username,
                initial_balance=initial_balance,
                public_key=public_key_hex,
            )
            return

        user.public_key = public_key_hex
        if user.accounts["checking"].balance == 0.0:
            user.accounts["checking"].balance = initial_balance
        await self._save_user(user)

    async def get_balance(self, token: str, account_type: str = "checking") -> float:
        user = await self._get_user(token)
        return user.accounts.get(account_type, AccountData()).balance if user else 0.0

    async def get_username(self, token: str) -> str:
        user = await self._get_user(token)
        return user.username if user else "Unknown"

    async def get_token_by_username(self, username: str) -> Optional[str]:
        if not username:
            return None
        container = get_async_container("users")
        items: list[Dict[str, Any]] = []
        async for item in container.query_items(
            query="SELECT c.id FROM c WHERE c.username = @u",
            parameters=[{"name": "@u", "value": username}],
            enable_cross_partition_query=True,
        ):
            items.append(item)
        return items[0]["id"] if items else None

    async def _verify_signature(self, token: str, message: str, signature_hex: str) -> bool:
        from pqcrypto.sign.ml_dsa_44 import verify as pq_verify

        user = await self._get_user(token)
        if not user or not user.public_key:
            return False
        try:
            return bool(
                pq_verify(
                    bytes.fromhex(user.public_key),
                    message.encode(),
                    bytes.fromhex(signature_hex),
                )
            )
        except Exception:
            return False

    async def transfer(
        self,
        sender_token: str,
        recipient_username: str,
        amount: float,
        description: str,
        from_account: str = "checking",
        to_account: str = "checking",
        signature: Optional[str] = None,
    ) -> bool:
        """Transfer funds with optimistic concurrency on the sender document."""
        if amount <= 0 or not recipient_username or not description:
            return False

        if signature and not await self._verify_signature(
            sender_token, f"{recipient_username}{amount}{description}", signature
        ):
            return False

        users_container = get_async_container("users")

        sender_doc = await self._get_user_doc(sender_token)
        if not sender_doc:
            return False
        sender_etag = sender_doc.get("_etag")

        recipient_docs: list[Dict[str, Any]] = []
        async for item in users_container.query_items(
            query="SELECT * FROM c WHERE c.username = @u",
            parameters=[{"name": "@u", "value": recipient_username}],
            enable_cross_partition_query=True,
        ):
            recipient_docs.append(item)
        if not recipient_docs:
            return False
        recipient_doc = recipient_docs[0]

        s_user = self._doc_to_user(sender_doc)
        r_user = self._doc_to_user(recipient_doc)

        if sender_token == r_user.token and from_account == to_account:
            return False
        if from_account not in s_user.accounts or to_account not in r_user.accounts:
            return False
        if s_user.accounts[from_account].balance < amount:
            return False

        tx = Transaction(
            sender=s_user.username,
            recipient=r_user.username,
            amount=amount,
            description=description,
            account_type=from_account,
        )
        s_user.accounts[from_account].balance -= amount
        s_user.accounts[from_account].history.append(tx)
        r_user.accounts[to_account].balance += amount
        r_user.accounts[to_account].history.append(tx)

        try:
            await users_container.upsert_item(
                body=self._user_to_doc(s_user),
                match_condition=MatchConditions.IfNotModified,
                etag=sender_etag,
            )
            await users_container.upsert_item(body=self._user_to_doc(r_user))
            await self._audit.log_transfer(
                sender=s_user.username,
                recipient=r_user.username,
                amount=amount,
                success=True,
                description=description,
            )
            return True
        except ResourceModifiedError:
            await self._audit.log_transfer(
                sender=s_user.username,
                recipient=r_user.username,
                amount=amount,
                success=False,
                description=description,
            )
            return False

    async def open_account(self, token: str, account_type: str) -> bool:
        user = await self._get_user(token)
        if not user or account_type in user.accounts:
            return bool(user)
        user.accounts[account_type] = AccountData()
        await self._save_user(user)
        return True

    async def request_funds(
        self, requester_token: str, target_username: str, amount: float, note: str
    ) -> bool:
        """Create a payment request from target user."""
        if amount <= 0:
            return False

        req_user = await self._get_user(requester_token)
        if not req_user:
            return False

        target_token = await self.get_token_by_username(target_username)
        if not target_token:
            return False
        tar_user = await self._get_user(target_token)
        if not tar_user:
            return False

        req_id = hashlib.sha256(
            f"{req_user.username}{datetime.now().isoformat()}{amount}".encode()
        ).hexdigest()[:8]

        tar_user.pending_requests.append({
            "id": req_id,
            "requester": req_user.username,
            "amount": amount,
            "note": note,
            "timestamp": datetime.now().isoformat(),
        })
        await self._save_user(tar_user)
        return True

    async def get_pending_requests(self, token: str) -> List[Dict[str, Any]]:
        user = await self._get_user(token)
        return user.pending_requests if user else []

    async def approve_request(
        self, token: str, request_id: str, signature: Optional[str] = None
    ) -> bool:
        user = await self._get_user(token)
        if not user:
            return False
        for req in user.pending_requests:
            if req["id"] == request_id:
                if signature and not await self._verify_signature(
                    token, f"APPROVE{request_id}", signature
                ):
                    return False
                if await self.transfer(
                    token, req["requester"], req["amount"], f"Approved: {req['note']}"
                ):
                    # Re-read after transfer so balance is current
                    updated = await self._get_user(token)
                    if updated:
                        updated.pending_requests = [
                            r for r in updated.pending_requests if r["id"] != request_id
                        ]
                        await self._save_user(updated)
                    return True
        return False

    async def get_history(self, token: str, account_type: str = "checking") -> str:
        user = await self._get_user(token)
        if not user or account_type not in user.accounts:
            return "Account not found."
        history = user.accounts[account_type].history
        if not history:
            return "No transactions found."

        lines = []
        for tx in history:
            is_sender = tx.sender.lower() == user.username.lower()
            if is_sender:
                lines.append(
                    f"- {tx.timestamp[:16]} SENT ${tx.amount:.2f} to {tx.recipient} - {tx.description}"
                )
            else:
                lines.append(
                    f"- {tx.timestamp[:16]} RECEIVED ${tx.amount:.2f} from {tx.sender} - {tx.description}"
                )
        return "\n".join(lines)

    async def list_user_accounts(self, token: str) -> str:
        user = await self._get_user(token)
        if not user:
            return "User not found."
        return "\n".join(
            f"- {at.capitalize()}: ${ad.balance:.2f}"
            for at, ad in user.accounts.items()
        )

    async def get_products(self) -> List[Product]:
        container = get_async_container("products")
        items: list[Dict[str, Any]] = []
        async for item in container.query_items(
            query="SELECT * FROM c",
            enable_cross_partition_query=True,
        ):
            items.append(item)
        return [
            Product(
                id=item["id"],
                name=item["name"],
                type=item["type"],
                interest_rate=item["interest_rate"],
                description=item["description"],
            )
            for item in items
        ]

    async def get_change_feed(self, last_id: int = 0) -> List[Dict[str, Any]]:
        """Return change feed events. last_id is treated as a Unix timestamp cursor (_ts)."""
        container = get_async_container("change_feed")
        items: list[Dict[str, Any]] = []
        if last_id:
            async for item in container.query_items(
                query="SELECT * FROM c WHERE c._ts > @ts ORDER BY c._ts ASC",
                parameters=[{"name": "@ts", "value": last_id}],
                enable_cross_partition_query=True,
            ):
                items.append(item)
        else:
            async for item in container.query_items(
                query="SELECT * FROM c ORDER BY c._ts ASC",
                enable_cross_partition_query=True,
            ):
                items.append(item)
        return items


_ledger_instance: Optional[LedgerEngine] = None


def get_ledger() -> LedgerEngine:
    global _ledger_instance
    if _ledger_instance is None:
        _ledger_instance = LedgerEngine()
    return _ledger_instance
