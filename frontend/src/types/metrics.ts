/**
 * Metrics Type Definitions for KS-LOS Phase 2
 * 
 * TypeScript types matching the Pydantic schemas from the backend.
 * These types ensure type-safe consumption of the metrics API.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Enums
// ─────────────────────────────────────────────────────────────────────────────

export const ApplicationStatus = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  APPROVED: 'approved',
  REJECTED: 'rejected',
  DISBURSED: 'disbursed',
  MANUAL_REVIEW: 'manual_review',
} as const;
export type ApplicationStatus = typeof ApplicationStatus[keyof typeof ApplicationStatus];

export const GradeLevel = {
  A: 'A',
  B: 'B',
  C: 'C',
  D: 'D',
  E: 'E',
} as const;
export type GradeLevel = typeof GradeLevel[keyof typeof GradeLevel];

export const RiskLevel = {
  LOW: 'low',
  MODERATE: 'moderate',
  ELEVATED: 'elevated',
  HIGH: 'high',
} as const;
export type RiskLevel = typeof RiskLevel[keyof typeof RiskLevel];

// ─────────────────────────────────────────────────────────────────────────────
// Tier B: Business Metrics Types (Client-Facing)
// ─────────────────────────────────────────────────────────────────────────────

export interface ApplicationMetrics {
  application_id: string;
  status: ApplicationStatus;
  processing_time_seconds: number;
  loan_amount: number;
  currency: string;
  
  // Credit metrics
  bureau_score: number | null;
  bureau_grade: GradeLevel | null;
  foir_ratio: number | null;
  ltv_ratio: number | null;
  
  // Journey tracking
  journey_progress: number;
  journey_stages: string[];
  current_stage: string | null;
  
  // Timestamps
  submitted_at: string; // ISO 8601
  processed_at: string | null; // ISO 8601
  
  // Decision
  decision_reason: string | null;
}

export interface PortfolioMetrics {
  period: string;
  period_start: string; // ISO 8601
  period_end: string; // ISO 8601
  
  // Volume metrics
  total_applications: number;
  approved_count: number;
  rejected_count: number;
  pending_count: number;
  
  // Rates
  approval_rate: number;
  rejection_rate: number;
  
  // Averages
  average_loan_amount: number;
  average_bureau_score: number;
  average_processing_time: number;
  average_foir: number | null;
  
  // Rejection breakdown
  rejection_reasons: Record<string, number>;
  
  // Risk distribution
  risk_distribution: Record<RiskLevel, number>;
}

export interface JourneyStageMetrics {
  stage_name: string;
  stage_order: number;
  entered_count: number;
  completed_count: number;
  drop_off_count: number;
  completion_rate: number;
  average_time_in_stage_seconds: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Tier A: Technical AI Metrics Types (Admin Only)
// ─────────────────────────────────────────────────────────────────────────────

export interface AIMetrics {
  conversation_id: string;
  session_id: string;
  application_id: string | null;
  
  // Hallucination metrics
  hallucination_rate: number;
  hallucination_flags: Array<Record<string, unknown>>;
  total_claims: number;
  unsupported_claims: number;
  
  // RAGAS quality scores
  ragas_faithfulness: number | null;
  ragas_relevance: number | null;
  ragas_context_precision: number | null;
  ragas_overall: number | null;
  
  // LLM performance
  llm_latency_p50: number;
  llm_latency_p95: number;
  llm_latency_p99: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  
  // Model information
  model_used: string;
  model_provider: 'openai' | 'ollama' | 'mixed';
  
  // Timestamps
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface AggregateAIMetrics {
  period: string;
  period_start: string; // ISO 8601
  period_end: string; // ISO 8601
  
  // Volume
  total_conversations: number;
  evaluated_conversations: number;
  
  // Hallucination metrics
  average_hallucination_rate: number;
  max_hallucination_rate: number;
  conversations_with_flags: number;
  
  // RAGAS quality
  average_ragas_faithfulness: number | null;
  average_ragas_relevance: number | null;
  average_ragas_overall: number | null;
  
  // LLM performance
  average_latency_p50: number;
  average_latency_p95: number;
  total_tokens: number;
  total_cost_usd: number;
  cost_per_conversation: number;
  
  // Model distribution
  model_distribution: Record<string, number>;
  
  // Provider distribution
  provider_distribution: Record<string, number>;
  
  // Quality alerts
  low_quality_conversations: number;
  high_hallucination_conversations: number;
}

export interface ModelPerformanceMetrics {
  model_name: string;
  provider: string;
  
  // Usage
  total_calls: number;
  total_tokens: number;
  
  // Performance
  latency_p50: number;
  latency_p95: number;
  latency_p99: number;
  
  // Cost
  total_cost_usd: number;
  cost_per_1k_tokens: number;
  
  // Quality (if evaluated)
  average_hallucination_rate: number | null;
  average_ragas_score: number | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Request/Response Types
// ─────────────────────────────────────────────────────────────────────────────

export interface MetricsPeriodRequest {
  period: 'today' | 'yesterday' | 'week' | 'month' | 'custom';
  start_date?: string; // ISO 8601
  end_date?: string; // ISO 8601
}

export interface AdminAuthRequest {
  password: string;
}

export interface AdminAuthResponse {
  success: boolean;
  token?: string;
  expires_at?: string; // ISO 8601
  message?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Module Exports
// ─────────────────────────────────────────────────────────────────────────────

export type {
  ApplicationMetrics as ApplicationMetricsType,
  PortfolioMetrics as PortfolioMetricsType,
  JourneyStageMetrics as JourneyStageMetricsType,
  AIMetrics as AIMetricsType,
  AggregateAIMetrics as AggregateAIMetricsType,
  ModelPerformanceMetrics as ModelPerformanceMetricsType,
};
