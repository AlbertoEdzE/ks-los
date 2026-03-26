"""
LLM Integration Layer for Agentic Orchestrator

This module provides the integration between the LLM-based intent extraction
and the deterministic orchestrator state machine. It implements confidence-based
routing with rigorous error handling and fallback mechanisms.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    User Message                              │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              LLM Intent Extractor                            │
    │  - Semantic understanding                                    │
    │  - Confidence scoring (0-1)                                  │
    │  - Caribbean context awareness                               │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              Confidence Router                               │
    │  - High (>0.8): Auto-accept                                  │
    │  - Medium (0.5-0.8): Clarify + fallback                      │
    │  - Low (<0.5): Use regex fallback                            │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              Deterministic Orchestrator                      │
    │  - State machine progression                                 │
    │  - Business logic validation                                 │
    │  - Calculation engines                                       │
    └─────────────────────────────────────────────────────────────┘

Design Principles:
1. **Graceful Degradation**: LLM failure → regex fallback → explicit questioning
2. **Confidence-Aware**: Field-level confidence drives clarification strategy
3. **Audit Trail**: All extractions logged with confidence scores
4. **Deterministic Core**: Business logic remains rule-based (no LLM hallucination)
"""

from typing import Dict, List, Any, Optional, Tuple, Literal
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json

from src.agents.orchestrator import LNAIOrchestrator, CapturedContext, ConversationStage
from src.agents.tools.intent_extractor import (
    IntentExtractorTool,
    IntentExtractionResult,
    extract_intent_from_conversation,
)
from src.agents.structured_parser import (
    parse_llm_response,
    IntentAnalysis,
    ParsedOutput,
)
from src.agents.prompts import BORROWER_SYSTEM_PROMPT, RESPONSE_GENERATION_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class IntegrationConfig:
    """Configuration for LLM integration"""
    
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD: float = 0.8
    MEDIUM_CONFIDENCE_THRESHOLD: float = 0.5
    
    # LLM configuration
    model_name: str = "qwen2.5:7b"
    ollama_base_url: str = "http://localhost:11434"
    temperature: float = 0.1  # Low for extraction tasks
    
    # Fallback configuration
    use_regex_fallback: bool = True
    max_llm_retries: int = 2
    llm_timeout_seconds: int = 30
    
    # Logging
    log_level: str = "INFO"
    log_confidence_scores: bool = True
    
    # Validation
    validate_extraction: bool = True
    min_income_for_confidence: float = 1000.0  # Minimum reasonable income
    max_loan_amount_multiplier: float = 50.0  # Max loan = income * multiplier


# ─────────────────────────────────────────────────────────────────────────────
# Extraction Result Container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ExtractionDecision:
    """
    Result from confidence-based routing decision.
    
    Attributes:
        action: What action to take (accept, clarify, fallback)
        context: Extracted context (may be partial)
        confidence: Overall confidence score
        field_confidence: Per-field confidence scores
        low_confidence_fields: Fields below threshold
        clarification_needed: What information to clarify
        use_fallback: Whether to use regex fallback
        llm_error: Any LLM errors encountered
    """
    action: Literal["accept", "clarify", "fallback"]
    context: CapturedContext
    confidence: float = 0.5
    field_confidence: Dict[str, float] = field(default_factory=dict)
    low_confidence_fields: List[str] = field(default_factory=list)
    clarification_needed: List[str] = field(default_factory=list)
    use_fallback: bool = False
    llm_error: Optional[str] = None
    
    def should_accept(self) -> bool:
        """Check if extraction should be accepted"""
        return self.action == "accept"
    
    def needs_clarification(self) -> bool:
        """Check if clarification is needed"""
        return self.action == "clarify" and len(self.clarification_needed) > 0
    
    def should_use_fallback(self) -> bool:
        """Check if regex fallback should be used"""
        return self.action == "fallback" or self.use_fallback


# ─────────────────────────────────────────────────────────────────────────────
# Confidence Router
# ─────────────────────────────────────────────────────────────────────────────

class ConfidenceRouter:
    """
    Routes extraction results based on confidence scores.
    
    Implements a three-tier routing strategy:
    1. HIGH (>0.8): Auto-accept, update context
    2. MEDIUM (0.5-0.8): Accept but ask clarifying questions
    3. LOW (<0.5): Reject, use regex fallback or explicit questioning
    
    Scientific Basis:
    - Thresholds based on empirical LLM reliability studies
    - Field-level confidence enables granular decisions
    - Validation rules prevent nonsensical extractions
    """
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def route(
        self,
        llm_result: IntentExtractionResult,
        current_context: CapturedContext
    ) -> ExtractionDecision:
        """
        Make routing decision based on confidence scores and validation.
        
        Args:
            llm_result: Result from LLM extraction
            current_context: Current orchestrator context
            
        Returns:
            ExtractionDecision with routing action
        """
        # Extract fields
        context = self._to_captured_context(llm_result.context)
        confidence = llm_result.confidence
        field_confidence = llm_result.field_confidence
        
        # Identify low-confidence fields
        low_confidence_fields = [
            field for field, conf in field_confidence.items()
            if conf < self.config.HIGH_CONFIDENCE_THRESHOLD
        ]
        
        # Validate extraction
        validation_errors = self._validate_extraction(context, field_confidence)
        
        # Make routing decision
        if validation_errors:
            # Validation failed → fallback
            action = "fallback"
            self.logger.warning(f"Validation failed: {validation_errors}")
        
        elif confidence >= self.config.HIGH_CONFIDENCE_THRESHOLD:
            # High confidence → accept
            action = "accept"
        
        elif confidence >= self.config.MEDIUM_CONFIDENCE_THRESHOLD:
            # Medium confidence → accept with clarification
            action = "clarify"
        
        else:
            # Low confidence → fallback
            action = "fallback"
        
        # Determine what needs clarification
        clarification_needed = self._identify_clarification_needs(
            context, field_confidence, current_context
        )
        
        decision = ExtractionDecision(
            action=action,
            context=context,
            confidence=confidence,
            field_confidence=field_confidence,
            low_confidence_fields=low_confidence_fields,
            clarification_needed=clarification_needed,
            use_fallback=(action == "fallback"),
            llm_error=llm_result.parse_errors
        )
        
        # Log decision
        if self.config.log_confidence_scores:
            self._log_decision(decision)
        
        return decision
    
    def _to_captured_context(self, intent: IntentAnalysis) -> CapturedContext:
        """Convert IntentAnalysis to CapturedContext"""
        # Parse numeric values from strings
        loan_amount = self._parse_currency(intent.loan_amount)
        monthly_income = self._parse_currency(intent.monthly_income)
        existing_debts = self._parse_currency(intent.existing_debts)
        
        return CapturedContext(
            purpose=intent.purpose,
            loan_amount=loan_amount,
            monthly_income=monthly_income,
            existing_debts=existing_debts,
            employment_type=intent.employment_type,
            borrower_name=intent.borrower_name,
            email=intent.email,
            phone=intent.phone,
            urgency=intent.urgency,
            affordability=intent.affordability,
            preferred_tenure=intent.preferred_tenure,
            collateral_available=intent.collateral_available,
            credit_history=intent.credit_history,
            seriousness_score=intent.seriousness_score,
            fit_score=intent.fit_score,
            next_conversation_angle=intent.next_conversation_angle,
            field_confidence={},  # Will be set from result
            currency=self._detect_currency(intent.loan_amount or intent.monthly_income or ""),
        )
    
    def _parse_currency(self, value: Optional[str]) -> Optional[float]:
        """Parse currency string to float"""
        if value is None:
            return None
        
        # Remove currency symbols and commas
        import re
        cleaned = re.sub(r'[,$€£¥]', '', str(value))
        
        try:
            return float(cleaned.strip())
        except ValueError:
            return None
    
    def _detect_currency(self, text: str) -> str:
        """Detect currency from text"""
        if not text:
            return "USD"
        
        text_lower = text.lower()
        if "ttd" in text_lower or "tt" in text_lower:
            return "TTD"
        elif "jmd" in text_lower or "jm" in text_lower:
            return "JMD"
        elif "bbd" in text_lower or "bb" in text_lower:
            return "BBD"
        elif "gyd" in text_lower or "gy" in text_lower:
            return "GYD"
        elif "xcd" in text_lower or "ec" in text_lower:
            return "XCD"
        elif "€" in text:
            return "EUR"
        elif "£" in text:
            return "GBP"
        else:
            return "USD"  # Default
    
    def _validate_extraction(
        self,
        context: CapturedContext,
        field_confidence: Dict[str, float]
    ) -> List[str]:
        """
        Validate extracted values for sanity.
        
        Validation rules:
        1. Income must be reasonable (> $1,000, < $1M/month)
        2. Loan amount must be proportional to income
        3. Purpose must be recognized
        4. Email must be valid format
        5. Phone must have digits
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate income
        if context.monthly_income is not None:
            if context.monthly_income < self.config.min_income_for_confidence:
                errors.append(f"Income too low: {context.monthly_income}")
            elif context.monthly_income > 1_000_000:
                errors.append(f"Income unrealistically high: {context.monthly_income}")
        
        # Validate loan amount vs income
        if context.loan_amount is not None and context.monthly_income is not None:
            max_reasonable = context.monthly_income * self.config.max_loan_amount_multiplier
            if context.loan_amount > max_reasonable:
                errors.append(
                    f"Loan amount ({context.loan_amount}) exceeds "
                    f"{self.config.max_loan_amount_multiplier}x income ({context.monthly_income})"
                )
        
        # Validate purpose
        valid_purposes = [
            "home_purchase", "auto", "personal", "business",
            "education", "medical", "debt_consolidation", None
        ]
        if context.purpose not in valid_purposes:
            errors.append(f"Invalid purpose: {context.purpose}")
        
        # Validate email format
        if context.email and "@" not in context.email:
            errors.append(f"Invalid email format: {context.email}")
        
        # Validate phone has digits
        if context.phone and not any(c.isdigit() for c in context.phone):
            errors.append(f"Phone has no digits: {context.phone}")
        
        return errors
    
    def _identify_clarification_needs(
        self,
        context: CapturedContext,
        field_confidence: Dict[str, float],
        current_context: CapturedContext
    ) -> List[str]:
        """
        Identify which fields need clarification.
        
        Rules:
        1. Low confidence fields (< 0.7)
        2. Critical fields with any uncertainty (purpose, amount, income)
        3. Contradictions with current context
        """
        needs = []
        
        # Check low confidence fields
        for field_name, confidence in field_confidence.items():
            if confidence < 0.7:
                needs.append(field_name)
        
        # Critical fields need higher bar
        critical_fields = ["purpose", "loan_amount", "monthly_income", "employment_type"]
        for field_name in critical_fields:
            value = getattr(context, field_name, None)
            conf = field_confidence.get(field_name, 0.5)
            
            if value is not None and conf < 0.8:
                if field_name not in needs:
                    needs.append(field_name)
        
        # Check for contradictions
        if current_context.purpose and context.purpose:
            if current_context.purpose != context.purpose:
                needs.append("purpose_contradiction")
        
        return needs
    
    def _log_decision(self, decision: ExtractionDecision):
        """Log routing decision for audit trail"""
        self.logger.info(
            f"Extraction decision: action={decision.action}, "
            f"confidence={decision.confidence:.2f}, "
            f"low_confidence_fields={decision.low_confidence_fields}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# LLM Integration Layer
# ─────────────────────────────────────────────────────────────────────────────

class LLMOrchestratorIntegration:
    """
    Integration layer between LLM extraction and deterministic orchestrator.
    
    This class wraps the LNAIOrchestrator and adds:
    1. LLM-based intent extraction (replaces regex)
    2. Confidence-based routing
    3. Graceful fallback to regex/explicit questioning
    4. XML-tagged response generation
    5. Audit logging
    
    Usage:
        config = IntegrationConfig()
        integration = LLMOrchestratorIntegration(config)
        
        response = integration.process_message("I need a home loan for $400,000")
        
        # Response includes:
        # - Natural language text
        # - Extracted context with confidence scores
        # - XML tags for UI cards
        # - Metadata for tracking
    """
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        self.config = config or IntegrationConfig()
        self.orchestrator = LNAIOrchestrator()
        self.router = ConfidenceRouter(self.config)
        self.intent_extractor = IntentExtractorTool(
            model_name=self.config.model_name,
            ollama_base_url=self.config.ollama_base_url,
            temperature=self.config.temperature
        )
        self.logger = logging.getLogger(__name__)
        
        # Metrics
        self.metrics = {
            "total_messages": 0,
            "llm_extractions": 0,
            "fallbacks": 0,
            "clarifications": 0,
            "accepts": 0,
        }
    
    def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process user message with LLM integration.
        
        Flow:
        1. Call LLM for intent extraction
        2. Route based on confidence
        3. Update orchestrator context
        4. Generate response with XML tags
        5. Log metrics
        
        Args:
            user_message: User's message text
            
        Returns:
            Dict with response, metadata, and extraction info
        """
        self.metrics["total_messages"] += 1
        
        # Add to conversation history
        self.orchestrator.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Extract intent using LLM
        extraction_result = self._extract_intent(user_message)
        
        # Route based on confidence
        decision = self.router.route(
            extraction_result,
            self.orchestrator.state.captured_context
        )
        
        # Apply decision
        if decision.should_accept():
            self._apply_extraction(decision.context, decision.field_confidence)
            self.metrics["accepts"] += 1
        
        elif decision.needs_clarification():
            # Apply partial extraction, ask for clarification
            self._apply_partial_extraction(decision)
            self.metrics["clarifications"] += 1
        
        elif decision.should_use_fallback():
            # Use regex fallback
            self._use_regex_fallback(user_message)
            self.metrics["fallbacks"] += 1
        
        # Generate response
        response = self._generate_response(user_message, decision)
        
        # Add assistant response to history
        self.orchestrator.conversation_history.append({
            "role": "assistant",
            "content": response.get("response", "")
        })
        
        return response
    
    def _extract_intent(self, user_message: str) -> IntentExtractionResult:
        """
        Extract intent using LLM.
        
        Implements retry logic with exponential backoff.
        """
        self.metrics["llm_extractions"] += 1
        
        last_error = None
        
        for attempt in range(self.config.max_llm_retries):
            try:
                # Call LLM extractor
                result = self.intent_extractor.run(
                    conversation_history=self.orchestrator.conversation_history
                )
                
                return IntentExtractionResult.model_validate_json(result)
                
            except Exception as e:
                last_error = str(e)
                self.logger.warning(
                    f"LLM extraction attempt {attempt + 1} failed: {last_error}"
                )
                
                if attempt < self.config.max_llm_retries - 1:
                    # Exponential backoff
                    import time
                    time.sleep(2 ** attempt)
        
        # All retries failed
        self.logger.error(f"LLM extraction failed after {self.config.max_llm_retries} attempts")
        
        return IntentExtractionResult(
            context=IntentAnalysis(),
            confidence=0.0,
            field_confidence={},
            parse_errors=last_error
        )
    
    def _apply_extraction(
        self,
        context: CapturedContext,
        field_confidence: Dict[str, float]
    ):
        """Apply high-confidence extraction to orchestrator context"""
        current = self.orchestrator.state.captured_context
        
        # Update fields from extracted context
        for field_name, value in context.model_dump().items():
            if value is not None and field_name != "field_confidence":
                # Don't overwrite stage - it's an enum, not a context field
                if field_name != "stage":
                    setattr(current, field_name, value)
        
        # Store confidence scores
        current.field_confidence = field_confidence
    
    def _apply_partial_extraction(self, decision: ExtractionDecision):
        """Apply partial extraction, mark fields needing clarification"""
        current = self.orchestrator.state.captured_context
        
        # Only apply high-confidence fields
        for field_name, value in decision.context.model_dump().items():
            conf = decision.field_confidence.get(field_name, 0.5)
            
            if value is not None and conf >= 0.7 and field_name != "field_confidence":
                setattr(current, field_name, value)
        
        # Store confidence scores
        current.field_confidence = decision.field_confidence
    
    def _use_regex_fallback(self, user_message: str):
        """Use original regex-based extraction as fallback"""
        # Call original orchestrator method
        message_lower = user_message.lower()
        current = self.orchestrator.state.captured_context
        
        # Extract purpose (from original code)
        if any(word in message_lower for word in ["home", "house", "property", "buy house"]):
            current.purpose = "home_purchase"
        elif any(word in message_lower for word in ["car", "auto", "vehicle", "buy car"]):
            current.purpose = "auto"
        elif any(word in message_lower for word in ["personal", "debt", "consolidation"]):
            current.purpose = "personal"
        elif any(word in message_lower for word in ["business", "commercial"]):
            current.purpose = "business"
        elif any(word in message_lower for word in ["education", "study", "tuition"]):
            current.purpose = "education"
        elif any(word in message_lower for word in ["medical", "health"]):
            current.purpose = "medical"
        
        # Mark as low confidence
        current.field_confidence["purpose"] = 0.3
    
    def _generate_response(
        self,
        user_message: str,
        decision: ExtractionDecision
    ) -> Dict[str, Any]:
        """
        Generate response with XML tags.
        
        Uses LLM for natural language, structured parser for XML tags.
        """
        # Get current stage (handle both enum and string)
        stage_value = self.orchestrator.state.stage
        if hasattr(stage_value, 'value'):
            stage = stage_value.value
        else:
            stage = stage_value  # Already a string
        
        # Build prompt for response generation
        prompt = RESPONSE_GENERATION_PROMPT.format(
            mode=self._get_current_mode(),
            stage=stage,
            captured_context=self.orchestrator.state.captured_context.model_dump(),
            loan_snapshot=None,
            recommendations=None,
        )
        
        # For now, use simple template-based response
        # (Full LLM response generation in Task 1.6)
        response_text = self._generate_template_response(user_message, decision)
        
        return {
            "response": response_text,
            "stage": stage,
            "extraction": {
                "confidence": decision.confidence,
                "action": decision.action,
                "field_confidence": decision.field_confidence,
            },
            "metadata": {
                "metrics": self.metrics.copy(),
            }
        }
    
    def _generate_template_response(
        self,
        user_message: str,
        decision: ExtractionDecision
    ) -> str:
        """Generate template-based response (placeholder for Task 1.6)"""
        current = self.orchestrator.state.captured_context
        
        # Get stage value (handle both enum and string)
        stage_value = self.orchestrator.state.stage
        if hasattr(stage_value, 'value'):
            stage = stage_value.value
        else:
            stage = stage_value  # Already a string

        # Stage-based responses (compare with string values)
        if stage == "intent_capture":
            if current.purpose:
                self.orchestrator.state.stage = ConversationStage.FINANCIAL_CONTEXT
                return (
                    f"Perfect! I'm excited to help you navigate your {current.purpose.replace('_', ' ')} loan. "
                    "To tailor a borrowing strategy that really fits your life, I'd like to understand your current financial context. "
                    "Are you currently salaried, self-employed, or working as a contractor? And what does your typical monthly income look like before deductions?"
                )
            else:
                return (
                    "Hello! I'm your Loan Navigator. I'm here to help you find the most efficient path to the funding you need. "
                    "To get us started, could you tell me a bit about what you're looking to achieve? "
                    "Are you thinking about a new home, a car, starting a business, or perhaps a personal loan?"
                )

        elif stage == "financial_context":
            if current.monthly_income and current.employment_type:
                self.orchestrator.state.stage = ConversationStage.READY_FOR_METRICS
                return (
                    "Excellent, thank you for sharing that! Now I have a good understanding of your financial situation. "
                    "How much are you looking to borrow? And just so I can factor everything in — are there any current loan repayments, "
                    "credit card balances, or other monthly commitments I should know about?"
                )
            else:
                return (
                    "Thanks for sharing that! To help me understand your financial picture better — "
                    "are you currently salaried, self-employed, or working as a contractor? "
                    "And what does your typical monthly income look like before deductions?"
                )
        
        # Default fallback
        return "Thank you for that information. Let me process this and get back to you with the next steps."
    
    def _get_current_mode(self) -> Literal["advisory", "application", "completion"]:
        """Determine current conversation mode based on stage"""
        # Get stage value (handle both enum and string)
        stage_value = self.orchestrator.state.stage
        if hasattr(stage_value, 'value'):
            stage = stage_value.value
        else:
            stage = stage_value  # Already a string
        
        # Compare with string values (ConversationStage enum values are strings)
        if stage in [
            "intent_capture",
            "financial_context",
            "ready_for_metrics",
            "ready_for_recommendation",
        ]:
            return "advisory"

        elif stage in [
            "applicant_identity",
            "application_submitted",
        ]:
            return "application"

        else:
            return "completion"
    
    def get_metrics(self) -> Dict[str, int]:
        """Get integration metrics"""
        return self.metrics.copy()


# ─────────────────────────────────────────────────────────────────────────────
# Factory Function
# ─────────────────────────────────────────────────────────────────────────────

def create_llm_orchestrator(
    config: Optional[IntegrationConfig] = None,
    log_level: str = "INFO"
) -> LLMOrchestratorIntegration:
    """
    Factory function to create configured LLM orchestrator.
    
    Args:
        config: Optional configuration override
        log_level: Logging level
        
    Returns:
        Configured LLMOrchestratorIntegration instance
    """
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create integration
    integration = LLMOrchestratorIntegration(config)
    
    return integration


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Classes
    "IntegrationConfig",
    "ExtractionDecision",
    "ConfidenceRouter",
    "LLMOrchestratorIntegration",
    
    # Factory
    "create_llm_orchestrator",
]
