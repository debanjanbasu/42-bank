# 42 Bank: Quantum-Safe Agentic Platform

42 Bank is a next-generation banking prototype built with the **Microsoft Agent Framework** and **Azure AI Foundry**. It features a full multi-agent "Handoff" architecture, post-quantum cryptographic identity, and a pro-active audit system.

## 🚀 Key Features

- **A2A Multi-Agent Handoff**: Specialized agents (**Triage**, **Transaction**, **Inquiry**, **Advisor**, **Bank Manager**) collaborate autonomously using the `HandoffBuilder`.
- **Post-Quantum Cryptography (PQC)**: Identity and transaction security powered by **ML-DSA-44 (Dilithium)** signatures.
- **Cloud-Ready Ledger**: High-performance SQLite document store mimicking **Azure Cosmos DB** logic.
- **Proactive Audit Service**: Real-time **Change Feed** monitoring for high-value alerts and fraud detection.
- **Stateful Multi-Account Flow**: Support for Checking and Savings accounts with asynchronous money requests and signed approvals.
- **Visual Debugging**: Native **DevUI** support to visualize agent reasoning, tool usage, and handoffs in real-time.

## 🛠️ Tech Stack

- **Orchestration**: Microsoft Agent Framework
- **Security**: NIST PQC (ML-DSA-44) via `pqcrypto`
- **Database**: SQLite (Production-ready interface for Cosmos DB)
- **Runtime**: Python 3.14 + `uv`
- **Inference**: Azure AI Foundry / Foundry Local

## 🚦 Quick Start

### 1. Requirements
- Install [uv](https://github.com/astral-sh/uv).
- Install [Foundry Local](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/get-started).

### 2. Setup
```bash
# Configure environment
cp .env.example .env

# Start local model (Recommended: 1.5b for speed)
foundry model run qwen2.5-1.5b

# Initialize quantum-safe identities and ledger
uv run bootstrap.py
```

### 3. Execution
```bash
# Terminal 1: Start Audit Service (Change Feed)
uv run audit_service.py

# Terminal 2: Start Banking CLI
uv run main.py --user alice

# Terminal 3: (Optional) Start Visual DevUI
uv run main.py --user alice --devui
```

## 🧪 Testing
```bash
uv run pytest
```

## 📂 Project Structure
- `identity.py`: PQC-safe key management (ML-DSA-44).
- `ledger.py`: Multi-account SQLite storage with pro-active Change Feed.
- `bank_agents/`: Modular specialist agent definitions (Triage, Advisor, etc.).
- `agents.py`: Central A2A Handoff orchestration logic.
- `tools.py`: PQC-signed agent skills.
- `audit_service.py`: Real-time ledger monitoring service.

## ⚖️ License
MIT
