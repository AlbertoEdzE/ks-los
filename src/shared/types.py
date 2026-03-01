from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from datetime import date, datetime

class Address(BaseModel):
    line1: str
    city: str
    territory: str
    territory_code: str

class Identity(BaseModel):
    full_name: str
    date_of_birth: date
    national_id_hash: str
    address: Address

class CreditSummary(BaseModel):
    credit_score: int
    score_band: str
    total_accounts: int
    open_accounts: int
    closed_accounts: int
    total_credit_limit_xcd: float
    total_current_balance_xcd: float
    utilization_ratio: float
    total_past_due_xcd: float
    months_oldest_account: int
    months_newest_account: int
    derogatory_marks: int
    thin_file: bool
    thin_file_reason: Optional[str] = None

class TradeLine(BaseModel):
    account_id_hash: str
    creditor_type: str
    account_type: str
    opened_date: date
    closed_date: Optional[date] = None
    credit_limit_xcd: float
    current_balance_xcd: float
    monthly_payment_xcd: float
    account_status: str
    payment_history_24m: str  # 24 chars: 1, 2, 3, B, X
    ecoa_code: str

class PaymentBehavior(BaseModel):
    on_time_payments_pct: float
    late_30_days_count: int
    late_60_days_count: int
    late_90_plus_days_count: int
    charge_offs: int
    collections: int
    worst_payment_status_ever: str
    payment_history_24m: str

class Inquiry(BaseModel):
    inquiry_date: date
    creditor_type: str
    inquiry_type: str

class Flags(BaseModel):
    has_bankruptcy: bool
    has_foreclosure: bool
    has_active_collections: bool
    is_deceased: bool
    fraud_alert: bool

class Metadata(BaseModel):
    source: Literal["everydata_eccu", "ccbl", "creditinfo_jm", "synthetic"]
    query_timestamp: datetime
    territory: str
    consent_token: str
    synthetic_archetype: Optional[str] = None
    synthetic_seed_hash: Optional[str] = None

class ApplicantCreditProfile(BaseModel):
    metadata: Metadata
    identity: Identity
    summary: CreditSummary
    payment_behavior: PaymentBehavior
    trade_lines: List[TradeLine]
    inquiries: List[Inquiry]
    flags: Flags
