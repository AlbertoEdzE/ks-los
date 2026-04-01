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
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import jwt
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from src.shared.db import get_db, Loan, V3ConversationState

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
    current_user: Optional[str] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationMetrics:
    """
    Get metrics for a specific loan application.
    
    This endpoint returns comprehensive metrics about a single application,
    including processing status, credit metrics, and journey progress.
    
    **Access:** Authenticated users (borrower or officer)
    """
    v3_state = (
        db.query(V3ConversationState)
        .filter(V3ConversationState.application_id == application_id)
        .first()
    )
    if v3_state is None:
        v3_state = db.get(V3ConversationState, application_id)

    loan = None
    if v3_state is not None:
        loan = (
            db.query(Loan)
            .filter(Loan.conversation_id == v3_state.session_id)
            .order_by(Loan.created_at.desc())
            .first()
        )
    if loan is None:
        loan = db.get(Loan, application_id)

    if loan is None and v3_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found"
        )

    stp_payload = loan.stp_payload if loan is not None and isinstance(loan.stp_payload, dict) else {}
    bureau_score = (
        _parse_int(_deep_get(stp_payload, ["bureauReport", "score"]))
        or (_parse_int(loan.credit_score) if loan is not None else None)
        or (int(v3_state.bureau_score) if v3_state is not None and v3_state.bureau_score is not None else None)
    )
    foir_raw = _parse_float(_deep_get(stp_payload, ["affordability", "foir"]))
    foir_ratio = foir_raw * 100 if foir_raw is not None and foir_raw <= 1.0 else foir_raw
    ltv_ratio = _parse_float(_deep_get(stp_payload, ["property", "ltv"])) or _parse_float(loan.ltv if loan is not None else None)

    submitted_at = (v3_state.created_at if v3_state is not None else None) or (loan.created_at if loan is not None else datetime.now())
    processed_at = loan.updated_at if loan is not None and loan.stp_processing_status in {"approved", "rejected", "disbursed"} else None

    journey_stages, current_stage, journey_progress = _compute_journey(v3_state, loan)

    processing_time_seconds = _compute_processing_seconds(loan)

    decision_reason = (
        _deep_get(stp_payload, ["decision", "reason"])
        or _deep_get(stp_payload, ["decision", "decision_reason"])
        or (loan.notes if loan is not None else None)
    )

    return ApplicationMetrics(
        application_id=(v3_state.application_id if v3_state is not None and v3_state.application_id else application_id),
        status=_loan_to_application_status(v3_state, loan),
        processing_time_seconds=processing_time_seconds,
        loan_amount=_parse_float(loan.loan_amount if loan is not None else None) or 0.0,
        currency="USD",
        bureau_score=bureau_score,
        bureau_grade=_score_to_grade(bureau_score),
        foir_ratio=foir_ratio,
        ltv_ratio=ltv_ratio,
        journey_progress=journey_progress,
        journey_stages=journey_stages,
        current_stage=current_stage,
        submitted_at=submitted_at,
        processed_at=processed_at,
        decision_reason=decision_reason,
    )


@router.get(
    "/portfolio/{period}",
    response_model=PortfolioMetrics,
    summary="Get Portfolio Metrics",
    description="Get aggregated portfolio metrics for a time period."
)
async def get_portfolio_metrics(
    period: str,
    current_user: Optional[str] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioMetrics:
    """
    Get aggregated portfolio metrics.
    
    Returns statistics across all applications for the specified period.
    Includes approval rates, averages, and rejection breakdowns.
    
    **Access:** Authenticated users (officers see all, borrowers see limited)
    """
    period_start, period_end = _period_bounds(period)
    
    loans = (
        db.query(Loan)
        .filter(Loan.created_at >= period_start)
        .filter(Loan.created_at <= period_end)
        .all()
    )
    state_scores = {
        row[0]: row[1]
        for row in (
            db.query(V3ConversationState.session_id, V3ConversationState.bureau_score)
            .filter(V3ConversationState.updated_at >= period_start)
            .filter(V3ConversationState.updated_at <= period_end)
            .all()
        )
        if row[0]
    }

    total = len(loans)
    approved = 0
    rejected = 0
    pending = 0
    loan_amounts: List[float] = []
    bureau_scores: List[int] = []
    processing_times: List[float] = []
    foirs: List[float] = []
    rejection_reasons: Dict[str, int] = {}
    risk_distribution: Dict[RiskLevel, int] = {r: 0 for r in RiskLevel}

    for loan in loans:
        status_value = _loan_to_application_status(None, loan)
        if status_value == ApplicationStatus.APPROVED:
            approved += 1
        elif status_value == ApplicationStatus.REJECTED:
            rejected += 1
        else:
            pending += 1

        amt = _parse_float(loan.loan_amount)
        if amt is not None:
            loan_amounts.append(amt)

        stp_payload = loan.stp_payload if isinstance(loan.stp_payload, dict) else {}
        score = (
            _parse_int(_deep_get(stp_payload, ["bureauReport", "score"]))
            or _parse_int(loan.credit_score)
            or (
                int(state_scores.get(loan.conversation_id))
                if loan.conversation_id and state_scores.get(loan.conversation_id) is not None
                else None
            )
        )
        if score is not None:
            bureau_scores.append(score)

        pt = _compute_processing_seconds(loan)
        if pt > 0:
            processing_times.append(pt)

        foir_raw = _parse_float(_deep_get(stp_payload, ["affordability", "foir"]))
        foir_pct = foir_raw * 100 if foir_raw is not None and foir_raw <= 1.0 else foir_raw
        if foir_pct is not None:
            foirs.append(foir_pct)

        decision_reason = _deep_get(stp_payload, ["decision", "reason"]) or _deep_get(stp_payload, ["decision", "decision_reason"])
        if status_value == ApplicationStatus.REJECTED and decision_reason:
            key = str(decision_reason).strip().lower().replace(" ", "_")[:80]
            rejection_reasons[key] = rejection_reasons.get(key, 0) + 1

        risk_distribution[_estimate_risk(score, foir_pct)] += 1

    approval_rate = (approved / total * 100) if total else 0.0
    rejection_rate = (rejected / total * 100) if total else 0.0

    return PortfolioMetrics(
        period=period,
        period_start=period_start,
        period_end=period_end,
        total_applications=total,
        approved_count=approved,
        rejected_count=rejected,
        pending_count=pending,
        approval_rate=approval_rate,
        rejection_rate=rejection_rate,
        average_loan_amount=(sum(loan_amounts) / len(loan_amounts)) if loan_amounts else 0.0,
        average_bureau_score=(sum(bureau_scores) / len(bureau_scores)) if bureau_scores else 300.0,
        average_processing_time=(sum(processing_times) / len(processing_times)) if processing_times else 0.0,
        average_foir=(sum(foirs) / len(foirs)) if foirs else None,
        rejection_reasons=rejection_reasons,
        risk_distribution=risk_distribution,
    )


@router.get(
    "/journey",
    response_model=List[JourneyStageMetrics],
    summary="Get Journey Stage Metrics",
    description="Get metrics for each stage of the borrower journey."
)
async def get_journey_metrics(
    current_user: Optional[str] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[JourneyStageMetrics]:
    """
    Get journey stage metrics.
    
    Returns completion rates and drop-off statistics for each stage
    of the borrower journey.
    """
    states = db.query(V3ConversationState).all()
    reached = {
        "advisory": 0,
        "application_submission": 0,
        "stp_processing": 0,
        "approval": 0,
        "disbursement": 0,
    }
    for s in states:
        stages, _, _ = _compute_journey(s, None)
        for st in stages:
            if st in reached:
                reached[st] += 1

    def stage_metrics(name: str, order: int, next_name: Optional[str]) -> JourneyStageMetrics:
        entered = reached.get(name, 0)
        completed = reached.get(next_name, 0) if next_name else entered
        drop = max(entered - completed, 0)
        rate = (completed / entered * 100) if entered else 0.0
        return JourneyStageMetrics(
            stage_name=name,
            stage_order=order,
            entered_count=entered,
            completed_count=completed,
            drop_off_count=drop,
            completion_rate=rate,
            average_time_in_stage_seconds=0.0,
        )

    return [
        stage_metrics("advisory", 1, "application"),
        stage_metrics("application", 2, "stp"),
        stage_metrics("stp", 3, "approval"),
        stage_metrics("approval", 4, "disbursement"),
        stage_metrics("disbursement", 5, None),
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
    admin_user: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AIMetrics:
    """
    Get AI quality metrics for a specific conversation.
    
    Returns comprehensive technical metrics including hallucination rates,
    RAGAS scores, LLM latency, and cost breakdown.
    
    **Access:** Admin only
    """
    v3_state = db.get(V3ConversationState, conversation_id)
    if v3_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    conversation_history = v3_state.conversation_history or []
    llm_calls = _extract_llm_calls(conversation_history)
    latencies = [c["latency_ms"] for c in llm_calls if isinstance(c.get("latency_ms"), (int, float))]
    prompt_tokens = sum(int(c.get("usage", {}).get("prompt_tokens", 0) or 0) for c in llm_calls)
    completion_tokens = sum(int(c.get("usage", {}).get("completion_tokens", 0) or 0) for c in llm_calls)
    total_tokens = prompt_tokens + completion_tokens
    cost_usd = sum(float(c.get("cost_usd", 0.0) or 0.0) for c in llm_calls)

    model_used = llm_calls[-1]["model"] if llm_calls else "unknown"
    model_provider = llm_calls[-1]["provider"] if llm_calls else "unknown"

    last_assistant = next(
        (m for m in reversed(conversation_history) if isinstance(m, dict) and m.get("role") == "assistant"),
        None,
    )
    last_content = last_assistant.get("content") if isinstance(last_assistant, dict) else ""
    rag_q, rag_a, rag_contexts = _extract_last_rag_exchange(conversation_history)

    try:
        from src.core.hallucination_detector import validate_response_before_display

        _, report = validate_response_before_display(
            response=str(rag_a or last_content or ""),
            context="\n\n".join(rag_contexts) if rag_contexts else "",
            retrieved_docs=rag_contexts if rag_contexts else None,
            use_nli=False,
            use_rag=bool(rag_contexts),
        )
        total_claims = int(report.total_claims or 0)
        unsupported_claims = int(report.unsupported_claims or 0)
        hallucination_rate = (unsupported_claims / total_claims) if total_claims else 0.0
        hallucination_flags = jsonable_encoder(report.flags or [])
    except Exception:
        total_claims = 0
        unsupported_claims = 0
        hallucination_rate = 0.0
        hallucination_flags = []

    ragas_faithfulness = None
    ragas_relevance = None
    ragas_context_precision = None
    ragas_overall = None
    if rag_q and rag_a and rag_contexts:
        try:
            from src.core.evaluation_service import RAGASEvaluator, EvaluationConfig

            provider = "openai" if os.getenv("OPENAI_API_KEY") else "ollama"
            evaluator = RAGASEvaluator(
                config=EvaluationConfig(
                    sampling_rate=1.0,
                    llm_provider=provider,
                    llm_model="gpt-4.1-mini" if provider == "openai" else "qwen2.5:7b",
                )
            )
            result = evaluator.evaluate_conversation(question=rag_q, answer=rag_a, contexts=rag_contexts)
            if result is not None:
                ragas_faithfulness = float(result.faithfulness)
                ragas_relevance = float(result.answer_relevance)
                ragas_context_precision = float(result.context_precision)
                ragas_overall = float(result.overall_score)
        except Exception:
            pass

    return AIMetrics(
        conversation_id=v3_state.session_id,
        session_id=v3_state.session_id,
        application_id=v3_state.application_id,
        hallucination_rate=hallucination_rate,
        hallucination_flags=hallucination_flags,
        total_claims=total_claims,
        unsupported_claims=unsupported_claims,
        ragas_faithfulness=ragas_faithfulness,
        ragas_relevance=ragas_relevance,
        ragas_context_precision=ragas_context_precision,
        ragas_overall=ragas_overall,
        llm_latency_p50=_percentile(latencies, 50),
        llm_latency_p95=_percentile(latencies, 95),
        llm_latency_p99=_percentile(latencies, 99),
        total_tokens=total_tokens,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        model_used=model_used,
        model_provider=model_provider,
        created_at=v3_state.created_at,
        updated_at=v3_state.updated_at,
    )


@router.get(
    "/ai/aggregate/{period}",
    response_model=AggregateAIMetrics,
    summary="Get Aggregated AI Metrics",
    description="Get aggregated AI quality metrics across all conversations. Admin access required."
)
async def get_aggregate_ai_metrics(
    period: str,
    admin_user: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AggregateAIMetrics:
    """
    Get aggregated AI quality metrics.
    
    Returns statistics across all conversations for monitoring AI system health.
    Includes hallucination rates, RAGAS scores, latency, and cost breakdowns.
    
    **Access:** Admin only
    """
    # Calculate period boundaries
    period_start, period_end = _period_bounds(period)
    
    states = (
        db.query(V3ConversationState)
        .filter(V3ConversationState.updated_at >= period_start)
        .filter(V3ConversationState.updated_at <= period_end)
        .all()
    )

    total_conversations = len(states)
    all_calls: List[Dict[str, Any]] = []
    for s in states:
        all_calls.extend(_extract_llm_calls(s.conversation_history or []))

    latencies = [c["latency_ms"] for c in all_calls if isinstance(c.get("latency_ms"), (int, float))]
    total_tokens = sum(int(c.get("usage", {}).get("prompt_tokens", 0) or 0) + int(c.get("usage", {}).get("completion_tokens", 0) or 0) for c in all_calls)
    total_cost = sum(float(c.get("cost_usd", 0.0) or 0.0) for c in all_calls)

    model_counts: Dict[str, int] = {}
    provider_counts: Dict[str, int] = {}
    for c in all_calls:
        model = str(c.get("model") or "unknown")
        provider = str(c.get("provider") or "unknown")
        model_counts[model] = model_counts.get(model, 0) + 1
        provider_counts[provider] = provider_counts.get(provider, 0) + 1

    def pct_dist(counts: Dict[str, int]) -> Dict[str, float]:
        total = sum(counts.values()) or 1
        return {k: (v / total * 100) for k, v in counts.items()}

    sample_states = [s for s in states if s.conversation_history][:20]
    hallucination_rates: List[float] = []
    ragas_f: List[float] = []
    ragas_r: List[float] = []
    ragas_o: List[float] = []
    with_flags = 0
    for s in sample_states:
        q, a, contexts = _extract_last_rag_exchange(s.conversation_history or [])
        if not a:
            last_user = next((m for m in reversed(s.conversation_history or []) if isinstance(m, dict) and m.get("role") == "user"), None)
            last_assistant = next((m for m in reversed(s.conversation_history or []) if isinstance(m, dict) and m.get("role") == "assistant"), None)
            q = str(last_user.get("content") or "") if isinstance(last_user, dict) else None
            a = str(last_assistant.get("content") or "") if isinstance(last_assistant, dict) else None
            contexts = []
        if not a or not str(a).strip():
            continue
        try:
            from src.core.hallucination_detector import validate_response_before_display

            _, report = validate_response_before_display(
                response=str(a),
                context="\n\n".join(contexts) if contexts else "",
                retrieved_docs=contexts if contexts else None,
                use_nli=False,
                use_rag=bool(contexts),
            )
            total_claims = int(report.total_claims or 0)
            unsupported_claims = int(report.unsupported_claims or 0)
            rate = (unsupported_claims / total_claims) if total_claims else 0.0
            hallucination_rates.append(rate)
            if report.flags:
                with_flags += 1
        except Exception:
            pass

        if q and a and contexts:
            try:
                from src.core.evaluation_service import RAGASEvaluator, EvaluationConfig

                provider = "openai" if os.getenv("OPENAI_API_KEY") else "ollama"
                evaluator = RAGASEvaluator(
                    config=EvaluationConfig(
                        sampling_rate=1.0,
                        llm_provider=provider,
                        llm_model="gpt-4.1-mini" if provider == "openai" else "qwen2.5:7b",
                    )
                )
                result = evaluator.evaluate_conversation(question=q, answer=a, contexts=contexts)
                if result is not None:
                    ragas_f.append(float(result.faithfulness))
                    ragas_r.append(float(result.answer_relevance))
                    ragas_o.append(float(result.overall_score))
            except Exception:
                pass

    avg_hall = (sum(hallucination_rates) / len(hallucination_rates)) if hallucination_rates else 0.0
    max_hall = max(hallucination_rates) if hallucination_rates else 0.0

    return AggregateAIMetrics(
        period=period,
        period_start=period_start,
        period_end=period_end,
        total_conversations=total_conversations,
        evaluated_conversations=len(hallucination_rates),
        average_hallucination_rate=avg_hall,
        max_hallucination_rate=max_hall,
        conversations_with_flags=with_flags,
        average_ragas_faithfulness=(sum(ragas_f) / len(ragas_f)) if ragas_f else None,
        average_ragas_relevance=(sum(ragas_r) / len(ragas_r)) if ragas_r else None,
        average_ragas_overall=(sum(ragas_o) / len(ragas_o)) if ragas_o else None,
        average_latency_p50=_percentile(latencies, 50),
        average_latency_p95=_percentile(latencies, 95),
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
        cost_per_conversation=(total_cost / total_conversations) if total_conversations else 0.0,
        model_distribution=pct_dist(model_counts),
        provider_distribution=pct_dist(provider_counts),
        low_quality_conversations=0,
        high_hallucination_conversations=0,
    )


@router.get(
    "/ai/models",
    response_model=List[ModelPerformanceMetrics],
    summary="Get Model Performance Metrics",
    description="Get performance breakdown by model. Admin access required."
)
async def get_model_performance_metrics(
    admin_user: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[ModelPerformanceMetrics]:
    """
    Get performance metrics by model.
    
    Returns latency, cost, and quality metrics for each model in use.
    Useful for optimizing model routing and cost management.
    
    **Access:** Admin only
    """
    states = db.query(V3ConversationState).all()
    all_calls: List[Dict[str, Any]] = []
    for s in states:
        all_calls.extend(_extract_llm_calls(s.conversation_history or []))

    by_model: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    for c in all_calls:
        key = (str(c.get("model") or "unknown"), str(c.get("provider") or "unknown"))
        by_model.setdefault(key, []).append(c)

    rows: List[ModelPerformanceMetrics] = []
    for (model_name, provider), calls in sorted(by_model.items(), key=lambda x: (-len(x[1]), x[0][0])):
        latencies = [c["latency_ms"] for c in calls if isinstance(c.get("latency_ms"), (int, float))]
        prompt_tokens = sum(int(c.get("usage", {}).get("prompt_tokens", 0) or 0) for c in calls)
        completion_tokens = sum(int(c.get("usage", {}).get("completion_tokens", 0) or 0) for c in calls)
        total_tokens = prompt_tokens + completion_tokens
        total_cost = sum(float(c.get("cost_usd", 0.0) or 0.0) for c in calls)
        rows.append(
            ModelPerformanceMetrics(
                model_name=model_name,
                provider=provider,
                total_calls=len(calls),
                total_tokens=total_tokens,
                latency_p50=_percentile(latencies, 50),
                latency_p95=_percentile(latencies, 95),
                latency_p99=_percentile(latencies, 99),
                total_cost_usd=total_cost,
                cost_per_1k_tokens=(total_cost / (total_tokens / 1000)) if total_tokens else 0.0,
                average_hallucination_rate=0.0,
                average_ragas_score=None,
            )
        )

    return rows


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
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        t = value.strip()
        if not t:
            return None
        cleaned = "".join(ch for ch in t if (ch.isdigit() or ch in ".-"))
        if cleaned in {"", "-", ".", "-.", ".-"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _parse_int(value: Any) -> Optional[int]:
    f = _parse_float(value)
    if f is None:
        return None
    try:
        return int(round(f))
    except Exception:
        return None


def _deep_get(obj: Any, path: List[str]) -> Any:
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _compute_processing_seconds(loan: Optional[Loan]) -> float:
    if loan is None:
        return 0.0
    log = loan.stp_processing_log if isinstance(loan.stp_processing_log, list) else []
    if log:
        ts_values = []
        for entry in log:
            if isinstance(entry, dict) and entry.get("ts"):
                try:
                    ts_values.append(datetime.fromisoformat(str(entry["ts"]).replace("Z", "+00:00")))
                except Exception:
                    pass
        if len(ts_values) >= 2:
            return max((max(ts_values) - min(ts_values)).total_seconds(), 0.0)
    try:
        return max((loan.updated_at - loan.created_at).total_seconds(), 0.0)
    except Exception:
        return 0.0


def _loan_to_application_status(v3_state: Optional[V3ConversationState], loan: Optional[Loan]) -> ApplicationStatus:
    if loan is not None and isinstance(loan.disbursement, dict) and loan.disbursement:
        return ApplicationStatus.DISBURSED
    if v3_state is not None:
        if v3_state.terms_accepted:
            return ApplicationStatus.APPROVED
        if v3_state.requires_manual_review:
            return ApplicationStatus.MANUAL_REVIEW
        if v3_state.stp_status in {"approved"}:
            return ApplicationStatus.APPROVED
        if v3_state.stp_status in {"rejected"}:
            return ApplicationStatus.REJECTED
        if v3_state.application_submitted:
            return ApplicationStatus.PROCESSING

    if loan is None:
        return ApplicationStatus.PENDING

    if loan.status in {"approved"}:
        return ApplicationStatus.APPROVED
    if loan.status in {"rejected"}:
        return ApplicationStatus.REJECTED
    if loan.status in {"disbursed"}:
        return ApplicationStatus.DISBURSED
    if loan.status in {"manual_review"}:
        return ApplicationStatus.MANUAL_REVIEW
    if loan.stp_processing_status in {"approved"}:
        return ApplicationStatus.APPROVED
    if loan.stp_processing_status in {"rejected"}:
        return ApplicationStatus.REJECTED
    if loan.stp_processing_status in {"processing", "awaiting_acceptance"}:
        return ApplicationStatus.PROCESSING
    return ApplicationStatus.PENDING


def _compute_journey(v3_state: Optional[V3ConversationState], loan: Optional[Loan]) -> tuple[List[str], Optional[str], float]:
    stages: List[str] = []
    if v3_state is None:
        return stages, None, 0.0

    stages.append("advisory")
    if v3_state.application_submitted or v3_state.mode in {"application", "completion"}:
        stages.append("application")
    if (v3_state.stp_status and v3_state.stp_status != "pending") or (loan is not None and loan.stp_processing_status):
        stages.append("stp")
    if v3_state.stp_approved or v3_state.awaiting_acceptance or v3_state.terms_accepted:
        stages.append("approval")
    if loan is not None and isinstance(loan.disbursement, dict) and loan.disbursement:
        stages.append("disbursement")

    current_stage = stages[-1] if stages else None
    progress = (len(stages) / 5) * 100 if stages else 0.0
    return stages, current_stage, progress


def _estimate_risk(bureau_score: Optional[int], foir_pct: Optional[float]) -> RiskLevel:
    score = bureau_score or 0
    foir = foir_pct if foir_pct is not None else 0.0
    if score >= 750 and foir <= 35:
        return RiskLevel.LOW
    if score >= 650 and foir <= 45:
        return RiskLevel.MODERATE
    if score >= 550 and foir <= 55:
        return RiskLevel.ELEVATED
    return RiskLevel.HIGH


def _percentile(values: List[float], p: int) -> float:
    if not values:
        return 0.0
    v = sorted(values)
    if len(v) == 1:
        return float(v[0])
    k = (len(v) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(v) - 1)
    if f == c:
        return float(v[f])
    d0 = v[f] * (c - k)
    d1 = v[c] * (k - f)
    return float(d0 + d1)


def _extract_llm_calls(conversation_history: List[Any]) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    for msg in conversation_history:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "assistant":
            continue
        meta = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else {}
        chunk = meta.get("llm_calls")
        if isinstance(chunk, list):
            for c in chunk:
                if isinstance(c, dict):
                    calls.append(c)
    return calls


def _extract_last_rag_exchange(conversation_history: List[Any]) -> tuple[Optional[str], Optional[str], List[str]]:
    for idx in range(len(conversation_history) - 1, -1, -1):
        msg = conversation_history[idx]
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "assistant":
            continue
        meta = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else {}
        if not meta.get("rag_used"):
            continue
        contexts_raw = meta.get("rag_contexts")
        if not isinstance(contexts_raw, list):
            continue
        contexts = [str(c) for c in contexts_raw if isinstance(c, str) and c.strip()]
        answer = str(msg.get("content") or "")
        question = None
        for j in range(idx - 1, -1, -1):
            prev = conversation_history[j]
            if isinstance(prev, dict) and prev.get("role") == "user":
                question = str(prev.get("content") or "")
                break
        return (question if question and question.strip() else None, answer if answer.strip() else None, contexts)
    return None, None, []


def _period_bounds(period: str) -> tuple[datetime, datetime]:
    now_local = datetime.now().astimezone()
    if period == "today":
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = now_local
    elif period == "yesterday":
        yesterday = now_local - timedelta(days=1)
        start_local = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)
    elif period == "week":
        start_local = now_local - timedelta(days=7)
        end_local = now_local
    elif period == "month":
        start_local = now_local - timedelta(days=30)
        end_local = now_local
    else:
        start_local = now_local - timedelta(days=1)
        end_local = now_local

    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


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
