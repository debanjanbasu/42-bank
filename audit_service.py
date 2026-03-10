import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from db.cosmos import get_async_container, get_container

logger = logging.getLogger(__name__)


class AuditLogger:
    """Logs banking events to the change_feed container for compliance."""

    def __init__(self) -> None:
        pass

    async def log_event(self, event_type: str, username: str, details: Dict[str, Any]) -> None:
        payload = {
            "username": username,
            "timestamp": datetime.now().isoformat(),
            **details,
        }
        try:
            await get_async_container("change_feed").upsert_item({
                "id": str(uuid.uuid4()),
                "event_type": event_type,
                "payload": payload,
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as e:
            logger.error("Audit log write failed: %s", e)

    async def log_transfer(
        self,
        sender: str,
        recipient: str,
        amount: float,
        success: bool,
        description: str,
    ) -> None:
        await self.log_event(
            "TRANSFER_SUCCESS" if success else "TRANSFER_FAILED",
            sender,
            {"recipient": recipient, "amount": amount, "description": description},
        )

    async def log_login(self, username: str, device_id: str, success: bool) -> None:
        await self.log_event(
            "LOGIN_SUCCESS" if success else "LOGIN_FAILED",
            username,
            {"device_id": device_id},
        )


def run_audit_service():
    print("--- 42 Bank Audit Service Starting ---")
    print("Monitoring Ledger Change Feed for suspicious activity...")

    last_ts = 0

    try:
        while True:
            container = get_container("change_feed")
            if last_ts:
                changes = list(container.query_items(
                    query="SELECT * FROM c WHERE c._ts > @ts ORDER BY c._ts ASC",
                    parameters=[{"name": "@ts", "value": last_ts}],
                    enable_cross_partition_query=True,
                ))
            else:
                changes = list(container.query_items(
                    query="SELECT TOP 1 c._ts FROM c ORDER BY c._ts DESC",
                    enable_cross_partition_query=True,
                ))
                if changes:
                    last_ts = changes[0].get("_ts", 0)
                changes = []

            for change in changes:
                last_ts = change.get("_ts", last_ts)
                event_type = change.get("event_type", "UNKNOWN")
                payload = change.get("payload", {})
                if isinstance(payload, str):
                    payload = json.loads(payload)

                username = payload.get("username", "Unknown")
                amount = payload.get("amount", 0.0)

                print(
                    f"[AUDIT] Event: {event_type} - User: {username}, Amount: ${amount:.2f}"
                )

                if amount > 5000:
                    print(f"!!! ALERT: High value transaction detected: {username}")

            time.sleep(2)
    except KeyboardInterrupt:
        print("\nAudit Service Stopped.")


if __name__ == "__main__":
    run_audit_service()
