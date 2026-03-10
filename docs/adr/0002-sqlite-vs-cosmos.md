# ADR 0002: Cosmos DB for All Environments

Date: 2026-03-10
Status: Accepted

## Context
Initial prototype used SQLite for local development (fast setup, no Docker required) with a DB_MODE=cosmos flag to switch to Azure Cosmos DB in production. This created an impedance mismatch: local tests ran against SQLite while production used a document database with different query semantics, partition keys, and consistency models.

## Decision
Use Azure Cosmos DB in all environments — local dev (emulator) and production. Docker Desktop is required for local development.

## Consequences
- **+** No impedance mismatch between local and production
- **+** True document model: nested accounts, transactions, pending_requests stored natively
- **+** Cosmos Change Feed available in all environments for audit/event streaming
- **-** Docker Desktop required for local development
- **-** Slightly slower test setup (emulator container vs in-process SQLite)

## Implementation
- `db/cosmos.py` is the single Cosmos client module
- `docker-compose.yml` starts the Cosmos Linux emulator (vNext preview)
- `bootstrap.py` seeds containers and data
- Tests use unique per-function database names (`banking_test_<uuid>`) for isolation
