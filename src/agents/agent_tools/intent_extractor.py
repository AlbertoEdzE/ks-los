"""
Intent Extraction Tool for Agentic Orchestrator

Extracts structured borrower intent from conversation history using LLM.
"""

from typing import List, Optional, Type, Dict, Any
from langchain.tools import BaseTool
from langchain_community.chat_models import ChatOllama
from pydantic import BaseModel, Field
import json
import re
import asyncio

from src.agents.prompts import INTENT_EXTRACTION_PROMPT
from src.agents.structured_parser import IntentAnalysis


class IntentExtractionInput(BaseModel):
    """Input schema for intent extraction tool"""
    conversation_history: List[Dict[str, str]] = Field(
        description="List of conversation messages with 'role' and 'content' keys"
    )


class IntentExtractionResult(BaseModel):
    """Result from intent extraction"""
    context: IntentAnalysis
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence score")
    field_confidence: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-field confidence scores"
    )
    raw_llm_output: Optional[str] = Field(default=None, description="Raw LLM JSON output")
    parse_errors: Optional[str] = Field(default=None, description="Any parsing errors")


class IntentExtractorTool(BaseTool):
    """
    Extract borrower intent and context from conversation history.
    
    This tool uses an LLM to semantically understand the borrower's needs,
    extracting structured data like loan purpose, amount, income, employment,
    and contact information.
    
    Features:
    - Semantic understanding (not just regex)
    - Handles variations in phrasing
    - Caribbean context awareness
    - Confidence scoring per field
    - Graceful degradation on ambiguous input
    
    Usage:
        tool = IntentExtractorTool()
        result = tool.run(conversation_history=[...])
        
        if result.confidence > 0.8:
            # Auto-accept extraction
            context = result.context
        elif result.confidence > 0.5:
            # Ask clarifying questions
            ...
        else:
            # Use explicit questioning
            ...
    """
    
    name: str = "extract_borrower_intent"
    description: str = (
        "Extracts structured borrower intent from conversation history. "
        "Returns loan purpose, amount, income, employment type, contact info, "
        "and confidence scores. Use this to understand what the borrower wants."
    )
    args_schema: Type[BaseModel] = IntentExtractionInput
    
    # Configuration
    model_name: str = "qwen2.5:7b"
    ollama_base_url: str = "http://localhost:11434"
    temperature: float = 0.1  # Low temperature for extraction tasks
    timeout_seconds: int = 30  # Timeout for LLM calls
    
    def __init__(self, **kwargs):
        """Initialize with optional configuration"""
        super().__init__(**kwargs)
        
        # Override defaults from kwargs
        if "model_name" in kwargs:
            self.model_name = kwargs["model_name"]
        if "ollama_base_url" in kwargs:
            self.ollama_base_url = kwargs["ollama_base_url"]
        if "temperature" in kwargs:
            self.temperature = kwargs["temperature"]
    
    def _run(self, conversation_history: List[Dict[str, str]]) -> str:
        """
        Extract intent from conversation history.
        
        Args:
            conversation_history: List of {role, content} dicts
            
        Returns:
            JSON string with extraction result
        """
        try:
            # Build messages for LLM
            messages = self._build_messages(conversation_history)
            
            # Call LLM
            llm_response = self._call_llm(messages)
            
            # Parse and validate
            result = self._parse_response(llm_response)
            
            # Return as JSON string
            return result.model_dump_json()
            
        except Exception as e:
            # Return error result
            error_result = IntentExtractionResult(
                context=IntentAnalysis(),
                confidence=0.0,
                parse_errors=str(e)
            )
            return error_result.model_dump_json()
    
    async def _arun(self, conversation_history: List[Dict[str, str]]) -> str:
        """
        Async version of intent extraction.
        
        Uses asyncio.to_thread to run sync _run in thread pool,
        preventing blocking of async event loop.
        """
        return await asyncio.to_thread(self._run, conversation_history)
    
    def _build_messages(self, conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Build messages list for LLM API.
        
        Args:
            conversation_history: Conversation messages
            
        Returns:
            Formatted messages for LLM
        """
        # System prompt
        system_message = {
            "role": "system",
            "content": INTENT_EXTRACTION_PROMPT
        }
        
        # Format conversation history
        formatted_history = []
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_history.append({"role": role, "content": content})
        
        # User message with conversation
        user_message = {
            "role": "user",
            "content": f"Extract intent from this conversation:\n\n{self._format_conversation(formatted_history)}"
        }
        
        return [system_message, user_message]
    
    def _format_conversation(self, messages: List[Dict[str, str]]) -> str:
        """Format conversation for LLM input"""
        lines = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            lines.append(f"{role.upper()}: {content}")
        return "\n\n".join(lines)
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        Call Ollama LLM for extraction.

        Args:
            messages: Formatted messages for LLM

        Returns:
            Raw LLM response text

        Raises:
            RuntimeError: If LLM call fails or times out
        """
        try:
            # Initialize ChatOllama
            llm = ChatOllama(
                model=self.model_name,
                base_url=self.ollama_base_url,
                temperature=self.temperature,
                num_predict=1024,  # Limit response length
            )

            # Call LLM with timeout
            response = llm.invoke(messages, {"timeout": self.timeout_seconds})

            return response.content

        except asyncio.TimeoutError:
            raise RuntimeError(
                f"LLM call timed out after {self.timeout_seconds} seconds"
            )
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {str(e)}")
    
    def _parse_response(self, llm_response: str) -> IntentExtractionResult:
        """
        Parse and validate LLM response.
        
        Args:
            llm_response: Raw LLM output
            
        Returns:
            Validated extraction result
        """
        try:
            # Try to extract JSON from response
            json_str = self._extract_json(llm_response)
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Create IntentAnalysis
            context = IntentAnalysis(**data)
            
            # Compute confidence scores
            field_confidence = self._compute_field_confidence(context, data)
            overall_confidence = sum(field_confidence.values()) / len(field_confidence) if field_confidence else 0.5
            
            return IntentExtractionResult(
                context=context,
                confidence=overall_confidence,
                field_confidence=field_confidence,
                raw_llm_output=json_str
            )
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Validation failed: {str(e)}")
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from LLM response (may contain markdown).

        Args:
            text: Raw LLM response

        Returns:
            Clean JSON string
        """
        # Remove markdown code blocks
        text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```\s*$", "", text)
        
        # Try to find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        
        if start >= 0 and end > start:
            return text[start:end].strip()
        
        return text.strip()
    
    def _compute_field_confidence(self, context: IntentAnalysis, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Compute per-field confidence scores.
        
        Heuristics:
        - Higher confidence for fields with specific values
        - Lower confidence for vague or missing fields
        - Extra boost for consistency across conversation
        
        Args:
            context: Parsed IntentAnalysis
            data: Raw parsed data
            
        Returns:
            Dict mapping field names to confidence scores (0-1)
        """
        confidence = {}
        
        # Check each field
        for field_name in data.keys():
            value = getattr(context, field_name, None)
            
            if value is None:
                confidence[field_name] = 0.0
            elif isinstance(value, str):
                # String fields
                if value.strip() == "" or value.lower() == "null":
                    confidence[field_name] = 0.0
                elif len(value) < 3:
                    # Very short values might be incomplete
                    confidence[field_name] = 0.5
                else:
                    # Specific, detailed values get higher confidence
                    confidence[field_name] = min(0.9, 0.6 + len(value) / 100)
            elif isinstance(value, (int, float)):
                # Numeric fields
                if value == 0:
                    confidence[field_name] = 0.3  # Zero might mean unknown
                else:
                    confidence[field_name] = 0.85
            else:
                confidence[field_name] = 0.5
        
        # Boost confidence for seriousness_score and fit_score if present
        if context.seriousness_score is not None:
            confidence["seriousness_score"] = 0.9
        if context.fit_score is not None:
            confidence["fit_score"] = 0.9
        
        # Boost confidence for email if it looks valid
        if context.email and "@" in context.email and "." in context.email:
            confidence["email"] = 0.95
        
        # Boost confidence for phone if it has digits
        if context.phone and any(c.isdigit() for c in context.phone):
            confidence["phone"] = 0.9
        
        return confidence


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Function
# ─────────────────────────────────────────────────────────────────────────────

def extract_intent_from_conversation(
    conversation_history: List[Dict[str, str]],
    model_name: str = "qwen2.5:7b",
    temperature: float = 0.1
) -> IntentExtractionResult:
    """
    Convenience function to extract intent from conversation.
    
    Args:
        conversation_history: List of {role, content} dicts
        model_name: Ollama model to use
        temperature: LLM temperature (lower = more deterministic)
        
    Returns:
        IntentExtractionResult with extracted context and confidence
    """
    tool = IntentExtractorTool(
        model_name=model_name,
        temperature=temperature
    )
    
    result_json = tool.run(conversation_history=conversation_history)
    result = IntentExtractionResult.model_validate_json(result_json)
    
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "IntentExtractorTool",
    "IntentExtractionInput",
    "IntentExtractionResult",
    "extract_intent_from_conversation",
]
