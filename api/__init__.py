"""
42-Bank Mobile API

This module provides REST API endpoints for mobile app integration.

Modules:
    auth - User registration and authentication
    keys - Key backup and restore
    notifications - Push notifications

Usage:
    from api import app
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

import logging
import os
import time
import uuid as _uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from api.auth import router as auth_router
from api.deps import limiter, validate_env, validate_jwt_configuration
from api.keys import router as keys_router
from api.notifications import router as notifications_router

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
)
logger = logging.getLogger("42bank.api")

# Create API app
validate_jwt_configuration()

app = FastAPI(
    title="42-Bank Mobile API",
    description=(
        "REST API for the 42-Bank mobile app. Provides authentication, "
        "key management, and push notifications for the quantum-safe "
        "multi-agent banking platform.\n\n"
        "## Authentication\n"
        "Most endpoints require a Bearer JWT in the `Authorization` header:\n"
        "```\nAuthorization: Bearer <access_token>\n```\n\n"
        "## Rate Limits\n"
        "- `/api/auth/register`: 5 requests/minute\n"
        "- `/api/auth/login`: 10 requests/minute\n"
        "- `/api/auth/refresh`: 20 requests/minute\n"
    ),
    version="1.0.0",
    openapi_tags=[
        {
            "name": "authentication",
            "description": "User registration, login, token refresh, device management.",
        },
        {
            "name": "key-management",
            "description": "ML-DSA-44 key backup, restore challenges, and status.",
        },
        {
            "name": "notifications",
            "description": "Push notification registration, history, and preferences.",
        },
    ],
    contact={"name": "42-Bank Team"},
    license_info={"name": "MIT"},
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# CORS for mobile app
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
allow_credentials = "*" not in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(_uuid.uuid4())[:8]
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 2)
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


# Include routers
app.include_router(auth_router)
app.include_router(keys_router)
app.include_router(notifications_router)

validate_env()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "42-bank-api"}
