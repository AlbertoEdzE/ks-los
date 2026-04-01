"""
Application Node for Agentic Orchestrator

Implements Mode 2 of the LNAI conversation flow: Application Collection & Submission.

Conversation Flow (Mode 2 - Application):
    Step 5: Contact capture (email, phone)
    Step 6: Submit application (all 10 required fields)
    Step 7: Documents checklist (included with submission)

This node handles the transition from advisory to formal application,
ensuring all required fields are collected before submission.

Usage:
    node = ApplicationNode()
    updated_state = node.process(current_state)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import re

from src.agents.graph_state import AgenticOrchestratorState, ConversationMode, Message
from src.agents.agent_tools.intent_extractor import IntentExtractorTool
from src.agents.response_generator import ApplicationSubmissionStrategy
from src.agents.agent_tools.document_requirements import DocumentRequirementsTool


class ApplicationNode:
    """
    Handles Mode 2 (Application) of borrower conversation.
    
    Responsibilities:
    1. Collect contact information (email, phone)
    2. Validate all 10 required fields
    3. Create loan application record
    4. Generate documents checklist
    5. Submit application with STP eligibility check
    
    Required Fields (10 total):
    1. First Name
    2. Last Name
    3. Email Address
    4. Phone Number
    5. Employment Type
    6. Monthly Income
    7. Loan Type
    8. Loan Amount
    9. Purpose
    10. Existing Debts
    
    Scientific Design:
    - Progressive disclosure (one field at a time)
    - Validation before submission
    - Confidence-based acceptance
    - Automatic document checklist generation
    
    Usage:
        node = ApplicationNode()
        state = node.process(state)
    """
    
    # Required fields for application submission
    REQUIRED_FIELDS = [
        "borrower_name",
        "email",
        "phone",
        "employment_type",
        "monthly_income",
        "purpose",
        "loan_amount",
        "existing_debts",
    ]
    
    def __init__(
        self,
        create_loan_callback: Optional[Any] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize application node.
        
        Args:
            create_loan_callback: Callback function to create loan record
            config: Configuration options
        """
        self.create_loan_callback = create_loan_callback
        self.config = config or {}
        
        self.intent_extractor = IntentExtractorTool()
        self.doc_requirements = DocumentRequirementsTool()
        
        self.logger = logging.getLogger(__name__)
    
    def process(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Process application mode conversation.
        
        Args:
            state: Current agentic state
            
        Returns:
            Updated state with application submitted
        """
        self.logger.info(f"Processing application mode, stage: {state.current_stage}")
        
        # Check if we have all required fields
        missing_fields = self._get_missing_fields(state)
        
        if missing_fields:
            # Need to collect more information
            state = self._collect_missing_fields(state, missing_fields)
        else:
            # All fields collected - submit application
            state = self._submit_application(state)
        
        state.update_timestamp()
        return state
    
    def _get_missing_fields(self, state: AgenticOrchestratorState) -> List[str]:
        """
        Get list of missing required fields.
        
        Args:
            state: Current state
            
        Returns:
            List of missing field names
        """
        context = state.captured_context
        missing = []
        
        # Check each required field
        field_checks = {
            "borrower_name": bool(context.borrower_name),
            "email": bool(context.email and self._is_valid_email(context.email)),
            "phone": bool(context.phone and self._has_digits(context.phone)),
            "employment_type": bool(context.employment_type),
            "monthly_income": bool(context.monthly_income),
            "purpose": bool(context.purpose),
            "loan_amount": bool(context.loan_amount),
            "existing_debts": context.existing_debts is not None,
        }
        
        for field, has_value in field_checks.items():
            if not has_value:
                missing.append(field)
        
        # Also check confidence scores
        low_confidence_fields = [
            field for field in missing
            if state.get_confidence(field) < 0.5
        ]
        
        if low_confidence_fields:
            self.logger.warning(
                f"Low confidence fields: {low_confidence_fields}"
            )
        
        return missing
    
    def _collect_missing_fields(
        self,
        state: AgenticOrchestratorState,
        missing_fields: List[str]
    ) -> AgenticOrchestratorState:
        """
        Collect missing required fields from user.
        
        Args:
            state: Current state
            missing_fields: List of missing field names
            
        Returns:
            Updated state with collection message
        """
        # Get last user message
        if not state.conversation_history:
            return state
        
        last_message = state.conversation_history[-1].content
        
        # Extract contact info using LLM
        try:
            extraction = self.intent_extractor._run(
                conversation_history=[
                    {"role": m.role, "content": m.content}
                    for m in state.conversation_history
                ],
                session_id=state.session_id,
            )
            
            from src.agents.agent_tools.intent_extractor import IntentExtractionResult
            result = IntentExtractionResult.model_validate_json(extraction)
            
            # Update context with extracted data
            if result.context.email:
                state.captured_context.email = result.context.email
            if result.context.phone:
                state.captured_context.phone = result.context.phone
            if result.context.borrower_name:
                state.captured_context.borrower_name = result.context.borrower_name
            
            # Update confidence scores
            state.confidence_scores.update(result.field_confidence)
            
        except Exception as e:
            self.logger.warning(f"Contact extraction failed: {str(e)}")
        
        # Check what's still missing
        still_missing = self._get_missing_fields(state)
        
        if still_missing:
            # Ask for remaining fields
            response_text = self._generate_collection_prompt(still_missing)
        else:
            # All fields collected - proceed to submission
            return self._submit_application(state)
        
        state.add_message("assistant", response_text)
        
        return state
    
    def _submit_application(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Submit loan application.
        
        Args:
            state: Current state with all required fields
            
        Returns:
            Updated state with application submitted
        """
        context = state.captured_context
        
        self.logger.info("Submitting loan application")
        
        # Generate application ID
        application_id = f"APP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        state.application_id = application_id
        
        # Generate documents checklist
        checklist_result = self.doc_requirements._run(
            loan_type=context.purpose or "personal",
            employment_type=context.employment_type or "salaried",
            loan_amount=float(context.loan_amount) if isinstance(context.loan_amount, (int, float)) else None
        )
        
        from src.agents.graph_state import DocumentsChecklist
        state.documents_checklist = DocumentsChecklist(**checklist_result)
        
        # Create loan record (if callback provided)
        if self.create_loan_callback:
            try:
                loan_data = {
                    "borrower_name": context.borrower_name,
                    "borrower_email": context.email,
                    "borrower_phone": context.phone,
                    "loan_type": context.purpose,
                    "loan_amount": context.loan_amount,
                    "purpose": context.purpose,
                    "employment_type": context.employment_type,
                    "monthly_income": context.monthly_income,
                    "existing_debts": context.existing_debts,
                }
                
                loan = self.create_loan_callback(loan_data)
                self.logger.info(f"Loan created: {loan.get('id', application_id)}")
                
            except Exception as e:
                self.logger.error(f"Failed to create loan: {str(e)}")
        
        # Mark application as submitted
        state.application_submitted = True
        
        # Generate submission response with documents checklist
        strategy = ApplicationSubmissionStrategy()
        response_text = strategy.generate(
            context=context,
            stage=None,
            application_data={
                "first_name": context.borrower_name.split()[0] if context.borrower_name else "",
                "last_name": " ".join(context.borrower_name.split()[1:]) if context.borrower_name else "",
                "email": context.email,
                "phone": context.phone,
            },
            documents=state.documents_checklist,
        )
        
        state.add_message("assistant", response_text, metadata={
            "application_id": application_id,
            "documents_checklist": state.documents_checklist.model_dump(),
            "application_submitted": True,
        })
        
        # Transition to completion mode
        state.mode = ConversationMode.COMPLETION
        state.current_stage = "documents_upload"
        
        self.logger.info(
            f"Application submitted: {application_id}, "
            f"mode transitioned to COMPLETION"
        )
        
        return state
    
    def _generate_collection_prompt(self, missing_fields: List[str]) -> str:
        """
        Generate prompt to collect missing fields.
        
        Args:
            missing_fields: List of missing field names
            
        Returns:
            Natural language prompt
        """
        prompts = {
            "borrower_name": (
                "To proceed with your application, I'll need your full name. "
                "Could you please provide your first and last name?"
            ),
            "email": (
                "Perfect! Now, what's the best email address to send your loan updates to?"
            ),
            "phone": (
                "Great! And what's your phone number so we can reach you quickly?"
            ),
            "employment_type": (
                "Thanks! Are you currently salaried, self-employed, or working as a contractor?"
            ),
            "monthly_income": (
                "And what is your typical monthly income before deductions?"
            ),
            "purpose": (
                "Just to confirm - what will this loan be used for?"
            ),
            "loan_amount": (
                "How much are you looking to borrow?"
            ),
            "existing_debts": (
                "And just so I can factor everything in — are there any current loan "
                "repayments, credit card balances, or other monthly commitments I should know about? "
                "If none, just say 'none'."
            ),
        }
        
        # Ask for first missing field
        if missing_fields:
            field = missing_fields[0]
            return prompts.get(field, "Please provide the missing information.")
        
        return "Please provide the required information to proceed."
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _has_digits(self, phone: str) -> bool:
        """Check if phone has digits"""
        if not phone:
            return False
        return any(c.isdigit() for c in phone)


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Function
# ─────────────────────────────────────────────────────────────────────────────

def process_application(
    state: AgenticOrchestratorState,
    create_loan_callback: Optional[Any] = None,
    **kwargs
) -> AgenticOrchestratorState:
    """
    Convenience function to process application mode.
    
    Args:
        state: Current state
        create_loan_callback: Callback to create loan record
        **kwargs: Additional arguments
        
    Returns:
        Updated state
    """
    node = ApplicationNode(create_loan_callback=create_loan_callback, **kwargs)
    return node.process(state)


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "ApplicationNode",
    "process_application",
]
