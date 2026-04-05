/**
 * Test Suite for Metrics Client
 * 
 * Tests the TypeScript metrics API client for:
 * - Authentication
 * - Tier B metrics endpoints
 * - Tier A metrics endpoints (admin)
 * - Error handling
 * - Token management
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MetricsApiClient, getMetricsClient, resetMetricsClient } from '../metricsClient';
import { ApplicationStatus, GradeLevel } from '../../types/metrics';

// Mock fetch globally (vitest)
global.fetch = vi.fn();

describe('MetricsApiClient', () => {
  let client: MetricsApiClient;

  beforeEach(() => {
    client = new MetricsApiClient({ baseUrl: '/api/metrics', debug: false });
    vi.clearAllMocks();
  });

  afterEach(() => {
    resetMetricsClient();
  });

  describe('Authentication', () => {
    it('should authenticate admin successfully', async () => {
      const mockResponse = {
        success: true,
        token: 'mock-jwt-token',
        expires_at: new Date(Date.now() + 86400000).toISOString(),
        message: 'Authentication successful',
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await client.authenticateAdmin('testpassword');

      expect(result.token).toBe('mock-jwt-token');
      expect(client.isAuthenticated()).toBe(true);
    });

    it('should reject invalid password', async () => {
      const mockResponse = {
        success: false,
        message: 'Invalid password',
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await expect(client.authenticateAdmin('wrongpassword')).rejects.toThrow(
        'Invalid password'
      );
    });

    it('should check authentication status', () => {
      expect(client.isAuthenticated()).toBe(false);
    });

    it('should logout and clear token', async () => {
      // First authenticate
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          token: 'mock-token',
          expires_at: new Date(Date.now() + 86400000).toISOString(),
        }),
      });

      await client.authenticateAdmin('password');
      expect(client.isAuthenticated()).toBe(true);

      // Then logout
      client.logout();
      expect(client.isAuthenticated()).toBe(false);
    });
  });

  describe('Tier B: Business Metrics', () => {
    it('should fetch application metrics', async () => {
      const mockMetrics = {
        application_id: 'APP-123',
        status: ApplicationStatus.APPROVED,
        processing_time_seconds: 2.3,
        loan_amount: 75000,
        currency: 'USD',
        bureau_score: 720,
        bureau_grade: GradeLevel.B,
        foir_ratio: 32.0,
        ltv_ratio: 83.0,
        journey_progress: 85.0,
        journey_stages: ['advisory', 'application', 'stp'],
        current_stage: 'approval',
        submitted_at: new Date().toISOString(),
        processed_at: new Date().toISOString(),
        decision_reason: 'All STP checks passed',
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics,
      });

      const result = await client.getApplicationMetrics('APP-123');

      expect(result.application_id).toBe('APP-123');
      expect(result.status).toBe(ApplicationStatus.APPROVED);
      expect(result.bureau_score).toBe(720);
    });

    it('should fetch portfolio metrics', async () => {
      const mockMetrics = {
        period: 'today',
        period_start: new Date().toISOString(),
        period_end: new Date().toISOString(),
        total_applications: 47,
        approved_count: 42,
        rejected_count: 5,
        pending_count: 0,
        approval_rate: 89.4,
        rejection_rate: 10.6,
        average_loan_amount: 68500,
        average_bureau_score: 695,
        average_processing_time: 2.8,
        average_foir: 38.5,
        rejection_reasons: { low_bureau_score: 2, high_foir: 2, aml_failure: 1 },
        risk_distribution: { low: 15, moderate: 20, elevated: 10, high: 2 },
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics,
      });

      const result = await client.getPortfolioMetrics({ period: 'today' });

      expect(result.total_applications).toBe(47);
      expect(result.approval_rate).toBe(89.4);
    });

    it('should fetch journey metrics', async () => {
      const mockMetrics = [
        {
          stage_name: 'advisory',
          stage_order: 1,
          entered_count: 150,
          completed_count: 140,
          drop_off_count: 10,
          completion_rate: 93.3,
          average_time_in_stage_seconds: 240.5,
        },
      ];

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics,
      });

      const result = await client.getJourneyMetrics();

      expect(Array.isArray(result)).toBe(true);
      expect(result[0].stage_name).toBe('advisory');
      expect(result[0].completion_rate).toBe(93.3);
    });
  });

  describe('Tier A: AI Metrics (Admin)', () => {
    it('should require admin auth for AI metrics', async () => {
      await expect(client.getAIMetrics('conv-123')).rejects.toThrow(
        'Admin authentication required'
      );
    });

    it('should fetch AI metrics after authentication', async () => {
      // Authenticate first
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          token: 'mock-token',
          expires_at: new Date(Date.now() + 86400000).toISOString(),
        }),
      });

      await client.authenticateAdmin('password');

      // Then fetch AI metrics
      const mockAIMetrics = {
        conversation_id: 'conv-123',
        session_id: 'session-123',
        application_id: 'APP-123',
        hallucination_rate: 0.02,
        hallucination_flags: [],
        total_claims: 15,
        unsupported_claims: 0,
        ragas_faithfulness: 0.96,
        ragas_relevance: 0.94,
        ragas_context_precision: 0.92,
        ragas_overall: 0.94,
        llm_latency_p50: 1200,
        llm_latency_p95: 3400,
        llm_latency_p99: 5200,
        total_tokens: 2341,
        prompt_tokens: 1800,
        completion_tokens: 541,
        cost_usd: 0.047,
        model_used: 'qwen2.5:7b',
        model_provider: 'ollama',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockAIMetrics,
      });

      const result = await client.getAIMetrics('conv-123');

      expect(result.hallucination_rate).toBe(0.02);
      expect(result.ragas_overall).toBe(0.94);
    });

    it('should fetch aggregate AI metrics', async () => {
      // Authenticate first
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          token: 'mock-token',
          expires_at: new Date(Date.now() + 86400000).toISOString(),
        }),
      });

      await client.authenticateAdmin('password');

      const mockAggregateMetrics = {
        period: 'today',
        period_start: new Date().toISOString(),
        period_end: new Date().toISOString(),
        total_conversations: 150,
        evaluated_conversations: 15,
        average_hallucination_rate: 0.018,
        max_hallucination_rate: 0.12,
        conversations_with_flags: 3,
        average_ragas_faithfulness: 0.94,
        average_ragas_relevance: 0.92,
        average_ragas_overall: 0.93,
        average_latency_p50: 1150,
        average_latency_p95: 3200,
        total_tokens: 351150,
        total_cost_usd: 7.05,
        cost_per_conversation: 0.047,
        model_distribution: { 'qwen2.5:7b': 87.0, 'gpt-4.1-mini': 13.0 },
        provider_distribution: { ollama: 87.0, openai: 13.0 },
        low_quality_conversations: 1,
        high_hallucination_conversations: 0,
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockAggregateMetrics,
      });

      const result = await client.getAggregateAIMetrics({ period: 'today' });

      expect(result.average_hallucination_rate).toBe(0.018);
      expect(result.model_distribution['qwen2.5:7b']).toBe(87.0);
    });
  });

  describe('Error Handling', () => {
    it('should handle 404 errors', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ message: 'Not found' }),
      });

      await expect(client.getApplicationMetrics('APP-NONEXISTENT')).rejects.toThrow();
    });

    it('should handle timeout errors', async () => {
      (global.fetch as any).mockImplementationOnce(() => {
        return new Promise((_, reject) => {
          setTimeout(() => reject(new Error('AbortError')), 100);
        });
      });

      client = new MetricsApiClient({ timeout: 50 });

      await expect(client.getApplicationMetrics('APP-123')).rejects.toThrow();
    });

    it('should handle network errors', async () => {
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      await expect(client.getApplicationMetrics('APP-123')).rejects.toThrow();
    });
  });

  describe('Singleton Pattern', () => {
    it('should return same instance from getMetricsClient', () => {
      const client1 = getMetricsClient();
      const client2 = getMetricsClient();

      expect(client1).toBe(client2);
    });

    it('should reset singleton with resetMetricsClient', () => {
      const client1 = getMetricsClient();
      resetMetricsClient();
      const client2 = getMetricsClient();

      expect(client1).not.toBe(client2);
    });
  });
});
