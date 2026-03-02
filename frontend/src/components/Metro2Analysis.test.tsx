import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Metro2Analysis } from './Metro2Analysis';
import type { ApplicantCreditProfile } from '../types';

const mockProfile: ApplicantCreditProfile = {
  identity: {
    full_name: 'Test User',
    date_of_birth: '1990-01-01',
    national_id_hash: 'hash123',
    address: {
      line1: '123 Test St',
      city: 'Test City',
      territory: 'Test Territory',
      territory_code: 'TT'
    }
  },
  summary: {
    credit_score: 750,
    score_band: 'GOOD',
    total_accounts: 5,
    open_accounts: 3,
    closed_accounts: 2,
    total_credit_limit_xcd: 5000,
    total_current_balance_xcd: 1000,
    utilization_ratio: 0.2,
    total_past_due_xcd: 0,
    months_oldest_account: 24,
    months_newest_account: 1,
    derogatory_marks: 0,
    thin_file: false
  },
  trade_lines: [
    {
      account_id_hash: 'hash123',
      creditor_type: 'Bank',
      account_type: 'Credit Card',
      opened_date: '2022-01-01',
      credit_limit_xcd: 1000,
      current_balance_xcd: 500,
      monthly_payment_xcd: 50,
      account_status: '11',
      payment_history_24m: '000000000000000000000000',
      ecoa_code: '1'
    }
  ],
  metadata: {
    source: 'synthetic',
    query_timestamp: '2023-01-01',
    territory: 'Test Territory',
    consent_token: 'token123',
    synthetic_archetype: 'test'
  },
  payment_behavior: {
    on_time_payments_pct: 100,
    late_30_days_count: 0,
    late_60_days_count: 0,
    late_90_plus_days_count: 0,
    charge_offs: 0,
    collections: 0,
    worst_payment_status_ever: '0',
    payment_history_24m: '000000000000000000000000'
  },
  inquiries: [],
  flags: {
    has_bankruptcy: false,
    has_foreclosure: false,
    has_active_collections: false,
    is_deceased: false,
    fraud_alert: false
  }
};

describe('Metro2Analysis', () => {
  it('renders the collapsed state initially', () => {
    render(<Metro2Analysis profile={mockProfile} />);
    expect(screen.getByText('METRO 2')).toBeDefined();
    expect(screen.getByText('Technical Analysis & Data Standards')).toBeDefined();
    // Content should not be visible yet
    expect(screen.queryByText('Payment History Profile (Base Segment)')).toBeNull();
  });

  it('expands when clicked', () => {
    render(<Metro2Analysis profile={mockProfile} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    
    expect(screen.getByText('Payment History Profile (Base Segment)')).toBeDefined();
    expect(screen.getByText('J1/J2 Segment Analysis')).toBeDefined();
    expect(screen.getByText('Payment Rating Derivation')).toBeDefined();
  });

  it('displays correct profile data when expanded', () => {
    render(<Metro2Analysis profile={mockProfile} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);

    // Check for status code description
    expect(screen.getByText('Current account')).toBeDefined();
    // Check for ECOA code description
    expect(screen.getByText('Individual')).toBeDefined();
  });
});
