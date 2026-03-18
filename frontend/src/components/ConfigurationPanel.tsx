import React, { useState, useEffect } from 'react';

const ADMIN_HEADERS = { Authorization: 'Bearer admin-access' };

const SuggestionsToggle: React.FC = () => {
  const [enabled, setEnabled] = useState(true);
  
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('http://localhost:8000/admin/config/suggestions_enabled', { headers: ADMIN_HEADERS });
        if (r.ok) {
          const data = await r.json();
          setEnabled(!!data.value);
        }
      } catch (err) {
        console.error('Failed to load suggestions configuration', err);
      }
    })();
  }, []);

  const toggle = async () => {
    try {
      const r = await fetch(`http://localhost:8000/admin/config/suggestions_enabled?value=${(!enabled).toString()}`, { method: 'POST', headers: ADMIN_HEADERS });
      if (r.ok) {
        const data = await r.json();
        setEnabled(!!data.value);
      }
    } catch (err) {
      console.error('Failed to update suggestions configuration', err);
    }
  };

  return (
    <button 
      onClick={toggle} 
      role="switch"
      aria-checked={enabled}
      style={{ 
        position: 'relative',
        width: '52px',
        height: '28px',
        borderRadius: '14px',
        backgroundColor: enabled ? '#3182ce' : '#cbd5e0',
        border: 'none',
        cursor: 'pointer',
        padding: '2px',
        transition: 'background-color 0.2s ease-in-out',
        outline: 'none'
      }}
    >
      <div style={{
        width: '24px',
        height: '24px',
        borderRadius: '50%',
        backgroundColor: 'white',
        transform: enabled ? 'translateX(24px)' : 'translateX(0)',
        transition: 'transform 0.2s cubic-bezier(0.4, 0.0, 0.2, 1)',
        boxShadow: '0 1px 3px rgba(0,0,0,0.2)'
      }} />
    </button>
  );
};

export const ConfigurationPanel: React.FC = () => {
    return (
        <div style={{ padding: '24px', backgroundColor: 'white', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: '#1a202c', marginBottom: '24px' }}>System Configuration</h2>
          
          <div style={{ padding: '24px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '600', color: '#2d3748', marginBottom: '20px' }}>AI Assistant</h3>
            
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
               <div style={{ maxWidth: '600px' }}>
                  <div style={{ fontWeight: '600', color: '#2d3748', marginBottom: '4px' }}>Smart Suggestions</div>
                  <div style={{ fontSize: '0.9rem', color: '#718096', lineHeight: '1.5' }}>
                    When enabled, the system will provide contextual hints, next-step recommendations, and automated insights throughout the application workflow.
                  </div>
               </div>
               <div style={{ marginLeft: '24px' }}>
                 <SuggestionsToggle />
               </div>
            </div>
          </div>
        </div>
    );
};
