import hashlib
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from azure.cosmos import PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from db.cosmos import get_async_container, get_container, get_database


def _make_doc_id(user_token: str, device_id_hash: str) -> str:
    """Generate a Cosmos DB-safe document ID."""
    return hashlib.sha256(f"{user_token}:{device_id_hash}".encode()).hexdigest()


class APIStorage:
    """Async storage layer for auth devices, key backups, challenges, and token blacklist.

    All data operations use the async Cosmos SDK. The sync SDK is only used
    during __init__ to create containers if they don't exist.
    """

    def __init__(self) -> None:
        self._init_db()

    def _init_db(self) -> None:
        db = get_database()
        for container_name, partition_path in [
            ("auth_devices", "/user_token"),
            ("key_backups", "/user_token"),
            ("restore_challenges", "/backup_id"),
            ("token_blacklist", "/jti"),
        ]:
            db.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path=partition_path),
                offer_throughput=400,
            )

    async def upsert_device(
        self,
        user_token: str,
        device_id_hash: str,
        device_name: Optional[str],
        biometric_enabled: bool,
        push_token: Optional[str],
    ) -> None:
        """Register or update a device for a user.

        Idempotent on (user_token, device_id_hash): re-upserting the same
        device preserves its original registered_at timestamp.
        """
        now = datetime.now(datetime.UTC).isoformat()
        container = get_async_container("auth_devices")
        doc_id = _make_doc_id(user_token, device_id_hash)
        try:
            existing = await container.read_item(item=doc_id, partition_key=user_token)
            registered_at = existing.get("registered_at", now)
        except CosmosResourceNotFoundError:
            registered_at = now
        await container.upsert_item(
            {
                "id": doc_id,
                "user_token": user_token,
                "device_id_hash": device_id_hash,
                "device_name": device_name,
                "biometric_enabled": biometric_enabled,
                "push_token": push_token,
                "registered_at": registered_at,
                "updated_at": now,
            }
        )

    async def remove_device(self, user_token: str, device_id_hash: str) -> None:
        """Remove a registered device by its hashed ID."""
        container = get_async_container("auth_devices")
        doc_id = _make_doc_id(user_token, device_id_hash)
        try:
            await container.delete_item(item=doc_id, partition_key=user_token)
        except CosmosResourceNotFoundError:
            pass

    async def has_device(self, user_token: str, device_id_hash: str) -> bool:
        container = get_async_container("auth_devices")
        doc_id = _make_doc_id(user_token, device_id_hash)
        try:
            await container.read_item(item=doc_id, partition_key=user_token)
            return True
        except CosmosResourceNotFoundError:
            return False

    async def list_devices(self, user_token: str) -> list[dict[str, Any]]:
        container = get_async_container("auth_devices")
        items: list[dict[str, Any]] = []
        async for item in container.query_items(
            query="SELECT * FROM c WHERE c.user_token = @t ORDER BY c.registered_at ASC",
            parameters=[{"name": "@t", "value": user_token}],
        ):
            items.append(item)
        return [
            {
                "device_id_hash": item["device_id_hash"],
                "device_name": item.get("device_name"),
                "biometric_enabled": bool(item.get("biometric_enabled", True)),
                "push_token": item.get("push_token"),
                "registered_at": item["registered_at"],
                "updated_at": item["updated_at"],
            }
            for item in items
        ]

    async def save_key_backup(self, user_token: str, backup: dict[str, Any]) -> None:
        await get_async_container("key_backups").upsert_item(
            {
                "id": backup["backup_id"],
                "user_token": user_token,
                "backup_id": backup["backup_id"],
                "encrypted_private_key": backup["encrypted_private_key"],
                "public_key": backup["public_key"],
                "recovery_key_hash": backup["recovery_key_hash"],
                "recovery_hint": backup.get("recovery_hint"),
                "encryption_version": backup["encryption_version"],
                "timestamp": backup["timestamp"],
                "username": backup.get("username"),
            }
        )

    async def get_key_backup_by_user(self, user_token: str) -> Optional[dict[str, Any]]:
        container = get_async_container("key_backups")
        items: list[dict[str, Any]] = []
        async for item in container.query_items(
            query="SELECT * FROM c WHERE c.user_token = @t",
            parameters=[{"name": "@t", "value": user_token}],
        ):
            items.append(item)
        if not items:
            return None
        item = items[0]
        return {
            "user_token": item["user_token"],
            "backup_id": item["backup_id"],
            "encrypted_private_key": item["encrypted_private_key"],
            "public_key": item["public_key"],
            "recovery_key_hash": item["recovery_key_hash"],
            "recovery_hint": item.get("recovery_hint"),
            "encryption_version": item["encryption_version"],
            "timestamp": item["timestamp"],
            "username": item.get("username"),
        }

    async def delete_key_backup(self, user_token: str) -> None:
        container = get_async_container("key_backups")
        items: list[dict[str, Any]] = []
        async for item in container.query_items(
            query="SELECT c.id, c.backup_id FROM c WHERE c.user_token = @t",
            parameters=[{"name": "@t", "value": user_token}],
        ):
            items.append(item)
        for item in items:
            await container.delete_item(item=item["id"], partition_key=user_token)
            await self.delete_challenge(item["backup_id"])

    async def save_challenge(
        self,
        backup_id: str,
        nonce: str,
        user_token: str,
        expires_at: str,
    ) -> None:
        now = datetime.now(datetime.UTC).isoformat()
        await get_async_container("restore_challenges").upsert_item(
            {
                "id": backup_id,
                "backup_id": backup_id,
                "nonce": nonce,
                "created_at": now,
                "expires_at": expires_at,
                "user_token": user_token,
            }
        )

    async def get_challenge(self, backup_id: str) -> Optional[dict[str, Any]]:
        try:
            item = await get_async_container("restore_challenges").read_item(
                item=backup_id, partition_key=backup_id
            )
            return {
                "backup_id": item["backup_id"],
                "nonce": item["nonce"],
                "created_at": item["created_at"],
                "expires_at": item["expires_at"],
                "user_token": item["user_token"],
            }
        except CosmosResourceNotFoundError:
            return None

    async def delete_challenge(self, backup_id: str) -> None:
        try:
            await get_async_container("restore_challenges").delete_item(
                item=backup_id, partition_key=backup_id
            )
        except CosmosResourceNotFoundError:
            pass

    async def count_devices(self, user_token: str) -> int:
        container = get_async_container("auth_devices")
        items: list[Any] = []
        async for item in container.query_items(
            query="SELECT VALUE COUNT(1) FROM c WHERE c.user_token = @t",
            parameters=[{"name": "@t", "value": user_token}],
        ):
            items.append(item)
        val = items[0] if items else 0
        return val if isinstance(val, int) else 0

    async def revoke_token(self, jti: str, user_token: str) -> None:
        now = datetime.now(datetime.UTC).isoformat()
        try:
            await get_async_container("token_blacklist").read_item(
                item=jti, partition_key=jti
            )
        except CosmosResourceNotFoundError:
            await get_async_container("token_blacklist").upsert_item(
                {
                    "id": jti,
                    "jti": jti,
                    "user_token": user_token,
                    "revoked_at": now,
                }
            )

    async def is_token_revoked(self, jti: str) -> bool:
        """Check if a JWT (identified by its JTI claim) has been revoked."""
        try:
            await get_async_container("token_blacklist").read_item(
                item=jti, partition_key=jti
            )
            return True
        except CosmosResourceNotFoundError:
            return False

    async def cleanup_expired_tokens(self, before_timestamp: str) -> None:
        container = get_async_container("token_blacklist")
        items: list[dict[str, Any]] = []
        async for item in container.query_items(
            query="SELECT c.id, c.jti FROM c WHERE c.revoked_at < @ts",
            parameters=[{"name": "@ts", "value": before_timestamp}],
        ):
            items.append(item)
        for item in items:
            try:
                await container.delete_item(item=item["id"], partition_key=item["jti"])
            except CosmosResourceNotFoundError:
                pass


_storage_instance: Optional[APIStorage] = None


def get_api_storage() -> APIStorage:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = APIStorage()
    return _storage_instance
