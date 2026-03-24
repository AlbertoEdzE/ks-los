from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from src.shared.types import ApplicantCreditProfile


class CalculatedMetrics(TypedDict, total=False):
    """
    Deterministic metrics from calculation engines.
    All values computed by Python engines (no LLM involvement).
    """
    # EMI calculation
    emi: Optional[float]
    total_interest: Optional[float]
    total_repayment: Optional[float]
    
    # Affordability
    foir: Optional[float]  # Fixed Obligation to Income Ratio
    dti: Optional[float]   # Debt-to-Income ratio
    dscr: Optional[float]  # Debt Service Coverage Ratio
    income_stability: Optional[str]  # strong/moderate/weak/unknown
    
    # Collateral
    ltv: Optional[float]   # Loan-to-Value ratio
    
    # Credit risk
    approval_probability: Optional[int]  # 0-100
    risk_grade: Optional[str]  # A/B/C/D/E
    
    # APR
    apr: Optional[float]   # Annual Percentage Rate
    
    # STP
    stp_tier: Optional[str]  # stp/referred/committee
    stp_reasons: Optional[List[str]]


class AgentState(TypedDict):
    """
    The state of the agent workflow.
    
    Enhanced with deterministic calculation metrics from Task 1 engines.
    """
    messages: Annotated[List[Any], add_messages]
    applicant_id: Optional[str]
    credit_profile: Optional[ApplicantCreditProfile]

    # Calculation Engine Outputs (Task 1)
    calculated_metrics: Optional[CalculatedMetrics]

    # Risk Engine Outputs
    risk_score: Optional[float]
    risk_decision: Optional[str]  # APPROVED, DECLINED, MANUAL_REVIEW
    risk_reasoning: Optional[str]

    # Advisory Output
    advice: Optional[str]
    next_step: Optional[str]

    # Context data
    user_input: Optional[str]
    session_id: Optional[str]
