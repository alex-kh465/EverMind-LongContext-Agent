/**
 * API Client for LongContext Agent
 * Handles all communication with the FastAPI backend
 */

import axios, { type AxiosInstance, type AxiosResponse } from 'axios';

// Types (shared with backend)
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface Memory {
  id: string;
  session_id: string;
  memory_type: 'conversation' | 'summary' | 'tool_output' | 'context';
  content: string;
  embedding?: number[];
  relevance_score: number;
  compression_ratio: number;
  token_count: number;
  timestamp: string;
  metadata: Record<string, any>;
}

export interface ToolCall {
  id: string;
  tool_type: 'calculator' | 'web_search' | 'wikipedia';
  parameters: Record<string, any>;
  result?: any;
  execution_time_ms: number;
  timestamp: string;
}

export interface ConversationSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  message_count?: number;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  use_tools?: boolean;
  max_context_tokens?: number;
}

export interface ChatResponse {
  message: ChatMessage;
  session_id: string;
  retrieved_memories: Memory[];
  tool_calls: ToolCall[];
  metrics: Record<string, any>;
}

export interface MemoryQuery {
  query: string;
  session_id?: string;
  memory_types?: string[];
  limit?: number;
  relevance_threshold?: number;
}

export interface MemoryQueryResponse {
  memories: Memory[];
  total_count: number;
  query_time_ms: number;
}

export interface PerformanceMetrics {
  context_retention_accuracy: number;
  compression_ratio: number;
  retrieval_precision: number;
  response_latency_ms: number;
  memory_growth_rate: number;
  total_memories: number;
  active_sessions: number;
  vector_db_size_mb: number;
}

export interface SystemHealth {
  status: string;
  database_connected: boolean;
  openai_api_available: boolean;
  memory_usage_mb: number;
  cpu_usage_percent: number;
  uptime_seconds: number;
}

class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000, // 30 seconds
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('❌ Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        console.log(`✅ API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        console.error('❌ Response Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Chat endpoints
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/chat', request);
    return response.data;
  }

  // Memory endpoints
  async searchMemories(query: MemoryQuery): Promise<MemoryQueryResponse> {
    const response = await this.client.post<MemoryQueryResponse>('/memory/search', query);
    return response.data;
  }

  async listSessions(): Promise<{ sessions: ConversationSession[] }> {
    const response = await this.client.get<{ sessions: ConversationSession[] }>('/memory/sessions');
    return response.data;
  }

  async createSession(request: { title?: string; metadata?: any }): Promise<ConversationSession> {
    const response = await this.client.post<ConversationSession>('/memory/sessions', request);
    return response.data;
  }

  async getSession(sessionId: string): Promise<ConversationSession> {
    const response = await this.client.get<ConversationSession>(`/memory/sessions/${sessionId}`);
    return response.data;
  }

  async deleteSession(sessionId: string): Promise<{ message: string }> {
    const response = await this.client.delete<{ message: string }>(`/memory/sessions/${sessionId}`);
    return response.data;
  }

  async updateSession(sessionId: string, updates: { title?: string; metadata?: any }): Promise<ConversationSession> {
    const response = await this.client.patch<ConversationSession>(`/memory/sessions/${sessionId}`, updates);
    return response.data;
  }

  // System endpoints
  async getHealth(): Promise<SystemHealth> {
    const response = await this.client.get<SystemHealth>('/health');
    return response.data;
  }

  async getMetrics(): Promise<PerformanceMetrics> {
    const response = await this.client.get<PerformanceMetrics>('/metrics');
    return response.data;
  }

  async getConfig(): Promise<Record<string, any>> {
    const response = await this.client.get<Record<string, any>>('/config');
    return response.data;
  }

  async resetSystem(): Promise<{ success: boolean; message: string; timestamp: number }> {
    const response = await this.client.post<{ success: boolean; message: string; timestamp: number }>('/system/reset');
    return response.data;
  }

  // Utility methods
  async ping(): Promise<boolean> {
    try {
      const response = await this.client.get('/');
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }

  getBaseURL(): string {
    return this.baseURL;
  }

  // Error handling utility
  handleApiError(error: any): string {
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const message = error.response.data?.detail || error.response.data?.message || 'Unknown error';
      
      switch (status) {
        case 400:
          return `Bad Request: ${message}`;
        case 401:
          return 'Unauthorized access';
        case 403:
          return 'Forbidden access';
        case 404:
          return 'Resource not found';
        case 429:
          return 'Rate limit exceeded. Please try again later.';
        case 500:
          return 'Internal server error. Please try again.';
        case 503:
          return 'Service temporarily unavailable';
        default:
          return `Server error (${status}): ${message}`;
      }
    } else if (error.request) {
      // Request was made but no response received
      return 'Unable to connect to server. Please check your connection.';
    } else {
      // Something else happened
      return error.message || 'An unexpected error occurred';
    }
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// Export default
export default apiClient;
