"""
RAGAS Quality Evaluation Service for KS-LOS Phase 2

This module provides automated quality evaluation using RAGAS framework:
- Faithfulness: Are claims supported by context?
- Answer Relevance: Does response address user intent?
- Context Precision: Were the right documents retrieved?

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    Conversation                              │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              RAGAS Evaluator                                 │
    ├─────────────────────────────────────────────────────────────┤
    │  Metrics:                                                    │
    │  - Faithfulness (0-1): Claims supported by context          │
    │  - Answer Relevance (0-1): Addresses user intent            │
    │  - Context Precision (0-1): Retrieved right documents       │
    │  - Answer Correctness (0-1): Factually accurate             │
    ├─────────────────────────────────────────────────────────────┤
    │  LLM for Grading:                                           │
    │  - OpenAI (if API key available)                            │
    │  - Ollama Qwen 2.5:7b (fallback, free)                      │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              Quality Report                                  │
    │  - Overall score (0-1)                                      │
    │  - Per-metric scores                                        │
    │  - Sampling decision (evaluate or skip)                     │
    │  - LangFuse integration                                     │
    └─────────────────────────────────────────────────────────────┘

Usage:
    from src.core.evaluation_service import RAGASEvaluator
    
    evaluator = RAGASEvaluator()
    
    # Evaluate conversation
    result = evaluator.evaluate_conversation(
        question="What is FOIR?",
        answer="FOIR is Fixed Obligation to Income Ratio...",
        contexts=[policy_doc_1, policy_doc_2]
    )
    
    # Log to LangFuse
    trace.score(name="ragas_faithfulness", value=result.faithfulness)
"""

import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import random

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RAGASResult:
    """Result from RAGAS evaluation"""
    faithfulness: float  # 0-1
    answer_relevance: float  # 0-1
    context_precision: float  # 0-1
    overall_score: float  # 0-1 (average)
    question: str
    answer: str
    contexts: List[str]
    evaluation_timestamp: datetime = field(default_factory=datetime.now)
    llm_used: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationConfig:
    """Configuration for RAGAS evaluation"""
    # Sampling rate (evaluate N% of conversations)
    sampling_rate: float = 0.1  # 10%
    
    # Minimum conversation length to evaluate (filters out trivial exchanges)
    min_answer_length: int = 20
    
    # LLM for grading
    llm_provider: str = "ollama"  # "openai" or "ollama"
    llm_model: str = "qwen2.5:7b"
    
    # Metrics to compute
    metrics: List[str] = field(default_factory=lambda: [
        "faithfulness",
        "answer_relevance",
        "context_precision"
    ])
    
    # Thresholds for quality alerts
    faithfulness_threshold: float = 0.7
    relevance_threshold: float = 0.7


# Default configuration
DEFAULT_CONFIG = EvaluationConfig()


# ─────────────────────────────────────────────────────────────────────────────
# RAGAS Evaluator
# ─────────────────────────────────────────────────────────────────────────────

class RAGASEvaluator:
    """
    RAGAS-based quality evaluation for KS-LOS conversations.
    
    Provides automated scoring of:
    - Faithfulness: Are claims supported by retrieved context?
    - Answer Relevance: Does response address user's question?
    - Context Precision: Were the right documents retrieved?
    
    Uses LLM-as-a-judge approach with either:
    - OpenAI GPT-4.1 (if API key available)
    - Ollama Qwen 2.5:7b (fallback, free)
    
    Usage:
        evaluator = RAGASEvaluator()
        result = evaluator.evaluate_conversation(
            question="What is FOIR?",
            answer="FOIR is Fixed Obligation to Income Ratio...",
            contexts=[policy_doc]
        )
    """
    
    def __init__(self, config: Optional[EvaluationConfig] = None):
        """
        Initialize RAGAS evaluator.
        
        Args:
            config: Evaluation configuration (uses DEFAULT_CONFIG if not provided)
        """
        self.config = config or DEFAULT_CONFIG
        self._ragas_metrics = None
        self._llm = None
        self._initialized = False
        
        logger.info(f"RAGASEvaluator initialized (sampling={self.config.sampling_rate})")
    
    def _should_evaluate(self) -> bool:
        """
        Determine if this conversation should be evaluated (sampling).
        
        Returns:
            True if conversation should be evaluated
        """
        return random.random() < self.config.sampling_rate
    
    def _ensure_initialized(self):
        """Lazy initialization of RAGAS metrics and LLM"""
        if self._initialized:
            return
        
        try:
            # Try to import RAGAS
            from ragas import evaluate
            from ragas.metrics import (
                faithfulness,
                answer_relevance,
                context_precision,
            )
            
            # Build metrics list
            metrics = []
            if "faithfulness" in self.config.metrics:
                metrics.append(faithfulness)
            if "answer_relevance" in self.config.metrics:
                metrics.append(answer_relevance)
            if "context_precision" in self.config.metrics:
                metrics.append(context_precision)
            
            self._ragas_metrics = metrics
            
            # Initialize LLM for grading
            self._init_llm()
            
            self._initialized = True
            logger.info(f"RAGAS evaluator initialized with {len(metrics)} metrics")
            
        except ImportError as e:
            logger.warning(f"RAGAS not installed, evaluation disabled: {e}")
            self._initialized = False
    
    def _init_llm(self):
        """Initialize LLM for grading"""
        try:
            # Check if OpenAI API key is available
            openai_key = os.getenv("OPENAI_API_KEY")
            
            if openai_key and self.config.llm_provider == "openai":
                from langchain_openai import ChatOpenAI
                
                self._llm = ChatOpenAI(
                    model=self.config.llm_model if self.config.llm_model != "qwen2.5:7b" else "gpt-4.1-mini",
                    api_key=openai_key,
                    temperature=0.0,  # Deterministic grading
                )
                
                logger.info(f"RAGAS using OpenAI ({self._llm.model_name})")
            else:
                # Fallback to Ollama
                from langchain_ollama import ChatOllama
                
                self._llm = ChatOllama(
                    model=self.config.llm_model,
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                    temperature=0.0,
                )
                
                logger.info(f"RAGAS using Ollama ({self.config.llm_model})")
        
        except Exception as e:
            logger.error(f"Failed to initialize LLM for RAGAS: {e}")
            self._llm = None
    
    def evaluate_conversation(
        self,
        question: str,
        answer: str,
        contexts: Optional[List[str]] = None
    ) -> Optional[RAGASResult]:
        """
        Evaluate a single conversation.
        
        Args:
            question: User's question
            answer: AI's response
            contexts: Retrieved policy documents used for RAG
        
        Returns:
            RAGASResult or None if evaluation disabled/failed
        """
        self._ensure_initialized()
        
        if not self._initialized:
            return None
        
        # Check sampling
        if not self._should_evaluate():
            return None
        
        # Validate input
        if len(answer) < self.config.min_answer_length:
            logger.debug(f"Answer too short ({len(answer)} chars), skipping evaluation")
            return None
        
        try:
            # Prepare data for RAGAS
            from datasets import Dataset
            
            data = {
                "question": [question],
                "answer": [answer],
                "contexts": [contexts if contexts else [""]],
            }
            
            dataset = Dataset.from_dict(data)
            
            # Run evaluation
            result = evaluate(
                dataset=dataset,
                metrics=self._ragas_metrics,
                llm=self._llm,
            )
            
            # Extract scores
            scores = result.to_pandas().iloc[0]
            
            faithfulness_score = float(scores.get("faithfulness", 0.5))
            relevance_score = float(scores.get("answer_relevance", 0.5))
            precision_score = float(scores.get("context_precision", 0.5))
            
            # Calculate overall score (weighted average)
            overall = (faithfulness_score + relevance_score + precision_score) / 3
            
            ragas_result = RAGASResult(
                faithfulness=faithfulness_score,
                answer_relevance=relevance_score,
                context_precision=precision_score,
                overall_score=overall,
                question=question,
                answer=answer,
                contexts=contexts if contexts else [],
                llm_used=self.config.llm_model,
                metadata={
                    "sampling_rate": self.config.sampling_rate,
                    "metrics_used": self.config.metrics,
                }
            )
            
            logger.info(
                f"RAGAS evaluation: faithfulness={faithfulness_score:.2f}, "
                f"relevance={relevance_score:.2f}, precision={precision_score:.2f}, "
                f"overall={overall:.2f}"
            )
            
            return ragas_result
            
        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            return None
    
    def evaluate_batch(
        self,
        conversations: List[Dict[str, Any]]
    ) -> List[RAGASResult]:
        """
        Evaluate multiple conversations in batch.
        
        Args:
            conversations: List of dicts with question, answer, contexts
        
        Returns:
            List of RAGASResult (may be shorter than input due to sampling)
        """
        results = []
        
        for conv in conversations:
            result = self.evaluate_conversation(
                question=conv.get("question", ""),
                answer=conv.get("answer", ""),
                contexts=conv.get("contexts")
            )
            
            if result:
                results.append(result)
        
        return results
    
    def should_alert(self, result: RAGASResult) -> bool:
        """
        Check if evaluation result warrants an alert.
        
        Args:
            result: RAGAS evaluation result
        
        Returns:
            True if quality is below thresholds
        """
        if result.faithfulness < self.config.faithfulness_threshold:
            logger.warning(
                f"Low faithfulness score: {result.faithfulness:.2f} "
                f"(threshold: {self.config.faithfulness_threshold})"
            )
            return True
        
        if result.answer_relevance < self.config.relevance_threshold:
            logger.warning(
                f"Low relevance score: {result.answer_relevance:.2f} "
                f"(threshold: {self.config.relevance_threshold})"
            )
            return True
        
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Simplified Evaluator (No RAGAS Dependency)
# ─────────────────────────────────────────────────────────────────────────────

class SimpleQualityEvaluator:
    """
    Simplified quality evaluator that doesn't require RAGAS.
    
    Uses heuristic-based scoring:
    - Answer length
    - Presence of key terms
    - Confidence from hallucination detector
    
    This is a fallback for when RAGAS is not available or too slow.
    """
    
    def evaluate(
        self,
        question: str,
        answer: str,
        hallucination_score: float = 0.0
    ) -> RAGASResult:
        """
        Evaluate conversation using heuristics.
        
        Args:
            question: User's question
            answer: AI's response
            hallucination_score: From hallucination detector (0-1, lower is better)
        
        Returns:
            RAGASResult with estimated scores
        """
        # Heuristic 1: Answer length (longer = more informative, up to a point)
        length_score = min(1.0, len(answer) / 200)  # Cap at 200 chars
        
        # Heuristic 2: Presence of question terms in answer
        question_terms = set(question.lower().split())
        answer_terms = set(answer.lower().split())
        overlap = len(question_terms & answer_terms) / max(len(question_terms), 1)
        relevance_score = min(1.0, overlap * 2)  # Boost overlap score
        
        # Heuristic 3: Hallucination score (inverse)
        faithfulness_score = 1.0 - hallucination_score
        
        # Overall score (weighted average)
        overall = (faithfulness_score * 0.5 + relevance_score * 0.3 + length_score * 0.2)
        
        return RAGASResult(
            faithfulness=faithfulness_score,
            answer_relevance=relevance_score,
            context_precision=0.5,  # Neutral (not evaluated)
            overall_score=overall,
            question=question,
            answer=answer,
            contexts=[],
            llm_used="simple_heuristic",
            metadata={
                "evaluator": "simple",
                "hallucination_score": hallucination_score,
                "length_score": length_score,
            }
        )


# ─────────────────────────────────────────────────────────────────────────────
# Integration Helper
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_and_log(
    question: str,
    answer: str,
    contexts: Optional[List[str]] = None,
    hallucination_score: float = 0.0,
    trace: Optional[Any] = None,
    use_simple: bool = False
) -> Optional[RAGASResult]:
    """
    Evaluate conversation and log to LangFuse.
    
    Args:
        question: User's question
        answer: AI's response
        contexts: Retrieved documents
        hallucination_score: From hallucination detector
        trace: LangFuse trace for logging
        use_simple: Use simple evaluator (no RAGAS)
    
    Returns:
        RAGASResult or None
    
    Usage:
        result = evaluate_and_log(
            question=user_question,
            answer=ai_response,
            contexts=retrieved_docs,
            hallucination_score=hallucination_report.hallucination_score,
            trace=langfuse_trace
        )
    """
    if use_simple:
        evaluator = SimpleQualityEvaluator()
        result = evaluator.evaluate(question, answer, hallucination_score)
    else:
        evaluator = RAGASEvaluator()
        result = evaluator.evaluate_conversation(question, answer, contexts)
        
        # Fall back to simple evaluator if RAGAS fails
        if not result:
            evaluator = SimpleQualityEvaluator()
            result = evaluator.evaluate(question, answer, hallucination_score)
    
    # Log to LangFuse
    if trace and result:
        trace.score(
            name="ragas_faithfulness",
            value=result.faithfulness,
            comment=f"Faithfulness score"
        )
        trace.score(
            name="ragas_relevance",
            value=result.answer_relevance,
            comment=f"Answer relevance"
        )
        trace.score(
            name="ragas_overall",
            value=result.overall_score,
            comment=f"Overall quality score"
        )
    
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Data classes
    "RAGASResult",
    "EvaluationConfig",
    
    # Evaluators
    "RAGASEvaluator",
    "SimpleQualityEvaluator",
    
    # Integration helper
    "evaluate_and_log",
    
    # Default config
    "DEFAULT_CONFIG",
]
