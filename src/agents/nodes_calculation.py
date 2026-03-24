"""
Calculation Node for LangGraph Agent Workflow.

This node computes deterministic financial metrics using the calculation engines
from Task 1. It runs BEFORE the risk_engine_node to ensure LLM reasoning is
grounded in accurate calculations (no hallucination of EMI, FOIR, etc.).

Ported from Loan-Navigator-AI's calculation engines with KS-LOS adaptations.
"""

import logging
from typing import Any, Dict, Optional
from src.agents.state import AgentState, CalculatedMetrics
from src.core.calculation_engines import (
    compute_full_loan_metrics,
    assess_stp_eligibility,
    parse_numeric,
)

logger = logging.getLogger(__name__)


def extract_loan_data_from_profile(profile: Any) -> Dict[str, Any]:
    """
    Extract loan data fields from ApplicantCreditProfile for calculation engines.
    
    This is an adapter function that maps the credit profile schema to the
    calculation engine's expected input format.
    
    Args:
        profile: ApplicantCreditProfile from state
        
    Returns:
        Dictionary with loan_data fields for compute_full_loan_metrics()
    """
    # Extract from summary
    summary = profile.summary if hasattr(profile, 'summary') else {}
    identity = profile.identity if hasattr(profile, 'identity') else {}
    
    # Caribbean territory to currency mapping
    territory = getattr(identity, 'address', None)
    territory_code = getattr(territory, 'territory', 'AG') if territory else 'AG'
    
    # Map territory to currency hint
    currency_map = {
        'AG': 'XCD',  # Antigua
        'GD': 'XCD',  # Grenada
        'LC': 'XCD',  # Saint Lucia
        'VC': 'XCD',  # Saint Vincent
        'KN': 'XCD',  # Saint Kitts
        'DM': 'XCD',  # Dominica
        'MS': 'XCD',  # Montserrat
        'TT': 'TTD',  # Trinidad & Tobago
        'GY': 'GYD',  # Guyana
        'JM': 'JMD',  # Jamaica
        'BB': 'BBD',  # Barbados
        'BS': 'BSD',  # Bahamas
    }
    currency = currency_map.get(territory_code.upper(), 'XCD')
    
    # Estimate loan amount from total debt (or use a default for demo)
    total_debt = getattr(summary, 'total_current_balance_xcd', 50000)
    
    # Estimate monthly income from credit score band (proxy for demo)
    score_band = getattr(summary, 'score_band', 'FAIR')
    income_map = {
        'EXCELLENT': 15000,
        'GOOD': 10000,
        'FAIR': 7000,
        'POOR': 4000,
    }
    monthly_income = income_map.get(score_band, 7000)
    
    # Existing debts from total debt (assume 2% monthly payment)
    existing_debts = total_debt * 0.02
    
    return {
        'loan_amount': f'{currency} {total_debt:.0f}',
        'interest_rate': '10.5',  # Default rate
        'tenure': '240',  # 20 years
        'monthly_income': f'{currency} {monthly_income:.0f}',
        'existing_debts': f'{currency} {existing_debts:.0f}',
        'credit_score': str(getattr(summary, 'credit_score', 650)),
        'employment_type': 'Salaried',  # Default
        'loan_type': 'Personal Loan',  # Default
        'territory': territory_code,
    }


def calculation_node(state: AgentState) -> AgentState:
    """
    Compute deterministic financial metrics using calculation engines.
    
    This node:
    1. Extracts loan data from credit profile
    2. Computes full loan metrics (EMI, FOIR, APR, etc.)
    3. Assesses STP eligibility
    4. Stores calculated metrics in state for downstream nodes
    
    Returns:
        Updated state with calculated_metrics field populated
        
    Side Effects:
        - Logs calculation results
        - No LLM calls (pure deterministic computation)
    """
    logger.info("[CalculationNode] Starting deterministic metric computation")
    
    profile = state.get('credit_profile')
    
    # Handle case where profile doesn't exist yet
    if not profile:
        logger.warning("[CalculationNode] No credit profile in state, skipping calculations")
        return {'calculated_metrics': None}
    
    try:
        # Step 1: Extract loan data from profile
        loan_data = extract_loan_data_from_profile(profile)
        logger.debug(f"[CalculationNode] Extracted loan data: {loan_data}")
        
        # Step 2: Compute full loan metrics
        metrics = compute_full_loan_metrics(loan_data)
        
        # Step 3: Assess STP eligibility
        stp_assessment = assess_stp_eligibility(loan_data)
        
        # Step 4: Build calculated metrics dictionary
        calculated_metrics: CalculatedMetrics = {
            # EMI
            'emi': float(metrics.emi.emi),
            'total_interest': float(metrics.emi.total_interest),
            'total_repayment': float(metrics.emi.total_repayment),
            
            # Affordability
            'foir': float(metrics.affordability.foir),
            'dti': float(metrics.affordability.dti),
            'dscr': float(metrics.affordability.dscr),
            'income_stability': metrics.affordability.income_stability_signal,
            
            # Collateral
            'ltv': float(metrics.collateral.ltv),
            
            # Credit risk
            'approval_probability': int(metrics.credit_risk.approval_probability),
            'risk_grade': metrics.credit_risk.risk_grade,
            
            # APR
            'apr': float(metrics.apr.apr),
            
            # STP
            'stp_tier': stp_assessment.tier,
            'stp_reasons': stp_assessment.reasons,
        }
        
        logger.info(
            f"[CalculationNode] Computed metrics: "
            f"EMI={calculated_metrics['emi']:.2f}, "
            f"FOIR={calculated_metrics['foir']:.2f}%, "
            f"Approval Prob={calculated_metrics['approval_probability']}%, "
            f"STP Tier={calculated_metrics['stp_tier']}"
        )
        
        return {'calculated_metrics': calculated_metrics}
        
    except Exception as e:
        logger.error(f"[CalculationNode] Calculation failed: {e}", exc_info=True)
        # Return None to allow graceful degradation
        return {'calculated_metrics': None}


def get_calculated_metrics(state: AgentState) -> Optional[CalculatedMetrics]:
    """
    Helper function to retrieve calculated metrics from state.
    
    Args:
        state: Current agent state
        
    Returns:
        CalculatedMetrics dict or None if not computed
    """
    return state.get('calculated_metrics')
