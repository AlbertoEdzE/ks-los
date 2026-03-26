"""
Repair Node for Agentic Orchestrator

Handles conversation repair mechanisms:
- User corrections ("Wait, I meant...", "Actually...")
- Digressions (off-topic questions)
- Contradictions (new info conflicts with prior)
- Clarification requests

This node ensures the conversation can recover gracefully from:
- User second thoughts
- Misunderstandings
- Information updates
- Topic changes

Usage:
    node = RepairNode()
    updated_state = node.process(current_state)
"""

from typing import Dict, List, Any, Optional, Tuple
import re
import logging

from src.agents.graph_state import AgenticOrchestratorState, Message
from src.agents.tools.intent_extractor import IntentExtractorTool


class RepairNode:
    """
    Handles conversation repair and recovery.
    
    Repair Scenarios:
    1. **Corrections**: User changes previously provided information
    2. **Digressions**: User asks off-topic questions
    3. **Contradictions**: New information conflicts with prior data
    4. **Clarifications**: User asks for clarification
    
    Scientific Design:
    - Pattern-based detection (regex + heuristics)
    - Confidence-based decision making
    - Context preservation during repair
    - Audit trail of all changes
    
    Usage:
        node = RepairNode()
        state = node.process(state)
    """
    
    # Correction detection patterns
    CORRECTION_PATTERNS = [
        r"\bwait,?\s*(?:i\s+)?(?:meant|changed\s+my\s+mind)\b",
        r"\bactually,?\b",
        r"\bcorrection\b",
        r"\bthat's\s+not\s+right\b",
        r"\bi\s+(?:changed\s+my\s+mind|made\s+a\s+mistake)\b",
        r"\bno,?\s+(?:that's\s+)?wrong\b",
        r"\blet\s+me\s+(?:correct|rephrase)\b",
        r"\bsorry,?\s+(?:i\s+)?meant\b",
    ]
    
    # Digression detection (questions not related to loan application)
    DIGRESSION_PATTERNS = [
        r"\bhow\s+(?:does|do|long|much)\b",
        r"\bwhat\s+(?:is|are|happens|if)\b",
        r"\bcan\s+i\b",
        r"\bwhy\s+(?:do|does|is|are)\b",
        r"\bwhen\s+(?:do|does|is|are)\b",
        r"\bis\s+it\s+possible\b",
        r"\btell\s+me\s+about\b",
        r"\bexplain\b",
    ]
    
    # Topics that are NOT digressions (loan-related questions)
    ON_TOPIC_TOPICS = [
        "interest rate",
        "emi",
        "loan amount",
        "tenure",
        "documents",
        "application",
        "approval",
        "income",
        "employment",
        "credit",
        "bureau",
        "stp",
        "fast track",
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize repair node.
        
        Args:
            config: Configuration options
        """
        self.config = config or {}
        self.intent_extractor = IntentExtractorTool()
        self.logger = logging.getLogger(__name__)
    
    def process(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Process conversation for repair needs.
        
        Args:
            state: Current agentic state
            
        Returns:
            Updated state with repairs applied
        """
        if not state.conversation_history:
            return state
        
        last_message = state.conversation_history[-1].content
        
        # Check for correction
        if self._is_correction(last_message):
            state = self._handle_correction(state)
        
        # Check for digression
        elif self._is_digression(last_message):
            state = self._handle_digression(state)
        
        # Check for contradiction
        elif self._has_contradiction(state):
            state = self._handle_contradiction(state)
        
        # Check for clarification request
        elif self._is_clarification_request(last_message):
            state = self._handle_clarification(state)
        
        return state
    
    def _is_correction(self, text: str) -> bool:
        """
        Check if message contains a correction.
        
        Args:
            text: User message text
            
        Returns:
            True if correction detected
        """
        text_lower = text.lower()
        
        for pattern in self.CORRECTION_PATTERNS:
            if re.search(pattern, text_lower):
                self.logger.debug(f"Correction detected: {pattern}")
                return True
        
        return False
    
    def _handle_correction(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Handle user correction.
        
        Args:
            state: Current state
            
        Returns:
            Updated state with correction applied
        """
        last_message = state.conversation_history[-1].content
        
        # Extract what's being corrected
        correction_target, new_value = self._identify_correction(
            last_message,
            state.captured_context
        )
        
        if correction_target and new_value is not None:
            # Apply correction
            old_value = getattr(state.captured_context, correction_target, None)
            setattr(state.captured_context, correction_target, new_value)
            
            # Reset confidence for corrected field
            state.confidence_scores[correction_target] = 0.5  # Reset to medium
            
            self.logger.info(
                f"Correction applied: {correction_target} "
                f"from '{old_value}' to '{new_value}'"
            )
            
            # Generate acknowledgment response
            response_text = self._generate_correction_acknowledgment(
                correction_target,
                new_value,
                old_value
            )
            
            state.add_message("assistant", response_text, metadata={
                "repair_type": "correction",
                "field_corrected": correction_target,
                "old_value": old_value,
                "new_value": new_value,
            })
        
        else:
            # Couldn't identify correction - ask for clarification
            response_text = (
                "I want to make sure I update the right information. "
                "Could you clarify what you'd like to change?"
            )
            
            state.add_message("assistant", response_text, metadata={
                "repair_type": "clarification_needed",
            })
        
        return state
    
    def _identify_correction(
        self,
        text: str,
        context: Any
    ) -> Tuple[Optional[str], Optional[Any]]:
        """
        Identify what field is being corrected and the new value.
        
        Args:
            text: User message with correction
            context: Current captured context
            
        Returns:
            Tuple of (field_name, new_value)
        """
        text_lower = text.lower()
        
        # Field detection patterns
        field_patterns = {
            "loan_amount": [
                r"(?:amount|loan)\s*(?:is|of|should\s+be)?\s*\$?([\d,]+)",
                r"borrow\s+\$?([\d,]+)",
                r"need\s+\$?([\d,]+)",
            ],
            "monthly_income": [
                r"(?:income|make|earn)\s*(?:is|of|should\s+be)?\s*\$?([\d,]+)",
                r"salary\s*(?:is|of)?\s*\$?([\d,]+)",
                r"paid\s+\$?([\d,]+)",
            ],
            "employment_type": [
                r"(?:employed|work)\s+as\s+(salaried|self-employed|contractor)",
                r"(?:i'm|i\s+am)\s+(salaried|self-employed|contractor|freelance)",
            ],
            "purpose": [
                r"(?:for|to)\s+(buy|purchase|finance)\s+(home|car|business|property)",
                r"(?:loan\s+)?(?:for|to)\s+(\w+)",
            ],
            "email": [
                r"email\s*(?:is|at)?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            ],
            "phone": [
                r"phone\s*(?:is|number)?\s*([\d+\-\s()]+)",
            ],
        }
        
        # Check each field
        for field_name, patterns in field_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    value = match.group(1).strip()
                    
                    # Convert to appropriate type
                    if field_name in ["loan_amount", "monthly_income"]:
                        try:
                            value = float(value.replace(",", ""))
                        except ValueError:
                            pass
                    
                    return field_name, value
        
        return None, None
    
    def _is_digression(self, text: str) -> bool:
        """
        Check if message is a digression (off-topic).
        
        Args:
            text: User message text
            
        Returns:
            True if digression detected
        """
        text_lower = text.lower()
        
        # First check if it's a question
        is_question = any([
            "?" in text,
            text_lower.startswith(("how", "what", "why", "when", "can", "is", "does")),
        ])
        
        if not is_question:
            return False
        
        # Check if it matches digression patterns
        matches_digression = any(
            re.search(pattern, text_lower)
            for pattern in self.DIGRESSION_PATTERNS
        )
        
        if not matches_digression:
            return False
        
        # Check if it's actually on-topic (loan-related)
        is_on_topic = any(
            topic in text_lower
            for topic in self.ON_TOPIC_TOPICS
        )
        
        # It's a digression if it matches patterns but isn't on-topic
        return not is_on_topic
    
    def _handle_digression(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Handle off-topic digression.
        
        Strategy:
        1. Acknowledge the question
        2. Provide brief answer
        3. Gently redirect to main flow
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        last_message = state.conversation_history[-1].content
        
        # Generate digression response
        response_text = self._generate_digression_response(last_message, state)
        
        state.add_message("assistant", response_text, metadata={
            "repair_type": "digression",
            "redirected": True,
        })
        
        self.logger.debug("Digression handled")
        
        return state
    
    def _generate_digression_response(
        self,
        question: str,
        state: AgenticOrchestratorState
    ) -> str:
        """
        Generate response to off-topic question.
        
        Args:
            question: User's question
            state: Current state
            
        Returns:
            Response text
        """
        question_lower = question.lower()
        
        # Common digression responses
        if "how long" in question_lower:
            return (
                "Good question! Loan processing typically takes 2-5 business days for "
                "standard applications, or 24-48 hours for Fast-Track (STP) processing.\n\n"
                "Now, where were we? Oh yes - you were telling me about your income. "
                "What does your typical monthly income look like before deductions?"
            )
        
        elif "interest rate" in question_lower:
            return (
                "Our interest rates typically range from 7.5% to 12% depending on the "
                "loan type, amount, and your credit profile. I'll provide you with "
                "personalized rates once I have a bit more information.\n\n"
                "Speaking of which, could you tell me your monthly income before deductions?"
            )
        
        elif "documents" in question_lower:
            return (
                "You'll need to provide some basic documents like your ID, proof of "
                "income (pay slips or bank statements), and for home loans, property "
                "documents. I'll give you a complete checklist once we submit your application.\n\n"
                "For now, could you tell me - are you currently salaried, self-employed, "
                "or working as a contractor?"
            )
        
        else:
            # Generic response
            return (
                "That's a great question! I'd be happy to explain that in more detail "
                "once we have your application set up. Our loan officers can provide "
                "comprehensive answers to all your questions.\n\n"
                "To continue with your application, could you tell me "
            ) + self._get_next_question(state)
    
    def _has_contradiction(self, state: AgenticOrchestratorState) -> bool:
        """
        Check if new information contradicts prior data.
        
        Args:
            state: Current state
            
        Returns:
            True if contradiction detected
        """
        # This would require more sophisticated NLP
        # For now, we'll rely on confidence scores
        low_confidence_fields = [
            field for field, conf in state.confidence_scores.items()
            if conf < 0.3
        ]
        
        return len(low_confidence_fields) > 0
    
    def _handle_contradiction(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Handle contradictory information.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        # Find low-confidence fields
        low_confidence_fields = [
            field for field, conf in state.confidence_scores.items()
            if conf < 0.3
        ]
        
        if low_confidence_fields:
            field = low_confidence_fields[0]
            
            # Ask for clarification
            response_text = (
                f"I want to make sure I have the correct information. "
                f"Could you clarify your {field.replace('_', ' ')}? "
                f"I want to ensure everything is accurate for your application."
            )
            
            state.add_message("assistant", response_text, metadata={
                "repair_type": "contradiction",
                "field": field,
            })
        
        return state
    
    def _is_clarification_request(self, text: str) -> bool:
        """
        Check if user is asking for clarification.
        
        Args:
            text: User message text
            
        Returns:
            True if clarification request
        """
        text_lower = text.lower()
        
        clarification_phrases = [
            "what do you mean",
            "can you explain",
            "i don't understand",
            "could you clarify",
            "what is",
            "how does that work",
        ]
        
        return any(phrase in text_lower for phrase in clarification_phrases)
    
    def _handle_clarification(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Handle clarification request.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        last_message = state.conversation_history[-1].content
        
        # Provide clarification based on current stage
        if state.current_stage == "intent_capture":
            response_text = (
                "I'm here to help you find the best loan option! To get started, "
                "I just need to understand what you're looking to finance. "
                "Are you thinking about a home, car, business, or perhaps a personal loan?"
            )
        
        elif state.current_stage == "financial_context":
            response_text = (
                "Let me explain - I need to understand your financial situation "
                "to recommend the best loan options for you. This includes your "
                "employment type and monthly income. Don't worry, all information "
                "is kept confidential."
            )
        
        else:
            response_text = (
                "I'm here to guide you through the loan application process step by step. "
                "If you have any specific questions, feel free to ask! Otherwise, "
                "let's continue with "
            ) + self._get_next_question(state)
        
        state.add_message("assistant", response_text, metadata={
            "repair_type": "clarification",
        })
        
        return state
    
    def _generate_correction_acknowledgment(
        self,
        field: str,
        new_value: Any,
        old_value: Any
    ) -> str:
        """
        Generate acknowledgment of correction.
        
        Args:
            field: Field that was corrected
            new_value: New value
            old_value: Old value
            
        Returns:
            Acknowledgment text
        """
        field_display = field.replace("_", " ")
        
        return (
            f"Thanks for clarifying! I've updated your {field_display} to {new_value}. "
            f"Let's continue with your application."
        )
    
    def _get_next_question(self, state: AgenticOrchestratorState) -> str:
        """
        Get the next question to ask based on current stage.
        
        Args:
            state: Current state
            
        Returns:
            Next question text
        """
        context = state.captured_context
        
        if not context.purpose:
            return "what type of loan you're looking for?"
        elif not context.employment_type:
            return "about your employment type?"
        elif not context.monthly_income:
            return "about your monthly income?"
        elif not context.loan_amount:
            return "how much you need to borrow?"
        else:
            return "with the next steps?"


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Function
# ─────────────────────────────────────────────────────────────────────────────

def process_repair(state: AgenticOrchestratorState, **kwargs) -> AgenticOrchestratorState:
    """
    Convenience function to process conversation repair.
    
    Args:
        state: Current state
        **kwargs: Additional arguments
        
    Returns:
        Updated state
    """
    node = RepairNode(**kwargs)
    return node.process(state)


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "RepairNode",
    "process_repair",
]
