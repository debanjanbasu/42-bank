# 42-Bank Mobile App

React Native mobile app for 42-Bank, built with Expo 55.

## Features

- **A2A Protocol**: Agent-to-agent communication with cloud banking agents via SSE streaming
- **Quantum-Safe Security**: ML-DSA-44 cryptographic keys stored in secure enclave
- **Biometric Auth**: Face ID / Touch ID / Fingerprint authentication
- **Offline Cache**: AsyncStorage-backed account and transaction caching
- **Push Notifications**: Transaction alerts via Expo Notifications

## Quick Start

```bash
# Terminal 1: Start backend
./dev.sh alice

# Terminal 2: Start mobile app
cd mobile
npm install
npx expo start --dev-client
# Press 'i' for iOS, 'a' for Android
```

### Importing Keys for Existing Users

If you have existing backend accounts (e.g., `alice`, `bob`) created via the bootstrap script:

1. Generate import data: `python3 generate_mobile_keys.py`
2. In the app: **Settings** tab -> **Import Keys** -> paste JSON -> **Import**

Registering a new account from the app generates keys automatically.

## Project Structure

```
mobile/
├── app/
│   ├── _layout.tsx           # Root layout (Paper + Auth)
│   ├── (auth)/
│   │   ├── _layout.tsx       # Auth stack
│   │   ├── login.tsx         # Login screen
│   │   └── register.tsx      # Registration with key generation
│   ├── (tabs)/
│   │   ├── _layout.tsx       # Tab navigation
│   │   ├── index.tsx         # Chat screen (Gifted Chat)
│   │   ├── accounts.tsx      # Account balances
│   │   ├── transactions.tsx  # Transaction history
│   │   └── settings.tsx      # Settings & logout
│   └── +not-found.tsx
├── src/
│   ├── config/env.ts         # Environment configuration
│   ├── services/
│   │   ├── A2AClient.ts      # A2A protocol client (SSE streaming)
│   │   ├── APIClient.ts      # Centralized HTTP client
│   │   ├── AuthService.ts    # Auth API client
│   │   ├── CacheService.ts   # Offline cache (AsyncStorage)
│   │   ├── KeyManager.ts     # ML-DSA-44 key management
│   │   ├── NotificationService.ts  # Push notification registration
│   │   └── StorageService.ts # Secure storage wrapper
│   ├── components/
│   │   ├── ErrorBoundary.tsx
│   │   └── TransactionConfirmModal.tsx
│   ├── contexts/AuthContext.tsx
│   ├── hooks/
│   │   ├── useA2A.ts
│   │   ├── useBiometric.ts
│   │   └── useTransactionSigning.ts
│   ├── utils/
│   │   ├── theme.ts
│   │   └── crypto.ts
│   └── types/
│       ├── index.ts
│       └── event-source-polyfill.d.ts
├── patches/
│   └── react-native-gifted-chat+3.3.2.patch
├── package.json
├── app.json
├── eas.json
├── tsconfig.json
└── babel.config.js
```

## Configuration

For physical device testing, override the API URL in `mobile/app.json`:

```json
{
  "expo": {
    "extra": {
      "apiUrl": "http://192.168.1.100:8000"
    }
  }
}
```

See `mobile/src/config/env.ts` for environment-based configuration (development/staging/production).

## Path Aliases

Imports use `@/` prefix (resolves to `src/`):

```typescript
import { useAuth } from '@/contexts/AuthContext';  // ✅
import { useAuth } from '@/src/contexts/AuthContext';  // ❌
```

## Key Management

- **ML-DSA-44** via `@noble/post-quantum` (JS/WASM, no native modules)
- Private keys in **Keychain** (iOS) / **Keystore** (Android)
- Keys never leave the device

## Commands

```bash
npm install          # Install dependencies
npx expo start --dev-client  # Start Metro bundler
npm run ios          # Run on iOS simulator
npm run android      # Run on Android emulator
npm run typecheck    # TypeScript type checking
```
