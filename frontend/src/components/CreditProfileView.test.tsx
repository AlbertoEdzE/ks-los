import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CreditProfileView } from './CreditProfileView';
import type { ApplicantCreditProfile } from '../types';

const mockProfile: ApplicantCreditProfile = {
  metadata: {
    source: "synthetic",
    query_timestamp: "2023-01-01T00:00:00",
    territory: "AG",
    consent_token: "token",
    synthetic_archetype: "TEST_ARCHETYPE"
  },
  identity: {
    full_name: "John Doe",
    date_of_birth: "1990-01-01",
    national_id_hash: "hash",
    address: {
      line1: "123 Main St",
      city: "St John's",
      territory: "Antigua",
      territory_code: "AG"
    }
  },
  summary: {
    credit_score: 750,
    score_band: "GOOD",
    total_accounts: 5,
    open_accounts: 5,
    closed_accounts: 0,
    total_credit_limit_xcd: 50000,
    total_current_balance_xcd: 10000,
    utilization_ratio: 0.2,
    total_past_due_xcd: 0,
    months_oldest_account: 60,
    months_newest_account: 12,
    derogatory_marks: 0,
    thin_file: false
  },
  payment_behavior: {
    on_time_payments_pct: 1.0,
    late_30_days_count: 0,
    late_60_days_count: 0,
    late_90_plus_days_count: 0,
    charge_offs: 0,
    collections: 0,
    worst_payment_status_ever: "OK",
    payment_history_24m: "111111111111111111111111"
  },
  trade_lines: [
    {
      account_id_hash: "acc1",
      creditor_type: "BANK",
      account_type: "CREDIT_CARD",
      opened_date: "2020-01-01",
      credit_limit_xcd: 10000,
      current_balance_xcd: 2000,
      monthly_payment_xcd: 500,
      account_status: "CURRENT",
      payment_history_24m: "111111111111111111111111",
      ecoa_code: "INDIVIDUAL"
    }
  ],
  inquiries: [],
  flags: {
    has_bankruptcy: false,
    has_foreclosure: false,
    has_active_collections: false,
    is_deceased: false,
    fraud_alert: false
  }
};

describe('CreditProfileView', () => {
  it('renders applicant name and score', () => {
    render(<CreditProfileView profile={mockProfile} />);
    
    expect(screen.getByText('John Doe')).toBeDefined();
    expect(screen.getByText('750')).toBeDefined();
    expect(screen.getByText('GOOD')).toBeDefined();
  });

  it('renders trade lines correctly', () => {
    render(<CreditProfileView profile={mockProfile} />);
    
    expect(screen.getByText('CREDIT_CARD')).toBeDefined();
    expect(screen.getByText('XCD 2,000')).toBeDefined();
  });
});
