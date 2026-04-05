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
  const adminAuthHeader = { Authorization: 'Bearer admin-access' };

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
          ...adminAuthHeader,
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
    try {
      const streamRes = await fetch('http://localhost:8000/admin/synthetic/stream', { headers: adminAuthHeader });
      if (!streamRes.ok || !streamRes.body) {
        setMessage('Failed to stream progress');
        return;
      }

      const reader = streamRes.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        while (true) {
          const boundaryIndex = buffer.indexOf('\n\n');
          if (boundaryIndex === -1) break;

          const eventBlock = buffer.slice(0, boundaryIndex);
          buffer = buffer.slice(boundaryIndex + 2);

          const lines = eventBlock.split('\n');
          for (const line of lines) {
            if (!line.startsWith('data:')) continue;
            const dataStr = line.slice('data:'.length).trim();
            try {
              const payload = JSON.parse(dataStr.replace(/'/g, '"'));
              setProgress(payload.progress || 0);
              setStatus(payload.status || 'running');
              setMessage(payload.message || '');
              if (payload.status === 'completed' || payload.status === 'error' || payload.status === 'idle') {
                await reader.cancel();
                return;
              }
            } catch {
              continue;
            }
          }
        }
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Stream failed';
      setMessage(msg);
    }
  };

  const validateOutput = async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/synthetic/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...adminAuthHeader,
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
    <div className="max-w-6xl mx-auto px-4 md:px-6 py-6">
      <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-6">
        <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">Synthetic Data Generator</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Generate reproducible credit profiles and stream progress.</p>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginTop: '20px' }}>
        <InputGroup label="Count">
          <input 
            type="number" 
            aria-label="Count"
            value={count} 
            onChange={(e) => setCount(parseInt(e.target.value || '0', 10))} 
            style={inputStyle} 
          />
        </InputGroup>
        
        <InputGroup label="Territory">
          <select 
            aria-label="Territory"
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
            aria-label="Archetype"
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
            aria-label="Seed (Optional)"
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
          className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-[#0078D4] to-[#005EA6] px-4 py-2.5 text-sm font-extrabold text-white shadow-lg shadow-[#0078D4]/20"
        >
          Start Generation
        </button>
        
        <button 
          onClick={validateOutput} 
          className="inline-flex items-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-700 dark:text-slate-200 shadow-sm hover:bg-white/90 dark:hover:bg-white/[0.08]"
        >
          Validate Output
        </button>
      </div>

      {(status !== 'idle' || progress > 0) && (
        <ProgressBar progress={progress} status={`${status === 'running' ? 'Generating...' : status} ${message ? `— ${message}` : ''}`} />
      )}
      </div>
    </div>
  );
};
