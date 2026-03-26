"""
Tools package for agentic orchestrator.

This package contains LangChain tools for the agentic workflow.
"""

# Initialize __all__
__all__ = []

# Re-export old tools for backward compatibility
import sys
import os

# Import from parent tools.py for backward compatibility
try:
    from ..tools import GenerateProfileTool
    __all__.append("GenerateProfileTool")
except (ImportError, AttributeError):
    # tools.py might not exist or might not have GenerateProfileTool
    pass

# Import new tools
from .intent_extractor import IntentExtractorTool
from .document_requirements import DocumentRequirementsTool

__all__.extend([
    "IntentExtractorTool",
    "DocumentRequirementsTool",
])
