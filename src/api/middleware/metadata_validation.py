"""
Chat Metadata Validation Middleware.

This middleware validates all assistant response metadata against the
schema defined in chat_metadata.py. It ensures:

1. No hallucinated fields (extra='forbid' in schemas)
2. Type safety (all fields validated)
3. Required fields present
4. Backward compatibility (schema versioning)

Usage:
    from src.api.middleware.metadata_validation import validate_assistant_metadata
    
    metadata = validate_assistant_metadata(raw_metadata)
"""

import logging
from typing import Any, Dict, Optional
from pydantic import ValidationError

from src.api.schemas.chat_metadata import (
    AssistantResponseMetadata,
    validate_metadata,
    metadata_to_dict,
    get_schema_info,
    SCHEMA_VERSION,
)

logger = logging.getLogger(__name__)


class MetadataValidationError(Exception):
    """Raised when metadata validation fails."""
    
    def __init__(self, message: str, errors: Optional[list] = None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)


def validate_assistant_metadata(
    raw_metadata: Optional[Dict[str, Any]],
    strict: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Validate assistant response metadata.
    
    Args:
        raw_metadata: Raw metadata dictionary from agent
        strict: If True, raise exception on validation failure.
                If False, return None and log warning.
                
    Returns:
        Validated metadata dictionary (normalized), or None if invalid
        
    Raises:
        MetadataValidationError: If strict=True and validation fails
        
    Side Effects:
        - Logs validation errors
        - Logs schema version for audit trail
    """
    if raw_metadata is None:
        logger.debug("[MetadataValidation] No metadata to validate")
        return None
    
    try:
        # Validate against schema
        validated = validate_metadata(raw_metadata)
        
        # Convert back to dict (normalized, with aliases)
        normalized = metadata_to_dict(validated)
        
        # Add schema version for audit trail
        normalized['_schema_version'] = SCHEMA_VERSION
        
        logger.info(
            f"[MetadataValidation] Validation successful: "
            f"intent={validated.intent_analysis is not None}, "
            f"recommendations={len(validated.loan_recommendations) if validated.loan_recommendations else 0}, "
            f"schema_version={SCHEMA_VERSION}"
        )
        
        return normalized
        
    except ValidationError as e:
        error_details = [
            {"field": ".".join(str(x) for x in error["loc"]), "message": error["msg"]}
            for error in e.errors()
        ]
        
        logger.warning(
            f"[MetadataValidation] Validation failed: {error_details}"
        )
        
        if strict:
            raise MetadataValidationError(
                f"Metadata validation failed: {error_details}",
                errors=error_details
            )
        
        return None


def validate_intent_analysis(
    intent_data: Optional[Dict[str, Any]],
    strict: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Validate intent analysis subset.
    
    Used for unit testing intent extraction without full metadata.
    
    Args:
        intent_data: Raw intent analysis dictionary
        strict: If True, raise exception on failure
        
    Returns:
        Validated intent analysis dictionary
        
    Raises:
        MetadataValidationError: If strict=True and validation fails
    """
    from src.api.schemas.chat_metadata import IntentAnalysis
    
    if intent_data is None:
        return None
    
    try:
        validated = IntentAnalysis.model_validate(intent_data)
        return validated.model_dump(by_alias=True, exclude_none=True)
    except ValidationError as e:
        logger.warning(f"[IntentValidation] Validation failed: {e.errors()}")
        
        if strict:
            raise MetadataValidationError(
                f"Intent validation failed: {e.errors()}",
                errors=e.errors()
            )
        
        return None


def validate_recommendations(
    recommendations: Optional[list],
    strict: bool = True
) -> Optional[list]:
    """
    Validate loan recommendations list.
    
    Args:
        recommendations: List of raw recommendation dictionaries
        strict: If True, raise exception on failure
        
    Returns:
        Validated recommendations list
        
    Raises:
        MetadataValidationError: If strict=True and validation fails
    """
    from src.api.schemas.chat_metadata import LoanRecommendation
    
    if not recommendations:
        return None
    
    validated_list = []
    errors = []
    
    for i, rec in enumerate(recommendations):
        try:
            validated = LoanRecommendation.model_validate(rec)
            validated_list.append(validated.model_dump(by_alias=True, exclude_none=True))
        except ValidationError as e:
            errors.append({"index": i, "errors": e.errors()})
            logger.warning(f"[RecommendationValidation] Item {i} failed: {e.errors()}")
    
    if errors and strict:
        raise MetadataValidationError(
            f"Recommendation validation failed for {len(errors)} items",
            errors=errors
        )
    
    return validated_list if validated_list else None


def get_validation_stats() -> Dict[str, Any]:
    """
    Get validation statistics for monitoring.
    
    Returns:
        Dictionary with validation stats
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "schema_info": get_schema_info(),
        "validation_rules": {
            "extra_fields": "forbidden",
            "type_checking": "strict",
            "required_fields": "enforced",
        },
    }


# =============================================================================
# FastAPI Dependency (for route-level validation)
# =============================================================================

async def validate_metadata_dependency(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    FastAPI dependency for route-level validation.
    
    Usage:
        @router.post("/api/conversations/{id}/messages")
        async def send_message(
            metadata: Dict = Depends(validate_metadata_dependency)
        ):
            # metadata is already validated
            pass
    """
    from fastapi import HTTPException
    
    try:
        validated = validate_assistant_metadata(metadata, strict=True)
        if validated is None:
            raise HTTPException(
                status_code=400,
                detail="Metadata validation failed: empty metadata"
            )
        return validated
    except MetadataValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Metadata validation failed",
                "errors": e.errors,
            }
        )
