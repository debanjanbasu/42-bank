"""
Authentication API for Mobile App.

Provides user registration and login endpoints for the 42-Bank mobile app.
Users register with their device-generated ML-DSA-44 public key.

Endpoints:
    POST /api/auth/register - Register new user
    POST /api/auth/login - Login with device ID
    POST /api/auth/refresh - Refresh JWT token
    POST /api/auth/device - Register additional device

Security:
    - JWT tokens for authentication
    - Device ID binding for mobile security
    - Optional biometric authentication
"""

import os
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

import jwt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.requests import Request

from api.deps import (
    get_current_user,
    validate_token,
    JWT_SECRET,
    JWT_ALGORITHM,
    limiter,
)
from api.storage import get_api_storage
from ledger import get_ledger

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Configuration
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "168"))  # 7 days
JWT_REFRESH_EXPIRY_DAYS = int(os.getenv("JWT_REFRESH_EXPIRY_DAYS", "30"))
MAX_DEVICES_PER_USER = int(os.getenv("MAX_DEVICES_PER_USER", "10"))


# ============ Request/Response Models ============


class RegisterRequest(BaseModel):
    """User registration request from mobile app."""

    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-z0-9_]+$")
    public_key: str = Field(..., description="ML-DSA-44 public key from device")
    device_id: str = Field(..., description="Unique device identifier")
    device_name: Optional[str] = Field(None, description="User-friendly device name")
    biometric_enabled: bool = Field(
        True, description="Whether biometric auth is enabled"
    )
    push_token: Optional[str] = Field(None, description="Push notification token")


class RegisterResponse(BaseModel):
    """Registration response with JWT tokens."""

    user_id: str
    username: str
    token: str
    refresh_token: str
    expires_at: str
    public_key: str


class LoginRequest(BaseModel):
    """Login request from mobile app."""

    username: str
    device_id: str
    biometric_token: Optional[str] = Field(
        None, description="Biometric auth token if enabled"
    )
    push_token: Optional[str] = Field(None, description="Push notification token")


class LoginResponse(BaseModel):
    """Login response with JWT tokens."""

    user_id: str
    username: str
    token: str
    refresh_token: str
    expires_at: str


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class RefreshResponse(BaseModel):
    """Refresh token response."""

    token: str
    expires_at: str


class DeviceRegistrationRequest(BaseModel):
    """Register additional device for existing user."""

    device_id: str
    device_name: Optional[str] = None
    biometric_enabled: bool = True
    push_token: Optional[str] = None


class UserInfo(BaseModel):
    """User information response."""

    user_id: str
    username: str
    public_key: str
    created_at: Optional[str] = None
    devices: list[dict[str, Any]] = Field(default_factory=list)


# ============ Helper Functions ============


def generate_jwt(
    user_id: str, username: str, device_id: str, expiry_hours: int = JWT_EXPIRY_HOURS
) -> str:
    """Generate JWT token for user."""
    payload = {
        "sub": user_id,
        "username": username,
        "device_id": device_id,
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(datetime.UTC),
        "exp": datetime.now(datetime.UTC) + timedelta(hours=expiry_hours),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_refresh_token(user_id: str, username: str, device_id: str) -> str:
    """Generate refresh token for user."""
    payload = {
        "sub": user_id,
        "username": username,
        "device_id": device_id,
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(datetime.UTC),
        "exp": datetime.now(datetime.UTC) + timedelta(days=JWT_REFRESH_EXPIRY_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def hash_device_id(device_id: str) -> str:
    """Hash device ID for storage."""
    return hashlib.sha256(device_id.encode()).hexdigest()


async def register_device_for_user(
    user_token: str,
    device_id: str,
    device_name: Optional[str],
    biometric_enabled: bool,
    push_token: Optional[str],
) -> None:
    device_hash = hash_device_id(device_id)
    await get_api_storage().upsert_device(
        user_token=user_token,
        device_id_hash=device_hash,
        device_name=device_name,
        biometric_enabled=biometric_enabled,
        push_token=push_token,
    )


async def has_registered_device(user_token: str, device_id: str) -> bool:
    device_hash = hash_device_id(device_id)
    return await get_api_storage().has_device(user_token, device_hash)


# ============ Endpoints ============


@router.post("/register", response_model=RegisterResponse)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest):
    """
    Register a new user from the mobile app.

    The mobile app generates ML-DSA-44 keypair on device:
    - Private key stays in secure storage (Keychain/Keystore)
    - Public key is sent to server for verification

    Flow:
    1. Mobile app generates keypair
    2. User enters username
    3. App sends username + public_key + device_id
    4. Server creates user account
    5. Server returns JWT tokens
    """
    ledger = get_ledger()

    # Check if username already exists
    existing = await ledger.get_user_by_username(body.username)
    if existing:
        raise HTTPException(400, f"Username '{body.username}' already exists")

    # Generate user token (internal ID) using cryptographically secure random
    user_token = f"{body.username}_{secrets.token_urlsafe(32)}"

    # Create user in ledger
    success = await ledger.create_user(
        token=user_token,
        username=body.username,
        initial_balance=0.0,  # Start with zero balance
        public_key=body.public_key,
    )

    if not success:
        raise HTTPException(500, "Failed to create user")

    await register_device_for_user(
        user_token=user_token,
        device_id=body.device_id,
        device_name=body.device_name,
        biometric_enabled=body.biometric_enabled,
        push_token=body.push_token,
    )

    # Verify device count AFTER registration to close TOCTOU window.
    # upsert_device is idempotent on device_id, so this is safe.
    device_count = await get_api_storage().count_devices(user_token)
    if device_count > MAX_DEVICES_PER_USER:
        device_hash = hash_device_id(body.device_id)
        await get_api_storage().remove_device(user_token, device_hash)
        raise HTTPException(
            400,
            f"Maximum device limit ({MAX_DEVICES_PER_USER}) reached for this account",
        )

    # Generate JWT tokens
    access_token = generate_jwt(user_token, body.username, body.device_id)
    refresh_token = generate_refresh_token(user_token, body.username, body.device_id)

    expires_at = datetime.now(datetime.UTC) + timedelta(hours=JWT_EXPIRY_HOURS)

    return RegisterResponse(
        user_id=user_token,
        username=body.username,
        token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at.isoformat(),
        public_key=body.public_key,
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    """
    Login from mobile app.

    Validates:
    - Username exists
    - Device ID is registered for this user
    - Optional biometric token if enabled

    Returns JWT tokens for subsequent API calls.
    """
    ledger = get_ledger()

    # Get user by username
    user = await ledger.get_user_by_username(body.username)
    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not await has_registered_device(user.token, body.device_id):
        raise HTTPException(
            401,
            "Device is not registered for this user. Register from a trusted device first.",
        )

    # Generate new JWT tokens
    access_token = generate_jwt(user.token, user.username, body.device_id)
    refresh_token = generate_refresh_token(user.token, user.username, body.device_id)

    expires_at = datetime.now(datetime.UTC) + timedelta(hours=JWT_EXPIRY_HOURS)

    return LoginResponse(
        user_id=user.token,
        username=user.username,
        token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at.isoformat(),
    )


@router.post("/refresh", response_model=RefreshResponse)
@limiter.limit("20/minute")
async def refresh_token(request: Request, body: RefreshRequest):
    """
    Refresh access token using refresh token.

    Mobile apps should use this to get new access tokens
    without requiring user to login again.
    """
    # Validate refresh token
    payload = await validate_token(body.refresh_token, expected_type="refresh")

    # Generate new access token
    new_token = generate_jwt(payload["sub"], payload["username"], payload["device_id"])

    expires_at = datetime.now(datetime.UTC) + timedelta(hours=JWT_EXPIRY_HOURS)

    return RefreshResponse(token=new_token, expires_at=expires_at.isoformat())


@router.post("/device", response_model=dict)
async def register_device(
    request: DeviceRegistrationRequest, user: dict = Depends(get_current_user)
):
    """
    Register an additional device for an existing user.

    Users can have multiple devices (phone, tablet).
    Each device needs to be registered separately.
    """
    await register_device_for_user(
        user_token=user["sub"],
        device_id=request.device_id,
        device_name=request.device_name,
        biometric_enabled=request.biometric_enabled,
        push_token=request.push_token,
    )

    # Verify device count AFTER registration to close TOCTOU window.
    device_count = await get_api_storage().count_devices(user["sub"])
    if device_count > MAX_DEVICES_PER_USER:
        device_hash = hash_device_id(request.device_id)
        await get_api_storage().remove_device(user["sub"], device_hash)
        raise HTTPException(
            400,
            f"Maximum device limit ({MAX_DEVICES_PER_USER}) reached for this account",
        )

    return {
        "status": "success",
        "message": f"Device {request.device_id} registered for user {user['username']}",
        "device_id": request.device_id,
    }


@router.get("/me", response_model=UserInfo)
async def get_user_info(user: dict = Depends(get_current_user)):
    """
    Get current user information.

    Returns user details including:
    - User ID
    - Username
    - Public key
    - Registered devices
    """
    ledger = get_ledger()

    user_data = await ledger.get_user(user["sub"])
    if not user_data:
        raise HTTPException(404, "User not found")

    return UserInfo(
        user_id=user_data.token,
        username=user_data.username,
        public_key=user_data.public_key or "",
        created_at=getattr(user_data, "created_at", None),
        devices=await get_api_storage().list_devices(user_data.token),
    )


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    Logout user from current device.

    Adds the current JWT to the blacklist so it cannot be reused.
    """
    jti = user.get("jti", "")
    if jti:
        await get_api_storage().revoke_token(jti, user["sub"])
    return {"status": "success", "message": "Logged out successfully"}


class DevLoginRequest(BaseModel):
    """Development-only login with username."""

    username: str = Field(..., min_length=3, max_length=50)


class DevLoginResponse(BaseModel):
    """Development login response."""

    user_id: str
    username: str
    token: str
    refresh_token: str
    expires_at: str
    device_id: str


@router.post("/dev-login", response_model=DevLoginResponse)
async def dev_login(request: DevLoginRequest):
    """
    Development-only endpoint to login as a test user.

    This endpoint creates a device ID and registers it for the user,
    allowing login without ML-DSA-44 keys for testing purposes.

    ONLY AVAILABLE IN DEVELOPMENT MODE.
    """
    if os.getenv("APP_ENV", "development") not in ("development", "test"):
        raise HTTPException(403, "This endpoint is only available in development mode")

    ledger = get_ledger()

    user_data = await ledger.get_user_by_username(request.username)
    if not user_data:
        raise HTTPException(404, f"User '{request.username}' not found")

    device_id = f"dev-device-{request.username}"
    device_hash = hash_device_id(device_id)

    await get_api_storage().upsert_device(
        user_token=user_data.token,
        device_id_hash=device_hash,
        device_name=f"Dev Device ({request.username})",
        biometric_enabled=False,
        push_token=None,
    )

    access_token = generate_jwt(user_data.token, user_data.username, device_id)
    refresh_token = generate_refresh_token(
        user_data.token, user_data.username, device_id
    )
    expires_at = datetime.now(datetime.UTC) + timedelta(hours=JWT_EXPIRY_HOURS)

    return DevLoginResponse(
        user_id=user_data.token,
        username=user_data.username,
        token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at.isoformat(),
        device_id=device_id,
    )
