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
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from src.agents.orchestrator import (
    CapturedContext,
    LoanSnapshot,
    LoanRecommendation,
    DocumentsChecklist,
    STPCheckpoint,
)
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
        """Check if ready to proceed to application mode"""
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
    "AgenticOrchestratorState",
    
    # Factory
    "create_initial_state",
]
