"""
LLM Router Service for KS-LOS Phase 2

Hybrid LLM routing with automatic provider selection based on:
1. Environment variable (OPENAI_API_KEY)
2. Task type (simple vs complex)
3. Provider availability

Features:
- Seamless OpenAI ↔ Ollama switching
- Automatic fallback on errors
- Token usage tracking
- Cost estimation
- LangFuse integration ready

Usage:
    router = LLMRouter()
    response = router.chat(messages, task_type="intent_extraction")
    print(f"Provider used: {response.provider}")
    print(f"Tokens: {response.usage}")
    print(f"Cost: ${response.cost_usd}")
"""

import os
import time
import logging
import contextvars
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass, field
import yaml

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

_request_llm_calls: contextvars.ContextVar[Optional[List[Dict[str, Any]]]] = contextvars.ContextVar(
    "ks_los_request_llm_calls",
    default=None,
)
_request_langfuse_trace: contextvars.ContextVar[Optional[Any]] = contextvars.ContextVar(
    "ks_los_request_langfuse_trace",
    default=None,
)


def reset_request_llm_calls() -> None:
    _request_llm_calls.set([])


def get_request_llm_calls() -> List[Dict[str, Any]]:
    calls = _request_llm_calls.get()
    return list(calls) if calls else []


def set_request_langfuse_trace(trace: Any) -> contextvars.Token:
    return _request_langfuse_trace.set(trace)


def get_request_langfuse_trace() -> Optional[Any]:
    return _request_langfuse_trace.get()


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ChatResponse:
    """Response from LLM router with metadata"""
    content: str
    provider: str  # "openai" or "ollama"
    model: str  # e.g., "gpt-4.1-mini" or "qwen2.5:7b"
    usage: Dict[str, int] = field(default_factory=dict)  # prompt_tokens, completion_tokens
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingRule:
    """Rule for routing tasks to providers"""
    task: str
    use: Literal["primary", "fallback"]


@dataclass
class LLMRoutingConfig:
    """Configuration for LLM routing"""
    primary_provider: str
    primary_model: str
    primary_api_key_env: str
    fallback_provider: str
    fallback_model: str
    fallback_base_url: str
    routing_rules: List[RoutingRule]
    retry_on_error: bool
    primary_timeout_seconds: int
    max_retries: int
    cost_rates: Dict[str, float]


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Loader
# ─────────────────────────────────────────────────────────────────────────────

def load_llm_routing_config(config_path: Optional[str] = None) -> LLMRoutingConfig:
    """
    Load LLM routing configuration from YAML file.
    
    Args:
        config_path: Path to config file (default: src/config/llm_routing.yaml)
    
    Returns:
        LLMRoutingConfig object
    """
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__),
            "llm_routing.yaml"
        )
    
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    routing_rules = [
        RoutingRule(
            task=rule['task'],
            use=rule['use']
        )
        for rule in config_data['llm_routing']['routing_rules']
    ]
    
    return LLMRoutingConfig(
        primary_provider=config_data['llm_routing']['primary']['provider'],
        primary_model=config_data['llm_routing']['primary']['model'],
        primary_api_key_env=config_data['llm_routing']['primary']['api_key_env'],
        fallback_provider=config_data['llm_routing']['fallback']['provider'],
        fallback_model=config_data['llm_routing']['fallback']['model'],
        fallback_base_url=config_data['llm_routing']['fallback']['base_url'],
        routing_rules=routing_rules,
        retry_on_error=config_data['llm_routing']['fallback_behavior']['retry_on_error'],
        primary_timeout_seconds=config_data['llm_routing']['fallback_behavior']['primary_timeout_seconds'],
        max_retries=config_data['llm_routing']['fallback_behavior']['max_retries'],
        cost_rates=config_data['llm_routing']['cost_tracking']['rates'],
    )


# ─────────────────────────────────────────────────────────────────────────────
# LLM Router Service
# ─────────────────────────────────────────────────────────────────────────────

class LLMRouter:
    """
    Hybrid LLM router with automatic provider selection.
    
    Automatically routes LLM calls to OpenAI (if API key available) or
    Ollama (local fallback) based on task type and configuration.
    
    Features:
    - Zero code changes to switch providers
    - Automatic fallback on errors
    - Token usage and cost tracking
    - LangFuse integration ready
    
    Usage:
        router = LLMRouter()
        response = router.chat(messages, task_type="intent_extraction")
    """
    
    def __init__(self, config: Optional[LLMRoutingConfig] = None):
        """
        Initialize LLM router.
        
        Args:
            config: Routing configuration (auto-loaded if not provided)
        """
        self.config = config or load_llm_routing_config()
        self._primary_llm: Optional[BaseChatModel] = None
        self._fallback_llm: Optional[BaseChatModel] = None
        
        logger.info("LLM Router initialized")
        logger.info(f"Primary provider: {self.config.primary_provider}/{self.config.primary_model}")
        logger.info(f"Fallback provider: {self.config.fallback_provider}/{self.config.fallback_model}")
    
    def get_provider(self, task_type: str = "simple_chat") -> str:
        """
        Determine which provider to use based on task type and API key availability.
        
        Args:
            task_type: Type of task (e.g., "simple_chat", "complex_reasoning")
        
        Returns:
            Provider name: "openai" or "ollama"
        """
        # Check if OpenAI API key is available
        api_key = os.getenv(self.config.primary_api_key_env)
        
        if not api_key:
            # No API key - always use fallback
            logger.debug(f"No API key available, using fallback provider")
            return self.config.fallback_provider
        
        # Find routing rule for this task type
        rule = next(
            (r for r in self.config.routing_rules if r.task == task_type),
            None
        )
        
        if rule and rule.use == "primary":
            logger.debug(f"Task '{task_type}' routed to primary provider")
            return self.config.primary_provider
        else:
            logger.debug(f"Task '{task_type}' routed to fallback provider")
            return self.config.fallback_provider
    
    def _get_primary_llm(self) -> BaseChatModel:
        """Get or create primary LLM instance (lazy initialization)"""
        if self._primary_llm is None:
            # Check if in test mode first
            if os.getenv("PYTEST_CURRENT_TEST") or str(os.getenv("LLM_TEST_MODE", "")).strip() in {"1", "true", "yes"}:
                # Use test LLM for deterministic testing
                from src.config.llm import get_llm
                self._primary_llm = get_llm(temperature=0.7)
                logger.info("Primary LLM initialized: _TestLLM (test mode)")
                return self._primary_llm
            
            try:
                from langchain_openai import ChatOpenAI
                
                api_key = os.getenv(self.config.primary_api_key_env)
                if not api_key:
                    raise RuntimeError(f"API key not found: {self.config.primary_api_key_env}")
                
                self._primary_llm = ChatOpenAI(
                    model=self.config.primary_model,
                    api_key=api_key,
                    temperature=0.7,
                    timeout=self.config.primary_timeout_seconds,
                )
                
                logger.info(f"Primary LLM initialized: {self.config.primary_model}")
                
            except ImportError:
                logger.warning("langchain-openai not installed, falling back to Ollama")
                raise RuntimeError("OpenAI provider not available")
        
        return self._primary_llm
    
    def _get_fallback_llm(self) -> BaseChatModel:
        """Get or create fallback LLM instance (lazy initialization)"""
        if self._fallback_llm is None:
            # Use existing get_llm from src.config.llm for consistency
            # This ensures test mode (_TestLLM) is respected
            from src.config.llm import get_llm
            
            self._fallback_llm = get_llm(
                temperature=0.7,
                model=self.config.fallback_model
            )
            
            logger.info(f"Fallback LLM initialized: {self.config.fallback_model}")
            
            return self._fallback_llm
        
        return self._fallback_llm
    
    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """
        Calculate cost based on token usage.
        
        Args:
            model: Model identifier (e.g., "openai/gpt-4.1-mini")
            usage: Token usage dict (prompt_tokens, completion_tokens)
        
        Returns:
            Cost in USD
        """
        rate_key = f"{model}"
        rate = self.config.cost_rates.get(rate_key, 0.0)
        
        total_tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        cost = (total_tokens / 1000) * rate
        
        return cost
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        task_type: str = "simple_chat",
        session_id: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout_seconds: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """
        Send chat message through appropriate LLM provider.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            task_type: Type of task for routing decision
            **kwargs: Additional arguments passed to LLM
        
        Returns:
            ChatResponse with content and metadata
        
        Raises:
            RuntimeError: If both providers fail
        """
        provider = self.get_provider(task_type)
        retries = 0
        last_error: Optional[Exception] = None
        
        while retries <= self.config.max_retries:
            try:
                start_time = time.time()
                
                # Select LLM
                if provider == self.config.primary_provider:
                    llm = self._get_primary_llm() if temperature is None else self._build_primary_llm(temperature)
                    model = self.config.primary_model
                else:
                    llm = self._get_fallback_llm() if temperature is None else self._build_fallback_llm(temperature)
                    model = self.config.fallback_model
                
                # Convert messages to LangChain format
                lc_messages = []
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    
                    if role == "system":
                        lc_messages.append(SystemMessage(content=content))
                    elif role == "assistant":
                        lc_messages.append(AIMessage(content=content))
                    else:
                        lc_messages.append(HumanMessage(content=content))
                
                # Invoke LLM
                observer_trace = get_request_langfuse_trace()
                if observer_trace is None and session_id:
                    try:
                        from src.shared.observability import get_langfuse_observer

                        observer = get_langfuse_observer()
                        observer_trace = observer.start_trace(
                            name="llm_router",
                            session_id=session_id,
                            metadata={"task_type": task_type},
                        )
                    except Exception:
                        observer_trace = None

                span = None
                if observer_trace is not None:
                    try:
                        span = observer_trace.span(
                            name=task_type,
                            input_data={"messages": messages},
                            metadata={"provider": provider, "model": model},
                        )
                    except Exception:
                        span = None

                invoke_config = {}
                if timeout_seconds is not None:
                    invoke_config["timeout"] = timeout_seconds

                start_time = time.time()
                response_obj = llm.invoke(lc_messages, config=invoke_config or None, **kwargs)
                end_time = time.time()

                # Extract usage metadata (handle None for test LLM)
                usage_metadata = getattr(response_obj, "usage_metadata", None) or {}
                usage = {
                    "prompt_tokens": usage_metadata.get("input_tokens", 0) if isinstance(usage_metadata, dict) else 0,
                    "completion_tokens": usage_metadata.get("output_tokens", 0) if isinstance(usage_metadata, dict) else 0,
                }

                # Calculate latency and cost
                latency_ms = (end_time - start_time) * 1000
                cost_usd = self._calculate_cost(model, usage)

                logger.info(
                    f"LLM call: provider={provider}, model={model}, "
                    f"latency={latency_ms:.0f}ms, tokens={usage}, cost=${cost_usd:.6f}"
                )

                call_record = {
                    "task_type": task_type,
                    "provider": provider,
                    "model": model,
                    "latency_ms": latency_ms,
                    "usage": usage,
                    "cost_usd": cost_usd,
                }
                existing = _request_llm_calls.get()
                if existing is None:
                    _request_llm_calls.set([call_record])
                else:
                    existing.append(call_record)

                if span is not None:
                    try:
                        span.end(
                            output={"content": response_obj.content},
                            usage=usage,
                            metadata={"cost_usd": cost_usd},
                        )
                    except Exception:
                        pass

                return ChatResponse(
                    content=response_obj.content,
                    provider=provider,
                    model=model,
                    usage=usage,
                    latency_ms=latency_ms,
                    cost_usd=cost_usd,
                    metadata={
                        "task_type": task_type,
                        "retries": retries,
                    }
                )
                
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call failed (provider={provider}, retry={retries}): {str(e)}")
                
                if not self.config.retry_on_error:
                    raise
                
                # Switch to fallback if primary failed
                if provider == self.config.primary_provider:
                    logger.info("Switching to fallback provider")
                    provider = self.config.fallback_provider
                    retries += 1
                else:
                    # Already on fallback, re-raise
                    break
        
        # All retries exhausted
        raise RuntimeError(f"LLM call failed after {retries} retries: {str(last_error)}")

    def _build_primary_llm(self, temperature: float) -> BaseChatModel:
        if os.getenv("PYTEST_CURRENT_TEST") or str(os.getenv("LLM_TEST_MODE", "")).strip() in {"1", "true", "yes"}:
            from src.config.llm import get_llm

            return get_llm(temperature=temperature)

        from langchain_openai import ChatOpenAI

        api_key = os.getenv(self.config.primary_api_key_env)
        if not api_key:
            raise RuntimeError(f"API key not found: {self.config.primary_api_key_env}")

        return ChatOpenAI(
            model=self.config.primary_model,
            api_key=api_key,
            temperature=temperature,
            timeout=self.config.primary_timeout_seconds,
        )

    def _build_fallback_llm(self, temperature: float) -> BaseChatModel:
        from src.config.llm import get_llm

        return get_llm(
            temperature=temperature,
            model=self.config.fallback_model,
        )
    
    def generate(
        self,
        prompt: str,
        task_type: str = "simple_chat",
        **kwargs
    ) -> ChatResponse:
        """
        Generate response for a single prompt.
        
        Convenience method for single-turn generation.
        
        Args:
            prompt: Input prompt text
            task_type: Type of task for routing
            **kwargs: Additional arguments
        
        Returns:
            ChatResponse
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, task_type=task_type, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton Instance
# ─────────────────────────────────────────────────────────────────────────────

# Global router instance (lazy initialization)
_router_instance: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """
    Get global LLM router instance (singleton).
    
    Returns:
        LLMRouter instance
    """
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance


def reset_llm_router():
    """Reset router instance (useful for testing)"""
    global _router_instance
    _router_instance = None


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Data classes
    "ChatResponse",
    "RoutingRule",
    "LLMRoutingConfig",
    
    # Configuration
    "load_llm_routing_config",
    
    # Router service
    "LLMRouter",
    
    # Singleton
    "get_llm_router",
    "reset_llm_router",

    # Request-scoped context
    "reset_request_llm_calls",
    "get_request_llm_calls",
    "set_request_langfuse_trace",
    "get_request_langfuse_trace",
]
