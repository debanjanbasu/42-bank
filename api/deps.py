import os
from typing import Any, Optional

import jwt
from fastapi import Header, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.storage import get_api_storage


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"

limiter = Limiter(key_func=get_remote_address)


def validate_jwt_configuration() -> None:
    env = os.getenv("APP_ENV", "development").lower()
    requires_strong_secret = env in {"production", "staging"}

    if JWT_SECRET == "dev-secret-change-in-production" or len(JWT_SECRET) < 32:
        if requires_strong_secret:
            raise RuntimeError(
                "JWT_SECRET must be explicitly configured with at least 32 characters in staging/production"
            )
        if os.getenv("REQUIRE_STRONG_SECRETS"):
            raise RuntimeError(
                "JWT_SECRET is using insecure default. Set JWT_SECRET or unset REQUIRE_STRONG_SECRETS."
            )


async def validate_token(token: str, expected_type: Optional[str] = "access") -> dict[str, Any]:
    """Decode and validate a JWT token, checking expiry, type, and revocation."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(401, "Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(401, "Invalid token") from exc

    if expected_type and payload.get("type") != expected_type:
        raise HTTPException(401, f"Invalid token type: expected {expected_type}")

    jti = payload.get("jti", "")
    if jti and await get_api_storage().is_token_revoked(jti):
        raise HTTPException(401, "Token has been revoked")

    return payload


async def get_current_user(authorization: str = Header(None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    return await validate_token(authorization[7:])


def validate_env() -> None:
    """Validate required environment variables are set. Called at startup."""
    env = os.getenv("APP_ENV", "development").lower()

    warnings_list: list[str] = []
    errors: list[str] = []

    if JWT_SECRET == "dev-secret-change-in-production":
        if env in ("production", "staging"):
            errors.append("JWT_SECRET must be set in production/staging")
        else:
            warnings_list.append(
                "JWT_SECRET is using default dev value — set JWT_SECRET for security"
            )

    if env in ("production", "staging"):
        if not os.getenv("AZURE_AI_PROJECT_ENDPOINT"):
            warnings_list.append(
                "AZURE_AI_PROJECT_ENDPOINT not set — Azure AI features disabled"
            )

    if warnings_list:
        import warnings as _w
        for w in warnings_list:
            _w.warn(w, stacklevel=2)

    if errors:
        raise RuntimeError(
            "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
        )
