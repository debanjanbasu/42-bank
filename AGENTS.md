# AGENTS.md - 42 Bank Multi-Agent Banking System

Guide for AI coding agents operating in this repository.

## Project Overview

42-Bank is a quantum-safe multi-agent banking platform using Microsoft Agent Framework with MCP (Model Context Protocol) and A2A (Agent-to-Agent) protocols. Features 5 specialized agents (Triage, Inquiry, Transaction, Advisor, Manager) and 9 banking tools.

---

## Build/Lint/Test Commands

### Prerequisites
- **uv** - Python package manager (required)
- **Foundry Local** - Local LLM runtime (required for integration tests)
- Python 3.14+ (specified in `.python-version`)

### Install Dependencies
```bash
uv sync
```

### Initialize Database
```bash
uv run python bootstrap.py
```

### Run Tests

```bash
# Run all tests (requires Foundry Local running)
uv run pytest tests/ -v

# Run single test file
uv run pytest tests/test_mcp_tools.py -v

# Run single test
uv run pytest tests/test_mcp_tools.py::test_check_balance_tool -v

# Run tests by marker
uv run pytest tests/ -m mcp      # MCP tool tests only (deterministic)
uv run pytest tests/ -m a2a      # A2A agent tests only
uv run pytest tests/ -m e2e      # E2E integration tests only
uv run pytest tests/ -m "not slow" -v  # Skip slow tests

# Run with coverage
uv run pytest tests/ --cov=. --cov-report=html
```

### Type Checking
```bash
# Pyright is configured in pyrightconfig.json
# Standard type checking mode
pyright
```

### Start Development Servers
```bash
# Quick start (starts MCP + A2A servers)
./dev.sh alice

# Manual start
uv run python mcp_server.py --http --user alice --port 8001  # MCP server
uv run python a2a_server.py --user alice --port 8000        # A2A server
uv run main.py --user alice                                  # CLI client
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
- Import types from `typing` module (Any, Dict, List, Optional, Protocol, etc.)
- Use Pydantic models for data structures

```python
def get_balance(self, token: str, account_type: str = "checking") -> float:
    ...

def transfer(
    self,
    sender_token: str,
    recipient_username: str,
    amount: float,
    description: str,
    from_account: str = "checking",
    to_account: str = "checking",
    signature: Optional[str] = None,
) -> bool:
    ...
```

### Naming Conventions
- **Functions/Variables**: `snake_case` (e.g., `check_balance`, `get_token_by_username`)
- **Classes**: `PascalCase` (e.g., `LedgerEngine`, `UserAccount`, `Transaction`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `TEST_DB`, `HISTORY_FILE`)
- **Private methods**: Prefix with `_` (e.g., `_get_user`, `_save_user`, `_init_db`)
- **Protocol classes**: Suffix with `Protocol` (e.g., `ChatClientProtocol`)

### Pydantic Models
Use Pydantic BaseModel for data structures:
```python
class Transaction(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    sender: str
    recipient: str
    amount: float
    description: str
    account_type: str = "checking"


class UserAccount(BaseModel):
    token: str
    username: str
    public_key: Optional[str] = None
    accounts: Dict[str, AccountData] = Field(default_factory=lambda: {...})
```

### Formatting
- **Indentation**: 4 spaces
- **Line length**: ~100 characters (flexible)
- **Blank lines**: 2 blank lines between top-level functions/classes
- **Docstrings**: Triple-quoted for modules and public functions

### Docstrings
```python
def transfer(
    self,
    sender_token: str,
    recipient_username: str,
    amount: float,
    description: str,
) -> bool:
    """
    Transfer funds between users atomically.

    Returns:
        bool: True if transfer succeeded, False otherwise
    """
```

### Error Messages
Use consistent prefixes for error messages:
```python
# Service/initialization errors
return "ERROR: Not initialized"
return "ERROR: Service not initialized"

# Business logic failures
return f"FAILED: Insufficient funds. Balance: ${balance:.2f}"
return f"FAILED: User '{to}' not found."
return "FAILED: Amount must be positive."
```

---

## Testing Philosophy

### Critical: AI Testing is Different

This project tests **LLM-based agents**. Standard deterministic testing doesn't apply.

### Three Test Categories

| Type | File | Assertion Strategy | Pass Rate |
|------|------|-------------------|-----------|
| Deterministic | `test_mcp_tools.py` | Exact string matching | 100% |
| Non-deterministic | `test_a2a_agents.py` | Flexible AI parsing | Variable |
| E2E | `test_e2e_flow.py` | Flexible AI parsing | Variable |

### When Writing Tests

**Deterministic (MCP Tools)** - Use exact assertions:
```python
result = await mcp_tool.call_tool("check_balance")
assert result == "Your checking account balance is $1000.00"
```

**Non-deterministic (AI Agents)** - Use flexible assertions:
```python
# Extract numeric values (handles formatting variance)
balance = extract_balance(text)
assert balance == 1000.0

# For transactions - accept LLM variance
assert is_transaction_successful(text)  # True unless hard business error
```

### Helper Functions (in `tests/conftest.py`)

- `extract_text(response_data)` - Strip tool call XML from responses
- `extract_balance(text)` - Extract numeric balance (handles "$1000", "$1,000.00")
- `is_transaction_successful(text)` - Returns True unless hard business failure

### What NOT to Test

- LLM parsing perfection (probabilistic, not deterministic)
- Exact response wording ("transferred" vs "sent")
- Parameter extraction success rate

---

## Project Structure

```
42-bank/
├── main.py              # CLI client (A2A HTTP client)
├── a2a_server.py        # A2A server (5 agents, SSE streaming)
├── mcp_server.py        # MCP server (9 banking tools)
├── mcp_client.py        # MCPStreamableHTTPTool helper
├── ledger.py            # Transaction ledger (SQLite + Pydantic)
├── identity.py          # ML-DSA-44 post-quantum cryptography
├── bootstrap.py         # Database initialization
├── utils.py             # Shared utilities (Foundry discovery)
├── audit_service.py     # Audit logging
├── dev.sh               # Development startup script
│
├── bank_agents/         # Agent definitions
│   ├── __init__.py
│   ├── triage.py        # Routes queries to specialists
│   ├── inquiry.py       # Balance, history queries
│   ├── transaction.py   # Send/request money
│   ├── advisor.py       # Products, account opening
│   └── manager.py       # Escalations, oversight
│
├── tests/               # Test suite
│   ├── conftest.py      # Fixtures and helpers
│   ├── test_mcp_tools.py    # Deterministic tool tests
│   ├── test_a2a_agents.py   # Agent tests
│   └── test_e2e_flow.py     # Integration tests
│
└── data/                # SQLite database
    └── bank.db
```

---

## Agent Development

### Agent Pattern
All agents follow this structure:
```python
from typing import Protocol, Any, Optional, Sequence
from agent_framework import Agent

class ChatClientProtocol(Protocol):
    def as_agent(
        self,
        *,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[Sequence[Any]] = None,
    ) -> Agent: ...

def get_agent(client: ChatClientProtocol, tools) -> Agent:
    instructions = (
        "CRITICAL: You MUST respond ONLY in English.\n"
        "You are AgentName. You handle [domain].\n"
        "ALWAYS call the appropriate tool:\n"
        "- [condition] → call [tool_name]()\n"
    )
    return client.as_agent(
        name="AgentName",
        instructions=instructions,
        tools=tools,
    )
```

### Agent Instructions Best Practices
- Use UPPERCASE for critical directives ("CRITICAL:", "ALWAYS:", "NEVER:")
- Specify tool mappings explicitly
- Include response format requirements
- Language constraints (English only)

---

## MCP Tool Development

### Tool Pattern
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("42-bank-tools")

@mcp.tool()
def check_balance() -> str:
    """View your checking account balance."""
    if not _ledger or not _session_token:
        return "ERROR: Not initialized"
    balance = _ledger.get_balance(_session_token, "checking")
    return f"Your checking account balance is ${balance:.2f}"
```

### Tool Guidelines
- All tools must have docstrings (used by LLM for tool selection)
- Return strings for human-readable output
- Return structured data (lists, dicts) for programmatic use
- Validate inputs at the start of the function
- Check initialization state before operations

---

## Error Handling

### In MCP Tools
```python
# Check initialization
if not _ledger or not _session_token:
    return "ERROR: Not initialized"

# Validate inputs
if amount <= 0:
    return "FAILED: Amount must be positive."
if not recipient_username:
    return "FAILED: Recipient username required."

# Check business constraints
if balance < amount:
    return f"FAILED: Insufficient funds. Balance: ${balance:.2f}"
```

### In Ledger Methods
```python
def transfer(...) -> bool:
    # Validate inputs
    if amount <= 0:
        return False
    if not recipient_username:
        return False

    # Check business rules
    if s_user.accounts[from_account].balance < amount:
        return False

    # Execute atomically
    with sqlite3.connect(self.db_path) as conn:
        self._save_user(s_user, conn)
        self._save_user(r_user, conn)
    return True
```

---

## Configuration Files

- `pyproject.toml` - Project dependencies, pytest config, uv settings
- `pyrightconfig.json` - Type checking configuration (standard mode)
- `.python-version` - Python version (3.14)
- `host.json` / `host.a2a.json` - Azure Functions configuration

---

## Common Tasks

### Add New MCP Tool
1. Add `@mcp.tool()` decorated function in `mcp_server.py`
2. Include docstring (used by LLM for tool discovery)
3. Validate inputs and return appropriate error messages
4. Test with: `uv run pytest tests/test_mcp_tools.py -v`

### Add New Agent
1. Create file in `bank_agents/` following existing patterns
2. Import and register in `a2a_server.py`
3. Add routing rules to `triage.py` if needed
4. Test with: `uv run pytest tests/test_a2a_agents.py -v`

### Database Changes
1. Modify schema in `ledger.py` `_init_db()` method
2. Update Pydantic models as needed
3. Run `uv run python bootstrap.py` to reinitialize

---

## Azure Deployment

### Architecture

42-Bank supports dual deployment:
- **Local**: SQLite + Foundry Local (default)
- **Azure**: Cosmos DB + Azure AI Foundry

### Database Abstraction

The `cosmos_mcp_client.py` module provides Cosmos DB integration:

```python
from cosmos_mcp_client import CosmosMCPClient

# Auto-selects based on environment
# Cosmos if COSMOS_MCP_URL is set, SQLite otherwise
```

### Local Development with Cosmos DB Emulator

```bash
# Start emulator (Docker required)
docker-compose up -d cosmos-emulator

# Initialize database
uv run python scripts/init-cosmos-local.py

# Run with Cosmos
DB_MODE=cosmos ./dev.sh alice
```

### Azure Deployment Commands

```bash
# Deploy infrastructure
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep

# Deploy Cosmos DB MCP Toolkit (Microsoft)
git clone https://github.com/AzureCosmosDB/MCPToolKit.git
cd MCPToolKit && azd up

# Deploy Banking MCP Server
docker build -f Dockerfile.banking-mcp -t 42bank-banking-mcp .
az containerapp create --name 42bank-banking-mcp --image 42bank-banking-mcp
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_MODE` | Database mode | `sqlite` or `cosmos` |
| `AZURE_COSMOS_CONNECTION_STRING` | Cosmos DB connection | `AccountEndpoint=...;AccountKey=...` |
| `COSMOS_MCP_URL` | MCP Toolkit URL | `https://cosmos-mcp.azurecontainerapps.io/mcp` |
| `COSMOS_DATABASE` | Database name | `banking` |
| `AZURE_AI_PROJECT_ENDPOINT` | Foundry project | `https://42-bank.cognitiveservices.azure.com/` |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Model deployment | `Qwen/Qwen3.5-35B-A3B` |

### Model Selection

- **Qwen3.5-35B-A3B** (recommended): Cheapest MoE, 3B active params
- **Qwen3.5-27B**: Best instruction-following (95.0 IFEval)
- **GPT-4o-mini**: OpenAI ecosystem

### Files Created

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local Cosmos emulator setup |
| `scripts/init-cosmos-local.py` | Database initialization |
| `cosmos_mcp_client.py` | Cosmos DB MCP client |
| `mcp_banking_server.py` | Banking MCP wrapper |
| `Dockerfile.banking-mcp` | Container build |
| `infra/main.bicep` | Azure infrastructure |
| `AZURE_DEPLOYMENT.md` | Deployment guide |

---

## Docker Commands

### Cosmos DB Emulator

```bash
# Start
docker-compose up -d cosmos-emulator

# Check status
docker-compose ps

# View logs
docker-compose logs -f cosmos-emulator

# Stop
docker-compose down

# Reset data
docker-compose down -v
```

### Health Checks

```bash
# Cosmos emulator
curl -sk https://localhost:8081/_explorer/index.html

# Data explorer (browser)
open https://localhost:1234/_explorer/index.html

# Banking MCP server
curl http://localhost:8002/health
```

---

## Testing with Cosmos DB

### Integration Tests

```bash
# Run tests with Cosmos emulator
DB_MODE=cosmos uv run pytest tests/ -v

# Specific Cosmos tests
uv run pytest tests/ -m cosmos
```

### Seed Data

```bash
# Initialize test data
uv run python scripts/init-cosmos-local.py

# Verify
curl -sk https://localhost:8081/_explorer/index.html
```

---

## Notes

- **Foundry Local must be running** for integration tests
- Tests use ports 8100 (A2A) and 8101 (MCP) to avoid conflicts
- Test database: `data/test_bank.db` (auto-cleaned)
- Production database: `data/bank.db`
- **Cosmos emulator** requires Docker and ~2GB RAM
- **Local development** defaults to SQLite (no Docker required)
