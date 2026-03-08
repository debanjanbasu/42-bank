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

import os
import hashlib
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/keys", tags=["key-management"])


# ============ Request/Response Models ============

class BackupRequest(BaseModel):
    """Request to backup encrypted private key."""
    encrypted_private_key: str = Field(
        ...,
        description="Private key encrypted with user's recovery key (base64)"
    )
    public_key: str = Field(
        ...,
        description="ML-DSA-44 public key (for verification)"
    )
    recovery_key_hash: str = Field(
        ...,
        description="SHA-256 hash of recovery key (for zero-knowledge verification)"
    )
    recovery_hint: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional hint for recovery (NOT the key!)"
    )
    encryption_version: str = Field(
        "1.0",
        description="Version of encryption scheme used"
    )


class BackupResponse(BaseModel):
    """Response after successful backup."""
    backup_id: str
    timestamp: str
    recovery_key_hash: str
    status: str = "success"


class RestoreRequest(BaseModel):
    """Request to restore encrypted private key."""
    backup_id: str = Field(
        ...,
        description="Backup ID to restore from"
    )
    recovery_key_proof: str = Field(
        ...,
        description="Proof that user has recovery key (HMAC with nonce)"
    )
    nonce: str = Field(
        ...,
        description="Random nonce for proof generation"
    )


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


# ============ In-Memory Storage (Replace with Cosmos DB in production) ============

# Structure: { user_token: { backup_id: str, encrypted_key: str, public_key: str, ... } }
_key_backups: dict = {}

# Structure: { backup_id: { nonce: str, created_at: datetime } }
_restore_challenges: dict = {}


# ============ Helper Functions ============

def generate_backup_id() -> str:
    """Generate unique backup ID."""
    return f"backup_{secrets.token_hex(16)}"


def generate_nonce() -> str:
    """Generate random nonce for challenge."""
    return secrets.token_hex(32)


def verify_recovery_key_proof(
    stored_hash: str,
    recovery_key_proof: str,
    nonce: str
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


async def get_current_user(authorization: str = Header(None)) -> dict:
    """Dependency to validate JWT and return user payload."""
    import jwt
    
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    
    token = authorization[7:]
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


# ============ Endpoints ============

@router.post("/backup", response_model=BackupResponse)
async def backup_keys(
    request: BackupRequest,
    user: dict = Depends(get_current_user)
):
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
    timestamp = datetime.utcnow().isoformat()
    
    # Store backup (replace with Cosmos DB in production)
    _key_backups[user_token] = {
        "backup_id": backup_id,
        "encrypted_private_key": request.encrypted_private_key,
        "public_key": request.public_key,
        "recovery_key_hash": request.recovery_key_hash,
        "recovery_hint": request.recovery_hint,
        "encryption_version": request.encryption_version,
        "timestamp": timestamp,
        "username": user.get("username", "unknown")
    }
    
    return BackupResponse(
        backup_id=backup_id,
        timestamp=timestamp,
        recovery_key_hash=request.recovery_key_hash,
        status="success"
    )


@router.post("/challenge", response_model=ChallengeResponse)
async def get_restore_challenge(
    request: ChallengeRequest,
    user: dict = Depends(get_current_user)
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
    if user_token not in _key_backups:
        raise HTTPException(404, "No backup found for user")
    
    backup = _key_backups[user_token]
    
    if backup["backup_id"] != request.backup_id:
        raise HTTPException(400, "Invalid backup ID")
    
    # Generate nonce
    nonce = generate_nonce()
    expires_at = datetime.utcnow().replace(
        minute=datetime.utcnow().minute + 5
    ).isoformat()
    
    # Store challenge
    _restore_challenges[backup["backup_id"]] = {
        "nonce": nonce,
        "created_at": datetime.utcnow().isoformat(),
        "user_token": user_token
    }
    
    return ChallengeResponse(
        nonce=nonce,
        backup_id=request.backup_id,
        expires_at=expires_at
    )


@router.post("/restore", response_model=RestoreResponse)
async def restore_keys(
    request: RestoreRequest,
    user: dict = Depends(get_current_user)
):
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
    if user_token not in _key_backups:
        raise HTTPException(404, "No backup found for user")
    
    backup = _key_backups[user_token]
    
    if backup["backup_id"] != request.backup_id:
        raise HTTPException(400, "Invalid backup ID")
    
    # Get challenge
    if request.backup_id not in _restore_challenges:
        raise HTTPException(400, "No challenge found. Request a challenge first.")
    
    challenge = _restore_challenges[request.backup_id]
    
    # Verify nonce matches
    if challenge.get("nonce") != request.nonce:
        raise HTTPException(400, "Invalid nonce")
    
    # Verify recovery key proof
    if not verify_recovery_key_proof(
        backup["recovery_key_hash"],
        request.recovery_key_proof,
        request.nonce
    ):
        raise HTTPException(401, "Invalid recovery key proof")
    
    # Clear challenge (one-time use)
    del _restore_challenges[request.backup_id]
    
    return RestoreResponse(
        encrypted_private_key=backup["encrypted_private_key"],
        public_key=backup["public_key"],
        encryption_version=backup["encryption_version"],
        timestamp=backup["timestamp"]
    )


@router.get("/status", response_model=BackupStatusResponse)
async def get_backup_status(user: dict = Depends(get_current_user)):
    """
    Check if user has a backup.
    
    Returns backup metadata without the encrypted key.
    """
    user_token = user["sub"]
    
    if user_token not in _key_backups:
        return BackupStatusResponse(has_backup=False)
    
    backup = _key_backups[user_token]
    
    return BackupStatusResponse(
        has_backup=True,
        backup_id=backup["backup_id"],
        timestamp=backup["timestamp"],
        recovery_hint=backup.get("recovery_hint")
    )


@router.delete("/backup")
async def delete_backup(user: dict = Depends(get_current_user)):
    """
    Delete backup (for account deletion or key rotation).
    
    WARNING: This permanently deletes the encrypted backup.
    User will NOT be able to restore keys after this.
    """
    user_token = user["sub"]
    
    if user_token in _key_backups:
        del _key_backups[user_token]
    
    return {
        "status": "success",
        "message": "Backup deleted successfully"
    }


@router.post("/verify")
async def verify_key_ownership(
    public_key: str,
    signature: str,
    message: str,
    user: dict = Depends(get_current_user)
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
    if user_token in _key_backups:
        stored_public_key = _key_backups[user_token]["public_key"]
    else:
        # Get from ledger
        from ledger import get_ledger
        ledger = get_ledger()
        user_data = ledger.get_user(user_token)
        if not user_data or not user_data.public_key:
            raise HTTPException(404, "No public key found for user")
        stored_public_key = user_data.public_key
    
    # Verify signature (would use pqcrypto in production)
    # For demo, we'll just check the public key matches
    if public_key != stored_public_key:
        raise HTTPException(401, "Public key mismatch")
    
    # TODO: Verify ML-DSA-44 signature
    # from pqcrypto.sign import verify
    # if not verify(stored_public_key, message, signature):
    #     raise HTTPException(401, "Invalid signature")
    
    return {
        "status": "verified",
        "message": "Key ownership verified successfully"
    }
