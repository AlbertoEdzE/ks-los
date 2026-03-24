"""
Loan Calculation Engines for KS-LOS.

This module provides deterministic financial calculation functions for loan origination.
All functions are pure (no side effects) and designed for testability.

Ported from Loan-Navigator-AI's TypeScript implementation with Caribbean market adaptations.
"""

from dataclasses import dataclass, field
from typing import Literal
import math
import re


# =============================================================================
# Data Classes (Type Definitions)
# =============================================================================

@dataclass
class EMIResult:
    """Result of EMI calculation."""
    emi: int
    total_interest: int
    total_repayment: int
    principal: int
    monthly_rate: float
    effective_annual_rate: float


@dataclass
class InterestCalc:
    """Interest calculation breakdown."""
    simple_interest: int
    compound_interest: int
    monthly_reducing_interest: int
    daily_reducing_interest: int
    nominal_rate: float
    effective_rate: float


@dataclass
class AffordabilityMetrics:
    """Affordability assessment metrics."""
    foir: float  # Fixed Obligation to Income Ratio
    dti: float  # Debt-to-Income ratio
    dscr: float  # Debt Service Coverage Ratio
    income_surplus: int
    disposable_income: int
    repayment_burden_ratio: float
    existing_emi_burden: float
    post_loan_emi_burden: float
    total_obligation_ratio: float
    income_stability_signal: Literal["strong", "moderate", "weak", "unknown"]
    leverage_indicator: Literal["low", "moderate", "high", "very-high"]


@dataclass
class CollateralMetrics:
    """Collateral assessment metrics."""
    ltv: float  # Loan-to-Value ratio
    collateral_coverage_ratio: float
    haircut_adjusted_value: int
    pledged_asset_value: int
    security_type: str
    margin_contribution: int
    equity_contribution: int
    unsecured_exposure: int
    secured_exposure: int
    borrower_own_contribution: int


@dataclass
class CreditRiskMetrics:
    """Credit risk assessment metrics."""
    approval_probability: int
    sanction_readiness_score: int
    risk_grade: Literal["A", "B", "C", "D", "E"]
    eligibility_score: int
    policy_deviation_count: int
    compensating_factor_count: int
    delinquency_risk_signal: Literal["low", "moderate", "high", "critical"]
    drop_off_risk_signal: Literal["low", "moderate", "high", "critical"]
    fraud_flags: list[str] = field(default_factory=list)
    deviations: list[str] = field(default_factory=list)
    compensating_factors: list[str] = field(default_factory=list)


@dataclass
class AmortizationRow:
    """Single row in amortization schedule."""
    installment_number: int
    opening_balance: int
    emi_amount: int
    principal_component: int
    interest_component: int
    closing_balance: int
    cumulative_principal: int
    cumulative_interest: int


@dataclass
class AmortizationSchedule:
    """Complete amortization schedule."""
    rows: list[AmortizationRow]
    total_principal: int
    total_interest: int
    total_repayment: int
    effective_rate: float


@dataclass
class APRResult:
    """Annual Percentage Rate calculation result."""
    apr: float
    total_interest_payable: int
    total_repayment_amount: int
    total_fees: int
    total_fees_with_gst: int
    net_cost_of_borrowing: int
    effective_cash_received: int
    fee_breakdown: dict[str, int]


@dataclass
class FeeStructure:
    """Fee structure for loan calculations."""
    processing_fee_percent: float = 1.0
    processing_fee_flat: float = 0.0
    admin_fee: float = 0.0
    documentation_fee: float = 500.0
    valuation_fee: float = 3000.0
    insurance_fee: float = 0.0
    legal_fee: float = 2000.0
    stamp_duty: float = 0.0
    gst_on_fees_percent: float = 18.0


@dataclass
class PrepaymentResult:
    """Prepayment/foreclosure calculation result."""
    pre_closure_amount: int
    foreclosure_amount: int
    foreclosure_charge: int
    part_payment_amount: int
    revised_emi: int
    revised_tenure: int
    interest_saved: int
    emi_reduction: int
    tenure_reduction: int
    total_savings: int


@dataclass
class STPAssessment:
    """Straight-Through Processing eligibility assessment."""
    tier: Literal["stp", "referred", "committee"]
    reasons: list[str]
    document_action: Literal["upload_now", "prepare_list"]
    referral_category: str | None = None


# =============================================================================
# Utility Functions
# =============================================================================

def parse_numeric(val: str | int | float | None) -> float:
    """
    Parse a numeric value from string, int, float, or None.
    
    Handles currency symbols, commas, and whitespace.
    Returns 0 for invalid or None inputs.
    
    Args:
        val: Value to parse (string, int, float, or None)
        
    Returns:
        Parsed numeric value, or 0 if invalid
        
    Examples:
        >>> parse_numeric("$50,000")
        50000.0
        >>> parse_numeric("₹ 1,20,000")
        120000.0
        >>> parse_numeric(None)
        0.0
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    # Remove currency symbols, commas, whitespace, and percentage signs
    cleaned = re.sub(r'[₹$€£,\s%a-zA-Z]', '', str(val)).strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _round(val: float) -> int:
    """Round to nearest integer."""
    return int(round(val))


# =============================================================================
# EMI Calculation Engines
# =============================================================================

def compute_reducing_emi(
    principal: float,
    annual_rate: float,
    tenure_months: int
) -> EMIResult:
    """
    Calculate EMI using reducing balance method.
    
    This is the standard EMI calculation method used by most banks.
    Formula: EMI = P × r × (1+r)^n / ((1+r)^n - 1)
    where P=principal, r=monthly rate, n=tenure in months
    
    Args:
        principal: Loan amount (must be > 0)
        annual_rate: Annual interest rate as percentage (e.g., 10.5 for 10.5%)
        tenure_months: Loan tenure in months (must be > 0)
        
    Returns:
        EMIResult with EMI amount, total interest, and breakdown
        
    Examples:
        >>> result = compute_reducing_emi(1000000, 10.5, 240)
        >>> result.emi > 0
        True
    """
    if principal <= 0 or tenure_months <= 0:
        return EMIResult(
            emi=0, total_interest=0, total_repayment=0,
            principal=0, monthly_rate=0.0, effective_annual_rate=0.0
        )
    
    if annual_rate <= 0:
        # Zero interest loan
        emi = principal / tenure_months
        return EMIResult(
            emi=_round(emi), total_interest=0, total_repayment=_round(principal),
            principal=_round(principal), monthly_rate=0.0, effective_annual_rate=0.0
        )
    
    monthly_rate = annual_rate / 100.0 / 12.0
    n = tenure_months
    
    # EMI formula: P × r × (1+r)^n / ((1+r)^n - 1)
    pow_term = math.pow(1 + monthly_rate, n)
    emi = (principal * monthly_rate * pow_term) / (pow_term - 1)
    
    total_repayment = emi * n
    total_interest = total_repayment - principal
    effective_annual_rate = (math.pow(1 + monthly_rate, 12) - 1) * 100
    
    return EMIResult(
        emi=_round(emi),
        total_interest=_round(total_interest),
        total_repayment=_round(total_repayment),
        principal=_round(principal),
        monthly_rate=monthly_rate,
        effective_annual_rate=round(effective_annual_rate * 100) / 100
    )


def compute_flat_emi(
    principal: float,
    annual_rate: float,
    tenure_months: int
) -> EMIResult:
    """
    Calculate EMI using flat rate method.
    
    In flat rate method, interest is calculated on the original principal
    for the entire tenure, regardless of principal repayment.
    
    Args:
        principal: Loan amount (must be > 0)
        annual_rate: Annual interest rate as percentage
        tenure_months: Loan tenure in months (must be > 0)
        
    Returns:
        EMIResult with EMI amount and breakdown
    """
    if principal <= 0 or tenure_months <= 0:
        return EMIResult(
            emi=0, total_interest=0, total_repayment=0,
            principal=0, monthly_rate=0.0, effective_annual_rate=annual_rate
        )
    
    total_interest = principal * (annual_rate / 100.0) * (tenure_months / 12.0)
    total_repayment = principal + total_interest
    emi = total_repayment / tenure_months
    
    monthly_rate = annual_rate / 100.0 / 12.0
    effective_annual_rate = (math.pow(1 + monthly_rate, 12) - 1) * 100
    
    return EMIResult(
        emi=_round(emi),
        total_interest=_round(total_interest),
        total_repayment=_round(total_repayment),
        principal=_round(principal),
        monthly_rate=monthly_rate,
        effective_annual_rate=round(effective_annual_rate * 100) / 100
    )


def compute_step_up_emi(
    principal: float,
    annual_rate: float,
    tenure_months: int,
    step_percent: float,
    step_interval_months: int
) -> dict:
    """
    Calculate step-up EMI schedule.
    
    Step-up EMI starts with a lower EMI that increases at regular intervals.
    Useful for borrowers expecting income growth.
    
    Args:
        principal: Loan amount
        annual_rate: Annual interest rate as percentage
        tenure_months: Total tenure in months
        step_percent: Percentage increase at each step (e.g., 5 for 5%)
        step_interval_months: Months between each step (e.g., 12 for annual step)
        
    Returns:
        Dictionary with schedule, average EMI, total interest, total repayment
    """
    monthly_rate = annual_rate / 100.0 / 12.0
    base_emi_result = compute_reducing_emi(principal, annual_rate, tenure_months)
    base_emi = base_emi_result.emi
    
    balance = principal
    schedule: list[int] = []
    total_paid = 0.0
    
    for month in range(1, tenure_months + 1):
        if balance <= 0:
            break
        
        # Calculate step index and current EMI
        step_index = (month - 1) // step_interval_months
        current_emi = min(
            base_emi * math.pow(1 + step_percent / 100.0, step_index),
            balance * (1 + monthly_rate)
        )
        
        interest_part = balance * monthly_rate
        principal_part = min(current_emi - interest_part, balance)
        balance -= principal_part
        
        schedule.append(_round(current_emi))
        total_paid += current_emi
    
    return {
        "schedule": schedule,
        "avg_emi": _round(total_paid / len(schedule)) if schedule else 0,
        "total_interest": _round(total_paid - principal),
        "total_repayment": _round(total_paid)
    }


# =============================================================================
# Interest Metrics Engine
# =============================================================================

def compute_interest_metrics(
    principal: float,
    annual_rate: float,
    tenure_months: int
) -> InterestCalc:
    """
    Compute various interest calculation methods for comparison.
    
    Args:
        principal: Loan amount
        annual_rate: Annual interest rate as percentage
        tenure_months: Tenure in months
        
    Returns:
        InterestCalc with simple, compound, monthly reducing, and daily reducing interest
    """
    years = tenure_months / 12.0
    
    # Simple interest: P × r × t
    simple_interest = principal * (annual_rate / 100.0) * years
    
    # Compound interest: P × ((1+r)^t - 1)
    compound_interest = principal * (math.pow(1 + annual_rate / 100.0, years) - 1)
    
    # Monthly reducing interest (from EMI calculation)
    emi_result = compute_reducing_emi(principal, annual_rate, tenure_months)
    monthly_reducing_interest = emi_result.total_interest
    
    # Daily reducing interest (approximation)
    daily_rate = annual_rate / 100.0 / 365.0
    days = tenure_months * 30
    daily_reducing_interest = (
        principal * (math.pow(1 + daily_rate, days) - 1) - principal +
        monthly_reducing_interest * 0.02  # Approximate 2% reduction for daily vs monthly
    )
    
    effective_rate = emi_result.effective_annual_rate
    
    return InterestCalc(
        simple_interest=_round(simple_interest),
        compound_interest=_round(compound_interest),
        monthly_reducing_interest=_round(monthly_reducing_interest),
        daily_reducing_interest=_round(daily_reducing_interest),
        nominal_rate=annual_rate,
        effective_rate=effective_rate
    )


# =============================================================================
# Affordability Engine
# =============================================================================

def compute_affordability(
    monthly_income: float,
    existing_emi_total: float,
    proposed_emi: float,
    co_applicant_income: float = 0.0,
    other_obligations: float = 0.0
) -> AffordabilityMetrics:
    """
    Compute affordability metrics for loan assessment.
    
    Key metrics:
    - FOIR (Fixed Obligation to Income Ratio): Total obligations / gross income
    - DTI (Debt-to-Income): Same as FOIR in this context
    - DSCR (Debt Service Coverage Ratio): Gross income / total obligations
    
    Args:
        monthly_income: Primary applicant's monthly income
        existing_emi_total: Sum of all existing EMI obligations
        proposed_emi: EMI for the proposed loan
        co_applicant_income: Additional income from co-applicant (if any)
        other_obligations: Other monthly financial obligations
        
    Returns:
        AffordabilityMetrics with all calculated ratios and signals
        
    Examples:
        >>> metrics = compute_affordability(10000, 2000, 3000)
        >>> metrics.foir > 0
        True
    """
    gross_income = monthly_income + co_applicant_income
    total_obligations = existing_emi_total + proposed_emi + other_obligations
    
    # Calculate ratios
    foir = (total_obligations / gross_income * 100) if gross_income > 0 else 0.0
    dti = foir  # Same calculation in this context
    dscr = (gross_income / total_obligations) if total_obligations > 0 else (10.0 if gross_income > 0 else 0.0)
    
    income_surplus = _round(gross_income - total_obligations)
    disposable_income = income_surplus
    
    repayment_burden_ratio = (proposed_emi / gross_income * 100) if gross_income > 0 else 0.0
    existing_emi_burden = (existing_emi_total / gross_income * 100) if gross_income > 0 else 0.0
    post_loan_emi_burden = ((existing_emi_total + proposed_emi) / gross_income * 100) if gross_income > 0 else 0.0
    
    # Income stability signal (Caribbean market thresholds in XCD)
    if monthly_income >= 50000:
        income_stability = "strong"
    elif monthly_income >= 25000:
        income_stability = "moderate"
    elif monthly_income > 0:
        income_stability = "weak"
    else:
        income_stability = "unknown"
    
    # Leverage indicator
    if dti > 60:
        leverage = "very-high"
    elif dti > 45:
        leverage = "high"
    elif dti > 30:
        leverage = "moderate"
    else:
        leverage = "low"
    
    return AffordabilityMetrics(
        foir=round(foir * 100) / 100,
        dti=round(dti * 100) / 100,
        dscr=round(dscr * 100) / 100,
        income_surplus=income_surplus,
        disposable_income=disposable_income,
        repayment_burden_ratio=round(repayment_burden_ratio * 100) / 100,
        existing_emi_burden=round(existing_emi_burden * 100) / 100,
        post_loan_emi_burden=round(post_loan_emi_burden * 100) / 100,
        total_obligation_ratio=round(foir * 100) / 100,
        income_stability_signal=income_stability,
        leverage_indicator=leverage
    )


# =============================================================================
# Collateral Engine
# =============================================================================

def compute_collateral_metrics(
    loan_amount: float,
    collateral_value: float,
    haircut_percent: float = 15.0,
    security_type: str = "property",
    down_payment: float = 0.0
) -> CollateralMetrics:
    """
    Compute collateral adequacy metrics.
    
    Args:
        loan_amount: Requested loan amount
        collateral_value: Appraised value of collateral
        haircut_percent: Haircut percentage applied to collateral value
        security_type: Type of collateral (property, vehicle, etc.)
        down_payment: Borrower's down payment (if any)
        
    Returns:
        CollateralMetrics with LTV, coverage ratios, and exposure analysis
    """
    # Loan-to-Value ratio
    ltv = (loan_amount / collateral_value * 100) if collateral_value > 0 else 100.0
    
    # Haircut-adjusted collateral value
    haircut_adjusted_value = collateral_value * (1 - haircut_percent / 100.0)
    
    # Collateral coverage ratio
    collateral_coverage_ratio = (haircut_adjusted_value / loan_amount) if loan_amount > 0 else 0.0
    
    # Margin and equity contributions
    margin_contribution = collateral_value - loan_amount
    equity_contribution = down_payment if down_payment > 0 else margin_contribution
    
    # Secured vs unsecured exposure
    unsecured_exposure = max(0, loan_amount - haircut_adjusted_value) if collateral_value > 0 else loan_amount
    secured_exposure = loan_amount - unsecured_exposure
    
    return CollateralMetrics(
        ltv=round(ltv * 100) / 100,
        collateral_coverage_ratio=round(collateral_coverage_ratio * 100) / 100,
        haircut_adjusted_value=_round(haircut_adjusted_value),
        pledged_asset_value=_round(collateral_value),
        security_type=security_type,
        margin_contribution=_round(margin_contribution),
        equity_contribution=_round(equity_contribution),
        unsecured_exposure=_round(unsecured_exposure),
        secured_exposure=_round(secured_exposure),
        borrower_own_contribution=_round(equity_contribution)
    )


# =============================================================================
# Credit Risk Engine
# =============================================================================

def compute_credit_risk(
    affordability: AffordabilityMetrics,
    collateral: CollateralMetrics,
    credit_score: int,
    completeness_score: int,
    loan_type: str,
    has_collateral: bool
) -> CreditRiskMetrics:
    """
    Compute credit risk assessment with approval probability.
    
    This is a deterministic rule-based model that combines:
    - Credit score analysis
    - Affordability assessment (FOIR)
    - Collateral adequacy (LTV)
    - Application completeness
    
    Args:
        affordability: Pre-computed affordability metrics
        collateral: Pre-computed collateral metrics
        credit_score: Credit bureau score (300-850 scale)
        completeness_score: Application completeness percentage (0-100)
        loan_type: Type of loan (for context)
        has_collateral: Whether collateral is provided
        
    Returns:
        CreditRiskMetrics with approval probability, risk grade, and factors
    """
    approval_prob = 50.0
    deviations: list[str] = []
    compensating: list[str] = []
    
    # Credit score factor
    if credit_score >= 750:
        approval_prob += 15
        compensating.append(f"Excellent credit bureau rating ({credit_score})")
    elif credit_score >= 700:
        approval_prob += 8
        compensating.append(f"Good credit bureau rating ({credit_score})")
    elif credit_score >= 650:
        pass  # Neutral
    elif credit_score > 0:
        approval_prob -= 15
        deviations.append(f"Below-average credit bureau rating ({credit_score})")
    
    # FOIR factor
    if affordability.foir <= 40:
        approval_prob += 10
        compensating.append(f"Healthy FOIR at {affordability.foir}%")
    elif affordability.foir <= 50:
        approval_prob += 3
    elif affordability.foir <= 60:
        approval_prob -= 5
        deviations.append(f"Elevated FOIR at {affordability.foir}%")
    else:
        approval_prob -= 15
        deviations.append(f"Critical FOIR at {affordability.foir}% exceeds policy limit")
    
    # LTV factor (if collateral exists)
    if has_collateral:
        if collateral.ltv <= 75:
            approval_prob += 8
            compensating.append(f"Conservative LTV at {collateral.ltv}%")
        elif collateral.ltv <= 85:
            approval_prob += 3
        elif collateral.ltv > 90:
            approval_prob -= 10
            deviations.append(f"High LTV at {collateral.ltv}% exceeds comfort level")
    
    # Completeness factor
    if completeness_score >= 80:
        approval_prob += 5
        compensating.append("Well-documented application")
    elif completeness_score < 50:
        approval_prob -= 10
        deviations.append(f"Application significantly incomplete ({completeness_score}%)")
    
    # Income stability factor
    if affordability.income_stability_signal == "strong":
        approval_prob += 5
        compensating.append("Strong income stability")
    elif affordability.income_stability_signal == "weak":
        approval_prob -= 5
        deviations.append("Weak income stability")
    
    # Clamp approval probability to [5, 95]
    approval_prob = max(5, min(95, approval_prob))
    
    # Risk grade assignment
    if approval_prob >= 80:
        risk_grade = "A"
    elif approval_prob >= 65:
        risk_grade = "B"
    elif approval_prob >= 45:
        risk_grade = "C"
    elif approval_prob >= 25:
        risk_grade = "D"
    else:
        risk_grade = "E"
    
    # Sanction readiness score
    sanction_readiness = completeness_score * 0.3 + approval_prob * 0.5
    if affordability.foir <= 50:
        sanction_readiness += 20
    elif affordability.foir <= 60:
        sanction_readiness += 10
    sanction_readiness_score = min(100, max(0, _round(sanction_readiness)))
    
    # Delinquency risk signal
    if affordability.foir > 60 or credit_score < 600:
        delinquency_risk = "critical"
    elif affordability.foir > 50 or credit_score < 650:
        delinquency_risk = "high"
    elif affordability.foir > 40 or credit_score < 700:
        delinquency_risk = "moderate"
    else:
        delinquency_risk = "low"
    
    # Drop-off risk signal
    if completeness_score < 30:
        drop_off_risk = "critical"
    elif completeness_score < 50:
        drop_off_risk = "high"
    elif completeness_score < 70:
        drop_off_risk = "moderate"
    else:
        drop_off_risk = "low"
    
    return CreditRiskMetrics(
        approval_probability=_round(approval_prob),
        sanction_readiness_score=sanction_readiness_score,
        risk_grade=risk_grade,
        eligibility_score=_round(approval_prob * 0.8 + completeness_score * 0.2),
        policy_deviation_count=len(deviations),
        compensating_factor_count=len(compensating),
        delinquency_risk_signal=delinquency_risk,
        drop_off_risk_signal=drop_off_risk,
        fraud_flags=[],
        deviations=deviations,
        compensating_factors=compensating
    )


def compute_file_completeness(loan_data: dict) -> int:
    """
    Compute application file completeness score.
    
    Args:
        loan_data: Dictionary containing loan application fields
        
    Returns:
        Completeness score as percentage (0-100)
    """
    fields = [
        "borrower_name", "borrower_email", "borrower_phone", "loan_type", "loan_amount",
        "interest_rate", "tenure", "purpose", "employment_type", "monthly_income",
        "existing_debts", "credit_score", "collateral", "down_payment", "property_value", "ltv"
    ]
    
    excluded_values = {
        "", None, "Not specified", "Not provided", "Not set",
        "Not available", "Not calculated", "None", "None disclosed"
    }
    
    filled_count = 0
    for field_name in fields:
        value = loan_data.get(field_name)
        if value not in excluded_values:
            filled_count += 1
    
    return _round((filled_count / len(fields)) * 100)


# =============================================================================
# Amortization Engine
# =============================================================================

def generate_amortization_schedule(
    principal: float,
    annual_rate: float,
    tenure_months: int,
    emi_type: Literal["reducing", "flat"] = "reducing"
) -> AmortizationSchedule:
    """
    Generate complete amortization schedule for a loan.
    
    Args:
        principal: Loan amount
        annual_rate: Annual interest rate as percentage
        tenure_months: Tenure in months
        emi_type: "reducing" (default) or "flat"
        
    Returns:
        AmortizationSchedule with month-by-month breakdown
    """
    if principal <= 0 or tenure_months <= 0:
        return AmortizationSchedule(
            rows=[], total_principal=0, total_interest=0,
            total_repayment=0, effective_rate=0.0
        )
    
    rows: list[AmortizationRow] = []
    total_interest = 0.0
    cumulative_principal = 0.0
    cumulative_interest = 0.0
    
    if emi_type == "flat":
        # Flat rate method
        total_int = principal * (annual_rate / 100.0) * (tenure_months / 12.0)
        emi = (principal + total_int) / tenure_months
        monthly_principal = principal / tenure_months
        monthly_interest = total_int / tenure_months
        balance = principal
        
        for i in range(1, tenure_months + 1):
            principal_part = balance if i == tenure_months else monthly_principal
            cumulative_principal += principal_part
            cumulative_interest += monthly_interest
            balance -= principal_part
            
            rows.append(AmortizationRow(
                installment_number=i,
                opening_balance=_round(balance + principal_part),
                emi_amount=_round(emi),
                principal_component=_round(principal_part),
                interest_component=_round(monthly_interest),
                closing_balance=_round(max(0, balance)),
                cumulative_principal=_round(cumulative_principal),
                cumulative_interest=_round(cumulative_interest)
            ))
        
        total_interest = total_int
    
    else:
        # Reducing balance method
        monthly_rate = annual_rate / 100.0 / 12.0
        
        if monthly_rate > 0:
            pow_term = math.pow(1 + monthly_rate, tenure_months)
            emi = (principal * monthly_rate * pow_term) / (pow_term - 1)
        else:
            emi = principal / tenure_months
        
        balance = principal
        for i in range(1, tenure_months + 1):
            interest_part = balance * monthly_rate
            
            if i == tenure_months:
                # Final installment - pay off remaining balance
                principal_part = balance
                actual_emi = principal_part + interest_part
                cumulative_principal += principal_part
                cumulative_interest += interest_part
                total_interest += interest_part
                
                rows.append(AmortizationRow(
                    installment_number=i,
                    opening_balance=_round(balance),
                    emi_amount=_round(actual_emi),
                    principal_component=_round(principal_part),
                    interest_component=_round(interest_part),
                    closing_balance=0,
                    cumulative_principal=_round(cumulative_principal),
                    cumulative_interest=_round(cumulative_interest)
                ))
                break
            
            principal_part = emi - interest_part
            balance -= principal_part
            cumulative_principal += principal_part
            cumulative_interest += interest_part
            total_interest += interest_part
            
            rows.append(AmortizationRow(
                installment_number=i,
                opening_balance=_round(balance + principal_part),
                emi_amount=_round(emi),
                principal_component=_round(principal_part),
                interest_component=_round(interest_part),
                closing_balance=_round(max(0, balance)),
                cumulative_principal=_round(cumulative_principal),
                cumulative_interest=_round(cumulative_interest)
            ))
    
    effective_rate = (math.pow(1 + annual_rate / 100.0 / 12, 12) - 1) * 100 if principal > 0 else 0.0
    
    return AmortizationSchedule(
        rows=rows,
        total_principal=_round(principal),
        total_interest=_round(total_interest),
        total_repayment=_round(principal + total_interest),
        effective_rate=round(effective_rate * 100) / 100
    )


def compute_broken_period_interest(
    principal: float,
    annual_rate: float,
    days: int
) -> int:
    """
    Compute interest for broken period (less than a month).
    
    Args:
        principal: Outstanding principal
        annual_rate: Annual interest rate
        days: Number of days
        
    Returns:
        Interest amount for the broken period
    """
    return _round(principal * (annual_rate / 100.0 / 365) * days)


def compute_moratorium_impact(
    principal: float,
    annual_rate: float,
    moratorium_months: int
) -> dict:
    """
    Compute impact of moratorium (payment holiday) on loan.
    
    During moratorium, interest accrues and is capitalized (added to principal).
    
    Args:
        principal: Original principal
        annual_rate: Annual interest rate
        moratorium_months: Number of months in moratorium
        
    Returns:
        Dictionary with accrued_interest and new_principal
    """
    monthly_rate = annual_rate / 100.0 / 12.0
    balance = principal
    accrued = 0.0
    
    for _ in range(moratorium_months):
        interest = balance * monthly_rate
        accrued += interest
        balance += interest  # Capitalize interest
    
    return {
        "accrued_interest": _round(accrued),
        "new_principal": _round(balance)
    }


# =============================================================================
# Fee and APR Engine
# =============================================================================

def compute_total_fees(
    principal: float,
    fees: FeeStructure | None = None
) -> dict:
    """
    Compute total fees for a loan.
    
    Args:
        principal: Loan amount
        fees: Fee structure (uses defaults if not provided)
        
    Returns:
        Dictionary with total, total_with_gst, and breakdown
    """
    if fees is None:
        fees = FeeStructure()
    
    # Processing fee: higher of percent or flat
    processing_fee = max(
        fees.processing_fee_flat,
        principal * (fees.processing_fee_percent / 100.0)
    )
    
    breakdown: dict[str, int] = {
        "processing_fee": _round(processing_fee),
        "admin_fee": _round(fees.admin_fee),
        "documentation_fee": _round(fees.documentation_fee),
        "valuation_fee": _round(fees.valuation_fee),
        "insurance_fee": _round(fees.insurance_fee),
        "legal_fee": _round(fees.legal_fee),
        "stamp_duty": _round(fees.stamp_duty),
    }
    
    subtotal = sum(breakdown.values())
    gst = _round(subtotal * (fees.gst_on_fees_percent / 100.0))
    breakdown["gst"] = gst
    
    return {
        "total": subtotal,
        "total_with_gst": subtotal + gst,
        "breakdown": breakdown
    }


def compute_apr(
    principal: float,
    annual_rate: float,
    tenure_months: int,
    fees: FeeStructure | None = None
) -> APRResult:
    """
    Compute Annual Percentage Rate (APR) including fees.
    
    APR represents the true cost of borrowing, including all fees.
    Uses binary search to find the rate that equates cash flows.
    
    Args:
        principal: Loan amount
        annual_rate: Nominal annual interest rate
        tenure_months: Tenure in months
        fees: Fee structure (uses defaults if not provided)
        
    Returns:
        APRResult with APR and cost breakdown
    """
    emi_result = compute_reducing_emi(principal, annual_rate, tenure_months)
    fee_info = compute_total_fees(principal, fees)
    
    total_fees = fee_info["total"]
    total_fees_with_gst = fee_info["total_with_gst"]
    
    # Effective cash received (principal minus upfront fees)
    effective_cash_received = principal - total_fees_with_gst
    
    total_repayment = emi_result.total_repayment
    total_interest = emi_result.total_interest
    net_cost = total_interest + total_fees_with_gst
    
    # Binary search for APR
    apr = annual_rate
    if effective_cash_received > 0 and tenure_months > 0:
        effective_monthly_payment = total_repayment / tenure_months
        
        lo = annual_rate
        hi = annual_rate * 3
        
        for _ in range(50):  # Binary search iterations
            mid = (lo + hi) / 2
            r = mid / 100.0 / 12
            
            if r > 0:
                pv = effective_monthly_payment * (1 - math.pow(1 + r, -tenure_months)) / r
            else:
                pv = effective_monthly_payment * tenure_months
            
            if pv > effective_cash_received:
                lo = mid
            else:
                hi = mid
        
        apr = round(((lo + hi) / 2) * 100) / 100
    
    return APRResult(
        apr=apr,
        total_interest_payable=_round(total_interest),
        total_repayment_amount=_round(total_repayment),
        total_fees=_round(total_fees),
        total_fees_with_gst=_round(total_fees_with_gst),
        net_cost_of_borrowing=_round(net_cost),
        effective_cash_received=_round(effective_cash_received),
        fee_breakdown=fee_info["breakdown"]
    )


# =============================================================================
# Prepayment Engine
# =============================================================================

def compute_part_payment_impact(
    outstanding_principal: float,
    annual_rate: float,
    remaining_tenure_months: int,
    part_payment_amount: float,
    option: Literal["reduce-emi", "reduce-tenure"] = "reduce-tenure",
    foreclosure_charge_percent: float = 0.0
) -> PrepaymentResult:
    """
    Compute impact of part-payment on loan.
    
    Args:
        outstanding_principal: Current outstanding principal
        annual_rate: Annual interest rate
        remaining_tenure_months: Remaining tenure in months
        part_payment_amount: Amount to prepay
        option: "reduce-emi" or "reduce-tenure"
        foreclosure_charge_percent: Charge for prepayment (if any)
        
    Returns:
        PrepaymentResult with revised terms and savings
    """
    if part_payment_amount <= 0 or outstanding_principal <= 0:
        current_emi = compute_reducing_emi(outstanding_principal, annual_rate, remaining_tenure_months)
        return PrepaymentResult(
            pre_closure_amount=0, foreclosure_amount=0, foreclosure_charge=0,
            part_payment_amount=0, revised_emi=current_emi.emi,
            revised_tenure=remaining_tenure_months, interest_saved=0,
            emi_reduction=0, tenure_reduction=0, total_savings=0
        )
    
    original_emi_result = compute_reducing_emi(outstanding_principal, annual_rate, remaining_tenure_months)
    original_emi = original_emi_result.emi
    
    new_principal = max(0, outstanding_principal - part_payment_amount)
    
    # Full pre-closure
    if new_principal == 0:
        charge = _round(outstanding_principal * (foreclosure_charge_percent / 100.0))
        return PrepaymentResult(
            pre_closure_amount=outstanding_principal + charge,
            foreclosure_amount=outstanding_principal + charge,
            foreclosure_charge=charge,
            part_payment_amount=_round(part_payment_amount),
            revised_emi=0,
            revised_tenure=0,
            interest_saved=original_emi_result.total_interest,
            emi_reduction=original_emi,
            tenure_reduction=remaining_tenure_months,
            total_savings=original_emi_result.total_interest - charge
        )
    
    # Partial prepayment
    if option == "reduce-emi":
        revised_tenure = remaining_tenure_months
        new_emi_result = compute_reducing_emi(new_principal, annual_rate, remaining_tenure_months)
        revised_emi = new_emi_result.emi
    else:  # reduce-tenure
        revised_emi = original_emi
        monthly_rate = annual_rate / 100.0 / 12.0
        
        if monthly_rate > 0 and revised_emi > new_principal * monthly_rate:
            revised_tenure = math.ceil(
                math.log(revised_emi / (revised_emi - new_principal * monthly_rate)) /
                math.log(1 + monthly_rate)
            )
        else:
            revised_tenure = math.ceil(new_principal / revised_emi)
    
    new_emi_result = compute_reducing_emi(new_principal, annual_rate, revised_tenure)
    interest_saved = original_emi_result.total_interest - new_emi_result.total_interest
    emi_reduction = original_emi - (revised_emi if option == "reduce-emi" else original_emi)
    tenure_reduction = remaining_tenure_months - revised_tenure
    
    return PrepaymentResult(
        pre_closure_amount=0,
        foreclosure_amount=0,
        foreclosure_charge=0,
        part_payment_amount=_round(part_payment_amount),
        revised_emi=revised_emi if option == "reduce-emi" else original_emi,
        revised_tenure=revised_tenure,
        interest_saved=_round(max(0, interest_saved)),
        emi_reduction=_round(max(0, emi_reduction)),
        tenure_reduction=max(0, tenure_reduction),
        total_savings=_round(max(0, interest_saved))
    )


def compute_foreclosure(
    outstanding_principal: float,
    annual_rate: float,
    remaining_tenure_months: int,
    foreclosure_charge_percent: float = 2.0,
    accrued_interest_days: int = 0
) -> dict:
    """
    Compute foreclosure (full pre-closure) amount.
    
    Args:
        outstanding_principal: Current outstanding principal
        annual_rate: Annual interest rate
        remaining_tenure_months: Remaining tenure
        foreclosure_charge_percent: Charge percentage for foreclosure
        accrued_interest_days: Days of accrued interest
        
    Returns:
        Dictionary with foreclosure amount and breakdown
    """
    charge = _round(outstanding_principal * (foreclosure_charge_percent / 100.0))
    accrued = compute_broken_period_interest(outstanding_principal, annual_rate, accrued_interest_days)
    
    emi_result = compute_reducing_emi(outstanding_principal, annual_rate, remaining_tenure_months)
    interest_saved = _round(emi_result.total_interest - accrued)
    
    return {
        "foreclosure_amount": outstanding_principal + charge + accrued,
        "foreclosure_charge": charge,
        "accrued_interest": accrued,
        "interest_saved": max(0, interest_saved)
    }


def compute_refinance_comparison(
    outstanding_principal: float,
    current_rate: float,
    new_rate: float,
    remaining_tenure_months: int,
    switching_cost: float = 0.0
) -> dict:
    """
    Compare refinancing options.
    
    Args:
        outstanding_principal: Current outstanding balance
        current_rate: Current interest rate
        new_rate: New loan interest rate
        remaining_tenure_months: Remaining tenure
        switching_cost: Cost to switch (processing fees, etc.)
        
    Returns:
        Dictionary with comparison metrics
    """
    current_emi_result = compute_reducing_emi(outstanding_principal, current_rate, remaining_tenure_months)
    new_emi_result = compute_reducing_emi(outstanding_principal, new_rate, remaining_tenure_months)
    
    emi_saving = current_emi_result.emi - new_emi_result.emi
    total_interest_saving = current_emi_result.total_interest - new_emi_result.total_interest
    net_saving = total_interest_saving - switching_cost
    
    break_even_months = math.ceil(switching_cost / emi_saving) if emi_saving > 0 else 0
    
    return {
        "current_emi": current_emi_result.emi,
        "new_emi": new_emi_result.emi,
        "emi_saving": _round(emi_saving),
        "total_interest_saving": _round(total_interest_saving),
        "net_saving": _round(net_saving),
        "break_even_months": break_even_months
    }


# =============================================================================
# STP Eligibility Engine
# =============================================================================

# STP thresholds in USD equivalent
STP_THRESHOLDS_USD = {
    "max_personal_loan_amount": 500000,
    "max_vehicle_loan_amount": 750000,
    "max_home_loan_amount": 2000000,
    "max_business_loan_amount": 300000,
    "max_foir": 0.40,
    "referred_foir_ceiling": 0.55,
    "min_monthly_income": 3000,
}

# Currency patterns with conversion rates to USD
CURRENCY_PATTERNS: list[tuple[re.Pattern, float]] = [
    (re.compile(r'₹|inr|rs\.?\s', re.IGNORECASE), 83.0),
    (re.compile(r'€|eur', re.IGNORECASE), 0.92),
    (re.compile(r'£|gbp', re.IGNORECASE), 0.79),
    (re.compile(r'ttd|tt\$', re.IGNORECASE), 6.8),
    (re.compile(r'gyd|gy\$', re.IGNORECASE), 209.0),
    (re.compile(r'jmd|j\$', re.IGNORECASE), 155.0),
    (re.compile(r'bbd|bds\$', re.IGNORECASE), 2.0),
    (re.compile(r'bsd', re.IGNORECASE), 1.0),
    (re.compile(r'xcd|ec\$', re.IGNORECASE), 2.7),
    (re.compile(r'us\$|usd', re.IGNORECASE), 1.0),
    (re.compile(r'\$', re.IGNORECASE), 1.0),
]


def detect_currency_rate(amount_str: str | None) -> float:
    """
    Detect currency from amount string and return conversion rate to USD.
    
    Args:
        amount_str: Amount string (may contain currency symbols)
        
    Returns:
        Conversion rate to USD (1.0 if USD or unknown)
    """
    if not amount_str:
        return 1.0
    
    s = amount_str.strip()
    for pattern, rate in CURRENCY_PATTERNS:
        if pattern.search(s):
            return rate
    return 1.0


def to_usd_equivalent(local_amount: float, currency_rate: float) -> float:
    """
    Convert local currency amount to USD equivalent.
    
    Args:
        local_amount: Amount in local currency
        currency_rate: Conversion rate to USD
        
    Returns:
        USD equivalent amount
    """
    return local_amount / currency_rate if currency_rate > 0 else local_amount


def assess_stp_eligibility(loan_data: dict) -> STPAssessment:
    """
    Assess Straight-Through Processing (STP) eligibility.
    
    STP allows automatic approval without manual intervention for low-risk applications.
    
    Args:
        loan_data: Dictionary with loan application fields:
            - loan_type: Type of loan
            - loan_amount: Requested amount (may include currency symbol)
            - monthly_income: Monthly income
            - existing_debts: Existing monthly obligations
            - employment_type: Employment status
            - property_value: Property value (for home loans)
            - down_payment: Down payment amount
            
    Returns:
        STPAssessment with tier, reasons, and document action
        
    Examples:
        >>> assessment = assess_stp_eligibility({
        ...     "loan_type": "Personal Loan",
        ...     "loan_amount": "$50,000",
        ...     "monthly_income": "$5,000",
        ...     "existing_debts": "$500",
        ...     "employment_type": "Salaried"
        ... })
        >>> assessment.tier in ["stp", "referred", "committee"]
        True
    """
    reasons: list[str] = []
    tier: Literal["stp", "referred", "committee"] = "stp"
    referral_category: str | None = None
    
    # Parse inputs
    amount = parse_numeric(loan_data.get("loan_amount", "0"))
    income = parse_numeric(loan_data.get("monthly_income", "0"))
    debts = parse_numeric(loan_data.get("existing_debts", "0"))
    loan_type = (loan_data.get("loan_type", "") or "").lower()
    employment = (loan_data.get("employment_type", "") or "").lower()
    
    # Currency detection and USD conversion
    currency_rate = detect_currency_rate(loan_data.get("loan_amount"))
    amount_usd = to_usd_equivalent(amount, currency_rate)
    
    income_currency_rate = detect_currency_rate(loan_data.get("monthly_income"))
    income_usd = to_usd_equivalent(income, income_currency_rate)
    
    # Calculate EMI for FOIR
    rate = 7.0 if "home" in loan_type or "mortgage" in loan_type else (8.5 if "vehicle" in loan_type else 12.0)
    tenure_months = 300 if "home" in loan_type or "mortgage" in loan_type else (84 if "vehicle" in loan_type else 60)
    
    emi = compute_reducing_emi(amount, rate, tenure_months).emi if amount > 0 else 0
    total_obligations = emi + debts
    foir = total_obligations / income if income > 0 else 0.0
    
    # Check employment type
    if "self" in employment or "contractor" in employment or "freelance" in employment:
        reasons.append("Self-employed or contractor — requires income verification by officer")
        tier = "referred"
        referral_category = "income_verification"
    
    # Check loan type
    if "business" in loan_type:
        reasons.append("Business loan — requires financial assessment and business viability review")
        tier = "referred"
        referral_category = referral_category or "business_review"
    
    # Check amount thresholds
    amount_threshold_usd = STP_THRESHOLDS_USD["max_personal_loan_amount"]
    if "home" in loan_type or "mortgage" in loan_type or "property" in loan_type:
        amount_threshold_usd = STP_THRESHOLDS_USD["max_home_loan_amount"]
    elif "vehicle" in loan_type or "car" in loan_type or "auto" in loan_type:
        amount_threshold_usd = STP_THRESHOLDS_USD["max_vehicle_loan_amount"]
    elif "business" in loan_type:
        amount_threshold_usd = STP_THRESHOLDS_USD["max_business_loan_amount"]
    
    if amount_usd > amount_threshold_usd:
        reasons.append(f"Loan amount exceeds standard processing limit for {loan_data.get('loan_type', 'loan')}")
        tier = "referred" if tier == "stp" else tier
        referral_category = referral_category or "high_value"
    
    if amount_usd > amount_threshold_usd * 2:
        reasons.append("Amount significantly above threshold — committee approval required")
        tier = "committee"
        referral_category = "committee_review"
    
    # Check FOIR
    if income > 0 and foir > STP_THRESHOLDS_USD["referred_foir_ceiling"]:
        reasons.append("Monthly obligations exceed 55% of income — affordability review needed")
        if tier != "committee":
            tier = "referred"
        referral_category = referral_category or "affordability_concern"
    elif income > 0 and foir > STP_THRESHOLDS_USD["max_foir"]:
        reasons.append("Monthly obligations between 40-55% of income — officer review recommended")
        if tier == "stp":
            tier = "referred"
        referral_category = referral_category or "affordability_review"
    
    # Check minimum income
    min_income_local = 500 * income_currency_rate if income_currency_rate > 10 else STP_THRESHOLDS_USD["min_monthly_income"]
    if income > 0 and income < min_income_local:
        reasons.append("Income below standard threshold — additional assessment needed")
        if tier == "stp":
            tier = "referred"
        referral_category = referral_category or "income_verification"
    
    # Check LTV for home loans
    if "home" in loan_type or "mortgage" in loan_type:
        prop_value = parse_numeric(loan_data.get("property_value", "0"))
        dp = parse_numeric(loan_data.get("down_payment", "0"))
        
        if prop_value > 0 and amount > 0:
            ltv = amount / prop_value
            if ltv > 0.90:
                reasons.append("Loan-to-value ratio above 90% — higher risk, officer review needed")
                if tier == "stp":
                    tier = "referred"
                referral_category = referral_category or "high_ltv"
    
    return STPAssessment(
        tier=tier,
        reasons=reasons,
        document_action="upload_now" if tier == "stp" else "prepare_list",
        referral_category=referral_category
    )


# =============================================================================
# Full Loan Metrics Snapshot
# =============================================================================

@dataclass
class LoanMetricsSnapshot:
    """Complete loan metrics snapshot."""
    loan_id: str | None
    computed_at: str
    emi: EMIResult
    affordability: AffordabilityMetrics
    collateral: CollateralMetrics
    credit_risk: CreditRiskMetrics
    apr: APRResult


def compute_full_loan_metrics(
    loan_data: dict,
    fees: FeeStructure | None = None
) -> LoanMetricsSnapshot:
    """
    Compute complete loan metrics snapshot.
    
    This is the main entry point for loan assessment, combining all engines.
    
    Args:
        loan_data: Dictionary with loan application fields
        fees: Fee structure (uses defaults if not provided)
        
    Returns:
        LoanMetricsSnapshot with all calculated metrics
    """
    from datetime import datetime, timezone
    
    principal = parse_numeric(loan_data.get("loan_amount", "0"))
    rate_str = loan_data.get("interest_rate", "10")
    rate = parse_numeric(rate_str) if rate_str else 10.0
    
    tenure_str = loan_data.get("tenure", "240")
    tenure_months = parse_numeric(tenure_str)
    if "year" in str(tenure_str).lower():
        tenure_months = parse_numeric(tenure_str) * 12
    if tenure_months <= 0:
        tenure_months = 240
    
    effective_rate = rate if rate > 0 else 10.0
    
    # EMI calculation
    emi_result = compute_reducing_emi(principal, effective_rate, tenure_months)
    
    # Affordability
    monthly_income = parse_numeric(loan_data.get("monthly_income", "0"))
    existing_debts = parse_numeric(loan_data.get("existing_debts", "0"))
    affordability = compute_affordability(monthly_income, existing_debts, emi_result.emi)
    
    # Collateral
    property_value = parse_numeric(loan_data.get("property_value", "0"))
    down_payment = parse_numeric(loan_data.get("down_payment", "0"))
    collateral_value = property_value if property_value > 0 else parse_numeric(loan_data.get("collateral", "0"))
    has_collateral = collateral_value > 0
    collateral = compute_collateral_metrics(
        principal, collateral_value, 15.0,
        loan_data.get("loan_type", "property"), down_payment
    )
    
    # Credit risk
    credit_score = int(parse_numeric(loan_data.get("credit_score", "0")))
    completeness = compute_file_completeness(loan_data)
    credit_risk = compute_credit_risk(
        affordability, collateral,
        credit_score if credit_score > 0 else 700,
        completeness,
        loan_data.get("loan_type", ""),
        has_collateral
    )
    
    # APR
    apr_result = compute_apr(principal, effective_rate, tenure_months, fees)
    
    return LoanMetricsSnapshot(
        loan_id=loan_data.get("id"),
        computed_at=datetime.now(timezone.utc).isoformat(),
        emi=emi_result,
        affordability=affordability,
        collateral=collateral,
        credit_risk=credit_risk,
        apr=apr_result
    )
