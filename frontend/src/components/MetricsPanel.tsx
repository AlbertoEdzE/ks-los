import React from 'react';

const ADMIN_HEADERS = { Authorization: 'Bearer admin-access' };

export const MetricsPanel: React.FC = () => {
  const API_BASE_URL =
    (import.meta.env.VITE_API_URL as string | undefined) ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');

  const openDriftReport = async () => {
    const res = await fetch(`${API_BASE_URL}/training/drift/report`, { headers: ADMIN_HEADERS })
    if (!res.ok) return
    const html = await res.text()
    const blob = new Blob([html], { type: "text/html" })
    const url = URL.createObjectURL(blob)
    window.open(url, "_blank", "noopener,noreferrer")
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }

  return (
    <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5">
      <h2 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Observability & Metrics</h2>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Open your local observability stack and diagnostics.</p>
      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <a className="inline-flex items-center justify-between rounded-2xl px-4 py-3 bg-white/70 dark:bg-white/[0.03] border border-slate-200/60 dark:border-white/[0.06] text-sm font-semibold text-slate-700 dark:text-slate-200 no-underline hover:bg-white/90 dark:hover:bg-white/[0.05]" href="http://localhost:3000" target="_blank" rel="noreferrer">
          Open LangFuse <span className="text-xs text-slate-400">↗</span>
        </a>
        <a className="inline-flex items-center justify-between rounded-2xl px-4 py-3 bg-white/70 dark:bg-white/[0.03] border border-slate-200/60 dark:border-white/[0.06] text-sm font-semibold text-slate-700 dark:text-slate-200 no-underline hover:bg-white/90 dark:hover:bg-white/[0.05]" href="http://localhost:3001" target="_blank" rel="noreferrer">
          Open Grafana <span className="text-xs text-slate-400">↗</span>
        </a>
        <a className="inline-flex items-center justify-between rounded-2xl px-4 py-3 bg-white/70 dark:bg-white/[0.03] border border-slate-200/60 dark:border-white/[0.06] text-sm font-semibold text-slate-700 dark:text-slate-200 no-underline hover:bg-white/90 dark:hover:bg-white/[0.05]" href="http://localhost:9090" target="_blank" rel="noreferrer">
          Open Prometheus <span className="text-xs text-slate-400">↗</span>
        </a>
        <a className="inline-flex items-center justify-between rounded-2xl px-4 py-3 bg-white/70 dark:bg-white/[0.03] border border-slate-200/60 dark:border-white/[0.06] text-sm font-semibold text-slate-700 dark:text-slate-200 no-underline hover:bg-white/90 dark:hover:bg-white/[0.05]" href={`${API_BASE_URL}/metrics`} target="_blank" rel="noreferrer">
          Open API /metrics <span className="text-xs text-slate-400">↗</span>
        </a>
        <button
          onClick={openDriftReport}
          className="sm:col-span-2 inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-[#0078D4] to-[#005EA6] px-4 py-3 text-sm font-extrabold text-white shadow-lg shadow-[#0078D4]/20"
        >
          Open Drift Report
        </button>
      </div>
    </div>
  );
};
