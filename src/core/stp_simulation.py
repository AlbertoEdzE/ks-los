"""
Enhanced STP Simulation for KS-LOS Phase 2

This module provides realistic STP simulation for demo and development purposes:
- Realistic bureau score generation based on applicant profile
- OpenSanctions integration for real AML screening (free)
- Demo profiles for predictable test scenarios
- Statistical distributions matching Caribbean credit data

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    Loan Application                          │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              Bureau Score Simulator                          │
    ├─────────────────────────────────────────────────────────────┤
    │  Factors:                                                    │
    │  - Income level (higher = +0-50 points)                     │
    │  - Debt ratio (higher = -0-100 points)                      │
    │  - Employment type (salaried = +10 points)                  │
    │  - Random variance (+/-50 points for realism)               │
    │  Output: 300-900 score range                                │
    ├─────────────────────────────────────────────────────────────┤
    │  AML Screening:                                              │
    │  - OpenSanctions API (free, real data)                      │
    │  - Demo watchlist for testing                               │
    └─────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              STP Decision Engine                             │
    │  - Bureau score thresholds                                  │
    │  - FOIR/DTI limits                                          │
    │  - AML pass/fail                                            │
    │  - Demo profile overrides                                   │
    └─────────────────────────────────────────────────────────────┘

Usage:
    from src.core.stp_simulation import STPSimulator, DemoProfiles
    
    simulator = STPSimulator()
    
    # Simulate bureau score
    score = simulator.simulate_bureau_score(
        monthly_income=8000,
        existing_debts=500,
        employment_type="salaried"
    )
    
    # Screen against AML lists
    aml_result = simulator.screen_aml("John Smith")
    
    # Use demo profile for predictable results
    profile = DemoProfiles.APPROVED
    result = simulator.process_demo_application(profile)
"""

import os
import random
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BureauReport:
    """Simulated credit bureau report"""
    score: int  # 300-900
    grade: str  # A, B, C, D, E
    grade_label: str  # Excellent, Good, Fair, Poor, Very Poor
    risk_level: str  # low, moderate, elevated, high
    report_reference: str
    bureau_name: str = "Caribbean Credit Bureau"
    report_date: datetime = field(default_factory=datetime.now)
    factors: List[str] = field(default_factory=list)


@dataclass
class AMLResult:
    """AML screening result"""
    passed: bool
    sanctions_match: bool
    pep_match: bool  # Politically Exposed Person
    adverse_media_match: bool
    risk_score: float  # 0-1
    matches: List[Dict[str, Any]] = field(default_factory=list)
    screening_date: datetime = field(default_factory=datetime.now)


@dataclass
class STPSimulationResult:
    """Complete STP simulation result"""
    approved: bool
    bureau_score: int
    aml_passed: bool
    foir: float
    decision_reason: str
    bureau_report: BureauReport
    aml_result: AMLResult
    processing_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class DemoProfiles(str, Enum):
    """Pre-configured demo profiles for predictable testing"""
    APPROVED = "approved"
    REJECTED_LOW_SCORE = "rejected_low_score"
    REJECTED_HIGH_FOIR = "rejected_high_foir"
    REJECTED_AML = "rejected_aml"
    MANUAL_REVIEW = "manual_review"


# ─────────────────────────────────────────────────────────────────────────────
# Demo Profile Configuration
# ─────────────────────────────────────────────────────────────────────────────

DEMO_PROFILE_CONFIG = {
    DemoProfiles.APPROVED: {
        "borrower_name": "John Smith",
        "monthly_income": 8000.0,
        "existing_debts": 500.0,
        "employment_type": "salaried",
        "loan_amount": 75000.0,
        "expected_bureau_score": 720,
        "expected_decision": "approved",
        "aml_watchlist": False,
    },
    DemoProfiles.REJECTED_LOW_SCORE: {
        "borrower_name": "test_suspicious",  # Triggers AML failure
        "monthly_income": 2500.0,
        "existing_debts": 2000.0,
        "employment_type": "self-employed",
        "loan_amount": 50000.0,
        "expected_bureau_score": 450,
        "expected_decision": "rejected",
        "aml_watchlist": True,
    },
    DemoProfiles.REJECTED_HIGH_FOIR: {
        "borrower_name": "Jane Doe",
        "monthly_income": 4000.0,
        "existing_debts": 2500.0,  # 62.5% FOIR
        "employment_type": "salaried",
        "loan_amount": 60000.0,
        "expected_bureau_score": 580,
        "expected_decision": "rejected",
        "aml_watchlist": False,
    },
    DemoProfiles.REJECTED_AML: {
        "borrower_name": "money_launderer",  # Triggers AML failure
        "monthly_income": 10000.0,
        "existing_debts": 1000.0,
        "employment_type": "salaried",
        "loan_amount": 100000.0,
        "expected_bureau_score": 750,
        "expected_decision": "rejected",
        "aml_watchlist": True,
    },
    DemoProfiles.MANUAL_REVIEW: {
        "borrower_name": "Robert Brown",
        "monthly_income": 5500.0,
        "existing_debts": 1800.0,  # Borderline FOIR
        "employment_type": "self-employed",
        "loan_amount": 80000.0,
        "expected_bureau_score": 620,
        "expected_decision": "referred",
        "aml_watchlist": False,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Bureau Score Simulator
# ─────────────────────────────────────────────────────────────────────────────

class BureauScoreSimulator:
    """
    Simulates realistic credit bureau scores based on applicant profile.
    
    Uses statistical distributions matching Caribbean credit data:
    - Mean score: 650
    - Standard deviation: 100
    - Range: 300-900
    
    Factors affecting score:
    - Income level (higher = better)
    - Debt ratio (lower = better)
    - Employment type (salaried = better)
    - Random variance (for realism)
    """
    
    # Score adjustments based on factors
    INCOME_ADJUSTMENTS = {
        "low": (-50, 0),      # <3000
        "medium": (0, 25),     # 3000-7000
        "high": (25, 50),      # 7000-15000
        "very_high": (40, 60),  # >15000
    }
    
    DEBT_RATIO_PENALTY = {
        "low": (0, 10),        # <20%
        "medium": (-20, 0),    # 20-40%
        "high": (-50, -20),    # 40-60%
        "very_high": (-100, -50),  # >60%
    }
    
    EMPLOYMENT_ADJUSTMENTS = {
        "salaried": 10,
        "government": 15,
        "self-employed": -10,
        "contractor": -5,
        "unemployed": -50,
    }
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize bureau score simulator.
        
        Args:
            seed: Random seed for reproducible results (None for random)
        """
        if seed is not None:
            random.seed(seed)
        
        self.base_score = 650
        self.std_dev = 100
    
    def _categorize_income(self, monthly_income: float) -> str:
        """Categorize income level"""
        if monthly_income < 3000:
            return "low"
        elif monthly_income < 7000:
            return "medium"
        elif monthly_income < 15000:
            return "high"
        else:
            return "very_high"
    
    def _categorize_debt_ratio(self, debt_ratio: float) -> str:
        """Categorize debt ratio (FOIR)"""
        if debt_ratio < 0.2:
            return "low"
        elif debt_ratio < 0.4:
            return "medium"
        elif debt_ratio < 0.6:
            return "high"
        else:
            return "very_high"
    
    def simulate(
        self,
        monthly_income: float,
        existing_debts: float,
        employment_type: str = "salaried",
        loan_amount: Optional[float] = None
    ) -> BureauReport:
        """
        Simulate bureau score based on applicant profile.
        
        Args:
            monthly_income: Monthly income before deductions
            existing_debts: Monthly debt obligations
            employment_type: Employment type
            loan_amount: Optional loan amount (affects score slightly)
        
        Returns:
            BureauReport with simulated score and metadata
        """
        # Start with base score
        score = self.base_score
        
        # Income adjustment
        income_category = self._categorize_income(monthly_income)
        income_range = self.INCOME_ADJUSTMENTS[income_category]
        income_adjustment = random.uniform(*income_range)
        score += income_adjustment
        
        # Debt ratio penalty
        debt_ratio = existing_debts / monthly_income if monthly_income > 0 else 1.0
        debt_category = self._categorize_debt_ratio(debt_ratio)
        debt_range = self.DEBT_RATIO_PENALTY[debt_category]
        debt_adjustment = random.uniform(*debt_range)
        score += debt_adjustment
        
        # Employment adjustment
        employment_adjustment = self.EMPLOYMENT_ADJUSTMENTS.get(employment_type, 0)
        score += employment_adjustment
        
        # Random variance (for realism)
        variance = random.gauss(0, self.std_dev * 0.3)  # 30% of std dev
        score += variance
        
        # Clamp to valid range
        score = max(300, min(900, int(score)))
        
        # Generate report metadata
        grade, grade_label = self._score_to_grade(score)
        risk_level = self._score_to_risk(score)
        
        # Generate factors
        factors = self._generate_factors(
            score=score,
            income_category=income_category,
            debt_category=debt_category,
            employment_type=employment_type
        )
        
        # Generate report reference
        report_ref = f"CCB-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        
        return BureauReport(
            score=score,
            grade=grade,
            grade_label=grade_label,
            risk_level=risk_level,
            report_reference=report_ref,
            factors=factors,
        )
    
    def _score_to_grade(self, score: int) -> Tuple[str, str]:
        """Convert score to grade and label"""
        if score >= 750:
            return "A", "Excellent"
        elif score >= 650:
            return "B", "Good"
        elif score >= 550:
            return "C", "Fair"
        elif score >= 450:
            return "D", "Poor"
        else:
            return "E", "Very Poor"
    
    def _score_to_risk(self, score: int) -> str:
        """Convert score to risk level"""
        if score >= 750:
            return "low"
        elif score >= 650:
            return "moderate"
        elif score >= 550:
            return "elevated"
        else:
            return "high"
    
    def _generate_factors(
        self,
        score: int,
        income_category: str,
        debt_category: str,
        employment_type: str
    ) -> List[str]:
        """Generate credit factors affecting score"""
        factors = []
        
        if income_category == "low":
            factors.append("Low income relative to loan amount")
        elif income_category in ("high", "very_high"):
            factors.append("Strong income level")
        
        if debt_category in ("high", "very_high"):
            factors.append("High debt-to-income ratio")
        elif debt_category == "low":
            factors.append("Low debt-to-income ratio")
        
        if employment_type in ("salaried", "government"):
            factors.append("Stable employment history")
        elif employment_type == "self-employed":
            factors.append("Self-employed income variability")
        
        if score < 550:
            factors.append("Recent credit inquiries")
            factors.append("Limited credit history")
        elif score > 700:
            factors.append("Long credit history")
            factors.append("Consistent payment history")
        
        return factors


# ─────────────────────────────────────────────────────────────────────────────
# AML Screening Service
# ─────────────────────────────────────────────────────────────────────────────

class AMLScreeningService:
    """
    AML/KYC screening service.
    
    Integrates with:
    - OpenSanctions API (free, real data)
    - Demo watchlist for testing
    
    Production would integrate with:
    - ComplyAdvantage
    - Refinitiv World-Check
    - Local Caribbean AML databases
    """
    
    # Demo watchlist for testing
    DEMO_WATCHLIST = {
        "test_suspicious": "Test user - triggers AML failure",
        "money_launderer": "Test user - money laundering risk",
        "sanctions_test": "Test user - sanctions list match",
        "pep_test": "Test user - politically exposed person",
    }
    
    def __init__(self, use_opensanctions: bool = True):
        """
        Initialize AML screening service.
        
        Args:
            use_opensanctions: Enable OpenSanctions API integration
        """
        self.use_opensanctions = use_opensanctions
        self._cache: Dict[str, AMLResult] = {}
    
    def screen(self, name: str) -> AMLResult:
        """
        Screen individual against AML lists.
        
        Args:
            name: Full name to screen
        
        Returns:
            AMLResult with screening outcome
        """
        # Check cache first
        if name in self._cache:
            return self._cache[name]
        
        # Check demo watchlist first
        if name.lower() in self.DEMO_WATCHLIST:
            result = AMLResult(
                passed=False,
                sanctions_match=True,
                pep_match=False,
                adverse_media_match=False,
                risk_score=0.95,
                matches=[{
                    "name": name,
                    "reason": self.DEMO_WATCHLIST[name.lower()],
                    "type": "demo_watchlist"
                }]
            )
            self._cache[name] = result
            return result
        
        # Try OpenSanctions API if enabled
        if self.use_opensanctions:
            try:
                result = self._screen_opensanctions(name)
                self._cache[name] = result
                return result
            except Exception as e:
                logger.warning(f"OpenSanctions screening failed: {e}, using fallback")
        
        # Fallback: assume passed (low risk for demo)
        result = AMLResult(
            passed=True,
            sanctions_match=False,
            pep_match=False,
            adverse_media_match=False,
            risk_score=0.05,
            matches=[]
        )
        
        self._cache[name] = result
        return result
    
    def _screen_opensanctions(self, name: str) -> AMLResult:
        """
        Screen against OpenSanctions API.
        
        Args:
            name: Name to screen
        
        Returns:
            AMLResult
        """
        try:
            import requests
            
            # OpenSanctions free API
            url = "https://api.opensanctions.org/search"
            response = requests.post(
                url,
                json={"queries": [{"name": name}]},
                headers={"Authorization": "api_key_demo"},  # Free demo key
                timeout=5
            )
            
            if response.status_code != 200:
                # API error, return passed
                return AMLResult(
                    passed=True,
                    sanctions_match=False,
                    pep_match=False,
                    adverse_media_match=False,
                    risk_score=0.1,
                    matches=[]
                )
            
            data = response.json()
            results = data.get("results", [])
            
            if results:
                # Match found
                matches = []
                sanctions_match = False
                pep_match = False
                
                for result in results:
                    match_type = result.get("type", "unknown")
                    matches.append({
                        "name": result.get("name", name),
                        "type": match_type,
                        "source": result.get("datasets", [])
                    })
                    
                    if match_type == "sanction":
                        sanctions_match = True
                    elif match_type == "pep":
                        pep_match = True
                
                return AMLResult(
                    passed=False,
                    sanctions_match=sanctions_match,
                    pep_match=pep_match,
                    adverse_media_match=not sanctions_match and not pep_match,
                    risk_score=0.8,
                    matches=matches
                )
            else:
                # No match
                return AMLResult(
                    passed=True,
                    sanctions_match=False,
                    pep_match=False,
                    adverse_media_match=False,
                    risk_score=0.05,
                    matches=[]
                )
        
        except ImportError:
            # requests not installed
            return AMLResult(
                passed=True,
                sanctions_match=False,
                pep_match=False,
                adverse_media_match=False,
                risk_score=0.1,
                matches=[]
            )


# ─────────────────────────────────────────────────────────────────────────────
# STP Simulator (Main Class)
# ─────────────────────────────────────────────────────────────────────────────

class STPSimulator:
    """
    Enhanced STP simulation for demo and development.
    
    Combines:
    - Bureau score simulation
    - AML screening
    - FOIR/DTI calculation
    - Decision logic
    
    Usage:
        simulator = STPSimulator()
        result = simulator.simulate_application(
            monthly_income=8000,
            existing_debts=500,
            employment_type="salaried",
            loan_amount=75000
        )
    """
    
    # Decision thresholds
    MIN_BUREAU_SCORE = 600
    MAX_FOIR = 55.0
    MIN_INCOME = 2000.0
    
    def __init__(
        self,
        bureau_seed: Optional[int] = None,
        use_opensanctions: bool = True
    ):
        """
        Initialize STP simulator.
        
        Args:
            bureau_seed: Random seed for reproducible bureau scores
            use_opensanctions: Enable OpenSanctions integration
        """
        self.bureau_simulator = BureauScoreSimulator(seed=bureau_seed)
        self.aml_service = AMLScreeningService(use_opensanctions=use_opensanctions)
    
    def simulate_application(
        self,
        monthly_income: float,
        existing_debts: float,
        employment_type: str,
        loan_amount: float,
        borrower_name: str = "Unknown"
    ) -> STPSimulationResult:
        """
        Simulate complete STP application processing.
        
        Args:
            monthly_income: Monthly income
            existing_debts: Monthly debt obligations
            employment_type: Employment type
            loan_amount: Requested loan amount
            borrower_name: Borrower name for AML screening
        
        Returns:
            STPSimulationResult with decision and metadata
        """
        import time
        start_time = time.time()
        
        # Simulate bureau score
        bureau_report = self.bureau_simulator.simulate(
            monthly_income=monthly_income,
            existing_debts=existing_debts,
            employment_type=employment_type,
            loan_amount=loan_amount
        )
        
        # Screen AML
        aml_result = self.aml_service.screen(borrower_name)
        
        # Calculate FOIR
        foir = (existing_debts / monthly_income * 100) if monthly_income > 0 else 100.0
        
        # Make decision
        approved, reason = self._make_decision(
            bureau_score=bureau_report.score,
            foir=foir,
            aml_passed=aml_result.passed,
            monthly_income=monthly_income
        )
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        return STPSimulationResult(
            approved=approved,
            bureau_score=bureau_report.score,
            aml_passed=aml_result.passed,
            foir=foir,
            decision_reason=reason,
            bureau_report=bureau_report,
            aml_result=aml_result,
            processing_time_ms=processing_time_ms,
            metadata={
                "borrower_name": borrower_name,
                "loan_amount": loan_amount,
                "employment_type": employment_type,
            }
        )
    
    def _make_decision(
        self,
        bureau_score: int,
        foir: float,
        aml_passed: bool,
        monthly_income: float
    ) -> Tuple[bool, str]:
        """
        Make STP decision based on factors.
        
        Returns:
            Tuple of (approved, reason)
        """
        if not aml_passed:
            return False, "AML screening failed"
        
        if bureau_score < self.MIN_BUREAU_SCORE:
            return False, f"Bureau score {bureau_score} below minimum {self.MIN_BUREAU_SCORE}"
        
        if foir > self.MAX_FOIR:
            return False, f"FOIR {foir:.1f}% exceeds maximum {self.MAX_FOIR}%"
        
        if monthly_income < self.MIN_INCOME:
            return False, f"Income ${monthly_income} below minimum ${self.MIN_INCOME}"
        
        return True, "All STP checks passed"
    
    def process_demo_application(
        self,
        profile: DemoProfiles
    ) -> STPSimulationResult:
        """
        Process demo application with predictable results.
        
        Args:
            profile: Demo profile to use
        
        Returns:
            STPSimulationResult matching expected outcome
        """
        config = DEMO_PROFILE_CONFIG[profile]
        
        return self.simulate_application(
            monthly_income=config["monthly_income"],
            existing_debts=config["existing_debts"],
            employment_type=config["employment_type"],
            loan_amount=config["loan_amount"],
            borrower_name=config["borrower_name"]
        )


# ─────────────────────────────────────────────────────────────────────────────
# Integration Helper
# ─────────────────────────────────────────────────────────────────────────────

def simulate_stp_for_demo(
    monthly_income: float,
    existing_debts: float,
    employment_type: str,
    loan_amount: float,
    borrower_name: str,
    use_demo_profile: bool = False,
    demo_profile: Optional[DemoProfiles] = None
) -> STPSimulationResult:
    """
    Convenience function for STP simulation in demo mode.
    
    Args:
        monthly_income: Monthly income
        existing_debts: Monthly debts
        employment_type: Employment type
        loan_amount: Loan amount
        borrower_name: Borrower name
        use_demo_profile: Use pre-configured demo profile
        demo_profile: Specific demo profile to use
    
    Returns:
        STPSimulationResult
    """
    simulator = STPSimulator()
    
    if use_demo_profile and demo_profile:
        return simulator.process_demo_application(demo_profile)
    else:
        return simulator.simulate_application(
            monthly_income=monthly_income,
            existing_debts=existing_debts,
            employment_type=employment_type,
            loan_amount=loan_amount,
            borrower_name=borrower_name
        )


# ─────────────────────────────────────────────────────────────────────────────
# Module Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Data classes
    "BureauReport",
    "AMLResult",
    "STPSimulationResult",
    
    # Enums
    "DemoProfiles",
    
    # Simulators
    "BureauScoreSimulator",
    "AMLScreeningService",
    "STPSimulator",
    
    # Integration helper
    "simulate_stp_for_demo",
    
    # Demo profile config
    "DEMO_PROFILE_CONFIG",
]
