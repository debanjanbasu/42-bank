# 42 Bank: Multi-Agent Banking System

A **quantum-safe multi-agent banking platform** with mobile-first design, featuring on-device AI integration (Apple Intelligence / Gemini Nano), A2A protocol agents, and ML-DSA-44 post-quantum cryptography.

## ✨ Features

### Core Platform
- 🤖 **5 Specialized Agents** - Triage, Inquiry, Transaction, Advisor, Manager
- 🔌 **MCP Protocol** - 9 banking tools via Model Context Protocol
- 🔗 **A2A Protocol** - Agent-to-Agent communication with streaming
- 🔒 **Post-Quantum Security** - ML-DSA-44 (Dilithium) signatures

### Mobile App (New)
- 📱 **Cross-Platform** - React Native / Flutter with Expo
- 🧠 **On-Device AI** - Apple Intelligence (iOS) / Gemini Nano (Android)
- 🔐 **Secure Enclave** - Keys stored in Keychain / Keystore
- 👆 **Biometric Auth** - Face ID / Touch ID / Fingerprint
- 🔔 **Push Notifications** - Real-time transaction alerts

### Cloud Backend
- ☁️ **Azure AI Foundry** - Qwen3.5-35B-A3B (MoE model)
- 💾 **Cosmos DB** - Serverless global database
- 📊 **Application Insights** - Full observability

---

## 🚀 Quick Start

### Mobile App Development (Recommended)

```bash
# Terminal 1: Start backend
./dev.sh alice

# Terminal 2: Start mobile app
cd mobile
npm install
npx expo start --dev-client

# Scan QR code with Expo Go or run on device
```

### CLI Client (Legacy - For Quick Testing)

```bash
# Terminal 1: Start LLM
foundry model run qwen2.5-14b-instruct-generic-gpu:4

# Terminal 2: Start Cosmos emulator + backend
docker-compose up -d
./dev.sh alice
```

---

## 🏗️ Architecture

### Complete System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Mobile App (Expo)                                                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐            │
│  │ Apple Intel.   │  │ Gemini Nano    │  │ Biometric Auth │            │
│  │ (iOS 18+)      │  │ (Android)      │  │ (Face ID/Touch)│            │
│  └────────┬───────┘  └────────┬───────┘  └────────────────┘            │
│           │                   │                                          │
│  ┌────────▼───────────────────▼────────────────────────────┐            │
│  │ A2A Client (TypeScript)                                 │            │
│  │ • HTTP/SSE communication                                │            │
│  │ • JWT authentication                                    │            │
│  │ • Transaction signing                                   │            │
│  └────────┬────────────────────────────────────────────────┘            │
│           │                                                               │
│  ┌────────▼────────────────────────────────────────────────┐            │
│  │ Secure Storage                                          │            │
│  │ • iOS: Keychain (Secure Enclave)                        │            │
│  │ • Android: Keystore (TEE)                               │            │
│  │ • ML-DSA-44 private keys                                │            │
│  └─────────────────────────────────────────────────────────┘            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              │ A2A Protocol (HTTPS/SSE)
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Azure Backend (42-Bank)                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ REST API (FastAPI)                                                 │  │
│  │ • POST /api/auth/register - User registration                      │  │
│  │ • POST /api/auth/login - JWT authentication                        │  │
│  │ • POST /api/keys/backup - Key backup                               │  │
│  │ • POST /api/notifications/register - Push tokens                   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ A2A Server (Port 8000)                                             │  │
│  │ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │  │
│  │ │ Triage  │ │ Inquiry │ │Transaction│ │ Advisor │ │ Manager │       │  │
│  │ │ Agent   │ │ Agent   │ │ Agent    │ │ Agent   │ │ Agent   │       │  │
│  │ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │  │
│  │      │           │           │           │           │              │  │
│  │      └───────────┴───────────┴───────────┴───────────┘              │  │
│  │                              │                                       │  │
│  │                   Qwen3.5-35B-A3B (3B active params)                │  │
│  └──────────────────────────────┼──────────────────────────────────────┘  │
│                                 │                                          │
│  ┌──────────────────────────────▼──────────────────────────────────────┐  │
│  │ MCP Server (Port 8001)                                             │  │
│  │ • check_balance • send_money • view_history                        │  │
│  │ • request_payment • approve_request • list_products                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Azure Services                                                     │  │
│  │ • Cosmos DB (Serverless) - Users, transactions                    │  │
│  │ • Notification Hubs - Push notifications                          │  │
│  │ • Application Insights - Monitoring                               │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Request Flow (Mobile)

```
User: "What's my balance?"
        ↓
┌──────────────────────────────────────┐
│ Mobile On-Device AI                  │
│ • Classify intent → "inquiry"        │
│ • Decide: local or cloud?            │
└───────────────┬──────────────────────┘
                │
                │ Needs fresh data → Route to cloud
                ▼
┌──────────────────────────────────────┐
│ A2A Request                          │
│ POST /a2a/triage/v1/message          │
│ Headers: Authorization: Bearer JWT   │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ Azure A2A Server                     │
│ • Validate JWT                       │
│ • Triage routes to Inquiry Agent     │
│ • Agent calls check_balance()        │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│ Response                             │
│ "Your checking balance is $1,000.00" │
│ • SSE stream to mobile               │
│ • Push notification on completion    │
└──────────────────────────────────────┘
```

---

## 📁 Project Structure

```
42-bank/
├── api/                          # Mobile REST API (NEW)
│   ├── __init__.py               # FastAPI app
│   ├── auth.py                   # User registration & JWT
│   ├── keys.py                   # Key backup/restore
│   └── notifications.py          # Push notifications
│
├── mobile/                       # Mobile App (NEW)
│   ├── app/                      # Expo Router screens
│   ├── src/
│   │   ├── services/
│   │   │   ├── A2AClient.ts      # A2A protocol client
│   │   │   ├── KeyManager.ts     # ML-DSA-44 crypto
│   │   │   ├── Notifications.ts  # Push notifications
│   │   │   └── SecureStorage.ts  # Keychain/Keystore
│   │   └── native/
│   │       ├── ios/AppleIntelligenceBridge.swift
│   │       └── android/GeminiNanoBridge.kt
│   ├── app.json
│   ├── package.json
│   └── README.md
│
├── bank_agents/                  # A2A agents
│   ├── triage.py
│   ├── inquiry.py
│   ├── transaction.py
│   ├── advisor.py
│   └── manager.py
│
├── infra/                        # Azure infrastructure
│   └── main.bicep
│
├── scripts/                      # Utility scripts
│
├── a2a_server.py                 # A2A server (5 agents)
├── mcp_server.py                 # MCP server (9 tools)
├── ledger.py                     # Transaction ledger (async Cosmos)
├── identity.py                   # ML-DSA-44 crypto
│
├── docker-compose.yml            # Cosmos DB emulator
│
├── AZURE_DEPLOYMENT.md           # Azure deployment guide
├── MOBILE_DEVELOPMENT.md         # Mobile dev guide
├── AGENTS.md                     # AI agent instructions
└── README.md                     # This file
```

---

## 📱 Mobile App

### Development Without App Store

See [MOBILE_DEVELOPMENT.md](MOBILE_DEVELOPMENT.md) for complete guide.

**Quick setup:**
```bash
cd mobile
npm install

# Option 1: Expo Go (limited features)
npx expo start

# Option 2: Dev Client (full features - recommended)
npx expo run:ios
npx expo run:android
```

### Key Features

| Feature | iOS | Android |
|---------|-----|---------|
| On-Device AI | Apple Intelligence (iOS 18+) | Gemini Nano (Pixel 8+) |
| Biometric Auth | Face ID / Touch ID | Fingerprint |
| Secure Storage | Keychain + Secure Enclave | Keystore + TEE |
| Push Notifications | APNs via Expo | FCM via Expo |
| A2A Streaming | ✅ SSE | ✅ SSE |

---

## ☁️ Azure Deployment

### Quick Deploy

```bash
# 1. Deploy 42-Bank infrastructure
az deployment sub create --location eastus --template-file infra/main.bicep

# 2. Initialize database
export AZURE_COSMOS_CONNECTION_STRING="AccountEndpoint=...;AccountKey=..."
uv run python bootstrap.py
```

See [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md) for complete guide.

### Cost Estimate

| Component | Monthly Cost |
|-----------|--------------|
| Cosmos DB Serverless | $5-15 |
| Container Apps | $10-30 |
| Qwen3.5-35B-A3B | $5-20 |
| Notification Hubs | $0-5 |
| **Total** | **$20-70/month** |

---

## 🔐 Security

### ML-DSA-44 Post-Quantum Cryptography

All transactions signed with **ML-DSA-44** (FIPS 204):
- Quantum-resistant lattice-based signatures
- Security Level 2 (~128-bit equivalent)
- Signature size: ~2.4KB
- Public key: ~1.3KB

### Mobile Key Storage

| Platform | Storage | Hardware Backing |
|----------|---------|------------------|
| iOS | Keychain | Secure Enclave |
| Android | Keystore | TEE (Trusted Execution Environment) |

### Authentication Flow

```
┌─────────────┐
│ Mobile App  │  1. Generate ML-DSA-44 keypair on device
│             │     Private key → Secure Enclave
│             │     Public key → Server
└─────────────┘
       │
       │ 2. Register user
       ▼
┌─────────────┐
│ API Server  │  3. Create user account
│             │     Store public key
│             │     Return JWT token
└─────────────┘
       │
       │ 4. Login
       ▼
┌─────────────┐
│ Device Auth │  5. Biometric verification
│             │     Sign challenge with private key
│             │     Server verifies signature
└─────────────┘
```

---

## 💻 Development

### Prerequisites

- **Python 3.10+** with uv package manager
- **Node.js 18+** for mobile app
- **Docker Desktop** (required, for Cosmos DB emulator)
- **Foundry Local** (for local LLM)
- **Expo CLI** (for mobile app)

### Backend Development

```bash
# Install dependencies
uv sync

# Start Cosmos DB emulator + backend
docker-compose up -d
./dev.sh alice

# Run tests
uv run pytest tests/ -v
```

### Mobile Development

```bash
cd mobile

# Install dependencies
npm install

# Start development
npx expo start --dev-client

# Build for device
npx expo run:ios
npx expo run:android
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md) | Azure deployment guide |
| [MOBILE_DEVELOPMENT.md](MOBILE_DEVELOPMENT.md) | Mobile app development |
| [AGENTS.md](AGENTS.md) | AI agent instructions |
| [TESTING.md](TESTING.md) | Testing guide |

---

## 🧪 Testing

### Backend Tests

```bash
# All tests (requires Foundry Local)
uv run pytest tests/ -v

# Specific test
uv run pytest tests/test_mcp_tools.py::test_check_balance_tool -v

# With coverage
uv run pytest tests/ --cov=. --cov-report=html
```

### Mobile Tests

```bash
cd mobile

# Unit tests
npm test

# E2E tests
npm run test:e2e
```

---

## 🛠️ Technology Stack

### Backend
- **Python 3.10+** - FastAPI, Pydantic, Azure SDK
- **Agent Framework** - Microsoft Agent Framework
- **Database** - Azure Cosmos DB (emulator for local dev)
- **AI Model** - Qwen3.5-35B-A3B (Azure AI Foundry)

### Mobile
- **React Native / Expo** - Cross-platform framework
- **TypeScript** - Type-safe development
- **Expo Router** - File-based navigation
- **Native Modules** - Swift (iOS) / Kotlin (Android)

### Protocols
- **MCP** - Model Context Protocol (tools)
- **A2A** - Agent-to-Agent (agent communication)
- **JWT** - JSON Web Tokens (auth)
- **ML-DSA-44** - Post-quantum signatures

### Azure Services
- **AI Foundry** - Model hosting
- **Cosmos DB** - Global database
- **Container Apps** - Backend hosting (managed identity, encrypted secrets)
- **Notification Hubs** - Push notifications

---

## 📝 License

MIT License - See LICENSE file

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing`
3. Make changes and test
4. Commit: `git commit -m 'Add amazing feature'`
5. Push: `git push origin feature/amazing`
6. Submit pull request

---

**Status:** ✅ Production Ready  
**Updated:** 2026-03-08  
**Protocols:** MCP + A2A + REST API  
**Security:** ML-DSA-44 (Post-Quantum) + JWT + Biometric  
**Mobile:** iOS (Apple Intelligence) + Android (Gemini Nano)
