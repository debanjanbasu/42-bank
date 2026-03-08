# Mobile Development Guide

Complete guide for developing and testing the 42-Bank mobile app without App Store submission.

## Quick Start (No App Store Required)

### Option 1: Expo Go (Fastest - Limited Native Features)

```bash
cd mobile
npm install
npx expo start
# Scan QR code with Expo Go app
```

**Limitations:**
- No native AI (Apple Intelligence / Gemini Nano)
- No biometric auth
- Limited push notifications

### Option 2: Expo Dev Client (Recommended - Full Features)

```bash
cd mobile

# Install dependencies
npm install

# Build development client (one-time)
npx expo run:ios
# OR
npx expo run:android

# After first build, use:
npx expo start --dev-client
```

**Benefits:**
- ✅ All native features (AI, biometrics, push)
- ✅ Hot reload for instant updates
- ✅ Install via QR code or USB
- ✅ No App Store needed

### Option 3: Physical Device with Native Build

```bash
# iOS (requires Mac + Xcode)
npx expo run:ios --device

# Android (requires Android Studio)
npx expo run:android --device
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Mobile App (Expo Router)                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ App Shell (expo-router)                                  │   │
│  │  • app/_layout.tsx - Root layout                         │   │
│  │  • app/(auth)/ - Login/Register screens                  │   │
│  │  • app/(tabs)/ - Main banking screens                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Services                                                  │   │
│  │  • A2AClient.ts - Agent communication                    │   │
│  │  • KeyManager.ts - ML-DSA-44 crypto                      │   │
│  │  • Notifications.ts - Push notifications                 │   │
│  │  • SecureStorage.ts - Keychain/Keystore                  │   │
│  │  • NativeAI.ts - Apple Intelligence / Gemini Nano        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Native Modules                                            │   │
│  │  • iOS: AppleIntelligenceBridge.swift                    │   │
│  │  • Android: GeminiNanoBridge.kt                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ A2A Protocol (HTTPS)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 42-Bank Backend (Azure)                                         │
│  • API: /api/auth/* - Authentication                           │
│  • API: /api/keys/* - Key management                           │
│  • API: /api/notifications/* - Push notifications              │
│  • A2A: /a2a/* - Agent communication                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Setup

### 1. Install Dependencies

```bash
cd mobile
npm install
```

### 2. Configure Environment

Create `mobile/.env`:

```env
# Backend API
API_URL=http://localhost:8000
API_URL_PROD=https://42bank.azurewebsites.net

# Development mode
ENV=development

# Push notifications (Expo)
EXPO_PROJECT_ID=your-project-id

# Feature flags
ENABLE_NATIVE_AI=true
ENABLE_BIOMETRIC=true
```

### 3. Run Development Server

```bash
# Start backend (Terminal 1)
cd ..
./dev.sh alice

# Start mobile app (Terminal 2)
cd mobile
npx expo start --dev-client
```

---

## Development Workflow

### Day-to-Day Development

```bash
# 1. Start backend
./dev.sh alice

# 2. Start mobile app
cd mobile
npx expo start --dev-client

# 3. Make changes - hot reload automatically
# Edit files, see changes instantly

# 4. Test on device
# Press 'i' for iOS simulator
# Press 'a' for Android emulator
# Scan QR for physical device
```

### Testing Push Notifications

```bash
# Development (Expo notifications)
# 1. Open app on device
# 2. Register for notifications
# 3. Use Expo push token for testing

# Test notification from backend
curl -X POST http://localhost:8000/api/notifications/test \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Screens Structure

### Auth Flow

```
app/
├── _layout.tsx           # Root layout
├── (auth)/
│   ├── _layout.tsx       # Auth layout
│   ├── index.tsx         # Splash screen
│   ├── login.tsx         # Login screen
│   └── register.tsx      # Registration screen
└── (tabs)/
    ├── _layout.tsx       # Tab navigation
    ├── index.tsx         # Home/Chat
    ├── accounts.tsx      # Account list
    ├── transactions.tsx  # Transaction history
    └── settings.tsx      # Settings
```

### Screen Implementation Example

```tsx
// app/(tabs)/index.tsx
import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity } from 'react-native';
import { A2AClient } from '@/services/A2AClient';

export default function HomeScreen() {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);

  const client = new A2AClient(API_URL, jwtToken);

  const sendMessage = async () => {
    setLoading(true);
    try {
      const result = await client.sendMessage('triage', message);
      setResponse(result.result.parts[0].text);
    } catch (error) {
      setResponse('Error: ' + error.message);
    }
    setLoading(false);
  };

  return (
    <View style={{ flex: 1, padding: 20 }}>
      <Text style={{ fontSize: 24, marginBottom: 20 }}>42-Bank</Text>
      
      <TextInput
        placeholder="Ask about your balance..."
        value={message}
        onChangeText={setMessage}
        style={{ borderWidth: 1, padding: 10, marginBottom: 10 }}
      />
      
      <TouchableOpacity
        onPress={sendMessage}
        style={{ backgroundColor: '#1a1a2e', padding: 15, borderRadius: 8 }}
      >
        <Text style={{ color: 'white', textAlign: 'center' }}>
          {loading ? 'Sending...' : 'Send'}
        </Text>
      </TouchableOpacity>

      {response && (
        <Text style={{ marginTop: 20 }}>{response}</Text>
      )}
    </View>
  );
}
```

---

## Services Implementation

### Notifications Service

```typescript
// src/services/Notifications.ts
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export class NotificationService {
  static async register(): Promise<string | null> {
    if (!Device.isDevice) {
      console.log('Push notifications only work on physical devices');
      return null;
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      console.log('Push notification permission denied');
      return null;
    }

    const token = await Notifications.getExpoPushTokenAsync({
      projectId: process.env.EXPO_PROJECT_ID,
    });

    // Register with backend
    await fetch(`${API_URL}/api/notifications/register`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${jwtToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        push_token: token.data,
        platform: Platform.OS,
        device_id: Device.modelName,
      }),
    });

    return token.data;
  }

  static async listen(callback: (notification: any) => void) {
    Notifications.addNotificationReceivedListener(callback);
  }
}
```

### Biometric Auth

```typescript
// src/services/BiometricAuth.ts
import * as LocalAuthentication from 'expo-local-authentication';

export class BiometricAuthService {
  static async isAvailable(): Promise<boolean> {
    const compatible = await LocalAuthentication.hasHardwareAsync();
    const enrolled = await LocalAuthentication.isEnrolledAsync();
    return compatible && enrolled;
  }

  static async authenticate(reason: string = 'Authenticate to continue'): Promise<boolean> {
    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: reason,
        fallbackLabel: 'Use Passcode',
        cancelLabel: 'Cancel',
        disableDeviceFallback: false,
      });
      
      return result.success;
    } catch (error) {
      console.error('Biometric auth error:', error);
      return false;
    }
  }
}
```

---

## Native AI Integration

### iOS (Apple Intelligence)

```swift
// ios/AppleIntelligenceBridge.swift
import Foundation
import CoreML
import NaturalLanguage

@objc(AppleIntelligenceBridge)
class AppleIntelligenceBridge: NSObject {
  
  @objc
  func isAvailable() -> Bool {
    if #available(iOS 18.0, *) {
      return true
    }
    return false
  }
  
  @objc
  func classifyIntent(_ text: String, resolve: @escaping RCTPromiseResolveBlock) {
    let lowercased = text.lowercased()
    
    if lowercased.contains("balance") || lowercased.contains("account") {
      resolve("inquiry")
    } else if lowercased.contains("send") || lowercased.contains("transfer") {
      resolve("transaction")
    } else if lowercased.contains("product") || lowercased.contains("open") {
      resolve("advisor")
    } else {
      resolve("general")
    }
  }
}
```

### Android (Gemini Nano)

```kotlin
// android/GeminiNanoBridge.kt
package com.bank42.mobile

import com.google.ai.client.generativeai.GenerativeModel
import com.google.ai.client.generativeai.type.content

class GeminiNanoBridge {
    private var generativeModel: GenerativeModel? = null

    suspend fun initialize() {
        generativeModel = GenerativeModel(
            modelName = "gemini-nano",
            context = context
        )
    }

    suspend fun classifyIntent(text: String): String {
        val prompt = """
        Classify this banking query into one of: inquiry, transaction, advisor, general.
        Query: $text
        Return only the category name.
        """
        
        val response = generativeModel?.generateContent(prompt)
        return response?.text?.trim() ?: "general"
    }
}
```

---

## Testing

### Unit Tests

```bash
npm test
```

### E2E Tests

```bash
# Install Detox
npm install --save-dev detox detox-expo-helpers

# Build test app
npx expo run:ios --configuration Release

# Run E2E tests
npm run test:e2e
```

### Manual Testing Checklist

- [ ] Register new user
- [ ] Login with existing user
- [ ] Check balance
- [ ] Send money to another user
- [ ] Request payment
- [ ] Approve payment request
- [ ] View transaction history
- [ ] Receive push notification
- [ ] Biometric authentication
- [ ] Key backup/restore
- [ ] Logout and re-login

---

## Debugging

### React Native Debugger

```bash
# Install standalone debugger
brew install --cask react-native-debugger

# Open debugger
open "rndebugger://set-debugger-loc?host=localhost&port=19000"
```

### Console Logs

```tsx
import { LogBox } from 'react-native';

// Ignore specific warnings
LogBox.ignoreLogs(['Non-serializable values were found']);
```

### Network Requests

```tsx
// Enable network debugging
import { enableExpoNetworkLogging } from 'react-native-network-logger';

enableExpoNetworkLogging();
```

---

## Deployment

### Build for Testing (Development Build)

```bash
# iOS
eas build --profile development --platform ios

# Android
eas build --profile development --platform android

# Install on device
eas build:run --platform ios
```

### Build for Production

```bash
# iOS App Store
eas build --profile production --platform ios
eas submit --platform ios

# Android Play Store
eas build --profile production --platform android
eas submit --platform android
```

---

## Troubleshooting

### Common Issues

**Push notifications not working:**
```bash
# Ensure physical device (not simulator)
# Check permissions in app.json
# Verify Expo project ID
```

**Native AI not available:**
```bash
# iOS: Requires iOS 18+ device
# Android: Requires Pixel 8+ or compatible device
# Check device capabilities
```

**Biometric auth failing:**
```bash
# Ensure biometrics enrolled on device
# Check app.json permissions
# Test on physical device
```

---

## Next Steps

1. ✅ Backend API endpoints ready
2. ✅ Push notifications configured
3. 🔄 Build Expo app shell
4. 🔄 Implement screens
5. 🔄 Add native AI bridges
6. 🔄 Test on devices
7. 🔄 Submit to stores (optional)

---

## Resources

- [Expo Documentation](https://docs.expo.dev/)
- [React Native Documentation](https://reactnative.dev/)
- [Azure Notification Hubs](https://learn.microsoft.com/azure/notification-hubs/)
- [Apple Intelligence](https://developer.apple.com/apple-intelligence/)
- [Gemini Nano](https://developer.android.com/developers/gemini-nano)
