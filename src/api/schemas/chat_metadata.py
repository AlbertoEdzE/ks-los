"""
Borrower Chat Metadata Schema.

This module defines strict, validated schemas for all metadata exchanged
between the agentic backend and the borrower frontend.

Purpose:
- Prevent hallucination of UI-critical fields
- Ensure type safety across API boundaries
- Enable schema versioning and backward compatibility
- Support golden test datasets for regression testing

All schemas use Pydantic v2 for validation.
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


# =============================================================================
# Intent Analysis Schema
# =============================================================================

class IntentAnalysis(BaseModel):
    """
    Extracted intent from borrower conversation.
    
    Populated by profile_parser_node after each user message.
    Used by ApplicationReadinessPanel to show progress.
    """
    model_config = ConfigDict(extra='forbid', populate_by_name=True)  # Allow both snake and alias
    
    # Core loan details
    purpose: Optional[str] = Field(
        default=None,
        description="Loan purpose (e.g., 'Home purchase', 'Vehicle', 'Debt consolidation')"
    )
    urgency: Optional[Literal["low", "medium", "high", "critical"]] = Field(
        default=None,
        description="Borrower's urgency level"
    )
    affordability: Optional[str] = Field(
        default=None,
        description="Affordability assessment (e.g., 'Moderate - monthly income around $8,000')"
    )
    
    # Financial details
    monthly_income: Optional[str] = Field(
        default=None,
        alias="monthlyIncome",
        description="Monthly income with currency (e.g., '$8,000', 'XCD 6,000')"
    )
    existing_debts: Optional[str] = Field(
        default=None,
        alias="existingDebts",
        description="Existing monthly obligations (e.g., 'Car loan $1,200/month')"
    )
    loan_amount: Optional[str] = Field(
        default=None,
        alias="loanAmount",
        description="Requested loan amount with currency"
    )
    preferred_tenure: Optional[str] = Field(
        default=None,
        alias="preferredTenure",
        description="Preferred loan tenure (e.g., '20 years')"
    )
    collateral_available: Optional[str] = Field(
        default=None,
        alias="collateralAvailable",
        description="Available collateral (e.g., 'Property in Saint Lucia')"
    )
    
    # Employment
    employment_type: Optional[str] = Field(
        default=None,
        alias="employmentType",
        description="Employment status (e.g., 'Salaried', 'Self-employed')"
    )
    credit_history: Optional[str] = Field(
        default=None,
        alias="creditHistory",
        description="Credit history summary (e.g., 'Good', 'Thin file')"
    )
    
    # Identity (for application submission)
    first_name: Optional[str] = Field(
        default=None,
        alias="firstName"
    )
    last_name: Optional[str] = Field(
        default=None,
        alias="lastName"
    )
    email: Optional[str] = Field(
        default=None,
        description="Email address"
    )
    phone: Optional[str] = Field(
        default=None,
        description="Phone number"
    )
    
    # AI-derived scores
    seriousness_score: Optional[int] = Field(
        default=None,
        alias="seriousnessScore",
        ge=0,
        le=100,
        description="How ready is this borrower? (0-100)"
    )
    fit_score: Optional[int] = Field(
        default=None,
        alias="fitScore",
        ge=0,
        le=100,
        description="How well can we serve them? (0-100)"
    )
    
    # Next action
    next_conversation_angle: Optional[str] = Field(
        default=None,
        alias="nextConversationAngle",
        description="What should a loan officer focus on?"
    )
    
    @field_validator('purpose', 'affordability', mode='before')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from string fields."""
        return v.strip() if v and isinstance(v, str) else v


# =============================================================================
# Loan Recommendation Schema
# =============================================================================

class LoanRecommendation(BaseModel):
    """
    Single loan product recommendation.
    
    Must be derived from catalog products (not hardcoded).
    Displayed in ChatBubble as recommendation cards.
    """
    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    
    product_id: str = Field(
        alias="productId",
        description="Product ID from catalog"
    )
    product_name: str = Field(
        alias="productName",
        description="Product display name"
    )
    product_code: Optional[str] = Field(
        default=None,
        alias="productCode",
        description="Product code (e.g., 'HL-PUR-001')"
    )
    category: Optional[str] = Field(
        default=None,
        description="Product category (e.g., 'Home Loan', 'Vehicle Loan')"
    )
    
    # Financial terms
    estimated_rate: Optional[str] = Field(
        default=None,
        alias="estimatedRate",
        description="Interest rate range (e.g., '8.40% - 9.5%')"
    )
    estimated_emi: Optional[str] = Field(
        default=None,
        alias="estimatedEmi",
        description="Estimated monthly EMI (e.g., '$5,200/month')"
    )
    tenure: Optional[str] = Field(
        default=None,
        description="Loan tenure (e.g., '15 years', '180 months')"
    )
    total_interest: Optional[str] = Field(
        default=None,
        alias="totalInterest",
        description="Total interest payable (e.g., '$436,000')"
    )
    
    # Approval
    approval_speed: Optional[str] = Field(
        default=None,
        alias="approvalSpeed",
        description="Expected approval timeline (e.g., '5-7 business days')"
    )
    
    # Trade-offs
    pros: List[str] = Field(
        default_factory=list,
        description="Product advantages"
    )
    cons: List[str] = Field(
        default_factory=list,
        description="Product disadvantages"
    )
    recommendation: str = Field(
        description="Why this product is recommended"
    )
    
    @field_validator('pros', 'cons', mode='before')
    @classmethod
    def ensure_list(cls, v):
        """Ensure pros/cons are lists."""
        return v if isinstance(v, list) else []


# =============================================================================
# Documents Checklist Schema
# =============================================================================

class DocumentRequirement(BaseModel):
    """
    Single document requirement.
    
    Displayed in ChatBubble as checklist card.
    """
    model_config = ConfigDict(extra='forbid')
    
    name: str = Field(
        description="Document name (e.g., 'Valid National ID or Passport')"
    )
    description: str = Field(
        description="Document description (e.g., 'Government-issued photo ID')"
    )
    category: Optional[Literal["identity", "income", "employment", "property", "other"]] = Field(
        default="other",
        description="Document category for grouping"
    )
    required: bool = Field(
        default=True,
        description="Whether this document is mandatory"
    )


class DocumentsChecklist(BaseModel):
    """
    Complete documents checklist.
    
    Populated based on loan type and employment type.
    """
    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    
    required_now: List[DocumentRequirement] = Field(
        alias="requiredNow",
        description="Documents needed immediately"
    )
    likely_later: Optional[List[DocumentRequirement]] = Field(
        default=None,
        alias="likelyLater",
        description="Documents that may be needed later"
    )
    if_applicable: Optional[List[DocumentRequirement]] = Field(
        default=None,
        alias="ifApplicable",
        description="Conditional documents (e.g., for self-employed)"
    )


# =============================================================================
# Loan Application Result Schema
# =============================================================================

class LoanApplicationResult(BaseModel):
    """
    Result of loan application submission.
    
    Displayed in ChatBubble as success/failure card.
    """
    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    
    success: bool = Field(
        description="Whether submission was successful"
    )
    loan_id: Optional[str] = Field(
        default=None,
        alias="loanId",
        description="Assigned loan ID"
    )
    message: str = Field(
        description="User-facing message"
    )
    approval_tier: Optional[Literal["stp", "referred", "committee"]] = Field(
        default=None,
        alias="approvalTier",
        description="Approval tier (STP = Straight-Through Processing)"
    )
    
    # STP-specific fields
    stp_approved: Optional[bool] = Field(
        default=None,
        alias="stpApproved",
        description="Whether STP approved"
    )
    awaiting_acceptance: Optional[bool] = Field(
        default=None,
        alias="awaitingAcceptance",
        description="Whether awaiting borrower acceptance"
    )
    stp_completed: Optional[bool] = Field(
        default=None,
        alias="stpCompleted",
        description="Whether STP completed with disbursement"
    )
    referral_reason: Optional[str] = Field(
        default=None,
        alias="referralReason",
        description="Reason for referral (if referred)"
    )
    
    # Bureau report (if pulled)
    bureau_report: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Credit bureau report summary"
    )
    
    # Affordability analysis
    affordability: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Affordability analysis result"
    )
    
    # Liability comparison
    liability_comparison: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="liabilityComparison",
        description="Liability comparison analysis"
    )
    
    # STP steps
    stp_steps: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="STP checkpoint progress"
    )
    
    # Approval details
    approval: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Approval terms (rate, tenure, EMI)"
    )
    
    # Audit
    audit: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Audit trail metadata"
    )


# =============================================================================
# Phase Action Schema
# =============================================================================

class PhaseAction(BaseModel):
    """
    Phase progression action.
    
    Triggered when borrower advances to next phase.
    """
    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    
    type: Literal["advance_phase", "stay_phase"] = Field(
        description="Action type"
    )
    phase_id: Optional[str] = Field(
        default=None,
        alias="phaseId",
        description="Target phase ID (for advance_phase)"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for phase change"
    )


# =============================================================================
# Loan Snapshot Schema
# =============================================================================

class LoanSnapshot(BaseModel):
    """
    Loan snapshot for display.
    
    Shows understood requirements back to borrower.
    """
    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    
    loan_type: str = Field(
        alias="loanType",
        description="Type of loan"
    )
    loan_amount: str = Field(
        alias="loanAmount",
        description="Requested amount with currency"
    )
    estimated_emi: Optional[str] = Field(
        default=None,
        alias="estimatedEmi",
        description="Estimated monthly EMI range"
    )
    tenure: Optional[str] = Field(
        default=None,
        description="Loan tenure"
    )
    rate_band: Optional[str] = Field(
        default=None,
        alias="rateBand",
        description="Interest rate band"
    )
    down_payment: Optional[str] = Field(
        default=None,
        alias="downPayment",
        description="Down payment amount"
    )
    asset_price: Optional[str] = Field(
        default=None,
        alias="assetPrice",
        description="Total asset price (for vehicle/home loans)"
    )


# =============================================================================
# Assistant Response Metadata (Complete)
# =============================================================================

class AssistantResponseMetadata(BaseModel):
    """
    Complete metadata structure for assistant messages.
    
    This is the contract between backend and frontend.
    All fields are optional except those required for specific UI panels.
    """
    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    
    # Intent analysis (always populated)
    intent_analysis: Optional[IntentAnalysis] = Field(
        default=None,
        alias="intentAnalysis"
    )
    
    # Recommendations (populated when showing products)
    loan_recommendations: Optional[List[LoanRecommendation]] = Field(
        default=None,
        alias="loanRecommendations"
    )
    
    # Documents checklist (populated after application submission)
    documents_checklist: Optional[DocumentsChecklist] = Field(
        default=None,
        alias="documentsChecklist"
    )
    
    # Loan application result (populated on submission)
    loan_application: Optional[LoanApplicationResult] = Field(
        default=None,
        alias="loanApplication"
    )
    
    # Phase action (populated when advancing phases)
    phase_action: Optional[PhaseAction] = Field(
        default=None,
        alias="phaseAction"
    )
    
    # Loan snapshot (populated during advisory)
    loan_snapshot: Optional[LoanSnapshot] = Field(
        default=None,
        alias="loanSnapshot"
    )
    
    # Calculated metrics (from Task 3)
    calculated_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="calculatedMetrics",
        description="Deterministic metrics from calculation engines"
    )
    
    # Product cards (for officer chat)
    product_cards: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        alias="productCards",
        description="Matched products for officer queries"
    )
    
    # Actor role (for filtering)
    actor_role: Optional[Literal["borrower", "officer", "officer_assistant"]] = Field(
        default=None,
        alias="actorRole",
        description="Which actor this message is for"
    )
    
    # Timestamp
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message timestamp"
    )


# =============================================================================
# Validation Helper Functions
# =============================================================================

def validate_metadata(metadata: Dict[str, Any]) -> AssistantResponseMetadata:
    """
    Validate and normalize metadata dictionary.
    
    Args:
        metadata: Raw metadata dictionary from agent
        
    Returns:
        Validated AssistantResponseMetadata object
        
    Raises:
        ValidationError: If metadata doesn't match schema
    """
    return AssistantResponseMetadata.model_validate(metadata)


def metadata_to_dict(metadata: AssistantResponseMetadata) -> Dict[str, Any]:
    """
    Convert metadata to JSON-serializable dictionary.
    
    Args:
        metadata: Validated metadata object
        
    Returns:
        Dictionary ready for JSON serialization
    """
    return metadata.model_dump(by_alias=True, exclude_none=True)


# =============================================================================
# Schema Versioning
# =============================================================================

SCHEMA_VERSION = "2.0.0"
SCHEMA_COMPATIBILITY = {
    "min_backend_version": "2.0.0",
    "min_frontend_version": "2.0.0",
}


def get_schema_info() -> Dict[str, Any]:
    """
    Get schema version and compatibility info.
    
    Returns:
        Dictionary with version info
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "compatibility": SCHEMA_COMPATIBILITY,
        "fields": list(AssistantResponseMetadata.model_fields.keys()),
    }
