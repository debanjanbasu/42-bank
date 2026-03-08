import * as Keychain from 'react-native-keychain';
import * as Crypto from 'expo-crypto';
import { ml_dsa44 } from '@noble/post-quantum/ml-dsa';

const PRIVATE_KEY_SERVICE = 'com.bank42.mldsa44_private';
const PUBLIC_KEY_SERVICE = 'com.bank42.mldsa44_public';

export interface KeyPair {
  publicKey: string;
  privateKey?: string;
}

export class KeyManager {
  static async generateKeyPair(): Promise<KeyPair> {
    const existingKey = await this.getPublicKey();
    if (existingKey) {
      throw new Error('Keys already exist. Delete existing keys first.');
    }

    const seed = new Uint8Array(32);
    const randomBytes = await Crypto.getRandomBytesAsync(32);
    seed.set(randomBytes);

    const keys = ml_dsa44.keygen(seed);
    const publicKeyBase64 = this.uint8ArrayToBase64(keys.publicKey);
    const privateKeyBase64 = this.uint8ArrayToBase64(keys.secretKey);

    await Keychain.setGenericPassword(PRIVATE_KEY_SERVICE, privateKeyBase64, {
      accessControl: Keychain.ACCESS_CONTROL.BIOMETRY_CURRENT_SET,
      accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
      securityLevel: Keychain.SECURITY_LEVEL.SECURE_HARDWARE,
    });

    await Keychain.setGenericPassword(PUBLIC_KEY_SERVICE, publicKeyBase64, {
      accessControl: Keychain.ACCESS_CONTROL.DEVICE_PASSCODE,
      accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED,
    });

    return { publicKey: publicKeyBase64, privateKey: privateKeyBase64 };
  }

  static async sign(data: string): Promise<string> {
    const credentials = await Keychain.getGenericPassword({
      service: PRIVATE_KEY_SERVICE,
      authenticationPrompt: {
        title: 'Sign Transaction',
        subtitle: 'Authenticate to sign this transaction',
        description: 'Your biometric is required to authorize this transaction',
        cancel: 'Cancel',
      },
    });

    if (!credentials) {
      throw new Error('Private key not found. Please register first.');
    }

    const privateKey = this.base64ToUint8Array(credentials.password);
    const dataBytes = new TextEncoder().encode(data);
    const signature = ml_dsa44.sign(privateKey, dataBytes);

    return this.uint8ArrayToBase64(signature);
  }

  static async verify(
    publicKeyBase64: string,
    data: string,
    signatureBase64: string
  ): Promise<boolean> {
    const publicKey = this.base64ToUint8Array(publicKeyBase64);
    const signature = this.base64ToUint8Array(signatureBase64);
    const dataBytes = new TextEncoder().encode(data);
    return ml_dsa44.verify(publicKey, dataBytes, signature);
  }

  static async getPublicKey(): Promise<string | null> {
    try {
      const credentials = await Keychain.getGenericPassword({
        service: PUBLIC_KEY_SERVICE,
      });
      if (credentials === false) {
        return null;
      }
      return credentials.password;
    } catch {
      return null;
    }
  }

  static async hasKeys(): Promise<boolean> {
    const publicKey = await this.getPublicKey();
    return publicKey !== null;
  }

  static async deleteKeys(): Promise<void> {
    await Keychain.resetGenericPassword({ service: PRIVATE_KEY_SERVICE });
    await Keychain.resetGenericPassword({ service: PUBLIC_KEY_SERVICE });
  }

  private static uint8ArrayToBase64(bytes: Uint8Array): string {
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  private static base64ToUint8Array(base64: string): Uint8Array {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
  }
}

export default KeyManager;
