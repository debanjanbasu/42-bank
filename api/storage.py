import os
import sqlite3
from datetime import datetime
from typing import Any, Optional


class APIStorage:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or os.getenv("API_DB_PATH") or os.getenv("TEST_DB") or os.getenv("BANK_DB_PATH") or "data/bank.db"
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS auth_devices (
                    user_token TEXT NOT NULL,
                    device_id_hash TEXT NOT NULL,
                    device_name TEXT,
                    biometric_enabled INTEGER NOT NULL DEFAULT 1,
                    push_token TEXT,
                    registered_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_token, device_id_hash)
                );

                CREATE TABLE IF NOT EXISTS key_backups (
                    user_token TEXT PRIMARY KEY,
                    backup_id TEXT UNIQUE NOT NULL,
                    encrypted_private_key TEXT NOT NULL,
                    public_key TEXT NOT NULL,
                    recovery_key_hash TEXT NOT NULL,
                    recovery_hint TEXT,
                    encryption_version TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    username TEXT
                );

                CREATE TABLE IF NOT EXISTS restore_challenges (
                    backup_id TEXT PRIMARY KEY,
                    nonce TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    user_token TEXT NOT NULL
                );
                """
            )

    def upsert_device(
        self,
        user_token: str,
        device_id_hash: str,
        device_name: Optional[str],
        biometric_enabled: bool,
        push_token: Optional[str],
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT registered_at FROM auth_devices WHERE user_token = ? AND device_id_hash = ?",
                (user_token, device_id_hash),
            ).fetchone()
            registered_at = existing["registered_at"] if existing else now
            conn.execute(
                """
                INSERT OR REPLACE INTO auth_devices (
                    user_token, device_id_hash, device_name, biometric_enabled, push_token, registered_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_token,
                    device_id_hash,
                    device_name,
                    1 if biometric_enabled else 0,
                    push_token,
                    registered_at,
                    now,
                ),
            )

    def has_device(self, user_token: str, device_id_hash: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM auth_devices WHERE user_token = ? AND device_id_hash = ?",
                (user_token, device_id_hash),
            ).fetchone()
            return row is not None

    def list_devices(self, user_token: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT device_id_hash, device_name, biometric_enabled, push_token, registered_at, updated_at
                FROM auth_devices
                WHERE user_token = ?
                ORDER BY registered_at ASC
                """,
                (user_token,),
            ).fetchall()
            return [
                {
                    "device_id_hash": row["device_id_hash"],
                    "device_name": row["device_name"],
                    "biometric_enabled": bool(row["biometric_enabled"]),
                    "push_token": row["push_token"],
                    "registered_at": row["registered_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

    def save_key_backup(self, user_token: str, backup: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO key_backups (
                    user_token, backup_id, encrypted_private_key, public_key, recovery_key_hash,
                    recovery_hint, encryption_version, timestamp, username
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_token,
                    backup["backup_id"],
                    backup["encrypted_private_key"],
                    backup["public_key"],
                    backup["recovery_key_hash"],
                    backup.get("recovery_hint"),
                    backup["encryption_version"],
                    backup["timestamp"],
                    backup.get("username"),
                ),
            )

    def get_key_backup_by_user(self, user_token: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM key_backups WHERE user_token = ?",
                (user_token,),
            ).fetchone()
            return dict(row) if row else None

    def delete_key_backup(self, user_token: str) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT backup_id FROM key_backups WHERE user_token = ?",
                (user_token,),
            ).fetchone()
            conn.execute("DELETE FROM key_backups WHERE user_token = ?", (user_token,))
            if row:
                conn.execute("DELETE FROM restore_challenges WHERE backup_id = ?", (row["backup_id"],))

    def save_challenge(
        self,
        backup_id: str,
        nonce: str,
        user_token: str,
        expires_at: str,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO restore_challenges (backup_id, nonce, created_at, expires_at, user_token)
                VALUES (?, ?, ?, ?, ?)
                """,
                (backup_id, nonce, now, expires_at, user_token),
            )

    def get_challenge(self, backup_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM restore_challenges WHERE backup_id = ?",
                (backup_id,),
            ).fetchone()
            return dict(row) if row else None

    def delete_challenge(self, backup_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM restore_challenges WHERE backup_id = ?", (backup_id,))


_storage_instance: Optional[APIStorage] = None


def get_api_storage() -> APIStorage:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = APIStorage()
    return _storage_instance
