import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { SyntheticDataControl } from './SyntheticDataControl';
import { ConfigurationPanel } from './ConfigurationPanel';
import { ModelPanel } from './ModelPanel';
import { MetricsPanel } from './MetricsPanel';
import { TrainingPanel } from './TrainingPanel';

export const AdminPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'configuration' | 'synthetic' | 'model' | 'metrics' | 'training'>('synthetic');

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#ffffff' }}>
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <div style={{ marginLeft: '250px', padding: '32px', width: 'calc(100% - 250px)' }}>
        <div style={{ display: activeTab === 'synthetic' ? 'block' : 'none' }}>
          <SyntheticDataControl />
        </div>
        <div style={{ display: activeTab === 'configuration' ? 'block' : 'none' }}>
          <ConfigurationPanel />
        </div>
        <div style={{ display: activeTab === 'model' ? 'block' : 'none' }}>
          <ModelPanel />
        </div>
        <div style={{ display: activeTab === 'metrics' ? 'block' : 'none' }}>
          <MetricsPanel />
        </div>
        <div style={{ display: activeTab === 'training' ? 'block' : 'none' }}>
          <TrainingPanel />
        </div>
      </div>
    </div>
  );
};
