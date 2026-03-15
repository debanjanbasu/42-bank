# 42-Bank Demo Script (5 Minutes)

## Pre-Demo Checklist

- [ ] Backend deployed: `https://bank42api.calmdesert-cd3f3a1f.eastus.azurecontainerapps.io`
- [ ] Database bootstrapped (5 users created)
- [ ] Mobile app ready (Expo Go)
- [ ] Test login works

## Demo Flow

### 1. Introduction (30 seconds)

**Show:** Azure Portal → Container Apps → bank42api

**Say:** 
> "42-Bank is a quantum-safe multi-agent banking platform with 5 AI agents powered by Microsoft Agent Framework, running on Azure Container Apps."

### 2. Backend Health (30 seconds)

**Open:** `https://bank42api.calmdesert-cd3f3a1f.eastus.azurecontainerapps.io/api/health`

**Expected:**
```json
{
  "status": "healthy",
  "service": "42-bank-api"
}
```

### 3. Mobile App Demo (3 minutes)

**Open:** Mobile app (Expo Go)

**Steps:**
1. **Login as "alice"** → Show balance: $2,500
2. **Send $50 to Bob** → Show transaction complete
3. **View balance** → Show: $2,450
4. **Ask AI:** "What is my balance?" → Show AI response

### 4. Technical Highlights (1 minute)

**Say:**
> "Built with:
> - Azure Container Apps (serverless compute)
> - Cosmos DB (global database)
> - ML-DSA-44 post-quantum cryptography
> - A2A protocol for AI agents"

## Backup Plan

If live demo fails, show:
- Screen recording (pre-recorded)
- Screenshots in slides
- Cosmos DB Data Explorer (data exists)

## Judges' Questions

**Q: "How is this quantum-safe?"**  
A: "ML-DSA-44 post-quantum signatures for all transactions"

**Q: "What's the cost?"**  
A: "~$0 using Azure free tier for hackathon"

**Q: "How do agents communicate?"**  
A: "A2A protocol with triage agent routing to specialists"

---

**Good luck! 🚀**
