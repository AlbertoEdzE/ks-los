"""
Caribbean Credit Bureau Integration.

This module provides a simulated credit bureau integration for Caribbean markets.
In production, this would connect to real bureaus (EveryData, CCBL, CreditInfo Jamaica).

For demo/development, it generates realistic bureau reports based on applicant data.
"""

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

BureauGrade = Literal["A", "B", "C", "D", "E"]
RiskLevel = Literal["low", "moderate", "elevated", "high"]


class BureauReport(Dict[str, Any]):
    """Credit bureau report structure."""
    pass


# =============================================================================
# Bureau Names (Caribbean)
# =============================================================================

BUREAU_NAMES = [
    "CariCRIS",
    "CRIF Caribbean",
    "TransUnion Caribbean",
    "Creditinfo Caribbean",
    "EveryData ECCU",
]


# =============================================================================
# Helper Functions
# =============================================================================

def select_bureau(region: Optional[str] = None) -> str:
    """
    Select appropriate bureau based on region.
    
    Args:
        region: Region hint (e.g., 'Guyana', 'Trinidad', 'Jamaica')
        
    Returns:
        Bureau name
    """
    if region:
        region_lower = region.lower()
        if 'guyan' in region_lower or 'gyd' in region_lower:
            return "Creditinfo Caribbean"
        if 'trinidad' in region_lower or 'tobago' in region_lower or 'ttd' in region_lower:
            return "TransUnion Caribbean"
        if 'jamaica' in region_lower or 'jmd' in region_lower:
            return "CariCRIS"
    
    return random.choice(BUREAU_NAMES)


def generate_report_reference() -> str:
    """
    Generate unique report reference number.
    
    Returns:
        Reference string (e.g., 'CBR-20260323-ABC123')
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d')
    random_suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
    return f"CBR-{timestamp}-{random_suffix}"


def compute_base_score(profile: Dict[str, Any]) -> int:
    """
    Compute base credit score from profile data.
    
    Args:
        profile: Applicant profile data
        
    Returns:
        Credit score (300-850)
    """
    score = 650  # Base score
    
    # Extract profile data
    monthly_income = float(profile.get('monthlyIncome', 0) or 0)
    existing_debts = float(profile.get('existingDebts', 0) or 0)
    loan_amount = float(profile.get('loanAmount', 0) or 0)
    employment_type = (profile.get('employmentType') or '').lower()
    
    # DTI factor
    if monthly_income > 0:
        dti = (existing_debts / monthly_income) * 100
        if dti < 20:
            score += 80
        elif dti < 30:
            score += 50
        elif dti < 40:
            score += 20
        elif dti < 50:
            score -= 20
        else:
            score -= 60
    
    # Employment factor
    if 'salaried' in employment_type or 'employed' in employment_type or 'permanent' in employment_type:
        score += 40
    elif 'self' in employment_type or 'business' in employment_type or 'entrepreneur' in employment_type:
        score += 10
    elif 'contract' in employment_type or 'freelance' in employment_type or 'gig' in employment_type:
        score -= 10
    else:
        score -= 20
    
    # Affordability factor
    if monthly_income > 0:
        affordability = loan_amount / (monthly_income * 12)
        if affordability < 1:
            score += 30
        elif affordability < 2:
            score += 15
        elif affordability < 3:
            score += 0
        elif affordability < 5:
            score -= 15
        else:
            score -= 35
    
    # Income level factor (Caribbean thresholds in local currency)
    if monthly_income >= 200000:  # High income
        score += 20
    elif monthly_income >= 100000:
        score += 10
    elif monthly_income >= 50000:
        score += 5
    
    # Add variance for realism
    variance = random.randint(-15, 15)
    score += variance
    
    # Clamp to valid range
    return max(300, min(850, round(score)))


def score_to_grade(score: int) -> tuple[BureauGrade, str]:
    """
    Convert credit score to grade and label.
    
    Args:
        score: Credit score (300-850)
        
    Returns:
        Tuple of (grade, label)
    """
    if score >= 750:
        return 'A', 'Excellent'
    elif score >= 700:
        return 'B', 'Good'
    elif score >= 650:
        return 'C', 'Fair'
    elif score >= 550:
        return 'D', 'Below Average'
    else:
        return 'E', 'Poor'


def score_to_risk(score: int) -> RiskLevel:
    """
    Convert credit score to risk level.
    
    Args:
        score: Credit score (300-850)
        
    Returns:
        Risk level
    """
    if score >= 750:
        return 'low'
    elif score >= 700:
        return 'moderate'
    elif score >= 600:
        return 'elevated'
    else:
        return 'high'


def generate_factors(score: int, profile: Dict[str, Any]) -> List[str]:
    """
    Generate credit factors for report.
    
    Args:
        score: Credit score
        profile: Applicant profile
        
    Returns:
        List of factor descriptions
    """
    factors: List[str] = []
    
    monthly_income = float(profile.get('monthlyIncome', 0) or 0)
    existing_debts = float(profile.get('existingDebts', 0) or 0)
    employment_type = (profile.get('employmentType') or '').lower()
    
    if score >= 750:
        factors.append("Strong repayment capacity based on income-to-debt ratio")
        factors.append("Stable employment history")
    elif score >= 700:
        factors.append("Adequate income relative to obligations")
        if 'salaried' in employment_type:
            factors.append("Salaried employment is a positive indicator")
    elif score >= 650:
        if existing_debts > 0:
            factors.append("Existing debt obligations noted")
        factors.append("Income level supports moderate borrowing")
    else:
        if existing_debts > monthly_income * 6:
            factors.append("High existing debt relative to income")
        if 'salaried' not in employment_type and 'employed' not in employment_type:
            factors.append("Employment type may affect repayment stability")
        factors.append("Limited credit headroom for new obligations")
    
    if monthly_income == 0:
        factors.append("Income data not verified — affects scoring accuracy")
    
    return factors


def generate_recommendation(grade: BureauGrade) -> str:
    """
    Generate bureau recommendation.
    
    Args:
        grade: Credit grade
        
    Returns:
        Recommendation text
    """
    recommendations = {
        'A': "Applicant demonstrates strong creditworthiness. Proceed with standard terms.",
        'B': "Satisfactory credit profile. Standard processing recommended.",
        'C': "Moderate risk profile. Consider additional documentation or guarantor.",
        'D': "Elevated risk. Recommend enhanced due diligence and possible collateral requirement.",
        'E': "High risk profile. Manual officer review required before proceeding.",
    }
    return recommendations.get(grade, "Manual review recommended.")


# =============================================================================
# Main Functions
# =============================================================================

async def fetch_credit_bureau_report(
    applicant_data: Dict[str, Any],
    region_hint: Optional[str] = None,
) -> BureauReport:
    """
    Fetch credit bureau report for applicant.
    
    This is a simulated implementation for demo/development.
    In production, this would call real bureau APIs.
    
    Args:
        applicant_data: Applicant data including:
            - borrowerName: Applicant name
            - monthlyIncome: Monthly income
            - existingDebts: Existing monthly obligations
            - loanAmount: Requested loan amount
            - employmentType: Employment status
            - borrowerEmail: Email address
        region_hint: Optional region hint for bureau selection
        
    Returns:
        BureauReport with credit assessment
        
    Example:
        >>> report = await fetch_credit_bureau_report({
        ...     'borrowerName': 'John Doe',
        ...     'monthlyIncome': 'XCD 6,000',
        ...     'existingDebts': 'XCD 1,000',
        ...     'loanAmount': 'XCD 50,000',
        ...     'employmentType': 'Salaried',
        ... })
        >>> report['score']
        720
    """
    # Simulate API delay
    await asyncio.sleep(random.uniform(0.2, 0.5))
    
    # Parse numeric values
    from src.core.calculation_engines import parse_numeric
    
    monthly_income = parse_numeric(applicant_data.get('monthlyIncome', '0'))
    existing_debts = parse_numeric(applicant_data.get('existingDebts', '0'))
    loan_amount = parse_numeric(applicant_data.get('loanAmount', '0'))
    employment_type = applicant_data.get('employmentType', 'unknown')
    
    # Build profile for scoring
    profile = {
        'monthlyIncome': monthly_income,
        'existingDebts': existing_debts,
        'loanAmount': loan_amount,
        'employmentType': employment_type,
    }
    
    # Compute score
    score = compute_base_score(profile)
    grade, grade_label = score_to_grade(score)
    risk_level = score_to_risk(score)
    factors = generate_factors(score, profile)
    recommendation = generate_recommendation(grade)
    
    # Build report
    report = BureauReport({
        'score': score,
        'grade': grade,
        'gradeLabel': grade_label,
        'bureauName': select_bureau(region_hint),
        'reportReference': generate_report_reference(),
        'inquiryDate': datetime.now(timezone.utc).isoformat(),
        'factors': factors,
        'riskLevel': risk_level,
        'recommendation': recommendation,
    })
    
    logger.info(f"[Bureau] Generated report: {report['bureauName']} score={score} ({grade})")
    
    return report


def format_bureau_summary(report: BureauReport) -> str:
    """
    Format bureau report as summary string.
    
    Args:
        report: Bureau report
        
    Returns:
        Formatted summary string
    """
    return (
        f"Bureau: {report['bureauName']} | "
        f"Score: {report['score']} ({report['grade']} — {report['gradeLabel']}) | "
        f"Risk: {report['riskLevel']} | "
        f"Ref: {report['reportReference']}"
    )


# =============================================================================
# CLI Demo (for testing)
# =============================================================================

if __name__ == '__main__':
    import json
    
    async def demo():
        """Run demo bureau report generation."""
        test_cases = [
            {
                'name': 'Prime Borrower',
                'data': {
                    'borrowerName': 'Marcus Baptiste',
                    'monthlyIncome': 'XCD 12,000',
                    'existingDebts': 'XCD 2,000',
                    'loanAmount': 'XCD 50,000',
                    'employmentType': 'Salaried',
                },
            },
            {
                'name': 'Thin File Young',
                'data': {
                    'borrowerName': 'Keisha John',
                    'monthlyIncome': 'XCD 4,000',
                    'existingDebts': 'XCD 0',
                    'loanAmount': 'XCD 20,000',
                    'employmentType': 'Salaried',
                },
            },
            {
                'name': 'Self-Employed',
                'data': {
                    'borrowerName': 'Raj Kumar',
                    'monthlyIncome': 'TTD 15,000',
                    'existingDebts': 'TTD 3,000',
                    'loanAmount': 'TTD 200,000',
                    'employmentType': 'Self-employed',
                },
            },
        ]
        
        for case in test_cases:
            print(f"\n{'='*60}")
            print(f"Test Case: {case['name']}")
            print('='*60)
            
            report = await fetch_credit_bureau_report(case['data'])
            print(f"\n{format_bureau_summary(report)}")
            print(f"\nRecommendation: {report['recommendation']}")
            print(f"\nFactors:")
            for factor in report['factors']:
                print(f"  • {factor}")
    
    asyncio.run(demo())
