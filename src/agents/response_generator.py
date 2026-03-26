"""
XML Tag Response Generator for Agentic Orchestrator

Generates LLM responses with properly formatted XML tags for UI card rendering.
Supports all LNAI-style tags: intent_analysis, loan_snapshot, loan_recommendations,
loan_application, documents_checklist, and phase_update.

This module ensures:
1. Valid JSON within XML tags
2. Proper escaping and formatting
3. Consistent structure across responses
4. Caribbean regional context in responses
"""

from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel
import json

from src.agents.orchestrator import (
    CapturedContext,
    LoanSnapshot,
    LoanRecommendation,
    DocumentsChecklist,
    ConversationStage,
)
from src.agents.structured_parser import (
    IntentAnalysis,
    PhaseUpdate,
)


# ─────────────────────────────────────────────────────────────────────────────
# Response Templates
# ─────────────────────────────────────────────────────────────────────────────

class ResponseTemplate(BaseModel):
    """Template for generating structured responses"""
    chat_text: str  # Natural language response
    include_intent: bool = True
    include_snapshot: bool = False
    include_recommendations: bool = False
    include_application: bool = False
    include_documents: bool = False
    include_phase_update: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# XML Tag Generator
# ─────────────────────────────────────────────────────────────────────────────

class XMLTagResponseGenerator:
    """
    Generates LLM responses with XML-tagged structured data.
    
    Usage:
        generator = XMLTagResponseGenerator()
        response = generator.generate(
            chat_text="I've analyzed your financials...",
            intent=intent_analysis,
            snapshot=loan_snapshot,
            recommendations=[rec1, rec2, rec3]
        )
        
        # Response contains:
        # Natural language text + <intent_analysis>...</intent_analysis>
        # + <loan_snapshot>...</loan_snapshot> + <loan_recommendations>...</loan_recommendations>
    """
    
    def __init__(self, pretty_print: bool = True):
        """
        Initialize generator.
        
        Args:
            pretty_print: If True, format JSON with indentation
        """
        self.pretty_print = pretty_print
    
    def generate(
        self,
        chat_text: str,
        intent: Optional[IntentAnalysis] = None,
        snapshot: Optional[LoanSnapshot] = None,
        recommendations: Optional[List[LoanRecommendation]] = None,
        application: Optional[Dict[str, Any]] = None,
        documents: Optional[DocumentsChecklist] = None,
        phase_update: Optional[PhaseUpdate] = None,
    ) -> str:
        """
        Generate complete response with XML tags.
        
        Args:
            chat_text: Natural language response text
            intent: Intent analysis data
            snapshot: Loan snapshot data
            recommendations: List of loan recommendations
            application: Loan application data
            documents: Documents checklist
            phase_update: Phase progression update
            
        Returns:
            Complete response with XML-tagged structured data
        """
        parts = [chat_text.strip()]
        
        # Add XML-tagged sections
        if intent:
            parts.append(self._format_intent(intent))
        
        if snapshot:
            parts.append(self._format_snapshot(snapshot))
        
        if recommendations:
            parts.append(self._format_recommendations(recommendations))
        
        if application:
            parts.append(self._format_application(application))
        
        if documents:
            parts.append(self._format_documents(documents))
        
        if phase_update:
            parts.append(self._format_phase_update(phase_update))
        
        return "\n\n".join(parts)
    
    def _format_json(self, data: Dict[str, Any]) -> str:
        """Format data as JSON string"""
        if self.pretty_print:
            return json.dumps(data, indent=2, default=str)
        else:
            return json.dumps(data, default=str)
    
    def _format_intent(self, intent: IntentAnalysis) -> str:
        """Format intent analysis XML tag"""
        data = intent.model_dump(exclude_none=True)
        json_str = self._format_json(data)
        return f"<intent_analysis>\n{json_str}\n</intent_analysis>"
    
    def _format_snapshot(self, snapshot: LoanSnapshot) -> str:
        """Format loan snapshot XML tag"""
        data = snapshot.model_dump(exclude_none=True)
        json_str = self._format_json(data)
        return f"<loan_snapshot>\n{json_str}\n</loan_snapshot>"
    
    def _format_recommendations(self, recommendations: List[LoanRecommendation]) -> str:
        """Format loan recommendations XML tag"""
        data = [rec.model_dump() for rec in recommendations]
        json_str = self._format_json(data)
        return f"<loan_recommendations>\n{json_str}\n</loan_recommendations>"
    
    def _format_application(self, application: Dict[str, Any]) -> str:
        """Format loan application XML tag"""
        json_str = self._format_json(application)
        return f"<loan_application>\n{json_str}\n</loan_application>"
    
    def _format_documents(self, documents: DocumentsChecklist) -> str:
        """Format documents checklist XML tag"""
        data = documents.model_dump(exclude_none=True)
        json_str = self._format_json(data)
        return f"<documents_checklist>\n{json_str}\n</documents_checklist>"
    
    def _format_phase_update(self, phase_update: PhaseUpdate) -> str:
        """Format phase update XML tag"""
        data = phase_update.model_dump(exclude_none=True)
        json_str = self._format_json(data)
        return f"<phase_update>\n{json_str}\n</phase_update>"


# ─────────────────────────────────────────────────────────────────────────────
# Response Generation Strategies
# ─────────────────────────────────────────────────────────────────────────────

class ResponseStrategy:
    """Base class for response generation strategies"""
    
    def generate(
        self,
        context: CapturedContext,
        stage: ConversationStage,
        **kwargs
    ) -> str:
        """Generate response based on context and stage"""
        raise NotImplementedError


class IntentCaptureStrategy(ResponseStrategy):
    """Strategy for intent capture stage responses"""
    
    def generate(
        self,
        context: CapturedContext,
        stage: ConversationStage,
        has_purpose: bool = False,
        **kwargs
    ) -> str:
        generator = XMLTagResponseGenerator()
        
        if not has_purpose or not context.purpose:
            # Initial greeting
            chat_text = (
                "Hello! I'm your Loan Navigator. I'm here to help you find the most "
                "efficient path to the funding you need. To get us started, could you "
                "tell me a bit about what you're looking to achieve? Are you thinking "
                "about a new home, a car, starting a business, or perhaps a personal loan?"
            )
        else:
            # Purpose captured, move to next stage
            chat_text = (
                f"That's wonderful! A {context.purpose.replace('_', ' ')} is a major milestone. "
                "To help me structure the best path for you, could you share more details? "
                "Specifically, I'd love to know what the property value or loan amount is, "
                "and what you're planning for a down payment so we can find the most affordable option."
            )
        
        # Always include intent analysis
        intent = IntentAnalysis(
            purpose=context.purpose,
            urgency=context.urgency,
            seriousness_score=context.seriousness_score,
            fit_score=context.fit_score,
        )
        
        return generator.generate(
            chat_text=chat_text,
            intent=intent
        )


class FinancialContextStrategy(ResponseStrategy):
    """Strategy for financial context stage responses"""
    
    def generate(
        self,
        context: CapturedContext,
        stage: ConversationStage,
        has_income: bool = False,
        has_employment: bool = False,
        **kwargs
    ) -> str:
        generator = XMLTagResponseGenerator()
        
        if not has_employment or not has_income:
            # Ask for employment and income
            chat_text = (
                "Perfect! I'm excited to help you navigate this financial journey. "
                "To tailor a borrowing strategy that really fits your life, I'd like "
                "to understand your current financial context. Are you currently "
                "salaried, self-employed, or working as a contractor? And what does "
                "your typical monthly income look like before deductions?"
            )
        else:
            # Have employment and income, ask for loan amount
            chat_text = (
                "Excellent, thank you for sharing that! Now I have a good understanding "
                "of your financial situation. How much are you looking to borrow? And "
                "just so I can factor everything in — are there any current loan "
                "repayments, credit card balances, or other monthly commitments I should "
                "know about?"
            )
        
        intent = IntentAnalysis(
            purpose=context.purpose,
            employment_type=context.employment_type,
            monthly_income=f"${float(context.monthly_income):,}" if isinstance(context.monthly_income, (int, float)) else str(context.monthly_income) if context.monthly_income else None,
            existing_debts=f"${context.existing_debts:,}" if context.existing_debts else None,
            seriousness_score=context.seriousness_score,
            fit_score=context.fit_score,
        )
        
        return generator.generate(
            chat_text=chat_text,
            intent=intent
        )


class RecommendationStrategy(ResponseStrategy):
    """Strategy for presenting loan recommendations"""
    
    def generate(
        self,
        context: CapturedContext,
        stage: ConversationStage,
        snapshot: Optional[LoanSnapshot] = None,
        recommendations: Optional[List[LoanRecommendation]] = None,
        **kwargs
    ) -> str:
        generator = XMLTagResponseGenerator()
        
        chat_text = (
            "I've analysed your financials and put together the ideal path for you — "
            "here are your top options, with my recommendation highlighted. "
            "Take a look at the options below and let me know which one you prefer."
        )
        
        intent = IntentAnalysis(
            purpose=context.purpose,
            loan_amount=f"${context.loan_amount:,}" if context.loan_amount else None,
            monthly_income=f"${float(context.monthly_income):,}" if isinstance(context.monthly_income, (int, float)) else str(context.monthly_income) if context.monthly_income else None,
            seriousness_score=context.seriousness_score,
            fit_score=context.fit_score,
            next_conversation_angle="Wait for borrower to select recommendation",
        )
        
        return generator.generate(
            chat_text=chat_text,
            intent=intent,
            snapshot=snapshot,
            recommendations=recommendations,
        )


class ApplicationSubmissionStrategy(ResponseStrategy):
    """Strategy for application submission responses"""
    
    def generate(
        self,
        context: CapturedContext,
        stage: ConversationStage,
        application_data: Optional[Dict[str, Any]] = None,
        documents: Optional[DocumentsChecklist] = None,
        **kwargs
    ) -> str:
        generator = XMLTagResponseGenerator()
        
        chat_text = (
            "### Success! Your application is in motion.\n\n"
            f"I've officially submitted your request. To complete the verification, "
            f"please upload the required documents below. Our system will process them instantly."
        )
        
        intent = IntentAnalysis(
            purpose=context.purpose,
            borrower_name=context.borrower_name,
            email=context.email,
            phone=context.phone,
            seriousness_score=90,  # High seriousness at submission
            fit_score=context.fit_score,
            next_conversation_angle="Awaiting document upload and STP processing",
        )
        
        return generator.generate(
            chat_text=chat_text,
            intent=intent,
            application=application_data,
            documents=documents,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Response Generator Factory
# ─────────────────────────────────────────────────────────────────────────────

class ResponseGeneratorFactory:
    """Factory for creating appropriate response strategy based on stage"""
    
    STRATEGIES = {
        ConversationStage.INTENT_CAPTURE: IntentCaptureStrategy,
        ConversationStage.FINANCIAL_CONTEXT: FinancialContextStrategy,
        ConversationStage.READY_FOR_METRICS: RecommendationStrategy,
        ConversationStage.READY_FOR_RECOMMENDATION: RecommendationStrategy,
        ConversationStage.APPLICATION_SUBMITTED: ApplicationSubmissionStrategy,
    }
    
    @classmethod
    def get_strategy(cls, stage: ConversationStage) -> ResponseStrategy:
        """Get appropriate strategy for stage"""
        strategy_class = cls.STRATEGIES.get(stage, IntentCaptureStrategy)
        return strategy_class()
    
    @classmethod
    def generate_response(
        cls,
        stage: ConversationStage,
        context: CapturedContext,
        **kwargs
    ) -> str:
        """Generate response using appropriate strategy"""
        strategy = cls.get_strategy(stage)
        return strategy.generate(context=context, stage=stage, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────────────────────

def generate_xml_response(
    chat_text: str,
    intent: Optional[IntentAnalysis] = None,
    snapshot: Optional[LoanSnapshot] = None,
    recommendations: Optional[List[LoanRecommendation]] = None,
    application: Optional[Dict[str, Any]] = None,
    documents: Optional[DocumentsChecklist] = None,
    pretty_print: bool = True,
) -> str:
    """
    Convenience function to generate XML-tagged response.
    
    Args:
        chat_text: Natural language response
        intent: Intent analysis data
        snapshot: Loan snapshot data
        recommendations: Loan recommendations
        application: Application data
        documents: Documents checklist
        pretty_print: Format JSON with indentation
        
    Returns:
        Complete response with XML tags
    """
    generator = XMLTagResponseGenerator(pretty_print=pretty_print)
    return generator.generate(
        chat_text=chat_text,
        intent=intent,
        snapshot=snapshot,
        recommendations=recommendations,
        application=application,
        documents=documents,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Classes
    "XMLTagResponseGenerator",
    "ResponseTemplate",
    "ResponseStrategy",
    "IntentCaptureStrategy",
    "FinancialContextStrategy",
    "RecommendationStrategy",
    "ApplicationSubmissionStrategy",
    "ResponseGeneratorFactory",
    
    # Convenience functions
    "generate_xml_response",
]
