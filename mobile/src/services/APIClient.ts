import { StorageService } from '@/services/StorageService';
import { API_URL } from '@/config/env';

export class APIError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = 'APIError';
  }
}

const REQUEST_TIMEOUT_MS = 15_000;

export class APIClient {
  static async request<T = unknown>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const token = await StorageService.getToken();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...options.headers,
        },
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new APIError(
          body?.detail ?? `HTTP ${response.status}`,
          response.status,
          body,
        );
      }

      return response.json() as Promise<T>;
    } catch (err) {
      if (err instanceof APIError) throw err;
      if (err instanceof Error && err.name === 'AbortError') {
        throw new APIError('Request timed out', 408);
      }
      throw new APIError(
        err instanceof Error ? err.message : 'Network error',
        0,
      );
    } finally {
      clearTimeout(timeoutId);
    }
  }

  static get<T = unknown>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  static post<T = unknown>(endpoint: string, body: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }
}
