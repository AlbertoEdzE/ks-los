"""
Unit Tests for LLM Integration Layer

Tests confidence-based routing, fallback mechanisms, and extraction validation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain.schema import AIMessage

from src.agents.llm_integration import (
    IntegrationConfig,
    ExtractionDecision,
    ConfidenceRouter,
    LLMOrchestratorIntegration,
    create_llm_orchestrator,
)
from src.agents.orchestrator import CapturedContext, ConversationStage
from src.agents.tools.intent_extractor import IntentExtractionResult
from src.agents.structured_parser import IntentAnalysis


class TestIntegrationConfig:
    """Test configuration dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = IntegrationConfig()
        
        assert config.HIGH_CONFIDENCE_THRESHOLD == 0.8
        assert config.MEDIUM_CONFIDENCE_THRESHOLD == 0.5
        assert config.model_name == "qwen2.5:7b"
        assert config.ollama_base_url == "http://localhost:11434"
        assert config.temperature == 0.1
        assert config.use_regex_fallback is True
        assert config.max_llm_retries == 2
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = IntegrationConfig(
            HIGH_CONFIDENCE_THRESHOLD=0.9,
            model_name="llama3.1:8b",
            use_regex_fallback=False,
        )
        
        assert config.HIGH_CONFIDENCE_THRESHOLD == 0.9
        assert config.model_name == "llama3.1:8b"
        assert config.use_regex_fallback is False


class TestExtractionDecision:
    """Test ExtractionDecision dataclass"""
    
    def test_accept_decision(self):
        """Test accept decision"""
        context = CapturedContext(purpose="home_purchase")
        decision = ExtractionDecision(
            action="accept",
            context=context,
            confidence=0.85,
        )
        
        assert decision.should_accept() is True
        assert decision.needs_clarification() is False
        assert decision.should_use_fallback() is False
    
    def test_clarify_decision(self):
        """Test clarify decision"""
        context = CapturedContext(purpose="home_purchase")
        decision = ExtractionDecision(
            action="clarify",
            context=context,
            confidence=0.65,
            clarification_needed=["loan_amount", "monthly_income"],
        )
        
        assert decision.should_accept() is False
        assert decision.needs_clarification() is True
        assert decision.should_use_fallback() is False
    
    def test_fallback_decision(self):
        """Test fallback decision"""
        context = CapturedContext()
        decision = ExtractionDecision(
            action="fallback",
            context=context,
            confidence=0.3,
            use_fallback=True,
        )
        
        assert decision.should_accept() is False
        assert decision.needs_clarification() is False
        assert decision.should_use_fallback() is True


class TestConfidenceRouter:
    """Test ConfidenceRouter routing logic"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = IntegrationConfig()
        self.router = ConfidenceRouter(self.config)
    
    def test_route_high_confidence(self):
        """Test routing with high confidence extraction"""
        llm_result = IntentExtractionResult(
            context=IntentAnalysis(
                purpose="home_purchase",
                loan_amount="$400,000",
                monthly_income="$8,000",
            ),
            confidence=0.9,
            field_confidence={
                "purpose": 0.95,
                "loan_amount": 0.9,
                "monthly_income": 0.88,
            }
        )
        
        current_context = CapturedContext()
        decision = self.router.route(llm_result, current_context)
        
        assert decision.action == "accept"
        assert decision.confidence == 0.9
        assert decision.should_accept() is True
    
    def test_route_medium_confidence(self):
        """Test routing with medium confidence extraction"""
        llm_result = IntentExtractionResult(
            context=IntentAnalysis(
                purpose="home_purchase",
                loan_amount="$400,000",
            ),
            confidence=0.65,
            field_confidence={
                "purpose": 0.7,
                "loan_amount": 0.6,
            }
        )
        
        current_context = CapturedContext()
        decision = self.router.route(llm_result, current_context)
        
        assert decision.action == "clarify"
        assert decision.confidence == 0.65
        assert decision.needs_clarification() is True
    
    def test_route_low_confidence(self):
        """Test routing with low confidence extraction"""
        llm_result = IntentExtractionResult(
            context=IntentAnalysis(purpose="unknown"),
            confidence=0.3,
            field_confidence={"purpose": 0.3}
        )
        
        current_context = CapturedContext()
        decision = self.router.route(llm_result, current_context)
        
        assert decision.action == "fallback"
        assert decision.confidence == 0.3
        assert decision.should_use_fallback() is True
    
    def test_route_validation_failure(self):
        """Test routing with validation failure"""
        llm_result = IntentExtractionResult(
            context=IntentAnalysis(
                purpose="home_purchase",
                monthly_income="$500",  # Too low, fails validation
                loan_amount="$10,000,000",  # Unrealistic
            ),
            confidence=0.85,
            field_confidence={
                "purpose": 0.9,
                "monthly_income": 0.85,
                "loan_amount": 0.85,
            }
        )
        
        current_context = CapturedContext()
        decision = self.router.route(llm_result, current_context)
        
        # Should fallback due to validation failure
        assert decision.action == "fallback"
    
    def test_route_with_llm_error(self):
        """Test routing when LLM extraction failed"""
        llm_result = IntentExtractionResult(
            context=IntentAnalysis(),
            confidence=0.0,
            field_confidence={},
            parse_errors="LLM connection failed"
        )
        
        current_context = CapturedContext()
        decision = self.router.route(llm_result, current_context)
        
        assert decision.action == "fallback"
        assert decision.llm_error == "LLM connection failed"
    
    def test_identify_clarification_needs(self):
        """Test identification of fields needing clarification"""
        context = CapturedContext(
            purpose="home_purchase",
            loan_amount=400000,
            monthly_income=8000,
        )
        
        field_confidence = {
            "purpose": 0.9,
            "loan_amount": 0.6,  # Low confidence
            "monthly_income": 0.5,  # Low confidence
        }
        
        current_context = CapturedContext()
        
        needs = self.router._identify_clarification_needs(
            context, field_confidence, current_context
        )
        
        assert "loan_amount" in needs
        assert "monthly_income" in needs
    
    def test_parse_currency_with_symbols(self):
        """Test currency parsing with various symbols"""
        context = CapturedContext()
        
        assert self.router._parse_currency("$400,000") == 400000.0
        assert self.router._parse_currency("$8,000") == 8000.0
        assert self.router._parse_currency("500000") == 500000.0
        assert self.router._parse_currency(None) is None
        assert self.router._parse_currency("invalid") is None
    
    def test_detect_currency_from_text(self):
        """Test currency detection from text"""
        assert self.router._detect_currency("$400,000") == "USD"
        assert self.router._detect_currency("TTD 500,000") == "TTD"
        assert self.router._detect_currency("JMD 5,000,000") == "JMD"
        assert self.router._detect_currency("€400,000") == "EUR"
        assert self.router._detect_currency("£300,000") == "GBP"
        assert self.router._detect_currency("") == "USD"  # Default
    
    def test_validate_income_too_low(self):
        """Test validation rejects unrealistically low income"""
        context = CapturedContext(monthly_income=500)  # $500/month too low
        field_confidence = {"monthly_income": 0.9}
        
        errors = self.router._validate_extraction(context, field_confidence)
        
        assert any("Income too low" in error for error in errors)
    
    def test_validate_income_too_high(self):
        """Test validation rejects unrealistically high income"""
        context = CapturedContext(monthly_income=2_000_000)  # $2M/month unrealistic
        field_confidence = {"monthly_income": 0.9}
        
        errors = self.router._validate_extraction(context, field_confidence)
        
        assert any("Income unrealistically high" in error for error in errors)
    
    def test_validate_loan_to_income_ratio(self):
        """Test validation rejects unreasonable loan-to-income ratio"""
        context = CapturedContext(
            monthly_income=5000,
            loan_amount=1_000_000,  # 200x income
        )
        field_confidence = {"monthly_income": 0.9, "loan_amount": 0.9}
        
        errors = self.router._validate_extraction(context, field_confidence)
        
        assert any("exceeds" in error and "income" in error for error in errors)
    
    def test_validate_invalid_email(self):
        """Test validation rejects invalid email format"""
        context = CapturedContext(email="not-an-email")
        field_confidence = {"email": 0.9}
        
        errors = self.router._validate_extraction(context, field_confidence)
        
        assert any("Invalid email" in error for error in errors)
    
    def test_validate_invalid_phone(self):
        """Test validation rejects phone without digits"""
        context = CapturedContext(phone="abc-defg")
        field_confidence = {"phone": 0.9}
        
        errors = self.router._validate_extraction(context, field_confidence)
        
        assert any("no digits" in error for error in errors)


class TestLLMOrchestratorIntegration:
    """Test LLMOrchestratorIntegration end-to-end"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = IntegrationConfig(
            max_llm_retries=1,  # Speed up tests
            use_regex_fallback=True,
        )
    
    @patch('src.agents.llm_integration.IntentExtractorTool')
    def test_process_message_high_confidence(self, mock_extractor_class):
        """Test processing with high confidence extraction"""
        # Setup mock
        mock_extractor = Mock()
        mock_extractor.run.return_value = IntentExtractionResult(
            context=IntentAnalysis(
                purpose="home_purchase",
                loan_amount="$400,000",
                monthly_income="$8,000",
            ),
            confidence=0.9,
            field_confidence={"purpose": 0.95, "loan_amount": 0.9, "monthly_income": 0.88}
        ).model_dump_json()
        mock_extractor_class.return_value = mock_extractor
        
        integration = LLMOrchestratorIntegration(self.config)
        response = integration.process_message("I need a $400,000 home loan, I make $8k monthly")
        
        assert "response" in response
        assert response["extraction"]["confidence"] == 0.9
        assert response["extraction"]["action"] == "accept"
        assert integration.metrics["accepts"] == 1
    
    @patch('src.agents.llm_integration.IntentExtractorTool')
    def test_process_message_low_confidence_fallback(self, mock_extractor_class):
        """Test processing with low confidence → fallback"""
        # Setup mock to return low confidence
        mock_extractor = Mock()
        mock_extractor.run.return_value = IntentExtractionResult(
            context=IntentAnalysis(),
            confidence=0.2,
            field_confidence={},
            parse_errors="Uncertain extraction"
        ).model_dump_json()
        mock_extractor_class.return_value = mock_extractor
        
        integration = LLMOrchestratorIntegration(self.config)
        response = integration.process_message("I need money")
        
        assert "response" in response
        assert response["extraction"]["action"] == "fallback"
        assert integration.metrics["fallbacks"] == 1
    
    @patch('src.agents.llm_integration.IntentExtractorTool')
    def test_process_message_with_llm_failure(self, mock_extractor_class):
        """Test processing when LLM completely fails"""
        # Setup mock to raise exception
        mock_extractor = Mock()
        mock_extractor.run.side_effect = Exception("LLM connection failed")
        mock_extractor_class.return_value = mock_extractor
        
        integration = LLMOrchestratorIntegration(self.config)
        response = integration.process_message("I need a loan")
        
        # Should fallback gracefully
        assert "response" in response
        assert integration.metrics["fallbacks"] >= 1
    
    def test_process_message_stage_progression(self):
        """Test that conversation progresses through stages"""
        integration = LLMOrchestratorIntegration(self.config)
        
        # Initial stage
        assert integration.orchestrator.state.stage == ConversationStage.INTENT_CAPTURE
        
        # Process message that captures purpose
        with patch('src.agents.llm_integration.IntentExtractorTool') as mock_class:
            mock_extractor = Mock()
            mock_extractor.run.return_value = IntentExtractionResult(
                context=IntentAnalysis(purpose="home_purchase"),
                confidence=0.9,
                field_confidence={"purpose": 0.95}
            ).model_dump_json()
            mock_class.return_value = mock_extractor
            
            integration.process_message("I want to buy a house")
        
        # Should progress to FINANCIAL_CONTEXT
        assert integration.orchestrator.state.stage == ConversationStage.FINANCIAL_CONTEXT
    
    def test_get_metrics(self):
        """Test metrics retrieval"""
        integration = LLMOrchestratorIntegration(self.config)
        
        metrics = integration.get_metrics()
        
        assert "total_messages" in metrics
        assert "llm_extractions" in metrics
        assert "fallbacks" in metrics
        assert "accepts" in metrics
        assert "clarifications" in metrics


class TestFactoryFunction:
    """Test create_llm_orchestrator factory"""
    
    @patch('src.agents.llm_integration.LLMOrchestratorIntegration')
    def test_create_with_defaults(self, mock_integration_class):
        """Test factory with default configuration"""
        integration = create_llm_orchestrator()
        
        mock_integration_class.assert_called_once()
    
    @patch('src.agents.llm_integration.LLMOrchestratorIntegration')
    def test_create_with_custom_config(self, mock_integration_class):
        """Test factory with custom configuration"""
        config = IntegrationConfig(model_name="llama3.1:8b")
        integration = create_llm_orchestrator(config, log_level="DEBUG")
        
        mock_integration_class.assert_called_once_with(config)


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios"""
    
    @patch('src.agents.llm_integration.IntentExtractorTool')
    def test_complete_intent_capture_scenario(self, mock_extractor_class):
        """Test complete intent capture flow"""
        # Setup mock
        mock_extractor = Mock()
        mock_extractor.run.return_value = IntentExtractionResult(
            context=IntentAnalysis(
                purpose="home_purchase",
                borrower_name="Marcus Williams",
                urgency="high",
                seriousness_score=85,
                fit_score=80,
            ),
            confidence=0.88,
            field_confidence={
                "purpose": 0.95,
                "borrower_name": 0.9,
                "urgency": 0.85,
                "seriousness_score": 0.9,
                "fit_score": 0.85,
            }
        ).model_dump_json()
        mock_extractor_class.return_value = mock_extractor
        
        config = IntegrationConfig()
        integration = LLMOrchestratorIntegration(config)
        
        # Process message
        response = integration.process_message(
            "Hi, I'm Marcus Williams. I urgently need a home loan to buy a house"
        )
        
        # Verify extraction
        context = integration.orchestrator.state.captured_context
        assert context.purpose == "home_purchase"
        assert context.borrower_name == "Marcus Williams"
        assert context.urgency == "high"
        assert context.seriousness_score == 85
        assert context.fit_score == 80
        
        # Verify confidence tracking
        assert context.get_confidence("purpose") == 0.95
        assert context.get_average_confidence() > 0.8
    
    @patch('src.agents.llm_integration.IntentExtractorTool')
    def test_caribbean_currency_handling(self, mock_extractor_class):
        """Test Caribbean currency handling"""
        mock_extractor = Mock()
        mock_extractor.run.return_value = IntentExtractionResult(
            context=IntentAnalysis(
                purpose="home_purchase",
                loan_amount="TTD 2,000,000",
                monthly_income="TTD 40,000",
            ),
            confidence=0.85,
            field_confidence={"loan_amount": 0.85, "monthly_income": 0.85}
        ).model_dump_json()
        mock_extractor_class.return_value = mock_extractor
        
        integration = LLMOrchestratorIntegration(IntegrationConfig())
        response = integration.process_message(
            "I need a TTD 2 million home loan, I make TTD 40k monthly in Trinidad"
        )
        
        context = integration.orchestrator.state.captured_context
        assert context.currency == "TTD"
        # Note: The parser extracts numeric values, currency is tracked separately
        assert context.currency_symbol == "$"  # TTD uses $ symbol


# ─────────────────────────────────────────────────────────────────────────────
# Run Tests
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
