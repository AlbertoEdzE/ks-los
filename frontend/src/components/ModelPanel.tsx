import React, { useState, useEffect } from 'react';

export const ModelPanel: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [score, setScore] = useState<number | null>(null);
  const [featureValues, setFeatureValues] = useState<Record<string, number>>({});
  const [importances, setImportances] = useState<Record<string, number>>({});
  const [age, setAge] = useState(30);
  const [territory, setTerritory] = useState('ECCU');
  const [scenario, setScenario] = useState<string>('PRIME_ESTABLISHED');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('http://localhost:8000/observability/summary');
        if (r.ok) {
          const data = await r.json();
          setSummary(data);
        }
      } catch {}
    })();
  }, []);

  const runSandbox = async () => {
    setLoading(true);
    try {
      const gen = await fetch('http://localhost:8000/scdg/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ age, territory, scenario_type: scenario })
      });
      const profile = await gen.json();
      const exp = await fetch('http://localhost:8000/explain/inference', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile })
      });
      if (exp.ok) {
        const data = await exp.json();
        setScore(typeof data.score === 'number' ? data.score : null);
        setFeatureValues(data.feature_values || {});
        setImportances(data.feature_importances || {});
      }
    } catch {} finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '16px' }}>
      <h2>Model</h2>
      <div style={{ marginBottom: '12px', color: '#666' }}>Observability Summary</div>
      <pre style={{ backgroundColor: '#f8f8f8', padding: '10px', borderRadius: '6px', overflowX: 'auto' }}>
        {summary ? JSON.stringify(summary, null, 2) : 'Loading...'}
      </pre>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginTop: '12px' }}>
        <div>
          <label>Age</label>
          <input type="number" value={age} onChange={(e) => setAge(parseInt(e.target.value || '0', 10))} style={{ width: '100%', padding: '8px' }} />
        </div>
        <div>
          <label>Territory</label>
          <input value={territory} onChange={(e) => setTerritory(e.target.value)} style={{ width: '100%', padding: '8px' }} />
        </div>
        <div>
          <label>Scenario</label>
          <input value={scenario} onChange={(e) => setScenario(e.target.value)} style={{ width: '100%', padding: '8px' }} />
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end' }}>
          <button onClick={runSandbox} style={{ padding: '10px 14px', backgroundColor: '#0056b3', color: '#fff', border: 'none', borderRadius: '4px' }}>
            {loading ? 'Running...' : 'Run Sandbox'}
          </button>
        </div>
      </div>
      <div style={{ marginTop: '16px' }}>
        <div style={{ marginBottom: '8px', color: '#666' }}>Score</div>
        <div style={{ fontSize: '18px', fontWeight: 'bold' }}>{score !== null ? score.toFixed(3) : '-'}</div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '16px' }}>
        <div>
          <div style={{ marginBottom: '8px', color: '#666' }}>Feature Values</div>
          <pre style={{ backgroundColor: '#f8f8f8', padding: '10px', borderRadius: '6px', overflowX: 'auto' }}>
            {Object.keys(featureValues).length ? JSON.stringify(featureValues, null, 2) : '-'}
          </pre>
        </div>
        <div>
          <div style={{ marginBottom: '8px', color: '#666' }}>Feature Importances</div>
          <pre style={{ backgroundColor: '#f8f8f8', padding: '10px', borderRadius: '6px', overflowX: 'auto' }}>
            {Object.keys(importances).length ? JSON.stringify(importances, null, 2) : '-'}
          </pre>
        </div>
      </div>
    </div>
  );
};
