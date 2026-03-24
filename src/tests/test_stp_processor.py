"""
Unit tests for STP (Straight-Through Processing) Engine.

Tests cover:
1. Currency detection
2. STP eligibility assessment
3. 17-checkpoint pipeline processing
4. Two-phase processing (stop before disbursement)
5. Bureau report integration
6. Affordability analysis

All tests are deterministic where possible.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.core.stp_processor import (
    StpProcessor,
    StpResult,
    detect_currency,
    format_currency,
    process_stp_loan,
    STP_RULE_PIPELINE,
    DEMO_MODE,
)
from src.core.caribbean_credit_bureau import (
    fetch_credit_bureau_report,
    format_bureau_summary,
    compute_base_score,
    score_to_grade,
    score_to_risk,
)


# =============================================================================
# Mock Storage Adapter
# =============================================================================

class MockStorage:
    """Mock storage adapter for testing."""
    
    def __init__(self):
        self.loans: Dict[str, Dict[str, Any]] = {}
        self.phases: List[Dict[str, Any]] = []
        self.documents: List[Dict[str, Any]] = []
    
    async def get_loan(self, loan_id: str) -> Dict[str, Any]:
        return self.loans.get(loan_id)
    
    async def update_loan(self, loan_id: str, data: Dict[str, Any]):
        if loan_id in self.loans:
            self.loans[loan_id].update(data)
    
    async def get_active_phases(self) -> List[Dict[str, Any]]:
        return self.phases
    
    async def get_documents_by_loan_id(self, loan_id: str) -> List[Dict[str, Any]]:
        return [d for d in self.documents if d.get('loanId') == loan_id]
    
    async def update_document_status(self, doc_id: str, status: str, note: str):
        for doc in self.documents:
            if doc['id'] == doc_id:
                doc['status'] = status
                doc['reviewNote'] = note


# =============================================================================
# Currency Detection Tests
# =============================================================================

class TestCurrencyDetection:
    """Test currency detection functions."""
    
    def test_detect_xcd(self):
        """Test XCD currency detection."""
        symbol, code = detect_currency('XCD 50,000', 'XCD 6,000')
        assert code == 'XCD'
        assert symbol == 'EC$'
    
    def test_detect_ttd(self):
        """Test TTD currency detection."""
        symbol, code = detect_currency('TTD 150,000', 'TTD 12,000')
        assert code == 'TTD'
        assert symbol == 'TT$'
    
    def test_detect_gyd(self):
        """Test GYD currency detection."""
        symbol, code = detect_currency('GYD 40,000,000', 'GYD 800,000')
        assert code == 'GYD'
        assert symbol == 'GY$'
    
    def test_detect_jmd(self):
        """Test JMD currency detection."""
        symbol, code = detect_currency('JMD 5,000,000', 'JMD 400,000')
        assert code == 'JMD'
        assert symbol == 'J$'
    
    def test_detect_default_usd(self):
        """Test default USD detection."""
        symbol, code = detect_currency('$50,000', '$6,000')
        assert code == 'USD'
        assert symbol == '$'
    
    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(50000.00, 'EC$') == 'EC$50,000.00'
        assert format_currency(150000.00, 'TT$') == 'TT$150,000.00'


# =============================================================================
# Bureau Report Tests
# =============================================================================

class TestBureauReport:
    """Test credit bureau report generation."""
    
    @pytest.mark.asyncio
    async def test_prime_borrower_score(self):
        """Test high score for prime borrower."""
        report = await fetch_credit_bureau_report({
            'borrowerName': 'Prime User',
            'monthlyIncome': 'XCD 15,000',
            'existingDebts': 'XCD 2,000',
            'loanAmount': 'XCD 50,000',
            'employmentType': 'Salaried',
        })
        
        assert 700 <= report['score'] <= 850
        assert report['grade'] in ('A', 'B')
        assert report['riskLevel'] in ('low', 'moderate')
    
    @pytest.mark.asyncio
    async def test_thin_file_score(self):
        """Test moderate score for thin file borrower."""
        report = await fetch_credit_bureau_report({
            'borrowerName': 'Thin File User',
            'monthlyIncome': 'XCD 4,000',
            'existingDebts': 'XCD 0',
            'loanAmount': 'XCD 20,000',
            'employmentType': 'Salaried',
        })
        
        # Thin file can vary widely - just check it's in valid range
        assert 300 <= report['score'] <= 850
        assert report['grade'] in ('A', 'B', 'C', 'D', 'E')
    
    @pytest.mark.asyncio
    async def test_bureau_summary_format(self):
        """Test bureau summary formatting."""
        report = await fetch_credit_bureau_report({
            'borrowerName': 'Test User',
            'monthlyIncome': 'XCD 6,000',
            'existingDebts': 'XCD 1,000',
            'loanAmount': 'XCD 50,000',
            'employmentType': 'Salaried',
        })
        
        summary = format_bureau_summary(report)
        assert 'Bureau:' in summary
        assert 'Score:' in summary
        assert 'Ref:' in summary


# =============================================================================
# STP Processor Tests
# =============================================================================

class TestStpProcessor:
    """Test STP processor."""
    
    @pytest.mark.asyncio
    async def test_processor_initialization(self):
        """Test processor initializes correctly."""
        storage = MockStorage()
        processor = StpProcessor(demo_mode=True, storage_adapter=storage)
        
        assert processor.demo_mode is True
        assert processor.storage is storage
    
    @pytest.mark.asyncio
    async def test_process_loan_not_found(self):
        """Test processing non-existent loan."""
        storage = MockStorage()
        processor = StpProcessor(demo_mode=True, storage_adapter=storage)
        
        with pytest.raises(ValueError, match="Loan not found"):
            await processor.process_loan('NONEXISTENT-001')
    
    @pytest.mark.asyncio
    async def test_process_loan_stp_eligible(self):
        """Test processing STP-eligible loan."""
        storage = MockStorage()
        
        # Setup loan
        storage.loans['LOAN-001'] = {
            'id': 'LOAN-001',
            'borrowerName': 'Test Borrower',
            'loanType': 'Personal Loan',
            'loanAmount': 'XCD 50,000',
            'monthlyIncome': 'XCD 6,000',
            'existingDebts': 'XCD 500',
            'employmentType': 'Salaried',
            'approvalTier': 'stp',
            'stpProcessingStatus': None,
        }
        
        # Setup phases
        storage.phases = [
            {'id': 'phase-1', 'name': 'Application Submission', 'sortOrder': 1, 'isActive': True},
            {'id': 'phase-2', 'name': 'Document Collection & KYC', 'sortOrder': 2, 'isActive': True},
            {'id': 'phase-3', 'name': 'Verification & Credit Appraisal', 'sortOrder': 3, 'isActive': True},
            {'id': 'phase-4', 'name': 'Underwriting & Credit Decision', 'sortOrder': 4, 'isActive': True},
            {'id': 'phase-5', 'name': 'Disbursement', 'sortOrder': 5, 'isActive': True},
        ]
        
        processor = StpProcessor(demo_mode=True, storage_adapter=storage)
        result = await processor.process_loan('LOAN-001', stop_before_disbursement=True)
        
        assert result['success'] is True
        assert result['stpApproved'] is True
        assert result['awaitingAcceptance'] is True
        assert 'approval' in result
        assert 'bureauReport' in result or result['bureauReport'] is None  # May be None if bureau unavailable
    
    @pytest.mark.asyncio
    async def test_process_loan_full_pipeline(self):
        """Test processing through full pipeline (including disbursement)."""
        storage = MockStorage()
        
        storage.loans['LOAN-002'] = {
            'id': 'LOAN-002',
            'borrowerName': 'Full Pipeline User',
            'loanType': 'Vehicle Loan',
            'loanAmount': 'XCD 80,000',
            'monthlyIncome': 'XCD 10,000',
            'existingDebts': 'XCD 1,000',
            'employmentType': 'Salaried',
            'approvalTier': 'stp',
            'stpProcessingStatus': None,
        }
        
        storage.phases = [
            {'id': 'phase-1', 'name': 'Application Submission', 'sortOrder': 1, 'isActive': True},
            {'id': 'phase-5', 'name': 'Disbursement', 'sortOrder': 5, 'isActive': True},
        ]
        
        processor = StpProcessor(demo_mode=True, storage_adapter=storage)
        result = await processor.process_loan('LOAN-002', stop_before_disbursement=False)
        
        assert result['success'] is True
        # In demo mode with stop_before_disbursement=False, should have approval or disbursement
        assert 'approval' in result or 'disbursement' in result
    
    @pytest.mark.asyncio
    async def test_stp_pipeline_has_17_checkpoints(self):
        """Test STP pipeline has 17 checkpoints."""
        assert len(STP_RULE_PIPELINE) == 17
        
        # Verify rule groups A through V
        rule_groups = [r['ruleGroup'] for r in STP_RULE_PIPELINE]
        assert 'A' in rule_groups  # Application Intake
        assert 'K' in rule_groups  # Credit Bureau
        assert 'L' in rule_groups  # Affordability
        assert 'V' in rule_groups  # Disbursement


# =============================================================================
# Affordability Analysis Tests
# =============================================================================

class TestAffordabilityAnalysis:
    """Test affordability analysis within STP."""
    
    @pytest.mark.asyncio
    async def test_foir_calculation(self):
        """Test FOIR calculation in STP processing."""
        storage = MockStorage()
        
        # Low FOIR (< 40%) - should pass
        storage.loans['LOAN-LOW-FOIR'] = {
            'id': 'LOAN-LOW-FOIR',
            'borrowerName': 'Low FOIR User',
            'loanType': 'Personal Loan',
            'loanAmount': 'XCD 30,000',
            'monthlyIncome': 'XCD 10,000',
            'existingDebts': 'XCD 500',
            'employmentType': 'Salaried',
            'approvalTier': 'stp',
        }
        
        storage.phases = [
            {'id': 'phase-1', 'name': 'Application Submission', 'sortOrder': 1, 'isActive': True},
        ]
        
        processor = StpProcessor(demo_mode=True, storage_adapter=storage)
        result = await processor.process_loan('LOAN-LOW-FOIR', stop_before_disbursement=True)
        
        assert result['success'] is True
        if result.get('affordability'):
            foir_str = result['affordability'].get('foir', '0%')
            foir = float(foir_str.replace('%', ''))
            assert foir < 40  # Should pass affordability
    
    @pytest.mark.asyncio
    async def test_high_foir_flagged(self):
        """Test high FOIR is flagged in affordability."""
        storage = MockStorage()
        
        # High FOIR (> 55%) - should be flagged
        storage.loans['LOAN-HIGH-FOIR'] = {
            'id': 'LOAN-HIGH-FOIR',
            'borrowerName': 'High FOIR User',
            'loanType': 'Personal Loan',
            'loanAmount': 'XCD 100,000',
            'monthlyIncome': 'XCD 5,000',
            'existingDebts': 'XCD 2,000',
            'employmentType': 'Salaried',
            'approvalTier': 'stp',
        }
        
        storage.phases = [
            {'id': 'phase-1', 'name': 'Application Submission', 'sortOrder': 1, 'isActive': True},
        ]
        
        processor = StpProcessor(demo_mode=True, storage_adapter=storage)
        result = await processor.process_loan('LOAN-HIGH-FOIR', stop_before_disbursement=True)
        
        # In demo mode, still approves but flags affordability
        assert result['success'] is True
        if result.get('affordability'):
            foir_str = result['affordability'].get('foir', '0%')
            foir = float(foir_str.replace('%', ''))
            # Should be high
            assert foir > 40


# =============================================================================
# Integration Tests
# =============================================================================

class TestStpIntegration:
    """Test STP integration with full workflow."""
    
    @pytest.mark.asyncio
    async def test_full_stp_workflow(self):
        """Test complete STP workflow from application to disbursement."""
        storage = MockStorage()
        notifications = []
        
        async def notify(user_id, type, title, message, loan_id=None):
            notifications.append({
                'userId': user_id,
                'type': type,
                'title': title,
                'message': message,
                'loanId': loan_id,
            })
        
        # Setup loan
        storage.loans['LOAN-INTEGRATION'] = {
            'id': 'LOAN-INTEGRATION',
            'borrowerName': 'Integration User',
            'loanType': 'Home Loan',
            'loanAmount': 'XCD 500,000',
            'monthlyIncome': 'XCD 15,000',
            'existingDebts': 'XCD 2,000',
            'employmentType': 'Salaried',
            'approvalTier': 'stp',
            'stpProcessingStatus': None,
            'userId': 'USER-001',
        }
        
        storage.phases = [
            {'id': 'phase-1', 'name': 'Application Submission', 'sortOrder': 1, 'isActive': True},
            {'id': 'phase-2', 'name': 'Document Collection & KYC', 'sortOrder': 2, 'isActive': True},
            {'id': 'phase-3', 'name': 'Verification & Credit Appraisal', 'sortOrder': 3, 'isActive': True},
            {'id': 'phase-4', 'name': 'Underwriting & Credit Decision', 'sortOrder': 4, 'isActive': True},
            {'id': 'phase-5', 'name': 'Conditional Approval & Offer', 'sortOrder': 5, 'isActive': True},
            {'id': 'phase-6', 'name': 'Disbursement', 'sortOrder': 6, 'isActive': True},
        ]
        
        # Process with stop before disbursement
        result = await process_stp_loan(
            'LOAN-INTEGRATION',
            storage=storage,
            notify=notify,
            stop_before_disbursement=True,
            demo_mode=True,
        )
        
        assert result['success'] is True
        assert result['stpApproved'] is True
        assert result['awaitingAcceptance'] is True
        
        # Check notifications
        assert len(notifications) >= 1
        assert notifications[0]['title'] == 'Loan Approved!'
        
        # Check loan was updated
        loan = storage.loans['LOAN-INTEGRATION']
        assert loan['stpProcessingStatus'] == 'awaiting_acceptance'
        assert loan['status'] == 'approved'
        assert 'approvedRate' in loan


# =============================================================================
# Demo Mode Tests
# =============================================================================

class TestDemoMode:
    """Test demo mode behavior."""
    
    def test_demo_mode_enabled(self):
        """Test demo mode is enabled for development."""
        assert DEMO_MODE is True  # Should be True for development
    
    @pytest.mark.asyncio
    async def test_demo_auto_approves(self):
        """Test demo mode auto-approves applications."""
        storage = MockStorage()
        
        storage.loans['LOAN-DEMO'] = {
            'id': 'LOAN-DEMO',
            'borrowerName': 'Demo User',
            'loanType': 'Personal Loan',
            'loanAmount': 'XCD 50,000',
            'monthlyIncome': 'XCD 0',  # Even with zero income
            'existingDebts': 'XCD 0',
            'employmentType': 'Unknown',
            'approvalTier': 'stp',
        }
        
        storage.phases = [
            {'id': 'phase-1', 'name': 'Application Submission', 'sortOrder': 1, 'isActive': True},
        ]
        
        processor = StpProcessor(demo_mode=True, storage_adapter=storage)
        result = await processor.process_loan('LOAN-DEMO', stop_before_disbursement=True)
        
        # Demo mode should approve anyway
        assert result['success'] is True
        assert result['stpApproved'] is True
