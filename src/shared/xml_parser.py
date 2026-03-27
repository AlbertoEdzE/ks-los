"""
XML Tag Parser for LLM Responses

Parses XML-tagged JSON from LLM responses and extracts structured data.

Example LLM response:
```
That's wonderful! A home purchase is a major milestone.

<intent_analysis>
{"purpose": "home_purchase", "urgency": "medium"}
</intent_analysis>
```

This module extracts:
- chat_text: "That's wonderful! A home purchase is a major milestone."
- intent: {"purpose": "home_purchase", "urgency": "medium"}
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


# XML tag patterns
XML_PATTERNS = {
    "intent_analysis": r"<intent_analysis>\s*([\s\S]*?)\s*</intent_analysis>",
    "loan_snapshot": r"<loan_snapshot>\s*([\s\S]*?)\s*</loan_snapshot>",
    "loan_recommendations": r"<loan_recommendations>\s*([\s\S]*?)\s*</loan_recommendations>",
    "documents_checklist": r"<documents_checklist>\s*([\s\S]*?)\s*</documents_checklist>",
    "loan_application": r"<loan_application>\s*([\s\S]*?)\s*</loan_application>",
    "stp_processing": r"<stp_processing>\s*([\s\S]*?)\s*</stp_processing>",
    "terms_acceptance": r"<terms_acceptance>\s*([\s\S]*?)\s*</terms_acceptance>",
    "phase_update": r"<phase_update>\s*([\s\S]*?)\s*</phase_update>",
}


def extract_xml_tag(content: str, tag_name: str) -> Optional[str]:
    """
    Extract JSON content from XML tag.
    
    Args:
        content: Full LLM response text
        tag_name: Name of XML tag to extract
        
    Returns:
        JSON string content or None if not found
    """
    pattern = XML_PATTERNS.get(tag_name)
    if not pattern:
        logger.warning(f"Unknown XML tag: {tag_name}")
        return None
    
    match = re.search(pattern, content)
    if match:
        return match.group(1).strip()
    return None


def parse_json_safely(json_str: str, tag_name: str) -> Optional[Dict[str, Any]]:
    """
    Parse JSON string with error handling.
    
    Args:
        json_str: JSON string to parse
        tag_name: Tag name for error reporting
        
    Returns:
        Parsed dict or None if parsing fails
    """
    try:
        # Clean up common JSON formatting issues
        cleaned = json_str.strip()
        
        # Try to parse
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from {tag_name}: {e}")
        logger.debug(f"JSON string was: {json_str[:200]}...")
        return None


def strip_xml_tags(content: str) -> str:
    """
    Remove all XML tags, their content, and inline JSON objects from text.
    
    Args:
        content: Text with XML tags and potentially inline JSON
        
    Returns:
        Clean text with XML tags and inline JSON removed
    """
    cleaned = content
    
    # Remove all known XML tags with their content
    for pattern in XML_PATTERNS.values():
        cleaned = re.sub(pattern, "", cleaned)
    
    # Remove any remaining XML tags
    cleaned = re.sub(r"</?[a-z][a-z0-9_-]*[^>]*\s*/?>", "", cleaned)
    
    # Remove inline JSON objects (standalone {...} or {...} at end of sentences)
    # This pattern matches JSON-like objects that appear on their own
    cleaned = re.sub(r'\s*\{\s*"[^"]+"\s*:\s*"[^"]+"\s*\}\s*', ' ', cleaned)
    cleaned = re.sub(r'\s*\{\s*"[^"]+"\s*:\s*\[[^\]]*\]\s*\}\s*', ' ', cleaned)
    
    # Clean up whitespace
    cleaned = re.sub(r"\n\s*\n", "\n", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    
    return cleaned.strip()


def parse_llm_response(content: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parse LLM response with XML-tagged structured data.
    
    Args:
        content: Full LLM response text
        
    Returns:
        Tuple of (clean_text, metadata_dict)
        - clean_text: Text with XML tags removed for display
        - metadata_dict: Parsed JSON from all XML tags
    """
    metadata = {}
    
    # Extract each XML tag
    for tag_name in XML_PATTERNS.keys():
        json_str = extract_xml_tag(content, tag_name)
        if json_str:
            parsed = parse_json_safely(json_str, tag_name)
            if parsed:
                # Convert snake_case tag to camelCase metadata key
                metadata_key = tag_name.replace("_", "")
                if tag_name == "intent_analysis":
                    metadata_key = "intentAnalysis"
                elif tag_name == "loan_snapshot":
                    metadata_key = "loanSnapshot"
                elif tag_name == "loan_recommendations":
                    metadata_key = "loanRecommendations"
                elif tag_name == "documents_checklist":
                    metadata_key = "documentsChecklist"
                elif tag_name == "loan_application":
                    metadata_key = "loanApplication"
                elif tag_name == "stp_processing":
                    metadata_key = "stpProcessing"
                elif tag_name == "terms_acceptance":
                    metadata_key = "termsAcceptance"
                elif tag_name == "phase_update":
                    metadata_key = "phaseUpdate"
                
                metadata[metadata_key] = parsed
    
    # Special handling for intent_analysis to match frontend expectations
    if "intentAnalysis" in metadata:
        intent = metadata["intentAnalysis"]
        # Frontend expects intentSummary inside intentAnalysis
        if isinstance(intent, dict):
            metadata["intentAnalysis"] = {
                "intentSummary": intent
            }
    
    # Strip XML tags from content
    clean_text = strip_xml_tags(content)
    
    return clean_text, metadata


def parse_metadata_from_content(content: str) -> Dict[str, Any]:
    """
    Extract only metadata from LLM response.
    
    Args:
        content: Full LLM response text
        
    Returns:
        Metadata dict with parsed XML tag contents
    """
    _, metadata = parse_llm_response(content)
    return metadata


# Example usage
if __name__ == "__main__":
    # Test parsing
    test_content = """
    That's wonderful! A home purchase is a major milestone.
    
    <intent_analysis>
    {"purpose": "home_purchase", "urgency": "medium"}
    </intent_analysis>
    
    <loan_snapshot>
    {"loan_amount": 350000, "interest_rate": 8.5}
    </loan_snapshot>
    """
    
    clean_text, metadata = parse_llm_response(test_content)
    
    print("Clean text:", clean_text)
    print("Metadata:", json.dumps(metadata, indent=2))
