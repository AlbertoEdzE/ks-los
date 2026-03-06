import React, { useState } from 'react';

const ProgressBar: React.FC<{ progress: number; status: string }> = ({ progress, status }) => (
  <div style={{ width: '100%', marginTop: '24px' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
      <span style={{ fontWeight: '500', color: '#4a5568', fontSize: '0.875rem' }}>{status}</span>
      <span style={{ fontWeight: '600', color: '#3182ce', fontSize: '0.875rem' }}>{progress}%</span>
    </div>
    <div style={{ width: '100%', height: '10px', backgroundColor: '#edf2f7', borderRadius: '5px', overflow: 'hidden' }}>
      <div style={{ 
        width: `${progress}%`, 
        height: '100%', 
        backgroundColor: '#3182ce', 
        transition: 'width 0.3s ease' 
      }} />
    </div>
  </div>
);

const InputGroup: React.FC<{ label: string; children: React.ReactNode; info?: string }> = ({ label, children, info }) => (
  <div style={{ marginBottom: '16px' }}>
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '6px' }}>
      <label style={{ fontSize: '0.875rem', fontWeight: '500', color: '#4a5568' }}>{label}</label>
      {info && (
        <span title={info} style={{ marginLeft: '6px', cursor: 'help', fontSize: '0.8rem', color: '#a0aec0' }}>ℹ️</span>
      )}
    </div>
    {children}
  </div>
);

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

  const inputStyle = {
    width: '100%',
    padding: '10px 12px',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
    fontSize: '0.95rem',
    color: '#2d3748',
    outline: 'none',
    transition: 'border-color 0.2s',
    backgroundColor: '#fff'
  };

  return (
    <div style={{ padding: '24px', backgroundColor: 'white', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
      <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#1a202c', marginBottom: '24px' }}>Synthetic Data Generator</h2>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
        <InputGroup label="Count">
          <input 
            type="number" 
            value={count} 
            onChange={(e) => setCount(parseInt(e.target.value || '0', 10))} 
            style={inputStyle} 
          />
        </InputGroup>
        
        <InputGroup label="Territory">
          <select 
            value={territory} 
            onChange={(e) => setTerritory(e.target.value)} 
            style={inputStyle}
          >
            {TERRITORIES.map((t) => (
              <option key={t.code} value={t.code}>
                {t.name}
              </option>
            ))}
          </select>
        </InputGroup>
        
        <InputGroup label="Archetype">
          <select 
            value={archetype} 
            onChange={(e) => setArchetype(e.target.value)} 
            style={inputStyle}
          >
            {ARCHETYPES.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </InputGroup>
        
        <InputGroup label="Seed (Optional)" info="Use a numeric seed for reproducible data generation">
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
            placeholder="0"
            style={inputStyle}
          />
        </InputGroup>
      </div>

      <div style={{ display: 'flex', gap: '16px', marginTop: '24px' }}>
        <button 
          onClick={startGeneration} 
          style={{ 
            padding: '10px 24px', 
            backgroundColor: '#3182ce', 
            color: '#fff', 
            border: 'none', 
            borderRadius: '6px', 
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'background-color 0.2s',
            boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
          }}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#2b6cb0'}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#3182ce'}
        >
          Start Generation
        </button>
        
        <button 
          onClick={validateOutput} 
          style={{ 
            padding: '10px 24px', 
            backgroundColor: '#edf2f7', 
            color: '#4a5568', 
            border: '1px solid #e2e8f0', 
            borderRadius: '6px', 
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#e2e8f0'}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#edf2f7'}
        >
          Validate Output
        </button>
      </div>

      {(status !== 'idle' || progress > 0) && (
        <ProgressBar progress={progress} status={`${status === 'running' ? 'Generating...' : status} ${message ? `— ${message}` : ''}`} />
      )}
    </div>
  );
};
