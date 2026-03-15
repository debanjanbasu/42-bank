# 42-Bank Comprehensive Fix Plan

## Executive Summary

After thorough testing of the deployed 42-Bank application on Azure Container Apps, I've identified **5 critical issues** preventing the AI agents and API from functioning correctly. This plan addresses all issues systematically.

**Deployment Status:**
- ✅ Container App: Running (`bank42api`)
- ✅ Cosmos DB: Connected (3 containers)
- ✅ Environment Variables: Set (COSMOS_ENDPOINT, AZURE_AI_PROJECT_ENDPOINT, etc.)
- ✅ Health Endpoint: Responding correctly
- ❌ **A2A Endpoints**: Returning 404 (CRITICAL)
- ❌ **API Authentication**: Internal Server Errors
- ❌ **Mobile App**: Not configured for production

---

## Phase 1: Fix A2A Mounting (CRITICAL)

### Issue
All A2A endpoints (`/a2a/triage`, `/a2a/inquiry`, etc.) return **404 Not Found**.

**Root Cause:** The A2A mount in `api/__init__.py` is failing silently, and the MCP server URL is hardcoded to `localhost:8001`.

### Files to Fix

#### 1. `api/a2a_mount.py` (Lines 52-64)
**Problem:** Hardcoded MCP server URL
**Fix:** Make MCP server URL configurable via environment variable

```python
# Current (Line 61):
mcp_server_url="http://localhost:8001", # Internal MCP

# Fix:
mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")
```

#### 2. `api/__init__.py` (Lines 133-157)
**Problem:** A2A mount exception handling is too broad, hiding the actual error
**Fix:** Add better error logging and validation

```python
# Current (Lines 152-157):
except Exception as e:
    logger.warning(f"⚠️ Could not mount A2A server: {e}")
    logger.warning(" A2A endpoints will not be available")

# Fix: Add stack trace and critical error logging
except Exception as e:
    import traceback
    logger.error(f"❌ CRITICAL: A2A mount failed: {e}")
    logger.error(traceback.format_exc())
    # Don't silently continue - this is critical for the app to function
    raise
```

#### 3. `a2a_server.py` (Line 473)
**Problem:** Default MCP URL hardcoded
**Fix:** Update default to use environment variable

```python
# Current (Line 473):
mcp_server_url: str = "http://localhost:8001",

# Fix:
mcp_server_url: str = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp"),
```

### Environment Variable to Add
```bash
MCP_SERVER_URL="http://localhost:8001/mcp"
```

**Note:** In single-container deployment, we need to either:
- **Option A:** Run MCP server as a sidecar (complex)
- **Option B (Recommended):** Refactor to use ledger directly instead of MCP HTTP calls

**Recommended:** Option B - The agents should call ledger methods directly, not through MCP HTTP. This eliminates the need for a separate MCP server process.

---

## Phase 2: Environment Variables

### Missing Variables

#### 1. `AZURE_OPENAI_API_KEY` (CRITICAL)
**Purpose:** Required for hosted AI mode with Azure AI Foundry
**Current:** Not set
**Fix:** Add via Azure CLI:

```bash
az containerapp update \
  --name bank42api \
  --resource-group 42-bank-hackathon \
  --set-env-vars "AZURE_OPENAI_API_KEY=<your-api-key>"
```

**Alternative:** Use Managed Identity instead of API key (more secure)

#### 2. `MCP_SERVER_URL` (from Phase 1)
```bash
az containerapp update \
  --name bank42api \
  --resource-group 42-bank-hackathon \
  --set-env-vars "MCP_SERVER_URL=http://localhost:8001/mcp"
```

### Current Environment Variables (Verified)
```json
[
  {"name": "COSMOS_ENDPOINT", "value": "https://42bank-cosmos-uwchkmtayph5i.documents.azure.com:443/"},
  {"name": "COSMOS_DATABASE", "value": "banking"},
  {"name": "APP_ENV", "value": "production"},
  {"name": "AZURE_AI_PROJECT_ENDPOINT", "value": "https://42-bank-us-east-2-resource.cognitiveservices.azure.com/"},
  {"name": "AZURE_AI_MODEL_DEPLOYMENT_NAME", "value": "model-router"},
  {"name": "JWT_SECRET", "value": "hackathon-demo-secret-key-for-jwt-signing-1234567890"},
  {"name": "REBUILD", "value": "1773532009"}
]
```

---

## Phase 3: Mobile App Configuration

### Issue
Mobile app is configured for localhost development, not production deployment.

### Files to Update

#### 1. `mobile/app.json` (Lines 64-66)
**Current:**
```json
"extra": {
  "apiUrl": "http://localhost:8000",
  "a2aUrl": "http://localhost:8000",
  "enableDebugging": true
}
```

**Fix for Production:**
```json
"extra": {
  "apiUrl": "https://bank42api.victoriousbush-d930b25a.eastus.azurecontainerapps.io",
  "a2aUrl": "https://bank42api.victoriousbush-d930b25a.eastus.azurecontainerapps.io",
  "enableDebugging": false
}
```

#### 2. `mobile/src/config/env.ts` (Line 32)
**Current:** Uses `__DEV__` to determine environment
**Issue:** May not correctly detect production build
**Fix:** Force production mode in release builds

```typescript
// Current (Line 32):
const ENV: Environment = __DEV__ ? 'development' : 'production';

// Fix: Use app.json override explicitly
const ENV: Environment = (Constants.expoConfig?.extra?.apiUrl?.includes('localhost')) 
  ? 'development' 
  : 'production';
```

### Deployment Steps
```bash
cd mobile

# For development testing:
npx expo config --type json > app-config.json

# For production build:
eas build --profile production --platform ios
eas build --profile production --platform android
```

---

## Phase 4: End-to-End Testing

### Test Matrix

| Test Case | Endpoint | Expected Result | Priority |
|-----------|----------|-----------------|----------|
| **API Health** | `/api/health` | `{"status": "healthy"}` | P0 |
| **A2A Health** | `/a2a/health` | `{"status": "healthy", "agents": [...]}` | P0 |
| **User Registration** | `POST /api/auth/register` | JWT token returned | P0 |
| **User Login** | `POST /api/auth/login` | JWT token returned | P0 |
| **A2A Balance Query** | `POST /a2a/triage/v1/message` | Balance response | P0 |
| **A2A Transfer** | `POST /a2a/transaction/v1/message` | Transfer confirmation | P1 |
| **Transaction History** | `GET /api/accounts/transactions` | Transaction list | P1 |
| **Mobile Login Flow** | Mobile App | Successful auth | P0 |
| **Mobile Balance Query** | Mobile App via A2A | Balance displayed | P0 |
| **Mobile Transfer** | Mobile App via A2A | Money sent | P1 |

### Test Commands

```bash
# 1. API Health
curl -s "https://bank42api.../api/health" | jq .

# 2. A2A Health (after fix)
curl -s "https://bank42api.../a2a/health" | jq .

# 3. User Registration
curl -s -X POST "https://bank42api.../api/auth/register" \
  -H "x-api-key: hackathon-demo-key-2024" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","device_id":"test-123","public_key":"0102030405"}' | jq .

# 4. A2A Balance Query (after fix)
curl -s "https://bank42api.../a2a/triage/v1/message" \
  -H "x-api-key: hackathon-demo-key-2024" \
  -H "Content-Type: application/json" \
  -d '{"message": {"parts": [{"kind": "text", "text": "What is my balance?"}]}}' | jq .
```

---

## Phase 5: Documentation Cleanup

### Files to Consolidate

**Current Documentation:**
- `README.md` - Quick start guide
- `DEMO.md` - 5-minute demo script
- `DEPLOY.md` - Deployment instructions
- `AGENTS.md` - Architecture guide
- `MOBILE_DEVELOPMENT.md` - Mobile dev guide
- `TESTING.md` - Testing philosophy
- `AI_TESTING_PHILOSOPHY.md` - AI testing approach
- `PRODUCTION_RELEASE.md` - Release notes
- `RELEASE_SUMMARY.md` - Release summary
- `SETUP.md` - Setup guide

### Recommended Structure

**Keep and Update:**
1. `README.md` - Main entry point with quick start
2. `AGENTS.md` - Architecture (rename to `ARCHITECTURE.md`)
3. `DEPLOY.md` - Deployment guide
4. `mobile/README.md` - Mobile-specific guide

**Consolidate Into Above:**
- `DEMO.md` → Move demo script to `README.md`
- `MOBILE_DEVELOPMENT.md` → Merge into `mobile/README.md`
- `TESTING.md` + `AI_TESTING_PHILOSOPHY.md` → Merge into `README.md` Testing section
- `PRODUCTION_RELEASE.md` + `RELEASE_SUMMARY.md` → Delete (outdated)
- `SETUP.md` → Merge into `README.md`

**Docs Directory:**
- Keep `docs/adr/` for Architecture Decision Records
- Add `docs/deployment.md` for detailed deployment steps

---

## Implementation Checklist

### Phase 1: A2A Mounting (CRITICAL)
- [ ] Fix `api/a2a_mount.py` - Make MCP URL configurable
- [ ] Fix `api/__init__.py` - Add better error logging
- [ ] Fix `a2a_server.py` - Update default MCP URL
- [ ] Deploy updated container image
- [ ] Verify A2A endpoints respond (not 404)

### Phase 2: Environment Variables
- [ ] Add `AZURE_OPENAI_API_KEY` to Container App
- [ ] Add `MCP_SERVER_URL` to Container App
- [ ] Verify environment variables in Azure Portal
- [ ] Test AI model connectivity

### Phase 3: Mobile App
- [ ] Update `mobile/app.json` with production URLs
- [ ] Test mobile app registration
- [ ] Test mobile app login
- [ ] Test mobile app balance query
- [ ] Test mobile app transfer

### Phase 4: End-to-End Testing
- [ ] Run all test cases from test matrix
- [ ] Document any remaining issues
- [ ] Create demo script for judges

### Phase 5: Documentation
- [ ] Consolidate README files
- [ ] Update architecture diagram
- [ ] Update deployment guide
- [ ] Remove outdated files

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| A2A mount continues to fail | High | Medium | Fallback to direct ledger calls |
| Azure AI Foundry connectivity issues | High | Low | Use local model for demo |
| Mobile app CORS issues | Medium | Medium | Update CORS settings |
| Cosmos DB connection timeout | Medium | Low | Add retry logic |
| JWT expiry during demo | Low | Medium | Use longer expiry or refresh |

---

## Success Criteria

✅ **All endpoints respond correctly:**
- `/api/health` returns healthy
- `/a2a/health` returns healthy with 5 agents
- `/api/auth/register` creates user
- `/api/auth/login` returns JWT

✅ **A2A agents functional:**
- Triage routes queries correctly
- Inquiry returns balance
- Transaction agent sends money
- Advisor lists products
- Manager handles escalations

✅ **Mobile app connected:**
- Can register/login
- Can query balance via A2A
- Can send money via A2A

✅ **Documentation clean:**
- Single source of truth for setup
- Clear deployment steps
- Demo script ready

---

## Estimated Time

- **Phase 1 (A2A Fix):** 30 minutes
- **Phase 2 (Environment):** 10 minutes
- **Phase 3 (Mobile App):** 20 minutes
- **Phase 4 (Testing):** 30 minutes
- **Phase 5 (Documentation):** 30 minutes

**Total: ~2 hours**

---

## Next Steps

1. **Immediate:** Fix A2A mounting (Phase 1)
2. **Then:** Add missing environment variables (Phase 2)
3. **Then:** Update mobile app config (Phase 3)
4. **Then:** Run comprehensive tests (Phase 4)
5. **Finally:** Clean up documentation (Phase 5)

**Ready to proceed with implementation.**
