import React from 'react';

export type AdminTabId = 'leads' | 'loans' | 'configuration' | 'synthetic' | 'simulator' | 'metrics' | 'training';

interface SidebarProps {
  activeTab: AdminTabId;
  onTabChange: (tab: AdminTabId) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const tabs: Array<{ id: AdminTabId; label: string }> = [
    { id: 'leads', label: 'Leads' },
    { id: 'loans', label: 'Loans' },
    { id: 'synthetic', label: 'Synthetic Data' },
    { id: 'configuration', label: 'Configuration' },
    { id: 'simulator', label: 'Simulator' },
    { id: 'metrics', label: 'Metrics' },
    { id: 'training', label: 'ML Training' },
  ];

  return (
    <div style={{ width: '250px', borderRight: '1px solid #e5e7eb', height: '100vh', backgroundColor: '#f8f9fa', padding: '20px', display: 'flex', flexDirection: 'column', position: 'fixed', left: 0, top: 0, overflowY: 'auto' }}>
      <h2 style={{ marginBottom: '24px', fontSize: '1.25rem', fontWeight: '600', color: '#1a202c' }}>Admin Panel</h2>
      <nav>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {tabs.map((tab) => (
            <li key={tab.id} style={{ marginBottom: '8px' }}>
              <button
                onClick={() => onTabChange(tab.id)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: '12px 16px',
                  backgroundColor: activeTab === tab.id ? '#3b82f6' : 'transparent',
                  color: activeTab === tab.id ? '#ffffff' : '#4a5568',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: activeTab === tab.id ? '600' : '500',
                  transition: 'all 0.2s',
                  fontSize: '0.95rem'
                }}
                onMouseEnter={(e) => {
                  if (activeTab !== tab.id) {
                    e.currentTarget.style.backgroundColor = '#e2e8f0';
                  }
                }}
                onMouseLeave={(e) => {
                  if (activeTab !== tab.id) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }
                }}
              >
                {tab.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <div style={{ marginTop: 'auto', padding: '12px', fontSize: '0.8rem', color: '#718096', borderTop: '1px solid #e2e8f0' }}>
        v1.0.0
      </div>
    </div>
  );
};
