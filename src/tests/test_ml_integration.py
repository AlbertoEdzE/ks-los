import pytest
from unittest.mock import patch, MagicMock
from src.agents.nodes import risk_engine_node
from src.shared.types import ApplicantCreditProfile, Identity, Address, CreditSummary, PaymentBehavior, TradeLine, Inquiry, Flags, Metadata
from datetime import date
import json
from langchain_core.messages import AIMessage

# Validation of Phase 4 Integration
# Tests if the Risk Engine correctly incorporates the ML model's probability.

def create_test_profile(score=700):
    """Creates a controlled profile."""
    address = Address(line1="123 Main St", city="St. John's", territory="Antigua", territory_code="AG")
    identity = Identity(full_name="Test Applicant", date_of_birth=date(1990, 1, 1), national_id_hash="123", address=address)
    return ApplicantCreditProfile(
        metadata=Metadata(source="synthetic", query_timestamp=date.today(), territory="AG", consent_token="xyz"),
        identity=identity,
        summary=CreditSummary(credit_score=score, score_band="Good", total_accounts=5, open_accounts=3, closed_accounts=2, total_credit_limit_xcd=10000, total_current_balance_xcd=1000, utilization_ratio=0.1, total_past_due_xcd=0, months_oldest_account=60, months_newest_account=12, derogatory_marks=0, thin_file=False),
        payment_behavior=PaymentBehavior(on_time_payments_pct=1.0, late_30_days_count=0, late_60_days_count=0, late_90_plus_days_count=0, charge_offs=0, collections=0, worst_payment_status_ever="Current", payment_history_24m="1"*24),
        trade_lines=[], inquiries=[], flags=Flags(has_bankruptcy=False, has_foreclosure=False, has_active_collections=False, is_deceased=False, fraud_alert=False),
        associated_consumers=[]
    )

@patch("src.agents.nodes.get_kb")
@patch("src.agents.nodes.get_ml_model")
@patch("src.agents.nodes.llm")
def test_risk_engine_ensemble_logic(mock_llm, mock_get_ml, mock_get_kb):
    """
    Test that ML probability is used in the prompt and decision logic.
    """
    # 1. Setup Mock ML Model
    mock_ml_instance = MagicMock()
    # Simulate HIGH RISK (Low probability of good credit)
    mock_ml_instance.predict.return_value = {"probability_good": 0.15, "score": 0.15}
    mock_get_ml.return_value = mock_ml_instance
    
    # 2. Setup Mock KB
    mock_get_kb.return_value = None # Skip RAG for this test
    
    # 3. Setup Mock LLM Response (Initially says APPROVED based on policy)
    # We mock the .invoke() method on the llm object
    mock_response = AIMessage(content='{"decision": "APPROVED", "risk_score": 80, "reasoning": "Looks good based on policy."}')
    mock_llm.invoke.return_value = mock_response
    
    # 4. Execute
    profile = create_test_profile()
    state = {"credit_profile": profile}
    result = risk_engine_node(state)
    
    # 5. Verify Override
    # Should be downgraded to MANUAL_REVIEW because prob (0.15) < 0.2
    assert result["risk_decision"] == "MANUAL_REVIEW"
    assert "SYSTEM OVERRIDE" in result["risk_reasoning"]
    
    # Verify ML model was called
    mock_ml_instance.predict.assert_called_once()

    # Verify LLM was called
    mock_llm.invoke.assert_called_once()
