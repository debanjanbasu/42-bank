# 42-Bank Testing Guide

## Test Suite Organization

We have **26 tests** in **3 categories**:

| Test File | Tests | Type | Assertion Strategy |
|-----------|-------|------|-------------------|
| `test_mcp_tools.py` | 9 | Deterministic | Exact string matching |
| `test_a2a_agents.py` | 10 | Non-deterministic | Flexible AI parsing |
| `test_e2e_flow.py` | 7 | Non-deterministic | Flexible AI parsing |

## Quick Start

```bash
# Ensure Foundry is running
foundry service status

# Run all tests
uv run pytest tests/ -v

# Run just fast deterministic tests
uv run pytest tests/test_mcp_tools.py -v
```

## Test Categories

### 1. MCP Tool Tests (Deterministic) ✅

Tests banking tools **directly** - no AI involved.

```python
# Example: test_check_balance_tool
result = await mcp_tool.call_tool("check_balance")
assert result == "Your checking account balance is $1000.00"  # Exact match OK!
```

**Why deterministic?** Tools are pure functions: same input = same output.

### 2. A2A Agent Tests (Non-Deterministic) ⚠️

Tests agents that use **LLMs** to generate natural language responses.

```python
# Example: test_inquiry_agent_balance
text = extract_text(response.json())
balance = extract_balance(text)
assert balance == 1000.0  # Flexible! Works with "$1000", "$1,000.00", etc.
```

**Why non-deterministic?** LLMs phrase answers differently: "balance is $1000" vs "$1,000.00 in your account".

### 3. E2E Flow Tests (Non-Deterministic) ⚠️

Tests complete user journeys through multiple agents.

```python
# Example: test_full_balance_check_flow  
# User → Triage → Inquiry → MCP tool → Database → Response
balance = extract_balance(text)
assert balance == 1000.0
```

## Helper Functions

Located in `tests/conftest.py`:

- **`extract_text(data)`**: Strips `<tool_call>` XML from responses
- **`extract_balance(text)`**: Extracts numeric balance (1000.0) from any phrasing

## Flexible Assertion Patterns

### ✅ DO

```python
# Extract numbers
balance = extract_balance(text)
assert balance == 1000.0

# Check keywords
assert any(word in text.lower() for word in ["success", "sent", "transferred"])

# Check presence
assert "bob" in text.lower()
```

### ❌ DON'T

```python
# Too brittle - breaks when LLM changes wording
assert "Your balance is $1000" in text
assert text == "Successfully sent $50"
```

## Test Infrastructure

### Fixtures

- **`test_db`**: Creates `data/test_bank.db` (Alice=$1000, Bob=$800)
- **`mcp_server`**: Starts MCP server on port 8101 with test database
- **`a2a_server`**: Starts A2A server on port 8100
- **`http_client`**: Shared async HTTP client

### Database Isolation

Tests use **separate test database** to avoid polluting production data.

### Foundry Discovery

Foundry runs on **random port** - tests auto-discover via `foundry service status`.

## Troubleshooting

### Tests Fail with "$0.00" Balance

**Problem**: Orphaned test servers using wrong database

**Solution**:
```bash
# Find servers
ps aux | grep -E "(mcp_server|a2a_server)"

# Kill them (replace PIDs)
kill <PID1> <PID2> ...

# Run tests fresh
uv run pytest tests/ -v
```

### "Failed to connect to Foundry"

**Problem**: Foundry not running

**Solution**:
```bash
foundry local start
```

### RuntimeError: Event loop is closed

**Status**: Harmless teardown issue - tests pass, ignore the error

## Running Subsets

```bash
# One test
uv run pytest tests/test_mcp_tools.py::test_check_balance_tool -v

# One file
uv run pytest tests/test_a2a_agents.py -v

# Skip slow tests
uv run pytest tests/ -m "not slow" -v
```

## CI/CD

### Fast CI (No Foundry)
```bash
pytest tests/test_mcp_tools.py  # Deterministic tests only
```

### Full Integration
```bash
# Requires Foundry Local or Azure AI Foundry
pytest tests/ -v
```

## Coverage

| Component | Status |
|-----------|--------|
| MCP Tools | ✅ All 6 tools |
| Agents | ✅ All 5 agents |
| Error Cases | ✅ Invalid users, insufficient funds |
| Multi-op Sequences | ✅ State consistency |

---

**Status**: ✅ 26 tests with flexible AI assertions  
**Updated**: 2026-02-17
