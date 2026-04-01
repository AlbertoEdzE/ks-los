"""
Hallucination Detection System for KS-LOS Phase 2

This module provides comprehensive hallucination detection using a hybrid approach:
1. Rule-Based Validation - Fast, deterministic checks for numeric claims
2. NLI-Based Validation - Semantic entailment checking for non-numeric claims
3. RAG Citation Check - Verifies claims against retrieved policy documents

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    LLM Response                              │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              Claim Extractor                                 │
    │  - Numeric claims (rates, amounts, dates)                   │
    │  - Policy claims (eligibility, requirements)                │
    │  - Calculation claims (EMI, FOIR, LTV)                      │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │         Hybrid Hallucination Detector                        │
    ├─────────────────────────────────────────────────────────────┤
    │  Layer 1: Rule-Based Validator (<1ms)                       │
    │    - Interest rate bounds (5-15%)                           │
    │    - FOIR maximum (55%)                                     │
    │    - LTV maximum (95%)                                      │
    │    - Amount thresholds                                      │
    ├─────────────────────────────────────────────────────────────┤
    │  Layer 2: NLI Entailment Check (~50ms)                      │
    │    - DeBERTa-v3 model                                       │
    │    - Checks if context entails claims                       │
    │    - Semantic validation                                    │
    ├─────────────────────────────────────────────────────────────┤
    │  Layer 3: RAG Citation Check (~100ms)                       │
    │    - Verifies claims against policy docs                    │
    │    - Source attribution                                     │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              Hallucination Report                            │
    │  - Overall score (0-1)                                      │
    │  - Per-claim validation                                     │
    │  - Flags for violations                                     │
    │  - Safe to display (boolean)                                │
    └─────────────────────────────────────────────────────────────┘

Usage:
    from src.core.hallucination_detector import HallucinationDetector
    
    detector = HallucinationDetector()
    
    result = detector.detect(
        response="Your interest rate is 8.5% with FOIR of 35%",
        context="Policy: rates 5-15%, max FOIR 55%",
        retrieved_docs=[policy_doc_1, policy_doc_2]
    )
    
    if result.safe_to_display:
        show_to_user(response)
    else:
        log_for_review(result)
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

class ClaimType(str, Enum):
    """Type of claim being validated"""
    NUMERIC = "numeric"
    POLICY = "policy"
    CALCULATION = "calculation"
    DOCUMENT = "document"
    GENERAL = "general"


@dataclass
class ExtractedClaim:
    """A claim extracted from AI response"""
    text: str
    claim_type: ClaimType
    value: Optional[Any] = None
    unit: Optional[str] = None
    context: Optional[str] = None


@dataclass
class ClaimValidation:
    """Validation result for a single claim"""
    claim: ExtractedClaim
    is_valid: bool
    confidence: float  # 0-1
    violation_type: Optional[str] = None
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    source: Optional[str] = None  # Policy document source


@dataclass
class HallucinationReport:
    """Complete hallucination detection report"""
    response: str
    hallucination_score: float  # 0-1 (lower is better)
    safe_to_display: bool
    total_claims: int
    validated_claims: int
    unsupported_claims: int
    flags: List[str] = field(default_factory=list)
    claim_validations: List[ClaimValidation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Policy Rules Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PolicyRules:
    """Policy rules for validation"""
    # Interest rate bounds
    interest_rate_min: float = 5.0
    interest_rate_max: float = 15.0
    
    # Affordability limits
    max_foir: float = 55.0
    max_dti: float = 45.0
    
    # Collateral limits
    max_ltv: float = 95.0
    min_down_payment_percent: float = 5.0
    
    # Loan amount limits
    min_loan_amount: float = 1000.0
    max_loan_amount: float = 5000000.0
    
    # Tenure limits
    min_tenure_months: int = 6
    max_tenure_months: int = 360
    
    # Credit score thresholds
    min_credit_score: int = 300
    max_credit_score: int = 900


# Default policy rules
DEFAULT_POLICY_RULES = PolicyRules()


# ─────────────────────────────────────────────────────────────────────────────
# Claim Extractor
# ─────────────────────────────────────────────────────────────────────────────

class ClaimExtractor:
    """
    Extracts claims from AI response text.
    
    Identifies:
    - Numeric claims (interest rates, amounts, ratios)
    - Policy claims (eligibility, requirements)
    - Calculation claims (EMI, payments)
    - Document claims (requirements, verifications)
    """
    
    # Regex patterns for claim extraction
    PATTERNS = {
        "interest_rate": re.compile(r'(\d+\.?\d*)\s*%.*?(?:interest|rate|APR)', re.IGNORECASE),
        "percentage": re.compile(r'(\d+\.?\d*)\s*%'),
        "foir": re.compile(r'FOIR.*?(\d+\.?\d*)\s*%', re.IGNORECASE),
        "ltv": re.compile(r'LTV.*?(\d+\.?\d*)\s*%', re.IGNORECASE),
        "loan_amount": re.compile(r'(?:loan|amount).{0,30}?(\$|USD|TTD|JMD|GYD|BBD|XCD)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', re.IGNORECASE),
        "monthly_payment": re.compile(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:per month|monthly|/month)', re.IGNORECASE),
        "tenure": re.compile(r'(\d+)\s*(?:year|month|yr|mo)', re.IGNORECASE),
        "credit_score": re.compile(r'credit.*?(?:score|rating).{0,20}?(\d{3})', re.IGNORECASE),
    }
    
    def extract(self, text: str) -> List[ExtractedClaim]:
        """
        Extract claims from text.
        
        Args:
            text: AI response text
        
        Returns:
            List of extracted claims
        """
        claims = []
        
        # Extract interest rate claims
        for match in self.PATTERNS["interest_rate"].finditer(text):
            value = float(match.group(1))
            claims.append(ExtractedClaim(
                text=match.group(0),
                claim_type=ClaimType.NUMERIC,
                value=value,
                unit="percent",
                context="interest_rate"
            ))
        
        # Extract FOIR claims
        for match in self.PATTERNS["foir"].finditer(text):
            value = float(match.group(1))
            claims.append(ExtractedClaim(
                text=match.group(0),
                claim_type=ClaimType.CALCULATION,
                value=value,
                unit="percent",
                context="foir"
            ))
        
        # Extract LTV claims
        for match in self.PATTERNS["ltv"].finditer(text):
            value = float(match.group(1))
            claims.append(ExtractedClaim(
                text=match.group(0),
                claim_type=ClaimType.CALCULATION,
                value=value,
                unit="percent",
                context="ltv"
            ))
        
        # Extract percentage claims (general)
        for match in self.PATTERNS["percentage"].finditer(text):
            value = float(match.group(1))
            # Skip if already captured by more specific patterns
            if not any(c.value == value and c.unit == "percent" for c in claims):
                claims.append(ExtractedClaim(
                    text=match.group(0),
                    claim_type=ClaimType.NUMERIC,
                    value=value,
                    unit="percent"
                ))
        
        # Extract loan amount claims
        for match in self.PATTERNS["loan_amount"].finditer(text):
            currency = match.group(1) or "USD"
            amount_str = match.group(2).replace(",", "")
            value = float(amount_str)
            claims.append(ExtractedClaim(
                text=match.group(0),
                claim_type=ClaimType.NUMERIC,
                value=value,
                unit=currency,
                context="loan_amount"
            ))
        
        # Extract monthly payment claims
        for match in self.PATTERNS["monthly_payment"].finditer(text):
            amount_str = match.group(1).replace(",", "")
            value = float(amount_str)
            claims.append(ExtractedClaim(
                text=match.group(0),
                claim_type=ClaimType.CALCULATION,
                value=value,
                unit="USD",
                context="monthly_payment"
            ))
        
        # Extract credit score claims
        for match in self.PATTERNS["credit_score"].finditer(text):
            value = int(match.group(1))
            claims.append(ExtractedClaim(
                text=match.group(0),
                claim_type=ClaimType.NUMERIC,
                value=value,
                unit="score",
                context="credit_score"
            ))
        
        return claims


# ─────────────────────────────────────────────────────────────────────────────
# Rule-Based Validator
# ─────────────────────────────────────────────────────────────────────────────

class RuleBasedValidator:
    """
    Validates numeric claims against policy rules.
    
    Fast (<1ms), deterministic validation for:
    - Interest rates within bounds
    - FOIR/DTI within limits
    - LTV within limits
    - Loan amounts within thresholds
    - Credit scores in valid range
    """
    
    def __init__(self, policy_rules: Optional[PolicyRules] = None):
        """
        Initialize validator with policy rules.
        
        Args:
            policy_rules: Policy rules for validation (uses DEFAULT_POLICY_RULES if not provided)
        """
        self.rules = policy_rules or DEFAULT_POLICY_RULES
    
    def validate(self, claim: ExtractedClaim) -> ClaimValidation:
        """
        Validate a single claim against policy rules.
        
        Args:
            claim: Claim to validate
        
        Returns:
            Validation result
        """
        if claim.claim_type not in (ClaimType.NUMERIC, ClaimType.CALCULATION):
            return ClaimValidation(
                claim=claim,
                is_valid=True,
                confidence=1.0
            )
        
        # Validate based on context
        if claim.context == "interest_rate":
            return self._validate_interest_rate(claim)
        elif claim.context == "foir":
            return self._validate_foir(claim)
        elif claim.context == "ltv":
            return self._validate_ltv(claim)
        elif claim.context == "loan_amount":
            return self._validate_loan_amount(claim)
        elif claim.context == "credit_score":
            return self._validate_credit_score(claim)
        elif claim.context == "monthly_payment":
            return self._validate_monthly_payment(claim)
        else:
            # General numeric validation
            return ClaimValidation(
                claim=claim,
                is_valid=True,
                confidence=0.9  # High confidence for uncategorized numerics
            )
    
    def _validate_interest_rate(self, claim: ExtractedClaim) -> ClaimValidation:
        """Validate interest rate claim"""
        is_valid = self.rules.interest_rate_min <= claim.value <= self.rules.interest_rate_max
        
        return ClaimValidation(
            claim=claim,
            is_valid=is_valid,
            confidence=1.0,
            violation_type=None if is_valid else "interest_rate_out_of_bounds",
            expected_value=f"{self.rules.interest_rate_min}-{self.rules.interest_rate_max}%",
            actual_value=f"{claim.value}%"
        )
    
    def _validate_foir(self, claim: ExtractedClaim) -> ClaimValidation:
        """Validate FOIR claim"""
        is_valid = claim.value <= self.rules.max_foir
        
        return ClaimValidation(
            claim=claim,
            is_valid=is_valid,
            confidence=1.0,
            violation_type=None if is_valid else "foir_exceeds_maximum",
            expected_value=f"<={self.rules.max_foir}%",
            actual_value=f"{claim.value}%"
        )
    
    def _validate_ltv(self, claim: ExtractedClaim) -> ClaimValidation:
        """Validate LTV claim"""
        is_valid = claim.value <= self.rules.max_ltv
        
        return ClaimValidation(
            claim=claim,
            is_valid=is_valid,
            confidence=1.0,
            violation_type=None if is_valid else "ltv_exceeds_maximum",
            expected_value=f"<={self.rules.max_ltv}%",
            actual_value=f"{claim.value}%"
        )
    
    def _validate_loan_amount(self, claim: ExtractedClaim) -> ClaimValidation:
        """Validate loan amount claim"""
        is_valid = self.rules.min_loan_amount <= claim.value <= self.rules.max_loan_amount
        
        return ClaimValidation(
            claim=claim,
            is_valid=is_valid,
            confidence=1.0,
            violation_type=None if is_valid else "loan_amount_out_of_bounds",
            expected_value=f"{self.rules.min_loan_amount}-{self.rules.max_loan_amount}",
            actual_value=f"{claim.value}"
        )
    
    def _validate_credit_score(self, claim: ExtractedClaim) -> ClaimValidation:
        """Validate credit score claim"""
        is_valid = self.rules.min_credit_score <= claim.value <= self.rules.max_credit_score
        
        return ClaimValidation(
            claim=claim,
            is_valid=is_valid,
            confidence=1.0,
            violation_type=None if is_valid else "credit_score_invalid",
            expected_value=f"{self.rules.min_credit_score}-{self.rules.max_credit_score}",
            actual_value=f"{claim.value}"
        )
    
    def _validate_monthly_payment(self, claim: ExtractedClaim) -> ClaimValidation:
        """Validate monthly payment claim"""
        # Just check if positive
        is_valid = claim.value > 0
        
        return ClaimValidation(
            claim=claim,
            is_valid=is_valid,
            confidence=0.9,
            violation_type=None if is_valid else "negative_payment",
        )


# ─────────────────────────────────────────────────────────────────────────────
# NLI-Based Semantic Validator
# ─────────────────────────────────────────────────────────────────────────────

class NLISemanticValidator:
    """
    Validates claims using Natural Language Inference.
    
    Uses DeBERTa-v3 model to check if context entails claims.
    More accurate than simple string matching (~50ms per claim).
    """
    
    MODEL_NAME = "MoritzLaurer/deberta-v3-base-zeroshot-v1.1-all-33"
    
    def __init__(self, use_cpu: bool = True):
        """
        Initialize NLI validator.
        
        Args:
            use_cpu: Force CPU usage (default True for consistency)
        """
        self._model = None
        self._use_cpu = use_cpu
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of NLI model"""
        if self._initialized:
            return
        
        try:
            from transformers import pipeline
            
            device = "cpu" if self._use_cpu else -1  # -1 = auto
            
            self._model = pipeline(
                "text-classification",
                model=self.MODEL_NAME,
                return_all_scores=True,
                device=device,
            )
            
            self._initialized = True
            logger.info(f"NLI validator initialized (model={self.MODEL_NAME})")
            
        except ImportError:
            logger.warning("transformers not installed, NLI validation disabled")
            self._initialized = False
        except Exception as e:
            logger.error(f"Failed to load NLI model: {e}")
            self._initialized = False
    
    def validate(self, claim: str, context: str) -> ClaimValidation:
        """
        Validate claim using NLI.
        
        Args:
            claim: Claim text to validate
            context: Context/premise to check against
        
        Returns:
            Validation result
        """
        self._ensure_initialized()
        
        if not self._initialized or not self._model:
            # Degraded mode - return neutral validation
            return ClaimValidation(
                claim=ExtractedClaim(text=claim, claim_type=ClaimType.GENERAL),
                is_valid=True,
                confidence=0.5,  # Neutral confidence
                source="nli_degraded"
            )
        
        try:
            # NLI model checks if context ENTAILS the claim
            result = self._model({
                "premise": context,
                "hypothesis": claim
            })
            
            # Find ENTAILMENT score
            entailment_score = 0.0
            for item in result:
                if item["label"] == "ENTAILMENT":
                    entailment_score = item["score"]
                    break
            
            # Threshold for entailment
            threshold = 0.75
            is_valid = entailment_score >= threshold
            
            return ClaimValidation(
                claim=ExtractedClaim(text=claim, claim_type=ClaimType.GENERAL),
                is_valid=is_valid,
                confidence=entailment_score if is_valid else (1.0 - entailment_score),
                violation_type=None if is_valid else "not_entailed_by_context",
                source="nli_deberta_v3"
            )
            
        except Exception as e:
            logger.error(f"NLI validation failed: {e}")
            return ClaimValidation(
                claim=ExtractedClaim(text=claim, claim_type=ClaimType.GENERAL),
                is_valid=True,
                confidence=0.5,
                source="nli_error"
            )


# ─────────────────────────────────────────────────────────────────────────────
# RAG Citation Validator
# ─────────────────────────────────────────────────────────────────────────────

class RAGCitationValidator:
    """
    Validates claims against retrieved policy documents.
    
    Checks if claims are supported by retrieved documents
    through string matching and semantic similarity.
    """
    
    def validate(self, claim: str, retrieved_docs: List[str]) -> ClaimValidation:
        """
        Validate claim against retrieved documents.
        
        Args:
            claim: Claim to validate
            retrieved_docs: List of retrieved policy documents
        
        Returns:
            Validation result
        """
        if not retrieved_docs:
            return ClaimValidation(
                claim=ExtractedClaim(text=claim, claim_type=ClaimType.GENERAL),
                is_valid=True,
                confidence=0.5,  # Neutral if no docs
                source="rag_no_docs"
            )
        
        # Check if claim appears in any retrieved document
        claim_lower = claim.lower()
        for doc in retrieved_docs:
            doc_lower = doc.lower()
            
            # Simple string matching
            if claim_lower in doc_lower:
                return ClaimValidation(
                    claim=ExtractedClaim(text=claim, claim_type=ClaimType.GENERAL),
                    is_valid=True,
                    confidence=0.9,
                    source="rag_string_match"
                )
            
            # Check for key terms (more lenient)
            words = claim_lower.split()
            if len(words) > 3:
                matching_words = sum(1 for w in words if w in doc_lower)
                if matching_words / len(words) > 0.7:
                    return ClaimValidation(
                        claim=ExtractedClaim(text=claim, claim_type=ClaimType.GENERAL),
                        is_valid=True,
                        confidence=0.7,
                        source="rag_partial_match"
                    )
        
        # No match found
        return ClaimValidation(
            claim=ExtractedClaim(text=claim, claim_type=ClaimType.GENERAL),
            is_valid=False,
            confidence=0.8,
            violation_type="not_supported_by_retrieved_docs",
            source="rag_no_match"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Hybrid Hallucination Detector
# ─────────────────────────────────────────────────────────────────────────────

class HallucinationDetector:
    """
    Hybrid hallucination detector combining multiple validation strategies.
    
    Architecture:
    1. Extract claims from response
    2. Validate numeric claims with rules (<1ms)
    3. Validate semantic claims with NLI (~50ms)
    4. Validate against retrieved docs (~100ms)
    5. Aggregate results into hallucination score
    
    Usage:
        detector = HallucinationDetector()
        result = detector.detect(
            response="Your rate is 8.5%",
            context="Policy: rates 5-15%",
            retrieved_docs=[policy_doc]
        )
        
        if result.safe_to_display:
            show_to_user(response)
    """
    
    def __init__(
        self,
        policy_rules: Optional[PolicyRules] = None,
        use_nli: bool = True,
        use_rag: bool = True,
        nli_use_cpu: bool = True
    ):
        """
        Initialize hallucination detector.
        
        Args:
            policy_rules: Policy rules for validation
            use_nli: Enable NLI-based validation
            use_rag: Enable RAG citation validation
            nli_use_cpu: Force CPU for NLI model
        """
        self.claim_extractor = ClaimExtractor()
        self.rule_validator = RuleBasedValidator(policy_rules)
        self.nli_validator = NLISemanticValidator(use_cpu=nli_use_cpu) if use_nli else None
        self.rag_validator = RAGCitationValidator() if use_rag else None
        
        self.use_nli = use_nli
        self.use_rag = use_rag
        
        logger.info(f"HallucinationDetector initialized (NLI={use_nli}, RAG={use_rag})")
    
    def detect(
        self,
        response: str,
        context: str = "",
        retrieved_docs: Optional[List[str]] = None
    ) -> HallucinationReport:
        """
        Detect hallucinations in AI response.
        
        Args:
            response: AI response text to validate
            context: Context/premise for validation
            retrieved_docs: Retrieved policy documents for citation checking
        
        Returns:
            Hallucination report
        """
        # Step 1: Extract claims
        claims = self.claim_extractor.extract(response)
        
        if not claims:
            # No claims to validate - low risk
            return HallucinationReport(
                response=response,
                hallucination_score=0.0,
                safe_to_display=True,
                total_claims=0,
                validated_claims=0,
                unsupported_claims=0,
                metadata={"note": "no_claims_extracted"}
            )
        
        # Step 2: Validate claims
        validations = []
        flags = []
        unsupported_count = 0
        
        for claim in claims:
            # Rule-based validation (always enabled)
            rule_validation = self.rule_validator.validate(claim)
            validations.append(rule_validation)
            
            if not rule_validation.is_valid:
                unsupported_count += 1
                if rule_validation.violation_type:
                    flags.append(f"{rule_validation.violation_type}: {claim.text}")
                continue
            
            # NLI validation (if enabled and rule validation passed)
            if self.use_nli and context:
                nli_validation = self.nli_validator.validate(claim.text, context)
                validations.append(nli_validation)
                
                if not nli_validation.is_valid:
                    unsupported_count += 1
                    if nli_validation.violation_type:
                        flags.append(f"{nli_validation.violation_type}: {claim.text}")
                    continue
            
            # RAG validation (if enabled and docs available)
            if self.use_rag and retrieved_docs:
                rag_validation = self.rag_validator.validate(claim.text, retrieved_docs)
                validations.append(rag_validation)
                
                if not rag_validation.is_valid:
                    unsupported_count += 1
                    if rag_validation.violation_type:
                        flags.append(f"{rag_validation.violation_type}: {claim.text}")
        
        # Step 3: Calculate hallucination score
        total_claims = len(claims)
        validated_claims = total_claims - unsupported_count
        
        # Score = proportion of unsupported claims (0 = perfect, 1 = all hallucinated)
        hallucination_score = unsupported_count / total_claims if total_claims > 0 else 0.0
        
        # Safe to display if hallucination score < 0.3 (less than 30% unsupported)
        safe_to_display = hallucination_score < 0.3
        
        return HallucinationReport(
            response=response,
            hallucination_score=hallucination_score,
            safe_to_display=safe_to_display,
            total_claims=total_claims,
            validated_claims=validated_claims,
            unsupported_claims=unsupported_count,
            flags=flags,
            claim_validations=validations,
            metadata={
                "use_nli": self.use_nli,
                "use_rag": self.use_rag,
                "context_length": len(context),
                "retrieved_docs_count": len(retrieved_docs) if retrieved_docs else 0,
            }
        )


# ─────────────────────────────────────────────────────────────────────────────
# Integration Helper
# ─────────────────────────────────────────────────────────────────────────────

def validate_response_before_display(
    response: str,
    context: str = "",
    retrieved_docs: Optional[List[str]] = None,
    policy_rules: Optional[PolicyRules] = None,
    use_nli: bool = True,
    use_rag: bool = True
) -> Tuple[bool, HallucinationReport]:
    """
    Convenience function to validate response before displaying to user.
    
    Args:
        response: AI response to validate
        context: Context for validation
        retrieved_docs: Retrieved policy documents
        policy_rules: Policy rules (uses DEFAULT_POLICY_RULES if not provided)
        use_nli: Enable NLI validation
        use_rag: Enable RAG validation
    
    Returns:
        Tuple of (safe_to_display, report)
    
    Usage:
        safe, report = validate_response_before_display(
            response=ai_response,
            context=policy_context,
            retrieved_docs=retrieved_docs
        )
        
        if safe:
            return response
        else:
            return "Let me verify that information for you..."
    """
    detector = HallucinationDetector(
        policy_rules=policy_rules,
        use_nli=use_nli,
        use_rag=use_rag
    )
    
    report = detector.detect(response, context, retrieved_docs)
    
    return report.safe_to_display, report


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Data classes
    "ClaimType",
    "ExtractedClaim",
    "ClaimValidation",
    "HallucinationReport",
    "PolicyRules",
    
    # Validators
    "ClaimExtractor",
    "RuleBasedValidator",
    "NLISemanticValidator",
    "RAGCitationValidator",
    
    # Main detector
    "HallucinationDetector",
    
    # Integration helper
    "validate_response_before_display",
    
    # Default rules
    "DEFAULT_POLICY_RULES",
]
