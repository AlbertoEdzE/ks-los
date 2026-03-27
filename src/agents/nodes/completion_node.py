"""
Completion Node for Agentic Orchestrator

Implements Mode 3 of the LNAI conversation flow: Post-Submission Processing.

Conversation Flow (Mode 3 - Completion):
    - STP processing awareness and communication
    - Terms acceptance guidance
    - Disbursement confirmation
    - Celebration and next steps

This node handles everything after application submission, including
STP processing, terms acceptance, and final disbursement.

Usage:
    node = CompletionNode(stp_processor=stp_processor)
    updated_state = node.process(current_state)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from src.agents.graph_state import AgenticOrchestratorState, ConversationMode
from src.agents.nodes.stp_trigger_node import STPTriggerNode, check_stp_eligibility


class CompletionNode:
    """
    Handles Mode 3 (Completion) of borrower conversation.
    
    Responsibilities:
    1. Monitor STP processing status
    2. Communicate STP checkpoint progress
    3. Handle terms acceptance
    4. Confirm disbursement
    5. Provide next steps and celebration
    
    STP Stages:
    - pending: Awaiting document upload
    - processing: Running STP checkpoints
    - approved: Ready for terms acceptance
    - disbursed: Funds released
    
    Scientific Design:
    - Real-time STP status updates
    - Clear communication of each stage
    - Empathetic handling of approvals/rejections
    - Audit trail for compliance
    
    Usage:
        node = CompletionNode()
        state = node.process(state)
    """
    
    def __init__(
        self,
        stp_processor: Optional[Any] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize completion node.
        
        Args:
            stp_processor: STP processing service
            config: Configuration options
        """
        self.stp_processor = stp_processor
        self.config = config or {}
        
        self.stp_trigger = STPTriggerNode()
        
        self.logger = logging.getLogger(__name__)
    
    def process(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Process completion mode conversation.
        
        Args:
            state: Current agentic state
            
        Returns:
            Updated state with completion status
        """
        self.logger.info(f"Processing completion mode, STP status: {state.stp_status}")
        
        # Check STP status and handle accordingly
        if state.stp_status == "pending":
            state = self._handle_stp_pending(state)
        
        elif state.stp_status == "processing":
            state = self._handle_stp_processing(state)
        
        elif state.stp_status == "approved":
            if not state.terms_accepted:
                state = self._handle_terms_acceptance(state)
            else:
                state = self._handle_disbursement(state)
        
        elif state.stp_status == "disbursed":
            state = self._handle_post_disbursement(state)
        
        elif state.stp_status == "rejected":
            state = self._handle_rejection(state)
        
        state.update_timestamp()
        return state
    
    def _handle_stp_pending(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Handle STP pending state (awaiting documents).
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        # Check if we can trigger STP
        if state.can_trigger_stp():
            self.logger.info("STP trigger conditions met")
            
            eligible, reason = check_stp_eligibility(state)
            
            if eligible:
                # Trigger STP processing
                state.stp_status = "processing"
                state.stp_checkpoints = self._initialize_stp_checkpoints()
                
                response_text = (
                    "Great news! I've initiated the automated underwriting checks. "
                    "Our system is now processing your application through the following checks:\n\n"
                    "• Identity Verification\n"
                    "• AML/KYC Screening\n"
                    "• Credit Bureau Check\n"
                    "• Affordability Assessment\n"
                    "• Employment Verification\n\n"
                    "This typically takes 2-5 minutes. I'll update you as soon as it's complete!"
                )
                
                state.add_message("assistant", response_text, metadata={
                    "stp_status": "processing",
                    "checkpoints_initialized": True,
                })
                
                # In production, this would trigger async STP processing
                # For now, we'll simulate progression
                return self._simulate_stp_progress(state)
        
        else:
            # Still waiting for documents
            response_text = (
                "Your application is submitted and awaiting document upload. "
                "Please upload the required documents using the attachment button below. "
                "Once uploaded, our system will automatically begin processing."
            )
            
            state.add_message("assistant", response_text)
        
        return state
    
    def _handle_stp_processing(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Handle STP processing state.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        # Simulate or check actual STP progress
        # In production, this would poll the STP processor
        
        # For demonstration, we'll simulate completion
        state = self._complete_stp_processing(state)
        
        return state
    
    def _handle_terms_acceptance(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Handle terms acceptance stage.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        # Generate terms acceptance prompt
        context = state.captured_context
        
        response_text = (
            f"Excellent news! Your loan application has been approved through our Fast-Track system.\n\n"
            f"I've run all the necessary checks — credit bureau verification, identity screening, "
            f"affordability analysis, and compliance checks — and everything looks great.\n\n"
            f"Please review your approved terms below and accept to receive your funds."
        )
        
        # Add terms details to metadata
        terms_metadata = {
            "loan_amount": context.loan_amount,
            "interest_rate": state.loan_snapshot.interest_rate if state.loan_snapshot else None,
            "tenure_years": state.loan_snapshot.tenure_years if state.loan_snapshot else None,
            "monthly_emi": state.loan_snapshot.estimated_emi if state.loan_snapshot else None,
            "total_repayment": state.loan_snapshot.total_repayment if state.loan_snapshot else None,
            "awaiting_acceptance": True,
        }
        
        state.add_message("assistant", response_text, metadata=terms_metadata)
        
        state.current_stage = "awaiting_terms_acceptance"
        
        return state
    
    def _handle_disbursement(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Handle disbursement stage.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        context = state.captured_context
        
        # Generate disbursement confirmation
        response_text = (
            f"🎉 Congratulations! Your loan has been disbursed!\n\n"
            f"**Funds have been credited to your account!**\n\n"
            f"Here are your loan details:\n"
            f"• **Amount**: ${float(context.loan_amount):,.2f}\n"
            f"• **Interest Rate**: {state.loan_snapshot.interest_rate:.2f}%\n"
            f"• **Tenure**: {state.loan_snapshot.tenure_years} years\n"
            f"• **Monthly EMI**: ${state.loan_snapshot.estimated_emi:,.2f}\n"
            f"• **Transaction Reference**: TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}\n\n"
            f"Your first EMI is due on {datetime.now().strftime('%B %d, %Y')}.\n\n"
            f"Thank you for choosing us for your lending needs!"
        )
        
        state.add_message("assistant", response_text, metadata={
            "disbursement_completed": True,
            "celebration": True,
        })
        
        state.stp_status = "disbursed"
        state.current_stage = "completed"
        
        self.logger.info(f"Loan disbursed: {state.application_id}")
        
        return state
    
    def _handle_post_disbursement(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Handle post-disbursement queries.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        response_text = (
            f"Your loan is active! Application ID: {state.application_id}\n\n"
            f"If you have any questions about your loan, feel free to ask. You can also:\n"
            f"• View your amortization schedule\n"
            f"• Make early payments\n"
            f"• Request loan statements\n"
            f"• Apply for additional products"
        )
        
        state.add_message("assistant", response_text)
        
        return state
    
    def _handle_rejection(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Handle rejection with empathy and next steps.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        response_text = (
            f"Thank you for your patience while we reviewed your application.\n\n"
            f"After careful consideration, we're unable to approve your loan at this time. "
            f"This decision is based on our current lending criteria.\n\n"
            f"A loan officer will reach out to you within 24 hours to discuss your options. "
            f"In the meantime, if you have any questions, please don't hesitate to ask."
        )
        
        state.add_message("assistant", response_text, metadata={
            "application_rejected": True,
            "officer_callback_scheduled": True,
        })
        
        state.requires_manual_review = True
        state.escalation_needed = True
        
        self.logger.info(f"Application rejected, escalation triggered: {state.application_id}")
        
        return state
    
    def _initialize_stp_checkpoints(self) -> List[Dict]:
        """Initialize STP checkpoints"""
        from src.agents.graph_state import STPCheckpoint
        
        checkpoints = [
            STPCheckpoint(name="Identity Verification", status="pending"),
            STPCheckpoint(name="AML/KYC Check", status="pending"),
            STPCheckpoint(name="Fraud Detection", status="pending"),
            STPCheckpoint(name="Credit Bureau Pull", status="pending"),
            STPCheckpoint(name="Affordability Assessment", status="pending"),
            STPCheckpoint(name="FOIR Validation", status="pending"),
            STPCheckpoint(name="LTV Assessment", status="pending"),
            STPCheckpoint(name="Employment Verification", status="pending"),
            STPCheckpoint(name="Income Validation", status="pending"),
            STPCheckpoint(name="Document Verification", status="pending"),
        ]
        
        return [cp.model_dump() for cp in checkpoints]
    
    def _simulate_stp_progress(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Simulate STP progress for demonstration.
        
        In production, this would be replaced with actual STP polling.
        """
        # Simulate checkpoint progression
        for i, checkpoint in enumerate(state.stp_checkpoints):
            if checkpoint.get("status") == "pending":
                checkpoint["status"] = "processing"
                
                # Add progress message
                response_text = f"Processing: {checkpoint['name']}..."
                
                state.add_message("assistant", response_text, metadata={
                    "stp_checkpoint": checkpoint["name"],
                    "stp_in_progress": True,
                })
                
                break
        
        return state
    
    def _complete_stp_processing(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Complete STP processing (simulate for demo).
        
        In production, this would receive actual STP results.
        """
        # Mark all checkpoints as passed
        for checkpoint in state.stp_checkpoints:
            checkpoint["status"] = "passed"
        
        # Set STP status to approved
        state.stp_status = "approved"
        state.stp_approved = True
        
        # Simulate bureau score
        state.bureau_score = 720
        
        # Add approval message
        response_text = (
            f"<stp_completed>\n"
            f"Great news! Your application has been approved!\n\n"
            f"Credit Score: {state.bureau_score} (Good)\n"
            f"Approval Decision: APPROVED\n"
            f"</stp_completed>"
        )
        
        state.add_message("assistant", response_text, metadata={
            "stp_completed": True,
            "stp_approved": True,
            "bureau_score": state.bureau_score,
        })
        
        self.logger.info("STP processing complete - approved")
        
        return state


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Function
# ─────────────────────────────────────────────────────────────────────────────

def process_completion(
    state: AgenticOrchestratorState,
    stp_processor: Optional[Any] = None,
    **kwargs
) -> AgenticOrchestratorState:
    """
    Convenience function to process completion mode.
    
    Args:
        state: Current state
        stp_processor: STP processing service
        **kwargs: Additional arguments
        
    Returns:
        Updated state
    """
    node = CompletionNode(stp_processor=stp_processor, **kwargs)
    return node.process(state)


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "CompletionNode",
    "process_completion",
]
