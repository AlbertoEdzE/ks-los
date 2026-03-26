"""
Unit Tests for Intent Extraction Tool

Tests intent extraction from conversation history.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain.schema import AIMessage

from src.agents.tools.intent_extractor import (
    IntentExtractorTool,
    IntentExtractionInput,
    IntentExtractionResult,
    extract_intent_from_conversation,
)
from src.agents.structured_parser import IntentAnalysis


class TestIntentExtractionInput:
    """Test input schema validation"""
    
    def test_valid_input(self):
        """Test valid conversation history input"""
        history = [
            {"role": "user", "content": "I need a home loan"},
            {"role": "assistant", "content": "I can help with that."}
        ]
        
        input_data = IntentExtractionInput(conversation_history=history)
        
        assert len(input_data.conversation_history) == 2
        assert input_data.conversation_history[0]["role"] == "user"
        assert input_data.conversation_history[0]["content"] == "I need a home loan"
    
    def test_empty_history(self):
        """Test empty conversation history"""
        input_data = IntentExtractionInput(conversation_history=[])
        
        assert len(input_data.conversation_history) == 0
    
    def test_missing_role(self):
        """Test handling of missing role in message"""
        history = [
            {"content": "I need a loan"}  # Missing role
        ]
        
        input_data = IntentExtractionInput(conversation_history=history)
        
        assert len(input_data.conversation_history) == 1
        assert "role" not in input_data.conversation_history[0]


class TestIntentExtractionResult:
    """Test result schema validation"""
    
    def test_valid_result(self):
        """Test valid extraction result"""
        context = IntentAnalysis(
            purpose="home_purchase",
            loan_amount="$400,000",
            monthly_income="$8,000",
            seriousness_score=75,
            fit_score=80
        )
        
        result = IntentExtractionResult(
            context=context,
            confidence=0.85,
            field_confidence={
                "purpose": 0.9,
                "loan_amount": 0.85,
                "monthly_income": 0.8
            }
        )
        
        assert result.confidence == 0.85
        assert result.context.purpose == "home_purchase"
        assert len(result.field_confidence) == 3
    
    def test_result_with_errors(self):
        """Test result with parse errors"""
        result = IntentExtractionResult(
            context=IntentAnalysis(),
            confidence=0.0,
            parse_errors="Failed to parse JSON"
        )
        
        assert result.confidence == 0.0
        assert result.parse_errors == "Failed to parse JSON"
        assert result.context.purpose is None
    
    def test_result_serialization(self):
        """Test JSON serialization"""
        context = IntentAnalysis(purpose="auto_loan")
        result = IntentExtractionResult(
            context=context,
            confidence=0.75
        )
        
        json_str = result.model_dump_json()
        
        assert "purpose" in json_str
        assert "auto_loan" in json_str
        assert "0.75" in json_str


class TestIntentExtractorTool:
    """Test IntentExtractorTool functionality"""
    
    def test_tool_initialization(self):
        """Test tool initialization with defaults"""
        tool = IntentExtractorTool()
        
        assert tool.name == "extract_borrower_intent"
        assert tool.model_name == "qwen2.5:7b"
        assert tool.ollama_base_url == "http://localhost:11434"
        assert tool.temperature == 0.1
    
    def test_tool_initialization_with_custom_params(self):
        """Test tool initialization with custom parameters"""
        tool = IntentExtractorTool(
            model_name="llama3.1:8b",
            ollama_base_url="http://localhost:11435",
            temperature=0.2
        )
        
        assert tool.model_name == "llama3.1:8b"
        assert tool.ollama_base_url == "http://localhost:11435"
        assert tool.temperature == 0.2
    
    def test_format_conversation(self):
        """Test conversation formatting"""
        tool = IntentExtractorTool()
        
        messages = [
            {"role": "user", "content": "I need a loan"},
            {"role": "assistant", "content": "How much?"}
        ]
        
        formatted = tool._format_conversation(messages)
        
        assert "USER: I need a loan" in formatted
        assert "ASSISTANT: How much?" in formatted
    
    def test_extract_json_from_plain_text(self):
        """Test JSON extraction from plain text"""
        tool = IntentExtractorTool()
        
        text = '{"purpose": "home_purchase", "amount": "$400,000"}'
        
        extracted = tool._extract_json(text)
        
        assert extracted == text
    
    def test_extract_json_from_markdown_block(self):
        """Test JSON extraction from markdown code block"""
        tool = IntentExtractorTool()
        
        text = """
        Here's the JSON:
        ```json
        {"purpose": "home_purchase", "amount": "$400,000"}
        ```
        """
        
        extracted = tool._extract_json(text)
        
        assert extracted == '{"purpose": "home_purchase", "amount": "$400,000"}'
    
    def test_extract_json_with_trailing_text(self):
        """Test JSON extraction with trailing text"""
        tool = IntentExtractorTool()
        
        text = """
        Some text before
        {"purpose": "home_purchase"}
        Some text after
        """
        
        extracted = tool._extract_json(text)
        
        assert extracted == '{"purpose": "home_purchase"}'
    
    @patch('src.agents.tools.intent_extractor.ChatOllama')
    def test_call_llm(self, mock_chat_ollama_class):
        """Test LLM calling (mocked)"""
        # Setup mock
        mock_llm = Mock()
        mock_chat_ollama_class.return_value = mock_llm
        mock_llm.invoke.return_value = AIMessage(
            content='{"purpose": "home_purchase", "loan_amount": "$400,000"}'
        )
        
        tool = IntentExtractorTool()
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Extract intent"}
        ]
        
        response = tool._call_llm(messages)
        
        assert response == '{"purpose": "home_purchase", "loan_amount": "$400,000"}'
        mock_chat_ollama_class.assert_called_once()
    
    def test_compute_field_confidence_with_values(self):
        """Test confidence computation for fields with values"""
        tool = IntentExtractorTool()
        
        context = IntentAnalysis(
            purpose="home_purchase",
            loan_amount="$400,000",
            email="test@example.com"
        )
        data = {
            "purpose": "home_purchase",
            "loan_amount": "$400,000",
            "email": "test@example.com"
        }
        
        confidence = tool._compute_field_confidence(context, data)
        
        assert confidence["purpose"] > 0.6
        assert confidence["loan_amount"] > 0.6
        assert confidence["email"] == 0.95  # Valid email boost
    
    def test_compute_field_confidence_with_none(self):
        """Test confidence computation for missing fields"""
        tool = IntentExtractorTool()
        
        context = IntentAnalysis()
        data = {"purpose": None, "loan_amount": None}
        
        confidence = tool._compute_field_confidence(context, data)
        
        assert confidence["purpose"] == 0.0
        assert confidence["loan_amount"] == 0.0
    
    def test_compute_field_confidence_with_empty_string(self):
        """Test confidence computation for empty strings"""
        tool = IntentExtractorTool()
        
        context = IntentAnalysis(purpose="")
        data = {"purpose": ""}
        
        confidence = tool._compute_field_confidence(context, data)
        
        assert confidence["purpose"] == 0.0
    
    @patch('src.agents.tools.intent_extractor.ChatOllama')
    def test_run_successful_extraction(self, mock_chat_ollama_class):
        """Test successful intent extraction (mocked LLM)"""
        # Setup mock
        mock_llm = Mock()
        mock_chat_ollama_class.return_value = mock_llm
        mock_llm.invoke.return_value = AIMessage(
            content='''
            {
                "purpose": "home_purchase",
                "loan_amount": "$400,000",
                "monthly_income": "$8,000",
                "employment_type": "salaried",
                "seriousness_score": 75,
                "fit_score": 80
            }
            '''
        )
        
        tool = IntentExtractorTool()
        history = [
            {"role": "user", "content": "I need a $400,000 home loan. I make $8,000 monthly from my job."}
        ]
        
        result_json = tool._run(conversation_history=history)
        result = IntentExtractionResult.model_validate_json(result_json)
        
        assert result.context.purpose == "home_purchase"
        assert result.context.loan_amount == "$400,000"
        assert result.context.monthly_income == "$8,000"
        assert result.confidence > 0.5
        assert result.parse_errors is None
    
    @patch('src.agents.tools.intent_extractor.ChatOllama')
    def test_run_with_markdown_response(self, mock_chat_ollama_class):
        """Test handling of markdown-formatted JSON response"""
        mock_llm = Mock()
        mock_chat_ollama_class.return_value = mock_llm
        mock_llm.invoke.return_value = AIMessage(
            content='''
            ```json
            {
                "purpose": "auto_loan",
                "loan_amount": "$50,000"
            }
            ```
            '''
        )
        
        tool = IntentExtractorTool()
        history = [
            {"role": "user", "content": "I want to buy a car for $50,000"}
        ]
        
        result_json = tool._run(conversation_history=history)
        result = IntentExtractionResult.model_validate_json(result_json)
        
        assert result.context.purpose == "auto_loan"
        assert result.context.loan_amount == "$50,000"
    
    @patch('src.agents.tools.intent_extractor.IntentExtractorTool._call_llm')
    def test_run_with_invalid_json(self, mock_call_llm):
        """Test handling of invalid JSON (no mock, tests error handling)"""
        mock_call_llm.return_value = '{invalid json}'
        
        tool = IntentExtractorTool()
        result_json = tool._run(conversation_history=[])
        result = IntentExtractionResult.model_validate_json(result_json)
        
        # Should return error result, not crash
        assert result.confidence == 0.0
        assert result.parse_errors is not None
    
    @patch('src.agents.tools.intent_extractor.ChatOllama')
    def test_run_with_partial_data(self, mock_chat_ollama_class):
        """Test extraction with partial information"""
        mock_llm = Mock()
        mock_chat_ollama_class.return_value = mock_llm
        mock_llm.invoke.return_value = AIMessage(
            content='{"purpose": "personal_loan", "loan_amount": null, "monthly_income": null}'
        )
        
        tool = IntentExtractorTool()
        history = [
            {"role": "user", "content": "I need a personal loan"}
        ]
        
        result_json = tool._run(conversation_history=history)
        result = IntentExtractionResult.model_validate_json(result_json)
        
        assert result.context.purpose == "personal_loan"
        assert result.context.loan_amount is None
        assert result.confidence < 0.5  # Lower confidence for partial data


class TestConvenienceFunction:
    """Test extract_intent_from_conversation convenience function"""
    
    @patch('src.agents.tools.intent_extractor.IntentExtractorTool')
    def test_extract_intent_from_conversation(self, mock_tool_class):
        """Test convenience function"""
        # Setup mock
        mock_tool = Mock()
        mock_tool_class.return_value = mock_tool
        mock_tool.run.return_value = '''
        {
            "context": {"purpose": "business_loan"},
            "confidence": 0.8,
            "field_confidence": {"purpose": 0.9}
        }
        '''
        
        history = [{"role": "user", "content": "I need a business loan"}]
        
        result = extract_intent_from_conversation(history)
        
        assert result.context.purpose == "business_loan"
        assert result.confidence == 0.8
        mock_tool_class.assert_called_once()


class TestIntegration:
    """Integration tests with realistic conversation scenarios"""
    
    @patch('src.agents.tools.intent_extractor.ChatOllama')
    def test_full_conversation_extraction(self, mock_chat_ollama_class):
        """Test extraction from multi-turn conversation"""
        mock_llm = Mock()
        mock_chat_ollama_class.return_value = mock_llm
        mock_llm.invoke.return_value = AIMessage(
            content='''
            {
                "purpose": "home_purchase",
                "urgency": "medium",
                "monthly_income": "$12,000",
                "existing_debts": "$1,500/month",
                "loan_amount": "$500,000",
                "employment_type": "salaried",
                "borrower_name": "Marcus Williams",
                "email": "marcus.w@email.com",
                "phone": "+1-868-555-1234",
                "seriousness_score": 85,
                "fit_score": 80,
                "next_conversation_angle": "Proceed to application"
            }
            '''
        )
        
        conversation = [
            {"role": "user", "content": "Hi, I'm looking to buy a house"},
            {"role": "assistant", "content": "Great! What's your budget?"},
            {"role": "user", "content": "Around $500,000. I make $12,000 monthly from my government job."},
            {"role": "assistant", "content": "Perfect! Do you have existing debts?"},
            {"role": "user", "content": "Yes, a car loan of $1,500/month. My name is Marcus Williams, email marcus.w@email.com"},
        ]
        
        tool = IntentExtractorTool()
        result_json = tool._run(conversation_history=conversation)
        result = IntentExtractionResult.model_validate_json(result_json)
        
        assert result.context.purpose == "home_purchase"
        assert result.context.loan_amount == "$500,000"
        assert result.context.monthly_income == "$12,000"
        assert result.context.borrower_name == "Marcus Williams"
        assert result.context.email == "marcus.w@email.com"
        assert result.confidence > 0.7


# ─────────────────────────────────────────────────────────────────────────────
# Run Tests
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
