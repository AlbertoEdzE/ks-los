import React, { useState, useEffect } from 'react';

const SuggestionsToggle: React.FC = () => {
  const [enabled, setEnabled] = useState(true);
  useEffect(() => {
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

export const ConfigurationPanel: React.FC = () => {
    return (
        <div style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '16px' }}>
          <h2>Configuration</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label>Suggestions Enabled</label>
            <SuggestionsToggle />
          </div>
        </div>
    );
};
