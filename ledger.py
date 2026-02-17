import json
import os
import hashlib
import sqlite3
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Protocol, Any, Union


class Transaction(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    sender: str
    recipient: str
    amount: float
    description: str
    account_type: str = "checking"


class AccountData(BaseModel):
    balance: float = 0.0
    history: List[Transaction] = Field(default_factory=list)


class UserAccount(BaseModel):
    token: str
    username: str
    public_key: Optional[str] = None
    accounts: Dict[str, AccountData] = Field(
        default_factory=lambda: {
            "checking": AccountData(balance=0.0),
            "savings": AccountData(balance=0.0),
        }
    )
    pending_requests: List[Dict[str, Any]] = Field(default_factory=list)


class Product(BaseModel):
    id: str
    name: str
    type: str  # checking, saving, loan, mortgage, credit_card
    interest_rate: float
    description: str


class LedgerEngine:
    def __init__(self, db_path: str = "data/bank.db") -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    token TEXT PRIMARY KEY,
                    username TEXT UNIQUE COLLATE NOCASE,
                    data TEXT
                );
                CREATE TABLE IF NOT EXISTS change_feed (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    payload TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    type TEXT,
                    interest_rate REAL,
                    description TEXT
                );
            """)
            if not conn.execute("SELECT 1 FROM products LIMIT 1").fetchone():
                products = [
                    (
                        "p0",
                        "Standard Checking",
                        "checking",
                        0.0,
                        "Default everyday account.",
                    ),
                    ("p1", "High-Yield Savings", "saving", 4.5, "Earn 4.5% interest."),
                    ("p2", "Home Mortgage", "mortgage", 3.8, "30-year fixed rate."),
                    ("p3", "Express Auto Loan", "loan", 5.9, "Instant car financing."),
                    (
                        "p4",
                        "Infinite Rewards Card",
                        "credit_card",
                        15.4,
                        "2% cashback.",
                    ),
                ]
                conn.executemany(
                    "INSERT INTO products VALUES (?, ?, ?, ?, ?)", products
                )

    def _get_user(self, token: str) -> Optional[UserAccount]:
        if not token:
            return None
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM users WHERE token = ?", (token,)
            ).fetchone()
            return UserAccount.model_validate_json(row[0]) if row else None

    def _save_user(self, user: Optional[UserAccount]) -> None:
        if not user:
            return
        data = user.model_dump_json()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO users (token, username, data) VALUES (?, ?, ?)",
                (user.token, user.username, data),
            )
            conn.execute(
                "INSERT INTO change_feed (event_type, payload) VALUES (?, ?)",
                ("USER_UPDATE", data),
            )

    def register_user(
        self,
        token: str,
        username: str,
        public_key_hex: str,
        initial_balance: float = 0.0,
    ) -> None:
        user = self._get_user(token) or UserAccount(
            token=token, username=username, public_key=public_key_hex
        )
        user.public_key = public_key_hex
        if user.accounts["checking"].balance == 0.0:
            user.accounts["checking"].balance = initial_balance
        self._save_user(user)

    def get_balance(self, token: str, account_type: str = "checking") -> float:
        user = self._get_user(token)
        return user.accounts.get(account_type, AccountData()).balance if user else 0.0

    def get_username(self, token: str) -> str:
        user = self._get_user(token)
        return user.username if user else "Unknown"

    def get_token_by_username(self, username: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT token FROM users WHERE username = ?", (username,)
            ).fetchone()
            return str(row[0]) if row else None

    def _verify_signature(self, token: str, message: str, signature_hex: str) -> bool:
        from pqcrypto.sign.ml_dsa_44 import verify as pq_verify

        user = self._get_user(token)
        if not user or not user.public_key:
            return False
        try:
            # Returns True on success
            return bool(
                pq_verify(
                    bytes.fromhex(user.public_key),
                    message.encode(),
                    bytes.fromhex(signature_hex),
                )
            )
        except Exception:
            return False

    def transfer(
        self,
        sender_token: str,
        recipient_username: str,
        amount: float,
        description: str,
        from_account: str = "checking",
        to_account: str = "checking",
        signature: Optional[str] = None,
    ) -> bool:
        if signature and not self._verify_signature(
            sender_token, f"{recipient_username}{amount}{description}", signature
        ):
            return False

        recipient_token = self.get_token_by_username(recipient_username)
        if (
            not recipient_token
            or (sender_token == recipient_token and from_account == to_account)
            or amount <= 0
        ):
            return False

        s_user, r_user = self._get_user(sender_token), self._get_user(recipient_token)
        if (
            not s_user
            or not r_user
            or from_account not in s_user.accounts
            or to_account not in r_user.accounts
        ):
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

        self._save_user(s_user)
        self._save_user(r_user)
        return True

    def open_account(self, token: str, account_type: str) -> bool:
        user = self._get_user(token)
        if not user or account_type in user.accounts:
            return bool(user)
        user.accounts[account_type] = AccountData()
        self._save_user(user)
        return True

    def request_funds(
        self, requester_token: str, target_username: str, amount: float, note: str
    ) -> bool:
        target_token = self.get_token_by_username(target_username)
        req_user = self._get_user(requester_token)
        if not target_token or not req_user:
            return False
        tar_user = self._get_user(target_token)
        if not tar_user or amount <= 0:
            return False

        req = {
            "id": hashlib.md5(
                f"{req_user.username}{datetime.now()}".encode()
            ).hexdigest()[:8],
            "requester": req_user.username,
            "amount": amount,
            "note": note,
            "timestamp": datetime.now().isoformat(),
        }
        tar_user.pending_requests.append(req)
        self._save_user(tar_user)
        return True

    def get_pending_requests(self, token: str) -> List[Dict[str, Any]]:
        user = self._get_user(token)
        return user.pending_requests if user else []

    def approve_request(
        self, token: str, request_id: str, signature: Optional[str] = None
    ) -> bool:
        user = self._get_user(token)
        if not user:
            return False
        for i, req in enumerate(user.pending_requests):
            if req["id"] == request_id:
                if signature and not self._verify_signature(
                    token, f"APPROVE{request_id}", signature
                ):
                    return False
                if self.transfer(
                    token, req["requester"], req["amount"], f"Approved: {req['note']}"
                ):
                    user = self._get_user(token)
                    if user:
                        user.pending_requests = [
                            r for r in user.pending_requests if r["id"] != request_id
                        ]
                        self._save_user(user)
                        return True
        return False

    def get_history(self, token: str, account_type: str = "checking") -> str:
        user = self._get_user(token)
        if not user or account_type not in user.accounts:
            return "Account not found."
        history = user.accounts[account_type].history
        if not history:
            return "No transactions found."

        lines = []
        for tx in history:
            is_sender = tx.sender.lower() == user.username.lower()
            if is_sender:
                # User sent money
                lines.append(
                    f"- {tx.timestamp[:16]} SENT ${tx.amount:.2f} to {tx.recipient} - {tx.description}"
                )
            else:
                # User received money
                lines.append(
                    f"- {tx.timestamp[:16]} RECEIVED ${tx.amount:.2f} from {tx.sender} - {tx.description}"
                )
        return "\n".join(lines)

    def list_user_accounts(self, token: str) -> str:
        user = self._get_user(token)
        if not user:
            return "User not found."
        return "\n".join(
            [
                f"- {at.capitalize()}: ${ad.balance:.2f}"
                for at, ad in user.accounts.items()
            ]
        )

    def get_products(self) -> List[Product]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return [
                Product(**dict(r))
                for r in conn.execute("SELECT * FROM products").fetchall()
            ]

    def get_change_feed(self, last_id: int = 0) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM change_feed WHERE id > ? ORDER BY id ASC", (last_id,)
                ).fetchall()
            ]
