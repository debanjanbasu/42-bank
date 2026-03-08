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

## Architecture Decision: SQLite vs Cosmos DB

### Current State (Local Development)
- **SQLite** is used for local development (`data/bank.db`)
- Works with `./dev.sh alice` for quick local testing
- **No external dependencies** required

### Production Deployment
- **Azure Cosmos DB** for production database
- **Azure Functions MCP Extension** for serverless MCP tools
- Hybrid approach: SQLite for dev, Cosmos DB for production

### Why Keep SQLite for Development?
1. **Zero setup**: No Docker, no emulator, no connection strings
2. **Fast iteration**: Tests run instantly without network latency
3. **Simple debugging**: SQLite file can be inspected directly
4. **Isolated tests**: Each test gets its own `test_bank.db`

### Migration Path
```bash
# Local development (default)
./dev.sh alice                           # Uses SQLite

# Local with Cosmos emulator (optional)
docker-compose up -d cosmos-emulator
DB_MODE=cosmos ./dev.sh alice

# Production
azd up                                   # Deploys to Cosmos DB + Azure Functions
```

---

## Mobile App (Expo 55)

### Technology Stack
- **Expo SDK 55** - Latest React Native framework
- **React Native Paper 5** - Material Design 3 components
- **React Native Gifted Chat** - Chat UI component
- **noble-post-quantum** - ML-DSA-44 cryptography (JS/WASM)
- **react-native-keychain** - Secure storage (Keychain/Keystore)

### Quick Start

```bash
# Terminal 1: Backend
./dev.sh alice

# Terminal 2: Mobile app
cd mobile
npm install
npm start
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
│   │   ├── AuthService.ts # Auth API client
│   │   ├── KeyManager.ts # ML-DSA-44 key management
│   │   └── StorageService.ts # Secure storage wrapper
│   ├── contexts/AuthContext.tsx # Auth state provider
│   ├── hooks/
│   │   ├── useA2A.ts # A2A client hook
│   │   └── useBiometric.ts # Biometric auth hook
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
./dev.sh alice                      # Quick start (SQLite)
DB_MODE=cosmos ./dev.sh alice       # With Cosmos emulator
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
npm start

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
import sqlite3
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
├── main.py                     # CLI client (deprecated, use mobile)
├── a2a_server.py               # A2A server (5 agents, SSE streaming)
├── mcp_server.py               # MCP server (9 banking tools)
├── ledger.py                   # Transaction ledger (SQLite/Pydantic)
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
└── data/                       # SQLite database
    └── bank.db
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
3. Test: `cd mobile && npm start`

### Database Changes
1. Modify schema in `ledger.py` `_init_db()` method
2. Update Pydantic models
3. Run `uv run python bootstrap.py` to reinitialize

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_MODE` | Database mode | `sqlite` or `cosmos` |
| `AZURE_COSMOS_CONNECTION_STRING` | Cosmos DB connection | `AccountEndpoint=...` |
| `AZURE_AI_PROJECT_ENDPOINT` | Foundry project | `https://42-bank.cognitiveservices.azure.com/` |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Model deployment | `Qwen3.5-35B-A3B` |
| `JWT_SECRET` | JWT signing key | (generate with secrets.token_urlsafe) |

---

## Notes

- **Foundry Local must be running** for integration tests
- **Mobile app** is the primary client (CLI deprecated)
- Tests use ports 8100 (A2A) and 8101 (MCP) to avoid conflicts
- Test database: `data/test_bank.db` (auto-cleaned)
- Production database: `data/bank.db`
- **SQLite for dev, Cosmos DB for production**
