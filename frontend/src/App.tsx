import { useState } from 'react';
import type { ApplicantCreditProfile } from './types';
import { CreditProfileView } from './components/CreditProfileView';
import { ChatInterface } from './components/ChatInterface';
import './App.css';

function App() {
  const [profile, setProfile] = useState<ApplicantCreditProfile | null>(null);

  return (
    <div className="app-container" style={{ padding: '20px' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '30px' }}>KS LOS - Agentic Journey Coach</h1>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', maxWidth: '1400px', margin: '0 auto' }}>
        <div>
          <h2>Chat with Journey Coach</h2>
          <ChatInterface onProfileReceived={setProfile} />
        </div>
        
        <div>
          <h2>Credit Profile</h2>
          {profile ? (
            <CreditProfileView profile={profile} />
          ) : (
            <div style={{ 
              padding: '40px', 
              border: '1px dashed #ccc', 
              borderRadius: '8px', 
              textAlign: 'center', 
              color: '#999',
              height: '500px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              No profile generated yet. Chat with the coach to begin.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
