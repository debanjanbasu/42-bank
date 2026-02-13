# 42 Bank: Quantum-Safe Agentic Platform

42 Bank is a next-generation banking prototype built with **Microsoft Agent Framework** and **Azure AI Foundry**. It features multi-agent orchestration, post-quantum security, and a pro-active audit system.

## 🚀 Key Features

- **A2A Multi-Agent Handoff**: Specialized agents (**Triage**, **Transaction**, **Inquiry**, **Advisor**, **Bank Manager**) collaborate using the `HandoffBuilder`.
- **Post-Quantum Cryptography (PQC)**: Identity and transaction security powered by **ML-DSA-44 (Dilithium)**.
- **Cloud-Ready Ledger**: High-performance SQLite document store mimicking **Azure Cosmos DB**.
- **Proactive Audit Service**: Simulated **Change Feed** monitoring for real-time fraud detection.
- **Stateful Approval Flow**: Support for asynchronous money requests and PQC-signed approvals.
- **Visual Debugging**: Built-in **DevUI** support to visualize agent thinking and tool usage.

## 🛠️ Tech Stack

- **Orchestration**: Microsoft Agent Framework
- **Security**: NIST PQC (ML-DSA-44) via `pqcrypto`
- **Database**: SQLite (Production-ready interface for Cosmos DB)
- **Runtime**: Python 3.14 + `uv`
- **Testing**: `pytest` + `pytest-asyncio`

## 🚦 Quick Start

### 1. Requirements
- [uv](https://github.com/astral-sh/uv)
- [Foundry Local](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/get-started) (or Ollama)

### 2. Setup
```bash
# Start local model
foundry model run qwen2.5-0.5b

# Initialize identities and ledger
uv run bootstrap.py
```

### 3. Execution
```bash
# Terminal 1: Start Audit Service
uv run audit_service.py

# Terminal 2: Start Banking CLI
uv run main.py --user alice
```


## 🧪 Testing
```bash
uv run pytest
```

## 📂 Architecture
- `identity.py`: Quantum-safe key management (ML-DSA-44).
- `ledger.py`: Document-based SQLite storage + Change Feed + Product Catalog.
- `bank_agents/`: Modular agent definitions (Triage, Advisor, etc.).
- `agents.py`: A2A Handoff orchestration.
- `tools.py`: PQC-signed agent tools.
- `audit_service.py`: Real-time audit processor.

## ⚖️ License
MIT
