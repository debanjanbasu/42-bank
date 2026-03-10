import React from 'react';
import { renderHook, act } from '@testing-library/react-hooks';
import { AuthProvider, useAuth } from '../AuthContext';
import { StorageService } from '@/services/StorageService';
import { AuthService } from '@/services/AuthService';
import { KeyManager } from '@/services/KeyManager';

jest.mock('@/services/StorageService');
jest.mock('@/services/AuthService');
jest.mock('@/services/KeyManager');

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (StorageService.getUser as jest.Mock).mockResolvedValue(null);
    (StorageService.getToken as jest.Mock).mockResolvedValue(null);
    (StorageService.getRefreshToken as jest.Mock).mockResolvedValue(null);
    (StorageService.isTokenExpired as jest.Mock).mockResolvedValue(false);
  });

  it('starts unauthenticated when no stored session', async () => {
    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    await waitForNextUpdate();
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
  });

  it('restores session from storage when token is valid', async () => {
    const mockUser = { user_id: 'abc', username: 'alice' };
    (StorageService.getUser as jest.Mock).mockResolvedValue(mockUser);
    (StorageService.getToken as jest.Mock).mockResolvedValue('valid-token');
    (AuthService.verifyToken as jest.Mock).mockResolvedValue(true);

    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    await waitForNextUpdate();

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.username).toBe('alice');
  });

  it('clears auth when stored token is invalid and no refresh token', async () => {
    const mockUser = { user_id: 'abc', username: 'alice' };
    (StorageService.getUser as jest.Mock).mockResolvedValue(mockUser);
    (StorageService.getToken as jest.Mock).mockResolvedValue('expired-token');
    (AuthService.verifyToken as jest.Mock).mockResolvedValue(false);
    (StorageService.getRefreshToken as jest.Mock).mockResolvedValue(null);
    (StorageService.clearAuth as jest.Mock).mockResolvedValue(undefined);

    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    await waitForNextUpdate();

    expect(result.current.isAuthenticated).toBe(false);
  });

  it('refreshes token when current token is expired', async () => {
    const mockUser = { user_id: 'abc', username: 'alice' };
    (StorageService.getUser as jest.Mock).mockResolvedValue(mockUser);
    (StorageService.getToken as jest.Mock).mockResolvedValue('old-token');
    (StorageService.isTokenExpired as jest.Mock).mockResolvedValue(true);
    (StorageService.getRefreshToken as jest.Mock).mockResolvedValue('refresh-token');
    (AuthService.refreshToken as jest.Mock).mockResolvedValue('new-access-token');
    (AuthService.verifyToken as jest.Mock).mockResolvedValue(true);
    (StorageService.setToken as jest.Mock).mockResolvedValue(undefined);

    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    await waitForNextUpdate();

    expect(AuthService.refreshToken).toHaveBeenCalledWith('refresh-token');
    expect(StorageService.setToken).toHaveBeenCalledWith('new-access-token');
  });

  it('calls clearAuth on logout', async () => {
    const mockUser = { user_id: 'abc', username: 'alice' };
    (StorageService.getUser as jest.Mock).mockResolvedValue(mockUser);
    (StorageService.getToken as jest.Mock).mockResolvedValue('valid-token');
    (AuthService.verifyToken as jest.Mock).mockResolvedValue(true);
    (KeyManager.deleteKeys as jest.Mock).mockResolvedValue(undefined);
    (StorageService.clearAuth as jest.Mock).mockResolvedValue(undefined);

    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    await waitForNextUpdate();

    await act(async () => {
      await result.current.logout();
    });

    expect(StorageService.clearAuth).toHaveBeenCalled();
    expect(result.current.isAuthenticated).toBe(false);
  });
});
