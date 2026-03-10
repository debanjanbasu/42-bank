"""
Shared Azure Cosmos DB client for 42-Bank.

Auth strategy (priority order):
  1. AZURE_COSMOS_CONNECTION_STRING set → key-based auth (local dev / emulator)
  2. COSMOS_ENDPOINT set, no connection string → DefaultAzureCredential
     - Production: system-assigned managed identity on Container App
     - Local dev against real Azure: `az login` credentials
  3. Neither set → localhost emulator defaults (dev fallback)

Local dev:
  docker-compose up -d   # starts Cosmos emulator at https://localhost:8081/
  ./dev.sh alice         # sets AZURE_COSMOS_CONNECTION_STRING automatically

Sync client: used only by _init_db() (container creation at startup).
Async client: used by all data-path operations.
"""

import os
from typing import Optional

from azure.cosmos import ContainerProxy, CosmosClient, DatabaseProxy
from azure.cosmos.aio import ContainerProxy as AsyncContainerProxy
from azure.cosmos.aio import CosmosClient as AsyncCosmosClient
from azure.cosmos.aio import DatabaseProxy as AsyncDatabaseProxy
from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential

EMULATOR_ENDPOINT = "https://localhost:8081/"
EMULATOR_KEY = "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
EMULATOR_CONN_STR = f"AccountEndpoint={EMULATOR_ENDPOINT};AccountKey={EMULATOR_KEY}"

_cosmos_client: Optional[CosmosClient] = None
_async_cosmos_client: Optional[AsyncCosmosClient] = None


def _build_sync_client() -> CosmosClient:
    conn_str = os.getenv("AZURE_COSMOS_CONNECTION_STRING")
    if conn_str:
        return CosmosClient.from_connection_string(
            conn_str, connection_verify=False, consistency_level="Session"
        )
    endpoint = os.getenv("COSMOS_ENDPOINT")
    if endpoint:
        return CosmosClient(
            endpoint, credential=DefaultAzureCredential(), consistency_level="Session"
        )
    # Local dev fallback: emulator
    return CosmosClient.from_connection_string(
        EMULATOR_CONN_STR, connection_verify=False, consistency_level="Session"
    )


def _build_async_client() -> AsyncCosmosClient:
    conn_str = os.getenv("AZURE_COSMOS_CONNECTION_STRING")
    if conn_str:
        return AsyncCosmosClient.from_connection_string(
            conn_str, connection_verify=False, consistency_level="Session"
        )
    endpoint = os.getenv("COSMOS_ENDPOINT")
    if endpoint:
        return AsyncCosmosClient(
            endpoint, credential=AsyncDefaultAzureCredential(), consistency_level="Session"
        )
    return AsyncCosmosClient.from_connection_string(
        EMULATOR_CONN_STR, connection_verify=False, consistency_level="Session"
    )


def get_cosmos_client() -> CosmosClient:
    """Return a singleton sync CosmosClient (used for startup/init only)."""
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = _build_sync_client()
    return _cosmos_client


def get_database(db_name: Optional[str] = None) -> DatabaseProxy:
    db_name = db_name or os.getenv("COSMOS_DATABASE", "banking")
    return get_cosmos_client().get_database_client(db_name)


def get_container(container_name: str, db_name: Optional[str] = None) -> ContainerProxy:
    return get_database(db_name).get_container_client(container_name)


def get_async_cosmos_client() -> AsyncCosmosClient:
    """Return a singleton async CosmosClient."""
    global _async_cosmos_client
    if _async_cosmos_client is None:
        _async_cosmos_client = _build_async_client()
    return _async_cosmos_client


def get_async_database(db_name: Optional[str] = None) -> AsyncDatabaseProxy:
    db_name = db_name or os.getenv("COSMOS_DATABASE", "banking")
    return get_async_cosmos_client().get_database_client(db_name)


def get_async_container(container_name: str, db_name: Optional[str] = None) -> AsyncContainerProxy:
    return get_async_database(db_name).get_container_client(container_name)
