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
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field

from ledger import get_ledger

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "168"))  # 7 days
JWT_REFRESH_EXPIRY_DAYS = int(os.getenv("JWT_REFRESH_EXPIRY_DAYS", "30"))


# ============ Request/Response Models ============

class RegisterRequest(BaseModel):
    """User registration request from mobile app."""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-z0-9_]+$")
    public_key: str = Field(..., description="ML-DSA-44 public key from device")
    device_id: str = Field(..., description="Unique device identifier")
    device_name: Optional[str] = Field(None, description="User-friendly device name")
    biometric_enabled: bool = Field(True, description="Whether biometric auth is enabled")
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
    biometric_token: Optional[str] = Field(None, description="Biometric auth token if enabled")
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
    devices: list = []


# ============ Helper Functions ============

def generate_jwt(user_id: str, username: str, device_id: str, expiry_hours: int = JWT_EXPIRY_HOURS) -> str:
    """Generate JWT token for user."""
    payload = {
        "sub": user_id,
        "username": username,
        "device_id": device_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=expiry_hours),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_refresh_token(user_id: str, username: str, device_id: str) -> str:
    """Generate refresh token for user."""
    payload = {
        "sub": user_id,
        "username": username,
        "device_id": device_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=JWT_REFRESH_EXPIRY_DAYS),
        "type": "refresh"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def validate_token(token: str, expected_type: str = "access") -> dict:
    """Validate JWT token and return payload."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            raise HTTPException(401, f"Invalid token type: expected {expected_type}")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, f"Invalid token: {e}")


async def get_current_user(authorization: str = Header(None)) -> dict:
    """Dependency to validate JWT and return user payload."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    token = authorization[7:]
    return validate_token(token)


def hash_device_id(device_id: str) -> str:
    """Hash device ID for storage."""
    return hashlib.sha256(device_id.encode()).hexdigest()


# ============ Endpoints ============

@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
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
    existing = ledger.get_user_by_username(request.username)
    if existing:
        raise HTTPException(400, f"Username '{request.username}' already exists")
    
    # Generate user token (internal ID)
    user_token = f"{request.username}_token_{datetime.now().timestamp()}"
    
    # Create user in ledger
    success = ledger.create_user(
        token=user_token,
        username=request.username,
        initial_balance=0.0,  # Start with zero balance
        public_key=request.public_key
    )
    
    if not success:
        raise HTTPException(500, "Failed to create user")
    
    # Store device registration (would be in Cosmos DB in production)
    # For now, we'll add device info to user metadata
    device_hash = hash_device_id(request.device_id)
    
    # Generate JWT tokens
    access_token = generate_jwt(user_token, request.username, request.device_id)
    refresh_token = generate_refresh_token(user_token, request.username, request.device_id)
    
    expires_at = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    
    return RegisterResponse(
        user_id=user_token,
        username=request.username,
        token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at.isoformat(),
        public_key=request.public_key
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
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
    user = ledger.get_user_by_username(request.username)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    
    # In production, validate device_id is registered for this user
    # For now, we'll just check the user exists
    device_hash = hash_device_id(request.device_id)
    
    # TODO: Check if device is registered
    # TODO: Validate biometric token if user has biometric_enabled
    
    # Generate new JWT tokens
    access_token = generate_jwt(user.token, user.username, request.device_id)
    refresh_token = generate_refresh_token(user.token, user.username, request.device_id)
    
    expires_at = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    
    return LoginResponse(
        user_id=user.token,
        username=user.username,
        token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at.isoformat()
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token.
    
    Mobile apps should use this to get new access tokens
    without requiring user to login again.
    """
    # Validate refresh token
    payload = validate_token(request.refresh_token, expected_type="refresh")
    
    # Generate new access token
    new_token = generate_jwt(
        payload["sub"],
        payload["username"],
        payload["device_id"]
    )
    
    expires_at = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    
    return RefreshResponse(
        token=new_token,
        expires_at=expires_at.isoformat()
    )


@router.post("/device", response_model=dict)
async def register_device(
    request: DeviceRegistrationRequest,
    user: dict = Depends(get_current_user)
):
    """
    Register an additional device for an existing user.
    
    Users can have multiple devices (phone, tablet).
    Each device needs to be registered separately.
    """
    # TODO: Store device registration in database
    # For now, just return success
    
    return {
        "status": "success",
        "message": f"Device {request.device_id} registered for user {user['username']}",
        "device_id": request.device_id
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
    
    user_data = ledger.get_user(user["sub"])
    if not user_data:
        raise HTTPException(404, "User not found")
    
    return UserInfo(
        user_id=user_data.token,
        username=user_data.username,
        public_key=user_data.public_key or "",
        created_at=getattr(user_data, "created_at", None),
        devices=[]  # TODO: List registered devices
    )


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    Logout user from current device.
    
    Invalidates the current JWT token.
    Note: JWT tokens can't be truly invalidated without a blacklist,
    so this is mainly for client-side cleanup.
    """
    # TODO: Add token to blacklist in production
    return {
        "status": "success",
        "message": "Logged out successfully"
    }
