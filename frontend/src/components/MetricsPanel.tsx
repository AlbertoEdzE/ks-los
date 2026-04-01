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
    <div style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '16px' }}>
      <h2>Metrics</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <a href="http://localhost:3000" target="_blank" rel="noreferrer">Open LangFuse</a>
        <a href="http://localhost:3001" target="_blank" rel="noreferrer">Open Grafana</a>
        <a href="http://localhost:9090" target="_blank" rel="noreferrer">Open Prometheus</a>
        <a href={`${API_BASE_URL}/metrics`} target="_blank" rel="noreferrer">Open API /metrics</a>
        <button onClick={openDriftReport} style={{ textAlign: 'left' }}>Open Drift Report</button>
      </div>
    </div>
  );
};
