import React, { useState } from 'react';
export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'configuration' | 'synthetic' | 'model' | 'metrics'>('synthetic');
  const [count, setCount] = useState(100);
  const [territory, setTerritory] = useState('ECCU');
  const [archetype, setArchetype] = useState('standard');
  const [seed, setSeed] = useState('0');
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');

  const TERRITORIES = [
    { code: 'AG', name: 'Antigua and Barbuda' },
    { code: 'GD', name: 'Grenada' },
    { code: 'LC', name: 'Saint Lucia' },
    { code: 'VC', name: 'Saint Vincent and the Grenadines' },
    { code: 'DM', name: 'Dominica' },
    { code: 'KN', name: 'Saint Kitts and Nevis' },
    { code: 'MS', name: 'Montserrat' },
    { code: 'AI', name: 'Anguilla' },
    { code: 'ECCU', name: 'ECCU (Generic)' },
    { code: 'US', name: 'United States' },
    { code: 'EU', name: 'European Union' },
    { code: 'APAC', name: 'Asia Pacific' },
  ];

  const ARCHETYPES = [
    'standard',
    'THIN_FILE_YOUNG',
    'THIN_FILE_IMMIGRANT',
    'PRIME_ESTABLISHED',
    'NEAR_PRIME',
    'RECOVERING',
    'STRESSED',
    'HIGH_UTILIZATION',
    'DEFAULTED'
  ];

  const startGeneration = async () => {
    setStatus('running');
    setProgress(0);
    setMessage('');
    try {
      const res = await fetch('http://localhost:8000/admin/synthetic/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ count, territory, archetype, seed })
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || 'Failed to start generation');
      }
      setMessage('Generation started');
    } catch (e: unknown) {
      setStatus('idle');
      const msg = e instanceof Error ? e.message : 'Error';
      setMessage(msg);
      return;
    }
    const es = new EventSource('http://localhost:8000/admin/synthetic/stream');
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data.replace(/'/g, '"'));
        setProgress(payload.progress || 0);
        setStatus(payload.status || 'running');
        setMessage(payload.message || '');
        if (payload.status === 'completed' || payload.status === 'error' || payload.status === 'idle') {
          es.close();
        }
      } catch {
        // ignore parse errors
      }
    };
    es.onerror = () => {
      es.close();
    };
  };
  const validateOutput = async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/synthetic/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      const data = await res.json();
      setMessage(typeof data === 'string' ? data : JSON.stringify(data));
    } catch {
      setMessage('Validation failed');
    }
  };
  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <button onClick={() => setActiveTab('synthetic')} style={{ padding: '8px 12px' }}>Synthetic Data</button>
        <button onClick={() => setActiveTab('configuration')} style={{ padding: '8px 12px' }}>Configuration</button>
        <button onClick={() => setActiveTab('model')} style={{ padding: '8px 12px' }}>Model</button>
        <button onClick={() => setActiveTab('metrics')} style={{ padding: '8px 12px' }}>Metrics</button>
      </div>
      {activeTab === 'synthetic' && (
        <div style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '16px' }}>
          <h2 style={{ marginBottom: '12px' }}>Synthetic Data Control</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label htmlFor="count-input">Count</label>
              <input id="count-input" type="number" value={count} onChange={(e) => setCount(parseInt(e.target.value || '0', 10))} style={{ width: '100%', padding: '8px' }} />
            </div>
            <div>
              <label htmlFor="territory-select">Territory</label>
              <select id="territory-select" value={territory} onChange={(e) => setTerritory(e.target.value)} style={{ width: '100%', padding: '8px' }}>
                {TERRITORIES.map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="archetype-select">Archetype</label>
              <select id="archetype-select" value={archetype} onChange={(e) => setArchetype(e.target.value)} style={{ width: '100%', padding: '8px' }}>
                {ARCHETYPES.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="seed-input" title="Use a seed for reproducible data generation (optional)">Seed (optional) ℹ️</label>
              <input
                id="seed-input"
                type="number"
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                placeholder="0"
                title="Enter a numeric seed for reproducibility"
                style={{ width: '100%', padding: '8px' }}
              />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
            <button onClick={startGeneration} style={{ padding: '10px 14px', backgroundColor: '#0056b3', color: '#fff', border: 'none', borderRadius: '4px' }}>
              Start Generation
            </button>
            <button onClick={validateOutput} style={{ padding: '10px 14px', backgroundColor: '#444', color: '#fff', border: 'none', borderRadius: '4px' }}>
              Validate Output
            </button>
          </div>
          <div style={{ marginTop: '16px' }}>
            <div style={{ height: '18px', backgroundColor: '#eee', borderRadius: '9px', overflow: 'hidden' }}>
              <div style={{ width: `${progress}%`, backgroundColor: '#28a745', height: '100%' }} />
            </div>
            <div style={{ marginTop: '8px', color: '#666' }}>
              Status: {status} {message && `– ${message}`}
            </div>
          </div>
        </div>
      )}
      {activeTab === 'configuration' && (
        <div style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '16px' }}>
          <h2>Configuration</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label>Suggestions Enabled</label>
            <SuggestionsToggle />
          </div>
        </div>
      )}
      {activeTab === 'model' && (
        <ModelPanel />
      )}
      {activeTab === 'metrics' && (
        <MetricsPanel />
      )}
    </div>
  );
}

const SuggestionsToggle: React.FC = () => {
  const [enabled, setEnabled] = React.useState(true);
  React.useEffect(() => {
    (async () => {
      try {
        const r = await fetch('http://localhost:8000/admin/config/suggestions_enabled');
        if (r.ok) {
          const data = await r.json();
          setEnabled(!!data.value);
        }
      } catch {}
    })();
  }, []);
  const toggle = async () => {
    try {
      const r = await fetch(`http://localhost:8000/admin/config/suggestions_enabled?value=${(!enabled).toString()}`, { method: 'POST' });
      if (r.ok) {
        const data = await r.json();
        setEnabled(!!data.value);
      }
    } catch {}
  };
  return (
    <button onClick={toggle} style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #ccc' }}>
      {enabled ? 'Disable' : 'Enable'}
    </button>
  );
};

const ModelPanel: React.FC = () => {
  const [summary, setSummary] = React.useState<any>(null);
  const [score, setScore] = React.useState<number | null>(null);
  const [featureValues, setFeatureValues] = React.useState<Record<string, number>>({});
  const [importances, setImportances] = React.useState<Record<string, number>>({});
  const [age, setAge] = React.useState(30);
  const [territory, setTerritory] = React.useState('ECCU');
  const [scenario, setScenario] = React.useState<string>('PRIME_ESTABLISHED');
  const [loading, setLoading] = React.useState(false);
  React.useEffect(() => {
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

const MetricsPanel: React.FC = () => {
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
