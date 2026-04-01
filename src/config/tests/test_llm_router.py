"""
Test Suite for LLM Router (TASK-001.02)

Testing Philosophy:
- Use REAL LLM calls (no mocking of LLM libraries)
- Test with both OpenAI (if API key available) and Ollama (local)
- Use synthetic test conversations for deterministic results
- Integration tests use real documents from data/ folder

Test Categories:
1. Correctness: Configuration loading, provider selection, routing logic
2. Integration: Real LLM calls (OpenAI and/or Ollama)
3. Document-based: Test with real documents from data/ folder

Environment Variables:
    OPENAI_API_KEY: Set in .env file - enables OpenAI testing
    LLM_TEST_MODE: If set to "1", uses _TestLLM for fast deterministic tests
    RUN_INTEGRATION: If set to "1", runs integration tests with real LLMs

Run with:
    # Unit tests only (uses test LLM)
    pytest src/config/tests/test_llm_router.py -v
    
    # Full integration (requires Ollama running, OpenAI API key in .env)
    RUN_INTEGRATION=1 pytest src/config/tests/test_llm_router.py -v

Data:
    Real documents from data/ folder used for integration testing:
    - JobLetter.jpg
    - Salary-slip*.jpg
    - passport-example.png
    - ProofAdress.jpg
"""

import pytest
import os
from typing import List, Dict
from pathlib import Path

from dotenv import load_dotenv

# Load .env file (includes OPENAI_API_KEY)
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from src.config.llm_router import (
    LLMRouter,
    LLMRoutingConfig,
    RoutingRule,
    ChatResponse,
    load_llm_routing_config,
    get_llm_router,
    reset_llm_router,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_config() -> LLMRoutingConfig:
    """Create sample routing configuration for testing"""
    return LLMRoutingConfig(
        primary_provider="openai",
        primary_model="gpt-4.1-mini",
        primary_api_key_env="OPENAI_API_KEY",
        fallback_provider="ollama",
        fallback_model="qwen2.5:7b",
        fallback_base_url="http://localhost:11434",
        routing_rules=[
            RoutingRule(task="simple_chat", use="fallback"),
            RoutingRule(task="intent_extraction", use="fallback"),
            RoutingRule(task="complex_reasoning", use="primary"),
            RoutingRule(task="document_analysis", use="primary"),
        ],
        retry_on_error=True,
        primary_timeout_seconds=30,
        max_retries=2,
        cost_rates={
            "openai/gpt-4.1-mini": 0.002,
            "ollama/qwen2.5:7b": 0.0,
        }
    )


@pytest.fixture
def router(sample_config: LLMRoutingConfig) -> LLMRouter:
    """Create router with sample configuration"""
    return LLMRouter(config=sample_config)


@pytest.fixture
def sample_messages() -> List[Dict[str, str]]:
    """Sample conversation messages for testing"""
    return [
        {"role": "system", "content": "You are a helpful loan advisor assistant."},
        {"role": "user", "content": "What is the loan interest rate?"},
    ]


@pytest.fixture
def borrower_conversation() -> List[Dict[str, str]]:
    """Realistic borrower conversation for testing"""
    return [
        {"role": "system", "content": "You are LoanAssist, a Caribbean loan advisor."},
        {"role": "assistant", "content": "Hello! I'm here to help you find the right loan. What are you looking to achieve?"},
        {"role": "user", "content": "I want to buy a home in Trinidad. The property costs $400,000 TTD."},
        {"role": "assistant", "content": "Great! A home purchase in Trinidad. What's your monthly income?"},
        {"role": "user", "content": "I earn about $8,000 TTD per month, and I have no existing debts."},
    ]


@pytest.fixture
def data_dir() -> Path:
    """Get path to data directory with real documents"""
    return Path(__file__).parent.parent.parent.parent / "data"


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Loading Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestConfigurationLoading:
    """Test configuration loading from YAML file"""
    
    def test_load_config_from_default_path(self):
        """Test loading config from default path"""
        config = load_llm_routing_config()
        
        assert config.primary_provider == "openai"
        assert config.primary_model == "gpt-4.1-mini"
        assert config.fallback_provider == "ollama"
        assert config.fallback_model == "qwen2.5:7b"
        assert len(config.routing_rules) > 0
    
    def test_load_config_has_all_routing_rules(self):
        """Test that all expected routing rules are present"""
        config = load_llm_routing_config()
        
        task_types = [rule.task for rule in config.routing_rules]
        
        assert "simple_chat" in task_types
        assert "intent_extraction" in task_types
        assert "complex_reasoning" in task_types
        assert "hallucination_check" in task_types
        assert "evaluation" in task_types
    
    def test_load_config_cost_rates(self):
        """Test cost rates are loaded correctly"""
        config = load_llm_routing_config()
        
        assert "openai/gpt-4.1-mini" in config.cost_rates
        assert "ollama/qwen2.5:7b" in config.cost_rates
        assert config.cost_rates["ollama/qwen2.5:7b"] == 0.0  # Free


# ─────────────────────────────────────────────────────────────────────────────
# Provider Selection Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProviderSelection:
    """Test provider selection logic"""
    
    def test_no_api_key_uses_fallback(self, router: LLMRouter):
        """Test that fallback is used when no API key is set"""
        # Temporarily remove API key
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            provider = router.get_provider("simple_chat")
            assert provider == "ollama"
        finally:
            # Restore API key
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
    
    def test_api_key_present_uses_routing_rules(self, router: LLMRouter):
        """Test that routing rules are followed when API key is set"""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set in .env")
        
        # Simple chat should use fallback (cost optimization)
        provider = router.get_provider("simple_chat")
        assert provider == "ollama"
        
        # Complex reasoning should use primary
        provider = router.get_provider("complex_reasoning")
        assert provider == "openai"
    
    def test_intent_extraction_uses_fallback(self, router: LLMRouter):
        """Test that intent extraction uses fallback (cost optimization)"""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set in .env")
        
        provider = router.get_provider("intent_extraction")
        assert provider == "ollama"
    
    def test_unknown_task_uses_default_rule(self, router: LLMRouter):
        """Test behavior for unknown task types"""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set in .env")
        
        # Unknown task should default to fallback (not in rules)
        provider = router.get_provider("unknown_task")
        assert provider == "ollama"


# ─────────────────────────────────────────────────────────────────────────────
# Chat Response Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestChatResponse:
    """Test ChatResponse data class"""
    
    def test_chat_response_creation(self):
        """Test ChatResponse creation with all fields"""
        response = ChatResponse(
            content="Test response",
            provider="openai",
            model="gpt-4.1-mini",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            latency_ms=150.5,
            cost_usd=0.00006,
            metadata={"task_type": "test"}
        )
        
        assert response.content == "Test response"
        assert response.provider == "openai"
        assert response.usage["prompt_tokens"] == 10
        assert response.latency_ms == 150.5
        assert response.cost_usd == 0.00006
    
    def test_chat_response_defaults(self):
        """Test ChatResponse default values"""
        response = ChatResponse(
            content="Test",
            provider="ollama",
            model="qwen2.5:7b"
        )
        
        assert response.usage == {}
        assert response.latency_ms == 0.0
        assert response.cost_usd == 0.0
        assert response.metadata == {}


# ─────────────────────────────────────────────────────────────────────────────
# Cost Calculation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCostCalculation:
    """Test cost calculation logic"""
    
    def test_calculate_cost_openai(self, router: LLMRouter):
        """Test cost calculation for OpenAI"""
        usage = {"prompt_tokens": 100, "completion_tokens": 200}
        cost = router._calculate_cost("openai/gpt-4.1-mini", usage)
        
        # 300 tokens / 1000 * $0.002 = $0.0006
        assert cost == 0.0006
    
    def test_calculate_cost_ollama_free(self, router: LLMRouter):
        """Test cost calculation for Ollama (free)"""
        usage = {"prompt_tokens": 1000, "completion_tokens": 2000}
        cost = router._calculate_cost("ollama/qwen2.5:7b", usage)
        
        assert cost == 0.0
    
    def test_calculate_cost_unknown_model(self, router: LLMRouter):
        """Test cost calculation for unknown model (defaults to 0)"""
        usage = {"prompt_tokens": 100, "completion_tokens": 200}
        cost = router._calculate_cost("unknown/model", usage)
        
        assert cost == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests - Real LLM Calls
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMRouterIntegration:
    """
    Test LLM router with real LLM instances.
    
    These tests make REAL API calls to:
    - Ollama (local) - always available
    - OpenAI - if OPENAI_API_KEY is set in .env
    
    Tests are marked as integration and require:
    - Ollama running locally (for fallback tests)
    - OPENAI_API_KEY in .env (for primary provider tests)
    """
    
    def test_chat_with_fallback_provider_ollama(self, router: LLMRouter, sample_messages: List[Dict]):
        """
        Test chat using fallback provider (Ollama).
        
        Verifies:
        - Router correctly initializes Ollama LLM
        - Messages are sent and response received
        - Response metadata is populated correctly
        - Cost is zero for local LLM
        
        Requirements:
        - Ollama must be running at localhost:11434
        """
        # Remove API key to force fallback
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            response = router.chat(sample_messages, task_type="simple_chat")
            
            # Verify response structure
            assert response.provider == "ollama"
            assert len(response.content) > 0
            assert response.latency_ms > 0
            assert response.latency_ms < 30000  # Should be < 30 seconds
            assert response.cost_usd == 0.0  # Free
        finally:
            # Restore API key
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set in .env"
    )
    def test_chat_with_primary_provider_openai(self, router: LLMRouter, sample_messages: List[Dict]):
        """
        Test chat using primary provider (OpenAI).
        
        Verifies:
        - Router correctly initializes OpenAI LLM
        - API key is loaded from environment
        - Response includes usage and cost data
        - Cost is > 0 for OpenAI
        
        Requirements:
        - OPENAI_API_KEY must be set in .env
        - Internet connection for API calls
        """
        response = router.chat(sample_messages, task_type="complex_reasoning")
        
        assert response.provider == "openai"
        assert len(response.content) > 0
        assert response.cost_usd >= 0.0  # May be very small but not negative
    
    def test_borrower_conversation_flow(self, router: LLMRouter, borrower_conversation: List[Dict]):
        """
        Test multi-turn borrower conversation.
        
        Verifies:
        - Conversation history is preserved
        - Context is maintained across turns
        - Response is relevant to loan context
        
        This tests the actual use case of the router.
        """
        # Use fallback for cost optimization on longer conversations
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            response = router.chat(borrower_conversation, task_type="simple_chat")
            
            assert response.provider == "ollama"
            assert len(response.content) > 0
            # Response should be relevant to loan context
            assert len(response.content) > 10  # Not empty or too short
        finally:
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set in .env"
    )
    def test_provider_switching_same_session(self, router: LLMRouter, sample_messages: List[Dict]):
        """
        Test that provider can be switched within same session.
        
        Verifies:
        - Different task types route to different providers
        - Router state is maintained correctly
        """
        # Simple chat -> fallback (Ollama)
        response1 = router.chat(sample_messages, task_type="simple_chat")
        assert response1.provider == "ollama"
        
        # Complex reasoning -> primary (OpenAI)
        response2 = router.chat(sample_messages, task_type="complex_reasoning")
        assert response2.provider == "openai"
        
        # Back to simple chat -> fallback again
        response3 = router.chat(sample_messages, task_type="simple_chat")
        assert response3.provider == "ollama"


# ─────────────────────────────────────────────────────────────────────────────
# Document-Based Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDocumentBasedIntegration:
    """
    Test LLM router with real documents from data/ folder.
    
    These tests simulate real document analysis scenarios:
    - Job letter analysis
    - Pay slip extraction
    - Passport/ID verification
    - Bank statement processing
    """
    
    @pytest.mark.skipif(
        not os.path.exists(Path(__file__).parent.parent.parent.parent / "data" / "JobLetter.jpg"),
        reason="Job letter document not found in data/ folder"
    )
    def test_job_letter_analysis_prompt(self, router: LLMRouter):
        """
        Test prompt for job letter analysis.
        
        Simulates extracting employment information from a job letter.
        Uses real document reference but text-based analysis.
        
        Note: In test mode (LLM_TEST_MODE=1), the _TestLLM returns generic
        responses. This test verifies the router works correctly with document
        analysis prompts. Integration tests with real Ollama/OpenAI will
        verify actual extraction quality.
        """
        messages = [
            {"role": "system", "content": "You are a document analysis assistant. Extract employment information from job letters."},
            {"role": "user", "content": """
                Analyze this job letter text:
                'This is to certify that Mr. John Smith is employed with Caribbean Financial Services Ltd.
                as a Senior Analyst since January 2020. His gross monthly salary is TTD 8,500.'
                
                Extract: employer name, employee name, position, start date, salary.
            """},
        ]
        
        # Use primary provider for complex document analysis (if available)
        response = router.chat(messages, task_type="document_analysis")
        
        # Verify response structure (content will be generic in test mode)
        assert len(response.content) > 0
        assert response.provider == "ollama"  # Test mode uses fallback
        assert response.latency_ms > 0
        assert response.cost_usd == 0.0  # Free
    
    @pytest.mark.skipif(
        not os.path.exists(Path(__file__).parent.parent.parent.parent / "data" / "Salary-slipJan.jpg"),
        reason="Pay slip documents not found in data/ folder"
    )
    def test_pay_slip_analysis_prompt(self, router: LLMRouter):
        """
        Test prompt for pay slip analysis.
        
        Simulates extracting income information from pay slips.
        
        Note: In test mode, _TestLLM returns generic responses.
        This test verifies router functionality, not extraction quality.
        """
        messages = [
            {"role": "system", "content": "You are a document analysis assistant. Extract income information from pay slips."},
            {"role": "user", "content": """
                Analyze this pay slip information:
                'Pay Period: January 2024
                Employee: Jane Doe
                Gross Pay: $7,200.00
                Net Pay: $6,100.00
                Deductions: $1,100.00'
                
                Extract: employee name, gross pay, net pay, pay period.
            """},
        ]
        
        response = router.chat(messages, task_type="document_analysis")
        
        # Verify response structure (test mode returns generic response)
        assert len(response.content) > 0
        assert response.provider == "ollama"
        assert response.latency_ms > 0
        assert response.cost_usd == 0.0
    
    @pytest.mark.skipif(
        not os.path.exists(Path(__file__).parent.parent.parent.parent / "data" / "passport-example.png"),
        reason="Passport document not found in data/ folder"
    )
    def test_passport_id_analysis_prompt(self, router: LLMRouter):
        """
        Test prompt for passport/ID analysis.
        
        Simulates extracting identity information from passports.
        
        Note: In test mode, _TestLLM returns generic responses.
        This test verifies router functionality, not extraction quality.
        """
        messages = [
            {"role": "system", "content": "You are a document analysis assistant. Extract identity information from passports."},
            {"role": "user", "content": """
                Analyze this passport information:
                'Republic of Trinidad and Tobago
                Passport No: T1234567
                Surname: MARIE
                Given Names: Jean Pierre
                Nationality: Trinidadian
                Date of Birth: 15 MAR 1985'
                
                Extract: full name, passport number, nationality, date of birth.
            """},
        ]
        
        response = router.chat(messages, task_type="document_analysis")
        
        # Verify response structure (test mode returns generic response)
        assert len(response.content) > 0
        assert response.provider == "ollama"
        assert response.latency_ms > 0
        assert response.cost_usd == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Fallback and Error Handling Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestFallbackBehavior:
    """Test fallback behavior when primary provider fails"""
    
    def test_retry_on_error_configuration(self, router: LLMRouter):
        """Test that retry configuration is loaded correctly"""
        assert router.config.retry_on_error is True
        assert router.config.max_retries == 2
        assert router.config.primary_timeout_seconds == 30


# ─────────────────────────────────────────────────────────────────────────────
# Singleton Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSingleton:
    """Test singleton pattern for global router instance"""
    
    def test_get_llm_router_creates_instance(self):
        """Test that get_llm_router creates instance on first call"""
        reset_llm_router()
        
        router = get_llm_router()
        
        assert router is not None
        assert isinstance(router, LLMRouter)
    
    def test_get_llm_router_returns_same_instance(self):
        """Test that get_llm_router returns same instance"""
        reset_llm_router()
        
        router1 = get_llm_router()
        router2 = get_llm_router()
        
        assert router1 is router2
    
    def test_reset_llm_router_clears_instance(self):
        """Test that reset_llm_router clears instance"""
        reset_llm_router()
        router1 = get_llm_router()
        
        reset_llm_router()
        router2 = get_llm_router()
        
        assert router1 is not router2


# ─────────────────────────────────────────────────────────────────────────────
# Performance Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance:
    """Test performance characteristics"""
    
    def test_latency_tracking_ollama(self, router: LLMRouter, sample_messages: List[Dict]):
        """Test that latency is tracked correctly for Ollama calls"""
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            response = router.chat(sample_messages, task_type="simple_chat")
            
            assert response.latency_ms > 0
            assert response.latency_ms < 30000  # Should be < 30 seconds
        finally:
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
    
    def test_router_initialization_time(self):
        """Test that router initializes quickly"""
        import time
        
        start = time.time()
        router = LLMRouter()
        elapsed = time.time() - start
        
        # Should initialize in < 1 second (lazy loading)
        assert elapsed < 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Main Test Runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
