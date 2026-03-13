import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from 'react';
import { AppState, AppStateStatus } from 'react-native';
import { User } from '@/types';
import { AuthService } from '@/services/AuthService';
import { CacheService } from '@/services/CacheService';
import { NotificationService } from '@/services/NotificationService';
import { StorageService } from '@/services/StorageService';
import { KeyManager } from '@/services/KeyManager';

interface AuthContextType {
	user: User | null;
	isLoading: boolean;
	isAuthenticated: boolean;
	login: (username: string) => Promise<void>;
	devLogin: (username: string) => Promise<void>;
	register: (username: string) => Promise<void>;
	logout: () => Promise<void>;
	refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const SESSION_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const lastActiveRef = React.useRef<number>(Date.now());
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clears session state only. Cryptographic keys are intentionally preserved
  // because they are protected by biometric auth (Keychain/Keystore) and are
  // needed for transaction signing after re-login. Only explicit logout (which
  // calls KeyManager.deleteKeys()) performs full key cleanup.
  const clearAuth = useCallback(async () => {
    await StorageService.clearAuth();
    setUser(null);
  }, []);

  useEffect(() => {
    checkExistingSession();
    async function checkExistingSession() {
      try {
        const storedUser = await StorageService.getUser();
        const token = await StorageService.getToken();
        if (storedUser && token) {
          const expired = await StorageService.isTokenExpired();
          if (expired) {
            const refreshToken = await StorageService.getRefreshToken();
            if (refreshToken) {
              try {
                const newToken = await AuthService.refreshToken(refreshToken);
                const isNewTokenValid = await AuthService.verifyToken(newToken);
                if (!isNewTokenValid) {
                  await clearAuth();
                  return;
                }
                await StorageService.setToken(newToken);
                setUser(storedUser);
              } catch {
                await clearAuth();
                return;
              }
            } else {
              await clearAuth();
              return;
            }
          } else {
            const isValid = await AuthService.verifyToken(token);
            if (isValid) {
              setUser(storedUser);
            } else {
              const refreshToken = await StorageService.getRefreshToken();
              if (refreshToken) {
                try {
                  const newToken = await AuthService.refreshToken(refreshToken);
                  const isNewTokenValid = await AuthService.verifyToken(newToken);
                  if (!isNewTokenValid) {
                    await clearAuth();
                    return;
                  }
                  await StorageService.setToken(newToken);
                  setUser(storedUser);
                } catch {
                  await clearAuth();
                }
              } else {
                await clearAuth();
              }
            }
          }
        }
      } catch (error) {
        console.error('Session check failed:', error);
        await clearAuth();
      } finally {
        setIsLoading(false);
      }
    }
  }, [clearAuth]);

	const resetSessionTimer = useCallback(() => {
		lastActiveRef.current = Date.now();
		if (timeoutRef.current) clearTimeout(timeoutRef.current);
		if (user) {
			timeoutRef.current = setTimeout(() => {
				clearAuth();
			}, SESSION_TIMEOUT_MS);
		}
	}, [user, clearAuth]);

	useEffect(() => {
		const subscription = AppState.addEventListener('change', (state: AppStateStatus) => {
			if (state === 'active') {
				const elapsed = Date.now() - lastActiveRef.current;
				if (elapsed > SESSION_TIMEOUT_MS && user) {
					clearAuth();
				} else {
					resetSessionTimer();
				}
			} else if (state === 'background') {
				lastActiveRef.current = Date.now();
				if (timeoutRef.current) clearTimeout(timeoutRef.current);
			}
		});
		return () => {
			subscription.remove();
			if (timeoutRef.current) clearTimeout(timeoutRef.current);
		};
	}, [user, resetSessionTimer, clearAuth]);

  const login = useCallback(async (username: string) => {
    setIsLoading(true);
    try {
      const deviceId = await StorageService.getOrCreateDeviceId();
      const response = await AuthService.login(username, deviceId);
      await StorageService.setUser(response.user);
      await StorageService.setToken(response.token);
      await StorageService.setTokenExpiry(response.expires_at);
      await StorageService.setRefreshToken(response.refresh_token);
      setUser(response.user);
      try {
        const pushToken = await NotificationService.registerForPushNotifications();
        if (pushToken) {
          await NotificationService.registerTokenWithServer(pushToken);
        }
      } catch (e) {
        // Non-fatal — app works without push notifications
        console.warn('Push notification setup failed:', e);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

	const register = useCallback(async (username: string) => {
		setIsLoading(true);
		let generatedKeys = false;
		try {
			console.log('Generating key pair...');
			const keyPair = await KeyManager.generateKeyPair();
			console.log('Key pair generated, public key:', keyPair.publicKey.substring(0, 20) + '...');
			generatedKeys = true;
			const deviceId = await StorageService.getOrCreateDeviceId();
			console.log('Device ID:', deviceId);
			const deviceName = await StorageService.getDeviceName();
			console.log('Device name:', deviceName);
			console.log('Calling AuthService.register...');
			const response = await AuthService.register({
				username,
				public_key: keyPair.publicKey,
				device_id: deviceId,
				device_name: deviceName,
			});
		console.log('Register response:', response);
		const user: User = {
			user_id: response.user_id,
			username: response.username,
			public_key: response.public_key,
		};
		await StorageService.setUser(user);
		await StorageService.setToken(response.token);
		await StorageService.setTokenExpiry(response.expires_at);
		await StorageService.setRefreshToken(response.refresh_token);
		setUser(user);
			try {
				const pushToken = await NotificationService.registerForPushNotifications();
				if (pushToken) {
					await NotificationService.registerTokenWithServer(pushToken);
				}
			} catch (e) {
				// Non-fatal — app works without push notifications
				console.warn('Push notification setup failed:', e);
			}
		} catch (error) {
			console.error('Registration error:', error);
			// Roll back generated keys when registration fails server-side.
			if (generatedKeys) {
				await KeyManager.deleteKeys();
			}
			throw error;
		} finally {
			setIsLoading(false);
		}
	}, []);

	const devLogin = useCallback(async (username: string) => {
		setIsLoading(true);
		try {
			const response = await AuthService.devLogin(username);
			const user: User = {
				user_id: response.user_id,
				username: response.username,
				public_key: '',
			};
			await StorageService.setUser(user);
			await StorageService.setToken(response.token);
			await StorageService.setTokenExpiry(response.expires_at);
			await StorageService.setRefreshToken(response.refresh_token);
			await StorageService.getOrCreateDeviceId();
			setUser(user);
		} catch (error) {
			throw error;
		} finally {
			setIsLoading(false);
		}
	}, []);

	const logout = useCallback(async () => {
		setIsLoading(true);
		try {
			await KeyManager.deleteKeys();
			await CacheService.clearAll();
			await clearAuth();
		} finally {
			setIsLoading(false);
		}
	}, [clearAuth]);

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
	}, [clearAuth]);

	return (
		<AuthContext.Provider
			value={{
				user,
				isLoading,
				isAuthenticated: !!user,
				login,
				devLogin,
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
