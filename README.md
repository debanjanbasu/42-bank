# 42-Bank

A quantum-safe multi-agent banking platform using the Microsoft Agent Framework (A2A + MCP protocols), Azure Cosmos DB, and ML-DSA-44 post-quantum cryptography.

## Architecture

- **5 specialized agents** (Triage, Inquiry, Transaction, Advisor, Manager) communicating via A2A protocol with SSE streaming
- **9 MCP banking tools** exposed via Model Context Protocol
- **React Native / Expo 55** mobile app with biometric auth and offline caching
- **Azure Cosmos DB** for all environments (serverless, async SDK)
- **ML-DSA-44** post-quantum cryptography for transaction signing

## Quick Start

```bash
# Prerequisites: Docker Desktop, uv, Foundry Local, Node.js 18+

# Start local Cosmos emulator
docker-compose up -d

# Start backend servers
./dev.sh alice

# Start mobile app
cd mobile && npm install && npx expo start --dev-client
```

## Documentation

| Document | Description |
|----------|-------------|
| [AGENTS.md](AGENTS.md) | Architecture, project structure, code conventions, agent definitions |
| [SETUP.md](SETUP.md) | Local development setup guide |
| [TESTING.md](TESTING.md) | Testing philosophy, test suite, running tests |
| [PRODUCTION_RELEASE.md](PRODUCTION_RELEASE.md) | Azure deployment and operations |
| [docs/adr/](docs/adr/) | Architecture Decision Records (5 ADRs) |

## Project Structure

```
42-bank/
├── a2a_server.py           # A2A protocol server (5 agents, SSE streaming)
├── mcp_server.py            # MCP server (9 banking tools)
├── ledger.py                # Transaction ledger (Cosmos DB, Pydantic)
├── identity.py              # ML-DSA-44 cryptography
├── api/                     # Mobile backend API (FastAPI)
├── bank_agents/             # Agent definitions
├── mobile/                  # React Native / Expo app
├── tests/                   # Test suite (43 tests)
├── infra/                   # Azure Bicep IaC
└── docs/adr/                # Architecture Decision Records
```

## License

MIT
