import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Sidebar } from './Sidebar';
import { SyntheticDataControl } from './SyntheticDataControl';
import { ConfigurationPanel } from './ConfigurationPanel';
import { SimulatorPanel } from './SimulatorPanel';
import { MetricsPanel } from './MetricsPanel';
import { TrainingPanel } from './TrainingPanel';
import type { V2Conversation } from '../types';

const API_URL = 'http://localhost:8000';
const OFFICER_HEADERS: Record<string, string> = {
  'x-officer-role': 'loan-officer-access',
};

type LeadStatus = 'active' | 'reviewing' | 'qualified' | 'closed';

const LeadsPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [leads, setLeads] = useState<V2Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');

  const selected = useMemo(() => leads.find((l) => l.id === selectedId) || null, [leads, selectedId]);

  const [draftBorrowerName, setDraftBorrowerName] = useState('');
  const [draftAssignedOfficer, setDraftAssignedOfficer] = useState('');
  const [draftStatus, setDraftStatus] = useState<LeadStatus>('active');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saveOk, setSaveOk] = useState(false);

  const refreshLeads = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_URL}/api/conversations`, { headers: OFFICER_HEADERS });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `Failed to load leads (${res.status})`);
      }
      const payload = (await res.json()) as V2Conversation[];
      setLeads(payload);
      if (payload.length > 0 && !selectedId) {
        setSelectedId(payload[0].id);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to load leads';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    void refreshLeads();
  }, [refreshLeads]);

  useEffect(() => {
    if (!selected) return;
    setDraftBorrowerName(selected.borrowerName || '');
    setDraftAssignedOfficer(selected.assignedOfficer || '');
    setDraftStatus(((selected.status as LeadStatus) || 'active') as LeadStatus);
    setSaveError('');
    setSaveOk(false);
  }, [selected]);

  const save = async () => {
    if (!selected) return;
    setSaving(true);
    setSaveError('');
    setSaveOk(false);
    try {
      const res = await fetch(`${API_URL}/api/conversations/${selected.id}`, {
        method: 'PATCH',
        headers: { ...OFFICER_HEADERS, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          borrowerName: draftBorrowerName.trim() || null,
          assignedOfficer: draftAssignedOfficer.trim() || null,
          status: draftStatus,
        }),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `Failed to save (${res.status})`);
      }
      const updated = (await res.json()) as V2Conversation;
      setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      setSaveOk(true);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to save';
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  };

  const approvalPct = selected?.approvalProbability ? Math.round(selected.approvalProbability.probability * 100) : null;
  const approvalColor =
    selected?.approvalProbability?.band === 'high'
      ? '#16a34a'
      : selected?.approvalProbability?.band === 'medium'
        ? '#f59e0b'
        : '#dc2626';

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'grid', gridTemplateColumns: '420px 1fr', gap: '16px' }}>
      <div style={{ border: '1px solid #e5e7eb', borderRadius: '12px', backgroundColor: '#ffffff', overflow: 'hidden' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h1 style={{ margin: 0, fontSize: '1.25rem' }} data-testid="text-leads-title">Leads</h1>
          <button
            type="button"
            onClick={() => void refreshLeads()}
            disabled={loading}
            style={{
              padding: '8px 10px',
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              backgroundColor: '#ffffff',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontWeight: 600,
            }}
          >
            Refresh
          </button>
        </div>

        {error ? (
          <div style={{ padding: '16px', color: '#b91c1c' }} data-testid="text-leads-error">{error}</div>
        ) : null}
        {loading ? (
          <div style={{ padding: '16px', color: '#6b7280' }}>Loading…</div>
        ) : null}

        <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
          {leads.map((l) => (
            <button
              key={l.id}
              type="button"
              onClick={() => setSelectedId(l.id)}
              style={{
                width: '100%',
                textAlign: 'left',
                border: 'none',
                borderBottom: '1px solid #f3f4f6',
                backgroundColor: selectedId === l.id ? '#eff6ff' : '#ffffff',
                padding: '12px 14px',
                cursor: 'pointer',
              }}
              data-testid={`lead-row-${l.id}`}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                <div style={{ fontWeight: 700, color: '#111827' }}>
                  {l.borrowerName || `Lead #${l.id.slice(0, 8)}`}
                </div>
                <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{l.status}</div>
              </div>
              <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '4px', display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                <div>Officer: {l.assignedOfficer || 'Unassigned'}</div>
                <div>Fit: {l.fitScore ?? '—'} / Serious: {l.seriousnessScore ?? '—'}</div>
              </div>
            </button>
          ))}
          {!loading && leads.length === 0 ? (
            <div style={{ padding: '16px', color: '#6b7280' }}>No leads yet.</div>
          ) : null}
        </div>
      </div>

      <div style={{ border: '1px solid #e5e7eb', borderRadius: '12px', backgroundColor: '#ffffff', padding: '18px' }}>
        <h2 style={{ marginTop: 0, marginBottom: '12px' }}>Lead Detail</h2>
        {!selected ? (
          <div style={{ color: '#6b7280' }}>Select a lead to edit.</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={{ gridColumn: '1 / -1', fontSize: '0.9rem', color: '#6b7280' }}>
              ID: <span style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>{selected.id}</span>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#374151', marginBottom: '6px' }}>Borrower Name</label>
              <input
                value={draftBorrowerName}
                onChange={(e) => setDraftBorrowerName(e.target.value)}
                placeholder="e.g. Jane Doe"
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #e5e7eb' }}
                data-testid="input-borrower-name"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#374151', marginBottom: '6px' }}>Assigned Officer</label>
              <input
                value={draftAssignedOfficer}
                onChange={(e) => setDraftAssignedOfficer(e.target.value)}
                placeholder="e.g. officer-1"
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #e5e7eb' }}
                data-testid="input-assigned-officer"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#374151', marginBottom: '6px' }}>Status</label>
              <select
                value={draftStatus}
                onChange={(e) => setDraftStatus(e.target.value as LeadStatus)}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #e5e7eb', backgroundColor: '#ffffff' }}
                data-testid="select-lead-status"
              >
                <option value="active">active</option>
                <option value="reviewing">reviewing</option>
                <option value="qualified">qualified</option>
                <option value="closed">closed</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => void save()}
                disabled={saving}
                style={{
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: '#111827',
                  color: '#ffffff',
                  fontWeight: 700,
                  cursor: saving ? 'not-allowed' : 'pointer',
                }}
                data-testid="button-save-lead"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
              {saveOk ? <div style={{ color: '#166534', fontWeight: 600 }} data-testid="text-save-ok">Saved</div> : null}
              {saveError ? <div style={{ color: '#b91c1c', fontWeight: 600 }} data-testid="text-save-error">{saveError}</div> : null}
            </div>

            <div style={{ gridColumn: '1 / -1', marginTop: '10px', borderTop: '1px solid #f3f4f6', paddingTop: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
                <h3 style={{ margin: 0, fontSize: '1rem', color: '#111827' }} data-testid="text-approval-probability-title">
                  Approval Probability
                </h3>
                <div style={{ fontWeight: 800, color: approvalPct == null ? '#6b7280' : approvalColor }} data-testid="text-approval-probability-score">
                  {approvalPct == null ? '—' : `${approvalPct}%`}
                </div>
              </div>

              <div style={{ marginTop: '10px' }}>
                <div style={{ height: '10px', borderRadius: '999px', backgroundColor: '#f3f4f6', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: approvalPct == null ? '0%' : `${approvalPct}%`,
                      height: '100%',
                      backgroundColor: approvalColor,
                      transition: 'width 200ms ease',
                    }}
                    aria-label="approval-probability-bar"
                  />
                </div>
                {selected.approvalProbability?.asOf ? (
                  <div style={{ marginTop: '6px', fontSize: '0.8rem', color: '#6b7280' }}>
                    As of {new Date(selected.approvalProbability.asOf).toLocaleString()}
                  </div>
                ) : null}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '12px' }}>
                <div style={{ border: '1px solid #f3f4f6', borderRadius: '10px', padding: '12px', backgroundColor: '#fafafa' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 800, color: '#111827', marginBottom: '8px' }} data-testid="text-approval-blockers-title">
                    Top Blockers
                  </div>
                  {selected.approvalProbability?.topBlockers?.length ? (
                    <div style={{ display: 'grid', gap: '8px' }}>
                      {selected.approvalProbability.topBlockers.map((b, idx) => (
                        <div key={`${b.title}-${idx}`} style={{ display: 'grid', gap: '2px' }} data-testid={`approval-blocker-${idx}`}>
                          <div style={{ fontWeight: 800, color: '#111827', fontSize: '0.9rem' }}>{b.title}</div>
                          <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>{b.detail}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>No blockers detected yet.</div>
                  )}
                </div>

                <div style={{ border: '1px solid #f3f4f6', borderRadius: '10px', padding: '12px', backgroundColor: '#fafafa' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 800, color: '#111827', marginBottom: '8px' }} data-testid="text-approval-actions-title">
                    Top Actions
                  </div>
                  {selected.approvalProbability?.topActions?.length ? (
                    <div style={{ display: 'grid', gap: '8px' }}>
                      {selected.approvalProbability.topActions.map((a, idx) => (
                        <div key={`${a.title}-${idx}`} style={{ display: 'grid', gap: '2px' }} data-testid={`approval-action-${idx}`}>
                          <div style={{ fontWeight: 800, color: '#111827', fontSize: '0.9rem' }}>{a.title}</div>
                          <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>{a.detail}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>No actions suggested yet.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'leads' | 'configuration' | 'synthetic' | 'simulator' | 'metrics' | 'training'>('synthetic');

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#ffffff' }}>
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <div style={{ marginLeft: '250px', padding: '32px', width: 'calc(100% - 250px)' }}>
        <div style={{ display: activeTab === 'leads' ? 'block' : 'none' }}>
          <LeadsPanel />
        </div>
        <div style={{ display: activeTab === 'synthetic' ? 'block' : 'none' }}>
          <SyntheticDataControl />
        </div>
        <div style={{ display: activeTab === 'configuration' ? 'block' : 'none' }}>
          <ConfigurationPanel />
        </div>
        <div style={{ display: activeTab === 'simulator' ? 'block' : 'none' }}>
          <SimulatorPanel />
        </div>
        <div style={{ display: activeTab === 'metrics' ? 'block' : 'none' }}>
          <MetricsPanel />
        </div>
        <div style={{ display: activeTab === 'training' ? 'block' : 'none' }}>
          <TrainingPanel />
        </div>
      </div>
    </div>
  );
};
