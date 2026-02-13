# 42 Bank - Developer Guide

Welcome to the 42 Bank development guide. This platform leverages the **Microsoft Agent Framework** to provide a secure, multi-agent banking experience locally and in the cloud.

## 🛠️ Local Environment Setup

### 1. Model Hosting
The platform is optimized for the **Qwen 2.5** family. For local development, we recommend the 1.5b model for a balance of reasoning and performance.
```bash
foundry model run qwen2.5-1.5b
```
Ensure the service is active (check port `59402` or your configured port in `.env`).

### 2. Quantum-Safe Bootstrap
Initialize the platform by generating PQC keys and the SQLite database:
```bash
uv run bootstrap.py
```
This script will:
- Completely reset the `data/` directory.
- Generate **ML-DSA-44 (Dilithium)** keys in `data/keys/`.
- Initialize `data/bank.db` with Alice ($1000) and Bob ($500).
- Open a **Savings** account for Alice.
- Execute genesis transactions to populate history.

### 3. Launch Interaction
Start an interactive banking session:
```bash
uv run main.py --user alice
```
Or launch the **Visual DevUI** to see the agents' internal monologue:
```bash
uv run main.py --user alice --devui
```

## 🤖 Multi-Agent Architecture (A2A)

The platform uses a **Modular Handoff Orchestration** pattern. Agents are decoupled in the `bank_agents/` directory:

1. **TriageAgent**: The "Receptionist". It handles routing based on user intent.
2. **TransactionAgent**: Specialist for money movement (`send_money`, `request_money`, `approve_payment`).
3. **InquiryAgent**: Specialist for account data (`check_balance`, `view_history`, `list_my_accounts`).
4. **AdvisorAgent**: Financial consultant for bank products (`list_products`) and account opening (`open_new_account`).
5. **BankManager**: High-level help and escalation point.

### Autonomous Mode
The workflow runs in **Autonomous Mode**, allowing agents to "talk" to each other to solve complex requests (e.g., "Check my balance and if it's over $500, recommend a mortgage").

## 🔐 Security & Identity

### Post-Quantum Cryptography
Users are identified by a **SHA-256 Token** derived from their **ML-DSA-44** public key.
- All private keys are stored locally as `.sk` files.
- **Signing**: Every financial action is cryptographically signed by the agent using the user's private key.
- **Verification**: The `LedgerEngine` verifies the signature against the stored public key before committing any transaction.

## 🧪 Testing
We maintain a robust test suite covering core logic:
```bash
uv run pytest
```
- `test_identity`: Validates PQC key generation and signature logic.
- `test_ledger`: Validates atomic transactions and multi-account state.
- `test_tools`: Validates agent-facing skills and PQC signing integration.
