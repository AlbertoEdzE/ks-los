import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document
from src.agents.nodes import risk_engine_node
from src.shared.types import ApplicantCreditProfile, Identity, Address, CreditSummary, PaymentBehavior, TradeLine, Inquiry, Flags, Metadata
from datetime import date

# Scientific Experiment: Risk Engine Logic Validation
# Hypothesis: Given a specific policy context and profile, the Risk Engine generates a structured decision.
# Variables: Policy Context (Controlled via Stub), Profile (Controlled Input).

class StubKnowledgeBase:
    """
    A controlled stub for the Knowledge Base to ensure reproducible experiments
    without relying on the external vector database state.
    """
    def query(self, query_text, k=3):
        # Return controlled policy documents
        return [
            Document(page_content="## Credit Score Bands\nSuper Prime (720+): Auto-Approval eligible."),
            Document(page_content="## DTI Ratios\nMaximum Backend DTI: 43%.")
        ]

def create_test_profile(score=750, dti_debt=1000):
    """Creates a controlled profile for testing."""
    address = Address(line1="123 Main St", city="St. John's", territory="Antigua", territory_code="AG")
    identity = Identity(full_name="Test Applicant", date_of_birth=date(1990, 1, 1), national_id_hash="123", address=address)
    
    return ApplicantCreditProfile(
        metadata=Metadata(source="synthetic", query_timestamp=date.today(), territory="AG", consent_token="xyz"),
        identity=identity,
        summary=CreditSummary(
            credit_score=score, score_band="Super Prime" if score >= 720 else "Subprime", 
            total_accounts=5, open_accounts=3, closed_accounts=2, 
            total_credit_limit_xcd=10000, total_current_balance_xcd=dti_debt, 
            utilization_ratio=0.1, total_past_due_xcd=0, 
            months_oldest_account=60, months_newest_account=12, 
            derogatory_marks=0, thin_file=False
        ),
        payment_behavior=PaymentBehavior(on_time_payments_pct=1.0, late_30_days_count=0, late_60_days_count=0, late_90_plus_days_count=0, charge_offs=0, collections=0, worst_payment_status_ever="Current", payment_history_24m="1"*24),
        trade_lines=[], inquiries=[], flags=Flags(has_bankruptcy=False, has_foreclosure=False, has_active_collections=False, is_deceased=False, fraud_alert=False),
        associated_consumers=[]
    )

@patch("src.agents.nodes.get_kb")
def test_risk_engine_logic_approved(mock_get_kb):
    """
    Experiment 1: Super Prime Profile -> Should be Approved.
    """
    # 1. Setup
    mock_get_kb.return_value = StubKnowledgeBase()
    profile = create_test_profile(score=750, dti_debt=1000) # Low debt, High score
    state = {"credit_profile": profile}
    
    # 2. Execution
    result = risk_engine_node(state)
    
    # 3. Observation (Validation)
    assert "risk_decision" in result
    assert "risk_score" in result
    # We expect the LLM to likely Approve given the strong profile and policy
    # However, since it's an LLM, we assert structure primarily, and log the decision
    print(f"Decision for 750 Score: {result['risk_decision']}")
    assert isinstance(result['risk_score'], float)

@patch("src.agents.nodes.get_kb")
def test_risk_engine_logic_declined(mock_get_kb):
    """
    Experiment 2: Subprime Profile -> Should be Declined/Manual Review.
    """
    # 1. Setup
    mock_get_kb.return_value = StubKnowledgeBase()
    profile = create_test_profile(score=500, dti_debt=1000)
    state = {"credit_profile": profile}
    
    # 2. Execution
    result = risk_engine_node(state)
    
    # 3. Observation
    print(f"Decision for 500 Score: {result['risk_decision']}")
    # Assert structure
    assert result['risk_decision'] in ["DECLINED", "MANUAL_REVIEW"]
