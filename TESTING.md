# 42-Bank API & Agent Testing Guide

Complete developer reference for testing all 42-Bank APIs and AI agents against the deployed environment.

## Quick Start

```bash
# Set variables (copy-paste ready)
BASE="https://bank42api.victoriousbush-d930b25a.eastus.azurecontainerapps.io"
API_KEY="HHUDvNLzIRatU5GeMv58p7wJbJokxmMK-k8yc1JTlUw"

# 1. Health check
curl $BASE/api/health

# 2. Create a user (returns JWT)
RESPONSE=$(curl -s -X POST $BASE/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"devtest","public_key":"dGVzdA==","device_id":"laptop-1","device_name":"Dev Laptop","biometric_enabled":false}')
JWT=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "JWT: $JWT"

# 3. Test an agent
curl -s -X POST $BASE/a2a/inquiry/v1/message \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"What is my balance?"}]}}'
```

---

## Base URL

| Environment | URL |
|-------------|-----|
| **Production** | `https://bank42api.victoriousbush-d930b25a.eastus.azurecontainerapps.io` |

## Authentication

Two auth methods are supported:

| Method | Header | Use Case |
|--------|--------|----------|
| **API Key** | `x-api-key: <key>` | Seed endpoint, A2A without user context |
| **JWT Bearer** | `Authorization: Bearer <jwt>` | All user-scoped endpoints, A2A with user data |

**API Key:** `HHUDvNLzIRatU5GeMv58p7wJbJokxmMK-k8yc1JTlUw`

**JWT Flow:** Register or login to get a JWT, then pass it in the `Authorization` header.

---

## REST API Endpoints

### Health & Seed

#### `GET /api/health`

Health check — no auth required.

```bash
curl $BASE/api/health
```

```json
{"status": "healthy", "service": "42-bank-api"}
```

#### `POST /api/seed`

Seed the database with test users `alice` and `bob`. Requires API key.

```bash
curl -X POST $BASE/api/seed \
  -H "x-api-key: $API_KEY"
```

```json
{"status": "ok", "results": ["alice: created", "bob: created"]}
```

---

### Authentication

#### `POST /api/auth/register`

Register a new user. Returns JWT tokens.

```bash
curl -X POST $BASE/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myuser",
    "public_key": "base64-encoded-public-key",
    "device_id": "unique-device-id",
    "device_name": "My Phone",
    "biometric_enabled": false
  }'
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | 3-50 chars, lowercase alphanumeric + underscore |
| `public_key` | string | Yes | ML-DSA-44 public key (base64) — use placeholder for testing |
| `device_id` | string | Yes | Unique device identifier |
| `device_name` | string | No | Human-readable device name |
| `biometric_enabled` | bool | No | Default `true` |
| `push_token` | string | No | Expo/APNs/FCM push token |

**Response (200):**
```json
{
  "user_id": "myuser_xK9mP2...",
  "username": "myuser",
  "token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "expires_at": "2026-04-01T12:00:00+00:00",
  "public_key": "base64-encoded-public-key"
}
```

#### `POST /api/auth/login`

Login with username and device ID.

```bash
curl -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myuser",
    "device_id": "unique-device-id"
  }'
```

#### `POST /api/auth/refresh`

Refresh an access token using a refresh token.

```bash
curl -X POST $BASE/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

#### `POST /api/auth/logout`

Revoke the current JWT.

```bash
curl -X POST $BASE/api/auth/logout \
  -H "Authorization: Bearer $JWT"
```

#### `GET /api/auth/me`

Get current user info.

```bash
curl $BASE/api/auth/me \
  -H "Authorization: Bearer $JWT"
```

**Response:**
```json
{
  "user_id": "myuser_xK9mP2...",
  "username": "myuser",
  "public_key": "base64...",
  "created_at": "2026-03-25T...",
  "devices": [{"device_id_hash": "...", "device_name": "My Phone"}]
}
```

---

### Accounts

#### `GET /api/accounts`

Get account balances. Requires JWT.

```bash
curl $BASE/api/accounts \
  -H "Authorization: Bearer $JWT"
```

```json
{"accounts": [{"type": "checking", "balance": 0.0, "account_number": "MYUSERAB"}]}
```

#### `GET /api/accounts/transactions`

Get transaction history. Requires JWT.

```bash
curl $BASE/api/accounts/transactions \
  -H "Authorization: Bearer $JWT"
```

```json
{"transactions": [{"id": "...", "sender": "alice", "recipient": "myuser", "amount": 50.0, "description": "Welcome", "timestamp": "...", "status": "completed"}]}
```

---

### Key Management

#### `GET /api/keys/status`

Check if user has a key backup.

```bash
curl $BASE/api/keys/status \
  -H "Authorization: Bearer $JWT"
```

```json
{"has_backup": false, "backup_id": null, "timestamp": null, "recovery_hint": null}
```

#### `POST /api/keys/backup`

Backup an encrypted private key.

```bash
curl -X POST $BASE/api/keys/backup \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "encrypted_private_key": "base64-encrypted-key",
    "public_key": "base64-public-key",
    "recovery_key_hash": "sha256-hash-of-recovery-key",
    "recovery_hint": "My hint"
  }'
```

#### `POST /api/keys/challenge`

Get a restore challenge nonce.

```bash
curl -X POST $BASE/api/keys/challenge \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"backup_id": "<backup_id>"}'
```

#### `POST /api/keys/restore`

Restore encrypted key using challenge proof.

#### `DELETE /api/keys/backup`

Delete key backup.

---

### Notifications

#### `GET /api/notifications/preferences`

Get notification preferences.

```bash
curl $BASE/api/notifications/preferences \
  -H "Authorization: Bearer $JWT"
```

```json
{"transactions": true, "payment_requests": true, "security_alerts": true, "marketing": false}
```

#### `PUT /api/notifications/preferences`

Update preferences.

```bash
curl -X PUT $BASE/api/notifications/preferences \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"transactions": true, "payment_requests": false, "security_alerts": true, "marketing": false}'
```

#### `POST /api/notifications/register`

Register push notification token.

#### `GET /api/notifications/history`

Get notification history.

---

## A2A Agents

5 specialized agents accessible via the A2A protocol. Each agent has message and streaming endpoints.

### Authentication

A2A agents accept either:
- `Authorization: Bearer <JWT>` — **recommended**, agents operate on authenticated user's data
- `x-api-key: <key>` — no user context, agents have limited functionality

### Common Request Format

All agent endpoints accept:

```json
{
  "message": {
    "contextId": "optional-uuid",
    "parts": [{"kind": "text", "text": "Your message here"}]
  }
}
```

### Common Response Format

```json
{
  "result": {
    "kind": "message",
    "role": "agent",
    "parts": [{"kind": "text", "text": "Agent's response"}],
    "messageId": "uuid",
    "contextId": "uuid"
  }
}
```

---

### Triage Agent (`/a2a/triage`)

Routes user queries to the appropriate specialist agent. Does NOT have banking tools itself.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /a2a/triage` | GET | Agent card |
| `POST /a2a/triage/v1/message` | POST | Route and respond |
| `POST /a2a/triage/v1/message:stream` | POST | Streaming version |

**Routing rules:**
- Balance/history queries → InquiryAgent
- Send/transfer/pay → TransactionAgent
- Products/loans/accounts → AdvisorAgent
- Complaints/escalations → BankManager

```bash
# Triage routes to Inquiry agent
curl -s -X POST $BASE/a2a/triage/v1/message \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"What is my balance?"}]}}'
```

---

### Inquiry Agent (`/a2a/inquiry`)

Handles balance and transaction history queries.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /a2a/inquiry` | GET | Agent card |
| `POST /a2a/inquiry/v1/message` | POST | Non-streaming |
| `POST /a2a/inquiry/v1/message:stream` | POST | Streaming |

**Available tools (called by the agent):**
- `check_balance` — View checking account balance
- `view_history` — View transaction history
- `list_my_accounts` — List all accounts

```bash
curl -s -X POST $BASE/a2a/inquiry/v1/message \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"Show my recent transactions"}]}}'
```

---

### Transaction Agent (`/a2a/transaction`)

Handles money transfers and payment requests.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /a2a/transaction` | GET | Agent card |
| `POST /a2a/transaction/v1/message` | POST | Non-streaming |
| `POST /a2a/transaction/v1/message:stream` | POST | Streaming |

**Available tools:**
- `send_money(to, amount, note)` — Transfer funds to another user
- `request_money(from_user, amount, note)` — Request payment
- `list_pending_requests` — List pending requests
- `approve_payment(request_id)` — Approve a pending request

```bash
curl -s -X POST $BASE/a2a/transaction/v1/message \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"Send $50 to bob for dinner"}]}}'
```

---

### Advisor Agent (`/a2a/advisor`)

Handles product inquiries and account opening.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /a2a/advisor` | GET | Agent card |
| `POST /a2a/advisor/v1/message` | POST | Non-streaming |
| `POST /a2a/advisor/v1/message:stream` | POST | Streaming |

**Available tools:**
- `list_products` — List bank products
- `open_new_account(account_type)` — Open a new account (checking, savings, loan, mortgage, credit_card)

```bash
curl -s -X POST $BASE/a2a/advisor/v1/message \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"What savings accounts do you offer?"}]}}'
```

---

### Manager Agent (`/a2a/manager`)

Handles escalations and oversight.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /a2a/manager` | GET | Agent card |
| `POST /a2a/manager/v1/message` | POST | Non-streaming |
| `POST /a2a/manager/v1/message:stream` | POST | Streaming |

```bash
curl -s -X POST $BASE/a2a/manager/v1/message \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"I have an unauthorized charge on my account"}]}}'
```

---

### List All Agents

```bash
curl -s $BASE/a2a/ -H "x-api-key: $API_KEY" | python3 -m json.tool
```

### A2A Health

```bash
curl -s $BASE/a2a/health -H "x-api-key: $API_KEY"
```

```json
{"status": "healthy", "protocol": "A2A", "version": "0.3.0", "agents": ["triage", "inquiry", "transaction", "advisor", "manager"]}
```

---

## Streaming (SSE)

All agents support Server-Sent Events streaming. Use `message:stream` endpoint.

```bash
curl -s -N -X POST $BASE/a2a/transaction/v1/message:stream \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"Send $10 to bob"}]}}'
```

Output:
```
data: {"result":{"kind":"message","role":"agent","parts":[{"kind":"text","text":"I"}],"messageId":"...","contextId":"..."}}

data: {"result":{"kind":"message","role":"agent","parts":[{"kind":"text","text":" will"}],"messageId":"...","contextId":"..."}}

...

data: [DONE]
```

---

## End-to-End Test Script

Copy and run this script to test everything:

```bash
#!/bin/bash
set -e

BASE="https://bank42api.victoriousbush-d930b25a.eastus.azurecontainerapps.io"
API_KEY="HHUDvNLzIRatU5GeMv58p7wJbJokxmMK-k8yc1JTlUw"
USER="test_$(date +%s)"

echo "============================================"
echo "  42-Bank API Test Suite"
echo "  User: $USER"
echo "============================================"

# 1. Health
echo ""
echo "--- Health Check ---"
curl -s $BASE/api/health | python3 -m json.tool

# 2. Seed
echo ""
echo "--- Seed Database ---"
curl -s -X POST $BASE/api/seed -H "x-api-key: $API_KEY" | python3 -m json.tool

# 3. Register
echo ""
echo "--- Register User ---"
REG=$(curl -s -X POST $BASE/api/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USER\",\"public_key\":\"dGVzdA==\",\"device_id\":\"dev-$USER\",\"device_name\":\"Test\",\"biometric_enabled\":false}")
echo "$REG" | python3 -m json.tool
JWT=$(echo "$REG" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "JWT acquired: ${JWT:0:40}..."

# 4. Me
echo ""
echo "--- User Info ---"
curl -s $BASE/api/auth/me -H "Authorization: Bearer $JWT" | python3 -m json.tool

# 5. Accounts
echo ""
echo "--- Accounts ---"
curl -s $BASE/api/accounts -H "Authorization: Bearer $JWT" | python3 -m json.tool

# 6. Transactions
echo ""
echo "--- Transactions ---"
curl -s $BASE/api/accounts/transactions -H "Authorization: Bearer $JWT" | python3 -m json.tool

# 7. Keys status
echo ""
echo "--- Key Backup Status ---"
curl -s $BASE/api/keys/status -H "Authorization: Bearer $JWT" | python3 -m json.tool

# 8. Notification prefs
echo ""
echo "--- Notification Preferences ---"
curl -s $BASE/api/notifications/preferences -H "Authorization: Bearer $JWT" | python3 -m json.tool

# 9. A2A Health
echo ""
echo "--- A2A Health ---"
curl -s $BASE/a2a/health -H "x-api-key: $API_KEY" | python3 -m json.tool

# 10. List agents
echo ""
echo "--- List Agents ---"
curl -s $BASE/a2a/ -H "x-api-key: $API_KEY" | python3 -m json.tool

# 11. Inquiry Agent
echo ""
echo "--- Inquiry Agent: Check Balance ---"
curl -s -X POST $BASE/a2a/inquiry/v1/message \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"What is my balance?"}]}}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
for p in d.get('result',{}).get('parts',[]):
    if p.get('kind')=='text': print(p['text'])
"

# 12. Triage -> Inquiry
echo ""
echo "--- Triage Agent: Route to Inquiry ---"
curl -s -X POST $BASE/a2a/triage/v1/message \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"Show my balance"}]}}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
for p in d.get('result',{}).get('parts',[]):
    if p.get('kind')=='text': print(p['text'])
"

# 13. Triage -> Transaction
echo ""
echo "--- Triage Agent: Route to Transaction ---"
curl -s -X POST $BASE/a2a/triage/v1/message \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"Send 5 dollars to bob"}]}}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
for p in d.get('result',{}).get('parts',[]):
    if p.get('kind')=='text': print(p['text'])
"

# 14. Advisor
echo ""
echo "--- Advisor Agent: Products ---"
curl -s -X POST $BASE/a2a/advisor/v1/message \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"What products do you have?"}]}}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
for p in d.get('result',{}).get('parts',[]):
    if p.get('kind')=='text': print(p['text'])
"

# 15. Manager
echo ""
echo "--- Manager Agent: Complaint ---"
curl -s -X POST $BASE/a2a/manager/v1/message \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"message":{"parts":[{"kind":"text","text":"I have a complaint about fees"}]}}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
for p in d.get('result',{}).get('parts',[]):
    if p.get('kind')=='text': print(p['text'])
"

# 16. Logout
echo ""
echo "--- Logout ---"
curl -s -X POST $BASE/api/auth/logout -H "Authorization: Bearer $JWT" | python3 -m json.tool

echo ""
echo "============================================"
echo "  All tests completed!"
echo "============================================"
```

---

## Architecture

```
+-------------------------------------------------------------+
|  Mobile App / curl / Test Script                            |
|  Auth: JWT Bearer or x-api-key                              |
+--------------+----------------------------------------------+
               |
               v
+-------------------------------------------------------------+
|  FastAPI (port 8000)                                        |
|                                                             |
|  REST API (/api/*)          A2A Agents (/a2a/*)             |
|  +-- /api/health            +-- /a2a/health                 |
|  +-- /api/auth/*            +-- /a2a/triage                 |
|  +-- /api/accounts/*        +-- /a2a/inquiry                |
|  +-- /api/keys/*            +-- /a2a/transaction            |
|  +-- /api/notifications/*   +-- /a2a/advisor                |
|  +-- /api/seed              +-- /a2a/manager                |
|                                                             |
|  +------------------------------------------------------+  |
|  | Azure OpenAI Model Router                             |  |
|  | gpt-4.1-nano, gpt-4.1-mini, o4-mini, etc.            |  |
|  +------------------------------------------------------+  |
|                                                             |
|  +------------------------------------------------------+  |
|  | MCP Tools (embedded, same process)                    |  |
|  | check_balance, send_money, view_history, etc.         |  |
|  | User context via contextvars.ContextVar               |  |
|  +------------------------------------------------------+  |
|                                                             |
|  +------------------------------------------------------+  |
|  | Azure Cosmos DB (serverless)                          |  |
|  | users, change_feed, products, auth_devices,           |  |
|  | key_backups, restore_challenges, token_blacklist      |  |
|  +------------------------------------------------------+  |
+-------------------------------------------------------------+
```

## MCP Tools Reference

These tools are called by the A2A agents when processing user requests:

| Tool | Parameters | Description |
|------|-----------|-------------|
| `check_balance` | — | View checking account balance |
| `view_history` | — | View transaction history |
| `list_my_accounts` | — | List all accounts and balances |
| `send_money` | `to`, `amount`, `note` | Transfer funds to another user |
| `request_money` | `from_user`, `amount`, `note` | Request payment from someone |
| `list_pending_requests` | — | List pending payment requests |
| `approve_payment` | `request_id` | Approve a pending request |
| `list_products` | — | List bank products (checking, savings, loans, etc.) |
| `open_new_account` | `account_type` | Open new account: checking, savings, loan, mortgage, credit_card |

## Product Catalog

| Product | Type | Interest Rate |
|---------|------|--------------|
| Standard Checking | checking | 0.0% |
| High-Yield Savings | savings | 4.5% |
| Home Mortgage | mortgage | 3.8% |
| Express Auto Loan | loan | 5.9% |
| Infinite Rewards Card | credit_card | 15.4% |

## Environment Variables

| Variable | Deployed Value | Description |
|----------|---------------|-------------|
| `AZURE_AI_PROJECT_ENDPOINT` | `https://42-bank-useast-2-resource.openai.azure.com/` | Azure OpenAI endpoint |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | `model-router` | Model deployment name |
| `AZURE_OPENAI_API_VERSION` | `2025-01-01-preview` | API version |
| `APP_ENV` | `production` | Runtime environment |
| `COSMOS_ENDPOINT` | `https://42bank-cosmos-uwchkmtayph5i.documents.azure.com:443/` | Cosmos DB |
| `COSMOS_DATABASE` | `banking` | Database name |
| `JWT_SECRET` | *(secret)* | JWT signing key |

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Missing or invalid auth | Pass `x-api-key` or valid JWT |
| `Token has expired` | JWT expired (7 day default) | Login again to get new JWT |
| `User not found` | Agent using wrong context | Use JWT auth (not API key) for user-scoped queries |
| `Insufficient funds` | Not enough balance | Seed users have $0; transfer from seeded alice/bob |
| `Internal Server Error` | Cosmos DB issue | Check logs: `az containerapp logs show --name bank42api --resource-group 42-bank-hackathon --tail 20` |

## Deployment

```bash
# Build and push (from project root)
docker build --platform linux/amd64 -t 42bankacruwchkmtayph5i.azurecr.io/42bank:latest .
docker push 42bankacruwchkmtayph5i.azurecr.io/42bank:latest

# Update container app
az containerapp update --name bank42api --resource-group 42-bank-hackathon \
  --image 42bankacruwchkmtayph5i.azurecr.io/42bank:latest \
  --set-env-vars "REBUILD=$(date +%s)"
```
