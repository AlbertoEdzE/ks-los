"""
Phase 2/3 Integration Tests - Simplified

Core integration tests for agentic components.
Uses real Caribbean document samples from data/ folder.
"""

import pytest
from datetime import datetime
from pathlib import Path

from src.agents.graph_state import (
    AgenticOrchestratorState,
    ConversationMode,
    create_initial_state,
)
from src.core.document_intelligence import DocumentIntelligence
from src.agents.graph_state import CapturedContext


DATA_DIR = Path(__file__).parent.parent.parent / "data"

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not OCR_AVAILABLE,
    reason="OCR libraries not installed"
)


class TestAgenticStateManagement:
    """Test agentic state management"""
    
    def test_state_creation(self):
        """Test state creation and initialization"""
        state = create_initial_state(session_id="test-001")
        
        assert state.session_id == "test-001"
        assert state.mode == ConversationMode.ADVISORY
        assert state.current_stage == "intent_capture"
        
        print(f"\nState Creation Test:")
        print(f"  Session ID: {state.session_id}")
        print(f"  Mode: {state.mode.value}")
    
    def test_mode_transitions(self):
        """Test mode transitions"""
        state = create_initial_state(session_id="test-002")
        
        # Advisory → Application
        state.captured_context.purpose = "home_purchase"
        state.captured_context.loan_amount = 400000.0
        state.captured_context.monthly_income = 8000.0
        state.captured_context.employment_type = "salaried"
        state.confidence_scores["purpose"] = 0.95
        state.confidence_scores["loan_amount"] = 0.9
        state.confidence_scores["monthly_income"] = 0.85
        state.confidence_scores["employment_type"] = 0.9
        
        assert state.can_proceed_to_application() is True
        
        state.mode = ConversationMode.APPLICATION
        
        # Application → Completion
        state.captured_context.email = "test@email.com"
        state.captured_context.phone = "+1-868-555-1234"
        state.application_submitted = True
        state.mode = ConversationMode.COMPLETION
        
        print(f"\nMode Transitions Test:")
        print(f"  Final Mode: {state.mode.value}")
        print(f"  Application Submitted: {state.application_submitted}")
    
    def test_confidence_tracking(self):
        """Test confidence score tracking"""
        state = create_initial_state(session_id="test-003")
        
        state.confidence_scores["purpose"] = 0.95
        state.confidence_scores["loan_amount"] = 0.85
        state.confidence_scores["monthly_income"] = 0.75
        
        assert state.get_confidence("purpose") == 0.95
        assert state.is_field_reliable("purpose", threshold=0.7) is True
        assert state.is_field_reliable("monthly_income", threshold=0.8) is False
        
        avg = state.get_average_confidence()
        assert 0.8 <= avg <= 0.9
        
        print(f"\nConfidence Tracking Test:")
        print(f"  Average Confidence: {avg:.2f}")


class TestDocumentIntelligenceIntegration:
    """Test document intelligence integration"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.doc_intelligence = DocumentIntelligence()
    
    def test_real_pay_slip_extraction(self):
        """Test real pay slip extraction"""
        pay_slip_path = DATA_DIR / "Salary-slipJan.jpg"
        
        if not pay_slip_path.exists():
            pytest.skip(f"Sample not found: {pay_slip_path}")
        
        result = self.doc_intelligence.process_image(str(pay_slip_path))
        
        assert result.document_type.value == "pay_slip"
        assert len(result.raw_text) > 50
        
        print(f"\nReal Pay Slip Test:")
        print(f"  Type: {result.document_type.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  OCR Quality: {result.ocr_quality:.2f}")
    
    def test_multiple_pay_slips_consistency(self):
        """Test multiple pay slips consistency"""
        pay_slip_paths = [
            DATA_DIR / "Salary-slipDec.jpg",
            DATA_DIR / "Salary-slipJan.jpg",
            DATA_DIR / "Salary-slipFeb.jpg",
        ]
        
        results = []
        for path in pay_slip_paths:
            if not path.exists():
                continue
            result = self.doc_intelligence.process_image(str(path))
            results.append(result)
        
        if len(results) < 2:
            pytest.skip("Need at least 2 samples")
        
        # All should be pay slips
        for i, result in enumerate(results):
            assert result.document_type.value == "pay_slip"
        
        print(f"\nMultiple Pay Slips Test:")
        print(f"  Processed: {len(results)} slips")
        print(f"  All pay_slip: {all(r.document_type.value == 'pay_slip' for r in results)}")
    
    def test_job_letter_extraction(self):
        """Test job letter extraction"""
        job_letter_path = DATA_DIR / "JobLetter.jpg"
        
        if not job_letter_path.exists():
            pytest.skip(f"Sample not found: {job_letter_path}")
        
        result = self.doc_intelligence.process_image(str(job_letter_path))
        
        assert result.document_type.value == "job_letter"
        assert len(result.raw_text) > 100
        
        print(f"\nJob Letter Test:")
        print(f"  Type: {result.document_type.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Text Length: {len(result.raw_text)} chars")


class TestEndToEndFlow:
    """Test end-to-end borrower journey"""
    
    def test_complete_flow_simulation(self):
        """Simulate complete borrower journey"""
        state = create_initial_state(session_id="e2e-001")
        
        # Step 1: Intent capture
        state.add_message("user", "I need a home loan")
        state.captured_context.purpose = "home_purchase"
        state.confidence_scores["purpose"] = 0.9
        
        # Step 2: Employment & income
        state.captured_context.employment_type = "salaried"
        state.captured_context.monthly_income = 8000.0
        state.confidence_scores["employment_type"] = 0.85
        state.confidence_scores["monthly_income"] = 0.8
        
        # Step 3: Loan amount
        state.captured_context.loan_amount = 400000.0
        state.confidence_scores["loan_amount"] = 0.9
        
        # Check can proceed to application
        assert state.can_proceed_to_application() is True
        
        # Step 4: Contact info
        state.captured_context.borrower_name = "Marcus Williams"
        state.captured_context.email = "marcus.w@email.com"
        state.captured_context.phone = "+1-868-555-1234"
        
        # Step 5: Submit application
        state.application_submitted = True
        state.mode = ConversationMode.COMPLETION
        
        print(f"\nEnd-to-End Flow Test:")
        print(f"  Purpose: {state.captured_context.purpose}")
        print(f"  Loan Amount: ${state.captured_context.loan_amount:,.2f}")
        print(f"  Income: ${state.captured_context.monthly_income:,.2f}")
        print(f"  Application Submitted: {state.application_submitted}")
        print(f"  Final Mode: {state.mode.value}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
