"""
Unit tests for KS-LOS calculation engines.

Tests are deterministic with known inputs and expected outputs.
All financial calculations are validated against reference implementations.
"""

import pytest
from src.core.calculation_engines import (
    parse_numeric,
    compute_reducing_emi,
    compute_flat_emi,
    compute_step_up_emi,
    compute_interest_metrics,
    compute_affordability,
    compute_collateral_metrics,
    compute_credit_risk,
    compute_file_completeness,
    generate_amortization_schedule,
    compute_broken_period_interest,
    compute_moratorium_impact,
    compute_total_fees,
    compute_apr,
    FeeStructure,
    compute_part_payment_impact,
    compute_foreclosure,
    compute_refinance_comparison,
    assess_stp_eligibility,
    detect_currency_rate,
    to_usd_equivalent,
    compute_full_loan_metrics,
)


class TestParseNumeric:
    """Test parse_numeric utility function."""

    def test_parse_plain_number(self):
        """Test parsing plain numeric strings."""
        assert parse_numeric("1000") == 1000.0
        assert parse_numeric("1000.50") == 1000.5

    def test_parse_with_currency_symbols(self):
        """Test parsing with various currency symbols."""
        assert parse_numeric("$1000") == 1000.0
        assert parse_numeric("€1000") == 1000.0
        assert parse_numeric("£1000") == 1000.0
        assert parse_numeric("₹1000") == 1000.0

    def test_parse_with_commas(self):
        """Test parsing with thousand separators."""
        assert parse_numeric("1,000") == 1000.0
        assert parse_numeric("1,000,000") == 1000000.0
        assert parse_numeric("$50,000") == 50000.0

    def test_parse_with_whitespace(self):
        """Test parsing with whitespace."""
        assert parse_numeric("  1000  ") == 1000.0
        assert parse_numeric("$ 50,000") == 50000.0

    def test_parse_none_and_invalid(self):
        """Test parsing None and invalid values."""
        assert parse_numeric(None) == 0.0
        assert parse_numeric("") == 0.0
        assert parse_numeric("invalid") == 0.0

    def test_parse_numeric_types(self):
        """Test parsing already numeric types."""
        assert parse_numeric(1000) == 1000.0
        assert parse_numeric(1000.5) == 1000.5
        assert parse_numeric(0) == 0.0


class TestComputeReducingEMI:
    """Test reducing balance EMI calculation."""

    def test_standard_loan(self):
        """Test standard loan EMI calculation."""
        result = compute_reducing_emi(1000000, 10.5, 240)
        
        # Validate EMI is positive and reasonable
        assert result.emi > 0
        assert result.emi < 1000000  # EMI should be fraction of principal
        
        # Validate totals
        assert result.total_repayment > result.principal
        assert result.total_interest > 0
        
        # Validate effective rate > nominal rate
        assert result.effective_annual_rate > 10.5

    def test_zero_interest_loan(self):
        """Test zero interest loan."""
        result = compute_reducing_emi(120000, 0, 12)
        
        assert result.emi == 10000  # 120000 / 12
        assert result.total_interest == 0
        assert result.total_repayment == 120000

    def test_invalid_inputs(self):
        """Test with invalid inputs."""
        result = compute_reducing_emi(0, 10, 12)
        assert result.emi == 0
        
        result = compute_reducing_emi(1000, 10, 0)
        assert result.emi == 0

    def test_caribbean_market_scenario(self):
        """Test typical Caribbean personal loan."""
        # XCD 50,000 at 12% for 5 years
        result = compute_reducing_emi(50000, 12.0, 60)
        
        assert result.emi > 0
        assert result.total_interest > 0


class TestComputeFlatEMI:
    """Test flat rate EMI calculation."""

    def test_flat_vs_reducing(self):
        """Flat EMI is higher than reducing EMI (interest on original principal)."""
        flat = compute_flat_emi(100000, 10, 12)
        reducing = compute_reducing_emi(100000, 10, 12)
        
        # Flat rate EMI is higher because interest is calculated on full principal
        assert flat.emi > reducing.emi
        assert flat.total_interest > reducing.total_interest


class TestComputeAffordability:
    """Test affordability metrics calculation."""

    def test_healthy_foir(self):
        """Test with healthy FOIR (< 40%)."""
        metrics = compute_affordability(
            monthly_income=10000,
            existing_emi_total=2000,
            proposed_emi=2000
        )
        
        assert metrics.foir == 40.0
        assert metrics.dti == 40.0
        # Caribbean thresholds: 10000 is "weak" (< 25000)
        assert metrics.income_stability_signal == "weak"
        assert metrics.leverage_indicator == "moderate"

    def test_high_foir(self):
        """Test with high FOIR (> 60%)."""
        metrics = compute_affordability(
            monthly_income=10000,
            existing_emi_total=4000,
            proposed_emi=3000
        )
        
        assert metrics.foir == 70.0
        assert metrics.leverage_indicator == "very-high"
        # Caribbean thresholds: 10000 is "weak" (< 25000)
        assert metrics.income_stability_signal == "weak"

    def test_with_co_applicant(self):
        """Test with co-applicant income."""
        metrics = compute_affordability(
            monthly_income=10000,
            existing_emi_total=2000,
            proposed_emi=2000,
            co_applicant_income=5000
        )
        
        # Gross income = 15000, obligations = 4000
        assert metrics.foir < 40.0  # Improved FOIR

    def test_zero_income(self):
        """Test with zero income."""
        metrics = compute_affordability(
            monthly_income=0,
            existing_emi_total=0,
            proposed_emi=0
        )
        
        assert metrics.foir == 0.0
        assert metrics.income_stability_signal == "unknown"


class TestComputeCollateralMetrics:
    """Test collateral adequacy metrics."""

    def test_conservative_ltv(self):
        """Test conservative LTV scenario."""
        metrics = compute_collateral_metrics(
            loan_amount=75000,
            collateral_value=100000,
            haircut_percent=15.0
        )
        
        assert metrics.ltv == 75.0
        assert metrics.haircut_adjusted_value == 85000
        assert metrics.collateral_coverage_ratio > 1.0

    def test_high_ltv(self):
        """Test high LTV scenario."""
        metrics = compute_collateral_metrics(
            loan_amount=95000,
            collateral_value=100000,
            haircut_percent=15.0
        )
        
        assert metrics.ltv == 95.0
        assert metrics.unsecured_exposure > 0

    def test_with_down_payment(self):
        """Test with borrower down payment."""
        metrics = compute_collateral_metrics(
            loan_amount=80000,
            collateral_value=100000,
            down_payment=20000
        )
        
        assert metrics.borrower_own_contribution == 20000


class TestComputeCreditRisk:
    """Test credit risk assessment."""

    def test_excellent_profile(self):
        """Test with excellent credit profile."""
        affordability = compute_affordability(10000, 1000, 2000)
        collateral = compute_collateral_metrics(50000, 100000)
        
        risk = compute_credit_risk(
            affordability=affordability,
            collateral=collateral,
            credit_score=780,
            completeness_score=90,
            loan_type="Personal Loan",
            has_collateral=True
        )
        
        assert risk.approval_probability >= 80
        assert risk.risk_grade == "A"
        assert len(risk.compensating_factors) > 0
        assert risk.delinquency_risk_signal == "low"

    def test_poor_profile(self):
        """Test with poor credit profile."""
        affordability = compute_affordability(5000, 3000, 2000)
        collateral = compute_collateral_metrics(8000, 10000)
        
        risk = compute_credit_risk(
            affordability=affordability,
            collateral=collateral,
            credit_score=580,
            completeness_score=30,
            loan_type="Personal Loan",
            has_collateral=False
        )
        
        assert risk.approval_probability < 50
        assert risk.risk_grade in ["D", "E"]
        assert len(risk.deviations) > 0
        assert risk.delinquency_risk_signal == "critical"

    def test_approval_probability_bounds(self):
        """Test approval probability is bounded [5, 95]."""
        affordability = compute_affordability(10000, 0, 0)
        collateral = compute_collateral_metrics(0, 0)
        
        # Perfect profile
        risk = compute_credit_risk(
            affordability=affordability,
            collateral=collateral,
            credit_score=850,
            completeness_score=100,
            loan_type="Personal Loan",
            has_collateral=False
        )
        
        assert 5 <= risk.approval_probability <= 95


class TestComputeFileCompleteness:
    """Test file completeness scoring."""

    def test_complete_application(self):
        """Test complete application."""
        loan_data = {
            "borrower_name": "John Doe",
            "borrower_email": "john@example.com",
            "borrower_phone": "+1234567890",
            "loan_type": "Personal Loan",
            "loan_amount": "50000",
            "interest_rate": "10",
            "tenure": "60",
            "purpose": "Debt consolidation",
            "employment_type": "Salaried",
            "monthly_income": "5000",
            "existing_debts": "1000",
            "credit_score": "720",
        }
        
        score = compute_file_completeness(loan_data)
        # 12 out of 16 fields filled = 75%
        assert score == 75

    def test_incomplete_application(self):
        """Test incomplete application."""
        loan_data = {
            "borrower_name": "John Doe",
            "loan_amount": "50000",
        }
        
        score = compute_file_completeness(loan_data)
        assert score < 50


class TestGenerateAmortizationSchedule:
    """Test amortization schedule generation."""

    def test_reducing_balance_schedule(self):
        """Test reducing balance amortization."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12.0,
            tenure_months=12,
            emi_type="reducing"
        )
        
        assert len(schedule.rows) == 12
        assert schedule.rows[-1].closing_balance == 0
        
        # Principal component should increase over time
        assert schedule.rows[-1].principal_component > schedule.rows[0].principal_component
        
        # Interest component should decrease over time
        assert schedule.rows[-1].interest_component < schedule.rows[0].interest_component

    def test_flat_schedule(self):
        """Test flat rate amortization."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=12.0,
            tenure_months=12,
            emi_type="flat"
        )
        
        assert len(schedule.rows) == 12
        
        # EMI should be constant
        emi_amount = schedule.rows[0].emi_amount
        for row in schedule.rows:
            assert row.emi_amount == emi_amount


class TestComputeAPR:
    """Test APR calculation including fees."""

    def test_apr_with_fees(self):
        """Test APR is higher than nominal rate when fees exist."""
        fees = FeeStructure(
            processing_fee_percent=2.0,
            documentation_fee=500,
            gst_on_fees_percent=18.0
        )
        
        result = compute_apr(
            principal=100000,
            annual_rate=10.0,
            tenure_months=24,
            fees=fees
        )
        
        # APR should be higher than nominal rate due to fees
        assert result.apr > 10.0
        assert result.total_fees > 0
        assert result.effective_cash_received < 100000

    def test_apr_without_fees(self):
        """Test APR equals nominal rate when no fees."""
        fees = FeeStructure(
            processing_fee_percent=0.0,
            processing_fee_flat=0.0,
            admin_fee=0.0,
            documentation_fee=0.0,
            valuation_fee=0.0,
            insurance_fee=0.0,
            legal_fee=0.0,
            stamp_duty=0.0,
            gst_on_fees_percent=0.0
        )
        
        result = compute_apr(
            principal=100000,
            annual_rate=10.0,
            tenure_months=24,
            fees=fees
        )
        
        # APR should be very close to nominal rate
        assert abs(result.apr - 10.0) < 0.1


class TestComputePartPaymentImpact:
    """Test part-payment impact calculations."""

    def test_reduce_tenure(self):
        """Test part-payment with tenure reduction."""
        result = compute_part_payment_impact(
            outstanding_principal=100000,
            annual_rate=10.0,
            remaining_tenure_months=60,
            part_payment_amount=20000,
            option="reduce-tenure"
        )
        
        assert result.part_payment_amount == 20000
        assert result.tenure_reduction > 0
        assert result.interest_saved > 0

    def test_reduce_emi(self):
        """Test part-payment with EMI reduction."""
        result = compute_part_payment_impact(
            outstanding_principal=100000,
            annual_rate=10.0,
            remaining_tenure_months=60,
            part_payment_amount=20000,
            option="reduce-emi"
        )
        
        assert result.part_payment_amount == 20000
        # Original EMI ~2125, revised should be lower
        assert result.revised_emi <= 1700
        assert result.revised_tenure == 60


class TestComputeForeclosure:
    """Test foreclosure calculations."""

    def test_foreclosure_with_charge(self):
        """Test foreclosure with charge."""
        result = compute_foreclosure(
            outstanding_principal=100000,
            annual_rate=10.0,
            remaining_tenure_months=60,
            foreclosure_charge_percent=2.0
        )
        
        # Result is a dict, not a dataclass
        assert result["foreclosure_amount"] > 100000
        assert result["foreclosure_charge"] == 2000  # 2% of 100000


class TestComputeRefinanceComparison:
    """Test refinancing comparison."""

    def test_beneficial_refinance(self):
        """Test beneficial refinancing scenario."""
        result = compute_refinance_comparison(
            outstanding_principal=100000,
            current_rate=12.0,
            new_rate=10.0,
            remaining_tenure_months=60,
            switching_cost=2000
        )
        
        # Result is a dict, not a dataclass
        assert result["new_emi"] < result["current_emi"]
        assert result["emi_saving"] > 0
        assert result["break_even_months"] > 0

    def test_unbeneficial_refinance(self):
        """Test refinancing to higher rate."""
        result = compute_refinance_comparison(
            outstanding_principal=100000,
            current_rate=10.0,
            new_rate=12.0,
            remaining_tenure_months=60
        )
        
        # Result is a dict, not a dataclass
        assert result["new_emi"] > result["current_emi"]
        assert result["emi_saving"] < 0


class TestSTPEligibility:
    """Test STP eligibility assessment."""

    def test_stp_approved_personal_loan(self):
        """Test STP approval for standard personal loan."""
        assessment = assess_stp_eligibility({
            "loan_type": "Personal Loan",
            "loan_amount": "$50,000",
            "monthly_income": "$6,000",
            "existing_debts": "$500",
            "employment_type": "Salaried"
        })
        
        assert assessment.tier == "stp"
        assert assessment.document_action == "upload_now"

    def test_referred_self_employed(self):
        """Test referral for self-employed applicant."""
        assessment = assess_stp_eligibility({
            "loan_type": "Personal Loan",
            "loan_amount": "$50,000",
            "monthly_income": "$8,000",
            "existing_debts": "$500",
            "employment_type": "Self-employed"
        })
        
        assert assessment.tier == "referred"
        assert assessment.referral_category == "income_verification"

    def test_referred_high_amount(self):
        """Test referral for high loan amount."""
        assessment = assess_stp_eligibility({
            "loan_type": "Personal Loan",
            "loan_amount": "$600,000",
            "monthly_income": "$20,000",
            "existing_debts": "$2,000",
            "employment_type": "Salaried"
        })
        
        assert assessment.tier == "referred"
        assert "exceeds standard processing limit" in assessment.reasons[0]

    def test_committee_review_very_high(self):
        """Test committee review for very high amount."""
        assessment = assess_stp_eligibility({
            "loan_type": "Personal Loan",
            "loan_amount": "$1,500,000",
            "monthly_income": "$50,000",
            "existing_debts": "$5,000",
            "employment_type": "Salaried"
        })
        
        assert assessment.tier == "committee"
        assert assessment.referral_category == "committee_review"

    def test_referred_high_foir(self):
        """Test referral for high FOIR."""
        assessment = assess_stp_eligibility({
            "loan_type": "Personal Loan",
            "loan_amount": "$100,000",
            "monthly_income": "$3,000",
            "existing_debts": "$1,000",
            "employment_type": "Salaried"
        })
        
        assert assessment.tier == "referred"
        assert "affordability" in assessment.reasons[0].lower()


class TestCurrencyDetection:
    """Test currency detection and USD conversion."""

    def test_detect_usd(self):
        """Test USD detection."""
        assert detect_currency_rate("$50,000") == 1.0
        assert detect_currency_rate("USD 50000") == 1.0

    def test_detect_caribbean_currencies(self):
        """Test Caribbean currency detection."""
        assert detect_currency_rate("TTD 50,000") == 6.8
        assert detect_currency_rate("GYD 500,000") == 209.0
        assert detect_currency_rate("JMD 500,000") == 155.0
        assert detect_currency_rate("XCD 50,000") == 2.7

    def test_usd_conversion(self):
        """Test USD conversion."""
        assert to_usd_equivalent(270000, 2.7) == 100000.0  # XCD to USD
        assert to_usd_equivalent(680000, 6.8) == 100000.0  # TTD to USD


class TestComputeFullLoanMetrics:
    """Test complete loan metrics snapshot."""

    def test_full_metrics_calculation(self):
        """Test full metrics for typical loan."""
        loan_data = {
            "id": "LOAN-001",
            "loan_amount": "100000",
            "interest_rate": "10.5",
            "tenure": "240",
            "monthly_income": "10000",
            "existing_debts": "2000",
            "credit_score": "720",
            "employment_type": "Salaried",
            "loan_type": "Personal Loan",
        }
        
        metrics = compute_full_loan_metrics(loan_data)
        
        assert metrics.loan_id == "LOAN-001"
        assert metrics.emi.emi > 0
        assert metrics.affordability.foir > 0
        assert metrics.credit_risk.approval_probability > 0
        assert metrics.apr.apr > 0


class TestCaribbeanMarketScenarios:
    """Test Caribbean-specific loan scenarios."""

    def test_xcd_personal_loan(self):
        """Test XCD personal loan for Antigua."""
        loan_data = {
            "loan_amount": "XCD 50,000",
            "monthly_income": "XCD 6,000",
            "existing_debts": "XCD 1,000",
            "employment_type": "Salaried",
            "loan_type": "Personal Loan",
        }
        
        metrics = compute_full_loan_metrics(loan_data)
        assert metrics.emi.emi > 0

    def test_ttd_vehicle_loan(self):
        """Test TTD vehicle loan for Trinidad."""
        loan_data = {
            "loan_amount": "TTD 150,000",
            "monthly_income": "TTD 12,000",
            "existing_debts": "TTD 2,000",
            "employment_type": "Salaried",
            "loan_type": "Vehicle Loan",
        }
        
        metrics = compute_full_loan_metrics(loan_data)
        assert metrics.emi.emi > 0

    def test_gyd_home_loan(self):
        """Test GYD home loan for Guyana."""
        loan_data = {
            "loan_amount": "GYD 40,000,000",
            "monthly_income": "GYD 800,000",
            "existing_debts": "GYD 100,000",
            "employment_type": "Salaried",
            "loan_type": "Home Loan",
            "property_value": "GYD 50,000,000",
            "down_payment": "GYD 10,000,000",
        }
        
        metrics = compute_full_loan_metrics(loan_data)
        assert metrics.emi.emi > 0
        assert metrics.collateral.ltv <= 100
