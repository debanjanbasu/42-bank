"""
42-Bank API - Consolidated Single-Port Deployment with Integrated A2A

This module provides REST API endpoints for mobile app integration
and integrates A2A server routes directly (no mounting).
"""

import asyncio
import logging
import os
import time
import uuid as _uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from api.auth import router as auth_router
from api.deps import limiter, validate_env
from api.keys import router as keys_router
from api.notifications import router as notifications_router
from api.accounts import router as accounts_router

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
)
logger = logging.getLogger("42bank.api")


# Initialize A2A on startup using lifespan
@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Initialize A2A on startup."""
    import sys

    print("🚀 Starting FastAPI lifespan...", flush=True, file=sys.stderr)
    try:
        success = await initialize_a2a()
        if not success:
            print(
                "❌ A2A initialization failed on startup", flush=True, file=sys.stderr
            )
        print(
            f"✅ Lifespan complete, A2A initialized: {success}",
            flush=True,
            file=sys.stderr,
        )
    except Exception as e:
        print(f"❌ A2A lifespan exception: {e}", flush=True, file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)

    # Log mounted routes
    mounted_count = 0
    for route in fastapi_app.routes:
        if hasattr(route, "__class__") and "Mount" in route.__class__.__name__:
            mounted_count += 1
    logger.info(f"📊 Mounted routes: {mounted_count}")

    yield

    logger.info("🚀 FastAPI lifespan ending")


# Create API app with lifespan
app = FastAPI(
    title="42-Bank API",
    description=(
        "Consolidated API for 42-Bank. Provides authentication, "
        "key management, notifications, and A2A agent communication.\n\n"
        "## Authentication\n"
        "API key required: set `x-api-key` header\n"
        "Production mode: Bearer JWT token in `Authorization` header\n\n"
        "## Endpoints\n"
        "- `/api/*` - Mobile API endpoints\n"
        "- `/a2a/*` - A2A agent endpoints\n"
        "- `/api/health` - Health check\n"
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
        {
            "name": "accounts",
            "description": "Account management and balance queries.",
        },
    ],
    contact={"name": "42-Bank Team"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


@app.post("/api/seed")
async def seed_database(x_api_key: Optional[str] = Header(None)):
    """Seed the database with test users (alice, bob). Requires x-api-key header."""
    expected_key = os.getenv("AZURE_API_KEY", "")
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(401, "Invalid or missing x-api-key")

    from ledger import LedgerEngine

    ledger = LedgerEngine()
    results = []

    for username in ["alice", "bob"]:
        try:
            await ledger.create_user(username, f"{username}-pub-key")
            results.append(f"{username}: created")
        except Exception as e:
            if "already exists" in str(e).lower() or "conflict" in str(e).lower():
                results.append(f"{username}: already exists")
            else:
                results.append(f"{username}: error - {e}")

    return {"status": "ok", "results": results}


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
app.include_router(accounts_router)

validate_env()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "42-bank-api"}


# A2A Integration - Initialize lazily on first request
# This avoids blocking app startup and allows the app to function even if A2A fails
_a2a_initialized = False
_a2a_error = None


async def initialize_a2a():
    """Initialize A2A integration lazily."""
    global _a2a_initialized, _a2a_error

    logger.info(f"🔄 initialize_a2a called, _a2a_initialized={_a2a_initialized}")

    if _a2a_initialized:
        logger.info(f"✅ A2A already initialized, returning: {_a2a_error is None}")
        return _a2a_error is None

    try:
        logger.info("🔄 Initializing A2A integration...")

        # Import A2A server creation
        from a2a_server import create_a2a_app as create_a2a_starlette_app
        from identity import IdentityManager
        from ledger import LedgerEngine

        # Initialize dependencies
        identity = IdentityManager()
        ledger = LedgerEngine()

        # Get session token for default user
        username = "alice"
        try:
            session_token = identity.get_token(username)
            if not session_token:
                import hashlib

                session_token = hashlib.sha256(username.encode()).hexdigest()
                logger.info(f"⚠️ Using placeholder token for user '{username}'")
        except Exception as e:
            logger.warning(f"Could not get token for {username}: {e}")
            import hashlib

            session_token = hashlib.sha256(username.encode()).hexdigest()

        # Get configuration
        api_key = os.getenv("AZURE_API_KEY", "")
        mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")
        model_name = os.getenv("MODEL_NAME")

        # Create A2A app
        logger.info("🔄 Creating A2A application...")
        a2a_mode = (
            "local"
            if os.getenv("APP_ENV", "development") == "development"
            else "hosted"
        )
        a2a_app = await create_a2a_starlette_app(
            ledger=ledger,
            identity=identity,
            username=username,
            session_token=session_token,
            mode=a2a_mode,
            model_name=model_name,
            api_key=api_key,
            require_auth=False,
            mcp_server_url=mcp_server_url,
            host="0.0.0.0",
            port=8000,
        )

        # Mount A2A app at /a2a
        logger.info(f"🔄 Mounting A2A app at /a2a, routes count: {len(a2a_app.routes)}")
        app.mount("/a2a", a2a_app)
        logger.info("✅ A2A server mounted at /a2a")

        # Debug: List all routes after mounting
        logger.info(f"📊 Total app routes after mount: {len(app.routes)}")
        for route in app.routes:
            if hasattr(route, "path"):
                path = getattr(route, "path", "")
                if "/a2a" in path:
                    logger.info(f"  Found A2A route: {path}")

        _a2a_initialized = True
        return True

    except Exception as e:
        import traceback

        _a2a_error = str(e)
        logger.error(f"❌ A2A initialization failed: {e}")
        logger.error(traceback.format_exc())
        _a2a_initialized = True
        return False


# Add lazy initialization endpoint
@app.get("/a2a/initialize")
async def trigger_a2a_init():
    """Trigger A2A initialization."""
    success = await initialize_a2a()
    if success:
        return {"status": "initialized"}
    else:
        return {"status": "failed", "error": _a2a_error}
