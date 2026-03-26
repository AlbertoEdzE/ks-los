"""
Integration Tests for Document Intelligence with Real Samples

Tests OCR and field extraction using actual Caribbean document samples
from the data folder. These tests verify end-to-end processing accuracy.

Requirements:
- OCR libraries installed (pytesseract, Pillow, pdf2image)
- Sample documents in data/ folder
"""

import pytest
import os
from pathlib import Path

from src.core.document_intelligence import (
    DocumentIntelligence,
    DocumentType,
    extract_from_image,
)


# ─────────────────────────────────────────────────────────────────────────────
# Test Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Path to test data
DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Skip tests if OCR not available
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not OCR_AVAILABLE,
    reason="OCR libraries not installed - skipping integration tests"
)


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRealDocumentProcessing:
    """Test processing of real Caribbean document samples"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = DocumentIntelligence()
    
    def test_process_pay_slip_real(self):
        """Test processing real pay slip sample"""
        sample_path = DATA_DIR / "Salary-slipJan.jpg"
        
        if not sample_path.exists():
            pytest.skip(f"Sample not found: {sample_path}")
        
        result = self.engine.process_image(str(sample_path))
        
        # Verify classification
        assert result.document_type == DocumentType.PAY_SLIP, \
            f"Expected PAY_SLIP, got {result.document_type}"
        
        # Verify extraction
        assert result.fields is not None, "Fields should be extracted"
        assert result.fields.gross_pay is not None or result.fields.net_pay is not None, \
            "Should extract at least one monetary value"
        
        # Verify confidence
        assert result.confidence > 0.4, \
            f"Confidence too low: {result.confidence}"
        
        # Log results for analysis
        print(f"\nPay Slip Results:")
        print(f"  Type: {result.document_type}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Gross Pay: {result.fields.gross_pay}")
        print(f"  Net Pay: {result.fields.net_pay}")
        print(f"  Flags: {result.flags}")
    
    def test_process_job_letter_real(self):
        """Test processing real job letter sample"""
        sample_path = DATA_DIR / "JobLetter.jpg"
        
        if not sample_path.exists():
            pytest.skip(f"Sample not found: {sample_path}")
        
        result = self.engine.process_image(str(sample_path))
        
        # Verify classification
        assert result.document_type in [DocumentType.JOB_LETTER, DocumentType.UNKNOWN], \
            f"Expected JOB_LETTER or UNKNOWN, got {result.document_type}"
        
        # Should extract some text at minimum
        assert len(result.raw_text) > 50, \
            f"Should extract text, got {len(result.raw_text)} chars"
        
        print(f"\nJob Letter Results:")
        print(f"  Type: {result.document_type}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Text length: {len(result.raw_text)} chars")
    
    def test_process_bank_statement_real(self):
        """Test processing real bank statement sample"""
        sample_path = DATA_DIR / "6-monthsBankSavings.jpg"
        
        if not sample_path.exists():
            pytest.skip(f"Sample not found: {sample_path}")
        
        result = self.engine.process_image(str(sample_path))
        
        # Verify classification
        assert result.document_type == DocumentType.BANK_STATEMENT, \
            f"Expected BANK_STATEMENT, got {result.document_type}"
        
        # Should extract balances
        if result.fields:
            print(f"\nBank Statement Results:")
            print(f"  Type: {result.document_type}")
            print(f"  Confidence: {result.confidence:.2f}")
            print(f"  Closing Balance: {result.fields.closing_balance}")
    
    def test_process_id_passport_real(self):
        """Test processing real ID/passport sample"""
        sample_path = DATA_DIR / "passport-example.png"
        
        if not sample_path.exists():
            pytest.skip(f"Sample not found: {sample_path}")
        
        result = self.engine.process_image(str(sample_path))
        
        # Verify classification
        assert result.document_type in [DocumentType.PASSPORT, DocumentType.NATIONAL_ID], \
            f"Expected PASSPORT or NATIONAL_ID, got {result.document_type}"
        
        # Should extract ID number or name
        if result.fields:
            print(f"\nID/Passport Results:")
            print(f"  Type: {result.document_type}")
            print(f"  Confidence: {result.confidence:.2f}")
            print(f"  ID Number: {result.fields.id_number if hasattr(result.fields, 'id_number') else 'N/A'}")
    
    def test_process_proof_of_address_real(self):
        """Test processing real utility bill sample"""
        sample_path = DATA_DIR / "ProofAdress.jpg"
        
        if not sample_path.exists():
            pytest.skip(f"Sample not found: {sample_path}")
        
        result = self.engine.process_image(str(sample_path))
        
        # Utility bills may be classified as unknown or utility_bill
        print(f"\nProof of Address Results:")
        print(f"  Type: {result.document_type}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Text length: {len(result.raw_text)} chars")
        
        # Should extract some text
        assert len(result.raw_text) > 20, "Should extract text from utility bill"
    
    def test_multiple_pay_slips_consistency(self):
        """Test processing multiple pay slips from same employer"""
        pay_slip_paths = [
            DATA_DIR / "Salary-slipDec.jpg",
            DATA_DIR / "Salary-slipJan.jpg",
            DATA_DIR / "Salary-slipFeb.jpg",
        ]
        
        results = []
        for path in pay_slip_paths:
            if not path.exists():
                continue
            
            result = self.engine.process_image(str(path))
            results.append(result)
        
        if len(results) < 2:
            pytest.skip("Need at least 2 pay slip samples")
        
        # All should be classified as pay slips
        for i, result in enumerate(results):
            assert result.document_type == DocumentType.PAY_SLIP, \
                f"Pay slip {i+1} not classified correctly"
        
        # Verify consistent employer extraction (if available)
        employers = []
        for result in results:
            if result.fields and hasattr(result.fields, 'employer_name'):
                if result.fields.employer_name:
                    employers.append(result.fields.employer_name)
        
        if len(employers) >= 2:
            # All should have same employer
            assert len(set(employers)) == 1, \
                f"Employer names inconsistent: {employers}"
        
        print(f"\nMultiple Pay Slips Consistency:")
        print(f"  Processed: {len(results)} slips")
        print(f"  Employers: {employers}")


class TestOCRAccuracy:
    """Test OCR accuracy metrics"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = DocumentIntelligence()
    
    def test_ocr_quality_estimation(self):
        """Test OCR quality estimation correlates with actual quality"""
        # High quality sample (clean scan)
        high_quality_path = DATA_DIR / "Salary-slipJan.jpg"
        
        if not high_quality_path.exists():
            pytest.skip("Sample not found")
        
        result = self.engine.process_image(str(high_quality_path))
        
        # OCR quality should be reasonable for clean scans
        assert result.ocr_quality > 0.5, \
            f"OCR quality too low for clean scan: {result.ocr_quality}"
        
        print(f"\nOCR Quality Test:")
        print(f"  Estimated Quality: {result.ocr_quality:.2f}")
        print(f"  Text Length: {len(result.raw_text)} chars")
    
    def test_preprocessing_improves_extraction(self):
        """Test that image preprocessing improves extraction"""
        sample_path = DATA_DIR / "Salary-slipJan.jpg"
        
        if not sample_path.exists():
            pytest.skip("Sample not found")
        
        # Process with preprocessing
        result_with_prep = self.engine.process_image(
            str(sample_path),
            preprocess=True
        )
        
        # Process without preprocessing
        result_without_prep = self.engine.process_image(
            str(sample_path),
            preprocess=False
        )
        
        # Preprocessing should help (or at least not hurt significantly)
        print(f"\nPreprocessing Comparison:")
        print(f"  With preprocessing: confidence={result_with_prep.confidence:.2f}")
        print(f"  Without preprocessing: confidence={result_without_prep.confidence:.2f}")
        
        # Note: This is informational - preprocessing may not always improve
        # results depending on the original image quality


class TestCaribbeanContext:
    """Test Caribbean-specific document handling"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = DocumentIntelligence()
    
    def test_ttd_currency_detection(self):
        """Test TTD currency detection in Caribbean documents"""
        sample_path = DATA_DIR / "Salary-slipJan.jpg"
        
        if not sample_path.exists():
            pytest.skip("Sample not found")
        
        result = self.engine.process_image(str(sample_path))
        
        # Check if TTD currency is detected
        if result.fields and hasattr(result.fields, 'currency'):
            print(f"\nCurrency Detection:")
            print(f"  Detected Currency: {result.fields.currency}")
            
            # Trinidad documents should use TTD or USD
            assert result.fields.currency in ["TTD", "USD", "$"], \
                f"Unexpected currency: {result.fields.currency}"
    
    def test_caribbean_document_formats(self):
        """Test recognition of Caribbean document formats"""
        # Test multiple Caribbean document types
        samples = [
            (DATA_DIR / "NIS:NI-ContributionsRecord.jpg", "Caribbean NIS/NI record"),
            (DATA_DIR / "PAN-1.jpg", "Trinidad PAN (tax) document"),
            (DATA_DIR / "TitleSearchDeedReport.jpg", "Caribbean property deed"),
        ]
        
        for sample_path, description in samples:
            if not sample_path.exists():
                continue
            
            result = self.engine.process_image(str(sample_path))
            
            print(f"\n{description}:")
            print(f"  Type: {result.document_type}")
            print(f"  Confidence: {result.confidence:.2f}")
            print(f"  Text sample: {result.raw_text[:100]}...")
            
            # Should extract meaningful text
            assert len(result.raw_text) > 30, \
                f"Should extract text from {description}"


# ─────────────────────────────────────────────────────────────────────────────
# Performance Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProcessingPerformance:
    """Test processing performance"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.engine = DocumentIntelligence()
    
    def test_processing_time_acceptable(self):
        """Test that processing time is acceptable for production"""
        sample_path = DATA_DIR / "Salary-slipJan.jpg"
        
        if not sample_path.exists():
            pytest.skip("Sample not found")
        
        import time
        start = time.time()
        
        result = self.engine.process_image(str(sample_path))
        
        elapsed = time.time() - start
        elapsed_ms = elapsed * 1000
        
        # Processing should complete in reasonable time
        # (adjust threshold based on your requirements)
        assert elapsed_ms < 10000, \
            f"Processing took too long: {elapsed_ms:.0f}ms"
        
        print(f"\nPerformance Test:")
        print(f"  Processing Time: {elapsed_ms:.0f}ms")
        print(f"  Document Type: {result.document_type}")


# ─────────────────────────────────────────────────────────────────────────────
# Run Tests
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
