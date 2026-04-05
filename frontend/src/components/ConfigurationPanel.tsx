import React, { useState, useEffect } from 'react';

const ADMIN_HEADERS = { Authorization: 'Bearer admin-access' };
const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

const SuggestionsToggle: React.FC = () => {
  const [enabled, setEnabled] = useState(true);
  
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API_URL}/admin/config/suggestions_enabled`, { headers: ADMIN_HEADERS });
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
      const r = await fetch(`${API_URL}/admin/config/suggestions_enabled?value=${(!enabled).toString()}`, { method: 'POST', headers: ADMIN_HEADERS });
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
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-6">
          <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-6">
          <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">System Configuration</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Feature flags and governance controls for the assistant.</p>
          
          <div className="mt-6 rounded-3xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] p-6">
            <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white mb-4">AI Assistant</h3>
            
            <div className="flex items-center justify-between gap-6">
               <div className="min-w-0 max-w-2xl">
                  <div className="font-extrabold text-slate-900 dark:text-white mb-1">Smart Suggestions</div>
                  <div className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                    When enabled, the system will provide contextual hints, next-step recommendations, and automated insights throughout the application workflow.
                  </div>
               </div>
               <div className="shrink-0">
                 <SuggestionsToggle />
               </div>
            </div>
          </div>
          </div>
        </div>
    );
};
