"""
Unit Tests for XML Tag Response Generator

Tests response generation with proper XML tag formatting.
"""

import pytest
import json

from src.agents.response_generator import (
    XMLTagResponseGenerator,
    ResponseTemplate,
    IntentCaptureStrategy,
    FinancialContextStrategy,
    RecommendationStrategy,
    ApplicationSubmissionStrategy,
    ResponseGeneratorFactory,
    generate_xml_response,
    ConversationStage,
)
from src.agents.graph_state import (
    CapturedContext,
    LoanSnapshot,
    LoanRecommendation,
    DocumentsChecklist,
)
from src.agents.structured_parser import IntentAnalysis, PhaseUpdate


class TestXMLTagResponseGenerator:
    """Test XML tag response generation"""
    
    def test_generate_basic_response(self):
        """Test generating basic response with chat text only"""
        generator = XMLTagResponseGenerator()
        
        response = generator.generate(
            chat_text="Hello! How can I help you?"
        )
        
        assert response == "Hello! How can I help you?"
    
    def test_generate_with_intent(self):
        """Test generating response with intent analysis"""
        generator = XMLTagResponseGenerator()
        
        intent = IntentAnalysis(
            purpose="home_purchase",
            urgency="high",
            seriousness_score=85,
            fit_score=80,
        )
        
        response = generator.generate(
            chat_text="I understand you need a home loan.",
            intent=intent,
        )
        
        assert "I understand you need a home loan." in response
        assert "<intent_analysis>" in response
        assert "</intent_analysis>" in response
        assert "home_purchase" in response
        assert "85" in response  # seriousness_score
    
    def test_generate_with_snapshot(self):
        """Test generating response with loan snapshot"""
        generator = XMLTagResponseGenerator()
        
        snapshot = LoanSnapshot(
            loan_amount=400000.0,
            down_payment=100000.0,
            property_value=500000.0,
            estimated_emi=2800.0,
            tenure_years=20,
            interest_rate=8.5,
            total_interest=280000.0,
            total_repayment=680000.0,
            ltv_ratio=80.0,
            currency="USD",
        )
        
        response = generator.generate(
            chat_text="Here's your loan snapshot.",
            snapshot=snapshot,
        )
        
        assert "<loan_snapshot>" in response
        assert "</loan_snapshot>" in response
        assert "400000" in response
        assert "2800" in response
    
    def test_generate_with_recommendations(self):
        """Test generating response with loan recommendations"""
        generator = XMLTagResponseGenerator()
        
        recommendations = [
            LoanRecommendation(
                name="Fast Track",
                type="aggressive",
                interest_rate=7.5,
                tenure_years=15,
                monthly_emi=3200.0,
                total_interest=436000.0,
                total_repayment=836000.0,
                pros=["Lowest interest", "Fast payoff"],
                cons=["High monthly payment"],
                recommended=False,
            ),
            LoanRecommendation(
                name="Standard",
                type="balanced",
                interest_rate=8.5,
                tenure_years=20,
                monthly_emi=2800.0,
                total_interest=550000.0,
                total_repayment=950000.0,
                pros=["Manageable payments"],
                cons=["Higher total interest"],
                recommended=True,
            ),
        ]
        
        response = generator.generate(
            chat_text="Here are your options.",
            recommendations=recommendations,
        )
        
        assert "<loan_recommendations>" in response
        assert "</loan_recommendations>" in response
        assert "Fast Track" in response
        assert "Standard" in response
        assert len(response.split("<loan_recommendations>")) == 2  # Only one tag
    
    def test_generate_with_application(self):
        """Test generating response with loan application"""
        generator = XMLTagResponseGenerator()
        
        application = {
            "first_name": "Marcus",
            "last_name": "Williams",
            "email": "marcus.w@email.com",
            "phone": "+1-868-555-1234",
            "loan_type": "Home Loan",
            "loan_amount": "$400,000",
        }
        
        response = generator.generate(
            chat_text="Application submitted!",
            application=application,
        )
        
        assert "<loan_application>" in response
        assert "</loan_application>" in response
        assert "Marcus" in response
        assert "marcus.w@email.com" in response
    
    def test_generate_with_documents(self):
        """Test generating response with documents checklist"""
        generator = XMLTagResponseGenerator()
        
        documents = DocumentsChecklist(
            identity=[
                {"name": "National ID", "description": "Photo ID"},
            ],
            income=[
                {"name": "Pay Slips", "description": "Last 3 months"},
            ]
        )
        
        response = generator.generate(
            chat_text="Please upload these documents.",
            documents=documents,
        )
        
        assert "<documents_checklist>" in response
        assert "</documents_checklist>" in response
        assert "National ID" in response
        assert "Pay Slips" in response
    
    def test_generate_with_phase_update(self):
        """Test generating response with phase update"""
        generator = XMLTagResponseGenerator()
        
        phase_update = PhaseUpdate(
            phase_id="phase-application-submitted",
            reason="All required fields collected",
        )
        
        response = generator.generate(
            chat_text="Moving to next phase.",
            phase_update=phase_update,
        )
        
        assert "<phase_update>" in response
        assert "</phase_update>" in response
        assert "phase-application-submitted" in response
    
    def test_generate_with_multiple_tags(self):
        """Test generating response with multiple XML tags"""
        generator = XMLTagResponseGenerator()
        
        intent = IntentAnalysis(purpose="home_purchase")
        snapshot = LoanSnapshot(
            loan_amount=400000.0,
            down_payment=100000.0,
            property_value=500000.0,
            estimated_emi=2800.0,
            tenure_years=20,
            interest_rate=8.5,
            total_interest=280000.0,
            total_repayment=680000.0,
            ltv_ratio=80.0,
            currency="USD",
        )
        recommendations = [
            LoanRecommendation(
                name="Option 1",
                type="aggressive",
                interest_rate=7.0,
                tenure_years=15,
                monthly_emi=3000.0,
                total_interest=100000.0,
                total_repayment=500000.0,
                pros=[],
                cons=[],
                recommended=True,
            )
        ]
        
        response = generator.generate(
            chat_text="Here's your analysis.",
            intent=intent,
            snapshot=snapshot,
            recommendations=recommendations,
        )
        
        assert "<intent_analysis>" in response
        assert "<loan_snapshot>" in response
        assert "<loan_recommendations>" in response
        # Verify order: chat text first, then tags
        assert response.startswith("Here's your analysis.")
    
    def test_generate_pretty_print(self):
        """Test JSON formatting with pretty print"""
        generator = XMLTagResponseGenerator(pretty_print=True)
        
        intent = IntentAnalysis(purpose="home_purchase", seriousness_score=85)
        
        response = generator.generate(
            chat_text="Test",
            intent=intent,
        )
        
        # Pretty print should have indentation
        assert "\n  " in response  # Indentation present
    
    def test_generate_compact_print(self):
        """Test JSON formatting without pretty print"""
        generator = XMLTagResponseGenerator(pretty_print=False)
        
        intent = IntentAnalysis(purpose="home_purchase", seriousness_score=85)
        
        response = generator.generate(
            chat_text="Test",
            intent=intent,
        )
        
        # Compact should be single line JSON
        assert '"purpose": "home_purchase"' in response or '"purpose":"home_purchase"' in response


class TestResponseTemplate:
    """Test response template model"""
    
    def test_template_defaults(self):
        """Test template default values"""
        template = ResponseTemplate(chat_text="Hello")
        
        assert template.chat_text == "Hello"
        assert template.include_intent is True
        assert template.include_snapshot is False
        assert template.include_recommendations is False
        assert template.include_application is False
        assert template.include_documents is False
        assert template.include_phase_update is False
    
    def test_template_custom_values(self):
        """Test template with custom values"""
        template = ResponseTemplate(
            chat_text="Hello",
            include_snapshot=True,
            include_recommendations=True,
        )
        
        assert template.include_snapshot is True
        assert template.include_recommendations is True


class TestIntentCaptureStrategy:
    """Test intent capture stage strategy"""
    
    def test_initial_greeting(self):
        """Test initial greeting when no purpose captured"""
        strategy = IntentCaptureStrategy()
        context = CapturedContext()
        
        response = strategy.generate(
            context=context,
            stage=ConversationStage.INTENT_CAPTURE,
            has_purpose=False,
        )
        
        assert "Hello" in response or "Loan Navigator" in response
        assert "<intent_analysis>" in response
    
    def test_follow_up_with_purpose(self):
        """Test follow-up when purpose captured"""
        strategy = IntentCaptureStrategy()
        context = CapturedContext(purpose="home_purchase")
        
        response = strategy.generate(
            context=context,
            stage=ConversationStage.INTENT_CAPTURE,
            has_purpose=True,
        )
        
        assert "home_purchase" in response.lower() or "property" in response.lower()
        assert "<intent_analysis>" in response


class TestFinancialContextStrategy:
    """Test financial context stage strategy"""
    
    def test_ask_employment_income(self):
        """Test asking for employment and income"""
        strategy = FinancialContextStrategy()
        context = CapturedContext(purpose="home_purchase")
        
        response = strategy.generate(
            context=context,
            stage=ConversationStage.FINANCIAL_CONTEXT,
            has_employment=False,
            has_income=False,
        )
        
        assert "salaried" in response.lower() or "self-employed" in response.lower()
        assert "income" in response.lower()
    
    def test_ask_loan_amount(self):
        """Test asking for loan amount when have employment/income"""
        strategy = FinancialContextStrategy()
        context = CapturedContext(
            purpose="home_purchase",
            employment_type="salaried",
            monthly_income=8000,
        )
        
        response = strategy.generate(
            context=context,
            stage=ConversationStage.FINANCIAL_CONTEXT,
            has_employment=True,
            has_income=True,
        )
        
        assert "borrow" in response.lower() or "loan amount" in response.lower()
        assert "debt" in response.lower() or "commitment" in response.lower()


class TestRecommendationStrategy:
    """Test recommendation presentation strategy"""
    
    def test_present_recommendations(self):
        """Test presenting loan recommendations"""
        strategy = RecommendationStrategy()
        context = CapturedContext(
            purpose="home_purchase",
            loan_amount=400000,
            monthly_income=8000,
        )
        
        snapshot = LoanSnapshot(
            loan_amount=400000.0,
            down_payment=100000.0,
            property_value=500000.0,
            estimated_emi=2800.0,
            tenure_years=20,
            interest_rate=8.5,
            total_interest=280000.0,
            total_repayment=680000.0,
            ltv_ratio=80.0,
            currency="USD",
        )
        
        recommendations = [
            LoanRecommendation(
                name="Fast Track",
                type="aggressive",
                interest_rate=7.5,
                tenure_years=15,
                monthly_emi=3200.0,
                total_interest=436000.0,
                total_repayment=836000.0,
                pros=["Low interest"],
                cons=["High payment"],
                recommended=True,
            )
        ]
        
        response = strategy.generate(
            context=context,
            stage=ConversationStage.READY_FOR_RECOMMENDATION,
            snapshot=snapshot,
            recommendations=recommendations,
        )
        
        assert "analysed" in response.lower() or "options" in response.lower()
        assert "<loan_snapshot>" in response
        assert "<loan_recommendations>" in response


class TestApplicationSubmissionStrategy:
    """Test application submission strategy"""
    
    def test_submit_application(self):
        """Test application submission response"""
        strategy = ApplicationSubmissionStrategy()
        context = CapturedContext(
            purpose="home_purchase",
            borrower_name="Marcus Williams",
            email="marcus.w@email.com",
            phone="+1-868-555-1234",
        )
        
        application = {
            "first_name": "Marcus",
            "last_name": "Williams",
            "email": "marcus.w@email.com",
        }
        
        documents = DocumentsChecklist(
            required_now=[
                {"name": "National ID", "description": "Photo ID", "required": True}
            ]
        )
        
        response = strategy.generate(
            context=context,
            stage=ConversationStage.APPLICATION_SUBMITTED,
            application_data=application,
            documents=documents,
        )
        
        assert "submitted" in response.lower() or "application" in response.lower()
        assert "<loan_application>" in response
        assert "<documents_checklist>" in response


class TestResponseGeneratorFactory:
    """Test factory for response strategies"""
    
    def test_get_intent_capture_strategy(self):
        """Test getting intent capture strategy"""
        strategy = ResponseGeneratorFactory.get_strategy(
            ConversationStage.INTENT_CAPTURE
        )
        
        assert isinstance(strategy, IntentCaptureStrategy)
    
    def test_get_financial_context_strategy(self):
        """Test getting financial context strategy"""
        strategy = ResponseGeneratorFactory.get_strategy(
            ConversationStage.FINANCIAL_CONTEXT
        )
        
        assert isinstance(strategy, FinancialContextStrategy)
    
    def test_get_recommendation_strategy(self):
        """Test getting recommendation strategy"""
        strategy = ResponseGeneratorFactory.get_strategy(
            ConversationStage.READY_FOR_RECOMMENDATION
        )
        
        assert isinstance(strategy, RecommendationStrategy)
    
    def test_generate_response_factory_method(self):
        """Test factory generate_response method"""
        context = CapturedContext(purpose="home_purchase")
        
        response = ResponseGeneratorFactory.generate_response(
            stage=ConversationStage.INTENT_CAPTURE,
            context=context,
        )
        
        assert response is not None
        assert "<intent_analysis>" in response


class TestConvenienceFunction:
    """Test generate_xml_response convenience function"""
    
    def test_generate_xml_response(self):
        """Test convenience function"""
        intent = IntentAnalysis(purpose="auto_loan")
        
        response = generate_xml_response(
            chat_text="I can help with a car loan.",
            intent=intent,
            pretty_print=False,
        )
        
        assert "I can help with a car loan." in response
        assert "<intent_analysis>" in response
        assert "auto_loan" in response


class TestIntegration:
    """Integration tests with realistic scenarios"""
    
    def test_complete_borrower_journey_response(self):
        """Test generating responses for complete borrower journey"""
        context = CapturedContext(
            purpose="home_purchase",
            loan_amount=400000,
            monthly_income=8000,
            employment_type="salaried",
            borrower_name="Marcus Williams",
            email="marcus.w@email.com",
            seriousness_score=85,
            fit_score=80,
        )
        
        # Stage 1: Intent capture
        response1 = ResponseGeneratorFactory.generate_response(
            stage=ConversationStage.INTENT_CAPTURE,
            context=context,
            has_purpose=True,
        )
        assert "<intent_analysis>" in response1
        
        # Stage 2: Financial context
        response2 = ResponseGeneratorFactory.generate_response(
            stage=ConversationStage.FINANCIAL_CONTEXT,
            context=context,
            has_employment=True,
            has_income=True,
        )
        assert "<intent_analysis>" in response2
        
        # Stage 3: Recommendations
        snapshot = LoanSnapshot(
            loan_amount=400000.0,
            down_payment=100000.0,
            property_value=500000.0,
            estimated_emi=2800.0,
            tenure_years=20,
            interest_rate=8.5,
            total_interest=280000.0,
            total_repayment=680000.0,
            ltv_ratio=80.0,
            currency="USD",
        )
        
        recommendations = [
            LoanRecommendation(
                name="Fast Track",
                type="aggressive",
                interest_rate=7.5,
                tenure_years=15,
                monthly_emi=3200.0,
                total_interest=436000.0,
                total_repayment=836000.0,
                pros=["Low interest"],
                cons=["High payment"],
                recommended=True,
            )
        ]
        
        response3 = ResponseGeneratorFactory.generate_response(
            stage=ConversationStage.READY_FOR_RECOMMENDATION,
            context=context,
            snapshot=snapshot,
            recommendations=recommendations,
        )
        
        assert "<loan_snapshot>" in response3
        assert "<loan_recommendations>" in response3


# ─────────────────────────────────────────────────────────────────────────────
# Run Tests
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
