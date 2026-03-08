export interface User {
  user_id: string;
  username: string;
  public_key: string;
  created_at?: string;
}

export interface Transaction {
  id: string;
  sender: string;
  recipient: string;
  amount: number;
  description: string;
  timestamp: string;
  status: 'pending' | 'completed' | 'failed';
}

export interface Account {
  type: 'checking' | 'savings';
  balance: number;
  account_number: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: Date;
  agent_name?: string;
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export interface A2AMessage {
  role: 'user' | 'agent';
  parts: A2AMessagePart[];
  contextId?: string;
}

export interface A2AMessagePart {
  kind: 'text' | 'image' | 'file';
  text?: string;
  image_url?: { url: string };
  file?: { url: string; mime_type: string };
}
