"""
Shared Azure Cosmos DB client for 42-Bank.

Reads connection from env (priority order):
  1. AZURE_COSMOS_CONNECTION_STRING
  2. COSMOS_ENDPOINT + COSMOS_KEY
  3. Localhost emulator defaults

For local dev: docker-compose up -d cosmos-emulator
Emulator defaults:
  endpoint: https://localhost:8081/
  key: C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==

Sync client: used by _init_db (container creation at startup).
Async client: used by all data-path operations (get/upsert/query/delete).
"""

import os
from typing import Optional

from azure.cosmos import ContainerProxy, CosmosClient, DatabaseProxy
from azure.cosmos.aio import ContainerProxy as AsyncContainerProxy
from azure.cosmos.aio import CosmosClient as AsyncCosmosClient
from azure.cosmos.aio import DatabaseProxy as AsyncDatabaseProxy

EMULATOR_ENDPOINT = "https://localhost:8081/"
EMULATOR_KEY = "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
EMULATOR_CONN_STR = f"AccountEndpoint={EMULATOR_ENDPOINT};AccountKey={EMULATOR_KEY}"

_cosmos_client: Optional[CosmosClient] = None
_async_cosmos_client: Optional[AsyncCosmosClient] = None


def get_cosmos_client() -> CosmosClient:
    """Return a singleton sync CosmosClient (used for startup/init only)."""
    global _cosmos_client
    if _cosmos_client is None:
        conn_str = os.getenv("AZURE_COSMOS_CONNECTION_STRING")
        if conn_str:
            _cosmos_client = CosmosClient.from_connection_string(
                conn_str, connection_verify=False, consistency_level="Session"
            )
        else:
            endpoint = os.getenv("COSMOS_ENDPOINT", EMULATOR_ENDPOINT)
            key = os.getenv("COSMOS_KEY", EMULATOR_KEY)
            _cosmos_client = CosmosClient(
                endpoint, key, connection_verify=False, consistency_level="Session"
            )
    return _cosmos_client


def get_database(db_name: Optional[str] = None) -> DatabaseProxy:
    db_name = db_name or os.getenv("COSMOS_DATABASE", "banking")
    return get_cosmos_client().get_database_client(db_name)


def get_container(container_name: str, db_name: Optional[str] = None) -> ContainerProxy:
    return get_database(db_name).get_container_client(container_name)


# ---------------------------------------------------------------------------
# Async client (used for all data-path IO in async FastAPI/A2A handlers)
# ---------------------------------------------------------------------------

def get_async_cosmos_client() -> AsyncCosmosClient:
    """Return a singleton async CosmosClient."""
    global _async_cosmos_client
    if _async_cosmos_client is None:
        conn_str = os.getenv("AZURE_COSMOS_CONNECTION_STRING")
        if conn_str:
            _async_cosmos_client = AsyncCosmosClient.from_connection_string(
                conn_str, connection_verify=False, consistency_level="Session"
            )
        else:
            endpoint = os.getenv("COSMOS_ENDPOINT", EMULATOR_ENDPOINT)
            key = os.getenv("COSMOS_KEY", EMULATOR_KEY)
            _async_cosmos_client = AsyncCosmosClient(
                endpoint, key, connection_verify=False, consistency_level="Session"
            )
    return _async_cosmos_client


def get_async_database(db_name: Optional[str] = None) -> AsyncDatabaseProxy:
    db_name = db_name or os.getenv("COSMOS_DATABASE", "banking")
    return get_async_cosmos_client().get_database_client(db_name)


def get_async_container(container_name: str, db_name: Optional[str] = None) -> AsyncContainerProxy:
    return get_async_database(db_name).get_container_client(container_name)
