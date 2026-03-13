export interface Address {
  line1: string;
  city: string;
  territory: string;
  territory_code: string;
}

export interface Identity {
  full_name: string;
  date_of_birth: string;
  national_id_hash: string;
  address: Address;
}

export interface CreditSummary {
  credit_score: number;
  score_band: string;
  total_accounts: number;
  open_accounts: number;
  closed_accounts: number;
  total_credit_limit_xcd: number;
  total_current_balance_xcd: number;
  utilization_ratio: number;
  total_past_due_xcd: number;
  months_oldest_account: number;
  months_newest_account: number;
  derogatory_marks: number;
  thin_file: boolean;
  thin_file_reason?: string;
}

export interface TradeLine {
  account_id_hash: string;
  creditor_type: string;
  account_type: string;
  opened_date: string;
  closed_date?: string;
  credit_limit_xcd: number;
  current_balance_xcd: number;
  monthly_payment_xcd: number;
  account_status: string;
  payment_history_24m: string;
  ecoa_code: string;
}

export interface PaymentBehavior {
  on_time_payments_pct: number;
  late_30_days_count: number;
  late_60_days_count: number;
  late_90_plus_days_count: number;
  charge_offs: number;
  collections: number;
  worst_payment_status_ever: string;
  payment_history_24m: string;
}

export interface Inquiry {
  inquiry_date: string;
  creditor_type: string;
  inquiry_type: string;
}

export interface Flags {
  has_bankruptcy: boolean;
  has_foreclosure: boolean;
  has_active_collections: boolean;
  is_deceased: boolean;
  fraud_alert: boolean;
}

export interface Metadata {
  source: "everydata_eccu" | "ccbl" | "creditinfo_jm" | "synthetic";
  query_timestamp: string;
  territory: string;
  consent_token: string;
  synthetic_archetype?: string;
  synthetic_seed_hash?: string;
}

export interface ApplicantCreditProfile {
  metadata: Metadata;
  identity: Identity;
  summary: CreditSummary;
  payment_behavior: PaymentBehavior;
  trade_lines: TradeLine[];
  inquiries: Inquiry[];
  flags: Flags;
}

export interface V2RecommendedProduct {
  name: string;
  type: string;
  estimatedRate: string;
  estimatedEmi: string;
  tenure: string;
  totalInterest: string;
  approvalSpeed: string;
  pros: string[];
  cons: string[];
  recommendation: string;
}

export interface V2ApprovalProbabilityItem {
  title: string;
  detail: string;
  severity?: 'low' | 'medium' | 'high';
  impact?: 'low' | 'medium' | 'high';
}

export interface V2ApprovalProbability {
  probability: number;
  band: 'low' | 'medium' | 'high';
  topBlockers: V2ApprovalProbabilityItem[];
  topActions: V2ApprovalProbabilityItem[];
  inputsUsed: Record<string, unknown>;
  method: string;
  asOf: string;
}

export interface V2Conversation {
  id: string;
  borrowerName: string | null;
  status: string;
  chatRole: string;
  currentPhaseId: string | null;
  seriousnessScore: number | null;
  fitScore: number | null;
  intentSummary: Record<string, unknown> | null;
  approvalProbability: V2ApprovalProbability | null;
  recommendedProducts: V2RecommendedProduct[] | null;
  nextConversationAngle: string | null;
  assignedOfficer: string | null;
  createdAt: string | null;
}

export interface V2Phase {
  id: string;
  name: string;
  description: string | null;
  sortOrder: number;
  isActive: boolean;
  color: string | null;
  icon: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface V2Loan {
  id: string;
  borrowerName: string | null;
  borrowerEmail: string | null;
  borrowerPhone: string | null;
  loanType: string | null;
  loanAmount: string | null;
  interestRate: string | null;
  tenure: string | null;
  monthlyEmi: string | null;
  purpose: string | null;
  employmentType: string | null;
  monthlyIncome: string | null;
  existingDebts: string | null;
  creditScore: string | null;
  collateral: string | null;
  downPayment: string | null;
  propertyValue: string | null;
  ltv: string | null;
  currentPhaseId: string | null;
  status: string | null;
  notes: string | null;
  conversationId: string | null;
  createdBy: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}
