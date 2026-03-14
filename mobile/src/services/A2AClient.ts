/**
 * 42-Bank A2A Client for Mobile Apps
 *
 * This client provides a TypeScript interface for communicating with
 * the 42-Bank A2A server from React Native / Flutter mobile apps.
 *
 * Features:
 * - A2A protocol communication (HTTP + SSE streaming)
 * - JWT authentication
 * - Transaction signing
 * - Native AI integration hooks
 *
 * Usage:
 * ```typescript
 * import { A2AClient } from './services/A2AClient';
 *
 * const client = new A2AClient('https://42bank.azurewebsites.net', jwtToken);
 * const response = await client.sendMessage('triage', 'What is my balance?');
 * ```
 */

import { EventSourcePolyfill } from 'event-source-polyfill';
import { A2AMessagePart } from '@/types';

// ============ Types ============

export interface A2AMessage {
  role: 'user' | 'agent';
  parts: A2AMessagePart[];
  contextId?: string;
}

export type { A2AMessagePart };

export interface A2AResponse {
  result: {
    kind: 'message';
    role: 'agent';
    parts: A2AMessagePart[];
    messageId: string;
    contextId: string;
  };
}

export interface A2AStreamChunk {
  result: {
    kind: 'message';
    role: 'agent';
    parts: A2AMessagePart[];
    messageId: string;
    contextId: string;
  };
}

export interface A2AAgentCard {
  name: string;
  description: string;
  version: string;
  url: string;
  capabilities: {
    streaming: boolean;
    pushNotifications: boolean;
  };
  skills: Array<{
    id: string;
    name: string;
    description: string;
    tags: string[];
  }>;
}

export interface A2AClientConfig {
  endpoint: string;
  jwtToken: string;
  timeout?: number;
  retries?: number;
}

export type StreamCallback = (chunk: string, done: boolean) => void;
export type ErrorCallback = (error: Error) => void;

// ============ A2A Client ============

export class A2AClient {
  private endpoint: string;
  private jwtToken: string;
  private timeout: number;
  private retries: number;

  constructor(config: A2AClientConfig);
  constructor(endpoint: string, jwtToken: string);
  constructor(endpointOrConfig: string | A2AClientConfig, jwtToken?: string) {
    if (typeof endpointOrConfig === 'string') {
      this.endpoint = endpointOrConfig;
      this.jwtToken = jwtToken || '';
      this.timeout = 30000;
      this.retries = 3;
    } else {
      this.endpoint = endpointOrConfig.endpoint;
      this.jwtToken = endpointOrConfig.jwtToken;
      this.timeout = endpointOrConfig.timeout || 30000;
      this.retries = endpointOrConfig.retries || 3;
    }
  }

  /**
   * Set JWT token (called after login or refresh)
   */
  setToken(token: string): void {
    this.jwtToken = token;
  }

  /**
   * Get authorization headers
   */
  private getHeaders(): Record<string, string> {
    return {
      'Authorization': `Bearer ${this.jwtToken}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  /**
   * Send a message to an A2A agent (non-streaming)
   */
  async sendMessage(
    agent: string,
    message: string,
    contextId?: string
  ): Promise<A2AResponse> {
    const url = `${this.endpoint}/a2a/${agent}/v1/message`;

    const body = {
      message: {
        role: 'user',
        parts: [{ kind: 'text', text: message }],
        contextId: contextId || this.generateContextId(),
      },
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new A2AError(
        error.message || `HTTP ${response.status}`,
        response.status
      );
    }

    return response.json();
  }

	/**
	 * Send a message - using non-streaming endpoint for reliability
	 */
	async sendMessageStream(
		agent: string,
		message: string,
		onChunk: StreamCallback,
		onError?: ErrorCallback,
		contextId?: string
	): Promise<void> {
		const url = `${this.endpoint}/a2a/${agent}/v1/message`;

		const body = {
			message: {
				role: 'user',
				parts: [{ kind: 'text', text: message }],
				contextId: contextId || this.generateContextId(),
			},
		};

		try {
			const response = await fetch(url, {
				method: 'POST',
				headers: this.getHeaders(),
				body: JSON.stringify(body),
			});

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(`HTTP ${response.status}: ${errorText}`);
			}

			const data = await response.json();
			const text = this.extractTextFromResponse(data);
			if (text) {
				onChunk(text, false);
			}
			onChunk('', true); // done
		} catch (error) {
			onError?.(error as Error);
			throw error;
		}
	}

  /**
   * Get agent card (discovery)
   */
  async getAgentCard(agent: string): Promise<A2AAgentCard> {
    const url = `${this.endpoint}/a2a/${agent}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new A2AError(`Failed to get agent card: ${response.status}`, response.status);
    }

    return response.json();
  }

  /**
   * List all available agents
   */
  async listAgents(): Promise<Array<{ name: string; path: string; description: string }>> {
    const url = `${this.endpoint}/a2a`;

    const response = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new A2AError(`Failed to list agents: ${response.status}`, response.status);
    }

    const data = await response.json();
    return data.agents;
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; protocol: string; agents: string[] }> {
    const url = `${this.endpoint}/health`;

    const response = await fetch(url, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new A2AError('Health check failed', response.status);
    }

    return response.json();
  }

  /**
   * Extract text from A2A response
   */
  private extractTextFromResponse(response: { result?: { parts?: A2AMessagePart[] } }): string {
    return (response.result?.parts ?? [])
      .filter((p): p is Extract<A2AMessagePart, { kind: 'text' }> => p.kind === 'text')
      .map(p => p.text)
      .join('');
  }

  /**
   * Generate unique context ID
   */
  private generateContextId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

// ============ Error Class ============

export class A2AError extends Error {
  constructor(message: string, public statusCode: number) {
    super(message);
    this.name = 'A2AError';
  }
}

// ============ Native AI Integration ============

/**
 * Interface for native AI services (Apple Intelligence / Gemini Nano)
 */
export interface NativeAIService {
  /**
   * Check if native AI is available on this device
   */
  isAvailable(): Promise<boolean>;

  /**
   * Classify intent of user query
   */
  classifyIntent(query: string): Promise<'inquiry' | 'transaction' | 'advisor' | 'general'>;

  /**
   * Generate response locally (for simple queries)
   */
  generateResponse(prompt: string): Promise<string>;
}

// Platform-specific native AI will be implemented in native modules
// See: src/native/ios/AppleIntelligenceBridge.swift
// See: src/native/android/GeminiNanoBridge.kt

// ============ Transaction Signing ============

/**
 * Transaction signing interface for ML-DSA-44
 */
export interface TransactionSigner {
  /**
   * Sign transaction data with private key
   */
  sign(data: string): Promise<string>;

  /**
   * Verify signature with public key
   */
  verify(publicKey: string, data: string, signature: string): Promise<boolean>;

  /**
   * Get public key for this user
   */
  getPublicKey(): Promise<string>;
}

// ============ Convenience Functions ============

/**
 * Quick function to send a banking query
 */
export async function sendBankingQuery(
  endpoint: string,
  token: string,
  query: string,
  onStream?: StreamCallback
): Promise<string> {
  const client = new A2AClient(endpoint, token);

  if (onStream) {
    let result = '';
    await client.sendMessageStream('triage', query, (chunk, done) => {
      result += chunk;
      onStream(chunk, done);
    });
    return result;
  } else {
    const response = await client.sendMessage('triage', query);
    return response.result.parts
      .filter((p): p is Extract<A2AMessagePart, { kind: 'text' }> => p.kind === 'text')
      .map(p => p.text)
      .join('');
  }
}

export default A2AClient;
