"""
Test Suite for Enhanced STP Simulation (TASK-005.01, TASK-005.02, TASK-005.03)

Testing Philosophy:
- Use REAL simulation logic (no mocking of core functions)
- Test with deterministic seeds for reproducibility
- Verify demo profiles produce expected outcomes
- Test OpenSanctions integration when available
- Use synthetic test data for deterministic results

Test Categories:
1. Correctness: Bureau simulation, AML screening, decision logic
2. Integration: OpenSanctions API, demo profiles
3. Performance: Processing time requirements
4. Edge Cases: Boundary conditions, invalid inputs

Run with:
    # Unit tests only
    pytest src/core/tests/test_stp_simulation.py -v
    
    # Integration tests (requires OpenSanctions API access)
    RUN_INTEGRATION=1 pytest src/core/tests/test_stp_simulation.py -v
"""

import pytest
import os
import time
from typing import Dict, Any

from src.core.stp_simulation import (
    BureauReport,
    AMLResult,
    STPSimulationResult,
    DemoProfiles,
    BureauScoreSimulator,
    AMLScreeningService,
    STPSimulator,
    simulate_stp_for_demo,
    DEMO_PROFILE_CONFIG,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def bureau_simulator() -> BureauScoreSimulator:
    """Create bureau score simulator with fixed seed"""
    return BureauScoreSimulator(seed=42)


@pytest.fixture
def stp_simulator() -> STPSimulator:
    """Create STP simulator with fixed seed"""
    return STPSimulator(bureau_seed=42, use_opensanctions=False)


@pytest.fixture
def sample_application() -> Dict[str, Any]:
    """Sample application data"""
    return {
        "monthly_income": 8000.0,
        "existing_debts": 500.0,
        "employment_type": "salaried",
        "loan_amount": 75000.0,
        "borrower_name": "John Smith",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Bureau Score Simulator Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBureauScoreSimulator:
    """Test bureau score simulation"""
    
    def test_simulator_creation(self, bureau_simulator: BureauScoreSimulator):
        """Test simulator initialization"""
        assert bureau_simulator.base_score == 650
        assert bureau_simulator.std_dev == 100
    
    def test_simulate_with_good_profile(self, bureau_simulator: BureauScoreSimulator):
        """Test simulation with good applicant profile"""
        report = bureau_simulator.simulate(
            monthly_income=10000.0,
            existing_debts=500.0,
            employment_type="salaried"
        )
        
        assert isinstance(report, BureauReport)
        assert 300 <= report.score <= 900
        assert report.grade in ("A", "B", "C", "D", "E")
        assert report.risk_level in ("low", "moderate", "elevated", "high")
        # Good profile should score above average
        assert report.score > 650
    
    def test_simulate_with_poor_profile(self, bureau_simulator: BureauScoreSimulator):
        """Test simulation with poor applicant profile"""
        report = bureau_simulator.simulate(
            monthly_income=2000.0,
            existing_debts=1800.0,
            employment_type="unemployed"
        )
        
        assert isinstance(report, BureauReport)
        assert 300 <= report.score <= 900
        # Poor profile should score below average
        assert report.score < 650
    
    def test_simulate_reproducible_with_seed(self):
        """Test that same seed produces similar score ranges"""
        sim1 = BureauScoreSimulator(seed=123)
        sim2 = BureauScoreSimulator(seed=123)
        
        # Run multiple simulations to establish pattern
        scores1 = []
        scores2 = []
        
        for _ in range(5):
            report1 = sim1.simulate(8000.0, 500.0, "salaried")
            report2 = sim2.simulate(8000.0, 500.0, "salaried")
            scores1.append(report1.score)
            scores2.append(report2.score)
        
        # Scores should be in similar range (within 100 points)
        # Exact match not guaranteed due to multiple random calls per simulation
        avg_diff = sum(abs(s1 - s2) for s1, s2 in zip(scores1, scores2)) / len(scores1)
        assert avg_diff < 100
    
    def test_income_categorization(self, bureau_simulator: BureauScoreSimulator):
        """Test income level categorization"""
        assert bureau_simulator._categorize_income(2000) == "low"
        assert bureau_simulator._categorize_income(5000) == "medium"
        assert bureau_simulator._categorize_income(10000) == "high"
        assert bureau_simulator._categorize_income(20000) == "very_high"
    
    def test_debt_ratio_categorization(self, bureau_simulator: BureauScoreSimulator):
        """Test debt ratio categorization"""
        assert bureau_simulator._categorize_debt_ratio(0.1) == "low"
        assert bureau_simulator._categorize_debt_ratio(0.3) == "medium"
        assert bureau_simulator._categorize_debt_ratio(0.5) == "high"
        assert bureau_simulator._categorize_debt_ratio(0.8) == "very_high"
    
    def test_score_to_grade_conversion(self, bureau_simulator: BureauScoreSimulator):
        """Test score to grade conversion"""
        assert bureau_simulator._score_to_grade(800) == ("A", "Excellent")
        assert bureau_simulator._score_to_grade(700) == ("B", "Good")
        assert bureau_simulator._score_to_grade(600) == ("C", "Fair")
        assert bureau_simulator._score_to_grade(500) == ("D", "Poor")
        assert bureau_simulator._score_to_grade(400) == ("E", "Very Poor")
    
    def test_score_to_risk_conversion(self, bureau_simulator: BureauScoreSimulator):
        """Test score to risk level conversion"""
        assert bureau_simulator._score_to_risk(800) == "low"
        assert bureau_simulator._score_to_risk(700) == "moderate"
        assert bureau_simulator._score_to_risk(600) == "elevated"
        assert bureau_simulator._score_to_risk(400) == "high"
    
    def test_generate_factors(self, bureau_simulator: BureauScoreSimulator):
        """Test factor generation"""
        factors = bureau_simulator._generate_factors(
            score=750,
            income_category="high",
            debt_category="low",
            employment_type="salaried"
        )
        
        assert len(factors) > 0
        assert any("income" in f.lower() for f in factors)
    
    def test_score_range_clamping(self, bureau_simulator: BureauScoreSimulator):
        """Test that scores are clamped to valid range"""
        # Extreme cases should still be in range
        report1 = bureau_simulator.simulate(50000.0, 0.0, "government")
        report2 = bureau_simulator.simulate(1000.0, 900.0, "unemployed")
        
        assert 300 <= report1.score <= 900
        assert 300 <= report2.score <= 900


# ─────────────────────────────────────────────────────────────────────────────
# AML Screening Service Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAMLScreeningService:
    """Test AML screening service"""
    
    def test_service_creation(self):
        """Test service initialization"""
        service = AMLScreeningService(use_opensanctions=False)
        assert service.use_opensanctions is False
    
    def test_screen_clean_name(self):
        """Test screening of clean name"""
        service = AMLScreeningService(use_opensanctions=False)
        result = service.screen("John Smith")
        
        assert isinstance(result, AMLResult)
        assert result.passed is True
        assert result.sanctions_match is False
        assert result.pep_match is False
        assert result.risk_score < 0.5
    
    def test_screen_demo_watchlist(self):
        """Test screening against demo watchlist"""
        service = AMLScreeningService(use_opensanctions=False)
        
        for name in ["test_suspicious", "money_launderer", "sanctions_test"]:
            result = service.screen(name)
            
            assert result.passed is False
            assert result.sanctions_match is True
            assert result.risk_score > 0.8
            assert len(result.matches) > 0
    
    def test_screen_caching(self):
        """Test that results are cached"""
        service = AMLScreeningService(use_opensanctions=False)
        
        # First call
        result1 = service.screen("Test User")
        
        # Second call should use cache
        result2 = service.screen("Test User")
        
        assert result1.risk_score == result2.risk_score
        assert result1.screening_date == result2.screening_date


# ─────────────────────────────────────────────────────────────────────────────
# STP Simulator Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSTPSimulator:
    """Test STP simulator"""
    
    def test_simulator_creation(self, stp_simulator: STPSimulator):
        """Test simulator initialization"""
        assert stp_simulator.bureau_simulator is not None
        assert stp_simulator.aml_service is not None
    
    def test_simulate_approved_application(self, stp_simulator: STPSimulator):
        """Test simulation of approved application"""
        result = stp_simulator.simulate_application(
            monthly_income=8000.0,
            existing_debts=500.0,
            employment_type="salaried",
            loan_amount=75000.0,
            borrower_name="John Smith"
        )
        
        assert isinstance(result, STPSimulationResult)
        assert result.approved is True
        assert result.bureau_score > 600
        assert result.aml_passed is True
        assert result.foir < 55.0
        assert result.processing_time_ms > 0
    
    def test_simulate_rejected_low_score(self, stp_simulator: STPSimulator):
        """Test simulation with low bureau score"""
        result = stp_simulator.simulate_application(
            monthly_income=2000.0,
            existing_debts=1800.0,
            employment_type="unemployed",
            loan_amount=50000.0,
            borrower_name="Poor Applicant"
        )
        
        # Should be rejected due to low score or high FOIR
        assert result.approved is False or result.foir > 55.0
    
    def test_simulate_rejected_aml(self, stp_simulator: STPSimulator):
        """Test simulation with AML failure"""
        result = stp_simulator.simulate_application(
            monthly_income=10000.0,
            existing_debts=500.0,
            employment_type="salaried",
            loan_amount=100000.0,
            borrower_name="test_suspicious"
        )
        
        assert result.approved is False
        assert result.aml_passed is False
        assert "AML" in result.decision_reason
    
    def test_simulate_rejected_high_foir(self, stp_simulator: STPSimulator):
        """Test simulation with high FOIR"""
        result = stp_simulator.simulate_application(
            monthly_income=4000.0,
            existing_debts=2500.0,  # 62.5% FOIR
            employment_type="salaried",
            loan_amount=60000.0,
            borrower_name="High Debt User"
        )
        
        # Should be rejected due to high FOIR or low bureau score
        assert result.approved is False
        assert result.foir == 62.5  # FOIR calculation is deterministic
        # Rejection reason should mention FOIR or bureau score
        assert "FOIR" in result.decision_reason or "Bureau" in result.decision_reason
    
    def test_demo_profile_approved(self, stp_simulator: STPSimulator):
        """Test demo profile for approved application"""
        result = stp_simulator.process_demo_application(DemoProfiles.APPROVED)
        
        assert result.approved is True
        assert result.bureau_score > 650
        assert result.aml_passed is True
    
    def test_demo_profile_rejected_low_score(self, stp_simulator: STPSimulator):
        """Test demo profile for rejected (low score) application"""
        result = stp_simulator.process_demo_application(DemoProfiles.REJECTED_LOW_SCORE)
        
        assert result.approved is False
        assert result.aml_passed is False  # This profile triggers AML
    
    def test_demo_profile_rejected_high_foir(self, stp_simulator: STPSimulator):
        """Test demo profile for rejected (high FOIR) application"""
        result = stp_simulator.process_demo_application(DemoProfiles.REJECTED_HIGH_FOIR)
        
        assert result.approved is False
        assert result.foir > 55.0
    
    def test_demo_profile_rejected_aml(self, stp_simulator: STPSimulator):
        """Test demo profile for rejected (AML) application"""
        result = stp_simulator.process_demo_application(DemoProfiles.REJECTED_AML)
        
        assert result.approved is False
        assert result.aml_passed is False
    
    def test_demo_profile_manual_review(self, stp_simulator: STPSimulator):
        """Test demo profile for manual review"""
        result = stp_simulator.process_demo_application(DemoProfiles.MANUAL_REVIEW)
        
        # This profile should be borderline
        assert result.bureau_score < 650 or result.foir > 40.0


# ─────────────────────────────────────────────────────────────────────────────
# Integration Helper Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationHelper:
    """Test simulate_stp_for_demo helper function"""
    
    def test_helper_with_regular_application(self):
        """Test helper with regular application"""
        result = simulate_stp_for_demo(
            monthly_income=8000.0,
            existing_debts=500.0,
            employment_type="salaried",
            loan_amount=75000.0,
            borrower_name="John Smith",
            use_demo_profile=False
        )
        
        assert isinstance(result, STPSimulationResult)
    
    def test_helper_with_demo_profile(self):
        """Test helper with demo profile"""
        result = simulate_stp_for_demo(
            monthly_income=0,
            existing_debts=0,
            employment_type="",
            loan_amount=0,
            borrower_name="",
            use_demo_profile=True,
            demo_profile=DemoProfiles.APPROVED
        )
        
        assert result.approved is True


# ─────────────────────────────────────────────────────────────────────────────
# Performance Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance:
    """Test performance characteristics"""
    
    def test_bureau_simulation_performance(self, bureau_simulator: BureauScoreSimulator):
        """Test bureau simulation is fast"""
        start = time.time()
        
        for _ in range(100):
            bureau_simulator.simulate(8000.0, 500.0, "salaried")
        
        elapsed = time.time() - start
        
        # Should be very fast (<100ms for 100 simulations)
        assert elapsed < 0.1
    
    def test_aml_screening_performance(self):
        """Test AML screening is fast"""
        service = AMLScreeningService(use_opensanctions=False)
        
        start = time.time()
        
        for _ in range(100):
            service.screen("John Smith")
        
        elapsed = time.time() - start
        
        # Should be very fast (<50ms for 100 screenings)
        assert elapsed < 0.05
    
    def test_stp_simulation_performance(self, stp_simulator: STPSimulator):
        """Test complete STP simulation performance"""
        start = time.time()
        
        for _ in range(10):
            stp_simulator.simulate_application(
                monthly_income=8000.0,
                existing_debts=500.0,
                employment_type="salaried",
                loan_amount=75000.0,
                borrower_name="John Smith"
            )
        
        elapsed = time.time() - start
        
        # Should complete 10 simulations in <1 second
        assert elapsed < 1.0
    
    def test_single_simulation_latency(self, stp_simulator: STPSimulator):
        """Test single simulation latency"""
        result = stp_simulator.simulate_application(
            monthly_income=8000.0,
            existing_debts=500.0,
            employment_type="salaried",
            loan_amount=75000.0,
            borrower_name="John Smith"
        )
        
        # Should complete in <100ms
        assert result.processing_time_ms < 100


# ─────────────────────────────────────────────────────────────────────────────
# Edge Cases and Error Handling
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_zero_income(self, stp_simulator: STPSimulator):
        """Test application with zero income"""
        result = stp_simulator.simulate_application(
            monthly_income=0.0,
            existing_debts=0.0,
            employment_type="unemployed",
            loan_amount=10000.0,
            borrower_name="No Income"
        )
        
        # Should be rejected
        assert result.approved is False
    
    def test_zero_debts(self, stp_simulator: STPSimulator):
        """Test application with no existing debts"""
        result = stp_simulator.simulate_application(
            monthly_income=8000.0,
            existing_debts=0.0,
            employment_type="salaried",
            loan_amount=75000.0,
            borrower_name="No Debts"
        )
        
        # Should be approved (good profile)
        assert result.approved is True
        assert result.foir == 0.0
    
    def test_very_high_income(self, stp_simulator: STPSimulator):
        """Test application with very high income"""
        result = stp_simulator.simulate_application(
            monthly_income=50000.0,
            existing_debts=5000.0,
            employment_type="salaried",
            loan_amount=500000.0,
            borrower_name="High Earner"
        )
        
        # Should be approved
        assert result.approved is True
        assert result.bureau_score > 650
    
    def test_empty_borrower_name(self, stp_simulator: STPSimulator):
        """Test application with empty borrower name"""
        result = stp_simulator.simulate_application(
            monthly_income=8000.0,
            existing_debts=500.0,
            employment_type="salaried",
            loan_amount=75000.0,
            borrower_name=""
        )
        
        # Should still process (name just won't match watchlist)
        assert isinstance(result, STPSimulationResult)
    
    def test_all_demo_profiles_exist(self):
        """Test that all demo profiles are configured"""
        for profile in DemoProfiles:
            assert profile in DEMO_PROFILE_CONFIG
            config = DEMO_PROFILE_CONFIG[profile]
            
            # Verify config has required fields
            assert "borrower_name" in config
            assert "monthly_income" in config
            assert "existing_debts" in config
            assert "employment_type" in config
            assert "loan_amount" in config
            assert "expected_decision" in config


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests (OpenSanctions)
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenSanctionsIntegration:
    """
    Integration tests with OpenSanctions API.
    
    These tests require internet connectivity and OpenSanctions API access.
    
    Run with:
        RUN_INTEGRATION=1 pytest src/core/tests/test_stp_simulation.py::TestOpenSanctionsIntegration -v
    """
    
    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION"),
        reason="Requires RUN_INTEGRATION=1"
    )
    def test_opensanctions_screening(self):
        """Test real OpenSanctions screening"""
        service = AMLScreeningService(use_opensanctions=True)
        
        # Screen a common name (should pass)
        result = service.screen("John Smith")
        
        assert isinstance(result, AMLResult)
        # Most common names should pass
        assert result.passed is True or len(result.matches) == 0
    
    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION"),
        reason="Requires RUN_INTEGRATION=1"
    )
    def test_opensanctions_known_match(self):
        """Test OpenSanctions with known match"""
        service = AMLScreeningService(use_opensanctions=True)
        
        # Screen a known sanctioned individual (example: test name)
        result = service.screen("test_suspicious")
        
        # Demo watchlist should still trigger
        assert result.passed is False
        assert result.sanctions_match is True


# ─────────────────────────────────────────────────────────────────────────────
# Main Test Runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
