# 42-Bank Mobile App

React Native / Flutter mobile app for 42-Bank, featuring on-device AI integration with native platform services.

## Features

- **On-Device AI**: Uses Apple Intelligence (iOS) and Gemini Nano (Android)
- **A2A Protocol**: Direct agent-to-agent communication with cloud agents
- **Quantum-Safe Security**: ML-DSA-44 cryptographic keys in secure enclave
- **Biometric Auth**: Face ID / Touch ID / Fingerprint authentication
- **Real-time Streaming**: SSE streaming for responsive conversations

## Architecture

```
┌─────────────────────────────────────────────────┐
│ Mobile App (React Native / Flutter)             │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │ On-Device AI                             │   │
│  │ • iOS: Apple Intelligence / Core ML      │   │
│  │ • Android: Gemini Nano / ML Kit          │   │
│  └──────────────────────────────────────────┘   │
│                     │                            │
│  ┌─────────────────▼────────────────────────┐   │
│  │ A2A Client (src/services/A2AClient.ts)   │   │
│  │ • HTTP/SSE communication                 │   │
│  │ • JWT authentication                     │   │
│  │ • Message routing                        │   │
│  └──────────────────────────────────────────┘   │
│                     │                            │
│  ┌─────────────────▼────────────────────────┐   │
│  │ Key Manager (src/services/KeyManager.ts) │   │
│  │ • ML-DSA-44 key generation               │   │
│  │ • Secure enclave storage                 │   │
│  │ • Transaction signing                    │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
└─────────────────────────────────────────────────┘
                      │
                      │ A2A Protocol (HTTPS)
                      ▼
┌─────────────────────────────────────────────────┐
│ 42-Bank Cloud (Azure)                           │
│ • Triage/Inquiry/Transaction Agents             │
│ • Qwen3.5-35B-A3B (MoE)                         │
│ • Cosmos DB                                     │
└─────────────────────────────────────────────────┘
```

## Getting Started

### Prerequisites

- Node.js 18+
- React Native CLI or Flutter
- Xcode 15+ (for iOS)
- Android Studio Hedgehog+ (for Android)
- Physical device with AI capabilities (iPhone 15 Pro+ or Pixel 8+)

### Installation

```bash
# Install dependencies
npm install

# iOS
cd ios && pod install

# Start metro bundler
npx expo start --dev-client

# Run on iOS
npm run ios

# Run on Android
npm run android
```

### Configuration

Create `.env` file:

```env
API_ENDPOINT=https://42bank.azurewebsites.net
API_KEY=your-api-key-here
```

## Project Structure

```
mobile/
├── src/
│   ├── components/         # UI components
│   │   ├── ChatScreen.tsx
│   │   ├── TransactionSign.tsx
│   │   └── BiometricAuth.tsx
│   │
│   ├── services/           # Business logic
│   │   ├── A2AClient.ts    # A2A protocol client
│   │   ├── KeyManager.ts   # Crypto key management
│   │   ├── NativeAI.ts     # Native AI bridge
│   │   └── SecureStorage.ts # Keychain/Keystore
│   │
│   ├── native/             # Native modules
│   │   ├── ios/
│   │   │   └── AppleIntelligenceBridge.swift
│   │   └── android/
│   │       └── GeminiNanoBridge.kt
│   │
│   └── utils/              # Utilities
│       └── crypto.ts
│
├── package.json
└── README.md
```

## API Reference

### A2AClient

```typescript
import { A2AClient } from './services/A2AClient';

// Initialize client
const client = new A2AClient(
  'https://42bank.azurewebsites.net',
  jwtToken
);

// Send message (non-streaming)
const response = await client.sendMessage('triage', 'What is my balance?');

// Send message with streaming
await client.sendMessageStream('triage', 'Send $50 to bob', (chunk, done) => {
  console.log(chunk);
  if (done) console.log('Complete!');
});

// List available agents
const agents = await client.listAgents();
```

### KeyManager

```typescript
import { KeyManager } from './services/KeyManager';

// Generate new ML-DSA-44 keypair
const { publicKey, encryptedBackup } = await KeyManager.generateKeys();

// Sign transaction
const signature = await KeyManager.signTransaction(transactionData);

// Backup keys to cloud
await KeyManager.backupKeys(encryptedBackup);

// Restore from backup (on new device)
await KeyManager.restoreFromBackup(backupId, recoveryKey);
```

### NativeAI (iOS)

```typescript
import { NativeAI } from './services/NativeAI';

// Check if Apple Intelligence is available
const available = await NativeAI.isAvailable();

// Classify user intent locally
const intent = await NativeAI.classifyIntent('What is my balance?');
// Returns: 'inquiry' | 'transaction' | 'advisor' | 'general'

// Generate local response
const response = await NativeAI.generateResponse(prompt);
```

## Authentication Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Mobile App  │     │ API Server  │     │  Cosmos DB  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │ 1. Generate       │                   │
       │    ML-DSA-44      │                   │
       │    keypair        │                   │
       │                   │                   │
       │ 2. POST /api/auth/register            │
       │    {username, public_key, device_id}  │
       │──────────────────►│                   │
       │                   │ 3. Create user    │
       │                   │──────────────────►│
       │                   │                   │
       │ 4. Return JWT     │                   │
       │◄──────────────────│                   │
       │                   │                   │
       │ 5. Store JWT in   │                   │
       │    secure storage │                   │
       │                   │                   │
```

## Transaction Signing

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Mobile App  │     │ A2A Server  │     │   Ledger    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │ "Send $50 to bob"│                   │
       │──────────────────►│                   │
       │                   │                   │
       │ "Please sign:     │                   │
       │  send $50 to bob" │                   │
       │◄──────────────────│                   │
       │                   │                   │
       │ 2. Sign with      │                   │
       │    private key    │                   │
       │    (secure enclave)│                   │
       │                   │                   │
       │ 3. Signature      │                   │
       │──────────────────►│                   │
       │                   │ 4. Verify with    │
       │                   │    public key     │
       │                   │──────────────────►│
       │                   │                   │
       │                   │ 5. Execute        │
       │                   │    transaction    │
       │                   │──────────────────►│
       │                   │                   │
       │ "Transaction      │                   │
       │  complete!"       │                   │
       │◄──────────────────│                   │
```

## Security

### Key Storage

| Platform | Storage | Access |
|----------|---------|--------|
| iOS | Keychain | Secure Enclave |
| Android | Keystore | TEE (Trusted Execution Environment) |

### Cryptography

- **Algorithm**: ML-DSA-44 (FIPS 204)
- **Key Size**: ~2.4KB signatures, ~1.3KB public keys
- **Security Level**: Quantum-resistant (128-bit equivalent)

### Network

- All traffic over HTTPS
- JWT tokens for authentication
- Device ID binding
- Rate limiting

## Testing

```bash
# Unit tests
npm test

# Integration tests
npm run test:integration

# E2E tests (requires device)
npm run test:e2e
```

## Deployment

### iOS

1. Configure Apple Developer account
2. Enable Apple Intelligence entitlement
3. Configure push notifications
4. Submit to App Store

### Android

1. Configure Google Play Console
2. Enable Gemini Nano API
3. Configure push notifications (FCM)
4. Submit to Play Store

## License

MIT License - See LICENSE file
