import React, { useState } from 'react';

export const SyntheticDataControl: React.FC = () => {
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
  );
};
