# ADR 0005 — Async Cosmos DB SDK (azure.cosmos.aio)

**Status:** Accepted  
**Date:** 2026-03-10

## Context

The initial Cosmos DB migration (ADR 0002) used the synchronous `azure.cosmos` SDK. All data-path methods in `ledger.py`, `api/storage.py`, and `audit_service.py` were sync functions called directly from FastAPI `async def` endpoints and A2A handlers.

This meant every database call (read, upsert, query, delete) **blocked the entire event loop** for the duration of the network round-trip to Cosmos DB. Under concurrent load — multiple users chatting, checking balances, or triggering transfers simultaneously — all requests would serialize behind each DB call.

FastMCP (used in `mcp_server.py`) and uvicorn run on asyncio event loops. Blocking the event loop in any of these causes latency spikes and connection queue buildup.

## Decision

Switch all data-path methods to `async def` using `azure.cosmos.aio` — the official async variant of the Azure Cosmos Python SDK. The sync SDK is retained **only** for `_init_db()` (container creation at startup), since that runs once before the event loop is fully engaged.

`db/cosmos.py` now exposes both:
- `get_container()` / `get_database()` — sync, used by `_init_db()` only
- `get_async_container()` / `get_async_database()` — async, used by all data operations

All public methods in `LedgerEngine`, `APIStorage`, and `AuditLogger` are now `async def`. FastAPI endpoints, A2A handlers, and MCP tools `await` them directly.

`utils.py` replaces `subprocess.run()` (blocking) with `asyncio.create_subprocess_exec()` in `get_foundry_local_endpoint_async()`. The result is cached in a module-level variable to avoid re-discovering the Foundry endpoint on every request.

## Consequences

**Positive:**
- Event loop is never blocked by IO; full concurrency under load
- Consistent `async/await` throughout the stack — no hidden blocking calls
- `get_foundry_local_endpoint_async()` with caching removes the repeated subprocess overhead

**Negative:**
- `_init_db()` still uses the sync SDK; mixing sync and async clients means two singleton objects in `db/cosmos.py`. Acceptable because init only runs once.
- Tests that create `LedgerEngine` / `APIStorage` instances must use `asyncio.run()` or `pytest-asyncio` fixtures for all data calls.
- `asyncio.run()` in `init_context()` (MCP server) wraps async initialization in a sync entry point; this is safe because MCP tools run before the main event loop starts.

## Alternatives Considered

- **Thread pool executor** (`loop.run_in_executor`) wrapping sync calls — avoids SDK change but adds thread overhead and hides the async nature of the code.
- **Keeping sync SDK everywhere** — simplest, but fundamentally wrong for an async web server under real load.
