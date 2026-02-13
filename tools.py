from typing import List, Annotated, Dict, Any, Optional, Union
from agent_framework import tool
from ledger import LedgerEngine, Transaction, Product
from identity import IdentityManager


class BankingTools:
    def __init__(
        self,
        ledger: LedgerEngine,
        identity: IdentityManager,
        username: str,
        session_token: str,
    ):
        self.ledger = ledger
        self.identity = identity
        self.username = username
        self.session_token = session_token

    @tool
    def check_balance(
        self,
        account_type: Annotated[
            str, "The specific account to check ('checking' or 'savings')"
        ] = "checking",
    ) -> str:
        """View the real-time balance of your own account."""
        balance = self.ledger.get_balance(self.session_token, account_type)
        return f"SUCCESS: Your {account_type} balance is ${balance:.2f}"

    @tool
    def view_history(
        self,
        account_type: Annotated[
            str, "Account type ('checking' or 'savings')"
        ] = "checking",
    ) -> str:
        """View the list of past transactions for your account."""
        return self.ledger.get_history(self.session_token, account_type)

    @tool
    def list_my_accounts(self) -> str:
        """Lists all your open accounts and their current balances."""
        return self.ledger.list_user_accounts(self.session_token)

    @tool
    def send_money(
        self,
        to: Annotated[str, "Recipient's exact username (e.g. 'alice' or 'bob')"],
        amount: Annotated[float, "Dollar amount to send"],
        note: Annotated[str, "Brief description of why you are sending money"],
        from_account: Annotated[
            str, "Your source account ('checking' or 'savings')"
        ] = "checking",
        to_account: Annotated[str, "Recipient's target account type"] = "checking",
    ) -> str:
        """Instantly send money to another user. This action is cryptographically signed."""
        payload = f"{to}{amount}{note}"
        sig = self.identity.sign_message(self.username, payload.encode())
        success = self.ledger.transfer(
            self.session_token,
            to,
            amount,
            note,
            from_account,
            to_account,
            signature=sig.hex(),
        )
        return (
            f"SUCCESS: Transferred ${amount:.2f} to {to}."
            if success
            else "FAILED: Check funds or username."
        )

    @tool
    def request_money(
        self,
        from_user: Annotated[str, "Username you are requesting money FROM"],
        amount: Annotated[float, "Dollar amount you want them to pay you"],
        note: Annotated[str, "Reason for the request"],
    ) -> str:
        """Ask another user to pay you. They must approve it before money moves."""
        success = self.ledger.request_funds(self.session_token, from_user, amount, note)
        return (
            f"SUCCESS: Requested ${amount:.2f} from {from_user}."
            if success
            else "FAILED: User not found."
        )

    @tool
    def list_pending_requests(self) -> List[Dict[str, Any]]:
        """See a list of requests from OTHER users asking YOU for money."""
        return self.ledger.get_pending_requests(self.session_token)

    @tool
    def approve_payment(
        self,
        request_id: Annotated[str, "The unique ID of the request you want to pay"],
    ) -> str:
        """Approve and pay a request from someone else. This is a final action."""
        payload = f"APPROVE{request_id}"
        sig = self.identity.sign_message(self.username, payload.encode())
        success = self.ledger.approve_request(
            self.session_token, request_id, signature=sig.hex()
        )
        return (
            "SUCCESS: Request approved and payment sent."
            if success
            else "FAILED: Check funds or ID."
        )

    @tool
    def list_products(self) -> str:
        """List available bank products (loans, cards) and their interest rates."""
        prods = self.ledger.get_products()
        lines = [
            f"- {p.name} ({p.type}): {p.interest_rate}% rate - {p.description}"
            for p in prods
        ]
        return "Bank Products:\n" + "\n".join(lines)

    @tool
    def open_new_account(
        self,
        account_type: Annotated[
            str, "Type of account to open ('savings' or 'checking')"
        ],
    ) -> str:
        """Open a new account type for yourself instantly."""
        success = self.ledger.open_account(self.session_token, account_type)
        return f"SUCCESS: Opened {account_type} account." if success else "FAILED."
