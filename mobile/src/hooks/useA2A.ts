import { useCallback } from 'react';
import { A2AClient } from '@/services/A2AClient';
import { useAuth } from '@/contexts/AuthContext';
import { A2A_URL } from '@/config/env';

export type StreamCallback = (chunk: string, done: boolean) => void;

export function useA2A() {
  const { user } = useAuth();

  const sendMessage = useCallback(
    async (message: string, onChunk: StreamCallback): Promise<void> => {
      const token = await getStoredToken();
      if (!token) {
        throw new Error('Not authenticated');
      }
      const client = new A2AClient(A2A_URL, token);
      await client.sendMessageStream('triage', message, onChunk);
    },
    [user]
  );

  const sendDirectToAgent = useCallback(
    async (
      agent: 'inquiry' | 'transaction' | 'advisor' | 'manager',
      message: string,
      onChunk: StreamCallback
    ): Promise<void> => {
      const token = await getStoredToken();
      if (!token) {
        throw new Error('Not authenticated');
      }
      const client = new A2AClient(A2A_URL, token);
      await client.sendMessageStream(agent, message, onChunk);
    },
    [user]
  );

  return {
    sendMessage,
    sendDirectToAgent,
    isReady: !!user,
  };
}

async function getStoredToken(): Promise<string | null> {
  const { StorageService } = await import('@/services/StorageService');
  return StorageService.getToken();
}
