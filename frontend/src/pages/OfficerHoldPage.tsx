import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useLocation } from 'react-router-dom';
import type { V2Conversation, V2Loan, V2ApprovalProbability } from '../types';
import { getMetricsClient } from '../api/metricsClient';
import type { AIMetrics, AggregateAIMetrics } from '../types/metrics';

type HoldKind = 'lead' | 'loan';
type HoldFilterMode = 'holds' | 'all';

export type OfficerHoldPageProps = {
  /**
   * Which tab is selected by default (unless a deep-link query param overrides it).
   * - lead: officer "Leads" world
   * - loan: officer "Loans/Pipeline" world
   */
  defaultKind?: HoldKind;
  /**
   * Filter behavior for lead list:
   * - holds: only show leads that appear "on hold" (blockers > 0 or reviewing)
   * - all: show all leads
   */
  leadFilter?: HoldFilterMode;
  /**
   * Filter behavior for loan list:
   * - holds: only show loans that appear "on hold" (awaiting docs or missing/rejected docs)
   * - all: show all loans
   */
  loanFilter?: HoldFilterMode;
  title?: string;
  subtitle?: string;
};

type HoldListItem =
  | {
      kind: 'lead';
      id: string;
      borrowerName: string | null;
      status: string;
      assignedOfficer: string | null;
      createdAt: string | null;
      approvalProbability: V2ApprovalProbability | null;
      recommendedProducts: V2Conversation['recommendedProducts'];
    }
  | {
      kind: 'loan';
      id: string;
      borrowerName: string | null;
      status: string | null;
      loanType: string | null;
      loanAmount: string | null;
      currentPhaseId: string | null;
      conversationId: string | null;
      stpProcessingStatus: string | null;
      documentChecklist: V2Loan['documentChecklist'] | null;
      updatedAt: string | null;
    };

const API_BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');
const OFFICER_HEADERS: Record<string, string> = { Authorization: 'Bearer loan-officer-access' };

function isApprovalNavigator(v: unknown): v is V2ApprovalProbability {
  if (!v || typeof v !== 'object') return false;
  const r = v as Record<string, unknown>;
  return typeof r.probability === 'number' && Array.isArray(r.topBlockers) && Array.isArray(r.topActions);
}

function getLeadHoldReason(ap: V2ApprovalProbability | null): { blockers: number; actions: number } {
  if (!ap) return { blockers: 0, actions: 0 };
  return { blockers: Array.isArray(ap.topBlockers) ? ap.topBlockers.length : 0, actions: Array.isArray(ap.topActions) ? ap.topActions.length : 0 };
}

function getLoanMissingCount(checklist: V2Loan['documentChecklist'] | null): number {
  if (!checklist?.items) return 0;
  return checklist.items.filter((i) => (i.status || '').toLowerCase() === 'missing' || (i.status || '').toLowerCase() === 'rejected').length;
}

function formatShortId(id: string) {
  return id.slice(0, 8);
}

function Pill({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'danger' | 'info' | 'success' }) {
  const map: Record<string, string> = {
    neutral: 'bg-slate-100 dark:bg-white/[0.06] text-slate-700 dark:text-slate-300 border-slate-200/60 dark:border-white/[0.08]',
    danger: 'bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-200 border-red-200/70 dark:border-red-500/20',
    info: 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-200 border-blue-200/70 dark:border-blue-500/20',
    success: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-200 border-emerald-200/70 dark:border-emerald-500/20',
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${map[tone]}`}>
      {children}
    </span>
  );
}

function ApprovalNavigatorCard({ approvalProbability }: { approvalProbability: V2ApprovalProbability | null }) {
  const ap = approvalProbability;
  const probability = ap?.probability ?? null;
  const blockers = ap?.topBlockers ?? [];
  const actions = ap?.topActions ?? [];

  return (
    <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Approval Probability</h3>
        {ap?.band ? <Pill tone={ap.band === 'high' ? 'success' : ap.band === 'medium' ? 'info' : 'danger'}>{ap.band}</Pill> : null}
      </div>
      <div className="mt-3 text-3xl font-black tracking-tight text-slate-900 dark:text-white">
        {probability === null ? '—' : `${Math.round(probability * 100)}%`}
      </div>

      {blockers.length === 0 && actions.length === 0 ? (
        <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No blockers detected.</div>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4">
          {blockers.length ? (
            <div>
              <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Top blockers</div>
              <div className="mt-2 grid gap-2">
                {blockers.slice(0, 3).map((b, idx) => (
                  <div key={idx} className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-bold text-slate-900 dark:text-white">{b.title}</div>
                      {b.severity ? <Pill tone={b.severity === 'high' ? 'danger' : b.severity === 'medium' ? 'info' : 'neutral'}>{b.severity}</Pill> : null}
                    </div>
                    {b.detail ? <div className="mt-1 text-[12px] leading-relaxed text-slate-600 dark:text-slate-300">{b.detail}</div> : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {actions.length ? (
            <div>
              <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Next actions</div>
              <div className="mt-2 grid gap-2">
                {actions.slice(0, 3).map((a, idx) => (
                  <div key={idx} className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-bold text-slate-900 dark:text-white">{a.title}</div>
                      {a.impact ? <Pill tone={a.impact === 'high' ? 'danger' : a.impact === 'medium' ? 'info' : 'neutral'}>{a.impact}</Pill> : null}
                    </div>
                    {a.detail ? <div className="mt-1 text-[12px] leading-relaxed text-slate-600 dark:text-slate-300">{a.detail}</div> : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

function AIQualityCard({
  conversationId,
  compact = false,
}: {
  conversationId?: string | null;
  compact?: boolean;
}) {
  const metricsClient = React.useMemo(() => getMetricsClient({ debug: false }), []);
  const [adminAuthenticated, setAdminAuthenticated] = React.useState(metricsClient.isAuthenticated());
  const [adminPassword, setAdminPassword] = React.useState('');
  const [aiMetrics, setAiMetrics] = React.useState<AIMetrics | null>(null);
  const [aggregate, setAggregate] = React.useState<AggregateAIMetrics | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState('');

  const refresh = React.useCallback(async () => {
    if (!metricsClient.isAuthenticated()) return;
    setBusy(true);
    setError('');
    try {
      // Aggregate is always useful for officers as a system-wide health signal.
      const agg = await metricsClient.getAggregateAIMetrics({ period: 'today' });
      setAggregate(agg);
      // Per-conversation AI metrics are optional (only available for v3 sessions).
      if (conversationId) {
        const ai = await metricsClient.getAIMetrics(conversationId);
        setAiMetrics(ai);
      } else {
        setAiMetrics(null);
      }
    } catch (e) {
      setAiMetrics(null);
      // Don't block the UI if the conversation isn't found in v3 state.
      setError(e instanceof Error ? e.message : 'Failed to load AI metrics');
    } finally {
      setBusy(false);
    }
  }, [conversationId, metricsClient]);

  React.useEffect(() => {
    if (!adminAuthenticated) return;
    void refresh();
  }, [adminAuthenticated, refresh]);

  const onAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await metricsClient.authenticateAdmin(adminPassword);
      setAdminAuthenticated(true);
      setAdminPassword('');
      await refresh();
    } catch {
      setError('Invalid admin password');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">AI Quality (RAGAS)</h3>
          <p className="mt-0.5 text-[12px] text-slate-500 dark:text-slate-400">
            System health (aggregate) and—when available—per-conversation RAGAS.
          </p>
        </div>
        <Link
          to="/metrics"
          className="shrink-0 inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm no-underline"
        >
          Open Metrics
        </Link>
      </div>

      {!adminAuthenticated ? (
        <form onSubmit={onAuth} className="mt-4 grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3 items-end">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-300">Admin password (AI metrics)</label>
            <input
              type="password"
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
              className="w-full rounded-2xl border border-slate-200/60 dark:border-white/[0.08] bg-white/70 dark:bg-white/[0.03] px-3 py-2 text-sm text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-[#0078D4]/30"
              placeholder="Enter admin password"
            />
          </div>
          <button
            type="submit"
            disabled={busy || !adminPassword.trim()}
            className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-[#0078D4] to-[#005EA6] px-4 py-2.5 text-sm font-extrabold text-white shadow-lg shadow-[#0078D4]/20 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {busy ? 'Authenticating…' : 'Authenticate'}
          </button>
          {error ? <div className="md:col-span-2 text-sm font-semibold text-red-700 dark:text-red-300">{error}</div> : null}
        </form>
      ) : (
        <>
          <div className="mt-4 flex items-center gap-3">
            <button
              type="button"
              onClick={() => refresh()}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm disabled:opacity-60"
            >
              {busy ? 'Refreshing…' : 'Refresh AI metrics'}
            </button>
            {error ? <div className="text-sm font-semibold text-red-700 dark:text-red-300">{error}</div> : null}
          </div>

          {aggregate ? (
            <div className={`mt-4 grid gap-3 ${compact ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-3'}`}>
              <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Hallucination (avg)</div>
                <div className="mt-1 text-xl font-black text-slate-900 dark:text-white">{(aggregate.average_hallucination_rate * 100).toFixed(1)}%</div>
              </div>
              <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">RAGAS overall (avg)</div>
                <div className="mt-1 text-xl font-black text-slate-900 dark:text-white">
                  {aggregate.average_ragas_overall === null ? '—' : `${(aggregate.average_ragas_overall * 100).toFixed(1)}%`}
                </div>
              </div>
              <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Latency p95</div>
                <div className="mt-1 text-xl font-black text-slate-900 dark:text-white">{(aggregate.average_latency_p95 / 1000).toFixed(2)}s</div>
              </div>
            </div>
          ) : (
            <div className="mt-4 text-sm text-slate-500 dark:text-slate-400">Aggregate AI metrics unavailable.</div>
          )}

          {conversationId ? (
            <div className="mt-4 rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
              <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Conversation-level (if v3)</div>
              {aiMetrics ? (
                <div className="mt-2 grid grid-cols-1 md:grid-cols-4 gap-2">
                  <div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">RAGAS overall</div>
                    <div className="text-sm font-extrabold text-slate-900 dark:text-white">
                      {aiMetrics.ragas_overall === null ? '—' : `${(aiMetrics.ragas_overall * 100).toFixed(1)}%`}
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">Faithfulness</div>
                    <div className="text-sm font-extrabold text-slate-900 dark:text-white">
                      {aiMetrics.ragas_faithfulness === null ? '—' : `${(aiMetrics.ragas_faithfulness * 100).toFixed(1)}%`}
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">Relevance</div>
                    <div className="text-sm font-extrabold text-slate-900 dark:text-white">
                      {aiMetrics.ragas_relevance === null ? '—' : `${(aiMetrics.ragas_relevance * 100).toFixed(1)}%`}
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">Context precision</div>
                    <div className="text-sm font-extrabold text-slate-900 dark:text-white">
                      {aiMetrics.ragas_context_precision === null ? '—' : `${(aiMetrics.ragas_context_precision * 100).toFixed(1)}%`}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                  No per-conversation AI metrics found for this ID (common for v2 leads).
                </div>
              )}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

function LeadHoldDetail({
  lead,
  onSaved,
  relatedLoans,
}: {
  lead: Extract<HoldListItem, { kind: 'lead' }>;
  onSaved: (updated: V2Conversation) => void;
  relatedLoans: V2Loan[];
}) {
  const [draftBorrowerName, setDraftBorrowerName] = React.useState(lead.borrowerName ?? '');
  const [draftAssignedOfficer, setDraftAssignedOfficer] = React.useState(lead.assignedOfficer ?? '');
  const [draftStatus, setDraftStatus] = React.useState(lead.status ?? 'active');

  React.useEffect(() => {
    setDraftBorrowerName(lead.borrowerName ?? '');
    setDraftAssignedOfficer(lead.assignedOfficer ?? '');
    setDraftStatus(lead.status ?? 'active');
  }, [lead.id]);

  const save = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/conversations/${lead.id}`, {
        method: 'PATCH',
        headers: { ...OFFICER_HEADERS, 'content-type': 'application/json' },
        body: JSON.stringify({
          borrowerName: draftBorrowerName.trim() || null,
          assignedOfficer: draftAssignedOfficer.trim() || null,
          status: draftStatus,
        }),
      });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to save (${res.status})`);
      }
      return (await res.json()) as V2Conversation;
    },
    onSuccess: (updated) => onSaved(updated),
  });

  return (
    <div className="space-y-5">
      <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-black tracking-tight text-slate-900 dark:text-white">
              {lead.borrowerName?.trim() ? lead.borrowerName : `Lead #${formatShortId(lead.id)}`}
            </h2>
            <div className="mt-1 flex flex-wrap gap-2">
              <Pill tone="info">Lead</Pill>
              <Pill>{draftStatus}</Pill>
              {lead.assignedOfficer ? <Pill>{`Officer: ${lead.assignedOfficer}`}</Pill> : <Pill>Unassigned</Pill>}
            </div>
          </div>
          <div className="shrink-0 text-right">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">Created</div>
            <div className="text-xs font-semibold text-slate-700 dark:text-slate-200">{lead.createdAt ? new Date(lead.createdAt).toLocaleString() : '—'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            to={`/dashboard?leadId=${encodeURIComponent(lead.id)}`}
            className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm no-underline"
          >
            Open in Leads
          </Link>
          <Link
            to={`/officer-chat?conversationId=${encodeURIComponent(lead.id)}`}
            className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm no-underline"
          >
            Open in Officer Chat
          </Link>
          {relatedLoans.length > 0 ? (
            <Link
              to={`/pipeline?loanId=${encodeURIComponent(relatedLoans[0].id)}`}
              className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm no-underline"
            >
              Open related loan
            </Link>
          ) : null}
        </div>

        <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-300" htmlFor={`lead-borrower-${lead.id}`}>
              Borrower name
            </label>
            <input
              id={`lead-borrower-${lead.id}`}
              value={draftBorrowerName}
              onChange={(e) => setDraftBorrowerName(e.target.value)}
              className="w-full rounded-2xl border border-slate-200/60 dark:border-white/[0.08] bg-white/70 dark:bg-white/[0.03] px-3 py-2 text-sm text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-[#0078D4]/30"
              placeholder="e.g. Ada Lovelace"
              data-testid="lead-borrower-name-input"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-300" htmlFor={`lead-officer-${lead.id}`}>
              Assigned officer
            </label>
            <input
              id={`lead-officer-${lead.id}`}
              value={draftAssignedOfficer}
              onChange={(e) => setDraftAssignedOfficer(e.target.value)}
              className="w-full rounded-2xl border border-slate-200/60 dark:border-white/[0.08] bg-white/70 dark:bg-white/[0.03] px-3 py-2 text-sm text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-[#0078D4]/30"
              placeholder="e.g. officer-1"
              data-testid="lead-assigned-officer-input"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-300" htmlFor={`lead-status-${lead.id}`}>
              Status
            </label>
            <select
              id={`lead-status-${lead.id}`}
              value={draftStatus}
              onChange={(e) => setDraftStatus(e.target.value)}
              className="w-full rounded-2xl border border-slate-200/60 dark:border-white/[0.08] bg-white/70 dark:bg-white/[0.03] px-3 py-2 text-sm text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-[#0078D4]/30"
              data-testid="lead-status-select"
            >
              <option value="active">active</option>
              <option value="reviewing">reviewing</option>
              <option value="qualified">qualified</option>
              <option value="closed">closed</option>
            </select>
          </div>
        </div>

        <div className="mt-5 flex items-center gap-3">
          <button
            type="button"
            onClick={() => save.mutate()}
            disabled={save.isPending}
            className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-[#0078D4] to-[#005EA6] px-4 py-2.5 text-sm font-extrabold text-white shadow-lg shadow-[#0078D4]/20 disabled:opacity-60 disabled:cursor-not-allowed"
            data-testid="lead-save-button"
          >
            {save.isPending ? 'Saving…' : 'Save'}
          </button>
          {save.isSuccess ? <div className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">Saved</div> : null}
          {save.isError ? (
            <div className="text-sm font-semibold text-red-700 dark:text-red-300">{(save.error as Error).message}</div>
          ) : null}
        </div>
      </div>

      <ApprovalNavigatorCard approvalProbability={lead.approvalProbability} />

      <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Recommended products</h3>
          <Pill>{lead.recommendedProducts?.length ?? 0}</Pill>
        </div>
        {!lead.recommendedProducts || lead.recommendedProducts.length === 0 ? (
          <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No recommendations yet.</div>
        ) : (
          <div className="mt-4 grid gap-2">
            {lead.recommendedProducts.slice(0, 6).map((p, idx) => (
              <div key={`${p.name}-${idx}`} className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">{p.name}</div>
                  <Pill tone="info">{p.type}</Pill>
                </div>
                <div className="mt-1 text-[12px] text-slate-600 dark:text-slate-300">
                  Rate: {p.estimatedRate} · EMI: {p.estimatedEmi} · Tenure: {p.tenure}
                </div>
                {p.recommendation ? (
                  <div className="mt-2 text-[12px] leading-relaxed text-slate-700 dark:text-slate-200">{p.recommendation}</div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Related loans</h3>
          <Pill>{relatedLoans.length}</Pill>
        </div>
        {relatedLoans.length === 0 ? (
          <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No loans linked to this lead yet.</div>
        ) : (
          <div className="mt-4 grid gap-2">
            {relatedLoans.map((l) => (
              <Link
                key={l.id}
                to={`/pipeline?loanId=${encodeURIComponent(l.id)}`}
                className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3 no-underline hover:bg-white/90 dark:hover:bg-white/[0.05] transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white truncate">
                      {l.loanType || 'Loan'} · {l.loanAmount || '—'}
                    </div>
                    <div className="mt-0.5 text-[12px] text-slate-600 dark:text-slate-300 truncate">
                      Status: {l.status || '—'} {(l as any).stpProcessingStatus ? `· STP: ${(l as any).stpProcessingStatus}` : ''}
                    </div>
                  </div>
                  <Pill tone={getLoanMissingCount(l.documentChecklist) > 0 ? 'danger' : 'success'}>
                    {getLoanMissingCount(l.documentChecklist) > 0 ? `${getLoanMissingCount(l.documentChecklist)} missing` : 'OK'}
                  </Pill>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <AIQualityCard conversationId={lead.id} />
    </div>
  );
}

type LoanChecklistItem = {
  name: string;
  status: 'missing' | 'submitted' | 'verified' | 'rejected';
  updatedAt: string;
  upload?: { fileName?: string; uploadedAt?: string; extractedPreview?: string } | null;
};

function LoanHoldDetail({
  loan,
  onUpdated,
  phases,
}: {
  loan: Extract<HoldListItem, { kind: 'loan' }>;
  onUpdated: (updated: V2Loan) => void;
  phases: Array<{ id: string; name: string }>;
}) {
  const items: LoanChecklistItem[] = React.useMemo(() => {
    const raw = loan.documentChecklist?.items ?? [];
    return raw
      .map((i) => {
        const name = String((i as any).name ?? '');
        const statusRaw = String((i as any).status ?? 'missing').toLowerCase();
        const updatedAt = String((i as any).updatedAt ?? '');
        const upload = (i as any).upload && typeof (i as any).upload === 'object' ? (i as any).upload : null;
        const status: LoanChecklistItem['status'] =
          statusRaw === 'verified' || statusRaw === 'submitted' || statusRaw === 'rejected' ? statusRaw : 'missing';
        return { name, status, updatedAt, upload };
      })
      .filter((x) => x.name.trim().length > 0);
  }, [loan.documentChecklist]);

  const updateStatus = useMutation({
    mutationFn: async (payload: { name: string; status: LoanChecklistItem['status'] }) => {
      const res = await fetch(`${API_BASE_URL}/api/loans/${loan.id}/documents`, {
        method: 'PATCH',
        headers: { ...OFFICER_HEADERS, 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to update (${res.status})`);
      }
      return (await res.json()) as V2Loan;
    },
    onSuccess: onUpdated,
  });

  const uploadDoc = useMutation({
    mutationFn: async (payload: { name: string; file: File }) => {
      const fd = new FormData();
      fd.append('name', payload.name);
      fd.append('file', payload.file);
      const res = await fetch(`${API_BASE_URL}/api/loans/${loan.id}/documents/upload`, {
        method: 'POST',
        headers: OFFICER_HEADERS,
        body: fd,
      });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Upload failed (${res.status})`);
      }
      return (await res.json()) as V2Loan;
    },
    onSuccess: onUpdated,
  });

  const missingCount = getLoanMissingCount(loan.documentChecklist);
  const isAwaitingDocs = (loan.stpProcessingStatus || '').toLowerCase() === 'awaiting_documents';

  const updatePhase = useMutation({
    mutationFn: async (phaseId: string | null) => {
      const res = await fetch(`${API_BASE_URL}/api/loans/${loan.id}`, {
        method: 'PATCH',
        headers: { ...OFFICER_HEADERS, 'content-type': 'application/json' },
        body: JSON.stringify({ currentPhaseId: phaseId }),
      });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to update phase (${res.status})`);
      }
      return (await res.json()) as V2Loan;
    },
    onSuccess: onUpdated,
  });

  const [memoJson, setMemoJson] = React.useState<unknown>(null);
  const generateMemo = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/loans/${loan.id}/underwriting-memo`, {
        method: 'POST',
        headers: OFFICER_HEADERS,
      });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to generate memo (${res.status})`);
      }
      return (await res.json()) as { underwritingMemo?: unknown; loan?: V2Loan } | V2Loan;
    },
    onSuccess: (payload) => {
      // backend sometimes returns full loan, sometimes wrapper; be tolerant.
      const anyPayload: any = payload as any;
      const updatedLoan: V2Loan | null = anyPayload?.id ? (payload as V2Loan) : anyPayload?.loan?.id ? (anyPayload.loan as V2Loan) : null;
      const memo = anyPayload?.underwritingMemo ?? anyPayload?.underwriting_memo ?? anyPayload?.loan?.underwritingMemo ?? null;
      if (updatedLoan) onUpdated(updatedLoan);
      setMemoJson(memo);
    },
  });

  return (
    <div className="space-y-5">
      <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-black tracking-tight text-slate-900 dark:text-white">
              {loan.borrowerName?.trim() ? loan.borrowerName : `Loan #${formatShortId(loan.id)}`}
            </h2>
            <div className="mt-1 flex flex-wrap gap-2">
              <Pill tone="info">Loan</Pill>
              {loan.status ? <Pill>{loan.status}</Pill> : <Pill>—</Pill>}
              {isAwaitingDocs ? <Pill tone="danger">Awaiting documents</Pill> : loan.stpProcessingStatus ? <Pill>{loan.stpProcessingStatus}</Pill> : null}
              {missingCount > 0 ? <Pill tone="danger">{missingCount} missing</Pill> : <Pill tone="success">No missing</Pill>}
            </div>
            <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {loan.loanType || 'Loan'} · {loan.loanAmount || '—'}
            </div>
          </div>
          <div className="shrink-0 text-right">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">Updated</div>
            <div className="text-xs font-semibold text-slate-700 dark:text-slate-200">{loan.updatedAt ? new Date(loan.updatedAt).toLocaleString() : '—'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            to={`/pipeline?loanId=${encodeURIComponent(loan.id)}`}
            className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm no-underline"
          >
            Open in Pipeline
          </Link>
          {loan.conversationId ? (
            <>
              <Link
                to={`/dashboard?leadId=${encodeURIComponent(loan.conversationId)}`}
                className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm no-underline"
              >
                Open lead
              </Link>
              <Link
                to={`/officer-chat?conversationId=${encodeURIComponent(loan.conversationId)}`}
                className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm no-underline"
              >
                Open in Officer Chat
              </Link>
            </>
          ) : null}
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3 items-end">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-300">Phase</label>
            <select
              value={loan.currentPhaseId ?? ''}
              onChange={(e) => updatePhase.mutate(e.target.value ? e.target.value : null)}
              disabled={updatePhase.isPending}
              className="w-full rounded-2xl border border-slate-200/60 dark:border-white/[0.08] bg-white/70 dark:bg-white/[0.03] px-3 py-2 text-sm text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-[#0078D4]/30 disabled:opacity-60"
              data-testid="loan-phase-select"
            >
              <option value="">Unassigned</option>
              {phases.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={() => generateMemo.mutate()}
            disabled={generateMemo.isPending}
            className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-[#0078D4] to-[#005EA6] px-4 py-2.5 text-sm font-extrabold text-white shadow-lg shadow-[#0078D4]/20 disabled:opacity-60 disabled:cursor-not-allowed"
            data-testid="loan-generate-memo-button"
          >
            {generateMemo.isPending ? 'Generating…' : 'Generate underwriting memo'}
          </button>
          {updatePhase.isError ? <div className="md:col-span-2 text-sm font-semibold text-red-700 dark:text-red-300">{(updatePhase.error as Error).message}</div> : null}
          {generateMemo.isError ? <div className="md:col-span-2 text-sm font-semibold text-red-700 dark:text-red-300">{(generateMemo.error as Error).message}</div> : null}
        </div>
      </div>

      <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Document checklist</h3>
          <Pill>{items.length} items</Pill>
        </div>

        {items.length === 0 ? (
          <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No checklist found for this loan.</div>
        ) : (
          <div className="mt-4 grid gap-3">
            {items.map((it) => (
              <div key={it.name} className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-bold text-slate-900 dark:text-white">{it.name}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <Pill tone={it.status === 'verified' ? 'success' : it.status === 'submitted' ? 'info' : it.status === 'rejected' ? 'danger' : 'danger'}>
                        {it.status}
                      </Pill>
                      {it.upload?.fileName ? <Pill>{it.upload.fileName}</Pill> : <Pill>Not uploaded</Pill>}
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center gap-2">
                    <label className="sr-only" htmlFor={`status-${loan.id}-${it.name}`}>
                      Update status for {it.name}
                    </label>
                    <select
                      id={`status-${loan.id}-${it.name}`}
                      value={it.status}
                      onChange={(e) => updateStatus.mutate({ name: it.name, status: e.target.value as LoanChecklistItem['status'] })}
                      disabled={updateStatus.isPending}
                      className="rounded-xl border border-slate-200/60 dark:border-white/[0.08] bg-white/80 dark:bg-white/[0.04] px-2 py-1.5 text-xs text-slate-800 dark:text-slate-200 outline-none focus:ring-2 focus:ring-[#0078D4]/30 disabled:opacity-60"
                    >
                      <option value="missing">missing</option>
                      <option value="submitted">submitted</option>
                      <option value="verified">verified</option>
                      <option value="rejected">rejected</option>
                    </select>

                    <input
                      type="file"
                      accept=".pdf,image/*"
                      className="hidden"
                      id={`file-${loan.id}-${it.name}`}
                      onChange={(e) => {
                        const file = e.currentTarget.files?.[0];
                        e.currentTarget.value = '';
                        if (file) uploadDoc.mutate({ name: it.name, file });
                      }}
                    />
                    <label
                      htmlFor={`file-${loan.id}-${it.name}`}
                      className="cursor-pointer inline-flex items-center justify-center rounded-xl bg-blue-50 dark:bg-blue-500/10 border border-blue-200/70 dark:border-blue-500/20 px-3 py-1.5 text-xs font-semibold text-blue-700 dark:text-blue-200 hover:bg-blue-100 dark:hover:bg-blue-500/20 transition-colors"
                    >
                      {uploadDoc.isPending ? 'Uploading…' : it.upload?.fileName ? 'Replace' : 'Upload'}
                    </label>
                  </div>
                </div>

                {it.upload?.extractedPreview ? (
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs font-semibold text-slate-600 dark:text-slate-300">Preview extracted text</summary>
                    <pre className="mt-2 whitespace-pre-wrap text-[12px] leading-relaxed text-slate-700 dark:text-slate-200 bg-white/60 dark:bg-black/20 border border-slate-200/60 dark:border-white/[0.06] rounded-2xl p-3 max-h-44 overflow-auto">
                      {it.upload.extractedPreview}
                    </pre>
                  </details>
                ) : null}
              </div>
            ))}
          </div>
        )}

        {updateStatus.isError ? <div className="mt-3 text-sm font-semibold text-red-700 dark:text-red-300">{(updateStatus.error as Error).message}</div> : null}
        {uploadDoc.isError ? <div className="mt-3 text-sm font-semibold text-red-700 dark:text-red-300">{(uploadDoc.error as Error).message}</div> : null}
      </div>

      {memoJson ? (
        <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Underwriting memo</h3>
            <Pill tone="info">Generated</Pill>
          </div>
          <pre className="mt-4 whitespace-pre-wrap text-[12px] leading-relaxed text-slate-700 dark:text-slate-200 bg-white/60 dark:bg-black/20 border border-slate-200/60 dark:border-white/[0.06] rounded-2xl p-4 max-h-[360px] overflow-auto">
            {JSON.stringify(memoJson, null, 2)}
          </pre>
        </div>
      ) : null}
    </div>
  );
}

export default function OfficerHoldPage({
  defaultKind = 'lead',
  leadFilter = 'holds',
  loanFilter = 'holds',
  title = 'Officer Hold',
  subtitle = 'Review and resolve blockers across leads and loans.',
}: OfficerHoldPageProps) {
  const queryClient = useQueryClient();
  const routeLocation = useLocation();
  const routeLeadId = React.useMemo(() => (new URLSearchParams(routeLocation.search).get('leadId') || '').trim(), [routeLocation.search]);
  const routeLoanId = React.useMemo(() => (new URLSearchParams(routeLocation.search).get('loanId') || '').trim(), [routeLocation.search]);

  const conversations = useQuery({
    queryKey: ['officer-hold', 'conversations'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/conversations`, { headers: OFFICER_HEADERS });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to load leads (${res.status})`);
      }
      return (await res.json()) as V2Conversation[];
    },
    staleTime: 5_000,
  });

  const loans = useQuery({
    queryKey: ['officer-hold', 'loans'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/loans`, { headers: OFFICER_HEADERS });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to load loans (${res.status})`);
      }
      return (await res.json()) as V2Loan[];
    },
    staleTime: 5_000,
  });

  const phases = useQuery({
    queryKey: ['officer-hold', 'phases'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/phases`);
      if (!res.ok) return [] as Array<{ id: string; name: string }>;
      const data = (await res.json()) as Array<{ id: string; name: string }>;
      return Array.isArray(data) ? data : [];
    },
    staleTime: 30_000,
  });

  const holds = React.useMemo<HoldListItem[]>(() => {
    const leadItems: HoldListItem[] = (conversations.data ?? [])
      .map((c) => {
        const ap = isApprovalNavigator(c.approvalProbability) ? c.approvalProbability : null;
        return {
          kind: 'lead' as const,
          id: c.id,
          borrowerName: c.borrowerName,
          status: c.status,
          assignedOfficer: c.assignedOfficer,
          createdAt: c.createdAt,
          approvalProbability: ap,
          recommendedProducts: c.recommendedProducts,
        };
      })
      .filter((c) => {
        if (leadFilter === 'all') return true;
        const { blockers } = getLeadHoldReason(c.approvalProbability);
        // Treat any blocker as a hold signal, or explicit reviewing status
        return blockers > 0 || (c.status || '').toLowerCase() === 'reviewing';
      });

    const loanItems: HoldListItem[] = (loans.data ?? [])
      .map((l) => ({
        kind: 'loan' as const,
        id: l.id,
        borrowerName: l.borrowerName,
        status: l.status,
        loanType: l.loanType,
        loanAmount: l.loanAmount,
        currentPhaseId: l.currentPhaseId,
        conversationId: l.conversationId,
        stpProcessingStatus: (l as any).stpProcessingStatus ?? null,
        documentChecklist: l.documentChecklist,
        updatedAt: l.updatedAt,
      }))
      .filter((l) => {
        if (loanFilter === 'all') return true;
        const missing = getLoanMissingCount(l.documentChecklist);
        const stp = (l.stpProcessingStatus || '').toLowerCase();
        return missing > 0 || stp === 'awaiting_documents';
      });

    return [...leadItems, ...loanItems].sort((a, b) => {
      const aTs = a.kind === 'lead' ? a.createdAt : a.updatedAt;
      const bTs = b.kind === 'lead' ? b.createdAt : b.updatedAt;
      const ad = aTs ? new Date(aTs).getTime() : 0;
      const bd = bTs ? new Date(bTs).getTime() : 0;
      return bd - ad;
    });
  }, [conversations.data, leadFilter, loanFilter, loans.data]);

  const [activeKind, setActiveKind] = React.useState<HoldKind>(defaultKind);
  const filtered = React.useMemo(() => holds.filter((h) => h.kind === activeKind), [holds, activeKind]);
  const [selectedId, setSelectedId] = React.useState<string>('');

  // Deep link support: /officer-hold?leadId=... or ?loanId=...
  React.useEffect(() => {
    if (routeLeadId) {
      setActiveKind('lead');
      setSelectedId(routeLeadId);
      return;
    }
    if (routeLoanId) {
      setActiveKind('loan');
      setSelectedId(routeLoanId);
    }
  }, [routeLeadId, routeLoanId]);

  React.useEffect(() => {
    if (!selectedId && filtered.length > 0) setSelectedId(filtered[0].id);
    if (selectedId && !filtered.some((x) => x.id === selectedId)) setSelectedId(filtered[0]?.id ?? '');
  }, [filtered, selectedId]);

  const selected = React.useMemo(() => filtered.find((x) => x.id === selectedId) ?? null, [filtered, selectedId]);

  const refreshAll = useMutation({
    mutationFn: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['officer-hold', 'conversations'] }),
        queryClient.invalidateQueries({ queryKey: ['officer-hold', 'loans'] }),
      ]);
    },
  });

  const headerError = (conversations.error as Error | null)?.message || (loans.error as Error | null)?.message || '';

  return (
    <div className="min-h-[calc(100vh-60px)] bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d] px-4 md:px-6 py-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">{title}</h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>
          </div>
          <button
            type="button"
            onClick={() => refreshAll.mutate()}
            className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm"
          >
            Refresh
          </button>
        </div>

        {headerError ? <div className="mt-3 text-sm font-semibold text-red-700 dark:text-red-300">{headerError}</div> : null}

        <div className="mt-5 grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6">
          <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 overflow-hidden">
            <div className="p-4 border-b border-slate-200/60 dark:border-white/[0.06]">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveKind('lead')}
                  className={`flex-1 rounded-2xl px-3 py-2 text-xs font-bold border transition-colors ${
                    activeKind === 'lead'
                      ? 'bg-blue-50 border-blue-200/70 text-blue-800 dark:bg-blue-500/10 dark:border-blue-500/20 dark:text-blue-200'
                      : 'bg-white/70 border-slate-200/60 text-slate-700 hover:bg-white dark:bg-white/[0.02] dark:border-white/[0.06] dark:text-slate-200 dark:hover:bg-white/[0.04]'
                  }`}
                >
                  Lead holds
                </button>
                <button
                  type="button"
                  onClick={() => setActiveKind('loan')}
                  className={`flex-1 rounded-2xl px-3 py-2 text-xs font-bold border transition-colors ${
                    activeKind === 'loan'
                      ? 'bg-blue-50 border-blue-200/70 text-blue-800 dark:bg-blue-500/10 dark:border-blue-500/20 dark:text-blue-200'
                      : 'bg-white/70 border-slate-200/60 text-slate-700 hover:bg-white dark:bg-white/[0.02] dark:border-white/[0.06] dark:text-slate-200 dark:hover:bg-white/[0.04]'
                  }`}
                >
                  Loan holds
                </button>
              </div>
              <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
                <span>{filtered.length} items</span>
                <span className="uppercase tracking-wider">
                  {activeKind === 'lead'
                    ? leadFilter === 'all'
                      ? 'All leads'
                      : 'Holds only'
                    : loanFilter === 'all'
                      ? 'All loans'
                      : 'Holds only'}
                </span>
              </div>
            </div>

            <div className="max-h-[70vh] overflow-y-auto">
              {(conversations.isLoading || loans.isLoading) && filtered.length === 0 ? (
                <div className="p-4 text-sm text-slate-500 dark:text-slate-400">Loading…</div>
              ) : filtered.length === 0 ? (
                <div className="p-4 text-sm text-slate-500 dark:text-slate-400">No holds found.</div>
              ) : (
                filtered.map((h) => {
                  const selectedRow = h.id === selectedId;
                  const title =
                    h.kind === 'lead'
                      ? h.borrowerName?.trim() || `Lead #${formatShortId(h.id)}`
                      : h.borrowerName?.trim() || `Loan #${formatShortId(h.id)}`;
                  const subtitle =
                    h.kind === 'lead'
                      ? `Status: ${h.status || '—'}`
                      : `${h.loanType || 'Loan'} · ${h.loanAmount || '—'} · ${h.status || '—'}`;

                  const badge =
                    h.kind === 'lead'
                      ? (() => {
                          const r = getLeadHoldReason(h.approvalProbability);
                          return r.blockers > 0 ? `${r.blockers} blockers` : 'Review';
                        })()
                      : (() => {
                          const missing = getLoanMissingCount(h.documentChecklist);
                          const stp = (h.stpProcessingStatus || '').toLowerCase();
                          if (stp === 'awaiting_documents') return 'Awaiting docs';
                          return missing > 0 ? `${missing} missing` : 'Hold';
                        })();

                  const badgeTone =
                    h.kind === 'lead'
                      ? getLeadHoldReason(h.approvalProbability).blockers > 0
                        ? 'danger'
                        : 'info'
                      : 'danger';

                  return (
                    <button
                      key={h.id}
                      type="button"
                      onClick={() => setSelectedId(h.id)}
                      className={`w-full text-left px-4 py-3 border-b border-slate-200/40 dark:border-white/[0.04] transition-colors ${
                        selectedRow ? 'bg-blue-50/70 dark:bg-blue-500/10' : 'bg-transparent hover:bg-white/60 dark:hover:bg-white/[0.03]'
                      }`}
                      data-testid={`officer-hold-row-${h.id}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white truncate">{title}</div>
                          <div className="mt-0.5 text-[12px] text-slate-600 dark:text-slate-300 truncate">{subtitle}</div>
                        </div>
                        <div className="shrink-0">
                          <Pill tone={badgeTone as any}>{badge}</Pill>
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className="min-h-[200px]">
            {!selected ? (
              <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-6 text-slate-600 dark:text-slate-300">
                Select a hold item to view details.
              </div>
            ) : selected.kind === 'lead' ? (
              <LeadHoldDetail
                lead={selected}
                relatedLoans={(loans.data ?? []).filter((l) => l.conversationId && l.conversationId === selected.id)}
                onSaved={(updated) => {
                  queryClient.setQueryData(['officer-hold', 'conversations'], (prev: V2Conversation[] | undefined) =>
                    (prev ?? []).map((c) => (c.id === updated.id ? updated : c)),
                  );
                }}
              />
            ) : (
              <LoanHoldDetail
                loan={selected}
                phases={(phases.data ?? []) as Array<{ id: string; name: string }>}
                onUpdated={(updated) => {
                  queryClient.setQueryData(['officer-hold', 'loans'], (prev: V2Loan[] | undefined) =>
                    (prev ?? []).map((l) => (l.id === updated.id ? updated : l)),
                  );
                }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
