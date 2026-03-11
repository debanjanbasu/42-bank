import * as Keychain from 'react-native-keychain';
import * as Crypto from 'expo-crypto';
import { ml_dsa44 } from '@noble/post-quantum/ml-dsa.js';

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
    const signature = ml_dsa44.sign(dataBytes, privateKey);

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
    return ml_dsa44.verify(signature, dataBytes, publicKey);
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

  // Base64 lookup table — avoids dependency on btoa/atob which may not be
  // available or reliable across all React Native engines.
  private static readonly BASE64_CHARS =
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

  private static uint8ArrayToBase64(bytes: Uint8Array): string {
    let result = '';
    const len = bytes.length;
    for (let i = 0; i < len; i += 3) {
      const b0 = bytes[i];
      const b1 = i + 1 < len ? bytes[i + 1] : 0;
      const b2 = i + 2 < len ? bytes[i + 2] : 0;
      result += this.BASE64_CHARS[b0 >> 2];
      result += this.BASE64_CHARS[((b0 & 3) << 4) | (b1 >> 4)];
      result += i + 1 < len ? this.BASE64_CHARS[((b1 & 15) << 2) | (b2 >> 6)] : '=';
      result += i + 2 < len ? this.BASE64_CHARS[b2 & 63] : '=';
    }
    return result;
  }

  private static base64ToUint8Array(base64: string): Uint8Array {
    const cleaned = base64.replace(/=+$/, '');
    const len = cleaned.length;
    const bytes = new Uint8Array(Math.floor((len * 3) / 4));
    let j = 0;
    for (let i = 0; i < len; i += 4) {
      const a = this.BASE64_CHARS.indexOf(cleaned[i]);
      const b = i + 1 < len ? this.BASE64_CHARS.indexOf(cleaned[i + 1]) : 0;
      const c = i + 2 < len ? this.BASE64_CHARS.indexOf(cleaned[i + 2]) : 0;
      const d = i + 3 < len ? this.BASE64_CHARS.indexOf(cleaned[i + 3]) : 0;
      bytes[j++] = (a << 2) | (b >> 4);
      if (i + 2 < len) bytes[j++] = ((b & 15) << 4) | (c >> 2);
      if (i + 3 < len) bytes[j++] = ((c & 3) << 6) | d;
    }
    return bytes;
  }
}

export default KeyManager;
