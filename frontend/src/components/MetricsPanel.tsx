import React from 'react';

export const MetricsPanel: React.FC = () => {
  return (
    <div style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '16px' }}>
      <h2>Metrics</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <a href="http://localhost:3000" target="_blank" rel="noreferrer">Open Grafana</a>
        <a href="http://localhost:8000/metrics" target="_blank" rel="noreferrer">Open Prometheus Metrics</a>
        <a href="http://localhost:8000/training/drift/report" target="_blank" rel="noreferrer">Open Drift Report</a>
      </div>
    </div>
  );
};
