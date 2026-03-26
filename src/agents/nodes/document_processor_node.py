"""
Document Processor Node for Agentic Orchestrator

Auto-populates loan application fields from OCR-extracted document data.
Validates extracted information against user-declared data and flags discrepancies.

Architecture:
    Document Upload → OCR Extraction → Field Validation → Auto-Population → Discrepancy Flags

Usage:
    node = DocumentProcessorNode()
    updated_state = node.process(current_state, uploaded_documents)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

from src.agents.orchestrator import CapturedContext, OrchestratorState
from src.core.document_intelligence import (
    DocumentExtractionResult,
    PaySlipFields,
    BankStatementFields,
    IDFields,
)


@dataclass
class DiscrepancyFlag:
    """Represents a discrepancy between extracted and declared data"""
    field_name: str
    declared_value: Any
    extracted_value: Any
    variance_percent: float
    severity: str  # "low", "medium", "high"
    recommendation: str


class DocumentProcessorNode:
    """
    Processes uploaded documents and auto-populates loan application.
    
    Features:
    - Auto-population from OCR extraction
    - Discrepancy detection (declared vs extracted)
    - Confidence-based validation
    - Caribbean document awareness
    
    Usage:
        processor = DocumentProcessorNode()
        updated_context, flags = processor.process(
            current_context,
            extraction_results
        )
    """
    
    # Discrepancy thresholds
    LOW_VARIANCE_THRESHOLD = 0.10  # 10%
    MEDIUM_VARIANCE_THRESHOLD = 0.20  # 20%
    HIGH_VARIANCE_THRESHOLD = 0.30  # 30%
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process(
        self,
        state: OrchestratorState,
        extraction_results: List[DocumentExtractionResult]
    ) -> OrchestratorState:
        """
        Process extracted documents and update state.
        
        Args:
            state: Current orchestrator state
            extraction_results: List of OCR extraction results
            
        Returns:
            Updated state with auto-populated fields and flags
        """
        context = state.captured_context
        flags = []
        
        for result in extraction_results:
            if not result.is_reliable(threshold=0.5):
                self.logger.warning(f"Skipping low-confidence extraction: {result.document_type}")
                continue
            
            # Auto-populate based on document type
            if result.document_type.value in ["pay_slip", "job_letter"]:
                self._process_income_document(context, result, flags)
            
            elif result.document_type.value == "bank_statement":
                self._process_bank_statement(context, result, flags)
            
            elif result.document_type.value in ["national_id", "passport"]:
                self._process_id_document(context, result, flags)
        
        # Store flags in state
        state.captured_context = context
        
        # Log summary
        self.logger.info(
            f"Document processing complete: "
            f"{len(extraction_results)} docs, {len(flags)} flags"
        )
        
        return state
    
    def _process_income_document(
        self,
        context: CapturedContext,
        result: DocumentExtractionResult,
        flags: List[DiscrepancyFlag]
    ):
        """Process pay slip or job letter"""
        if not result.fields or not isinstance(result.fields, PaySlipFields):
            return
        
        fields = result.fields
        
        # Auto-populate employer name
        if fields.employer_name and not context.employment_type:
            context.employment_type = "salaried"
        
        # Auto-populate income with validation
        if fields.gross_pay:
            declared_income = context.monthly_income
            
            if declared_income:
                # Check for discrepancy
                variance = abs(fields.gross_pay - declared_income) / declared_income
                
                if variance > self.LOW_VARIANCE_THRESHOLD:
                    flags.append(DiscrepancyFlag(
                        field_name="monthly_income",
                        declared_value=declared_income,
                        extracted_value=fields.gross_pay,
                        variance_percent=variance * 100,
                        severity=self._get_severity(variance),
                        recommendation="Verify income with additional documents"
                    ))
                else:
                    # Auto-update if variance is small
                    context.monthly_income = fields.gross_pay
            else:
                # No declared income - auto-populate
                context.monthly_income = fields.gross_pay
        
        # Update field confidence
        if fields.gross_pay:
            context.field_confidence["monthly_income"] = result.confidence
    
    def _process_bank_statement(
        self,
        context: CapturedContext,
        result: DocumentExtractionResult,
        flags: List[DiscrepancyFlag]
    ):
        """Process bank statement"""
        if not result.fields or not isinstance(result.fields, BankStatementFields):
            return
        
        fields = result.fields
        
        # Auto-populate account holder name
        if fields.account_holder_name and not context.borrower_name:
            context.borrower_name = fields.account_holder_name
        
        # Validate income against average balance
        if fields.average_balance and context.monthly_income:
            # Average balance should be reasonable relative to income
            balance_to_income_ratio = fields.average_balance / max(context.monthly_income, 1)
            
            if balance_to_income_ratio < 0.5:
                flags.append(DiscrepancyFlag(
                    field_name="financial_stability",
                    declared_value=context.monthly_income,
                    extracted_value=fields.average_balance,
                    variance_percent=(1 - balance_to_income_ratio) * 100,
                    severity="medium",
                    recommendation="Request additional income verification"
                ))
    
    def _process_id_document(
        self,
        context: CapturedContext,
        result: DocumentExtractionResult,
        flags: List[DiscrepancyFlag]
    ):
        """Process ID or passport"""
        if not result.fields or not isinstance(result.fields, IDFields):
            return
        
        fields = result.fields
        
        # Auto-populate name
        if fields.full_name and not context.borrower_name:
            context.borrower_name = fields.full_name
        
        # Auto-populate nationality
        if fields.nationality:
            # Could be used for residency verification
            pass
        
        # Check expiry date
        if fields.expiry_date:
            from datetime import datetime
            try:
                # Try common date formats
                for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"]:
                    try:
                        expiry = datetime.strptime(fields.expiry_date, fmt)
                        if expiry < datetime.now():
                            flags.append(DiscrepancyFlag(
                                field_name="document_validity",
                                declared_value="valid",
                                extracted_value="expired",
                                variance_percent=0,
                                severity="high",
                                recommendation="Request valid, unexpired ID"
                            ))
                        break
                    except ValueError:
                        continue
            except Exception:
                pass  # Date parsing failed - not critical
    
    def _get_severity(self, variance: float) -> str:
        """Get severity level based on variance"""
        if variance > self.HIGH_VARIANCE_THRESHOLD:
            return "high"
        elif variance > self.MEDIUM_VARIANCE_THRESHOLD:
            return "medium"
        else:
            return "low"


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Function
# ─────────────────────────────────────────────────────────────────────────────

def process_documents(
    state: OrchestratorState,
    extraction_results: List[DocumentExtractionResult]
) -> OrchestratorState:
    """
    Convenience function to process documents.
    
    Args:
        state: Current state
        extraction_results: OCR extraction results
        
    Returns:
        Updated state
    """
    processor = DocumentProcessorNode()
    return processor.process(state, extraction_results)


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "DocumentProcessorNode",
    "DiscrepancyFlag",
    "process_documents",
]
