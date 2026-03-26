"""
Escalation Node for Agentic Orchestrator

Handles escalation to human loan officers when:
- LLM confidence is too low
- High-severity discrepancy flags
- User frustration detected
- High-value loans requiring manual review
- Complex cases beyond agent scope

Usage:
    node = EscalationNode(notify_callback=notify_officers)
    updated_state = node.process(current_state)
"""

from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import logging

from src.agents.graph_state import AgenticOrchestratorState, Message


class EscalationNode:
    """
    Handles escalation to human loan officers.
    
    Escalation Triggers:
    1. **Low Confidence**: Average confidence < 0.3 for 3+ turns
    2. **High-Severity Flags**: Discrepancy flags with severity="high"
    3. **User Frustration**: Sentiment analysis detects frustration
    4. **High-Value Loans**: Loan amount exceeds auto-approval limits
    5. **Complex Cases**: Multiple repair attempts failed
    
    Scientific Design:
    - Multi-factor escalation decision
    - Comprehensive handoff summary
    - Officer notification system
    - User-friendly communication
    - Audit trail for compliance
    
    Usage:
        node = EscalationNode(notify_callback=notify_officers)
        state = node.process(state)
    """
    
    # Escalation thresholds
    LOW_CONFIDENCE_THRESHOLD = 0.3
    LOW_CONFIDENCE_TURNS = 3
    HIGH_VALUE_THRESHOLD_USD = 500_000  # Loans above this need review
    MAX_REPAIR_ATTEMPTS = 3
    
    def __init__(
        self,
        notify_callback: Optional[Callable] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize escalation node.
        
        Args:
            notify_callback: Callback to notify officers
            config: Configuration options
        """
        self.notify_callback = notify_callback
        self.config = config or {}
        
        # Tracking
        self.low_confidence_turns = 0
        self.repair_attempts = 0
        
        self.logger = logging.getLogger(__name__)
    
    def process(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Process conversation for escalation needs.
        
        Args:
            state: Current agentic state
            
        Returns:
            Updated state with escalation if needed
        """
        # Check if escalation already triggered
        if state.escalation_needed:
            return state
        
        # Check escalation conditions
        should_escalate = False
        reason = ""
        
        # Condition 1: Low confidence streak
        if self._has_low_confidence_streak(state):
            should_escalate = True
            reason = "Low confidence in information extraction"
        
        # Condition 2: High-severity flags
        elif state.has_high_severity_flags():
            should_escalate = True
            reason = "High-severity discrepancy flags detected"
        
        # Condition 3: High-value loan
        elif self._is_high_value_loan(state):
            should_escalate = True
            reason = "High-value loan requires manual review"
        
        # Condition 4: User frustration detected
        elif self._detect_user_frustration(state):
            should_escalate = True
            reason = "User frustration detected"
        
        # Condition 5: Multiple repair attempts failed
        elif self.repair_attempts >= self.MAX_REPAIR_ATTEMPTS:
            should_escalate = True
            reason = "Multiple conversation repair attempts failed"
        
        if should_escalate:
            state = self._trigger_escalation(state, reason)
        
        return state
    
    def _has_low_confidence_streak(self, state: AgenticOrchestratorState) -> bool:
        """
        Check if there's a streak of low-confidence extractions.
        
        Args:
            state: Current state
            
        Returns:
            True if low confidence streak detected
        """
        avg_confidence = state.get_average_confidence()
        
        if avg_confidence < self.LOW_CONFIDENCE_THRESHOLD:
            self.low_confidence_turns += 1
        else:
            self.low_confidence_turns = 0
        
        return self.low_confidence_turns >= self.LOW_CONFIDENCE_TURNS
    
    def _is_high_value_loan(self, state: AgenticOrchestratorState) -> bool:
        """
        Check if loan amount exceeds auto-approval limit.
        
        Args:
            state: Current state
            
        Returns:
            True if high-value loan
        """
        loan_amount = state.captured_context.loan_amount
        
        if not loan_amount:
            return False
        
        # Convert to float if string
        if isinstance(loan_amount, str):
            try:
                loan_amount = float(loan_amount.replace(",", "").replace("$", ""))
            except ValueError:
                return False
        
        return loan_amount > self.HIGH_VALUE_THRESHOLD_USD
    
    def _detect_user_frustration(self, state: AgenticOrchestratorState) -> bool:
        """
        Detect user frustration from conversation.
        
        Simple heuristic-based detection:
        - Repeated questions
        - Negative sentiment words
        - ALL CAPS messages
        - Excessive punctuation (!!!, ???)
        
        Args:
            state: Current state
            
        Returns:
            True if frustration detected
        """
        if not state.conversation_history:
            return False
        
        last_message = state.conversation_history[-1].content
        
        # Check for frustration indicators
        frustration_indicators = [
            last_message.isupper() and len(last_message) > 10,  # ALL CAPS
            "!!!" in last_message or "???" in last_message,  # Excessive punctuation
            any(word in last_message.lower() for word in [
                "frustrated", "annoyed", "useless", "not helping",
                "confusing", "complicated", "waste of time",
            ]),
        ]
        
        return any(frustration_indicators)
    
    def _trigger_escalation(
        self,
        state: AgenticOrchestratorState,
        reason: str
    ) -> AgenticOrchestratorState:
        """
        Trigger escalation to human officer.
        
        Args:
            state: Current state
            reason: Reason for escalation
            
        Returns:
            Updated state with escalation triggered
        """
        self.logger.info(f"Escalation triggered: {reason}")
        
        # Mark state as escalated
        state.escalation_needed = True
        state.requires_manual_review = True
        
        # Generate handoff summary
        handoff_summary = self._generate_handoff_summary(state, reason)
        
        # Notify officers
        if self.notify_callback:
            try:
                self.notify_callback(handoff_summary)
                self.logger.info("Officer notification sent")
            except Exception as e:
                self.logger.error(f"Failed to notify officers: {str(e)}")
        
        # Generate user-facing message
        response_text = self._generate_escalation_message(state, reason)
        
        state.add_message("assistant", response_text, metadata={
            "escalation_triggered": True,
            "escalation_reason": reason,
            "handoff_summary": handoff_summary,
            "officer_notified": self.notify_callback is not None,
        })
        
        return state
    
    def _generate_handoff_summary(
        self,
        state: AgenticOrchestratorState,
        reason: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive handoff summary for officer.
        
        Args:
            state: Current state
            reason: Escalation reason
            
        Returns:
            Handoff summary dict
        """
        context = state.captured_context
        
        return {
            "session_id": state.session_id,
            "application_id": state.application_id,
            "escalation_reason": reason,
            "timestamp": datetime.now().isoformat(),
            "borrower_info": {
                "name": context.borrower_name,
                "email": context.email,
                "phone": context.phone,
            },
            "loan_details": {
                "purpose": context.purpose,
                "amount": context.loan_amount,
                "income": context.monthly_income,
                "employment": context.employment_type,
            },
            "conversation_stats": {
                "total_messages": len(state.conversation_history),
                "average_confidence": state.get_average_confidence(),
                "low_confidence_turns": self.low_confidence_turns,
                "repair_attempts": self.repair_attempts,
            },
            "flags": [
                {
                    "field": flag.field_name,
                    "severity": flag.severity,
                    "description": f"{flag.declared_value} vs {flag.extracted_value}",
                }
                for flag in state.discrepancy_flags
            ],
            "conversation_history": [
                {"role": msg.role, "content": msg.content}
                for msg in state.conversation_history[-10:]  # Last 10 messages
            ],
            "recommended_action": self._get_recommended_action(reason),
        }
    
    def _generate_escalation_message(
        self,
        state: AgenticOrchestratorState,
        reason: str
    ) -> str:
        """
        Generate user-friendly escalation message.
        
        Args:
            state: Current state
            reason: Escalation reason
            
        Returns:
            User-facing message
        """
        context = state.captured_context
        
        # Personalize if we have borrower name
        borrower_name = context.borrower_name or "there"
        
        # Different messages based on reason
        if "high-severity" in reason.lower() or "discrepancy" in reason.lower():
            return (
                f"Thank you for your patience, {borrower_name}.\n\n"
                f"I want to ensure your application receives the attention it deserves. "
                f"Some of the information provided requires additional verification.\n\n"
                f"I'm connecting you with a senior loan officer who will reach out to you "
                f"within 24 hours to complete your application. They may request some "
                f"additional documentation.\n\n"
                f"Your application reference is **{state.application_id or 'being generated'}**. "
                f"Please keep this for your records."
            )
        
        elif "high-value" in reason.lower():
            return (
                f"Thank you for your application, {borrower_name}.\n\n"
                f"For loan amounts above ${self.HIGH_VALUE_THRESHOLD_USD:,}, our policy "
                f"requires a personal consultation with one of our senior loan officers "
                f"to ensure we structure the best possible terms for your needs.\n\n"
                f"A loan officer will contact you within 24 hours to discuss your "
                f"application in detail.\n\n"
                f"Your application reference is **{state.application_id or 'being generated'}**."
            )
        
        elif "frustration" in reason.lower():
            return (
                f"I apologize if I haven't been as helpful as you'd hoped, {borrower_name}.\n\n"
                f"Let me connect you with a human loan officer who can provide personalized "
                f"assistance and answer all your questions directly.\n\n"
                f"Someone will reach out to you within 24 hours. Your application reference "
                f"is **{state.application_id or 'being generated'}**."
            )
        
        else:
            # Generic escalation
            return (
                f"Thank you for your time, {borrower_name}.\n\n"
                f"To ensure you receive the best possible service, I'm connecting you "
                f"with a senior loan officer who can provide personalized assistance.\n\n"
                f"They will reach out to you within 24 hours to continue your application.\n\n"
                f"Your application reference is **{state.application_id or 'being generated'}**. "
                f"Please keep this for your records."
            )
    
    def _get_recommended_action(self, reason: str) -> str:
        """
        Get recommended action for officer.
        
        Args:
            reason: Escalation reason
            
        Returns:
            Recommended action text
        """
        if "discrepancy" in reason.lower():
            return "Verify discrepant information with borrower and request additional documentation"
        elif "high-value" in reason.lower():
            return "Conduct detailed financial assessment and structure appropriate terms"
        elif "frustration" in reason.lower():
            return "Provide personalized assistance and address borrower concerns"
        elif "confidence" in reason.lower():
            return "Review conversation history and manually extract required information"
        else:
            return "Review application and provide personalized assistance"
    
    def increment_repair_attempts(self):
        """Increment repair attempt counter"""
        self.repair_attempts += 1
        self.logger.debug(f"Repair attempt #{self.repair_attempts}")


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Function
# ─────────────────────────────────────────────────────────────────────────────

def process_escalation(
    state: AgenticOrchestratorState,
    notify_callback: Optional[Callable] = None,
    **kwargs
) -> AgenticOrchestratorState:
    """
    Convenience function to process escalation.
    
    Args:
        state: Current state
        notify_callback: Officer notification callback
        **kwargs: Additional arguments
        
    Returns:
        Updated state
    """
    node = EscalationNode(notify_callback=notify_callback, **kwargs)
    return node.process(state)


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "EscalationNode",
    "process_escalation",
]
