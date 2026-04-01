"""
Test Suite for LangFuse Observability (TASK-002.02)

Testing Philosophy:
- Use REAL LangFuse client when available (integration tests)
- Test graceful degradation when LangFuse is unavailable
- Verify trace/span creation and metadata recording
- Test with real LLM calls from EPIC-001

Test Categories:
1. Correctness: Observer initialization, trace/span creation, score recording
2. Integration: Real LangFuse server (when available)
3. Degradation: Behavior when LangFuse is unavailable

Run with:
    # Unit tests only (degraded mode)
    pytest src/shared/tests/test_observability.py -v
    
    # Integration tests (requires LangFuse running)
    RUN_INTEGRATION=1 pytest src/shared/tests/test_observability.py -v

Environment:
    LANGFUSE_HOST: LangFuse server URL (default: http://localhost:3000)
    LANGFUSE_PUBLIC_KEY: Public key (required for integration tests)
    LANGFUSE_SECRET_KEY: Secret key (required for integration tests)
"""

import pytest
import os
import time
from typing import Dict, Any

from src.shared.observability import (
    LangFuseObserver,
    Trace,
    Span,
    NoOpTrace,
    NoOpSpan,
    get_langfuse_observer,
    reset_langfuse_observer,
    observe_llm_call,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def disabled_observer() -> LangFuseObserver:
    """Create observer in disabled mode"""
    observer = LangFuseObserver(enabled=False)
    return observer


@pytest.fixture
def sample_trace_metadata() -> Dict[str, Any]:
    """Sample metadata for traces"""
    return {
        "session_id": "test-session-123",
        "application_id": "app-456",
        "conversation_mode": "advisory",
        "task_type": "intent_extraction",
    }


@pytest.fixture
def sample_llm_usage() -> Dict[str, int]:
    """Sample LLM token usage"""
    return {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Observer Initialization Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestObserverInitialization:
    """Test LangFuse observer initialization"""
    
    def test_observer_creation_disabled(self):
        """Test observer creation in disabled mode"""
        observer = LangFuseObserver(enabled=False)
        
        assert observer.enabled is False
        assert observer._client is None
        assert observer._initialized is False
    
    def test_observer_creation_enabled_no_keys(self):
        """Test observer creation when enabled but no keys available"""
        # Temporarily remove keys
        original_public = os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
        original_secret = os.environ.pop("LANGFUSE_SECRET_KEY", None)
        
        try:
            observer = LangFuseObserver(enabled=True)
            
            # Should gracefully degrade to disabled
            assert observer.enabled is False or observer._initialized is False
        finally:
            # Restore keys
            if original_public:
                os.environ["LANGFUSE_PUBLIC_KEY"] = original_public
            if original_secret:
                os.environ["LANGFUSE_SECRET_KEY"] = original_secret
    
    def test_singleton_pattern(self):
        """Test singleton pattern for global observer"""
        reset_langfuse_observer()
        
        observer1 = get_langfuse_observer()
        observer2 = get_langfuse_observer()
        
        assert observer1 is observer2
        
        reset_langfuse_observer()
        observer3 = get_langfuse_observer()
        
        assert observer1 is not observer3


# ─────────────────────────────────────────────────────────────────────────────
# No-Op Implementation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestNoOpImplementations:
    """Test no-op implementations for disabled mode"""
    
    def test_noop_trace_creation(self):
        """Test NoOpTrace creation"""
        trace = NoOpTrace(
            name="test_trace",
            session_id="session-123",
            metadata={"key": "value"}
        )
        
        assert trace.name == "test_trace"
        assert trace.session_id == "session-123"
        assert trace.metadata == {"key": "value"}
    
    def test_noop_trace_span_creation(self):
        """Test NoOpTrace span creation"""
        trace = NoOpTrace(name="test", session_id="123")
        span = trace.span(name="test_span")
        
        assert isinstance(span, NoOpSpan)
        assert span.name == "test_span"
    
    def test_noop_trace_score_recording(self):
        """Test NoOpTrace score recording (should be no-op)"""
        trace = NoOpTrace(name="test", session_id="123")
        
        # Should not raise
        trace.score(name="test_score", value=0.95)
        trace.score(name="hallucination_rate", value=0.02, comment="Low risk")
    
    def test_noop_trace_event_recording(self):
        """Test NoOpTrace event recording (should be no-op)"""
        trace = NoOpTrace(name="test", session_id="123")
        
        # Should not raise
        trace.event(name="test_event", metadata={"data": "value"})
    
    def test_noop_span_end(self):
        """Test NoOpSpan end method"""
        span = NoOpSpan(name="test_span")
        
        # Should not raise
        span.end(output={"result": "success"}, usage={"tokens": 100})
        span.generation(name="test", input_data={}, output_data={})
    
    def test_noop_span_metadata(self):
        """Test NoOpSpan ignores metadata"""
        span = NoOpSpan(name="test_span")
        
        # All these should be no-ops
        span.end(
            output={"content": "test"},
            usage={"prompt_tokens": 100, "completion_tokens": 50},
            metadata={"latency_ms": 150.5}
        )


# ─────────────────────────────────────────────────────────────────────────────
# Trace and Span Tests (Disabled Mode)
# ─────────────────────────────────────────────────────────────────────────────

class TestTraceAndSpanDisabled:
    """Test trace and span operations in disabled mode"""
    
    def test_trace_creation_disabled(self, disabled_observer: LangFuseObserver):
        """Test trace creation when observer is disabled"""
        trace = disabled_observer.start_trace(
            name="test_conversation",
            session_id="session-123",
            metadata={"test": "value"}
        )
        
        # Should return NoOpTrace
        assert isinstance(trace, NoOpTrace)
        assert trace.name == "test_conversation"
        assert trace.session_id == "session-123"
    
    def test_span_creation_disabled(self, disabled_observer: LangFuseObserver):
        """Test span creation when observer is disabled"""
        trace = disabled_observer.start_trace(name="test", session_id="123")
        span = trace.span(name="llm_call")
        
        assert isinstance(span, NoOpSpan)
    
    def test_score_recording_disabled(self, disabled_observer: LangFuseObserver):
        """Test score recording when observer is disabled"""
        trace = disabled_observer.start_trace(name="test", session_id="123")
        
        # Should not raise
        trace.score(name="quality", value=0.95)
        trace.score(name="hallucination_rate", value=0.02)
    
    def test_event_recording_disabled(self, disabled_observer: LangFuseObserver):
        """Test event recording when observer is disabled"""
        trace = disabled_observer.start_trace(name="test", session_id="123")
        
        # Should not raise
        trace.event(name="application_submitted", metadata={"id": "app-123"})
    
    def test_metadata_update_disabled(self, disabled_observer: LangFuseObserver):
        """Test metadata update when observer is disabled"""
        trace = disabled_observer.start_trace(
            name="test",
            session_id="123",
            metadata={"initial": "value"}
        )
        
        trace.update_metadata({"additional": "data"})
        
        assert trace.metadata == {"initial": "value", "additional": "data"}


# ─────────────────────────────────────────────────────────────────────────────
# Integration Helper Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationHelper:
    """Test observe_llm_call helper function"""
    
    def test_observe_llm_call_disabled(self, disabled_observer: LangFuseObserver):
        """Test observe_llm_call in disabled mode"""
        trace = disabled_observer.start_trace(name="test", session_id="123")
        
        # Should not raise
        observe_llm_call(
            trace=trace,
            provider="ollama",
            model="qwen2.5:7b",
            input_messages=[{"role": "user", "content": "Hello"}],
            output_content="Hi there!",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            latency_ms=150.5,
            cost_usd=0.0,
            task_type="simple_chat"
        )
    
    def test_observe_llm_call_with_real_data(self, disabled_observer: LangFuseObserver):
        """Test observe_llm_call with realistic data"""
        trace = disabled_observer.start_trace(
            name="borrower_conversation",
            session_id="session-456",
            metadata={
                "application_id": "app-789",
                "conversation_mode": "advisory"
            }
        )
        
        observe_llm_call(
            trace=trace,
            provider="ollama",
            model="qwen2.5:7b",
            input_messages=[
                {"role": "system", "content": "You are a loan advisor."},
                {"role": "user", "content": "What is FOIR?"},
            ],
            output_content="FOIR is Fixed Obligation to Income Ratio...",
            usage={"prompt_tokens": 50, "completion_tokens": 100},
            latency_ms=250.0,
            cost_usd=0.0,
            task_type="rag_response"
        )
        
        # In disabled mode, this should complete without errors
        assert True


# ─────────────────────────────────────────────────────────────────────────────
# Performance Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance:
    """Test performance characteristics"""
    
    def test_trace_creation_latency(self, disabled_observer: LangFuseObserver):
        """Test that trace creation is fast"""
        start = time.time()
        
        for _ in range(100):
            trace = disabled_observer.start_trace(name="test", session_id="123")
        
        elapsed = time.time() - start
        
        # Should be very fast (< 10ms for 100 traces in disabled mode)
        assert elapsed < 0.01
    
    def test_span_creation_latency(self, disabled_observer: LangFuseObserver):
        """Test that span creation is fast"""
        trace = disabled_observer.start_trace(name="test", session_id="123")
        
        start = time.time()
        
        for _ in range(100):
            span = trace.span(name="llm_call")
            span.end(output={"result": "test"})
        
        elapsed = time.time() - start
        
        # Should be very fast (< 10ms for 100 spans)
        assert elapsed < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests (Real LangFuse Server)
# ─────────────────────────────────────────────────────────────────────────────

class TestLangFuseIntegration:
    """
    Integration tests with real LangFuse server.
    
    These tests require:
    - LangFuse server running (docker-compose up langfuse)
    - LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY set
    - Internet connectivity (if using cloud version)
    
    Run with:
        RUN_INTEGRATION=1 pytest src/shared/tests/test_observability.py::TestLangFuseIntegration -v
    """
    
    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION") or not os.getenv("LANGFUSE_PUBLIC_KEY"),
        reason="Requires LangFuse server and API keys"
    )
    def test_trace_creation_enabled(self):
        """Test trace creation with real LangFuse server"""
        observer = LangFuseObserver(enabled=True)
        
        if not observer.enabled:
            pytest.skip("LangFuse not available, skipping integration test")
        
        trace = observer.start_trace(
            name="integration_test_conversation",
            session_id=f"integration-{int(time.time())}",
            metadata={"test": "integration"}
        )
        
        assert isinstance(trace, Trace)
        assert trace.name == "integration_test_conversation"
        
        observer.flush()
    
    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION") or not os.getenv("LANGFUSE_PUBLIC_KEY"),
        reason="Requires LangFuse server and API keys"
    )
    def test_span_recording_enabled(self):
        """Test span recording with real LangFuse server"""
        observer = LangFuseObserver(enabled=True)
        
        if not observer.enabled:
            pytest.skip("LangFuse not available")
        
        trace = observer.start_trace(
            name="span_test",
            session_id=f"span-test-{int(time.time())}"
        )
        
        span = trace.span(
            name="llm_call",
            input_data={"messages": [{"role": "user", "content": "Test"}]},
            metadata={"provider": "ollama"}
        )
        
        span.end(
            output={"content": "Test response"},
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            metadata={"latency_ms": 150.5}
        )
        
        observer.flush()
    
    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION") or not os.getenv("LANGFUSE_PUBLIC_KEY"),
        reason="Requires LangFuse server and API keys"
    )
    def test_score_recording_enabled(self):
        """Test score recording with real LangFuse server"""
        observer = LangFuseObserver(enabled=True)
        
        if not observer.enabled:
            pytest.skip("LangFuse not available")
        
        trace = observer.start_trace(
            name="score_test",
            session_id=f"score-test-{int(time.time())}"
        )
        
        trace.score(
            name="hallucination_rate",
            value=0.02,
            comment="Very low hallucination rate",
            data_type="NUMERIC"
        )
        
        trace.score(
            name="quality_pass",
            value=1.0,
            data_type="BOOLEAN"
        )
        
        observer.flush()


# ─────────────────────────────────────────────────────────────────────────────
# End-to-End Integration Test
# ─────────────────────────────────────────────────────────────────────────────

class TestEndToEndIntegration:
    """
    End-to-end integration test with LLM router from EPIC-001.
    
    This test verifies that:
    - LLM router integrates with LangFuse observer
    - Traces are created for LLM calls
    - Spans record token usage and latency
    - Scores can be added post-call
    
    Run with:
        RUN_INTEGRATION=1 pytest src/shared/tests/test_observability.py::TestEndToEndIntegration -v
    """
    
    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION"),
        reason="Requires integration test mode"
    )
    def test_llm_router_with_observability(self):
        """Test LLM router with LangFuse observability"""
        from src.config.llm_router import get_llm_router
        
        # Get observer and router
        observer = get_langfuse_observer()
        router = get_llm_router()
        
        # Skip if LangFuse not available
        if not observer.enabled:
            pytest.skip("LangFuse not available")
        
        # Start trace
        trace = observer.start_trace(
            name="e2e_borrower_conversation",
            session_id=f"e2e-{int(time.time())}",
            metadata={"test": "end_to_end"}
        )
        
        # Make LLM call
        messages = [
            {"role": "system", "content": "You are a loan advisor."},
            {"role": "user", "content": "What is the loan interest rate?"},
        ]
        
        response = router.chat(messages, task_type="simple_chat")
        
        # Record in LangFuse
        observe_llm_call(
            trace=trace,
            provider=response.provider,
            model=response.model,
            input_messages=messages,
            output_content=response.content,
            usage=response.usage,
            latency_ms=response.latency_ms,
            cost_usd=response.cost_usd,
            task_type="simple_chat"
        )
        
        # Add quality score
        trace.score(
            name="response_quality",
            value=0.95,
            comment="High quality response"
        )
        
        # Flush to LangFuse
        observer.flush()
        
        # Verify response
        assert len(response.content) > 0
        assert response.latency_ms > 0
        assert response.cost_usd >= 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Main Test Runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
