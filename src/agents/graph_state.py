"""
Agentic Orchestrator State Schema for KS-LOS v3.0

Complete state management for LLM-driven agentic borrower journey.
Replaces the deterministic state machine with flexible agentic state.

State Architecture:
┌─────────────────────────────────────────────────────────────┐
│              AgenticOrchestratorState                        │
├─────────────────────────────────────────────────────────────┤
│  Conversation State                                          │
│  - mode: advisory/application/completion                     │
│  - history: List[Message]                                    │
│  - current_stage: str                                        │
├─────────────────────────────────────────────────────────────┤
│  Borrower Context                                            │
│  - captured_context: CapturedContext                         │
│  - intent_analysis: IntentAnalysis                           │
│  - confidence_scores: Dict[str, float]                       │
├─────────────────────────────────────────────────────────────┤
│  Loan Details                                                │
│  - snapshot: LoanSnapshot                                    │
│  - recommendations: List[LoanRecommendation]                 │
│  - selected_option: Optional[LoanRecommendation]             │
├─────────────────────────────────────────────────────────────┤
│  Documents                                                   │
│  - checklist: DocumentsChecklist                             │
│  - uploaded: List[DocumentWithExtraction]                    │
│  - extraction_results: List[ExtractionResult]                │
├─────────────────────────────────────────────────────────────┤
│  STP Processing                                              │
│  - checkpoints: List[STPCheckpoint]                          │
│  - status: pending/processing/approved/disbursed             │
│  - bureau_score: Optional[int]                               │
├─────────────────────────────────────────────────────────────┤
│  Phase Progression                                           │
│  - current_phase_id: str                                     │
│  - phase_history: List[PhaseTransition]                      │
├─────────────────────────────────────────────────────────────┤
│  Flags & Alerts                                              │
│  - discrepancies: List[DiscrepancyFlag]                      │
│  - requires_review: bool                                     │
│  - escalation_needed: bool                                   │
└─────────────────────────────────────────────────────────────┘
"""

from typing import Dict, List, Any, Optional, Literal
import re
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum

from src.agents.structured_parser import IntentAnalysis
from src.core.document_intelligence import DocumentExtractionResult


# ─────────────────────────────────────────────────────────────────────────────
# Conversation Mode Enumeration
# ─────────────────────────────────────────────────────────────────────────────

class ConversationMode(str, Enum):
    """Agentic conversation modes (LNAI-style)"""
    ADVISORY = "advisory"  # Understanding & estimation
    APPLICATION = "application"  # Collecting details & submission
    COMPLETION = "completion"  # Post-submission (STP, acceptance, disbursement)


# ─────────────────────────────────────────────────────────────────────────────
# Message Schema
# ─────────────────────────────────────────────────────────────────────────────

class Message(BaseModel):
    """Single conversation message"""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Phase Transition Schema
# ─────────────────────────────────────────────────────────────────────────────

class PhaseTransition(BaseModel):
    """Records phase progression"""
    from_phase_id: Optional[str] = None
    to_phase_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    reason: str
    triggered_by: str  # "user_action", "agent_decision", "system"


# ─────────────────────────────────────────────────────────────────────────────
# Document with Extraction Result
# ─────────────────────────────────────────────────────────────────────────────

class DocumentWithExtraction(BaseModel):
    """Uploaded document with OCR extraction result"""
    document_id: str
    file_name: str
    category: str  # identity, income, property, etc.
    upload_timestamp: datetime
    extraction_result: Optional[DocumentExtractionResult] = None
    reviewed: bool = False
    review_notes: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Discrepancy Flag
# ─────────────────────────────────────────────────────────────────────────────

class DiscrepancyFlag(BaseModel):
    """Discrepancy between declared and extracted data"""
    field_name: str
    declared_value: Any
    extracted_value: Any
    variance_percent: float
    severity: Literal["low", "medium", "high"]
    recommendation: str
    resolved: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Core Domain Models (V3)
# ─────────────────────────────────────────────────────────────────────────────

class CapturedContext(BaseModel):
    purpose: Optional[str] = None
    property_value: Optional[float] = None
    property_currency: str = "USD"
    loan_amount: Optional[float] = None
    down_payment: Optional[float] = None
    down_payment_currency: str = "USD"
    employment_type: Optional[str] = None
    monthly_income: Optional[float] = None
    income_currency: str = "USD"
    existing_debts: Optional[float] = None
    loan_tenure_years: Optional[int] = None
    preferred_term: Optional[str] = None
    credit_score: Optional[int] = None
    credit_history: Optional[str] = None
    has_existing_debts: Optional[bool] = None
    property_location: Optional[str] = None
    borrower_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    urgency: Optional[Literal["low", "medium", "high", "critical"]] = None
    affordability: Optional[str] = None
    preferred_tenure: Optional[str] = None
    collateral_available: Optional[str] = None
    seriousness_score: Optional[int] = None
    fit_score: Optional[int] = None

    @field_validator(
        "property_value",
        "loan_amount",
        "down_payment",
        "monthly_income",
        "existing_debts",
        mode="before",
    )
    @classmethod
    def _coerce_numeric_money_fields(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            t = v.strip()
            if not t:
                return None
            cleaned = re.sub(r"[^\d.\-]", "", t.replace(",", ""))
            if cleaned in {"", "-", ".", "-.", ".-"}:
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return v

    @field_validator("loan_tenure_years", mode="before")
    @classmethod
    def _coerce_tenure_years(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        if isinstance(v, str):
            m = re.search(r"\d+", v)
            return int(m.group(0)) if m else None
        return v

    @field_validator("credit_score", mode="before")
    @classmethod
    def _coerce_credit_score(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        if isinstance(v, str):
            m = re.search(r"\d{3}", v)
            return int(m.group(0)) if m else None
        return v


class LoanSnapshot(BaseModel):
    loan_amount: float
    down_payment: float
    property_value: float
    estimated_emi: float
    tenure_years: int
    interest_rate: float
    total_interest: float
    total_repayment: float
    ltv_ratio: float
    foir_ratio: Optional[float] = None
    currency: str = "USD"


class LoanRecommendation(BaseModel):
    name: str
    type: Literal["aggressive", "balanced", "conservative"]
    interest_rate: float
    tenure_years: int
    monthly_emi: float
    total_interest: float
    total_repayment: float
    pros: List[str]
    cons: List[str]
    recommended: bool = False


class DocumentsChecklist(BaseModel):
    identity: List[Dict[str, Any]] = Field(default_factory=list)
    income: List[Dict[str, Any]] = Field(default_factory=list)
    business: List[Dict[str, Any]] = Field(default_factory=list)
    property: List[Dict[str, Any]] = Field(default_factory=list)
    vehicle: List[Dict[str, Any]] = Field(default_factory=list)


class STPCheckpoint(BaseModel):
    name: str
    status: Literal["pending", "processing", "passed", "failed"] = "pending"
    details: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Main Agentic State
# ─────────────────────────────────────────────────────────────────────────────

class AgenticOrchestratorState(BaseModel):
    """
    Complete state for agentic borrower journey.
    
    This state schema supports:
    - LLM-driven conversation flow
    - Confidence-based decision making
    - Document intelligence integration
    - STP processing tracking
    - Phase progression
    - Discrepancy management
    - Escalation handling
    
    Usage:
        state = AgenticOrchestratorState(
            session_id="session-123",
            mode=ConversationMode.ADVISORY
        )
        
        # Update state during conversation
        state.captured_context.purpose = "home_purchase"
        state.confidence_scores["purpose"] = 0.95
    """
    
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}
    
    # ──────────────────────────────────────────────────────────────────────
    # Core State
    # ──────────────────────────────────────────────────────────────────────
    
    session_id: str = Field(..., description="Unique session identifier")
    mode: ConversationMode = ConversationMode.ADVISORY
    current_stage: str = "intent_capture"
    
    # ──────────────────────────────────────────────────────────────────────
    # Conversation History
    # ──────────────────────────────────────────────────────────────────────
    
    conversation_history: List[Message] = Field(
        default_factory=list,
        description="Full conversation history"
    )
    
    # ──────────────────────────────────────────────────────────────────────
    # Borrower Context
    # ──────────────────────────────────────────────────────────────────────
    
    captured_context: CapturedContext = Field(
        default_factory=CapturedContext,
        description="Extracted borrower information"
    )
    
    intent_analysis: Optional[IntentAnalysis] = Field(
        default=None,
        description="LLM-extracted intent analysis"
    )
    
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-field confidence scores (0-1)"
    )
    
    # ──────────────────────────────────────────────────────────────────────
    # Loan Details
    # ──────────────────────────────────────────────────────────────────────
    
    loan_snapshot: Optional[LoanSnapshot] = Field(
        default=None,
        description="Computed loan metrics"
    )
    
    recommendations: List[LoanRecommendation] = Field(
        default_factory=list,
        description="Loan product recommendations"
    )
    
    selected_recommendation: Optional[LoanRecommendation] = Field(
        default=None,
        description="Borrower's selected option"
    )
    
    # ──────────────────────────────────────────────────────────────────────
    # Documents
    # ──────────────────────────────────────────────────────────────────────
    
    documents_checklist: Optional[DocumentsChecklist] = Field(
        default=None,
        description="Required documents checklist"
    )
    
    uploaded_documents: List[DocumentWithExtraction] = Field(
        default_factory=list,
        description="Uploaded documents with extraction results"
    )
    
    # ──────────────────────────────────────────────────────────────────────
    # STP Processing
    # ──────────────────────────────────────────────────────────────────────
    
    stp_checkpoints: List[STPCheckpoint] = Field(
        default_factory=list,
        description="STP checkpoint progress"
    )
    
    stp_status: Literal["pending", "processing", "approved", "disbursed", "rejected"] = "pending"
    
    bureau_score: Optional[int] = Field(
        default=None,
        description="Credit bureau score"
    )
    
    stp_approved: bool = False
    awaiting_acceptance: bool = False
    terms_accepted: bool = False
    
    # ──────────────────────────────────────────────────────────────────────
    # Phase Progression
    # ──────────────────────────────────────────────────────────────────────
    
    current_phase_id: Optional[str] = Field(
        default=None,
        description="Current loan lifecycle phase"
    )
    
    phase_history: List[PhaseTransition] = Field(
        default_factory=list,
        description="History of phase transitions"
    )
    
    # ──────────────────────────────────────────────────────────────────────
    # Flags & Alerts
    # ──────────────────────────────────────────────────────────────────────
    
    discrepancy_flags: List[DiscrepancyFlag] = Field(
        default_factory=list,
        description="Data discrepancy flags"
    )
    
    requires_manual_review: bool = Field(
        default=False,
        description="True if manual review required"
    )
    
    escalation_needed: bool = Field(
        default=False,
        description="True if escalation to officer needed"
    )
    
    # ──────────────────────────────────────────────────────────────────────
    # Application State
    # ──────────────────────────────────────────────────────────────────────
    
    application_id: Optional[str] = Field(
        default=None,
        description="Loan application ID"
    )
    
    application_submitted: bool = False
    
    # ──────────────────────────────────────────────────────────────────────
    # Metrics & Tracking
    # ──────────────────────────────────────────────────────────────────────
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # ──────────────────────────────────────────────────────────────────────
    # Helper Methods
    # ──────────────────────────────────────────────────────────────────────
    
    def get_confidence(self, field_name: str) -> float:
        """Get confidence score for specific field"""
        return self.confidence_scores.get(field_name, 0.5)
    
    def get_average_confidence(self) -> float:
        """Get average confidence across all fields"""
        if not self.confidence_scores:
            return 0.5
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)
    
    def is_field_reliable(self, field_name: str, threshold: float = 0.7) -> bool:
        """Check if field extraction is reliable"""
        return self.get_confidence(field_name) >= threshold
    
    def has_high_severity_flags(self) -> bool:
        """Check if any high-severity discrepancy flags exist"""
        return any(flag.severity == "high" for flag in self.discrepancy_flags)
    
    def needs_escalation(self) -> bool:
        """Check if escalation is needed"""
        return (
            self.escalation_needed or
            self.has_high_severity_flags() or
            self.get_average_confidence() < 0.3
        )
    
    def can_proceed_to_application(self) -> bool:
        """
        Check if ready to proceed to application mode.
        
        Scientific Design:
        - All required fields must be captured with high confidence
        - borrower_name is CRITICAL - must be captured before application mode
        - This ensures the agent completes Step 1 (Understand need: purpose + name)
          before moving to Step 2 (Employment & income)
        
        Required Fields (per LNAI design doc):
        1. purpose - Loan purpose (home, auto, personal, etc.)
        2. borrower_name - Full legal name (CRITICAL for application)
        3. loan_amount - Amount requested
        4. monthly_income - Income for affordability
        5. employment_type - Employment status for risk assessment
        
        Returns:
            True if all fields are reliable (confidence >= 0.7)
        """
        required_fields = [
            "purpose",
            "loan_amount",
            "monthly_income",
            "employment_type",
        ]

        # All required fields must be reliable
        for field in required_fields:
            if not self.is_field_reliable(field, threshold=0.7):
                return False

        return True
    
    def can_trigger_stp(self) -> bool:
        """Check if STP can be triggered"""
        return (
            self.application_submitted and
            len(self.uploaded_documents) >= 2 and  # ID + income proof
            not self.has_high_severity_flags()
        )
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to conversation history"""
        self.conversation_history.append(
            Message(
                role=role,
                content=content,
                metadata=metadata or {}
            )
        )
        self.update_timestamp()
    
    def transition_phase(self, to_phase_id: str, reason: str, triggered_by: str = "agent_decision"):
        """Record phase transition"""
        self.phase_history.append(
            PhaseTransition(
                from_phase_id=self.current_phase_id,
                to_phase_id=to_phase_id,
                reason=reason,
                triggered_by=triggered_by
            )
        )
        self.current_phase_id = to_phase_id
        self.update_timestamp()


# ─────────────────────────────────────────────────────────────────────────────
# State Factory
# ─────────────────────────────────────────────────────────────────────────────

def create_initial_state(session_id: str) -> AgenticOrchestratorState:
    """
    Create initial agentic state for new conversation.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        Initialized AgenticOrchestratorState
    """
    return AgenticOrchestratorState(
        session_id=session_id,
        mode=ConversationMode.ADVISORY,
        current_stage="intent_capture",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Enums
    "ConversationMode",
    
    # State models
    "Message",
    "PhaseTransition",
    "DocumentWithExtraction",
    "DiscrepancyFlag",
    "CapturedContext",
    "LoanSnapshot",
    "LoanRecommendation",
    "DocumentsChecklist",
    "STPCheckpoint",
    "AgenticOrchestratorState",
    
    # Factory
    "create_initial_state",
]
