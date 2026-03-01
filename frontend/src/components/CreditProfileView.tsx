import React from 'react';
import type { ApplicantCreditProfile } from '../types';

interface Props {
  profile: ApplicantCreditProfile;
}

export const CreditProfileView: React.FC<Props> = ({ profile }) => {
  return (
    <div className="profile-container" style={{ padding: '20px', border: '1px solid #ccc', borderRadius: '8px', maxWidth: '800px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      {/* Header */}
      <div className="section" style={{ marginBottom: '20px' }}>
        <h2 style={{ borderBottom: '2px solid #333', paddingBottom: '10px' }}>Applicant Profile</h2>
        <div className="grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          <div><strong>Name:</strong> {profile.identity.full_name}</div>
          <div><strong>DOB:</strong> {profile.identity.date_of_birth}</div>
          <div style={{ gridColumn: '1 / -1' }}><strong>Address:</strong> {profile.identity.address.line1}, {profile.identity.address.city}, {profile.identity.address.territory}</div>
        </div>
      </div>

      {/* Summary */}
      <div className="section" style={{ marginBottom: '20px', backgroundColor: '#f9f9f9', padding: '15px', borderRadius: '4px' }}>
        <h3 style={{ marginTop: 0 }}>Credit Summary</h3>
        <div className="grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px' }}>
            <div className="score-box" style={{ textAlign: 'center', border: '1px solid #ddd', padding: '10px', backgroundColor: '#fff' }}>
                <div className="label" style={{ fontSize: '0.8em', color: '#666' }}>Credit Score</div>
                <div className="value" style={{ fontSize: '1.5em', fontWeight: 'bold' }}>{profile.summary.credit_score}</div>
                <div className="band" style={{ color: profile.summary.score_band === 'GOOD' ? 'green' : profile.summary.score_band === 'POOR' ? 'red' : 'orange' }}>{profile.summary.score_band}</div>
            </div>
            <div>
                <div style={{ fontSize: '0.8em', color: '#666' }}>Accounts</div>
                <div>{profile.summary.total_accounts}</div>
            </div>
            <div>
                <div style={{ fontSize: '0.8em', color: '#666' }}>Utilization</div>
                <div>{(profile.summary.utilization_ratio * 100).toFixed(1)}%</div>
            </div>
            <div>
                <div style={{ fontSize: '0.8em', color: '#666' }}>Total Debt</div>
                <div>XCD {profile.summary.total_current_balance_xcd.toLocaleString()}</div>
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
