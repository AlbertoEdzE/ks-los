import React, { useState } from 'react';
export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'configuration' | 'synthetic' | 'model' | 'metrics'>('synthetic');
  const [count, setCount] = useState(100);
  const [territory, setTerritory] = useState('ECCU');
  const [archetype, setArchetype] = useState('standard');
  const [seed, setSeed] = useState('');
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
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
              <label>Count</label>
              <input type="number" value={count} onChange={(e) => setCount(parseInt(e.target.value || '0', 10))} style={{ width: '100%', padding: '8px' }} />
            </div>
            <div>
              <label>Territory</label>
              <input type="text" value={territory} onChange={(e) => setTerritory(e.target.value)} style={{ width: '100%', padding: '8px' }} />
            </div>
            <div>
              <label>Archetype</label>
              <input type="text" value={archetype} onChange={(e) => setArchetype(e.target.value)} style={{ width: '100%', padding: '8px' }} />
            </div>
            <div>
              <label>Seed</label>
              <input type="text" value={seed} onChange={(e) => setSeed(e.target.value)} style={{ width: '100%', padding: '8px' }} />
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
        <div style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '16px' }}>
          <h2>Model</h2>
          <div>Metrics, drift, fairness and sandbox will be added here.</div>
        </div>
      )}
      {activeTab === 'metrics' && (
        <div style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '16px' }}>
          <h2>Metrics</h2>
          <div>Links to Grafana dashboards will be added here.</div>
        </div>
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
