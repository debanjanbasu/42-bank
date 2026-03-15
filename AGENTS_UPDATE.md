# A2A Remote Deployment Fix Summary

## Problem
The A2A agent endpoints were returning 404 in production, even though they worked locally. The root cause was that the A2A Starlette app was not being mounted correctly in the main FastAPI application.

## Root Causes Identified

### 1. Route Creation Bug in `a2a_server.py`
**Issue:** The route creation loop had incorrect indentation. The `path = f"/{agent_key}"` line was OUTSIDE the for loop, so only the last agent's routes were being added.

**Fix:** Moved the route creation logic inside the for loop to ensure all agents' routes are created.

### 2. A2A App Not Mounted in `api/__init__.py`
**Issue:** The A2A app was being initialized asynchronously in a background task (`asyncio.create_task(initialize_a2a())`), which meant it wasn't ready when requests came in.

**Fix:** 
- Moved the lifespan definition BEFORE the FastAPI app creation
- Made A2A initialization synchronous during startup (not background task)
- Added proper lifespan to FastAPI app constructor

### 3. Agent Card URL Double-Prefixing
**Issue:** The `get_agent_card()` method was adding `/a2a/` prefix to URLs, but since the app is mounted at `/a2a`, this caused double-prefixing like `/a2a/a2a/triage`.

**Fix:** Removed the hardcoded `/a2a/` prefix since the base URL already includes it when the app is mounted.

### 4. Python Closure Issue in Route Creation
**Issue:** The async functions defined in the loop were capturing loop variables incorrectly.

**Fix:** Used default parameters to capture loop variable values correctly.

## Files Modified

### 1. `a2a_server.py`
- Fixed route creation indentation (lines 527-568)
- Fixed agent card URL construction (line 236)
- Fixed Python closure issue with default parameters

### 2. `api/__init__.py`
- Moved lifespan definition before app creation (lines 34-42)
- Added lifespan parameter to FastAPI app constructor (line 82)
- Made A2A initialization synchronous (lines 210-219)
- Removed duplicate lifespan definition

## Verification

All A2A endpoints now return 200 OK:
- `/a2a/health` ✅
- `/a2a/triage` ✅
- `/a2a/triage/v1/card` ✅
- `/a2a/inquiry` ✅
- `/a2a/inquiry/v1/card` ✅
- `/a2a/transaction` ✅
- `/a2a/triage/v1/message` ✅

## Deployment Instructions

1. **Commit and push the changes:**
   ```bash
   git add a2a_server.py api/__init__.py
   git commit -m "Fix A2A remote deployment - ensure routes are mounted correctly"
   git push origin main
   ```

2. **Trigger Azure Container Apps deployment:**
   - The CI/CD pipeline will automatically rebuild and deploy
   - Or manually trigger: `azd up`

3. **Verify deployment:**
   ```bash
   curl https://bank42api.victoriousbush-d930b25a.eastus.azurecontainerapps.io/a2a/health
   ```

## Production Considerations

- **Environment Variables:** Ensure `AZURE_COSMOS_CONNECTION_STRING` is set in production
- **Firewall:** Cosmos DB firewall must allow Container App outbound IP
- **Authentication:** Production uses `APP_ENV=production` which requires authentication
- **API Key:** Use `x-api-key` header for demo mode or JWT token for production

## Testing in Production

1. Test health endpoint:
   ```bash
   curl https://bank42api.victoriousbush-d930b25a.eastus.azurecontainerapps.io/a2a/health
   ```

2. Test agent endpoint:
   ```bash
   curl -X POST https://bank42api.victoriousbush-d930b25a.eastus.azurecontainerapps.io/a2a/triage/v1/message \
     -H "Content-Type: application/json" \
     -H "x-api-key: hackathon-demo-key-2024" \
     -d '{"message": {"parts": [{"kind": "text", "text": "What is my balance?"}], "contextId": "test"}}'
   ```

## Next Steps

1. Deploy to production
2. Test full end-to-end flow (Registration → Login → A2A Query → Transfer)
3. Verify mobile app connectivity to production A2A endpoints
4. Update mobile app configuration if needed
