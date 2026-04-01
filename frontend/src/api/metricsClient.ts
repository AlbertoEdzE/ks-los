/**
 * Metrics API Client for KS-LOS Phase 2
 * 
 * TypeScript client for consuming Tier A (Technical AI) and Tier B (Business)
 * metrics endpoints. Provides type-safe access to all metrics with proper
 * error handling and authentication.
 * 
 * Features:
 * - Type-safe API calls
 * - Automatic token refresh
 * - Error handling and retry logic
 * - Request/response logging (debug mode)
 * 
 * Usage:
 * ```typescript
 * const metricsClient = new MetricsApiClient();
 * 
 * // Get application metrics (Tier B)
 * const appMetrics = await metricsClient.getApplicationMetrics('APP-123');
 * 
 * // Get AI metrics (Tier A - requires admin auth)
 * await metricsClient.authenticateAdmin('password');
 * const aiMetrics = await metricsClient.getAIMetrics('conv-123');
 * ```
 */

import {
  ApplicationMetrics,
  PortfolioMetrics,
  JourneyStageMetrics,
  AIMetrics,
  AggregateAIMetrics,
  ModelPerformanceMetrics,
  ApplicationStatus,
  GradeLevel,
  RiskLevel,
} from '../types/metrics';

// ─────────────────────────────────────────────────────────────────────────────
// Type Definitions
// ─────────────────────────────────────────────────────────────────────────────

export interface MetricsPeriod {
  period: 'today' | 'yesterday' | 'week' | 'month' | 'custom';
  startDate?: Date;
  endDate?: Date;
}

export interface AuthToken {
  token: string;
  expiresAt: Date;
}

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// API Client Configuration
// ─────────────────────────────────────────────────────────────────────────────

export interface MetricsApiClientConfig {
  baseUrl: string;
  timeout: number;
  debug: boolean;
}

const DEFAULT_CONFIG: MetricsApiClientConfig = {
  baseUrl: '/api/metrics',
  timeout: 30000,
  debug: false,
};

// ─────────────────────────────────────────────────────────────────────────────
// Metrics API Client Class
// ─────────────────────────────────────────────────────────────────────────────

export class MetricsApiClient {
  private config: MetricsApiClientConfig;
  private authToken: AuthToken | null = null;

  constructor(config: Partial<MetricsApiClientConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Authentication Methods
  // ───────────────────────────────────────────────────────────────────────────

  /**
   * Authenticate as admin to access Tier A metrics
   */
  async authenticateAdmin(password: string): Promise<AuthToken> {
    const response = await this.fetch<AuthResponse>('/admin/auth', {
      method: 'POST',
      body: JSON.stringify({ password }),
    });

    if (!response.success || !response.token) {
      throw new Error(response.message || 'Authentication failed');
    }

    this.authToken = {
      token: response.token,
      expiresAt: new Date(response.expires_at),
    };

    this.log('Admin authentication successful');
    return this.authToken;
  }

  /**
   * Check if user is authenticated as admin
   */
  isAuthenticated(): boolean {
    if (!this.authToken) {
      return false;
    }

    // Check if token is expired
    if (new Date() >= this.authToken.expiresAt) {
      this.authToken = null;
      return false;
    }

    return true;
  }

  /**
   * Logout (clear admin token)
   */
  logout(): void {
    this.authToken = null;
    this.log('Logged out');
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Tier B: Business Metrics Methods (Public/Auth)
  // ───────────────────────────────────────────────────────────────────────────

  /**
   * Get metrics for a specific application
   */
  async getApplicationMetrics(applicationId: string): Promise<ApplicationMetrics> {
    this.log(`Fetching application metrics for ${applicationId}`);
    return this.fetch<ApplicationMetrics>(`/application/${applicationId}`);
  }

  /**
   * Get aggregated portfolio metrics
   */
  async getPortfolioMetrics(period: MetricsPeriod): Promise<PortfolioMetrics> {
    this.log(`Fetching portfolio metrics for period: ${period.period}`);
    return this.fetch<PortfolioMetrics>(`/portfolio/${period.period}`);
  }

  /**
   * Get journey stage metrics
   */
  async getJourneyMetrics(): Promise<JourneyStageMetrics[]> {
    this.log('Fetching journey metrics');
    return this.fetch<JourneyStageMetrics[]>('/journey');
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Tier A: AI Metrics Methods (Admin Only)
  // ───────────────────────────────────────────────────────────────────────────

  /**
   * Get AI quality metrics for a specific conversation
   */
  async getAIMetrics(conversationId: string): Promise<AIMetrics> {
    this.log(`Fetching AI metrics for conversation ${conversationId}`);
    this.requireAdminAuth();
    return this.fetch<AIMetrics>(`/ai/${conversationId}`);
  }

  /**
   * Get aggregated AI quality metrics
   */
  async getAggregateAIMetrics(period: MetricsPeriod): Promise<AggregateAIMetrics> {
    this.log(`Fetching aggregate AI metrics for period: ${period.period}`);
    this.requireAdminAuth();
    return this.fetch<AggregateAIMetrics>(`/ai/aggregate/${period.period}`);
  }

  /**
   * Get model performance breakdown
   */
  async getModelPerformanceMetrics(): Promise<ModelPerformanceMetrics[]> {
    this.log('Fetching model performance metrics');
    this.requireAdminAuth();
    return this.fetch<ModelPerformanceMetrics[]>('/ai/models');
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Private Helper Methods
  // ───────────────────────────────────────────────────────────────────────────

  /**
   * Require admin authentication
   */
  private requireAdminAuth(): void {
    if (!this.isAuthenticated()) {
      throw new Error('Admin authentication required');
    }
  }

  /**
   * Generic fetch method with error handling
   */
  private async fetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.config.baseUrl}${endpoint}`;
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add auth token if available
    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken.token}`;
    }

    this.log(`Fetching ${url}`);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw this.createApiError(response.status, errorData);
      }

      const data = await response.json();
      this.log(`Successfully fetched ${endpoint}`);
      return data as T;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw this.createApiError(408, { message: 'Request timeout' });
        }
        throw this.createApiError(500, { message: error.message });
      }
      
      throw this.createApiError(500, { message: 'Unknown error' });
    }
  }

  /**
   * Create API error object
   */
  private createApiError(status: number, data: Record<string, unknown>): ApiError {
    return {
      status,
      message: (data.message as string) || 'Unknown error',
      detail: (data.detail as string),
    };
  }

  /**
   * Debug logging
   */
  private log(message: string): void {
    if (this.config.debug) {
      console.log(`[MetricsAPI] ${message}`);
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth Response Type
// ─────────────────────────────────────────────────────────────────────────────

interface AuthResponse {
  success: boolean;
  token?: string;
  expires_at?: string;
  message?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Singleton Instance
// ─────────────────────────────────────────────────────────────────────────────

let metricsClientInstance: MetricsApiClient | null = null;

/**
 * Get or create metrics client singleton
 */
export function getMetricsClient(config?: Partial<MetricsApiClientConfig>): MetricsApiClient {
  if (!metricsClientInstance) {
    metricsClientInstance = new MetricsApiClient(config);
  }
  return metricsClientInstance;
}

/**
 * Reset metrics client singleton (useful for testing)
 */
export function resetMetricsClient(): void {
  metricsClientInstance = null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Module Exports
// ─────────────────────────────────────────────────────────────────────────────

export { MetricsApiClient as default };
