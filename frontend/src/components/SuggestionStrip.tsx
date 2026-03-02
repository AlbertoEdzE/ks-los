import React from 'react';

export interface Suggestion {
  label: string;
  text: string;
}

interface Props {
  suggestions: Suggestion[];
  onSelect: (text: string) => void;
  label?: string;
}

export const SuggestionStrip: React.FC<Props> = ({ suggestions, onSelect, label = "Suggested inputs:" }) => {
  if (suggestions.length === 0) return null;

  return (
    <div style={{ marginBottom: '16px', animation: 'fadeInUp 0.3s ease-out' }}>
      <div style={{
        fontSize: '11px',
        fontWeight: '600',
        color: '#6b7280',
        marginBottom: '8px',
        textTransform: 'uppercase',
        letterSpacing: '0.05em'
      }}>{label}</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {suggestions.map((s, idx) => (
          <button
            key={idx}
            onClick={() => onSelect(s.text)}
            style={{
              padding: '6px 12px',
              backgroundColor: 'white',
              color: '#4f46e5',
              fontSize: '13px',
              fontWeight: '500',
              borderRadius: '16px',
              border: '1px solid #e0e7ff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              transition: 'all 0.2s',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#eef2ff';
              e.currentTarget.style.boxShadow = '0 2px 4px rgba(79, 70, 229, 0.1)';
              e.currentTarget.querySelector('svg')!.style.opacity = '1';
              e.currentTarget.querySelector('svg')!.style.transform = 'translateX(2px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'white';
              e.currentTarget.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.05)';
              e.currentTarget.querySelector('svg')!.style.opacity = '0';
              e.currentTarget.querySelector('svg')!.style.transform = 'translateX(0)';
            }}
          >
            <span>{s.label}</span>
            <svg 
              width="12" 
              height="12" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2" 
              strokeLinecap="round" 
              strokeLinejoin="round"
              style={{
                marginLeft: '6px',
                opacity: 0,
                transition: 'all 0.2s',
                transform: 'translateX(0)'
              }}
            >
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
          </button>
        ))}
      </div>
      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};
