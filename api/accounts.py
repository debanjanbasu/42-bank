"""
Accounts API for Mobile App.

Provides account balance and transaction history endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from api.deps import get_current_user
from ledger import get_ledger

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class Account(BaseModel):
    type: str
    balance: float
    account_number: Optional[str] = None


class AccountsResponse(BaseModel):
    accounts: List[Account]


class Transaction(BaseModel):
    id: str
    sender: str
    recipient: str
    amount: float
    description: str
    timestamp: str
    status: str


class TransactionsResponse(BaseModel):
    transactions: List[Transaction]


@router.get("", response_model=AccountsResponse)
async def get_accounts(user: dict = Depends(get_current_user)):
    """
    Get user's account balances.

    Returns all accounts associated with the authenticated user.
    """
    ledger = get_ledger()
    user_data = await ledger.get_user(user["sub"])

    if not user_data:
        raise HTTPException(404, "User not found")

    balance = await ledger.get_balance(user_data.token)

    return AccountsResponse(
        accounts=[
            Account(
                type="checking",
                balance=balance,
                account_number=user_data.username[:8].upper(),
            )
        ]
    )


@router.get("/transactions", response_model=TransactionsResponse)
async def get_transactions(
    user: dict = Depends(get_current_user),
):
    """
    Get user's transaction history.

    Returns paginated list of transactions for the authenticated user.
    """
    ledger = get_ledger()
    user_data = await ledger.get_user(user["sub"])

    if not user_data:
        raise HTTPException(404, "User not found")

    history = await ledger.get_transactions(user_data.token)

    transactions = [
        Transaction(
            id=t.get("id", ""),
            sender=t.get("from", ""),
            recipient=t.get("to", ""),
            amount=t.get("amount", 0),
            description=t.get("memo", ""),
            timestamp=t.get("timestamp", ""),
            status=t.get("status", "completed"),
        )
        for t in history
    ]

    return TransactionsResponse(transactions=transactions)
