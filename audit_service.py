import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from db.cosmos import get_async_container

logger = logging.getLogger(__name__)


class AuditLogger:
    """Logs banking events to the change_feed container for compliance."""

    def __init__(self) -> None:
        pass

    async def log_event(
        self, event_type: str, username: str, details: Dict[str, Any]
    ) -> None:
        payload = {
            "username": username,
            "timestamp": datetime.now().isoformat(),
            **details,
        }
        try:
            await get_async_container("change_feed").upsert_item(
                {
                    "id": str(uuid.uuid4()),
                    "event_type": event_type,
                    "payload": payload,
                    "timestamp": datetime.now().isoformat(),
                }
            )
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
