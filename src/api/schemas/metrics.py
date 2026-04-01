"""
Metrics API Schemas for KS-LOS Phase 2

This module defines Pydantic schemas for Tier A (Technical AI) and Tier B (Business)
metrics endpoints. All schemas are designed for:
- Type safety and validation
- API documentation (OpenAPI/Swagger)
- Frontend consumption (TypeScript generation)
- Performance (minimal serialization overhead)

Tier A Metrics (Admin Only):
- Hallucination rates
- RAGAS quality scores
- LLM latency and costs
- Model distribution

Tier B Metrics (Client-Facing):
- Application status
- Processing times
- Bureau scores
- FOIR/LTV ratios
- Portfolio aggregates
"""

from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# Common Enums
# ─────────────────────────────────────────────────────────────────────────────

class ApplicationStatus(str, Enum):
    """Application processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    MANUAL_REVIEW = "manual_review"


class RiskLevel(str, Enum):
    """Risk classification"""
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"


class GradeLevel(str, Enum):
    """Credit grade levels"""
    A = "A"  # Excellent
    B = "B"  # Good
    C = "C"  # Fair
    D = "D"  # Poor
    E = "E"  # Very Poor


# ─────────────────────────────────────────────────────────────────────────────
# Tier B: Business Metrics Schemas (Client-Facing)
# ─────────────────────────────────────────────────────────────────────────────

class ApplicationMetrics(BaseModel):
    """
    Individual application metrics for borrower display.
    
    Contains all metrics a borrower should see about their
    specific application.
    """
    application_id: str = Field(..., description="Unique application identifier")
    status: ApplicationStatus = Field(..., description="Current application status")
    processing_time_seconds: float = Field(..., ge=0, description="Time from submission to decision")
    loan_amount: float = Field(..., gt=0, description="Requested loan amount in USD")
    currency: str = Field(default="USD", description="Currency code")
    
    # Credit metrics
    bureau_score: Optional[int] = Field(None, ge=300, le=900, description="Credit bureau score")
    bureau_grade: Optional[GradeLevel] = Field(None, description="Credit grade (A-E)")
    foir_ratio: Optional[float] = Field(None, ge=0, le=100, description="Fixed Obligation to Income Ratio (%)")
    ltv_ratio: Optional[float] = Field(None, ge=0, le=100, description="Loan-to-Value ratio (%)")
    
    # Journey tracking
    journey_progress: float = Field(..., ge=0, le=100, description="Journey completion percentage")
    journey_stages: List[str] = Field(default_factory=list, description="Completed journey stages")
    current_stage: Optional[str] = Field(None, description="Current journey stage")
    
    # Timestamps
    submitted_at: datetime = Field(..., description="Application submission timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    
    # Decision
    decision_reason: Optional[str] = Field(None, description="Approval/rejection reason")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "application_id": "APP-20260401-123456",
                "status": "approved",
                "processing_time_seconds": 2.3,
                "loan_amount": 75000.0,
                "currency": "USD",
                "bureau_score": 720,
                "bureau_grade": "B",
                "foir_ratio": 32.0,
                "ltv_ratio": 83.0,
                "journey_progress": 85.0,
                "journey_stages": ["advisory", "application", "stp"],
                "current_stage": "approval",
                "submitted_at": "2026-04-01T10:30:00Z",
                "processed_at": "2026-04-01T10:30:02Z",
                "decision_reason": "All STP checks passed"
            }
        }
    }


class PortfolioMetrics(BaseModel):
    """
    Aggregated portfolio metrics for dashboard display.
    
    Contains statistics across all applications for a given period.
    """
    period: str = Field(..., description="Time period (today, week, month)")
    period_start: datetime = Field(..., description="Period start timestamp")
    period_end: datetime = Field(..., description="Period end timestamp")
    
    # Volume metrics
    total_applications: int = Field(..., ge=0, description="Total applications in period")
    approved_count: int = Field(..., ge=0, description="Approved applications")
    rejected_count: int = Field(..., ge=0, description="Rejected applications")
    pending_count: int = Field(..., ge=0, description="Pending applications")
    
    # Rates
    approval_rate: float = Field(..., ge=0, le=100, description="Approval rate (%)")
    rejection_rate: float = Field(..., ge=0, le=100, description="Rejection rate (%)")
    
    # Averages
    average_loan_amount: float = Field(..., ge=0, description="Average loan amount (USD)")
    average_bureau_score: float = Field(..., ge=300, le=900, description="Average bureau score")
    average_processing_time: float = Field(..., ge=0, description="Average processing time (seconds)")
    average_foir: Optional[float] = Field(None, ge=0, le=100, description="Average FOIR (%)")
    
    # Rejection breakdown
    rejection_reasons: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by rejection reason"
    )
    
    # Risk distribution
    risk_distribution: Dict[RiskLevel, int] = Field(
        default_factory=dict,
        description="Applications by risk level"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "period": "today",
                "period_start": "2026-04-01T00:00:00Z",
                "period_end": "2026-04-01T23:59:59Z",
                "total_applications": 47,
                "approved_count": 42,
                "rejected_count": 5,
                "pending_count": 0,
                "approval_rate": 89.4,
                "rejection_rate": 10.6,
                "average_loan_amount": 68500.0,
                "average_bureau_score": 695.0,
                "average_processing_time": 2.8,
                "average_foir": 38.5,
                "rejection_reasons": {
                    "low_bureau_score": 2,
                    "high_foir": 2,
                    "aml_failure": 1
                },
                "risk_distribution": {
                    "low": 15,
                    "moderate": 20,
                    "elevated": 10,
                    "high": 2
                }
            }
        }
    }


class JourneyStageMetrics(BaseModel):
    """
    Metrics for specific journey stage.
    
    Tracks completion rates and drop-off points.
    """
    stage_name: str = Field(..., description="Stage identifier")
    stage_order: int = Field(..., ge=0, description="Stage sequence number")
    entered_count: int = Field(..., ge=0, description="Users who entered this stage")
    completed_count: int = Field(..., ge=0, description="Users who completed this stage")
    drop_off_count: int = Field(..., ge=0, description="Users who dropped off")
    completion_rate: float = Field(..., ge=0, le=100, description="Stage completion rate (%)")
    average_time_in_stage_seconds: float = Field(..., ge=0, description="Average time spent")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "stage_name": "application_submission",
                "stage_order": 2,
                "entered_count": 100,
                "completed_count": 85,
                "drop_off_count": 15,
                "completion_rate": 85.0,
                "average_time_in_stage_seconds": 180.5
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tier A: Technical AI Metrics Schemas (Admin Only)
# ─────────────────────────────────────────────────────────────────────────────

class AIMetrics(BaseModel):
    """
    Individual conversation AI quality metrics.
    
    Contains technical metrics for a single conversation.
    Admin access only.
    """
    conversation_id: str = Field(..., description="Unique conversation identifier")
    session_id: str = Field(..., description="Session identifier")
    application_id: Optional[str] = Field(None, description="Associated application ID")
    
    # Hallucination metrics
    hallucination_rate: float = Field(..., ge=0, le=1, description="Hallucination rate (0-1)")
    hallucination_flags: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Specific hallucination flags"
    )
    total_claims: int = Field(..., ge=0, description="Total claims extracted")
    unsupported_claims: int = Field(..., ge=0, description="Unsupported claims count")
    
    # RAGAS quality scores
    ragas_faithfulness: Optional[float] = Field(None, ge=0, le=1, description="RAGAS faithfulness score")
    ragas_relevance: Optional[float] = Field(None, ge=0, le=1, description="RAGAS relevance score")
    ragas_context_precision: Optional[float] = Field(None, ge=0, le=1, description="RAGAS context precision")
    ragas_overall: Optional[float] = Field(None, ge=0, le=1, description="RAGAS overall score")
    
    # LLM performance
    llm_latency_p50: float = Field(..., ge=0, description="Median LLM latency (ms)")
    llm_latency_p95: float = Field(..., ge=0, description="95th percentile LLM latency (ms)")
    llm_latency_p99: float = Field(..., ge=0, description="99th percentile LLM latency (ms)")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    prompt_tokens: int = Field(..., ge=0, description="Prompt tokens")
    completion_tokens: int = Field(..., ge=0, description="Completion tokens")
    cost_usd: float = Field(..., ge=0, description="Total cost (USD)")
    
    # Model information
    model_used: str = Field(..., description="Primary model used")
    model_provider: Literal["openai", "ollama", "mixed"] = Field(..., description="Model provider")
    
    # Timestamps
    created_at: datetime = Field(..., description="Conversation start timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "conversation_id": "conv-123456",
                "session_id": "session-789",
                "application_id": "APP-20260401-123456",
                "hallucination_rate": 0.02,
                "hallucination_flags": [],
                "total_claims": 15,
                "unsupported_claims": 0,
                "ragas_faithfulness": 0.96,
                "ragas_relevance": 0.94,
                "ragas_context_precision": 0.92,
                "ragas_overall": 0.94,
                "llm_latency_p50": 1200.0,
                "llm_latency_p95": 3400.0,
                "llm_latency_p99": 5200.0,
                "total_tokens": 2341,
                "prompt_tokens": 1800,
                "completion_tokens": 541,
                "cost_usd": 0.047,
                "model_used": "qwen2.5:7b",
                "model_provider": "ollama",
                "created_at": "2026-04-01T10:30:00Z",
                "updated_at": "2026-04-01T10:35:00Z"
            }
        }
    }


class AggregateAIMetrics(BaseModel):
    """
    Aggregated AI quality metrics across conversations.
    
    Contains statistics for monitoring AI system health.
    Admin access only.
    """
    period: str = Field(..., description="Time period (today, week, month)")
    period_start: datetime = Field(..., description="Period start timestamp")
    period_end: datetime = Field(..., description="Period end timestamp")
    
    # Volume
    total_conversations: int = Field(..., ge=0, description="Total conversations")
    evaluated_conversations: int = Field(..., ge=0, description="Conversations with RAGAS evaluation")
    
    # Hallucination metrics
    average_hallucination_rate: float = Field(..., ge=0, le=1, description="Average hallucination rate")
    max_hallucination_rate: float = Field(..., ge=0, le=1, description="Maximum hallucination rate")
    conversations_with_flags: int = Field(..., ge=0, description="Conversations with hallucination flags")
    
    # RAGAS quality
    average_ragas_faithfulness: Optional[float] = Field(None, ge=0, le=1, description="Average faithfulness")
    average_ragas_relevance: Optional[float] = Field(None, ge=0, le=1, description="Average relevance")
    average_ragas_overall: Optional[float] = Field(None, ge=0, le=1, description="Average overall score")
    
    # LLM performance
    average_latency_p50: float = Field(..., ge=0, description="Average median latency (ms)")
    average_latency_p95: float = Field(..., ge=0, description="Average 95th percentile latency (ms)")
    total_tokens: int = Field(..., ge=0, description="Total tokens consumed")
    total_cost_usd: float = Field(..., ge=0, description="Total cost (USD)")
    cost_per_conversation: float = Field(..., ge=0, description="Average cost per conversation")
    
    # Model distribution
    model_distribution: Dict[str, float] = Field(
        default_factory=dict,
        description="Percentage by model (must sum to 100)"
    )
    
    # Provider distribution
    provider_distribution: Dict[str, float] = Field(
        default_factory=dict,
        description="Percentage by provider (openai, ollama)"
    )
    
    # Quality alerts
    low_quality_conversations: int = Field(
        ..., ge=0,
        description="Conversations with RAGAS < 0.7"
    )
    high_hallucination_conversations: int = Field(
        ..., ge=0,
        description="Conversations with hallucination rate > 0.3"
    )
    
    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "period": "today",
                "period_start": "2026-04-01T00:00:00Z",
                "period_end": "2026-04-01T23:59:59Z",
                "total_conversations": 150,
                "evaluated_conversations": 15,
                "average_hallucination_rate": 0.018,
                "max_hallucination_rate": 0.12,
                "conversations_with_flags": 3,
                "average_ragas_faithfulness": 0.94,
                "average_ragas_relevance": 0.92,
                "average_ragas_overall": 0.93,
                "average_latency_p50": 1150.0,
                "average_latency_p95": 3200.0,
                "total_tokens": 351150,
                "total_cost_usd": 7.05,
                "cost_per_conversation": 0.047,
                "model_distribution": {
                    "qwen2.5:7b": 87.0,
                    "gpt-4.1-mini": 13.0
                },
                "provider_distribution": {
                    "ollama": 87.0,
                    "openai": 13.0
                },
                "low_quality_conversations": 1,
                "high_hallucination_conversations": 0
            }
        }
    }


class ModelPerformanceMetrics(BaseModel):
    """
    Performance metrics by model.
    
    Tracks latency, cost, and quality per model.
    """
    model_name: str = Field(..., description="Model identifier")
    provider: str = Field(..., description="Provider (openai, ollama)")
    
    # Usage
    total_calls: int = Field(..., ge=0, description="Total API calls")
    total_tokens: int = Field(..., ge=0, description="Total tokens")
    
    # Performance
    latency_p50: float = Field(..., ge=0, description="Median latency (ms)")
    latency_p95: float = Field(..., ge=0, description="95th percentile latency (ms)")
    latency_p99: float = Field(..., ge=0, description="99th percentile latency (ms)")
    
    # Cost
    total_cost_usd: float = Field(..., ge=0, description="Total cost (USD)")
    cost_per_1k_tokens: float = Field(..., ge=0, description="Cost per 1K tokens")
    
    # Quality (if evaluated)
    average_hallucination_rate: Optional[float] = Field(None, ge=0, le=1)
    average_ragas_score: Optional[float] = Field(None, ge=0, le=1)
    
    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "model_name": "qwen2.5:7b",
                "provider": "ollama",
                "total_calls": 1250,
                "total_tokens": 293625,
                "latency_p50": 1100.0,
                "latency_p95": 3100.0,
                "latency_p99": 4800.0,
                "total_cost_usd": 0.0,
                "cost_per_1k_tokens": 0.0,
                "average_hallucination_rate": 0.019,
                "average_ragas_score": 0.93
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Schemas
# ─────────────────────────────────────────────────────────────────────────────

class MetricsPeriodRequest(BaseModel):
    """Request for metrics with time period"""
    period: Literal["today", "yesterday", "week", "month", "custom"] = Field(
        default="today",
        description="Time period for metrics"
    )
    start_date: Optional[datetime] = Field(None, description="Custom period start")
    end_date: Optional[datetime] = Field(None, description="Custom period end")


class AdminAuthRequest(BaseModel):
    """Admin authentication request"""
    password: str = Field(..., min_length=8, description="Admin password")


class AdminAuthResponse(BaseModel):
    """Admin authentication response"""
    success: bool = Field(..., description="Authentication success")
    token: Optional[str] = Field(None, description="JWT token for subsequent requests")
    expires_at: Optional[datetime] = Field(None, description="Token expiration timestamp")
    message: Optional[str] = Field(None, description="Error message if failed")


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Enums
    "ApplicationStatus",
    "RiskLevel",
    "GradeLevel",
    
    # Tier B: Business metrics
    "ApplicationMetrics",
    "PortfolioMetrics",
    "JourneyStageMetrics",
    
    # Tier A: AI metrics
    "AIMetrics",
    "AggregateAIMetrics",
    "ModelPerformanceMetrics",
    
    # Request/Response
    "MetricsPeriodRequest",
    "AdminAuthRequest",
    "AdminAuthResponse",
]
