import AsyncStorage from '@react-native-async-storage/async-storage';
import { Account, Transaction } from '@/types';

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

const KEYS = {
  ACCOUNTS: 'cache:accounts',
  TRANSACTIONS: 'cache:transactions',
};

export class CacheService {
  static async setAccounts(accounts: Account[]): Promise<void> {
    const entry: CacheEntry<Account[]> = { data: accounts, timestamp: Date.now() };
    await AsyncStorage.setItem(KEYS.ACCOUNTS, JSON.stringify(entry));
  }

  static async getAccounts(): Promise<Account[] | null> {
    const raw = await AsyncStorage.getItem(KEYS.ACCOUNTS);
    if (!raw) return null;
    const entry: CacheEntry<Account[]> = JSON.parse(raw);
    if (Date.now() - entry.timestamp > CACHE_TTL_MS) return null; // stale
    return entry.data;
  }

  static async setTransactions(transactions: Transaction[]): Promise<void> {
    const entry: CacheEntry<Transaction[]> = { data: transactions, timestamp: Date.now() };
    await AsyncStorage.setItem(KEYS.TRANSACTIONS, JSON.stringify(entry));
  }

  static async getTransactions(): Promise<Transaction[] | null> {
    const raw = await AsyncStorage.getItem(KEYS.TRANSACTIONS);
    if (!raw) return null;
    const entry: CacheEntry<Transaction[]> = JSON.parse(raw);
    if (Date.now() - entry.timestamp > CACHE_TTL_MS) return null;
    return entry.data;
  }

  static async clearAll(): Promise<void> {
    await AsyncStorage.multiRemove([KEYS.ACCOUNTS, KEYS.TRANSACTIONS]);
  }
}
