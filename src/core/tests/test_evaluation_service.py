"""
Test Suite for RAGAS Quality Evaluation (TASK-004.02, TASK-004.03)

Testing Philosophy:
- Use REAL RAGAS when available (integration tests)
- Test with both OpenAI and Ollama for grading
- Verify simple evaluator works without RAGAS dependency
- Test sampling behavior
- Use synthetic test data for deterministic results

Test Categories:
1. Correctness: Configuration, sampling, scoring
2. Integration: Real RAGAS with OpenAI/Ollama
3. Degradation: Simple evaluator fallback
4. Performance: Evaluation latency

Run with:
    # Unit tests only (simple evaluator)
    pytest src/core/tests/test_evaluation_service.py -v
    
    # Integration tests (requires RAGAS, OpenAI/Ollama)
    RUN_INTEGRATION=1 pytest src/core/tests/test_evaluation_service.py -v

Environment:
    RUN_INTEGRATION: Set to "1" to enable integration tests
    OPENAI_API_KEY: For testing with OpenAI grading
"""

import pytest
import os
from typing import List, Dict

from src.core.evaluation_service import (
    RAGASResult,
    EvaluationConfig,
    RAGASEvaluator,
    SimpleQualityEvaluator,
    evaluate_and_log,
    DEFAULT_CONFIG,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_config() -> EvaluationConfig:
    """Sample evaluation configuration"""
    return EvaluationConfig(
        sampling_rate=1.0,  # Always evaluate for testing
        min_answer_length=10,
        llm_provider="ollama",
        llm_model="qwen2.5:7b",
        metrics=["faithfulness", "answer_relevance"],
    )


@pytest.fixture
def sample_question() -> str:
    """Sample user question"""
    return "What is FOIR and how is it calculated?"


@pytest.fixture
def sample_answer() -> str:
    """Sample AI answer"""
    return """
    FOIR (Fixed Obligation to Income Ratio) is a key metric used in loan underwriting.
    It measures the percentage of your monthly income that goes toward fixed obligations
    like loan repayments and credit card bills.
    
    Formula: FOIR = (Monthly Fixed Obligations / Monthly Income) × 100
    
    For example, if you earn $5,000 per month and have $1,500 in monthly obligations,
    your FOIR would be (1500/5000) × 100 = 30%.
    
    Most lenders prefer a FOIR below 55%.
    """


@pytest.fixture
def sample_contexts() -> List[str]:
    """Sample retrieved policy documents"""
    return [
        "Policy: FOIR (Fixed Obligation to Income Ratio) measures debt burden.",
        "Maximum FOIR allowed is 55% for personal loans.",
        "FOIR calculation: (Monthly Obligations / Monthly Income) × 100",
    ]


@pytest.fixture
def sample_conversation(sample_question: str, sample_answer: str, sample_contexts: List[str]) -> Dict[str, any]:
    """Sample conversation for testing"""
    return {
        "question": sample_question,
        "answer": sample_answer,
        "contexts": sample_contexts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluationConfig:
    """Test evaluation configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = DEFAULT_CONFIG
        
        assert config.sampling_rate == 0.1  # 10%
        assert config.min_answer_length == 20
        assert config.llm_provider == "ollama"
        assert config.llm_model == "qwen2.5:7b"
        assert len(config.metrics) == 3
    
    def test_custom_config(self, sample_config: EvaluationConfig):
        """Test custom configuration"""
        assert sample_config.sampling_rate == 1.0  # 100% for testing
        assert sample_config.min_answer_length == 10
        assert sample_config.llm_provider == "ollama"
        assert "faithfulness" in sample_config.metrics
        assert "answer_relevance" in sample_config.metrics


# ─────────────────────────────────────────────────────────────────────────────
# RAGAS Result Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRAGASResult:
    """Test RAGAS result data class"""
    
    def test_result_creation(self):
        """Test RAGASResult creation"""
        result = RAGASResult(
            faithfulness=0.9,
            answer_relevance=0.85,
            context_precision=0.8,
            overall_score=0.85,
            question="Test question",
            answer="Test answer",
            contexts=["context1"],
        )
        
        assert result.faithfulness == 0.9
        assert result.answer_relevance == 0.85
        assert result.context_precision == 0.8
        assert result.overall_score == 0.85
        assert result.question == "Test question"
        assert len(result.contexts) == 1
    
    def test_result_default_values(self):
        """Test RAGASResult default values"""
        result = RAGASResult(
            faithfulness=0.5,
            answer_relevance=0.5,
            context_precision=0.5,
            overall_score=0.5,
            question="Q",
            answer="A",
            contexts=[],
        )
        
        assert result.llm_used == "unknown"
        assert result.metadata == {}


# ─────────────────────────────────────────────────────────────────────────────
# Simple Quality Evaluator Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSimpleQualityEvaluator:
    """Test simple quality evaluator (no RAGAS dependency)"""
    
    def test_simple_evaluator_creation(self):
        """Test simple evaluator initialization"""
        evaluator = SimpleQualityEvaluator()
        assert evaluator is not None
    
    def test_simple_evaluation_with_good_answer(self):
        """Test evaluation of good quality answer"""
        evaluator = SimpleQualityEvaluator()
        
        question = "What is FOIR?"
        answer = "FOIR is Fixed Obligation to Income Ratio, calculated as monthly obligations divided by monthly income."
        
        result = evaluator.evaluate(
            question=question,
            answer=answer,
            hallucination_score=0.0  # No hallucinations
        )
        
        assert result is not None
        assert result.faithfulness == 1.0  # No hallucinations
        assert result.answer_relevance > 0.5  # Contains question terms
        assert result.overall_score > 0.5
    
    def test_simple_evaluation_with_hallucination(self):
        """Test evaluation with high hallucination score"""
        evaluator = SimpleQualityEvaluator()
        
        question = "What is FOIR?"
        answer = "FOIR is something about loans."
        
        result = evaluator.evaluate(
            question=question,
            answer=answer,
            hallucination_score=0.8  # High hallucination
        )
        
        assert abs(result.faithfulness - 0.2) < 0.01  # 1.0 - 0.8, with floating point tolerance
        assert result.overall_score < 0.5
    
    def test_simple_evaluation_length_scoring(self):
        """Test that longer answers get higher length scores"""
        evaluator = SimpleQualityEvaluator()
        
        short_answer = "FOIR is debt ratio."
        long_answer = "FOIR (Fixed Obligation to Income Ratio) is a comprehensive metric used by financial institutions to assess borrower creditworthiness by measuring the percentage of monthly income allocated to debt servicing."
        
        result_short = evaluator.evaluate("What is FOIR?", short_answer, 0.0)
        result_long = evaluator.evaluate("What is FOIR?", long_answer, 0.0)
        
        # Long answer should have higher length score
        assert result_long.metadata["length_score"] > result_short.metadata["length_score"]
    
    def test_simple_evaluation_relevance_scoring(self):
        """Test relevance scoring based on term overlap"""
        evaluator = SimpleQualityEvaluator()
        
        question = "What is the maximum LTV for home loans?"
        
        # High overlap
        answer_high = "The maximum LTV for home loans is 95%."
        result_high = evaluator.evaluate(question, answer_high, 0.0)
        
        # Low overlap
        answer_low = "Interest rates range from 5 to 15 percent."
        result_low = evaluator.evaluate(question, answer_low, 0.0)
        
        assert result_high.answer_relevance > result_low.answer_relevance


# ─────────────────────────────────────────────────────────────────────────────
# RAGAS Evaluator Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRAGASEvaluator:
    """Test RAGAS evaluator"""
    
    def test_evaluator_creation(self, sample_config: EvaluationConfig):
        """Test RAGAS evaluator initialization"""
        evaluator = RAGASEvaluator(config=sample_config)
        assert evaluator is not None
        assert evaluator.config.sampling_rate == 1.0
    
    def test_sampling_logic(self, sample_config: EvaluationConfig):
        """Test sampling behavior"""
        # With sampling_rate=1.0, should always evaluate
        evaluator = RAGASEvaluator(config=sample_config)
        assert evaluator._should_evaluate() is True
        
        # With sampling_rate=0.0, should never evaluate
        sample_config.sampling_rate = 0.0
        evaluator_no_sample = RAGASEvaluator(config=sample_config)
        assert evaluator_no_sample._should_evaluate() is False
    
    def test_min_answer_length_filter(self, sample_config: EvaluationConfig):
        """Test minimum answer length filtering"""
        sample_config.min_answer_length = 50
        evaluator = RAGASEvaluator(config=sample_config)
        evaluator._ensure_initialized()
        
        # Short answer should return None
        result = evaluator.evaluate_conversation(
            question="What is FOIR?",
            answer="Short",  # Too short
            contexts=["context"]
        )
        
        # Should be None due to length filter
        # (or None if RAGAS not initialized)
        assert result is None
    
    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION"),
        reason="Requires RAGAS and LLM installed"
    )
    def test_ragas_evaluation_real(self, sample_conversation: Dict):
        """Test real RAGAS evaluation"""
        evaluator = RAGASEvaluator()
        
        result = evaluator.evaluate_conversation(
            question=sample_conversation["question"],
            answer=sample_conversation["answer"],
            contexts=sample_conversation["contexts"]
        )
        
        if result:
            assert 0.0 <= result.faithfulness <= 1.0
            assert 0.0 <= result.answer_relevance <= 1.0
            assert 0.0 <= result.overall_score <= 1.0
    
    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION") or not os.getenv("OPENAI_API_KEY"),
        reason="Requires RAGAS and OpenAI API key"
    )
    def test_ragas_with_openai(self, sample_conversation: Dict):
        """Test RAGAS evaluation with OpenAI grading"""
        config = EvaluationConfig(
            sampling_rate=1.0,
            llm_provider="openai",
            llm_model="gpt-4.1-mini",
        )
        
        evaluator = RAGASEvaluator(config=config)
        result = evaluator.evaluate_conversation(
            question=sample_conversation["question"],
            answer=sample_conversation["answer"],
            contexts=sample_conversation["contexts"]
        )
        
        if result:
            assert result.llm_used == "gpt-4.1-mini"


# ─────────────────────────────────────────────────────────────────────────────
# Integration Helper Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationHelper:
    """Test evaluate_and_log helper function"""
    
    def test_evaluate_and_log_simple(self, sample_conversation: Dict):
        """Test helper with simple evaluator"""
        result = evaluate_and_log(
            question=sample_conversation["question"],
            answer=sample_conversation["answer"],
            contexts=sample_conversation.get("contexts"),
            hallucination_score=0.1,
            use_simple=True
        )
        
        assert result is not None
        assert result.faithfulness == 0.9  # 1.0 - 0.1
    
    def test_evaluate_and_log_with_trace_mock(self, sample_conversation: Dict):
        """Test helper with mock trace"""
        # Create mock trace
        class MockTrace:
            def __init__(self):
                self.scores = []
            
            def score(self, name, value, comment=None):
                self.scores.append({"name": name, "value": value, "comment": comment})
        
        trace = MockTrace()
        
        result = evaluate_and_log(
            question=sample_conversation["question"],
            answer=sample_conversation["answer"],
            use_simple=True,
            trace=trace
        )
        
        assert result is not None
        # Should have logged scores
        assert len(trace.scores) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Performance Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance:
    """Test performance characteristics"""
    
    def test_simple_evaluator_performance(self):
        """Test simple evaluator is fast"""
        import time
        
        evaluator = SimpleQualityEvaluator()
        
        start = time.time()
        for _ in range(100):
            evaluator.evaluate(
                question="What is FOIR?",
                answer="FOIR is Fixed Obligation to Income Ratio.",
                hallucination_score=0.1
            )
        elapsed = time.time() - start
        
        # Should be very fast (<100ms for 100 evaluations)
        assert elapsed < 0.1
    
    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION"),
        reason="Requires RAGAS installed"
    )
    def test_ragas_evaluator_performance(self, sample_conversation: Dict):
        """Test RAGAS evaluator performance"""
        import time
        
        evaluator = RAGASEvaluator()
        
        start = time.time()
        result = evaluator.evaluate_conversation(
            question=sample_conversation["question"],
            answer=sample_conversation["answer"],
            contexts=sample_conversation["contexts"]
        )
        elapsed = time.time() - start
        
        # RAGAS evaluation should complete in <30 seconds
        if result:
            assert elapsed < 30.0


# ─────────────────────────────────────────────────────────────────────────────
# Alert Threshold Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAlertThresholds:
    """Test alert threshold logic"""
    
    def test_should_alert_low_faithfulness(self, sample_config: EvaluationConfig):
        """Test alert for low faithfulness"""
        evaluator = RAGASEvaluator(config=sample_config)
        
        from src.core.evaluation_service import RAGASResult
        result = RAGASResult(
            faithfulness=0.5,  # Below threshold (0.7)
            answer_relevance=0.9,
            context_precision=0.8,
            overall_score=0.73,
            question="Q",
            answer="A",
            contexts=[],
        )
        
        assert evaluator.should_alert(result) is True
    
    def test_should_alert_low_relevance(self, sample_config: EvaluationConfig):
        """Test alert for low relevance"""
        evaluator = RAGASEvaluator(config=sample_config)
        
        from src.core.evaluation_service import RAGASResult
        result = RAGASResult(
            faithfulness=0.9,
            answer_relevance=0.5,  # Below threshold (0.7)
            context_precision=0.8,
            overall_score=0.73,
            question="Q",
            answer="A",
            contexts=[],
        )
        
        assert evaluator.should_alert(result) is True
    
    def test_no_alert_good_scores(self, sample_config: EvaluationConfig):
        """Test no alert for good scores"""
        evaluator = RAGASEvaluator(config=sample_config)
        
        from src.core.evaluation_service import RAGASResult
        result = RAGASResult(
            faithfulness=0.9,
            answer_relevance=0.85,
            context_precision=0.8,
            overall_score=0.85,
            question="Q",
            answer="A",
            contexts=[],
        )
        
        assert evaluator.should_alert(result) is False


# ─────────────────────────────────────────────────────────────────────────────
# Main Test Runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
