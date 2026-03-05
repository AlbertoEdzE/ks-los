import React, { useState } from 'react';
import type { ApplicantCreditProfile } from './types';
import { CreditProfileView } from './components/CreditProfileView';
import { ChatInterface } from './components/ChatInterface';
import './App.css';
import { MonitoringPanel } from './components/MonitoringPanel';
import { AdminPanel } from './components/AdminPanel';
import { GlobalProgressBar } from './components/GlobalProgressBar';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [role, setRole] = useState<'user' | 'admin'>('user');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [profile, setProfile] = useState<ApplicantCreditProfile | null>(null);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (username === 'admin' && password === 'admin123') {
      setRole('admin');
      setIsLoggedIn(true);
      setLoginError('');
    } else if (username === 'demo' && password === 'demo123') {
      setRole('user');
      setIsLoggedIn(true);
      setLoginError('');
    } else {
      setLoginError('Invalid credentials. Try demo/demo123 or admin/admin123');
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="app-container" style={{ 
        height: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        backgroundColor: '#f5f5f5'
      }}>
        <div style={{
          padding: '40px',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
          width: '100%',
          maxWidth: '400px'
        }}>
          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
             <div>
               <label htmlFor="login-username" style={{ display: 'block', marginBottom: '8px', color: '#666' }}>Username</label>
               <input
                 id="login-username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
                placeholder="Enter username"
              />
            </div>
            <div>
               <label htmlFor="login-password" style={{ display: 'block', marginBottom: '8px', color: '#666' }}>Password</label>
               <input
                 id="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
                placeholder="Enter password"
              />
            </div>
            
            {loginError && <div style={{ color: 'red', fontSize: '14px' }}>{loginError}</div>}
            <button 
              type="submit"
              style={{
                padding: '12px',
                backgroundColor: '#0056b3',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: 'bold'
              }}
            >
              Login
            </button>
            <div style={{ textAlign: 'center', fontSize: '12px', color: '#999', marginTop: '10px' }}>
              User: demo / demo123. Admin: admin / admin123.
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container" style={{ padding: '20px' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '30px' }}>KS LOS - Agentic Journey Coach</h1>
      
      {role === 'admin' ? (
        <AdminPanel />
      ) : (
        <>
          <div style={{ maxWidth: '1400px', margin: '0 auto 20px auto' }}>
             {profile && <GlobalProgressBar fullName={profile.identity.full_name} />}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', maxWidth: '1400px', margin: '0 auto' }}>
            <div>
              <ChatInterface onProfileReceived={setProfile} />
            </div>
            
            <div>
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
          <div style={{ maxWidth: '1400px', margin: '20px auto' }}>
            <MonitoringPanel />
          </div>
        </>
      )}
    </div>
  );
}

export default App;
