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

## Notes

- **Foundry Local must be running** for integration tests
- Tests use ports 8100 (A2A) and 8101 (MCP) to avoid conflicts
- Test database: `data/test_bank.db` (auto-cleaned)
- Production database: `data/bank.db`
