"""
Golden Test Datasets for Agent Outputs.

These datasets define expected agent outputs for canonical borrower
conversations. They are used for:

1. Regression testing (ensure outputs don't drift)
2. Schema validation (ensure outputs match contract)
3. Agent evaluation (measure output quality)

Each test case includes:
- Input: User messages + context
- Expected: Validated metadata structure
- Tolerance: Fields allowed to vary (for LLM-generated text)
"""

from typing import Any, Dict, List


# =============================================================================
# Test Case 1: Thin File Young Borrower
# =============================================================================

GOLDEN_THIN_FILE_YOUNG: Dict[str, Any] = {
    "name": "thin_file_young_borrower",
    "description": "22-year-old first-time borrower with thin credit file",
    
    "input": {
        "messages": [
            {
                "role": "user",
                "content": "Hi, I'm Marcus. I'm 22 and I need a loan for a car.",
            },
            {
                "role": "assistant",
                "content": "Nice to meet you, Marcus! I'd be happy to help you with a car loan.",
            },
            {
                "role": "user",
                "content": "I'm working full-time as a teacher, making about XCD 4,000 per month.",
            },
        ],
        "context": {
            "territory": "LC",
            "credit_profile_scenario": "THIN_FILE_YOUNG",
        },
    },
    
    "expected": {
        "intent_analysis": {
            "purpose": "Vehicle purchase",
            "urgency": "medium",
            "affordability": "Moderate - monthly income XCD 4,000",
            "monthly_income": "XCD 4,000",
            "existing_debts": "None disclosed",
            "loan_amount": None,  # Not yet specified
            "employment_type": "Salaried",
            "credit_history": "Thin file (age 22)",
            "seriousness_score": 65,
            "fit_score": 55,
            "next_conversation_angle": "Ask for loan amount and vehicle details",
        },
        "loan_recommendations": [],  # Too early for recommendations
        "documents_checklist": None,
        "loan_application": None,
        "phase_action": None,
        "calculated_metrics": {
            "emi": None,  # No amount specified yet
            "foir": None,
            "approval_probability": 55,  # Thin file penalty
            "risk_grade": "C",
            "stp_tier": "referred",  # Thin file requires manual review
        },
    },
    
    "tolerance": {
        # Fields allowed to vary (LLM-generated text)
        "variable_fields": [
            "intent_analysis.affordability",
            "intent_analysis.next_conversation_angle",
        ],
        # Fields that must be exact
        "exact_fields": [
            "intent_analysis.purpose",
            "intent_analysis.employment_type",
            "intent_analysis.seriousness_score",
            "calculated_metrics.approval_probability",
            "calculated_metrics.stp_tier",
        ],
    },
}


# =============================================================================
# Test Case 2: Prime Established Borrower
# =============================================================================

GOLDEN_PRIME_ESTABLISHED: Dict[str, Any] = {
    "name": "prime_established_borrower",
    "description": "45-year-old with excellent credit, established income",
    
    "input": {
        "messages": [
            {
                "role": "user",
                "content": "I need a home loan for XCD 500,000. My credit score is 780.",
            },
        ],
        "context": {
            "territory": "AG",
            "credit_profile_scenario": "PRIME_ESTABLISHED",
        },
    },
    
    "expected": {
        "intent_analysis": {
            "purpose": "Home purchase",
            "urgency": "medium",
            "affordability": "Strong - excellent credit score 780",
            "monthly_income": None,  # Not yet specified
            "existing_debts": None,
            "loan_amount": "XCD 500,000",
            "employment_type": None,
            "credit_history": "Excellent (score 780)",
            "seriousness_score": 85,
            "fit_score": 90,
            "next_conversation_angle": "Ask for income and employment details",
        },
        "loan_recommendations": [],  # Need more info first
        "documents_checklist": None,
        "loan_application": None,
        "phase_action": None,
        "calculated_metrics": {
            "emi": 4500.00,  # Approximate for XCD 500k at 7% over 20 years
            "foir": None,  # Need income
            "approval_probability": 88,  # Excellent credit
            "risk_grade": "A",
            "stp_tier": "stp",  # Prime borrower qualifies for STP
        },
    },
    
    "tolerance": {
        "variable_fields": [
            "intent_analysis.affordability",
            "intent_analysis.next_conversation_angle",
        ],
        "exact_fields": [
            "intent_analysis.purpose",
            "intent_analysis.loan_amount",
            "intent_analysis.seriousness_score",
            "calculated_metrics.approval_probability",
            "calculated_metrics.risk_grade",
            "calculated_metrics.stp_tier",
        ],
    },
}


# =============================================================================
# Test Case 3: Debt Consolidation Request
# =============================================================================

GOLDEN_DEBT_CONSOLIDATION: Dict[str, Any] = {
    "name": "debt_consolidation_request",
    "description": "Borrower seeking to consolidate multiple debts",
    
    "input": {
        "messages": [
            {
                "role": "user",
                "content": "I want to consolidate my debts. I have 3 credit cards and a car loan.",
            },
            {
                "role": "user",
                "content": "My total monthly payments are about XCD 2,500. I make XCD 8,000/month.",
            },
        ],
        "context": {
            "territory": "TT",
            "credit_profile_scenario": "NEAR_PRIME",
        },
    },
    
    "expected": {
        "intent_analysis": {
            "purpose": "Debt consolidation",
            "urgency": "high",
            "affordability": "Moderate - DTI ~31%",
            "monthly_income": "XCD 8,000",
            "existing_debts": "XCD 2,500/month (3 credit cards + car loan)",
            "loan_amount": None,  # Not specified
            "employment_type": None,
            "credit_history": "Near prime (managing multiple debts)",
            "seriousness_score": 75,
            "fit_score": 70,
            "next_conversation_angle": "Ask for total debt amount and credit score",
        },
        "loan_recommendations": [],
        "documents_checklist": None,
        "loan_application": None,
        "phase_action": None,
        "calculated_metrics": {
            "emi": None,
            "foir": 31.25,  # 2500/8000
            "approval_probability": 68,
            "risk_grade": "B",
            "stp_tier": "referred",  # Debt consolidation requires review
        },
    },
    
    "tolerance": {
        "variable_fields": [
            "intent_analysis.affordability",
            "intent_analysis.next_conversation_angle",
        ],
        "exact_fields": [
            "intent_analysis.purpose",
            "intent_analysis.monthly_income",
            "intent_analysis.existing_debts",
            "calculated_metrics.foir",
        ],
    },
}


# =============================================================================
# Test Case 4: Application Submission (STP Path)
# =============================================================================

GOLDEN_APPLICATION_SUBMISSION_STP: Dict[str, Any] = {
    "name": "application_submission_stp",
    "description": "Complete application submission qualifying for STP",
    
    "input": {
        "messages": [
            # ... previous conversation gathering info ...
            {
                "role": "user",
                "content": "Yes, please submit my application. My email is marcus@example.com and phone is +1-758-555-1234.",
            },
        ],
        "context": {
            "territory": "LC",
            "credit_profile_scenario": "THIN_FILE_YOUNG",
            "all_fields_collected": True,
        },
    },
    
    "expected": {
        "intent_analysis": {
            "purpose": "Vehicle purchase",
            "urgency": "medium",
            "affordability": "Moderate",
            "monthly_income": "XCD 4,000",
            "existing_debts": "None",
            "loan_amount": "XCD 50,000",
            "employment_type": "Salaried",
            "credit_history": "Thin file",
            "seriousness_score": 85,  # Increased after full submission
            "fit_score": 65,
            "next_conversation_angle": "Await STP decision",
            "email": "marcus@example.com",
            "phone": "+1-758-555-1234",
        },
        "loan_recommendations": [
            {
                "productId": "VL-STD-001",
                "productName": "Vehicle Loan — Standard",
                "productCode": "VL-STD-001",
                "category": "Vehicle Loan",
                "estimatedRate": "8.5% - 10.5%",
                "estimatedEmi": "XCD 1,050/month",
                "tenure": "5 years",
                "totalInterest": "XCD 13,000",
                "approvalSpeed": "STP (same day)",
                "pros": ["Fast approval", "Competitive rates"],
                "cons": ["Requires valid driver's license"],
                "recommendation": "Best for first-time vehicle buyers",
            },
        ],
        "documents_checklist": {
            "requiredNow": [
                {
                    "name": "Valid National ID or Passport",
                    "description": "Government-issued photo ID",
                    "category": "identity",
                    "required": True,
                },
                {
                    "name": "Job Letter",
                    "description": "From current employer, dated within 3 months",
                    "category": "employment",
                    "required": True,
                },
                {
                    "name": "Last 3 Months' Pay Slips",
                    "description": "Most recent payroll records",
                    "category": "income",
                    "required": True,
                },
                {
                    "name": "Pro-forma Invoice or Dealer Quotation",
                    "description": "Vehicle purchase documentation",
                    "category": "property",
                    "required": True,
                },
            ],
        },
        "loan_application": {
            "success": True,
            "loanId": "LOAN-TEST-001",
            "message": "Your application has been submitted for fast-track processing!",
            "approvalTier": "stp",
            "stpApproved": True,
            "awaitingAcceptance": True,
        },
        "phase_action": {
            "type": "advance_phase",
            "phaseId": "phase_application_submission",
            "reason": "Application submitted with all required fields",
        },
        "calculated_metrics": {
            "emi": 1050.00,
            "foir": 26.25,  # 1050/4000
            "approval_probability": 72,
            "risk_grade": "B",
            "stp_tier": "stp",
        },
    },
    
    "tolerance": {
        "variable_fields": [
            "loan_application.loanId",  # Generated at runtime
            "loan_application.message",  # May vary slightly
        ],
        "exact_fields": [
            "loan_application.success",
            "loan_application.approvalTier",
            "loan_application.stpApproved",
            "documents_checklist.requiredNow",
            "phase_action.type",
        ],
    },
}


# =============================================================================
# Test Case 5: Application Submission (Referred Path)
# =============================================================================

GOLDEN_APPLICATION_SUBMISSION_REFERRED: Dict[str, Any] = {
    "name": "application_submission_referred",
    "description": "Application requiring officer review (high FOIR or self-employed)",
    
    "input": {
        "messages": [
            {
                "role": "user",
                "content": "I'm self-employed, running a consulting business. Making about XCD 12,000/month.",
            },
            {
                "role": "user",
                "content": "I need a business loan of XCD 200,000 for equipment.",
            },
        ],
        "context": {
            "territory": "TT",
            "credit_profile_scenario": "SELF_EMPLOYED",
            "all_fields_collected": True,
        },
    },
    
    "expected": {
        "intent_analysis": {
            "purpose": "Business loan",
            "urgency": "medium",
            "affordability": "Moderate - self-employed income",
            "monthly_income": "XCD 12,000",
            "existing_debts": "None disclosed",
            "loan_amount": "XCD 200,000",
            "employment_type": "Self-employed",
            "credit_history": "Not specified",
            "seriousness_score": 70,
            "fit_score": 50,  # Lower fit for business loan
            "next_conversation_angle": "Await officer review",
        },
        "loan_recommendations": [],
        "documents_checklist": {
            "requiredNow": [
                {
                    "name": "Valid National ID or Passport",
                    "description": "Government-issued photo ID",
                    "category": "identity",
                    "required": True,
                },
                {
                    "name": "Business Registration",
                    "description": "Proof of business registration",
                    "category": "employment",
                    "required": True,
                },
                {
                    "name": "Last 2 Years' Financials",
                    "description": "Audited financial statements",
                    "category": "income",
                    "required": True,
                },
            ],
        },
        "loan_application": {
            "success": True,
            "loanId": "LOAN-TEST-002",
            "message": "Your application has been submitted! A dedicated loan officer will guide you.",
            "approvalTier": "referred",
            "referralReason": "Self-employed — requires income verification by officer",
        },
        "phase_action": {
            "type": "advance_phase",
            "phaseId": "phase_application_submission",
            "reason": "Application submitted, referred for officer review",
        },
        "calculated_metrics": {
            "emi": 4500.00,  # Approximate for business loan
            "foir": 37.5,  # 4500/12000
            "approval_probability": 55,  # Lower for self-employed
            "risk_grade": "C",
            "stp_tier": "referred",
        },
    },
    
    "tolerance": {
        "variable_fields": [
            "loan_application.loanId",
            "loan_application.message",
        ],
        "exact_fields": [
            "loan_application.success",
            "loan_application.approvalTier",
            "loan_application.referralReason",
            "calculated_metrics.stp_tier",
        ],
    },
}


# =============================================================================
# Golden Set Registry
# =============================================================================

GOLDEN_DATASETS: List[Dict[str, Any]] = [
    GOLDEN_THIN_FILE_YOUNG,
    GOLDEN_PRIME_ESTABLISHED,
    GOLDEN_DEBT_CONSOLIDATION,
    GOLDEN_APPLICATION_SUBMISSION_STP,
    GOLDEN_APPLICATION_SUBMISSION_REFERRED,
]


def get_golden_dataset(name: str) -> Dict[str, Any]:
    """
    Get golden dataset by name.
    
    Args:
        name: Dataset name (e.g., 'thin_file_young_borrower')
        
    Returns:
        Golden dataset dictionary
        
    Raises:
        KeyError: If dataset not found
    """
    for dataset in GOLDEN_DATASETS:
        if dataset["name"] == name:
            return dataset
    raise KeyError(f"Golden dataset not found: {name}")


def get_all_golden_dataset_names() -> List[str]:
    """
    Get all golden dataset names.
    
    Returns:
        List of dataset names
    """
    return [dataset["name"] for dataset in GOLDEN_DATASETS]
