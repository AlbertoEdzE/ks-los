import pytest
from datetime import date
from src.core.metro2 import Metro2Generator
from src.shared.types import ApplicantCreditProfile, Identity, Address, CreditSummary, PaymentBehavior, TradeLine, Inquiry, Flags, Metadata

# Scientific Validation of Metro 2 Compliance
# Focus: Structural integrity (426 bytes), Field correctness

def create_mock_profile():
    """Helper to create a valid profile for testing."""
    address = Address(line1="123 Main St", city="St. John's", territory="Antigua", territory_code="AG")
    identity = Identity(full_name="John Doe", date_of_birth=date(1990, 1, 1), national_id_hash="123456789", address=address)
    trade_line = TradeLine(
        account_id_hash="ACC123",
        creditor_type="BANK",
        account_type="CREDIT_CARD",
        opened_date=date(2020, 1, 1),
        credit_limit_xcd=5000.0,
        current_balance_xcd=1000.0,
        monthly_payment_xcd=100.0,
        account_status="CURRENT",
        payment_history_24m="1" * 24,
        ecoa_code="1"
    )
    # Minimal valid profile
    return ApplicantCreditProfile(
        metadata=Metadata(source="synthetic", query_timestamp=date.today(), territory="AG", consent_token="xyz"),
        identity=identity,
        summary=CreditSummary(credit_score=700, score_band="Prime", total_accounts=1, open_accounts=1, closed_accounts=0, total_credit_limit_xcd=5000, total_current_balance_xcd=1000, utilization_ratio=0.2, total_past_due_xcd=0, months_oldest_account=12, months_newest_account=12, derogatory_marks=0, thin_file=False),
        payment_behavior=PaymentBehavior(on_time_payments_pct=1.0, late_30_days_count=0, late_60_days_count=0, late_90_plus_days_count=0, charge_offs=0, collections=0, worst_payment_status_ever="Current", payment_history_24m="1"*24),
        trade_lines=[trade_line],
        inquiries=[],
        flags=Flags(has_bankruptcy=False, has_foreclosure=False, has_active_collections=False, is_deceased=False, fraud_alert=False),
        associated_consumers=[]
    )

def test_metro2_structure():
    """Validates that the generated file follows the fixed-width structure."""
    generator = Metro2Generator()
    profile = create_mock_profile()
    
    content = generator.generate_file(profile)
    lines = content.split("\n")
    
    # Check Record Count (Header + 1 Base + Trailer = 3)
    assert len(lines) == 3
    
    # Check Line Lengths (Must be exactly 426 bytes)
    for i, line in enumerate(lines):
        assert len(line) == 426, f"Line {i} length is {len(line)}, expected 426"

def test_metro2_header():
    """Validates Header Record content."""
    generator = Metro2Generator()
    profile = create_mock_profile()
    content = generator.generate_file(profile)
    header = content.split("\n")[0]
    
    assert header.startswith("HEADER")
    assert "KS_LOS_DEMO" in header

def test_metro2_base_segment():
    """Validates Base Segment data mapping."""
    generator = Metro2Generator()
    profile = create_mock_profile()
    content = generator.generate_file(profile)
    base = content.split("\n")[1]
    
    # Surname starts at index 204 (calculated from field lengths)
    surname = base[204:204+25].strip()
    assert surname == "Doe"
    
    # Check Account Number (starts at 20)
    # Base(4) + 1(1) + Date(14) + 0(1) = 20 chars.
    acc_num = base[20:40].strip()
    assert acc_num == "ACC123"

def test_metro2_j1_segment():
    """Validates J1 Segment generation for co-borrowers."""
    generator = Metro2Generator()
    profile = create_mock_profile()
    
    # Add a co-borrower at same address
    co_borrower = Identity(
        full_name="Jane Doe",
        date_of_birth=date(1992, 1, 1),
        national_id_hash="987654321",
        address=profile.identity.address # Same address
    )
    profile.associated_consumers = [co_borrower]
    
    content = generator.generate_file(profile)
    lines = content.split("\n")
    
    # Should have: Header, Base, J1, Trailer (4 lines)
    assert len(lines) == 4
    j1 = lines[2]
    
    assert j1.startswith("J1")
    assert "Jane" in j1
