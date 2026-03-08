import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from 'react';
import { User } from '@/types';
import { AuthService } from '@/services/AuthService';
import { StorageService } from '@/services/StorageService';
import { KeyManager } from '@/services/KeyManager';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string) => Promise<void>;
  register: (username: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkExistingSession();
  }, []);

  const checkExistingSession = async () => {
    try {
      const storedUser = await StorageService.getUser();
      const token = await StorageService.getToken();
      if (storedUser && token) {
        const isValid = await AuthService.verifyToken(token);
        if (isValid) {
          setUser(storedUser);
        } else {
          const refreshToken = await StorageService.getRefreshToken();
          if (refreshToken) {
            const newToken = await AuthService.refreshToken(refreshToken);
            await StorageService.setToken(newToken);
            setUser(storedUser);
          } else {
            await clearAuth();
          }
        }
      }
    } catch (error) {
      console.error('Session check failed:', error);
      await clearAuth();
    } finally {
      setIsLoading(false);
    }
  };

  const clearAuth = async () => {
    await StorageService.clearAuth();
    setUser(null);
  };

  const login = useCallback(async (username: string) => {
    setIsLoading(true);
    try {
      const deviceId = await StorageService.getOrCreateDeviceId();
      const response = await AuthService.login(username, deviceId);
      await StorageService.setUser(response.user);
      await StorageService.setToken(response.token);
      await StorageService.setRefreshToken(response.refresh_token);
      setUser(response.user);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (username: string) => {
    setIsLoading(true);
    try {
      const keyPair = await KeyManager.generateKeyPair();
      const deviceId = await StorageService.getOrCreateDeviceId();
      const response = await AuthService.register({
        username,
        public_key: keyPair.publicKey,
        device_id: deviceId,
        device_name: await StorageService.getDeviceName(),
      });
      await StorageService.setUser(response.user);
      await StorageService.setToken(response.token);
      await StorageService.setRefreshToken(response.refresh_token);
      setUser(response.user);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await KeyManager.deleteKeys();
      await clearAuth();
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshToken = useCallback(async () => {
    try {
      const currentRefreshToken = await StorageService.getRefreshToken();
      if (!currentRefreshToken) {
        throw new Error('No refresh token');
      }
      const newToken = await AuthService.refreshToken(currentRefreshToken);
      await StorageService.setToken(newToken);
    } catch (error) {
      await clearAuth();
      throw error;
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
