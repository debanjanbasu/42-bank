import { API_URL } from '@/config/env';
import { User } from '@/types';

export interface RegisterRequest {
	username: string;
	public_key: string;
	device_id: string;
	device_name?: string;
}

export interface RegisterResponse {
	user_id: string;
	username: string;
	token: string;
	refresh_token: string;
	expires_at: string;
	public_key: string;
}

export interface LoginResponse {
	user_id: string;
	username: string;
	token: string;
	refresh_token: string;
	expires_at: string;
}

export class AuthService {
  private static async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_URL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

	static async register(data: RegisterRequest): Promise<RegisterResponse> {
		console.log('AuthService.register called with:', { ...data, public_key: data.public_key.substring(0, 20) + '...' });
		console.log('API_URL:', API_URL);
		console.log('Full URL:', `${API_URL}/api/auth/register`);
		return this.request<RegisterResponse>('/api/auth/register', {
			method: 'POST',
			body: JSON.stringify(data),
		});
	}

  static async login(
    username: string,
    device_id: string
  ): Promise<LoginResponse> {
    return this.request<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, device_id }),
    });
  }

  static async refreshToken(refreshToken: string): Promise<string> {
    const response = await this.request<{ token: string; expires_at: string }>(
      '/api/auth/refresh',
      {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      }
    );
    return response.token;
  }

  static async verifyToken(token: string): Promise<boolean> {
    try {
      const response = await this.request<{ user_id: string }>('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      return !!response.user_id;
    } catch {
      return false;
    }
  }

  static async getUserInfo(token: string): Promise<User> {
    return this.request<User>('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    });
  }

	static async logout(token: string): Promise<void> {
		await this.request('/api/auth/logout', {
			method: 'POST',
			headers: { Authorization: `Bearer ${token}` },
		});
	}

	static async devLogin(username: string): Promise<LoginResponse & { device_id: string }> {
		return this.request<LoginResponse & { device_id: string }>('/api/auth/dev-login', {
			method: 'POST',
			body: JSON.stringify({ username }),
		});
	}
}

export default AuthService;
