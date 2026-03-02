import React, { useState } from 'react';
import type { ApplicantCreditProfile } from '../types';
import { Metro2Analysis } from './Metro2Analysis';

interface Props {
  profile: ApplicantCreditProfile;
}

const MetricLabelWithTooltip = ({ label, definition }: { label: string, definition: string }) => {
  const [show, setShow] = useState(false);
  
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', position: 'relative', marginBottom: '4px' }}>
      <span style={{ fontSize: '0.8em', color: '#666', fontWeight: 500 }}>{label}</span>
      <button 
        onClick={(e) => { e.stopPropagation(); setShow(!show); }}
        onBlur={() => setShow(false)}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 0,
          color: '#9ca3af',
          display: 'flex',
          alignItems: 'center',
          transition: 'color 0.2s'
        }}
        onMouseEnter={(e) => e.currentTarget.style.color = '#4f46e5'}
        onMouseLeave={(e) => e.currentTarget.style.color = '#9ca3af'}
        aria-label={`Definition of ${label}`}
        title="Click for definition"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
      </button>
      {show && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 50,
          backgroundColor: '#1f2937',
          color: 'white',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '0.75rem',
          width: '220px',
          marginTop: '8px',
          textAlign: 'center',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
          lineHeight: '1.4'
        }}>
          {definition}
          <div style={{ 
            position: 'absolute', 
            top: '-4px', 
            left: '50%', 
            transform: 'translateX(-50%) rotate(45deg)', 
            width: '8px', 
            height: '8px', 
            backgroundColor: '#1f2937' 
          }}></div>
        </div>
      )}
    </div>
  );
};

export const CreditProfileView: React.FC<Props> = ({ profile }) => {
  return (
    <div className="profile-container" style={{ padding: '24px', border: '1px solid #e5e7eb', borderRadius: '12px', maxWidth: '800px', margin: '0 auto', fontFamily: 'Inter, sans-serif', backgroundColor: 'white', boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)' }}>
      {/* Header */}
      <div className="section" style={{ marginBottom: '24px' }}>
        <h2 style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: '16px', marginBottom: '16px', fontSize: '1.25rem', fontWeight: 600, color: '#111827' }}>Applicant Profile</h2>
        <div className="grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '0.95rem' }}>
          <div><strong style={{ color: '#4b5563' }}>Name:</strong> <span style={{ color: '#111827' }}>{profile.identity.full_name}</span></div>
          <div><strong style={{ color: '#4b5563' }}>DOB:</strong> <span style={{ color: '#111827' }}>{profile.identity.date_of_birth}</span></div>
          <div style={{ gridColumn: '1 / -1' }}><strong style={{ color: '#4b5563' }}>Address:</strong> <span style={{ color: '#111827' }}>{profile.identity.address.line1}, {profile.identity.address.city}, {profile.identity.address.territory}</span></div>
        </div>
      </div>

      <Metro2Analysis profile={profile} />

      {/* Summary */}
      <div className="section" style={{ marginBottom: '24px', backgroundColor: '#f9fafb', padding: '20px', borderRadius: '8px', border: '1px solid #f3f4f6' }}>
        <h3 style={{ marginTop: 0, marginBottom: '16px', fontSize: '1rem', fontWeight: 600, color: '#374151' }}>Credit Summary</h3>
        <div className="grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
            <div className="score-box" style={{ textAlign: 'center', border: '1px solid #e5e7eb', padding: '16px', backgroundColor: '#fff', borderRadius: '8px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)' }}>
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <MetricLabelWithTooltip 
                    label="Credit Score" 
                    definition="A numerical expression based on a level analysis of a person's credit files, to represent the creditworthiness of an individual." 
                  />
                </div>
                <div className="value" style={{ fontSize: '1.875rem', fontWeight: 700, color: '#111827', lineHeight: 1 }}>{profile.summary.credit_score}</div>
                <div className="band" style={{ 
                  marginTop: '4px',
                  fontSize: '0.75rem', 
                  fontWeight: 600,
                  color: profile.summary.score_band === 'GOOD' ? '#059669' : profile.summary.score_band === 'POOR' ? '#dc2626' : '#d97706',
                  backgroundColor: profile.summary.score_band === 'GOOD' ? '#ecfdf5' : profile.summary.score_band === 'POOR' ? '#fef2f2' : '#fffbeb',
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  display: 'inline-block'
                }}>{profile.summary.score_band}</div>
            </div>
            <div style={{ textAlign: 'center', padding: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <MetricLabelWithTooltip 
                    label="Accounts" 
                    definition="The total number of open and closed credit accounts associated with the applicant." 
                  />
                </div>
                <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#111827' }}>{profile.summary.total_accounts}</div>
            </div>
            <div style={{ textAlign: 'center', padding: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <MetricLabelWithTooltip 
                    label="Utilization" 
                    definition="The ratio of current credit card balances to credit limits. Lower is generally better (below 30%)." 
                  />
                </div>
                <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#111827' }}>{(profile.summary.utilization_ratio * 100).toFixed(1)}%</div>
            </div>
            <div style={{ textAlign: 'center', padding: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <MetricLabelWithTooltip 
                    label="Total Debt" 
                    definition="The sum of all current balances across all credit accounts." 
                  />
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 600, color: '#111827' }}>XCD {profile.summary.total_current_balance_xcd.toLocaleString()}</div>
            </div>
        </div>
      </div>

      {/* Trade Lines */}
      <div className="section" style={{ marginBottom: '20px' }}>
        <h3>Trade Lines</h3>
        <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
                <tr style={{ backgroundColor: '#eee', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Type</th>
                    <th style={{ padding: '8px' }}>Creditor</th>
                    <th style={{ padding: '8px' }}>Status</th>
                    <th style={{ padding: '8px' }}>Balance</th>
                    <th style={{ padding: '8px' }}>History (24m)</th>
                </tr>
            </thead>
            <tbody>
                {profile.trade_lines.map((tl, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                        <td style={{ padding: '8px' }}>{tl.account_type}</td>
                        <td style={{ padding: '8px' }}>{tl.creditor_type}</td>
                        <td style={{ padding: '8px' }}>{tl.account_status}</td>
                        <td style={{ padding: '8px' }}>XCD {tl.current_balance_xcd.toLocaleString()}</td>
                        <td className="mono" style={{ padding: '8px', fontFamily: 'monospace', letterSpacing: '1px' }}>{tl.payment_history_24m}</td>
                    </tr>
                ))}
            </tbody>
        </table>
      </div>
      
      {/* Metadata Footer */}
      <div className="metadata-footer" style={{ fontSize: '0.7em', color: '#999', borderTop: '1px solid #eee', paddingTop: '10px' }}>
        Source: {profile.metadata.source.toUpperCase()} | Generated: {profile.metadata.query_timestamp} | Archetype: {profile.metadata.synthetic_archetype}
      </div>
    </div>
  );
};
