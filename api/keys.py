"""
Key Backup and Restore API for Mobile App.

Provides secure backup and restore of ML-DSA-44 private keys.
Private keys NEVER leave the device unencrypted.

Security Model:
1. Mobile device generates ML-DSA-44 keypair
2. Private key is encrypted with user's recovery key (never sent to server)
3. Encrypted private key is backed up to cloud
4. To restore, user proves they have recovery key (zero-knowledge proof)
5. Server sends encrypted backup, device decrypts locally

Endpoints:
    POST /api/keys/backup - Backup encrypted private key
    POST /api/keys/restore - Restore encrypted private key
    GET /api/keys/status - Check backup status
    DELETE /api/keys/backup - Delete backup (for account deletion)

Note: The recovery key is NEVER sent to the server.
We only store a hash of the recovery key for verification.
"""

import base64
import binascii
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_current_user
from api.storage import get_api_storage

router = APIRouter(prefix="/api/keys", tags=["key-management"])


# ============ Request/Response Models ============


class BackupRequest(BaseModel):
    """Request to backup encrypted private key."""

    encrypted_private_key: str = Field(
        ..., description="Private key encrypted with user's recovery key (base64)"
    )
    public_key: str = Field(..., description="ML-DSA-44 public key (for verification)")
    recovery_key_hash: str = Field(
        ...,
        description="SHA-256 hash of recovery key (for zero-knowledge verification)",
    )
    recovery_hint: Optional[str] = Field(
        None, max_length=100, description="Optional hint for recovery (NOT the key!)"
    )
    encryption_version: str = Field(
        "1.0", description="Version of encryption scheme used"
    )


class BackupResponse(BaseModel):
    """Response after successful backup."""

    backup_id: str
    timestamp: str
    recovery_key_hash: str
    status: str = "success"


class RestoreRequest(BaseModel):
    """Request to restore encrypted private key."""

    backup_id: str = Field(..., description="Backup ID to restore from")
    recovery_key_proof: str = Field(
        ..., description="Proof that user has recovery key (HMAC with nonce)"
    )
    nonce: str = Field(..., description="Random nonce for proof generation")


class RestoreResponse(BaseModel):
    """Response with encrypted private key."""

    encrypted_private_key: str
    public_key: str
    encryption_version: str
    timestamp: str


class BackupStatusResponse(BaseModel):
    """Backup status for user."""

    has_backup: bool
    backup_id: Optional[str] = None
    timestamp: Optional[str] = None
    recovery_hint: Optional[str] = None


class ChallengeRequest(BaseModel):
    """Request challenge for restore."""

    backup_id: str


class ChallengeResponse(BaseModel):
    """Challenge response for restore."""

    nonce: str
    backup_id: str
    expires_at: str


# ============ Helper Functions ============


def generate_backup_id() -> str:
    """Generate unique backup ID."""
    return f"backup_{secrets.token_hex(16)}"


def generate_nonce() -> str:
    """Generate random nonce for challenge."""
    return secrets.token_hex(32)


def verify_recovery_key_proof(
    stored_hash: str, recovery_key_proof: str, nonce: str
) -> bool:
    """
    Verify that the user has the recovery key without revealing it.

    The proof is computed as:
        proof = HMAC-SHA256(recovery_key, nonce + backup_id)

    We verify by computing the expected HMAC using stored hash
    (simplified for demo - production should use proper zero-knowledge proof).

    In production, use proper ZKP like:
    - SRP (Secure Remote Password)
    - OPAQUE protocol
    """
    # Simplified verification for demo
    # In production, implement proper zero-knowledge proof
    # Expected: proof = SHA256(recovery_key_hash + nonce)
    expected = hashlib.sha256((stored_hash + nonce).encode()).hexdigest()
    return secrets.compare_digest(recovery_key_proof, expected)


# ============ Endpoints ============


@router.post("/backup", response_model=BackupResponse)
async def backup_keys(request: BackupRequest, user: dict = Depends(get_current_user)):
    """
    Backup encrypted private key to cloud.

    Security:
    - Private key is encrypted on device BEFORE sending
    - Recovery key NEVER leaves device
    - Only hash of recovery key is stored for verification
    - Encrypted backup can only be decrypted with recovery key

    Flow:
    1. Mobile app generates recovery key locally
    2. App encrypts private key with recovery key
    3. App sends encrypted key + recovery_key_hash to server
    4. Server stores encrypted backup
    5. Later, user can restore by proving they have recovery key
    """
    user_token = user["sub"]

    # Generate backup ID
    backup_id = generate_backup_id()
    timestamp = datetime.now(timezone.utc).isoformat()

    backup_record = {
        "backup_id": backup_id,
        "encrypted_private_key": request.encrypted_private_key,
        "public_key": request.public_key,
        "recovery_key_hash": request.recovery_key_hash,
        "recovery_hint": request.recovery_hint,
        "encryption_version": request.encryption_version,
        "timestamp": timestamp,
        "username": user.get("username", "unknown"),
    }
    await get_api_storage().save_key_backup(user_token, backup_record)

    return BackupResponse(
        backup_id=backup_id,
        timestamp=timestamp,
        recovery_key_hash=request.recovery_key_hash,
        status="success",
    )


@router.post("/challenge", response_model=ChallengeResponse)
async def get_restore_challenge(
    request: ChallengeRequest, user: dict = Depends(get_current_user)
):
    """
    Get a challenge nonce for restore operation.

    This prevents replay attacks by requiring a fresh nonce
    for each restore attempt.

    Flow:
    1. Mobile app requests challenge with backup_id
    2. Server generates nonce and stores it
    3. App computes proof = HMAC(recovery_key, nonce)
    4. App sends proof to /restore endpoint
    5. Server verifies proof and returns encrypted key
    """
    user_token = user["sub"]

    # Check if backup exists
    backup = await get_api_storage().get_key_backup_by_user(user_token)
    if not backup:
        raise HTTPException(404, "No backup found for user")

    if backup["backup_id"] != request.backup_id:
        raise HTTPException(400, "Invalid backup ID")

    # Generate nonce
    nonce = generate_nonce()
    expires_at_dt = datetime.now(timezone.utc) + timedelta(minutes=5)
    expires_at = expires_at_dt.isoformat()

    # Store challenge
    await get_api_storage().save_challenge(
        backup_id=backup["backup_id"],
        nonce=nonce,
        user_token=user_token,
        expires_at=expires_at,
    )

    return ChallengeResponse(
        nonce=nonce, backup_id=request.backup_id, expires_at=expires_at
    )


@router.post("/restore", response_model=RestoreResponse)
async def restore_keys(request: RestoreRequest, user: dict = Depends(get_current_user)):
    """
    Restore encrypted private key from backup.

    Security:
    - User must prove they have recovery key (zero-knowledge)
    - Proof is computed with nonce to prevent replay
    - Encrypted key is returned, device decrypts locally

    Flow:
    1. App gets challenge nonce from /challenge
    2. App computes proof = HMAC-SHA256(recovery_key, nonce + backup_id)
    3. App sends proof to this endpoint
    4. Server verifies proof
    5. Server returns encrypted private key
    6. Device decrypts with recovery key
    """
    user_token = user["sub"]

    # Check if backup exists
    backup = await get_api_storage().get_key_backup_by_user(user_token)
    if not backup:
        raise HTTPException(404, "No backup found for user")

    if backup["backup_id"] != request.backup_id:
        raise HTTPException(400, "Invalid backup ID")

    # Get challenge
    challenge = await get_api_storage().get_challenge(request.backup_id)
    if not challenge:
        raise HTTPException(400, "No challenge found. Request a challenge first.")

    # Verify challenge owner
    if challenge.get("user_token") != user_token:
        raise HTTPException(403, "Challenge does not belong to the authenticated user")

    # Verify challenge expiry
    expires_at_value = challenge.get("expires_at")
    if not expires_at_value or datetime.now(timezone.utc) > datetime.fromisoformat(
        expires_at_value
    ):
        await get_api_storage().delete_challenge(request.backup_id)
        raise HTTPException(400, "Challenge has expired. Request a new challenge.")

    # Verify nonce matches
    if challenge.get("nonce") != request.nonce:
        raise HTTPException(400, "Invalid nonce")

    # Verify recovery key proof
    if not verify_recovery_key_proof(
        backup["recovery_key_hash"], request.recovery_key_proof, request.nonce
    ):
        raise HTTPException(401, "Invalid recovery key proof")

    # Clear challenge (one-time use)
    await get_api_storage().delete_challenge(request.backup_id)

    return RestoreResponse(
        encrypted_private_key=backup["encrypted_private_key"],
        public_key=backup["public_key"],
        encryption_version=backup["encryption_version"],
        timestamp=backup["timestamp"],
    )


@router.get("/status", response_model=BackupStatusResponse)
async def get_backup_status(user: dict = Depends(get_current_user)):
    """
    Check if user has a backup.

    Returns backup metadata without the encrypted key.
    """
    user_token = user["sub"]

    backup = await get_api_storage().get_key_backup_by_user(user_token)
    if not backup:
        return BackupStatusResponse(has_backup=False)

    return BackupStatusResponse(
        has_backup=True,
        backup_id=backup["backup_id"],
        timestamp=backup["timestamp"],
        recovery_hint=backup.get("recovery_hint"),
    )


@router.delete("/backup")
async def delete_backup(user: dict = Depends(get_current_user)):
    """
    Delete backup (for account deletion or key rotation).

    WARNING: This permanently deletes the encrypted backup.
    User will NOT be able to restore keys after this.
    """
    user_token = user["sub"]

    await get_api_storage().delete_key_backup(user_token)

    return {"status": "success", "message": "Backup deleted successfully"}


@router.post("/verify")
async def verify_key_ownership(
    public_key: str,
    signature: str,
    message: str,
    user: dict = Depends(get_current_user),
):
    """
    Verify that user owns the private key for a given public key.

    This is used when user needs to prove key ownership
    (e.g., before performing sensitive operations).

    Flow:
    1. Server sends a challenge message
    2. Mobile app signs message with private key
    3. App sends signature to this endpoint
    4. Server verifies signature with stored public key

    Note: This requires pqcrypto library for ML-DSA-44 verification.
    """
    user_token = user["sub"]

    # Get user's stored public key
    backup = await get_api_storage().get_key_backup_by_user(user_token)
    if backup:
        stored_public_key = backup["public_key"]
    else:
        # Get from ledger
        from ledger import get_ledger

        ledger = get_ledger()
        user_data = await ledger.get_user(user_token)
        if not user_data or not user_data.public_key:
            raise HTTPException(404, "No public key found for user")
        stored_public_key = user_data.public_key

    # Verify caller is proving ownership of the same key bound to the account
    if public_key != stored_public_key:
        raise HTTPException(401, "Public key mismatch")

    try:
        from pqcrypto.sign.ml_dsa_44 import verify as pq_verify

        public_key_bytes = base64.b64decode(stored_public_key)
        signature_bytes = base64.b64decode(signature)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            400, "Invalid base64 encoding for key or signature"
        ) from exc

    try:
        is_valid = bool(pq_verify(public_key_bytes, message.encode(), signature_bytes))
    except Exception:
        is_valid = False

    if not is_valid:
        raise HTTPException(401, "Invalid signature")

    return {"status": "verified", "message": "Key ownership verified successfully"}
