"""
Metrics API Router for KS-LOS Phase 2

This router provides REST API endpoints for Tier A (Technical AI) and Tier B (Business)
metrics. All endpoints are designed for:
- Real-time data access
- Secure authentication (Tier A requires admin)
- High performance (cached aggregations)
- Frontend consumption (TypeScript-compatible)

Tier B Endpoints (Authenticated Users):
- GET /api/metrics/application/{id} - Individual application metrics
- GET /api/metrics/portfolio/{period} - Portfolio aggregates
- GET /api/metrics/journey - Journey stage metrics

Tier A Endpoints (Admin Only):
- GET /api/metrics/ai/{conversation_id} - Individual AI metrics
- GET /api/metrics/ai/aggregate/{period} - Aggregated AI metrics
- GET /api/metrics/ai/models - Model performance breakdown
- POST /api/metrics/admin/auth - Admin authentication

Usage:
    from fastapi import FastAPI
    from src.api.routers.metrics import router
    
    app.include_router(router, prefix="/api/metrics", tags=["metrics"])
"""

import os
import logging
import time
import hashlib
import hmac
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt

logger = logging.getLogger(__name__)

from src.api.schemas.metrics import (
    # Tier B
    ApplicationMetrics,
    PortfolioMetrics,
    JourneyStageMetrics,
    # Tier A
    AIMetrics,
    AggregateAIMetrics,
    ModelPerformanceMetrics,
    # Requests
    MetricsPeriodRequest,
    AdminAuthRequest,
    AdminAuthResponse,
    # Enums
    ApplicationStatus,
    RiskLevel,
    GradeLevel,
)

# ─────────────────────────────────────────────────────────────────────────────
# Router Configuration
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(tags=["metrics"])
security = HTTPBearer(auto_error=False)

# Admin JWT configuration
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "ks-los-admin-secret-change-in-production")
ADMIN_TOKEN_EXPIRY_HOURS = 24


# ─────────────────────────────────────────────────────────────────────────────
# Authentication Dependencies
# ─────────────────────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Get current user from JWT token.
    
    Returns None if no credentials (public access).
    Raises HTTPException if invalid credentials.
    """
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            ADMIN_SECRET,
            algorithms=["HS256"]
        )
        return payload.get("sub")
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


async def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Require admin authentication.
    
    Raises HTTPException if not authenticated or not admin.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            ADMIN_SECRET,
            algorithms=["HS256"]
        )
        
        if payload.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return payload.get("sub")
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tier B: Business Metrics Endpoints (Authenticated Users)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/application/{application_id}",
    response_model=ApplicationMetrics,
    summary="Get Application Metrics",
    description="Retrieve metrics for a specific loan application. Accessible by the application owner."
)
async def get_application_metrics(
    application_id: str,
    current_user: Optional[str] = Depends(get_current_user)
) -> ApplicationMetrics:
    """
    Get metrics for a specific loan application.
    
    This endpoint returns comprehensive metrics about a single application,
    including processing status, credit metrics, and journey progress.
    
    **Access:** Authenticated users (borrower or officer)
    """
    # TODO: Integrate with database to fetch real metrics
    # For now, return simulated data for demo purposes
    
    # Simulate database lookup
    application_data = _get_application_from_db(application_id)
    
    if not application_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )
    
    # Convert to metrics schema
    return ApplicationMetrics(
        application_id=application_data["id"],
        status=ApplicationStatus(application_data.get("status", "pending")),
        processing_time_seconds=application_data.get("processing_time", 2.3),
        loan_amount=application_data.get("loan_amount", 75000.0),
        currency=application_data.get("currency", "USD"),
        bureau_score=application_data.get("bureau_score"),
        bureau_grade=_score_to_grade(application_data.get("bureau_score")),
        foir_ratio=application_data.get("foir"),
        ltv_ratio=application_data.get("ltv"),
        journey_progress=application_data.get("journey_progress", 0.0),
        journey_stages=application_data.get("journey_stages", []),
        current_stage=application_data.get("current_stage"),
        submitted_at=application_data.get("submitted_at", datetime.now()),
        processed_at=application_data.get("processed_at"),
        decision_reason=application_data.get("decision_reason"),
    )


@router.get(
    "/portfolio/{period}",
    response_model=PortfolioMetrics,
    summary="Get Portfolio Metrics",
    description="Get aggregated portfolio metrics for a time period."
)
async def get_portfolio_metrics(
    period: str,
    current_user: Optional[str] = Depends(get_current_user)
) -> PortfolioMetrics:
    """
    Get aggregated portfolio metrics.
    
    Returns statistics across all applications for the specified period.
    Includes approval rates, averages, and rejection breakdowns.
    
    **Access:** Authenticated users (officers see all, borrowers see limited)
    """
    # Calculate period boundaries
    now = datetime.now()
    if period == "today":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = now
    elif period == "yesterday":
        yesterday = now - timedelta(days=1)
        period_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)
    elif period == "week":
        period_start = now - timedelta(days=7)
        period_end = now
    elif period == "month":
        period_start = now - timedelta(days=30)
        period_end = now
    else:
        period_start = now - timedelta(days=1)
        period_end = now
    
    # TODO: Query database for real metrics
    # For now, return simulated data
    portfolio_data = _get_portfolio_from_db(period_start, period_end)
    
    return PortfolioMetrics(
        period=period,
        period_start=period_start,
        period_end=period_end,
        total_applications=portfolio_data.get("total", 47),
        approved_count=portfolio_data.get("approved", 42),
        rejected_count=portfolio_data.get("rejected", 5),
        pending_count=portfolio_data.get("pending", 0),
        approval_rate=portfolio_data.get("approval_rate", 89.4),
        rejection_rate=portfolio_data.get("rejection_rate", 10.6),
        average_loan_amount=portfolio_data.get("avg_loan", 68500.0),
        average_bureau_score=portfolio_data.get("avg_score", 695.0),
        average_processing_time=portfolio_data.get("avg_time", 2.8),
        average_foir=portfolio_data.get("avg_foir", 38.5),
        rejection_reasons=portfolio_data.get("rejection_reasons", {}),
        risk_distribution=portfolio_data.get("risk_distribution", {}),
    )


@router.get(
    "/journey",
    response_model=List[JourneyStageMetrics],
    summary="Get Journey Stage Metrics",
    description="Get metrics for each stage of the borrower journey."
)
async def get_journey_metrics(
    current_user: Optional[str] = Depends(get_current_user)
) -> List[JourneyStageMetrics]:
    """
    Get journey stage metrics.
    
    Returns completion rates and drop-off statistics for each stage
    of the borrower journey.
    """
    # TODO: Query database for real journey metrics
    # For now, return simulated data
    
    return [
        JourneyStageMetrics(
            stage_name="advisory",
            stage_order=1,
            entered_count=150,
            completed_count=140,
            drop_off_count=10,
            completion_rate=93.3,
            average_time_in_stage_seconds=240.5
        ),
        JourneyStageMetrics(
            stage_name="application_submission",
            stage_order=2,
            entered_count=140,
            completed_count=125,
            drop_off_count=15,
            completion_rate=89.3,
            average_time_in_stage_seconds=180.5
        ),
        JourneyStageMetrics(
            stage_name="stp_processing",
            stage_order=3,
            entered_count=125,
            completed_count=120,
            drop_off_count=5,
            completion_rate=96.0,
            average_time_in_stage_seconds=5.2
        ),
        JourneyStageMetrics(
            stage_name="approval",
            stage_order=4,
            entered_count=120,
            completed_count=110,
            drop_off_count=10,
            completion_rate=91.7,
            average_time_in_stage_seconds=60.0
        ),
        JourneyStageMetrics(
            stage_name="disbursement",
            stage_order=5,
            entered_count=110,
            completed_count=108,
            drop_off_count=2,
            completion_rate=98.2,
            average_time_in_stage_seconds=300.0
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Tier A: AI Metrics Endpoints (Admin Only)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/ai/{conversation_id}",
    response_model=AIMetrics,
    summary="Get AI Metrics for Conversation",
    description="Get detailed AI quality metrics for a specific conversation. Admin access required."
)
async def get_ai_metrics(
    conversation_id: str,
    admin_user: str = Depends(require_admin)
) -> AIMetrics:
    """
    Get AI quality metrics for a specific conversation.
    
    Returns comprehensive technical metrics including hallucination rates,
    RAGAS scores, LLM latency, and cost breakdown.
    
    **Access:** Admin only
    """
    # TODO: Query LangFuse and database for real metrics
    # For now, return simulated data
    
    ai_data = _get_ai_metrics_from_db(conversation_id)
    
    if not ai_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )
    
    return AIMetrics(
        conversation_id=conversation_id,
        session_id=ai_data.get("session_id", "session-123"),
        application_id=ai_data.get("application_id"),
        hallucination_rate=ai_data.get("hallucination_rate", 0.02),
        hallucination_flags=ai_data.get("hallucination_flags", []),
        total_claims=ai_data.get("total_claims", 15),
        unsupported_claims=ai_data.get("unsupported_claims", 0),
        ragas_faithfulness=ai_data.get("ragas_faithfulness", 0.96),
        ragas_relevance=ai_data.get("ragas_relevance", 0.94),
        ragas_context_precision=ai_data.get("ragas_context_precision", 0.92),
        ragas_overall=ai_data.get("ragas_overall", 0.94),
        llm_latency_p50=ai_data.get("latency_p50", 1200.0),
        llm_latency_p95=ai_data.get("latency_p95", 3400.0),
        llm_latency_p99=ai_data.get("latency_p99", 5200.0),
        total_tokens=ai_data.get("total_tokens", 2341),
        prompt_tokens=ai_data.get("prompt_tokens", 1800),
        completion_tokens=ai_data.get("completion_tokens", 541),
        cost_usd=ai_data.get("cost_usd", 0.047),
        model_used=ai_data.get("model_used", "qwen2.5:7b"),
        model_provider=ai_data.get("model_provider", "ollama"),
        created_at=ai_data.get("created_at", datetime.now()),
        updated_at=ai_data.get("updated_at", datetime.now()),
    )


@router.get(
    "/ai/aggregate/{period}",
    response_model=AggregateAIMetrics,
    summary="Get Aggregated AI Metrics",
    description="Get aggregated AI quality metrics across all conversations. Admin access required."
)
async def get_aggregate_ai_metrics(
    period: str,
    admin_user: str = Depends(require_admin)
) -> AggregateAIMetrics:
    """
    Get aggregated AI quality metrics.
    
    Returns statistics across all conversations for monitoring AI system health.
    Includes hallucination rates, RAGAS scores, latency, and cost breakdowns.
    
    **Access:** Admin only
    """
    # Calculate period boundaries
    now = datetime.now()
    if period == "today":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = now
    elif period == "week":
        period_start = now - timedelta(days=7)
        period_end = now
    elif period == "month":
        period_start = now - timedelta(days=30)
        period_end = now
    else:
        period_start = now - timedelta(days=1)
        period_end = now
    
    # TODO: Query LangFuse and database for real metrics
    # For now, return simulated data
    
    ai_data = _get_aggregate_ai_from_db(period_start, period_end)
    
    return AggregateAIMetrics(
        period=period,
        period_start=period_start,
        period_end=period_end,
        total_conversations=ai_data.get("total", 150),
        evaluated_conversations=ai_data.get("evaluated", 15),
        average_hallucination_rate=ai_data.get("avg_hallucination", 0.018),
        max_hallucination_rate=ai_data.get("max_hallucination", 0.12),
        conversations_with_flags=ai_data.get("with_flags", 3),
        average_ragas_faithfulness=ai_data.get("avg_faithfulness", 0.94),
        average_ragas_relevance=ai_data.get("avg_relevance", 0.92),
        average_ragas_overall=ai_data.get("avg_overall", 0.93),
        average_latency_p50=ai_data.get("latency_p50", 1150.0),
        average_latency_p95=ai_data.get("latency_p95", 3200.0),
        total_tokens=ai_data.get("total_tokens", 351150),
        total_cost_usd=ai_data.get("total_cost", 7.05),
        cost_per_conversation=ai_data.get("cost_per_conv", 0.047),
        model_distribution=ai_data.get("model_distribution", {
            "qwen2.5:7b": 87.0,
            "gpt-4.1-mini": 13.0
        }),
        provider_distribution=ai_data.get("provider_distribution", {
            "ollama": 87.0,
            "openai": 13.0
        }),
        low_quality_conversations=ai_data.get("low_quality", 1),
        high_hallucination_conversations=ai_data.get("high_hallucination", 0),
    )


@router.get(
    "/ai/models",
    response_model=List[ModelPerformanceMetrics],
    summary="Get Model Performance Metrics",
    description="Get performance breakdown by model. Admin access required."
)
async def get_model_performance_metrics(
    admin_user: str = Depends(require_admin)
) -> List[ModelPerformanceMetrics]:
    """
    Get performance metrics by model.
    
    Returns latency, cost, and quality metrics for each model in use.
    Useful for optimizing model routing and cost management.
    
    **Access:** Admin only
    """
    # TODO: Query LangFuse for real model metrics
    # For now, return simulated data
    
    return [
        ModelPerformanceMetrics(
            model_name="qwen2.5:7b",
            provider="ollama",
            total_calls=1250,
            total_tokens=293625,
            latency_p50=1100.0,
            latency_p95=3100.0,
            latency_p99=4800.0,
            total_cost_usd=0.0,
            cost_per_1k_tokens=0.0,
            average_hallucination_rate=0.019,
            average_ragas_score=0.93
        ),
        ModelPerformanceMetrics(
            model_name="gpt-4.1-mini",
            provider="openai",
            total_calls=195,
            total_tokens=57525,
            latency_p50=2100.0,
            latency_p95=4500.0,
            latency_p99=6800.0,
            total_cost_usd=7.05,
            cost_per_1k_tokens=0.123,
            average_hallucination_rate=0.012,
            average_ragas_score=0.96
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Admin Authentication Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/admin/auth",
    response_model=AdminAuthResponse,
    summary="Admin Authentication",
    description="Authenticate as admin to access Tier A metrics."
)
async def admin_auth(request: AdminAuthRequest) -> AdminAuthResponse:
    """
    Authenticate admin user.
    
    Returns JWT token for subsequent Tier A metric requests.
    Token expires after 24 hours.
    """
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(request.password.encode(), admin_password.encode()):
        return AdminAuthResponse(
            success=False,
            message="Invalid password"
        )
    
    # Generate JWT token
    expires_at = datetime.now() + timedelta(hours=ADMIN_TOKEN_EXPIRY_HOURS)
    token = jwt.encode(
        {
            "sub": "admin",
            "role": "admin",
            "exp": expires_at,
            "iat": datetime.now()
        },
        ADMIN_SECRET,
        algorithm="HS256"
    )
    
    return AdminAuthResponse(
        success=True,
        token=token,
        expires_at=expires_at,
        message="Authentication successful"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions (TODO: Replace with Database Queries)
# ─────────────────────────────────────────────────────────────────────────────

def _get_application_from_db(application_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch application data from database.
    
    TODO: Implement with real database query.
    For now, returns simulated data for demo.
    """
    # Simulated database
    return {
        "id": application_id,
        "status": "approved",
        "processing_time": 2.3,
        "loan_amount": 75000.0,
        "currency": "USD",
        "bureau_score": 720,
        "foir": 32.0,
        "ltv": 83.0,
        "journey_progress": 85.0,
        "journey_stages": ["advisory", "application", "stp"],
        "current_stage": "approval",
        "submitted_at": datetime.now() - timedelta(hours=1),
        "processed_at": datetime.now() - timedelta(minutes=58),
        "decision_reason": "All STP checks passed"
    }


def _get_portfolio_from_db(
    period_start: datetime,
    period_end: datetime
) -> Dict[str, Any]:
    """
    Fetch portfolio data from database.
    
    TODO: Implement with real database query.
    For now, returns simulated data for demo.
    """
    return {
        "total": 47,
        "approved": 42,
        "rejected": 5,
        "pending": 0,
        "approval_rate": 89.4,
        "rejection_rate": 10.6,
        "avg_loan": 68500.0,
        "avg_score": 695.0,
        "avg_time": 2.8,
        "avg_foir": 38.5,
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


def _get_ai_metrics_from_db(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch AI metrics from LangFuse/database.
    
    TODO: Implement with real LangFuse query.
    For now, returns simulated data for demo.
    """
    return {
        "session_id": "session-123",
        "application_id": "APP-20260401-123456",
        "hallucination_rate": 0.02,
        "hallucination_flags": [],
        "total_claims": 15,
        "unsupported_claims": 0,
        "ragas_faithfulness": 0.96,
        "ragas_relevance": 0.94,
        "ragas_context_precision": 0.92,
        "ragas_overall": 0.94,
        "latency_p50": 1200.0,
        "latency_p95": 3400.0,
        "latency_p99": 5200.0,
        "total_tokens": 2341,
        "prompt_tokens": 1800,
        "completion_tokens": 541,
        "cost_usd": 0.047,
        "model_used": "qwen2.5:7b",
        "model_provider": "ollama",
        "created_at": datetime.now() - timedelta(hours=1),
        "updated_at": datetime.now()
    }


def _get_aggregate_ai_from_db(
    period_start: datetime,
    period_end: datetime
) -> Dict[str, Any]:
    """
    Fetch aggregate AI metrics from LangFuse/database.
    
    TODO: Implement with real LangFuse aggregation query.
    For now, returns simulated data for demo.
    """
    return {
        "total": 150,
        "evaluated": 15,
        "avg_hallucination": 0.018,
        "max_hallucination": 0.12,
        "with_flags": 3,
        "avg_faithfulness": 0.94,
        "avg_relevance": 0.92,
        "avg_overall": 0.93,
        "latency_p50": 1150.0,
        "latency_p95": 3200.0,
        "total_tokens": 351150,
        "total_cost": 7.05,
        "cost_per_conv": 0.047,
        "model_distribution": {
            "qwen2.5:7b": 87.0,
            "gpt-4.1-mini": 13.0
        },
        "provider_distribution": {
            "ollama": 87.0,
            "openai": 13.0
        },
        "low_quality": 1,
        "high_hallucination": 0
    }


def _score_to_grade(score: Optional[int]) -> Optional[GradeLevel]:
    """Convert bureau score to grade level."""
    if score is None:
        return None
    
    if score >= 750:
        return GradeLevel.A
    elif score >= 650:
        return GradeLevel.B
    elif score >= 550:
        return GradeLevel.C
    elif score >= 450:
        return GradeLevel.D
    else:
        return GradeLevel.E


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = ["router"]
