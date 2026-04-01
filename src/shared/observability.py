"""
LangFuse AI Observability Integration for KS-LOS Phase 2

This module provides comprehensive LLM observability including:
- Trace tracking for all LLM calls
- Token usage monitoring
- Cost estimation and tracking
- Latency measurement
- Conversation visualization
- Quality metrics integration (RAGAS, hallucination scores)

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    LLM Router                                │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              LangFuse Observer                               │
    ├─────────────────────────────────────────────────────────────┤
    │  - Creates trace for each conversation                      │
    │  - Spans for individual LLM calls                           │
    │  - Metadata: tokens, latency, cost, model                   │
    │  - Scores: RAGAS, hallucination, user feedback              │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              LangFuse Server (Self-Hosted)                   │
    │  - PostgreSQL backend                                       │
    │  - REST API for queries                                     │
    │  - Web UI for visualization                                 │
    └─────────────────────────────────────────────────────────────┘

Usage:
    from src.shared.observability import langfuse_observer
    
    # Start trace
    trace = langfuse_observer.start_trace(
        name="borrower_conversation",
        session_id="session-123",
        metadata={"application_id": "app-456"}
    )
    
    # Create span for LLM call
    span = trace.span(name="intent_extraction")
    response = llm.chat(messages)
    span.end(output={"response": response}, usage=usage)
    
    # Add score
    trace.score(name="hallucination_rate", value=0.02)
"""

import os
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TraceMetadata:
    """Metadata for LLM trace"""
    session_id: str
    application_id: Optional[str] = None
    user_id: Optional[str] = None
    conversation_mode: Optional[str] = None
    task_type: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None


@dataclass
class SpanMetadata:
    """Metadata for LLM span"""
    name: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    model: Optional[str] = None
    provider: Optional[str] = None


@dataclass
class ScoreData:
    """Score data for trace evaluation"""
    name: str
    value: float  # 0-1 scale
    comment: Optional[str] = None
    data_type: str = "NUMERIC"  # NUMERIC, BOOLEAN, CATEGORICAL


# ─────────────────────────────────────────────────────────────────────────────
# LangFuse Observer
# ─────────────────────────────────────────────────────────────────────────────

class LangFuseObserver:
    """
    LangFuse observability wrapper for KS-LOS.
    
    Provides unified interface for:
    - Trace management
    - Span tracking
    - Score recording
    - Event logging
    
    Automatically handles:
    - LangFuse availability checking
    - Graceful degradation if unavailable
    - Async sending (non-blocking)
    - Batch processing for efficiency
    
    Usage:
        observer = LangFuseObserver()
        trace = observer.start_trace("conversation", session_id="123")
        span = trace.span("llm_call")
        # ... LLM call ...
        span.end(output=response)
        trace.score("quality", 0.95)
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize LangFuse observer.
        
        Args:
            enabled: If False, all operations are no-ops (for local dev)
        """
        self.enabled = enabled and os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"
        self._client = None
        self._initialized = False
        
        if self.enabled:
            self._initialize()
    
    def _initialize(self):
        """Initialize LangFuse client"""
        if self._initialized:
            return
        
        try:
            from langfuse import Langfuse
            
            # Get configuration from environment
            host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
            public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
            secret_key = os.getenv("LANGFUSE_SECRET_KEY")
            
            # For self-hosted, keys may not be set initially
            if not public_key or not secret_key:
                logger.warning("LangFuse keys not set, running in degraded mode")
                self.enabled = False
                return
            
            self._client = Langfuse(
                host=host,
                public_key=public_key,
                secret_key=secret_key,
            )
            
            # Test connectivity
            self._client.auth_check()
            
            self._initialized = True
            logger.info(f"LangFuse observer initialized (host={host})")
            
        except ImportError:
            logger.warning("langfuse package not installed, observability disabled")
            self.enabled = False
        except Exception as e:
            logger.warning(f"LangFuse initialization failed: {e}, running in degraded mode")
            self.enabled = False
    
    def start_trace(
        self,
        name: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> 'Trace':
        """
        Start a new trace.
        
        Args:
            name: Trace name (e.g., "borrower_conversation")
            session_id: Session identifier
            metadata: Additional metadata
            user_id: Optional user identifier
        
        Returns:
            Trace object (or NoOpTrace if disabled)
        """
        if not self.enabled:
            return NoOpTrace(name, session_id, metadata)
        
        try:
            trace = self._client.trace(
                name=name,
                session_id=session_id,
                user_id=user_id,
                metadata=metadata or {},
                timestamp=datetime.now(),
            )
            
            return Trace(trace, name, session_id, metadata)
            
        except Exception as e:
            logger.error(f"Failed to start trace: {e}")
            return NoOpTrace(name, session_id, metadata)
    
    def flush(self):
        """Flush all pending events to LangFuse"""
        if not self.enabled or not self._client:
            return
        
        try:
            self._client.flush()
        except Exception as e:
            logger.error(f"Failed to flush LangFuse events: {e}")
    
    def shutdown(self):
        """Shutdown LangFuse client"""
        if not self.enabled or not self._client:
            return
        
        try:
            self._client.shutdown()
        except Exception as e:
            logger.error(f"Failed to shutdown LangFuse: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Trace Wrapper
# ─────────────────────────────────────────────────────────────────────────────

class Trace:
    """
    Wrapper around LangFuse trace with KS-LOS specific methods.
    
    Provides:
    - Span creation for LLM calls
    - Score recording for quality metrics
    - Event logging for important milestones
    - Metadata updates
    """
    
    def __init__(
        self,
        langfuse_trace: Any,
        name: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self._trace = langfuse_trace
        self.name = name
        self.session_id = session_id
        self.metadata = metadata or {}
        self._spans: List[Span] = []
    
    def span(
        self,
        name: str,
        input_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> 'Span':
        """
        Create a new span within this trace.
        
        Args:
            name: Span name (e.g., "intent_extraction", "rag_response")
            input_data: Input to the operation
            metadata: Additional metadata
        
        Returns:
            Span object
        """
        span = Span(
            self._trace.span(
                name=name,
                input=input_data,
                metadata=metadata or {},
                start_time=datetime.now(),
            ),
            name,
        )
        self._spans.append(span)
        return span
    
    def score(
        self,
        name: str,
        value: float,
        comment: Optional[str] = None,
        data_type: str = "NUMERIC"
    ):
        """
        Record a score for this trace.
        
        Args:
            name: Score name (e.g., "hallucination_rate", "ragas_faithfulness")
            value: Score value (0-1 scale)
            comment: Optional comment
            data_type: Score type (NUMERIC, BOOLEAN, CATEGORICAL)
        """
        try:
            self._trace.score(
                name=name,
                value=value,
                comment=comment,
                data_type=data_type,
            )
        except Exception as e:
            logger.error(f"Failed to record score {name}: {e}")
    
    def event(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record an event within this trace.
        
        Args:
            name: Event name (e.g., "application_submitted", "stp_approved")
            metadata: Event metadata
        """
        try:
            self._trace.event(
                name=name,
                metadata=metadata or {},
                timestamp=datetime.now(),
            )
        except Exception as e:
            logger.error(f"Failed to record event {name}: {e}")
    
    def update_metadata(self, metadata: Dict[str, Any]):
        """Update trace metadata"""
        self.metadata.update(metadata)
        try:
            self._trace.update(metadata=metadata)
        except Exception as e:
            logger.error(f"Failed to update trace metadata: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Span Wrapper
# ─────────────────────────────────────────────────────────────────────────────

class Span:
    """
    Wrapper around LangFuse span for LLM call tracking.
    
    Automatically tracks:
    - Input/output data
    - Token usage
    - Latency
    - Cost
    """
    
    def __init__(self, langfuse_span: Any, name: str):
        self._span = langfuse_span
        self.name = name
        self._start_time = time.time()
    
    def end(
        self,
        output: Optional[Any] = None,
        usage: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        End the span and record metrics.
        
        Args:
            output: Output from the operation
            usage: Token usage (prompt_tokens, completion_tokens)
            metadata: Additional metadata
        """
        end_time = time.time()
        latency_ms = (end_time - self._start_time) * 1000
        
        try:
            end_data = {
                "output": output,
                "end_time": datetime.now(),
                "metadata": metadata or {},
            }
            
            # Add usage if provided
            if usage:
                end_data["usage"] = usage
                end_data["metadata"]["input_tokens"] = usage.get("prompt_tokens", 0)
                end_data["metadata"]["output_tokens"] = usage.get("completion_tokens", 0)
                end_data["metadata"]["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            
            # Add latency
            end_data["metadata"]["latency_ms"] = latency_ms
            
            self._span.end(**end_data)
            
        except Exception as e:
            logger.error(f"Failed to end span {self.name}: {e}")
    
    def generation(
        self,
        name: str,
        input_data: Any,
        output_data: Any,
        usage: Optional[Dict[str, int]] = None,
        model: Optional[str] = None,
        model_parameters: Optional[Dict[str, Any]] = None,
    ):
        """
        Record a generation event (special span type for LLM calls).
        
        Args:
            name: Generation name
            input_data: Prompt/messages sent to LLM
            output_data: LLM response
            usage: Token usage
            model: Model name
            model_parameters: Model parameters (temperature, etc.)
        """
        try:
            generation_data = {
                "name": name,
                "input": input_data,
                "output": output_data,
                "start_time": datetime.now(),
                "end_time": datetime.now(),
                "model": model,
                "model_parameters": model_parameters or {},
            }
            
            if usage:
                generation_data["usage"] = usage
            
            self._span.generation(**generation_data)
            
        except Exception as e:
            logger.error(f"Failed to record generation {name}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# No-Op Implementations (for disabled state)
# ─────────────────────────────────────────────────────────────────────────────

class NoOpTrace:
    """No-op trace for when LangFuse is disabled"""
    
    def __init__(self, name: str, session_id: str, metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.session_id = session_id
        self.metadata = metadata or {}
    
    def span(self, name: str, **kwargs) -> 'NoOpSpan':
        return NoOpSpan(name)
    
    def score(self, name: str, value: float, **kwargs):
        pass
    
    def event(self, name: str, **kwargs):
        pass
    
    def update_metadata(self, metadata: Dict[str, Any]):
        self.metadata.update(metadata)


class NoOpSpan:
    """No-op span for when LangFuse is disabled"""
    
    def __init__(self, name: str):
        self.name = name
    
    def end(self, **kwargs):
        pass
    
    def generation(self, **kwargs):
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Singleton Instance
# ─────────────────────────────────────────────────────────────────────────────

_langfuse_observer: Optional[LangFuseObserver] = None


def get_langfuse_observer() -> LangFuseObserver:
    """Get global LangFuse observer instance"""
    global _langfuse_observer
    if _langfuse_observer is None:
        _langfuse_observer = LangFuseObserver()
    return _langfuse_observer


def reset_langfuse_observer():
    """Reset observer (for testing)"""
    global _langfuse_observer
    _langfuse_observer = None


# ─────────────────────────────────────────────────────────────────────────────
# Integration Helper
# ─────────────────────────────────────────────────────────────────────────────

def observe_llm_call(
    trace: Trace,
    provider: str,
    model: str,
    input_messages: List[Dict[str, str]],
    output_content: str,
    usage: Dict[str, int],
    latency_ms: float,
    cost_usd: float,
    task_type: str,
):
    """
    Helper function to record LLM call in LangFuse.
    
    This provides a consistent interface for recording LLM calls
    across different parts of the codebase.
    
    Args:
        trace: Parent trace
        provider: LLM provider (openai, ollama)
        model: Model name
        input_messages: Messages sent to LLM
        output_content: LLM response
        usage: Token usage
        latency_ms: Call latency
        cost_usd: Call cost
        task_type: Type of task (simple_chat, complex_reasoning, etc.)
    """
    span = trace.span(
        name=f"llm_{task_type}",
        input_data={"messages": input_messages},
        metadata={
            "provider": provider,
            "model": model,
            "task_type": task_type,
        },
    )
    
    span.end(
        output={"content": output_content},
        usage=usage,
        metadata={
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Main observer
    "LangFuseObserver",
    "get_langfuse_observer",
    "reset_langfuse_observer",
    
    # Trace/Span wrappers
    "Trace",
    "Span",
    "NoOpTrace",
    "NoOpSpan",
    
    # Data classes
    "TraceMetadata",
    "SpanMetadata",
    "ScoreData",
    
    # Integration helper
    "observe_llm_call",
]
