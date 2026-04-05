import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useLocation } from 'react-router-dom';
import MetricsDashboard from '../components/MetricsDashboard';

const API_BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');
const OFFICER_HEADERS: Record<string, string> = { Authorization: 'Bearer loan-officer-access' };

type SessionSummary = {
  sessionId: string;
  applicationId: string | null;
  mode: string;
  stage: string;
  borrowerName: string | null;
  requiresManualReview: boolean;
  escalationNeeded: boolean;
  stpStatus: string | null;
  updatedAt: string | null;
  createdAt: string | null;
};

type SessionDetail = SessionSummary & {
  capturedContext?: unknown;
  intentAnalysis?: unknown;
  confidenceScores?: unknown;
  loanSnapshot?: unknown;
  recommendations?: unknown;
  selectedRecommendation?: unknown;
  documentsChecklist?: unknown;
  uploadedDocuments?: unknown;
  stpCheckpoints?: unknown;
  bureauScore?: number | null;
  stpApproved?: boolean;
  awaitingAcceptance?: boolean;
  termsAccepted?: boolean;
  currentPhaseId?: string | null;
  phaseHistory?: unknown;
  discrepancyFlags?: unknown;
};

type AgenticMessage = { role?: string; content?: string; [k: string]: unknown };

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

function toPrettyJson(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function DataValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <span className="text-slate-400">—</span>;
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return <span className="break-words text-slate-800 dark:text-slate-200">{String(value)}</span>;
  }
  const label = Array.isArray(value) ? `Array(${value.length})` : `Object(${Object.keys(value as any).length})`;
  return (
    <details className="group">
      <summary className="cursor-pointer list-none inline-flex items-center gap-2 rounded-xl px-2 py-1 text-xs font-semibold border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] text-slate-700 dark:text-slate-200">
        <span className="group-open:hidden">View {label}</span>
        <span className="hidden group-open:inline">Hide {label}</span>
      </summary>
      <pre className="mt-3 whitespace-pre-wrap text-[12px] leading-relaxed text-slate-700 dark:text-slate-200 bg-white/60 dark:bg-black/20 border border-slate-200/60 dark:border-white/[0.06] rounded-2xl p-4 max-h-[360px] overflow-auto">
        {toPrettyJson(value)}
      </pre>
    </details>
  );
}

function StructuredPanel({ title, value }: { title: string; value: unknown }) {
  const isObj = value && typeof value === 'object' && !Array.isArray(value);
  const entries = React.useMemo(() => {
    if (!isObj) return [];
    return Object.entries(value as Record<string, unknown>).slice(0, 18);
  }, [isObj, value]);

  return (
    <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">{title}</h3>
        <Pill>
          {value === undefined || value === null
            ? '—'
            : Array.isArray(value)
              ? `${value.length} items`
              : typeof value === 'object'
                ? `${Object.keys(value as any).length} fields`
                : 'value'}
        </Pill>
      </div>
      {isObj && entries.length ? (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          {entries.map(([k, v]) => (
            <div
              key={k}
              className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3"
            >
              <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider break-all">{k}</div>
              <div className="mt-1 text-sm">
                <DataValue value={v} />
              </div>
            </div>
          ))}
        </div>
      ) : value === undefined || value === null ? (
        <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No data.</div>
      ) : (
        <div className="mt-4">
          <DataValue value={value} />
        </div>
      )}
    </div>
  );
}

function formatTs(ts: string | null) {
  if (!ts) return '—';
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString();
}

export default function OfficerAgenticConsolePage() {
  const routeLocation = useLocation();
  const routeSessionId = React.useMemo(() => (new URLSearchParams(routeLocation.search).get('sessionId') || '').trim(), [routeLocation.search]);
  const sessions = useQuery({
    queryKey: ['officer-agentic', 'sessions'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/officer/agentic/sessions`, { headers: OFFICER_HEADERS });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to load sessions (${res.status})`);
      }
      return (await res.json()) as SessionSummary[];
    },
    staleTime: 5_000,
  });

  const [selectedId, setSelectedId] = React.useState<string>('');

  React.useEffect(() => {
    if (routeSessionId) {
      setSelectedId(routeSessionId);
      return;
    }
    if (!selectedId && (sessions.data?.length ?? 0) > 0) setSelectedId(sessions.data![0].sessionId);
  }, [routeSessionId, selectedId, sessions.data]);

  const detail = useQuery({
    queryKey: ['officer-agentic', 'session', selectedId],
    enabled: Boolean(selectedId),
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/officer/agentic/sessions/${encodeURIComponent(selectedId)}`, { headers: OFFICER_HEADERS });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to load session (${res.status})`);
      }
      return (await res.json()) as SessionDetail;
    },
    staleTime: 5_000,
  });

  const messages = useQuery({
    queryKey: ['officer-agentic', 'messages', selectedId],
    enabled: Boolean(selectedId),
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/officer/agentic/sessions/${encodeURIComponent(selectedId)}/messages`, { headers: OFFICER_HEADERS });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to load messages (${res.status})`);
      }
      return (await res.json()) as AgenticMessage[];
    },
    staleTime: 5_000,
  });

  const error = (sessions.error as Error | null)?.message || (detail.error as Error | null)?.message || (messages.error as Error | null)?.message || '';

  return (
    <div className="min-h-[calc(100vh-60px)] bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d] px-4 md:px-6 py-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">Agentic Console</h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Officer visibility into v3 agentic state (intent, confidence, flags, STP checkpoints) and AI quality metrics (RAGAS).
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Pill tone="info">{sessions.data?.length ?? 0} sessions</Pill>
          </div>
        </div>

        {error ? <div className="mt-3 text-sm font-semibold text-red-700 dark:text-red-300">{error}</div> : null}

        <div className="mt-5 grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
          <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 overflow-hidden">
            <div className="p-4 border-b border-slate-200/60 dark:border-white/[0.06]">
              <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Sessions</div>
              <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Most recently updated first</div>
            </div>
            <div className="max-h-[72vh] overflow-y-auto">
              {sessions.isLoading ? (
                <div className="p-4 text-sm text-slate-500 dark:text-slate-400">Loading…</div>
              ) : (sessions.data?.length ?? 0) === 0 ? (
                <div className="p-4 text-sm text-slate-500 dark:text-slate-400">No agentic sessions found yet.</div>
              ) : (
                (sessions.data ?? []).map((s) => {
                  const isSelected = s.sessionId === selectedId;
                  const title = s.borrowerName?.trim() ? s.borrowerName : `Session #${s.sessionId.slice(0, 8)}`;
                  const flags = [
                    s.escalationNeeded ? <Pill key="esc" tone="danger">Escalation</Pill> : null,
                    s.requiresManualReview ? <Pill key="mr" tone="danger">Manual review</Pill> : null,
                    s.stpStatus ? <Pill key="stp" tone={String(s.stpStatus).toLowerCase().includes('await') ? 'danger' : 'info'}>{s.stpStatus}</Pill> : null,
                  ].filter(Boolean);
                  return (
                    <button
                      key={s.sessionId}
                      type="button"
                      onClick={() => setSelectedId(s.sessionId)}
                      className={`w-full text-left px-4 py-3 border-b border-slate-200/40 dark:border-white/[0.04] transition-colors ${
                        isSelected ? 'bg-blue-50/70 dark:bg-blue-500/10' : 'bg-transparent hover:bg-white/60 dark:hover:bg-white/[0.03]'
                      }`}
                      data-testid={`agentic-session-${s.sessionId}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white truncate">{title}</div>
                          <div className="mt-0.5 text-[12px] text-slate-600 dark:text-slate-300 truncate">
                            Mode: {s.mode} · Stage: {s.stage}
                          </div>
                          <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400 truncate">Updated: {formatTs(s.updatedAt)}</div>
                          {s.applicationId ? <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400 truncate">App: {s.applicationId}</div> : null}
                        </div>
                      </div>
                      {flags.length ? <div className="mt-2 flex flex-wrap gap-1.5">{flags}</div> : null}
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className="space-y-6">
            {!selectedId ? (
              <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-6 text-slate-600 dark:text-slate-300">
                Select a session to view details.
              </div>
            ) : detail.isLoading ? (
              <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-6 text-slate-600 dark:text-slate-300">
                Loading session…
              </div>
            ) : detail.data ? (
              <>
                <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="text-lg font-black tracking-tight text-slate-900 dark:text-white">
                        {detail.data.borrowerName?.trim() ? detail.data.borrowerName : `Session #${detail.data.sessionId.slice(0, 8)}`}
                      </h2>
                      <div className="mt-1 flex flex-wrap gap-2">
                        <Pill tone="info">{detail.data.mode}</Pill>
                        <Pill>{detail.data.stage}</Pill>
                        {detail.data.escalationNeeded ? <Pill tone="danger">Escalation needed</Pill> : <Pill tone="success">No escalation</Pill>}
                        {detail.data.requiresManualReview ? <Pill tone="danger">Manual review</Pill> : <Pill tone="success">Auto</Pill>}
                        {detail.data.stpStatus ? <Pill tone={String(detail.data.stpStatus).toLowerCase().includes('await') ? 'danger' : 'info'}>{detail.data.stpStatus}</Pill> : null}
                      </div>
                      <div className="mt-2 text-[12px] text-slate-600 dark:text-slate-300">
                        Session ID: <span className="font-mono">{detail.data.sessionId}</span>
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="text-[11px] text-slate-500 dark:text-slate-400">Updated</div>
                      <div className="text-xs font-semibold text-slate-700 dark:text-slate-200">{formatTs(detail.data.updatedAt)}</div>
                      <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">Created</div>
                      <div className="text-xs font-semibold text-slate-700 dark:text-slate-200">{formatTs(detail.data.createdAt)}</div>
                    </div>
                  </div>
                </div>

                <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Conversation transcript</h3>
                    <Pill>{messages.data?.length ?? 0} msgs</Pill>
                  </div>
                  {messages.isLoading ? (
                    <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">Loading messages…</div>
                  ) : (messages.data?.length ?? 0) === 0 ? (
                    <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No messages recorded.</div>
                  ) : (
                    <div className="mt-4 grid gap-2">
                      {(messages.data ?? []).slice(-30).map((m, idx) => {
                        const role = String(m.role || 'unknown');
                        const content = String(m.content || '');
                        const isUser = role === 'user';
                        return (
                          <div
                            key={idx}
                            className={`rounded-2xl border px-4 py-3 ${
                              isUser
                                ? 'border-blue-200/70 dark:border-blue-500/20 bg-blue-50/60 dark:bg-blue-500/10'
                                : 'border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03]'
                            }`}
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{role}</div>
                            </div>
                            <div className="mt-1 text-[13px] leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-wrap">{content}</div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">AI quality (RAGAS, hallucinations)</h3>
                    <Pill tone="info">Admin 🔒</Pill>
                  </div>
                  <div className="mt-4">
                    <MetricsDashboard isAdmin conversationId={detail.data.sessionId} autoRefresh />
                  </div>
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                  <StructuredPanel title="Captured context" value={detail.data.capturedContext} />
                  <StructuredPanel title="Intent analysis" value={detail.data.intentAnalysis} />
                  <StructuredPanel title="Confidence scores" value={detail.data.confidenceScores} />
                  <StructuredPanel title="Flags / discrepancy" value={detail.data.discrepancyFlags} />
                  <StructuredPanel title="Loan snapshot" value={detail.data.loanSnapshot} />
                  <StructuredPanel title="Documents checklist" value={detail.data.documentsChecklist} />
                  <StructuredPanel title="STP checkpoints" value={detail.data.stpCheckpoints} />
                  <StructuredPanel title="Selected recommendation" value={detail.data.selectedRecommendation} />
                </div>
              </>
            ) : (
              <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-6 text-slate-600 dark:text-slate-300">
                Could not load session.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
