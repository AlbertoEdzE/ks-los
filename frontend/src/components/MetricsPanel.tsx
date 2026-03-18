import React from 'react';

const ADMIN_HEADERS = { Authorization: 'Bearer admin-access' };

export const MetricsPanel: React.FC = () => {
  const openDriftReport = async () => {
    const res = await fetch("http://localhost:8000/training/drift/report", { headers: ADMIN_HEADERS })
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
        <a href="http://localhost:3000" target="_blank" rel="noreferrer">Open Grafana</a>
        <a href="http://localhost:8000/metrics" target="_blank" rel="noreferrer">Open Prometheus Metrics</a>
        <button onClick={openDriftReport} style={{ textAlign: 'left' }}>Open Drift Report</button>
      </div>
    </div>
  );
};
