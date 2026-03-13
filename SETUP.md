# Local Development Setup

## Prerequisites

### 1. Install uv (Python package manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env   # or restart terminal
uv --version  # Should show 0.5+
```

### 2. Install Foundry Local (Local LLM runtime)
```bash
# macOS
brew tap microsoft/foundry && brew install foundry

# Windows / Linux — download from:
# https://aka.ms/foundry-local
```

Then start a model:
```bash
foundry model run qwen2.5-14b
# Wait ~60s for model to load — check: foundry service status
```

### 3. Install Node.js 20+ (for mobile app)
```bash
# macOS
brew install node@20

# Or use nvm: https://github.com/nvm-sh/nvm
nvm install 20 && nvm use 20
```

### 4. Docker Desktop (required — for Cosmos DB emulator)
Download from: https://www.docker.com/products/docker-desktop

Docker Desktop is **required** for local development. The Cosmos DB emulator runs in Docker and is used for all environments including local development.

---

## Quick Start (3 terminals)

**Terminal 1 — Foundry Local (LLM):**
```bash
foundry model run qwen2.5-14b
```

**Terminal 2 — Backend:**
```bash
git clone <repo>
cd 42-bank

# Copy environment config
cp .env.example .env   # Edit as needed

# Start Cosmos emulator (required before backend)
docker-compose up -d

# Install dependencies and start dev server
make install
./dev.sh alice   # Bootstraps DB and starts servers
```

**Terminal 3 — Mobile App:**
```bash
cd mobile
npm install
npm start
# Press 'i' for iOS simulator, 'a' for Android emulator
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET` | Yes (local) | Random string ≥32 chars for JWT signing |
| `APP_ENV` | No | `development` (default), `staging`, `production` |
| `FOUNDRY_LOCAL_ENDPOINT` | No | Override Foundry endpoint auto-discovery |
| `AZURE_AI_PROJECT_ENDPOINT` | Production | Azure AI Foundry project URL |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Production | Model deployment name |
| `AZURE_COSMOS_CONNECTION_STRING` | Local dev only | Set automatically by `dev.sh` (emulator key auth) |
| `COSMOS_ENDPOINT` | Production | Cosmos account URL — managed identity auth, no key needed |
| `COSMOS_DATABASE` | Auto-set by dev.sh | Cosmos database name (default: `banking`) |


Generate a strong JWT secret:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## Make Commands

```
make help          Show all available commands
make install       Install all dependencies
make dev           Start development server
make test          Run all tests
make test-quick    Run fast MCP tests only
make lint          Run linter
make typecheck     Run type checker
make docker-build  Build Docker images
make clean         Remove caches
```

---

## Troubleshooting

### `foundry: command not found`
Foundry Local is not in PATH. Run: `source ~/.local/bin/env` or restart your terminal.

### `Failed to connect to Foundry Local`
Model is still loading. Wait 30-60s and try again: `foundry service status`

### `JWT_SECRET is using default dev value`
Expected in development. Set `JWT_SECRET` env var for better security even locally.

### `pytest: No module named ...`
Run `uv sync` to install all dependencies.

### Cosmos emulator connection refused
Start it first: `docker-compose up -d`. Wait 30-60s for it to initialize.  
Check status: `curl -s http://localhost:1234`

### Mobile: Metro bundler can't find module
Run `cd mobile && npm install` to restore node_modules.

### iOS build fails (no simulator)
Install Xcode from the App Store, then: `xcode-select --install`

---

## Architecture Overview

See [README.md](README.md) for full architecture details and [AGENTS.md](AGENTS.md) for the agent system documentation.
