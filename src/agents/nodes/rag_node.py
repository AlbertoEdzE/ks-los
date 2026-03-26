"""
RAG Node for Agentic Orchestrator

Retrieval-Augmented Generation node for policy-grounded responses.
Uses PGVector knowledge base to ground LLM responses in actual policies.

Features:
- Policy retrieval from PGVector
- Policy-grounded response generation
- Citation of sources
- Fallback for unknown policies

Usage:
    node = RAGNode(knowledge_base=kb, llm=llm)
    updated_state = node.process(current_state)
"""

from typing import Dict, List, Any, Optional
import logging
import re

from src.agents.graph_state import AgenticOrchestratorState, Message


class RAGNode:
    """
    Handles policy-grounded responses using RAG.
    
    Responsibilities:
    1. Detect policy-related questions
    2. Retrieve relevant policies from knowledge base
    3. Generate grounded responses with citations
    4. Fallback gracefully if no policies found
    
    Scientific Design:
    - Cosine similarity search (k=3 default)
    - Relevance scoring
    - Citation tracking for audit
    - Confidence-based fallback
    
    Usage:
        node = RAGNode(knowledge_base=kb)
        state = node.process(state)
    """
    
    # Policy-related question patterns
    POLICY_PATTERNS = [
        r"\b(?:what\s+is|what\s+are)\s+(?:the\s+)?(?:minimum|maximum|max|min)\b",
        r"\b(?:eligibility|criteria|requirements)\b",
        r"\b(?:interest\s+rate|rates)\b",
        r"\b(?:loan\s+)?(?:limit|limits|amount)\b",
        r"\b(?:processing\s+)?(?:time|timeframe|how\s+long)\b",
        r"\b(?:documents|documentation|papers)\b",
        r"\b(?:approve|approval|approved|reject|rejected)\b",
        r"\b(?:credit\s+)?(?:score|bureau|rating)\b",
        r"\b(?:down\s+)?(?:payment|deposit)\b",
        r"\b(?:ltv|loan\s+to\s+value)\b",
        r"\b(?:foir|debt\s+to\s+income|dti)\b",
        r"\b(?:policy|policies|rule|rules|regulation)\b",
        r"\b(?:can\s+i|am\s+i\s+eligible|do\s+i\s+qualify)\b",
    ]
    
    def __init__(
        self,
        knowledge_base: Optional[Any] = None,
        llm: Optional[Any] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize RAG node.
        
        Args:
            knowledge_base: PGVector knowledge base instance
            llm: LLM for response generation
            config: Configuration options
        """
        self.knowledge_base = knowledge_base
        self.llm = llm
        self.config = config or {}
        
        # RAG configuration
        self.k = self.config.get("retrieval_k", 3)  # Number of documents to retrieve
        self.similarity_threshold = self.config.get("similarity_threshold", 0.5)
        
        self.logger = logging.getLogger(__name__)
    
    def process(self, state: AgenticOrchestratorState) -> AgenticOrchestratorState:
        """
        Process conversation for policy questions.
        
        Args:
            state: Current agentic state
            
        Returns:
            Updated state with policy-grounded response
        """
        if not state.conversation_history:
            return state
        
        last_message = state.conversation_history[-1].content
        
        # Check if this is a policy question
        if self._is_policy_question(last_message):
            state = self._handle_policy_question(state, last_message)
        
        return state
    
    def _is_policy_question(self, text: str) -> bool:
        """
        Check if message is a policy-related question.
        
        Args:
            text: User message text
            
        Returns:
            True if policy question
        """
        text_lower = text.lower()
        
        # Check for policy patterns
        matches_pattern = any(
            re.search(pattern, text_lower)
            for pattern in self.POLICY_PATTERNS
        )
        
        # Also check for question indicators
        is_question = any([
            "?" in text,
            text_lower.startswith(("what", "how", "can", "do", "does", "is", "are")),
        ])
        
        return matches_pattern and is_question
    
    def _handle_policy_question(
        self,
        state: AgenticOrchestratorState,
        question: str
    ) -> AgenticOrchestratorState:
        """
        Handle policy-related question with RAG.
        
        Args:
            state: Current state
            question: User's question
            
        Returns:
            Updated state with grounded response
        """
        self.logger.info(f"Policy question detected: {question[:50]}...")
        
        # Retrieve relevant policies
        if self.knowledge_base:
            try:
                retrieved_docs = self.knowledge_base.search(question, k=self.k)
                
                # Filter by similarity threshold
                relevant_docs = [
                    doc for doc in retrieved_docs
                    if getattr(doc, 'similarity', 0.5) >= self.similarity_threshold
                ]
                
                if relevant_docs:
                    # Generate grounded response
                    response_text = self._generate_grounded_response(
                        question,
                        relevant_docs
                    )
                    
                    state.add_message("assistant", response_text, metadata={
                        "rag_used": True,
                        "policies_retrieved": len(relevant_docs),
                        "citations": [
                            getattr(doc, 'metadata', {}).get('source', 'Unknown')
                            for doc in relevant_docs
                        ],
                    })
                    
                    self.logger.info(
                        f"RAG response generated with {len(relevant_docs)} policies"
                    )
                    
                    return state
                    
            except Exception as e:
                self.logger.warning(f"RAG retrieval failed: {str(e)}")
        
        # Fallback: No knowledge base or retrieval failed
        response_text = self._generate_fallback_response(question, state)
        
        state.add_message("assistant", response_text, metadata={
            "rag_used": False,
            "fallback": True,
        })
        
        return state
    
    def _generate_grounded_response(
        self,
        question: str,
        documents: List[Any]
    ) -> str:
        """
        Generate response grounded in retrieved policies.
        
        Args:
            question: User's question
            documents: Retrieved policy documents
            
        Returns:
            Grounded response text
        """
        # Extract policy content
        policy_content = []
        citations = []
        
        for i, doc in enumerate(documents, 1):
            content = getattr(doc, 'page_content', str(doc))
            metadata = getattr(doc, 'metadata', {})
            source = metadata.get('source', f'Policy {i}')
            
            policy_content.append(f"[{i}] {content}")
            citations.append(f"[{i}] {source}")
        
        # Generate response using LLM if available
        if self.llm:
            try:
                from langchain_core.messages import SystemMessage, HumanMessage
                
                system_prompt = """You are a helpful loan advisor. Answer the user's question 
                based ONLY on the provided policy documents. Include citations like [1], [2], etc. 
                If the policies don't contain enough information, say so clearly."""
                
                user_prompt = f"""Policies:
                {' '.join(policy_content)}

                Question: {question}

                Answer with citations:"""
                
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
                
                response = self.llm.invoke(messages)
                return response.content
                
            except Exception as e:
                self.logger.warning(f"LLM generation failed: {str(e)}")
        
        # Fallback: Simple concatenation of policies
        response_text = (
            f"Based on our policies:\n\n"
            f"{' '.join(policy_content)}\n\n"
            f"Sources: {', '.join(citations)}"
        )
        
        return response_text
    
    def _generate_fallback_response(
        self,
        question: str,
        state: AgenticOrchestratorState
    ) -> str:
        """
        Generate fallback response when RAG unavailable.
        
        Args:
            question: User's question
            state: Current state
            
        Returns:
            Fallback response text
        """
        question_lower = question.lower()
        
        # Common policy questions with canned responses
        if "interest rate" in question_lower:
            return (
                "Our interest rates typically range from 7.5% to 12% per annum, "
                "depending on the loan type, amount, your credit profile, and "
                "employment type. Once I have more information about your specific "
                "needs, I can provide you with personalized rates.\n\n"
                "Would you like to continue with your application?"
            )
        
        elif "minimum" in question_lower and "income" in question_lower:
            return (
                "Our minimum income requirement varies by loan type:\n"
                "• Personal Loans: $3,000/month\n"
                "• Home Loans: $5,000/month\n"
                "• Auto Loans: $4,000/month\n\n"
                "These are general guidelines - actual eligibility depends on your "
                "complete financial profile. What's your monthly income?"
            )
        
        elif "documents" in question_lower:
            return (
                "The documents required depend on your employment type:\n\n"
                "**For Salaried:**\n"
                "• National ID or Passport\n"
                "• Job Letter\n"
                "• Last 3 months' pay slips\n"
                "• Last 6 months' bank statements\n\n"
                "**For Self-Employed:**\n"
                "• Business Registration\n"
                "• Last 2 years' financial statements\n"
                "• Last 2 years' tax returns\n"
                "• Last 6 months' bank statements\n\n"
                "I'll provide you with a complete checklist once we submit your application."
            )
        
        elif "processing time" in question_lower or "how long" in question_lower:
            return (
                "Processing times vary by loan type:\n"
                "• Fast-Track (STP): 24-48 hours\n"
                "• Standard Personal Loans: 2-3 business days\n"
                "• Home Loans: 5-7 business days\n"
                "• Auto Loans: 2-4 business days\n\n"
                "These timelines assume all documents are provided correctly. "
                "Shall we continue with your application?"
            )
        
        else:
            # Generic response
            return (
                "That's a great question! Our loan policies cover various aspects like "
                "eligibility criteria, interest rates, documentation requirements, and "
                "processing timelines.\n\n"
                "A loan officer can provide you with detailed policy information. "
                "In the meantime, would you like to continue with your application? "
                "I can answer specific questions as we go."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Function
# ─────────────────────────────────────────────────────────────────────────────

def process_rag(
    state: AgenticOrchestratorState,
    knowledge_base: Optional[Any] = None,
    llm: Optional[Any] = None,
    **kwargs
) -> AgenticOrchestratorState:
    """
    Convenience function to process RAG-based responses.
    
    Args:
        state: Current state
        knowledge_base: PGVector knowledge base
        llm: LLM for generation
        **kwargs: Additional arguments
        
    Returns:
        Updated state
    """
    node = RAGNode(knowledge_base=knowledge_base, llm=llm, **kwargs)
    return node.process(state)


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "RAGNode",
    "process_rag",
]
