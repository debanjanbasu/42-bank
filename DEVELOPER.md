# 42 Bank - Developer Guide

## Environment Setup

### 1. Start Foundry Local
```bash
# Phi-4-mini (recommended - fast & efficient)
foundry model run Phi-4-mini-instruct-generic-gpu:5

# Check running models
foundry model list
```

### 2. Initialize Platform
```bash
uv run bootstrap.py
```
This creates:
- ML-DSA-44 keys in `data/keys/`
- SQLite database with test users (alice: $1000, bob: $500)

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your model settings
```

---

## Running Modes

### CLI Chat
```bash
uv run main.py --user alice
```

### A2A Server
```bash
uv run main.py --a2a --user alice --port 8000
```

### MCP Server (HTTP)
```bash
uv run main.py --mcp --user alice --port 8001
```

### MCP Server (stdio)
```bash
uv run main.py --mcp --stdio --user alice
```

### Visual DevUI
```bash
uv run main.py --user alice --devui
```

---

## A2A Protocol Integration

### Agent Discovery
```bash
curl http://localhost:8000/a2a/triage
```

Response (Agent Card):
```json
{
  "name": "42-Bank-TriageAgent",
  "description": "42 Bank Receptionist - Routes queries...",
  "version": "1.0.0",
  "capabilities": { "streaming": true },
  "skills": [...]
}
```

### Send Message
```bash
curl -X POST http://localhost:8000/a2a/transaction/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "kind": "message",
      "role": "user",
      "parts": [{"kind": "text", "text": "Send $50 to bob for lunch"}],
      "contextId": "test-123"
    }
  }'
```

### A2A Client (Python)
```python
import asyncio
import httpx
from a2a.client import A2ACardResolver
from agent_framework.a2a import A2AAgent

async def main():
    async with httpx.AsyncClient() as http_client:
        resolver = A2ACardResolver(httpx_client=http_client, base_url="http://localhost:8000")
        card = await resolver.get_agent_card("/a2a/transaction")
        
        async with A2AAgent(name="transaction", agent_card=card, url="http://localhost:8000/a2a/transaction") as agent:
            response = await agent.run("Send $50 to bob")
            print(response.messages[0].text)

asyncio.run(main())
```

---

## MCP Protocol Integration

### Connect via SSE
```javascript
const eventSource = new EventSource('http://localhost:8001/sse');
eventSource.onmessage = (event) => console.log(event.data);
```

### List Tools
```bash
curl http://localhost:8001/tools
```

### MCP Client (Python)
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py", "alice", "--stdio"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool("check_balance", {"account_type": "checking"})
            print(result.content)
```

### Claude Desktop Integration
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "42-bank": {
      "command": "python",
      "args": ["mcp_server.py", "alice", "--stdio"]
    }
  }
}
```

---

## Multi-Agent Architecture

```
┌─────────────┐
│ TriageAgent │ (Entry Point)
└──────┬──────┘
       │ routes to
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

### Agent Tools

| Agent | Tools |
|-------|-------|
| Triage | None (routing only) |
| Transaction | send_money, request_money, approve_payment, list_pending_requests |
| Inquiry | check_balance, view_history, list_my_accounts |
| Advisor | list_products, open_new_account |
| Manager | check_balance, view_history, list_pending_requests, list_products |

---

## Security

### Post-Quantum Signatures
```python
from identity import IdentityManager

ident = IdentityManager()
sig = ident.sign_message("alice", b"transfer $50")
verified = ident.verify_signature("alice", b"transfer $50", sig)
```

### Token Derivation
- User tokens are SHA-256 hashes of ML-DSA-44 public keys
- Enables non-custodial identity verification

---

## Testing

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_tools.py -v

# With coverage
uv run pytest --cov=.
```

---

## Troubleshooting

### Model not found
```bash
foundry model list  # Check available models
foundry model run <model-id>  # Start the model
```

### A2A connection refused
```bash
# Ensure A2A server is running
uv run main.py --a2a --user alice

# Check port
curl http://localhost:8000/health
```

### MCP tools not loading
```bash
# Test MCP server directly
uv run mcp_server.py alice --stdio
```
