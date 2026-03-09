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

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.deps import validate_jwt_configuration
from api.keys import router as keys_router
from api.notifications import router as notifications_router

# Create API app
validate_jwt_configuration()

app = FastAPI(
    title="42-Bank Mobile API",
    description="REST API for 42-Bank mobile app",
    version="1.0.0",
)

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

# Include routers
app.include_router(auth_router)
app.include_router(keys_router)
app.include_router(notifications_router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "42-bank-api"}
