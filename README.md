# 42 Bank: Multi-Agent Banking System

A **quantum-safe multi-agent banking platform** built with Microsoft Agent Framework, featuring MCP (Model Context Protocol) and A2A (Agent-to-Agent) protocols.

## ✨ Features

- 🤖 **5 Specialized Agents** - Triage, Inquiry, Transaction, Advisor, Manager
- 🔌 **MCP Protocol** - 9 banking tools via Model Context Protocol Streamable HTTP
- 🔗 **A2A Protocol** - Agent routing via HTTP streaming (Server-Sent Events)
- 🔒 **Post-Quantum Security** - ML-DSA-44 (Dilithium) transaction signatures  
- ☁️ **Azure Ready** - Deploy with Azure Functions + AI Agent Service
- 🏠 **Local Development** - Same architecture locally and in production

---

## 🚀 Quick Start

### Prerequisites
- [uv](https://github.com/astral-sh/uv) - Python package manager
- [Foundry Local](https://learn.microsoft.com/azure/ai-foundry/foundry-local/get-started) - Local LLM runtime

### Three Terminals

**Terminal 1: Start LLM** (one time, keep running)
```bash
foundry model run qwen2.5-14b-instruct-generic-gpu:4
# Loads ~7-14GB into GPU, auto-discovers port
```

**Terminal 2: Start Servers**
```bash
./dev.sh alice
# Auto-starts MCP (port 8001) + A2A (port 8000)
```

**Terminal 3: Chat**
```bash
uv run main.py --user alice
```

**Try:**
- "What's my balance?"
- "Send $50 to bob for dinner"
- "Show my transactions"
- "What banking products do you offer?"

---

## 🏗️ Architecture

### Request Flow
```
User Query
   ↓
CLI (main.py) - HTTP POST with streaming
   ↓
A2A Server :8000 → Triage Agent
   ↓ HTTP POST /a2a/{agent}/v1/message (or :stream)
Specialist Agents (Inquiry/Transaction/Advisor/Manager)
   ↓ MCPStreamableHTTPTool
MCP Server :8001/mcp → 9 Banking Tools
   ↓
SQLite Database + ML-DSA-44 Signatures
```

### Components

**5 Agents** (in `bank_agents/`)
- **Triage** - Routes queries to specialists via A2A HTTP
- **Inquiry** - Balance, history, account list
- **Transaction** - Send/request money, approvals
- **Advisor** - Products, account opening
- **Manager** - Escalations, oversight

**9 MCP Tools** (in `mcp_server.py`)
- `check_balance()`, `view_history()`, `list_my_accounts()`
- `send_money()`, `request_payment()`, `approve_request()`, `get_pending_requests()`
- `list_products()`, `open_account()`

**Protocols**
- **MCP Streamable HTTP** - Tools at `/mcp` endpoint (JSON-RPC 2.0)
- **A2A Streaming** - Agent routing via HTTP with Server-Sent Events (SSE)
- **ML-DSA-44** - Post-quantum signatures (FIPS 204)

---

## 📁 Project Structure

```
42-bank/
├── main.py                  # CLI (A2A HTTP client)
├── a2a_server.py            # A2A server (5 agents)
├── mcp_server.py            # MCP server (9 tools)
├── mcp_client.py            # MCPStreamableHTTPTool helper
├── dev.sh                   # Local development startup
├── utils.py                 # Shared utilities
├── ledger.py                # Transaction ledger (SQLite)
├── identity.py              # ML-DSA-44 cryptography
├── bootstrap.py             # Database initialization
├── audit_service.py         # Audit logging
│
├── bank_agents/             # Agent definitions
│   ├── triage.py
│   ├── inquiry.py
│   ├── transaction.py
│   ├── advisor.py
│   └── manager.py
│
├── data/                    # SQLite database
│   └── bank.db
│
├── tests/                   # Test suite (TODO: E2E tests)
│
└── README.md                # This file
```

**Lines of Code:** ~1,900 total
- Core: 9 Python files
- Agents: 5 specialized agents
- Clean, focused codebase

---

## 💻 Development

### Setup
```bash
# Install dependencies
uv sync

# Initialize database (alice: $1000, bob: $500)
uv run python bootstrap.py
```

### Manual Server Startup
```bash
# Option 1: Use dev.sh (recommended)
./dev.sh alice

# Option 2: Start individually
# Terminal 1: MCP server
uv run python mcp_server.py --http --user alice --port 8001

# Terminal 2: A2A server
uv run python a2a_server.py --user alice --port 8000

# Terminal 3: CLI
uv run main.py --user alice
```

### Testing Components

**MCP Server**
```bash
# List tools
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

**A2A Agents**
```bash
# Inquiry agent
curl -X POST http://localhost:8000/a2a/inquiry/v1/message \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"balance?"}]}}'

# Transaction agent
curl -X POST http://localhost:8000/a2a/transaction/v1/message \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"send $20 to bob"}]}}'
```

**Health Check**
```bash
curl http://localhost:8000/health
# Returns: {"status":"healthy","protocol":"A2A",...}
```

### Database

**Reset**
```bash
rm data/bank.db
uv run python bootstrap.py
```

**Inspect**
```bash
sqlite3 data/bank.db
.tables
SELECT username, json_extract(data, '$.accounts.checking.balance') FROM users;
.quit
```

---

## ☁️ Azure Deployment

### Architecture
```
Client → Azure AI Agent Service (managed agents)
           ↓ MCP Streamable HTTP
         Azure Functions (serverless tools)
           ↓
         Azure SQL / Cosmos DB
```

### Deploy MCP Tools (Azure Functions)

**1. Create Resources**
```bash
az group create --name 42bank-rg --location eastus

az storage account create \
  --name 42bankstorage \
  --resource-group 42bank-rg \
  --sku Standard_LRS

az functionapp create \
  --name 42bank-mcp \
  --resource-group 42bank-rg \
  --storage-account 42bankstorage \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4
```

**2. Deploy**
```bash
# See: https://learn.microsoft.com/azure/azure-functions/functions-bindings-mcp
# Reference implementation available in legacy/ folder
func azure functionapp publish 42bank-mcp
```

### Deploy Agents (Azure AI Agent Service)

**1. Setup**
```bash
az ai project create \
  --name 42bank-agents \
  --resource-group 42bank-rg \
  --location eastus
```

**2. Configure**
```bash
export AZURE_AI_PROJECT_ENDPOINT="https://YOUR_PROJECT.eastus.inference.azure.com"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4"
export MCP_SERVER_URL="https://42bank-mcp.azurewebsites.net/mcp"
```

**3. Deploy**
```bash
# See: Azure AI Agent Service documentation
# Agents automatically connect to MCP tools via MCPStreamableHTTPTool
```

### Costs (Estimated)
- Azure Functions: ~$5-20/month (consumption tier)
- Azure AI Agent Service: ~$10-50/month (pay per call)
- Storage: ~$1-5/month
- **Total: ~$16-75/month** (scales with usage)

---

## 🔒 Security

### Post-Quantum Cryptography
All transactions signed with **ML-DSA-44** (FIPS 204):
- Quantum-resistant lattice-based signatures
- Security Level 2 (~128-bit equivalent)
- Signature size: ~2.4KB
- Public key: ~1.3KB

```python
from identity import IdentityManager

ident = IdentityManager()
token = ident.create_identity("alice")
pub_key = ident.get_public_key("alice")
# Signatures auto-verified by ledger.py
```

### Authentication
- **Local**: Unauthenticated (dev mode)
- **Production**: API key or Microsoft Entra ID
- Configure via `--require-auth` flag

---

## 🐛 Troubleshooting

### Foundry Not Running
```bash
# Check status
foundry service status

# Start
foundry model run qwen2.5-14b-instruct-generic-gpu:4

# Port auto-discovery (dev.sh handles this)
export FOUNDRY_LOCAL_ENDPOINT="http://127.0.0.1:<PORT>/v1"  # Get actual port from: foundry service status
```

### MCP Server Issues
```bash
# Verify running
lsof -i :8001

# Check logs
tail -f /tmp/42bank-mcp.log

# Test endpoint
curl -X POST http://localhost:8001/mcp \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### A2A Server Issues
```bash
# Verify running
lsof -i :8000

# Check logs
tail -f /tmp/42bank-a2a.log

# Health check
curl http://localhost:8000/health
```

### Database Locked
```bash
# Restart servers (dev.sh handles cleanup)
./dev.sh alice
```

---

## 🛠️ Technology Stack

**Frameworks**
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) - Multi-agent orchestration
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server
- [Starlette](https://www.starlette.io/) - A2A server (ASGI)

**Azure**
- Azure AI Foundry - Model deployment
- Azure Functions - Serverless MCP
- Azure AI Agent Service - Managed agents

**Local Dev**
- Foundry Local - GPU inference
- SQLite - Transaction ledger
- Qwen 2.5 14B - Open LLM

**Protocols**
- MCP (Model Context Protocol) - Tool standard
- A2A (Agent-to-Agent) - Agent communication
- JSON-RPC 2.0 - Message format

**Security**
- ML-DSA-44 (pqcrypto) - Post-quantum signatures

---

## 📚 Learn More

- [MCP Specification](https://modelcontextprotocol.io/)
- [A2A Protocol](https://learn.microsoft.com/azure/ai-foundry/concepts/agent-to-agent)
- [Azure Functions MCP Binding](https://learn.microsoft.com/azure/azure-functions/functions-bindings-mcp)
- [ML-DSA-44 (FIPS 204)](https://csrc.nist.gov/pubs/fips/204/final)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing`
3. Make changes
4. Test locally: `./dev.sh alice`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing`
7. Submit pull request

---

## 📄 License

MIT License - See LICENSE file

---

**Status:** ✅ Production Ready  
**Updated:** 2026-02-18  
**Code:** ~2,350 lines  
**Protocols:** MCP + A2A Streaming  
**Security:** ML-DSA-44 (Post-Quantum)  
**Tests:** 26/26 passing ✅

---

## 🧪 Testing

### Prerequisites

⚠️ **REQUIRED: Foundry must be running before tests**

Tests are **integration tests** that use real LLM calls. Without Foundry running, all agent tests will fail with empty responses.

```bash
# Terminal 1: Start Foundry (REQUIRED!)
foundry model run qwen2.5-14b-instruct-generic-gpu:4

# Wait for: "Model management service is running on http://127.0.0.1:<PORT>/openai/status"
# Note: Foundry uses a random port each time it starts
```

✅ **MCP/A2A servers start automatically** - test fixtures handle server startup!

### Run All Tests
```bash
# Terminal 2: Run complete test suite (Foundry must be running!)
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=. --cov-report=html

# Run specific test categories  
uv run pytest tests/ -m a2a      # A2A agent tests only
uv run pytest tests/ -m e2e      # E2E integration tests only
```

### Troubleshooting Tests

**Empty responses / All tests fail:**
- ✅ Ensure Foundry is running: `foundry model run qwen2.5-14b-instruct-generic-gpu:4`
- ✅ Check Foundry is responding: `foundry service status`

**Port conflicts:**
- Tests use ports 8100 (A2A) and 8101 (MCP)
- Stop other instances: `lsof -i :8100 -i :8101`

**Slow tests:**
- First run: ~10-30s (server startup)
- Subsequent runs: Faster (servers reused)

### Test Structure

**conftest.py** - Fixtures and test infrastructure
- `test_db` - Clean test database for each test
- `mcp_server` - MCP server on port 8101 (session scope)
- `a2a_server` - A2A server on port 8100 (session scope)
- `http_client` - Async HTTP client

**test_a2a_agents.py** - A2A Agent Tests (10 tests)
- `test_a2a_health_endpoint` - Server health
- `test_triage_agent_balance_query` - Triage routing
- `test_inquiry_agent_balance` - Direct agent calls
- `test_inquiry_agent_history` - History queries
- `test_transaction_agent_send_money` - Transfers
- `test_advisor_agent_products` - Product inquiries
- `test_manager_agent_escalation` - Escalations
- `test_triage_multiple_queries` - Multiple query types

**test_e2e_flow.py** - Integration Tests (7 tests)
- `test_full_balance_check_flow` - Complete request flow
- `test_full_transfer_flow` - Transfer with verification
- `test_transaction_with_sender_recipient_display` - Display format
- `test_request_payment_full_flow` - Payment request workflow
- `test_product_inquiry_full_flow` - Product queries
- `test_agent_no_tool_call_leakage` - No XML artifacts
- `test_multiple_sequential_operations` - State consistency

**Total: 17 comprehensive integration tests** covering A2A agents and full end-to-end flows.

### Test Servers

Tests automatically start isolated test servers:
- MCP Server: `http://localhost:8101/mcp`
- A2A Server: `http://localhost:8100`
- Test Database: `data/test_bank.db` (auto-cleaned)

Servers start once per session and shut down automatically after tests complete.
