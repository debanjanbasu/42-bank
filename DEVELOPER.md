# 42 Bank - Agentic AI Banking Platform

Welcome to the 42 Bank developer guide. This platform uses the **Microsoft Agent Framework** to provide a secure, AI-driven banking experience locally.

## Prerequisites

1. **Foundry Local**: Install and run Foundry Local to host your AI models.
   - **macOS**: `brew tap microsoft/foundrylocal && brew install foundrylocal`
   - **Windows**: `winget install Microsoft.FoundryLocal`

2. **Python**: Ensure you have Python 3.10+ and `uv` installed.

## Setup Instructions

### 1. Start the AI Model
Open a new terminal and run:
```bash
foundry model run qwen2.5-0.5b
```
Ensure the service is running (default port is `8080`).

### 2. Initialize the Bank
Run the bootstrap script to create the Genesis accounts (Alice and Bob):
```bash
uv run bootstrap.py
```
This will:
- Generate cryptographic **ML-DSA-44 (Dilithium)** keys in `data/keys/`.
- Initialize `data/bank.db` with Alice ($1,000) and Bob ($500).
- Create a sample transaction.

### 3. Launch the Agent
You can now start an interactive session as Alice or Bob:
```bash
uv run main.py --user alice
```

## How it Works

### Multi-Agent Collaboration (A2A)
The platform uses a **Handoff Orchestration** pattern with specialized agents:
1. **TriageAgent**: Routes users to the correct specialist.
2. **TransactionAgent**: Handles money movement and approvals.
3. **InquiryAgent**: Handles account data.
4. **AdvisorAgent**: Provides product recommendations.
5. **BankManager**: Provides oversight and help.

Agents "talk" to each other using the Microsoft Agent Framework's built-in handoff mechanism, allowing for a natural conversational flow between different banking departments.

### Cryptographic Identity (PQC Safe)
Users are identified by a **SHA-256 Token** derived from their **ML-DSA-44 (Dilithium)** public key, making the platform resistant to future quantum computing attacks.
- The `IdentityManager` loads the `.sk` (secret key) and `.pk` (public key) files from `data/keys/`.
- The `LedgerEngine` verifies that the session token exists before allowing any data access.
- Keys are generated using the `pqcrypto` library, implementing NIST-standardized Post-Quantum Cryptography.

### Agentic Tools
The AI agent has access to the following secure tools:
- `get_balance`: Uses the session token to fetch the real-time balance.
- `get_transaction_history`: Retrieves the audit log for the current user.
- `transfer_funds`: Allows the AI to initiate transfers. Note that the AI *only* has access to the *current* user's token, preventing cross-account manipulation.

## Local Configuration
You can modify the `.env` file to change the endpoint or the model name if you use Ollama or a different Foundry configuration.
