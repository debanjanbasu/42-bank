import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Device from 'expo-device';
import { User } from '@/types';

const SECURE_KEYS = {
  TOKEN: 'auth_token',
  REFRESH_TOKEN: 'refresh_token',
  USER: 'user_data',
  DEVICE_ID: 'device_id',
};

const STORAGE_KEYS = {
  DEVICE_NAME: 'device_name',
};

export class StorageService {
  static async setToken(token: string): Promise<void> {
    await SecureStore.setItemAsync(SECURE_KEYS.TOKEN, token);
  }

  static async getToken(): Promise<string | null> {
    return SecureStore.getItemAsync(SECURE_KEYS.TOKEN);
  }

  static async setRefreshToken(token: string): Promise<void> {
    await SecureStore.setItemAsync(SECURE_KEYS.REFRESH_TOKEN, token);
  }

  static async getRefreshToken(): Promise<string | null> {
    return SecureStore.getItemAsync(SECURE_KEYS.REFRESH_TOKEN);
  }

  static async setUser(user: User): Promise<void> {
    await SecureStore.setItemAsync(SECURE_KEYS.USER, JSON.stringify(user));
  }

  static async getUser(): Promise<User | null> {
    const data = await SecureStore.getItemAsync(SECURE_KEYS.USER);
    return data ? JSON.parse(data) : null;
  }

  static async getOrCreateDeviceId(): Promise<string> {
    let deviceId = await SecureStore.getItemAsync(SECURE_KEYS.DEVICE_ID);
    if (!deviceId) {
      const randomBytes = await Crypto.getRandomBytesAsync(16);
      deviceId = Array.from(randomBytes)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
      await SecureStore.setItemAsync(SECURE_KEYS.DEVICE_ID, deviceId);
    }
    return deviceId;
  }

  static async getDeviceName(): Promise<string> {
    try {
      const storedName = await AsyncStorage.getItem(STORAGE_KEYS.DEVICE_NAME);
      if (storedName) return storedName;

      const modelName = Device.modelName || Device.modelId || 'Unknown';
      const osName = Device.osName || 'Device';
      const defaultName = `${modelName} (${osName})`;
      await AsyncStorage.setItem(STORAGE_KEYS.DEVICE_NAME, defaultName);
      return defaultName;
    } catch {
      return 'Mobile Device';
    }
  }

  static async clearAuth(): Promise<void> {
    await SecureStore.deleteItemAsync(SECURE_KEYS.TOKEN);
    await SecureStore.deleteItemAsync(SECURE_KEYS.REFRESH_TOKEN);
    await SecureStore.deleteItemAsync(SECURE_KEYS.USER);
    await AsyncStorage.removeItem('token_expires_at');
  }

  static async setTokenExpiry(expiresAt: string): Promise<void> {
    await AsyncStorage.setItem('token_expires_at', expiresAt);
  }

  static async getTokenExpiry(): Promise<string | null> {
    return AsyncStorage.getItem('token_expires_at');
  }

  static async isTokenExpired(): Promise<boolean> {
    const expiresAt = await this.getTokenExpiry();
    if (!expiresAt) return false; // Unknown — let the server decide
    return Date.now() > new Date(expiresAt).getTime() - 60_000; // 1 min buffer
  }

  static async clearAll(): Promise<void> {
    await this.clearAuth();
    await SecureStore.deleteItemAsync(SECURE_KEYS.DEVICE_ID);
    await AsyncStorage.removeItem(STORAGE_KEYS.DEVICE_NAME);
  }
}

export default StorageService;
