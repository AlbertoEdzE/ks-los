"""
Structured Output Parser for Agentic Orchestrator

Extracts structured data from LLM responses containing XML-tagged JSON blocks.
Supports the LNAI-style conversation format with typed Pydantic validation.

Example LLM Response:
```
I've analyzed your financials. Here are your options:

<intent_analysis>
{"purpose": "home_purchase", "loanAmount": 400000, "monthlyIncome": 8000}
</intent_analysis>

<loan_snapshot>
{"loanAmount": 400000, "estimatedEmi": 2800, "tenureYears": 20}
</loan_snapshot>
```

This parser extracts each tagged block and validates against Pydantic schemas.
"""

import re
import json
from typing import Dict, List, Any, Optional, TypeVar, Type, Generic
from pydantic import BaseModel, ValidationError, Field, ConfigDict
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models for XML-Tagged Content
# ─────────────────────────────────────────────────────────────────────────────

class IntentAnalysis(BaseModel):
    """Extracted intent from borrower conversation"""
    model_config = ConfigDict(extra="allow")
    
    purpose: Optional[str] = None
    urgency: Optional[str] = None  # "low", "medium", "high", "critical"
    affordability: Optional[str] = None
    monthly_income: Optional[str] = None
    existing_debts: Optional[str] = None
    loan_amount: Optional[str] = None
    preferred_tenure: Optional[str] = None
    collateral_available: Optional[str] = None
    employment_type: Optional[str] = None
    credit_history: Optional[str] = None
    seriousness_score: Optional[int] = Field(default=None, ge=0, le=100)
    fit_score: Optional[int] = Field(default=None, ge=0, le=100)
    next_conversation_angle: Optional[str] = None
    
    # Additional fields for flexibility
    email: Optional[str] = None
    phone: Optional[str] = None
    borrower_name: Optional[str] = None


class LoanSnapshot(BaseModel):
    """Computed loan metrics snapshot"""
    model_config = ConfigDict(extra="allow")
    
    loan_type: Optional[str] = None
    loan_amount: Optional[str] = None
    estimated_em: Optional[str] = None  # EMI per month
    tenure: Optional[str] = None
    rate_band: Optional[str] = None
    down_payment: Optional[str] = None
    property_value: Optional[str] = None
    ltv: Optional[str] = None
    foir: Optional[str] = None
    currency: Optional[str] = "$"


class LoanRecommendation(BaseModel):
    """Single loan recommendation option"""
    model_config = ConfigDict(extra="allow")
    
    name: str
    type: str
    estimated_rate: str
    estimated_em: str
    tenure: str
    total_interest: str
    approval_speed: Optional[str] = None
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    recommendation: str


class LoanApplication(BaseModel):
    """Submitted loan application data"""
    model_config = ConfigDict(extra="allow")
    
    first_name: str
    last_name: str
    email: str
    phone: str
    loan_type: str
    loan_amount: str
    purpose: str
    employment_type: str
    monthly_income: str
    existing_debts: str
    tenure: Optional[str] = None
    credit_bureau_rating: Optional[str] = None
    down_payment: Optional[str] = None
    property_value: Optional[str] = None


class DocumentItem(BaseModel):
    """Single document in checklist"""
    name: str
    description: str = ""
    required: bool = True


class DocumentsChecklist(BaseModel):
    """Required documents by category"""
    model_config = ConfigDict(populate_by_name=True)
    
    required_now: List[DocumentItem] = Field(default_factory=list, alias="requiredNow")
    likely_later: List[DocumentItem] = Field(default_factory=list, alias="likelyLater")
    if_applicable: List[DocumentItem] = Field(default_factory=list, alias="ifApplicable")


class PhaseUpdate(BaseModel):
    """Phase progression signal"""
    model_config = ConfigDict(populate_by_name=True)
    
    phase_id: str = Field(..., alias="phaseId")
    reason: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Parser Result Container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ParsedOutput:
    """Container for all parsed XML-tagged content"""
    # Extracted content
    intent_analysis: Optional[IntentAnalysis] = None
    loan_snapshot: Optional[LoanSnapshot] = None
    loan_recommendations: Optional[List[LoanRecommendation]] = None
    loan_application: Optional[LoanApplication] = None
    documents_checklist: Optional[DocumentsChecklist] = None
    phase_update: Optional[PhaseUpdate] = None
    
    # Metadata
    raw_response: str = ""
    clean_response: str = ""  # Response with XML tags removed
    parse_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def has_errors(self) -> bool:
        return len(self.parse_errors) > 0
    
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    def get_all_tags_found(self) -> List[str]:
        """Return list of tag types that were successfully parsed"""
        tags = []
        if self.intent_analysis:
            tags.append("intent_analysis")
        if self.loan_snapshot:
            tags.append("loan_snapshot")
        if self.loan_recommendations:
            tags.append("loan_recommendations")
        if self.loan_application:
            tags.append("loan_application")
        if self.documents_checklist:
            tags.append("documents_checklist")
        if self.phase_update:
            tags.append("phase_update")
        return tags


# ─────────────────────────────────────────────────────────────────────────────
# XML Tag Parser
# ─────────────────────────────────────────────────────────────────────────────

T = TypeVar('T', bound=BaseModel)


class XMLTagParser:
    """
    Extracts and validates XML-tagged JSON blocks from LLM responses.
    
    Supported tags:
    - <intent_analysis>...</intent_analysis>
    - <loan_snapshot>...</loan_snapshot>
    - <loan_recommendations>...</loan_recommendations>
    - <loan_application>...</loan_application>
    - <documents_checklist>...</documents_checklist>
    - <phase_update>...</phase_update>
    
    Usage:
        parser = XMLTagParser()
        result = parser.parse(llm_response)
        
        if result.intent_analysis:
            print(f"Purpose: {result.intent_analysis.purpose}")
        
        if result.parse_errors:
            logger.error(f"Parse errors: {result.parse_errors}")
    """
    
    # Tag patterns - order matters (recommendations before snapshot for proper matching)
    TAGS = [
        "intent_analysis",
        "loan_recommendations",
        "loan_snapshot",
        "loan_application",
        "documents_checklist",
        "phase_update",
    ]
    
    # Pydantic model mapping
    TAG_MODELS: Dict[str, Type[BaseModel]] = {
        "intent_analysis": IntentAnalysis,
        "loan_snapshot": LoanSnapshot,
        "loan_recommendations": list,  # Special case: array of LoanRecommendation
        "loan_application": LoanApplication,
        "documents_checklist": DocumentsChecklist,
        "phase_update": PhaseUpdate,
    }
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize parser.
        
        Args:
            strict_mode: If True, raise exceptions on parse failures.
                        If False, collect errors and continue.
        """
        self.strict_mode = strict_mode
    
    def parse(self, response: str) -> ParsedOutput:
        """
        Parse LLM response and extract all XML-tagged content.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            ParsedOutput with extracted and validated content
        """
        result = ParsedOutput(raw_response=response)
        
        # Extract and parse each tag type
        for tag in self.TAGS:
            try:
                extracted = self._extract_tag_content(response, tag)
                if extracted:
                    validated = self._validate_content(extracted, tag)
                    self._set_result(result, tag, validated)
            except Exception as e:
                error_msg = f"Failed to parse <{tag}>: {str(e)}"
                if self.strict_mode:
                    raise
                result.parse_errors.append(error_msg)
        
        # Generate clean response (remove all XML tags)
        result.clean_response = self._remove_xml_tags(response)
        
        return result
    
    def _extract_tag_content(self, text: str, tag: str) -> Optional[str]:
        """
        Extract content between XML tags.
        
        Args:
            text: Full response text
            tag: Tag name to extract (e.g., "intent_analysis")
            
        Returns:
            Content between tags, or None if not found
        """
        pattern = rf"<{tag}>([\s\S]*?)</{tag}>"
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        return None
    
    def _validate_content(self, content: str, tag: str) -> Any:
        """
        Validate and parse extracted content.
        
        Args:
            content: Raw content between XML tags
            tag: Tag type for model selection
            
        Returns:
            Validated Pydantic model or dict
            
        Raises:
            ValidationError: If content doesn't match schema
            json.JSONDecodeError: If content is not valid JSON
        """
        # Normalize JSON-like text
        normalized = self._normalize_json(content)
        
        # Parse JSON
        data = json.loads(normalized)
        
        # Get appropriate model
        model = self.TAG_MODELS.get(tag)
        if not model:
            raise ValueError(f"Unknown tag type: {tag}")
        
        # Special handling for loan_recommendations (array)
        if tag == "loan_recommendations":
            if not isinstance(data, list):
                raise ValidationError.from_exception_data(
                    "loan_recommendations",
                    [{"type": "list_type", "loc": ("root",), "msg": "Expected array"}]
                )
            return [LoanRecommendation(**item) for item in data]
        
        # Validate against Pydantic model
        return model(**data)
    
    def _normalize_json(self, text: str) -> str:
        """
        Normalize JSON-like text to valid JSON.
        
        Handles common LLM output issues:
        - Markdown code blocks (```json ... ```)
        - Curly quotes (" " ' ')
        - Trailing commas
        - Unquoted keys
        
        Args:
            text: Raw JSON-like text
            
        Returns:
            Valid JSON string
        """
        s = text.strip()
        
        # Remove markdown code blocks
        s = re.sub(r"```json\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"```\s*$", "", s)
        
        # Replace curly quotes with straight quotes
        curly_to_straight = {
            '"': '"',
            '"': '"',
            "'": "'",
            "'": "'",
            "‚": "'",
            "‛": "'",
        }
        for curly, straight in curly_to_straight.items():
            s = s.replace(curly, straight)
        
        # Remove trailing commas before } or ]
        s = re.sub(r",\s*}", "}", s)
        s = re.sub(r",\s*]", "]", s)
        
        # Quote unquoted keys (simple heuristic)
        # Matches: {key: or , key:
        s = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', s)
        
        # Handle multi-line strings (convert to single line)
        # This is a simplification - real implementation might need more sophistication
        lines = s.split('\n')
        s = ' '.join(line.strip() for line in lines if line.strip())
        
        return s
    
    def _set_result(self, result: ParsedOutput, tag: str, value: Any):
        """Set parsed value on result object"""
        if tag == "intent_analysis":
            result.intent_analysis = value
        elif tag == "loan_snapshot":
            result.loan_snapshot = value
        elif tag == "loan_recommendations":
            result.loan_recommendations = value
        elif tag == "loan_application":
            result.loan_application = value
        elif tag == "documents_checklist":
            result.documents_checklist = value
        elif tag == "phase_update":
            result.phase_update = value
    
    def _remove_xml_tags(self, text: str) -> str:
        """Remove all XML tags from text"""
        clean = text
        for tag in self.TAGS:
            pattern = rf"<{tag}>[\s\S]*?</{tag}>"
            clean = re.sub(pattern, "", clean, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        clean = re.sub(r"\n\s*\n", "\n", clean)
        return clean.strip()
    
    def parse_single(self, response: str, tag: str) -> Optional[Any]:
        """
        Parse a single tag type from response.
        
        Args:
            response: LLM response text
            tag: Specific tag to extract
            
        Returns:
            Validated content or None
        """
        content = self._extract_tag_content(response, tag)
        if not content:
            return None
        
        try:
            return self._validate_content(content, tag)
        except Exception:
            if self.strict_mode:
                raise
            return None
    
    def extract_all_tags(self, response: str) -> Dict[str, Any]:
        """
        Extract all tags as raw dictionaries (skip validation).
        
        Useful for debugging or when you want raw data.
        
        Args:
            response: LLM response text
            
        Returns:
            Dict mapping tag names to raw JSON dicts
        """
        extracted = {}
        
        for tag in self.TAGS:
            content = self._extract_tag_content(response, tag)
            if content:
                try:
                    normalized = self._normalize_json(content)
                    data = json.loads(normalized)
                    extracted[tag] = data
                except Exception:
                    extracted[tag] = {"_raw": content, "_error": "Invalid JSON"}
        
        return extracted


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────────────────────

def parse_llm_response(response: str, strict: bool = False) -> ParsedOutput:
    """
    Convenience function to parse LLM response.
    
    Args:
        response: Raw LLM response text
        strict: If True, raise on errors. If False, collect errors.
        
    Returns:
        ParsedOutput with extracted content
    """
    parser = XMLTagParser(strict_mode=strict)
    return parser.parse(response)


def extract_intent(response: str) -> Optional[IntentAnalysis]:
    """Extract only intent analysis from response"""
    parser = XMLTagParser()
    return parser.parse_single(response, "intent_analysis")


def extract_loan_snapshot(response: str) -> Optional[LoanSnapshot]:
    """Extract only loan snapshot from response"""
    parser = XMLTagParser()
    return parser.parse_single(response, "loan_snapshot")


def extract_recommendations(response: str) -> Optional[List[LoanRecommendation]]:
    """Extract only loan recommendations from response"""
    parser = XMLTagParser()
    return parser.parse_single(response, "loan_recommendations")


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Parser class
    "XMLTagParser",
    
    # Result container
    "ParsedOutput",
    
    # Pydantic models
    "IntentAnalysis",
    "LoanSnapshot",
    "LoanRecommendation",
    "LoanApplication",
    "DocumentsChecklist",
    "DocumentItem",
    "PhaseUpdate",
    
    # Convenience functions
    "parse_llm_response",
    "extract_intent",
    "extract_loan_snapshot",
    "extract_recommendations",
]
