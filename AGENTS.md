# AGENTS.md - 42 Bank Multi-Agent Banking System

Guide for AI coding agents operating in this repository.

## Project Overview

42-Bank is a **mobile-first** quantum-safe multi-agent banking platform using:
- **Microsoft Agent Framework** with MCP (Model Context Protocol) and A2A (Agent-to-Agent) protocols
- **Azure Functions** with MCP Extension for serverless MCP tools
- **React Native / Expo 55** for cross-platform mobile app
- **ML-DSA-44** post-quantum cryptography for transaction signing

Features 5 specialized agents (Triage, Inquiry, Transaction, Advisor, Manager) and 9 banking tools.

---

## Database: Azure Cosmos DB (All Environments)

All environments — local development, CI, staging, and production — use **Azure Cosmos DB**.

- **Local dev**: Cosmos DB Linux emulator in Docker (`docker-compose up -d`)
- **Production**: Azure Cosmos DB managed service

```bash
# Local development (requires Docker Desktop)
docker-compose up -d        # Start Cosmos emulator
./dev.sh alice              # Bootstrap DB and start servers
```

Docker is **required** for local development. The emulator API runs at `https://localhost:8081/` and the Data Explorer UI at `http://localhost:1234/`.

### Cosmos Containers

| Container | Partition Key | Description |
|-----------|--------------|-------------|
| `users` | `/username` | User accounts, balances, transaction history |
| `change_feed` | `/event_type` | Audit log (transfers, logins) |
| `products` | `/type` | Banking product catalog |
| `auth_devices` | `/user_token` | Registered mobile devices |
| `key_backups` | `/user_token` | Encrypted key backups |
| `restore_challenges` | `/backup_id` | Key restore challenges |
| `token_blacklist` | `/jti` | Revoked JWT tokens |

### Key Modules

- `db/cosmos.py` — Sync and **async** Cosmos singletons; `get_container()` / `get_database()` (sync, used at init) and `get_async_container()` / `get_async_database()` (async, used for all data operations)
- `ledger.py` — `LedgerEngine` with fully **async** Cosmos-backed operations (`async def get_user`, `transfer`, `get_history`, etc.)
- `api/storage.py` — `APIStorage` with fully **async** Cosmos-backed device/key/token operations
- `audit_service.py` — `AuditLogger` with `async def log_event` / `log_transfer` / `log_login` writing to `change_feed` container

---

## Mobile App (Expo 55)

### Technology Stack
- **Expo SDK 55** - Latest React Native framework
- **React Native Paper 5** - Material Design 3 components
- **React Native Gifted Chat** - Chat UI component
- **noble-post-quantum** - ML-DSA-44 cryptography (JS/WASM)
- **react-native-keychain** - Secure storage (Keychain/Keystore)
- **expo-notifications** - Push notification registration and handling
- **@react-native-async-storage/async-storage** - Offline cache (accounts, transactions)

### Quick Start

```bash
# Terminal 1: Backend
./dev.sh alice

# Terminal 2: Mobile app
cd mobile
npm install
npx expo start --dev-client
# Press 'i' for iOS, 'a' for Android
```

### Known Issues & Patches

#### react-native-gifted-chat ColorSchemeName Error

**Problem:** `react-native-gifted-chat@3.3.2` has a type incompatibility with newer React Native. The library's `IGiftedChatContext` expects `getColorScheme()` to return `'light' | 'dark' | null | undefined`, but React Native's `ColorSchemeName` includes `'unspecified'`.

**Solution:** A patch is applied via `patch-package`:
- File: `mobile/patches/react-native-gifted-chat+3.3.2.patch`
- The patch casts `colorScheme` to the expected type: `colorScheme as 'light' | 'dark' | null | undefined`

**How it works:**
1. `patch-package` is installed as a dev dependency
2. The `postinstall` script in `package.json` automatically applies patches
3. After `npm install`, the patch fixes the type error in `node_modules`

**If you need to update the patch:**
```bash
cd mobile
# Edit the file in node_modules directly
# Then create a new patch:
npx patch-package react-native-gifted-chat
```

### Environment Configuration

The mobile app uses environment-based configuration:

```typescript
// mobile/src/config/env.ts
const ENVIRONMENTS = {
  development: { API_URL: 'http://localhost:8000' },
  staging: { API_URL: 'https://42bank-staging.azurewebsites.net' },
  production: { API_URL: 'https://42bank.azurewebsites.net' },
};
```

For physical device testing, override in `mobile/app.json`:
```json
{
  "expo": {
    "extra": {
      "apiUrl": "http://192.168.1.100:8000"
    }
  }
}
```

### Path Aliases

The mobile app uses TypeScript path aliases for clean imports:

```typescript
// ✅ Correct - use @ prefix (resolves to src/)
import { useAuth } from '@/contexts/AuthContext';
import { darkTheme } from '@/utils/theme';
import { API_URL } from '@/config/env';

// ❌ Wrong - don't include src in the path
import { useAuth } from '@/src/contexts/AuthContext';
```

This is configured in:
- `mobile/tsconfig.json` - TypeScript path mapping
- `mobile/babel.config.js` - Babel module resolver for Metro bundler

### Key Management Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Mobile Device                                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─────────────────────────────────────────────────────┐     │
│ │ KeyManager (src/services/KeyManager.ts)             │     │
│ │ • Uses @noble/post-quantum for ML-DSA-44            │     │
│ │ • Key generation in JavaScript/WASM                 │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                             │
│ ▼                                                           │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐     │
│ │ Secure Storage (react-native-keychain)              │     │
│ │ • iOS: Keychain + Secure Enclave                    │     │
│ │ • Android: Keystore + TEE                           │     │
│ │ • Private key encrypted, never leaves device        │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### ML-DSA-44 API Note

The `@noble/post-quantum` library uses `keygen()` (not `keypair()`) for key generation:

```typescript
// Correct API (v0.3.0+)
import { ml_dsa44 } from '@noble/post-quantum/ml-dsa';
const keys = ml_dsa44.keygen(seed);
// keys.publicKey, keys.secretKey

// Common mistake (older API)
// const keypair = ml_dsa44.keypair(seed); // ❌ Does not exist
```
┌─────────────────────────────────────────────────────────────┐
│ Mobile Device                                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ KeyManager (src/services/KeyManager.ts)             │   │
│  │ • Uses @noble/post-quantum for ML-DSA-44            │   │
│  │ • Key generation in JavaScript/WASM                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Secure Storage (react-native-keychain)              │   │
│  │ • iOS: Keychain + Secure Enclave                    │   │
│  │ • Android: Keystore + TEE                           │   │
│  │ • Private key encrypted, never leaves device        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Mobile App Structure

```
mobile/
├── app/
│   ├── _layout.tsx # Root layout (Paper + Auth)
│   ├── (auth)/
│   │   ├── _layout.tsx # Auth stack
│   │   ├── login.tsx # Login screen
│   │   └── register.tsx # Registration with key generation
│   ├── (tabs)/
│   │   ├── _layout.tsx # Tab navigation
│   │   ├── index.tsx # Chat screen (Gifted Chat)
│   │   ├── accounts.tsx # Account balances
│   │   ├── transactions.tsx # Transaction history
│   │   └── settings.tsx # Settings & logout
│   └── +not-found.tsx # 404
├── src/
│   ├── config/env.ts # Environment configuration
│   ├── services/
│   │   ├── A2AClient.ts # A2A protocol client (SSE streaming)
│   │   ├── APIClient.ts # Centralized HTTP client (15s timeout, typed errors)
│   │   ├── AuthService.ts # Auth API client
│   │   ├── CacheService.ts # Offline cache with 5-min TTL (AsyncStorage)
│   │   ├── KeyManager.ts # ML-DSA-44 key management
│   │   ├── NotificationService.ts # Push notification registration & listeners
│   │   └── StorageService.ts # Secure storage wrapper
│   ├── components/
│   │   ├── ErrorBoundary.tsx # React error boundary
│   │   └── TransactionConfirmModal.tsx # Biometric-gated signing confirmation sheet
│   ├── contexts/AuthContext.tsx # Auth state provider (push token, session timeout)
│   ├── hooks/
│   │   ├── useA2A.ts # A2A client hook
│   │   ├── useBiometric.ts # Biometric auth hook
│   │   └── useTransactionSigning.ts # Promise-based signing state machine
│   ├── utils/
│   │   ├── theme.ts # Paper theme config
│   │   └── crypto.ts # Crypto utilities
│   └── types/
│       ├── index.ts # TypeScript types
│       └── event-source-polyfill.d.ts # SSE type declarations
├── patches/
│   └── react-native-gifted-chat+3.3.2.patch # ColorSchemeName fix
├── assets/ # App icons, splash, etc.
├── babel.config.js # Babel config with path aliases
├── package.json # Expo 55 dependencies
├── app.json # Expo configuration
├── eas.json # EAS build config
└── tsconfig.json # TypeScript config
```

---

## Build/Lint/Test Commands

### Prerequisites
- **uv** - Python package manager (required)
- **Node.js 18+** - For mobile app development
- **Foundry Local** - Local LLM runtime (required for integration tests)
- Python 3.14+ (specified in `.python-version`)

### Python Backend

```bash
# Install dependencies
uv sync

# Initialize database
uv run python bootstrap.py

# Run all tests (requires Foundry Local running)
uv run pytest tests/ -v

# Run specific tests
uv run pytest tests/test_mcp_tools.py -v
uv run pytest tests/ -m mcp          # MCP tool tests only
uv run pytest tests/ -m a2a          # A2A agent tests only

# Type checking
pyright

# Start development servers
./dev.sh alice                      # Requires Docker Desktop + Cosmos emulator running
```

### Mobile App

```bash
cd mobile

# Install dependencies
npm install

# Run on iOS simulator
npm run ios

# Run on Android emulator
npm run android

# Start Metro bundler
npx expo start --dev-client

# Type checking
npm run typecheck

# Build development client
eas build --profile development --platform ios
eas build --profile development --platform android
```

---

## Azure Functions MCP Integration

### Architecture

42-Bank can deploy MCP tools as Azure Functions using the Azure Functions MCP Extension:

```
┌─────────────────────────────────────────────────────────────┐
│ Azure Functions App                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  MCP Tools (Function App)                                   │
│  ├── check_balance()      → @app.mcp_tool()                │
│  ├── send_money()         → @app.mcp_tool()                │
│  ├── get_history()        → @app.mcp_tool()                │
│  └── ...                                                    │
│                                                             │
│  Endpoint: /runtime/webhooks/mcp                           │
│  Auth: System key or OAuth                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Deployment

```bash
# Using Azure Developer CLI
azd env new 42-bank-prod
azd up

# Or manual deployment
az functionapp create --name 42bank-mcp --resource-group 42-bank \\
  --runtime python --runtime-version 3.11 --functions-version 4
```

### MCP Tool Definition (Azure Functions)

```python
import azure.functions as func

@app.mcp_tool()
@app.mcp_tool_property(arg_name="account_type", description="Account type")
def check_balance(account_type: str) -> str:
    """Check account balance."""
    balance = ledger.get_balance(token, account_type)
    return f"Your {account_type} balance is ${balance:.2f}"
```

### host.json Configuration

```json
{
  "version": "2.0",
  "extensions": {
    "mcp": {
      "serverName": "42-Bank-MCP",
      "serverVersion": "1.0.0",
      "instructions": "Banking tools for 42-Bank AI agents"
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle.Preview",
    "version": "[4.32.0, 5.0.0)"
  }
}
```

---

## Code Style Guidelines

### Python Version
- Target: Python 3.14+
- Specified in `.python-version`

### Imports
Group imports in this order, alphabetically sorted within each group:
```python
# 1. Standard library
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

# 2. Third-party packages
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import httpx

# 3. Local imports
from ledger import LedgerEngine
from identity import IdentityManager
from agent_framework import Agent
```

### Type Hints
- Use type hints for all function parameters and return types
- Import types from `typing` module
- Use Pydantic models for data structures

### Naming Conventions
- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: Prefix with `_`

### Error Messages
Use consistent prefixes:
```python
return "ERROR: Not initialized"
return f"FAILED: Insufficient funds. Balance: ${balance:.2f}"
```

---

## Testing Philosophy

### Test Categories

| Type | File | Assertion Strategy | Pass Rate |
|------|------|-------------------|-----------|
| Deterministic | `test_mcp_tools.py` | Exact string matching | 100% |
| Non-deterministic | `test_a2a_agents.py` | Flexible AI parsing | Variable |
| E2E | `test_e2e_flow.py` | Flexible AI parsing | Variable |

### When Writing Tests

**Deterministic (MCP Tools)**:
```python
result = await mcp_tool.call_tool("check_balance")
assert result == "Your checking account balance is $1000.00"
```

**Non-deterministic (AI Agents)**:
```python
balance = extract_balance(text)
assert balance == 1000.0
assert is_transaction_successful(text)
```

---

## Project Structure

```
42-bank/
├── a2a_server.py               # A2A server (5 agents, SSE streaming)
├── mcp_server.py               # MCP server (9 banking tools)
├── ledger.py                   # Transaction ledger (Cosmos DB/Pydantic)
├── identity.py                 # ML-DSA-44 cryptography
├── bootstrap.py                # Database initialization
├── dev.sh                      # Development startup script
│
├── bank_agents/                # Agent definitions
│   ├── triage.py               # Routes queries to specialists
│   ├── inquiry.py              # Balance, history queries
│   ├── transaction.py          # Send/request money
│   ├── advisor.py              # Products, account opening
│   └── manager.py              # Escalations, oversight
│
├── api/                        # Mobile backend API
│   ├── __init__.py             # FastAPI app with CORS
│   ├── auth.py                 # User registration & JWT auth
│   ├── keys.py                 # Key backup/restore
│   └── notifications.py        # Push notifications
│
├── mobile/                     # React Native / Expo app
│   ├── app/                    # Screens
│   ├── src/                    # Services, hooks, utils
│   ├── assets/                 # Icons, splash, etc.
│   └── package.json            # Expo 55 dependencies
│
├── tests/                      # Test suite
│   ├── conftest.py             # Fixtures and helpers
│   ├── test_mcp_tools.py       # Deterministic tool tests
│   ├── test_a2a_agents.py      # Agent tests
│   └── test_e2e_flow.py        # Integration tests
│
└── db/                         # Cosmos DB client
    ├── __init__.py
    └── cosmos.py               # Singleton client, get_container() helper
```

---

## Common Tasks

### Add New MCP Tool
1. Add `@mcp.tool()` function in `mcp_server.py`
2. Include docstring for tool discovery
3. Test: `uv run pytest tests/test_mcp_tools.py -v`

### Add New Mobile Screen
1. Create file in `mobile/app/(tabs)/` or `mobile/app/(auth)/`
2. Update layout file if needed
3. Test: `cd mobile && npx expo start --dev-client`

### Database Changes
1. Modify schema in `ledger.py` `_init_db()` method (Cosmos container definitions)
2. Update Pydantic models
3. Run `uv run python bootstrap.py` to reinitialize containers and seed data

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_COSMOS_CONNECTION_STRING` | Cosmos DB connection (local dev only) | `AccountEndpoint=...` (emulator) |
| `COSMOS_ENDPOINT` | Cosmos account URL (production) | `https://42bank-cosmos.documents.azure.com:443/` |
| `COSMOS_DATABASE` | Cosmos database name | `banking` (default) |
| `AZURE_AI_PROJECT_ENDPOINT` | Foundry project | `https://42-bank.cognitiveservices.azure.com/` |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Model deployment | `Qwen3.5-35B-A3B` |
| `JWT_SECRET` | JWT signing key (local dev) | In production: Container Apps encrypted secret |
| `APP_ENV` | Runtime environment | `development` / `staging` / `production` |

---

## Notes

- **Foundry Local must be running** for integration tests
- **Docker Desktop must be running** with `docker-compose up -d` for Cosmos emulator
- **Mobile app** is the primary client (CLI deprecated)
- Tests use ports 8100 (A2A) and 8101 (MCP) to avoid conflicts
- Each test function uses an isolated Cosmos DB database (deleted on teardown)
- `data/keys/` is still used by `IdentityManager` for ML-DSA-44 key files
- All Cosmos data operations are **async** (`azure.cosmos.aio`); `_init_db()` uses sync SDK at startup only
- **Auth**: production uses `DefaultAzureCredential` (managed identity) for Cosmos — no keys in env vars. Local dev uses `AZURE_COSMOS_CONNECTION_STRING` (emulator key)
- `JWT_SECRET` is passed as a `@secure()` Bicep parameter at deploy time and stored as a Container Apps encrypted secret — free, no Key Vault needed
- Push notifications require a physical device; simulator will skip token registration gracefully
