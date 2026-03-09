import os
from typing import Any, Optional

import jwt
from fastapi import Header, HTTPException


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"


def validate_jwt_configuration() -> None:
    env = os.getenv("APP_ENV", "development").lower()
    requires_strong_secret = env in {"production", "staging"}
    if not requires_strong_secret:
        return

    if JWT_SECRET == "dev-secret-change-in-production" or len(JWT_SECRET) < 32:
        raise RuntimeError(
            "JWT_SECRET must be explicitly configured with at least 32 characters in staging/production"
        )


def validate_token(token: str, expected_type: Optional[str] = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(401, "Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(401, "Invalid token") from exc

    if expected_type and payload.get("type") != expected_type:
        raise HTTPException(401, f"Invalid token type: expected {expected_type}")
    return payload


async def get_current_user(authorization: str = Header(None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    return validate_token(authorization[7:])
