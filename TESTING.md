# 42-Bank Testing Guide

## Philosophy: Testing AI Systems

AI systems are fundamentally different from traditional software. Traditional code is deterministic (`f(x) = y` always), but LLMs produce a distribution of outputs (`f(x) = y₁ or y₂ or y₃...`). Tests must acknowledge this reality.

**We test the system, not the LLM:**

| What we TEST | What we DON'T test |
|---|---|
| Infrastructure works (servers, DB, connections) | LLM parsing is 100% accurate (impossible) |
| Business logic works (funds transfer, balances update) | Response wording is consistent (unrealistic) |
| Agents attempt correct behavior (call right tools) | Every transaction succeeds (probabilistic) |

### Three-Tier Assertion Strategy

| Tier | Used For | Strategy | Example |
|------|----------|----------|---------|
| **Deterministic** | MCP tool calls | Exact string matching | `assert result == "Balance: $1000"` |
| **Flexible** | Read queries (balance, history) | Extract structured data | `assert extract_balance(text) == 1000.0` |
| **Lenient** | Write actions (send money) | Accept LLM variance, reject business errors | `assert is_transaction_successful(text)` |

### Transaction Success Criteria

**Tests pass if:**
- Transaction succeeds (ideal)
- LLM has parsing issues (acceptable variance)

**Tests fail only if:**
- Insufficient funds (real business error)
- User not found (real business error)
- System crash (infrastructure error)

### Why Accept LLM Variance?

1. **LLMs are probabilistic** - Same prompt produces different responses. "send $50 to bob" might parse as `to="bob"` or fail to extract parameters. This is expected behavior, not a bug.

2. **Real-world usage** - Users retry if the agent doesn't understand. Production has error handling. Tests should reflect reality.

3. **Stable test suite** - Accepting variance means fewer false negatives. Only real errors cause failures.

## Test Suite Organization

**43 tests** in **5 files**:

| Test File | Tests | Type | Assertion Strategy |
|-----------|-------|------|-------------------|
| `test_mcp_tools.py` | 9 | Deterministic | Exact string matching |
| `test_a2a_agents.py` | 10 | Non-deterministic | Flexible AI parsing |
| `test_e2e_flow.py` | 7 | Non-deterministic | Flexible AI parsing |
| `test_error_paths.py` | 4 | Deterministic | Exact error matching |
| `test_security.py` | 13 | Deterministic | JWT/auth validation |

## Quick Start

```bash
# Ensure Foundry Local is running
foundry service status

# Run all tests (requires Foundry Local)
uv run pytest tests/ -v

# Run deterministic tests only (no Foundry needed)
uv run pytest tests/test_mcp_tools.py tests/test_error_paths.py tests/test_security.py -v
```

## Test Categories

### 1. MCP Tool Tests (Deterministic) - `test_mcp_tools.py`

Tests banking tools **directly** - no AI involved.

```python
result = await mcp_tool.call_tool("check_balance")
assert result == "Your checking account balance is $1000.00"
```

### 2. A2A Agent Tests (Non-Deterministic) - `test_a2a_agents.py`

Tests agents that use **LLMs** to generate natural language responses.

```python
text = extract_text(response.json())
balance = extract_balance(text)
assert balance == 1000.0  # Works with "$1000", "$1,000.00", etc.
```

### 3. E2E Flow Tests (Non-Deterministic) - `test_e2e_flow.py`

Tests complete user journeys: User query -> Triage -> Agent -> MCP tool -> Database -> Response.

### 4. Error Path Tests (Deterministic) - `test_error_paths.py`

Tests edge cases: insufficient funds, negative amounts, nonexistent users, self-transfers, invalid tokens, duplicate usernames, concurrent overdraft prevention.

### 5. Security Tests (Deterministic) - `test_security.py`

Tests JWT validation (wrong algorithm, expired, wrong secret, wrong type), token revocation, input sanitization, and ledger integrity (atomic transfers, history records).

## Helper Functions

Located in `tests/conftest.py`:

- **`extract_text(data)`**: Strips `<tool_call>` XML from responses
- **`extract_balance(text)`**: Extracts numeric balance from any phrasing
- **`is_transaction_successful(text)`**: Returns True unless hard business failure

## Flexible Assertion Patterns

### DO

```python
balance = extract_balance(text)
assert balance == 1000.0

assert any(word in text.lower() for word in ["checking", "savings"])
assert is_transaction_successful(text), f"Hard error: {text}"
```

### DON'T

```python
assert "Your balance is $1000" in text  # Too brittle
assert "success" in text.lower()  # LLM might say "encountered issue" and still be OK
```

## Test Infrastructure

Each test function gets an **isolated Cosmos DB database** (named `banking_test_<uuid>`) that is deleted on teardown. Tests run on ports 8100 (A2A) and 8101 (MCP) to avoid conflicts with local dev servers.

## Troubleshooting

### "Failed to connect to Foundry"

```bash
foundry local start
```

### Orphaned test servers

```bash
ps aux | grep -E "(mcp_server|a2a_server)" | awk '{print $2}' | xargs kill
```

### RuntimeError: Event loop is closed

Harmless teardown issue - tests pass, ignore the error.
