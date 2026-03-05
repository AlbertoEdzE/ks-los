import React, { useState } from 'react';
import type { ApplicantCreditProfile } from '../types';

interface Props {
  profile: ApplicantCreditProfile;
}

const METRO2_STATUS_CODES: Record<string, string> = {
  '11': 'Current account',
  '13': 'Paid or closed account/zero balance',
  '61': 'Account paid in full was a voluntary surrender',
  '62': 'Account paid in full was a collection account',
  '63': 'Account paid in full was a repossession',
  '64': 'Account paid in full was a charge-off',
  '71': 'Account 30-59 days past due',
  '78': 'Account 60-89 days past due',
  '80': 'Account 90-119 days past due',
  '82': 'Account 120-149 days past due',
  '83': 'Account 150-179 days past due',
  '84': 'Account 180+ days past due',
  '93': 'Account assigned to internal or external collections',
  '94': 'Foreclosure completed',
  '95': 'Voluntary surrender',
  '96': 'Merchandise was repossessed',
  '97': 'Unpaid balance reported as a loss (charge-off)'
};

const ECOA_CODES: Record<string, string> = {
  '1': 'Individual',
  '2': 'Joint Contractual Liability',
  '7': 'Maker',
  'W': 'Business/Commercial'
};

const PaymentHistoryGrid = ({ historyString }: { historyString: string }) => {
  // historyString is typically 24 chars, e.g. "000000001000000000000000"
  // 0, 1, 2, 3, 4, 5, 6, L, C, etc.
  // We'll visualize it as a grid of boxes.
  // Assuming 0=Current, 1=30, 2=60, 3=90, etc.

  const getStatusColor = (char: string) => {
    switch (char) {
      case '0': return '#10b981'; // Green (Current)
      case '1': return '#f59e0b'; // Amber (30 late)
      case '2': return '#f97316'; // Orange (60 late)
      case '3': 
      case '4': 
      case '5': 
      case '6': return '#ef4444'; // Red (90+ late)
      case 'L': return '#6366f1'; // Indigo (Charge-off/Loss)
      case 'C': return '#8b5cf6'; // Violet (Collection)
      case '-': return '#d1d5db'; // Gray (No Data)
      default: return '#e5e7eb'; // Light Gray (Unknown)
    }
  };

  const months = historyString.split('');

  return (
    <div style={{ display: 'flex', gap: '2px', flexWrap: 'wrap' }}>
      {months.map((char, i) => (
        <div 
          key={i}
          title={`Month ${i + 1}: ${char}`}
          style={{
            width: '12px',
            height: '12px',
            backgroundColor: getStatusColor(char),
            borderRadius: '2px'
          }}
        />
      ))}
    </div>
  );
};

export const Metro2Analysis: React.FC<Props> = ({ profile }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ 
      marginTop: '24px', 
      border: '1px solid #e5e7eb', 
      borderRadius: '8px', 
      overflow: 'hidden',
      backgroundColor: 'white'
    }}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '100%',
          padding: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#f9fafb',
          border: 'none',
          borderBottom: isOpen ? '1px solid #e5e7eb' : 'none',
          cursor: 'pointer',
          textAlign: 'left'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ 
            backgroundColor: '#4f46e5', 
            color: 'white', 
            padding: '4px 8px', 
            borderRadius: '4px', 
            fontSize: '0.75rem', 
            fontWeight: 700 
          }}>
            METRO 2
          </div>
          <span style={{ fontWeight: 600, color: '#374151' }}>Technical Analysis & Data Standards</span>
        </div>
        <svg 
          width="20" 
          height="20" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round"
          style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s' }}
        >
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>

      {isOpen && (
        <div style={{ padding: '24px' }}>
          <div style={{ marginBottom: '24px' }}>
            <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Payment History Profile (Base Segment)
            </h4>
            <p style={{ fontSize: '0.9rem', color: '#4b5563', marginBottom: '16px', lineHeight: '1.5' }}>
              The Metro 2 format standardizes credit reporting. Below is the technical breakdown of the payment history profile strings (24-month lookback) and status codes used to calculate the risk score.
            </p>
            
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
                  <th style={{ padding: '8px', color: '#374151' }}>Account Ref</th>
                  <th style={{ padding: '8px', color: '#374151' }}>Status Code</th>
                  <th style={{ padding: '8px', color: '#374151' }}>ECOA</th>
                  <th style={{ padding: '8px', color: '#374151' }}>Payment Pattern (24m)</th>
                </tr>
              </thead>
              <tbody>
                {profile.trade_lines.map((tl, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '10px 8px', fontFamily: 'monospace' }}>
                      {tl.account_id_hash.substring(0, 8)}...
                      <div style={{ fontSize: '0.75em', color: '#9ca3af' }}>{tl.creditor_type}</div>
                    </td>
                    <td style={{ padding: '10px 8px' }}>
                      <span style={{ 
                        backgroundColor: '#f3f4f6', 
                        padding: '2px 6px', 
                        borderRadius: '4px', 
                        fontFamily: 'monospace',
                        fontWeight: 600
                      }}>
                        {tl.account_status}
                      </span>
                      <div style={{ fontSize: '0.75em', color: '#6b7280', marginTop: '2px' }}>
                        {METRO2_STATUS_CODES[tl.account_status] || 'Unknown Status'}
                      </div>
                    </td>
                    <td style={{ padding: '10px 8px' }}>
                      <span style={{ fontWeight: 600 }}>{tl.ecoa_code}</span>
                      <div style={{ fontSize: '0.75em', color: '#6b7280' }}>
                        {ECOA_CODES[tl.ecoa_code] || 'Unknown'}
                      </div>
                    </td>
                    <td style={{ padding: '10px 8px' }}>
                      <PaymentHistoryGrid historyString={tl.payment_history_24m} />
                      <div style={{ fontFamily: 'monospace', fontSize: '0.7em', color: '#9ca3af', marginTop: '4px', letterSpacing: '1px' }}>
                        {tl.payment_history_24m}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div style={{ backgroundColor: '#f9fafb', padding: '16px', borderRadius: '8px' }}>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: '#374151' }}>J1/J2 Segment Analysis</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.9rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Bankruptcy Flags:</span>
                  <span style={{ fontWeight: 600, color: profile.flags.has_bankruptcy ? '#ef4444' : '#10b981' }}>
                    {profile.flags.has_bankruptcy ? 'DETECTED' : 'None'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Consumer Information Indicator:</span>
                  <span style={{ fontWeight: 600 }}>
                    {profile.flags.is_deceased ? 'Deceased' : 'Normal'}
                  </span>
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: '#f9fafb', padding: '16px', borderRadius: '8px' }}>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: '#374151' }}>Payment Rating Derivation</h4>
               <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.9rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Worst Rating (Ever):</span>
                  <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>{profile.payment_behavior.worst_payment_status_ever}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Late 30 Count:</span>
                  <span style={{ fontWeight: 600 }}>{profile.payment_behavior.late_30_days_count}</span>
                </div>
                 <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#6b7280' }}>Late 90+ Count:</span>
                  <span style={{ fontWeight: 600 }}>{profile.payment_behavior.late_90_plus_days_count}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
