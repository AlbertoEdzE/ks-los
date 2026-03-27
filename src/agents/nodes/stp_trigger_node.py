"""
STP Trigger Node for Agentic Orchestrator

Automatically triggers Straight-Through Processing when minimum document
threshold is met. Implements Caribbean-specific STP rules.

STP Eligibility Rules:
- Salaried employment
- Loan amount within limits (Personal < $500K, Auto < $750K, Home < $2M USD)
- Minimum documents uploaded
- No high-severity discrepancy flags

Usage:
    node = STPTriggerNode()
    should_trigger, reason = node.should_trigger_stp(state)
    
    if should_trigger:
        stp_result = node.trigger_stp(state)
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from src.agents.graph_state import AgenticOrchestratorState
from src.core.document_intelligence import DocumentType


@dataclass
class STPThreshold:
    """Document thresholds for STP eligibility"""
    min_identity_docs: int = 1
    min_income_docs: int = 1
    min_additional_docs: int = 0  # Property docs for home loans, etc.


@dataclass
class LoanAmountLimit:
    """STP loan amount limits by type (USD)"""
    personal: float = 500_000
    auto: float = 750_000
    home: float = 2_000_000
    business: float = 1_000_000


class STPTriggerNode:
    """
    Determines STP eligibility and triggers processing.
    
    Features:
    - Document threshold checking
    - Loan amount validation
    - Employment type verification
    - Discrepancy flag assessment
    - Caribbean-specific rules
    
    Usage:
        node = STPTriggerNode()
        
        # Check eligibility
        eligible, reason = node.check_eligibility(state)
        
        # Trigger STP
        if eligible:
            result = node.trigger(state)
    """
    
    # STP thresholds
    THRESHOLDS = STPThreshold()
    LOAN_LIMITS = LoanAmountLimit()
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_eligibility(
        self,
        state: AgenticOrchestratorState
    ) -> Tuple[bool, str]:
        """
        Check if application is eligible for STP.
        
        Args:
            state: Current orchestrator state
            
        Returns:
            Tuple of (eligible, reason)
        """
        context = state.captured_context
        
        # Rule 1: Employment type must be salaried
        if context.employment_type not in ["salaried", "employed", "government"]:
            return False, "Employment type not eligible (must be salaried)"
        
        # Rule 2: Loan amount within limits
        loan_amount = context.loan_amount
        if loan_amount:
            purpose = context.purpose or "personal"
            limit = self._get_loan_limit(purpose)
            
            if loan_amount > limit:
                return False, f"Loan amount exceeds STP limit (${limit:,})"
        
        # Rule 3: Minimum documents uploaded
        uploaded_docs = state.uploaded_documents if hasattr(state, 'uploaded_documents') else []
        if not self._meets_document_threshold(uploaded_docs, context.purpose):
            return False, "Insufficient documents uploaded"
        
        # Rule 4: No high-severity discrepancy flags
        if hasattr(state, 'flags'):
            high_severity_flags = [
                f for f in state.flags
                if getattr(f, 'severity', None) == 'high'
            ]
            if high_severity_flags:
                return False, "High-severity discrepancy flags present"
        
        # Rule 5: Income and employment verified
        if not context.monthly_income or not context.employment_type:
            return False, "Income or employment not verified"
        
        # All checks passed
        return True, "Eligible for STP"
    
    def should_trigger(
        self,
        state: AgenticOrchestratorState
    ) -> bool:
        """
        Check if STP should be triggered now.
        
        Args:
            state: Current state
            
        Returns:
            True if STP should be triggered
        """
        eligible, reason = self.check_eligibility(state)
        
        if eligible:
            self.logger.info(f"STP trigger conditions met: {reason}")
            return True
        else:
            self.logger.debug(f"STP not triggered: {reason}")
            return False
    
    def trigger(
        self,
        state: AgenticOrchestratorState
    ) -> Dict[str, Any]:
        """
        Trigger STP processing.
        
        Args:
            state: Current state
            
        Returns:
            STP processing result
        """
        self.logger.info("Triggering STP processing")
        
        state.stp_status = "processing"
        state.current_stage = "stp_processing"
        
        # Return trigger result
        return {
            "success": True,
            "message": "STP processing initiated",
            "stage": state.current_stage,
        }
    
    def _get_loan_limit(self, purpose: str) -> float:
        """Get STP loan limit for purpose"""
        purpose_lower = purpose.lower()
        
        if any(term in purpose_lower for term in ["home", "house", "property", "mortgage"]):
            return self.LOAN_LIMITS.home
        elif any(term in purpose_lower for term in ["auto", "car", "vehicle"]):
            return self.LOAN_LIMITS.auto
        elif any(term in purpose_lower for term in ["business", "commercial"]):
            return self.LOAN_LIMITS.business
        else:
            return self.LOAN_LIMITS.personal
    
    def _meets_document_threshold(
        self,
        uploaded_docs: List[Any],
        purpose: Optional[str]
    ) -> bool:
        """Check if uploaded documents meet minimum threshold"""
        if not uploaded_docs:
            return False
        
        # Count documents by category
        identity_count = 0
        income_count = 0
        additional_count = 0
        
        for doc in uploaded_docs:
            doc_type = getattr(doc, 'document_type', None) or getattr(doc, 'category', None)
            
            if doc_type in [DocumentType.NATIONAL_ID, DocumentType.PASSPORT, "identity"]:
                identity_count += 1
            elif doc_type in [DocumentType.PAY_SLIP, DocumentType.JOB_LETTER, "income"]:
                income_count += 1
            else:
                additional_count += 1
        
        # Check thresholds
        if identity_count < self.THRESHOLDS.min_identity_docs:
            return False
        
        if income_count < self.THRESHOLDS.min_income_docs:
            return False
        
        # Additional docs for home loans
        if purpose and "home" in purpose.lower():
            if additional_count < 2:  # Need property docs
                return False
        
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Function
# ─────────────────────────────────────────────────────────────────────────────

def check_stp_eligibility(state: AgenticOrchestratorState) -> Tuple[bool, str]:
    """
    Convenience function to check STP eligibility.
    
    Args:
        state: Current orchestrator state
        
    Returns:
        Tuple of (eligible, reason)
    """
    node = STPTriggerNode()
    return node.check_eligibility(state)


def trigger_stp_if_eligible(state: AgenticOrchestratorState) -> Tuple[bool, Dict[str, Any]]:
    """
    Check eligibility and trigger STP if eligible.
    
    Args:
        state: Current state
        
    Returns:
        Tuple of (triggered, result)
    """
    node = STPTriggerNode()
    
    if node.should_trigger(state):
        result = node.trigger(state)
        return True, result
    else:
        return False, {"success": False, "reason": "Not eligible for STP"}


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "STPTriggerNode",
    "STPThreshold",
    "LoanAmountLimit",
    "check_stp_eligibility",
    "trigger_stp_if_eligible",
]
