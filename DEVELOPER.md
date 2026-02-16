# 42 Bank - Developer Guide

## Local Development Setup

### 1. Start Foundry Local

```bash
# Start Phi-4-mini locally (recommended for development)
foundry model run Phi-4-mini-instruct-generic-gpu:5

# Verify model is running
foundry model list
```

### 2. Initialize Platform

```bash
# Install dependencies and initialize database
uv run bootstrap.py
```

This creates:
- ML-DSA-44 cryptographic keys in `data/keys/`
- SQLite database with test users:
  - alice: $1,000 checking balance
  - bob: $500 checking balance

### 3. Configure Environment

```bash
cp .env.example .env
# Defaults are configured for local development
```

---

## Running Modes

### CLI Chat (Interactive)

Test the multi-agent banking workflow locally:

```bash
uv run main.py --user alice
```

Try queries like:
- "What's my balance?"
- "Send $50 to bob"
- "Show transaction history"
- "What products do you offer?"

### Hosted Agent (Local Testing)

Test the Azure-deployable agent locally:

```bash
# Starts server on http://localhost:8088
uv run hosted_agent.py

# Test from another terminal
curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input": "Check my balance"}'
```

### A2A Server (Agent Integration)

Run A2A server for external agent integration:

```bash
# Start on port 8000
uv run main.py --a2a --user alice --port 8000
```

### MCP Server (Tool Exposure)

Run MCP server to expose banking tools:

```bash
# HTTP mode (port 8001)
uv run main.py --mcp --user alice --port 8001

# stdio mode (for Claude Desktop, etc.)
uv run main.py --mcp --stdio --user alice
```

### Visual DevUI

Debug agent interactions with visual interface:

```bash
uv run main.py --user alice --devui
# Opens browser at http://localhost:8081
```

---

## Protocol Integration

### A2A Protocol (Agent-to-Agent)

**When to use**: Integrating with other agents that need to discover and call your banking agents.

#### Agent Discovery

```bash
curl http://localhost:8000/a2a/triage
```

Returns agent card with capabilities:
```json
{
  "name": "42-Bank-TriageAgent",
  "description": "Routes banking queries to specialized agents",
  "version": "1.0.0",
  "capabilities": { "streaming": true },
  "skills": [...]
}
```

#### Send Message

```bash
curl -X POST http://localhost:8000/a2a/transaction/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "kind": "message",
      "role": "user",
      "parts": [{"kind": "text", "text": "Send $50 to bob"}],
      "contextId": "test-123"
    }
  }'
```

#### Python A2A Client

```python
import asyncio
import httpx
from a2a.client import A2ACardResolver
from agent_framework.a2a import A2AAgent

async def main():
    async with httpx.AsyncClient() as client:
        resolver = A2ACardResolver(httpx_client=client, base_url="http://localhost:8000")
        card = await resolver.get_agent_card("/a2a/transaction")
        
        async with A2AAgent(name="transaction", agent_card=card, 
                           url="http://localhost:8000/a2a/transaction") as agent:
            response = await agent.run("Send $50 to bob")
            print(response.messages[0].text)

asyncio.run(main())
```

---

### MCP Protocol (Model Context Protocol)

**When to use**: Exposing banking tools to MCP-compatible clients (Claude Desktop, Cursor, etc.).

#### Connect via SSE (HTTP Mode)

```javascript
const eventSource = new EventSource('http://localhost:8001/sse');
eventSource.onmessage = (event) => console.log(event.data);
```

#### List Available Tools

```bash
curl http://localhost:8001/tools
```

Returns all 9 banking tools with schemas.

#### Python MCP Client

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "main.py", "--mcp", "--stdio", "--user", "alice"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")
            
            # Call a tool
            result = await session.call_tool("check_balance", {"account_type": "checking"})
            print(result.content[0].text)
```

#### Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "42-bank": {
      "command": "uv",
      "args": ["run", "main.py", "--mcp", "--stdio", "--user", "alice"]
    }
  }
}
```

Restart Claude Desktop, and banking tools will be available in chats.

---

---

## Multi-Agent Architecture

### Agent Workflow

```
┌─────────────┐
│ TriageAgent │ (Entry point - routes queries)
└──────┬──────┘
       │
       ▼
┌──────────────┬──────────────┬──────────────┐
│ Transaction  │   Inquiry    │   Advisor    │
│   Agent      │   Agent      │   Agent      │
└──────┬───────┴──────┬───────┴──────┬───────┘
       │              │              │
       └──────────────┼──────────────┘
                      ▼
               ┌─────────────┐
               │ BankManager │ (Escalation)
               └─────────────┘
```

### Agent Specializations

| Agent | Purpose | Tools |
|-------|---------|-------|
| **Triage** | Route queries to specialists | None (routing logic only) |
| **Transaction** | Money movement | `send_money`, `request_money`, `approve_payment`, `list_pending_requests` |
| **Inquiry** | Account information | `check_balance`, `view_history`, `list_my_accounts` |
| **Advisor** | Products & services | `list_products`, `open_new_account` |
| **Manager** | Complex issues & escalations | All tools available |

### Handoff Flow Example

```
User: "Send $50 to bob"
  → Triage routes to Transaction Agent
  → Transaction Agent calls send_money tool
  → Returns confirmation
  → Hands back to Triage

User: "What products do you offer?"
  → Triage routes to Advisor Agent
  → Advisor calls list_products tool
  → Returns product list
  → Hands back to Triage
```

---

## Security & Cryptography

### Post-Quantum Signatures

All transactions are signed with ML-DSA-44 (Dilithium):

```python
from identity import IdentityManager

ident = IdentityManager()

# Sign a transaction
signature = ident.sign_message("alice", b"transfer $50 to bob")

# Verify signature
is_valid = ident.verify_signature("alice", b"transfer $50 to bob", signature)
```

### Identity Tokens

User tokens are SHA-256 hashes of ML-DSA-44 public keys:
- Non-custodial identity verification
- Quantum-safe authentication
- Portable across systems

---

## Testing

### Run All Tests

```bash
uv run pytest
```

### Specific Test Files

```bash
# Test banking tools
uv run pytest tests/test_tools.py -v

# Test identity/crypto
uv run pytest tests/test_identity.py -v

# Test ledger
uv run pytest tests/test_ledger.py -v
```

### With Coverage

```bash
uv run pytest --cov=. --cov-report=html
```

---

## Troubleshooting

### Model Not Found

```bash
# Check running models
foundry model list

# Start Phi-4-mini
foundry model run Phi-4-mini-instruct-generic-gpu:5

# Verify endpoint
echo $FOUNDRY_LOCAL_ENDPOINT
```

### A2A Connection Refused

```bash
# Ensure server is running
uv run main.py --a2a --user alice

# Test health endpoint
curl http://localhost:8000/health

# Check port availability
lsof -i :8000
```

### MCP Tools Not Loading

```bash
# Test stdio mode directly
uv run main.py --mcp --stdio --user alice

# Check for errors in output
# Verify Python path in MCP client config
```

### Database Issues

```bash
# Reinitialize database
rm data/bank.db
uv run bootstrap.py

# Check database contents
sqlite3 data/bank.db "SELECT * FROM users;"
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Use different port
uv run main.py --a2a --user alice --port 8002
```

---

## Development Tips

### Quick Iteration

```bash
# Watch mode for Python changes (install watchdog)
uv add --dev watchdog
watchmedo auto-restart --patterns="*.py" --recursive -- uv run main.py --user alice
```

### Debug Mode

Set environment variable for verbose logging:
```bash
export DEBUG=1
uv run main.py --user alice
```

### Testing Different Users

```bash
# Test as Alice (default)
uv run main.py --user alice

# Test as Bob
uv run main.py --user bob
```

### Clean Slate

```bash
# Remove all generated data
rm -rf data/
uv run bootstrap.py
```

---

## Project Structure

```
├── hosted_agent.py          # Azure AI Foundry entry point
├── main.py                  # CLI & server launcher
├── agents.py                # Multi-agent workflow setup
├── a2a_server.py            # A2A protocol server
├── mcp_server.py            # MCP protocol server
├── tools.py                 # 9 banking tools
├── identity.py              # ML-DSA-44 crypto
├── ledger.py                # SQLite ledger engine
├── bootstrap.py             # Database initialization
├── bank_agents/             # Individual agent definitions
│   ├── triage.py
│   ├── transaction.py
│   ├── inquiry.py
│   ├── advisor.py
│   └── manager.py
├── tests/                   # Test suite
├── Dockerfile               # Container for Azure
└── agent.yaml               # Azure deployment config
```

---

## Next Steps

- **Deploy to Azure**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Add Custom Tools**: Extend `tools.py` with new banking functions
- **Create New Agents**: Add specialized agents in `bank_agents/`
- **Integrate with Apps**: Use A2A/MCP servers in your applications
