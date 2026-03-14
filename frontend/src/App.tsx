import React, { useMemo, useState } from 'react';
import type { ApplicantCreditProfile } from './types';
import { CreditProfileView } from './components/CreditProfileView';
import { ChatInterface } from './components/ChatInterface';
import './App.css';
import { AdminPanel } from './components/AdminPanel';
import { GlobalProgressBar } from './components/GlobalProgressBar';
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [role, setRole] = useState<'user' | 'admin'>('user');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [profile, setProfile] = useState<ApplicantCreditProfile | null>(null);
  const [candidateName, setCandidateName] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const navigate = useNavigate();
  const location = useLocation();
  const fromPath = useMemo(() => {
    const state = location.state as { from?: { pathname?: string } } | null;
    return state?.from?.pathname || null;
  }, [location.state]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    const resolvePostLoginPath = (newRole: 'admin' | 'user') => {
      if (!fromPath || fromPath === '/login') {
        return newRole === 'admin' ? '/dashboard' : '/';
      }

      if (newRole === 'admin') {
        if (fromPath === '/' || fromPath === '/login') return '/dashboard';
        return fromPath;
      }

      if (fromPath === '/dashboard' || fromPath === '/pipeline' || fromPath === '/loan-products' || fromPath === '/officer-chat') {
        return '/';
      }
      return fromPath;
    };

    if (username === 'admin' && password === 'admin123') {
      setRole('admin');
      setIsLoggedIn(true);
      setLoginError('');
      navigate(resolvePostLoginPath('admin'), { replace: true });
    } else if (username === 'demo' && password === 'demo123') {
      setRole('user');
      setIsLoggedIn(true);
      setLoginError('');
      navigate(resolvePostLoginPath('user'), { replace: true });
    } else {
      setLoginError('Invalid credentials. Try demo/demo123 or admin/admin123');
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setRole('user');
    setUsername('');
    setPassword('');
    setLoginError('');
    navigate('/login', { replace: true });
  };

  const LoginPage = () => (
    <div
      className="app-container"
      style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f5f5f5',
      }}
    >
      <div
        style={{
          padding: '40px',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
          width: '100%',
          maxWidth: '400px',
        }}
      >
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

  const BorrowerHomePage = () => (
    <div className="app-container" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <h1 style={{ margin: 0 }}>Loan Navigator</h1>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {role === 'admin' ? <Link to="/dashboard">Officer</Link> : null}
          <button type="button" onClick={handleLogout} style={{ padding: '8px 10px' }}>
            Logout
          </button>
        </div>
      </div>
      <div style={{ maxWidth: '1400px', margin: '18px auto 20px auto' }}>
        <GlobalProgressBar fullName={profile?.identity.full_name || candidateName || 'Applicant'} isActive={isAnalyzing} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', maxWidth: '1400px', margin: '0 auto' }}>
        <div>
          <ChatInterface
            onProfileReceived={(p) => {
              setProfile(p);
              setIsAnalyzing(false);
            }}
            onNameDetected={setCandidateName}
            onAnalysisStart={() => setIsAnalyzing(true)}
          />
        </div>

        <div>
          {profile ? (
            <CreditProfileView profile={profile} />
          ) : (
            <div
              style={{
                padding: '40px',
                border: '1px dashed #ccc',
                borderRadius: '8px',
                textAlign: 'center',
                color: '#999',
                height: '500px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              No profile generated yet. Chat with the coach to begin.
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const OfficerChrome: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <div>
      <div
        style={{
          padding: '12px 16px',
          paddingLeft: '266px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ fontWeight: 900 }}>Officer</div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/pipeline">Pipeline</Link>
          <Link to="/loan-products">Loan Products</Link>
          <Link to="/officer-chat">Officer Chat</Link>
          <button type="button" onClick={handleLogout} style={{ padding: '6px 10px' }}>
            Logout
          </button>
        </div>
      </div>
      {children}
    </div>
  );

  const LoanProductsPage = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [items, setItems] = useState<Array<{ id: string; name: string; code: string; status?: string }>>([]);

    const refresh = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await fetch('http://localhost:8000/api/catalog-products', {
          headers: { 'x-officer-role': 'loan-officer-access' },
        });
        if (!res.ok) {
          setError(`Failed to load: ${res.status}`);
          return;
        }
        const data = (await res.json()) as Array<{ id: string; name: string; code: string; status?: string }>;
        setItems(data);
      } catch {
        setError('Failed to load');
      } finally {
        setLoading(false);
      }
    };

    React.useEffect(() => {
      void refresh();
    }, []);

    return (
      <OfficerChrome>
        <div style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
            <h1 style={{ margin: 0 }} data-testid="heading-loan-products">
              Loan Products
            </h1>
            <button type="button" onClick={() => void refresh()} disabled={loading} style={{ padding: '8px 10px' }}>
              Refresh
            </button>
          </div>
          {error ? (
            <div style={{ marginTop: '12px', color: '#b91c1c', fontWeight: 700 }} data-testid="text-loan-products-error">
              {error}
            </div>
          ) : null}
          {loading ? (
            <div style={{ marginTop: '12px', color: '#6b7280' }} data-testid="text-loan-products-loading">
              Loading…
            </div>
          ) : null}
          <div style={{ marginTop: '12px', display: 'grid', gap: '10px' }}>
            {items.map((p) => (
              <div key={p.id} style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px' }} data-testid={`loan-product-${p.code}`}>
                <div style={{ fontWeight: 900 }}>{p.name}</div>
                <div style={{ color: '#6b7280' }}>
                  {p.code}
                  {p.status ? ` · ${p.status}` : ''}
                </div>
              </div>
            ))}
            {!loading && !error && items.length === 0 ? <div style={{ color: '#6b7280' }}>No products.</div> : null}
          </div>
        </div>
      </OfficerChrome>
    );
  };

  const OfficerChatPage = () => (
    <OfficerChrome>
      <div style={{ padding: '16px' }}>
        <h1 style={{ marginTop: 0 }} data-testid="heading-officer-chat">
          Officer Chat
        </h1>
        <div style={{ color: '#6b7280' }}>Coming soon.</div>
      </div>
    </OfficerChrome>
  );

  const RequireAuth: React.FC<{ children: React.ReactElement }> = ({ children }) => {
    if (!isLoggedIn) {
      return <Navigate to="/login" replace state={{ from: location }} />;
    }
    return children;
  };

  const RequireRole: React.FC<{ allow: 'admin' | 'user'; children: React.ReactElement }> = ({ allow, children }) => {
    if (role !== allow) {
      return <Navigate to={role === 'admin' ? '/dashboard' : '/'} replace />;
    }
    return children;
  };

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <RequireRole allow="user">
              <BorrowerHomePage />
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <RequireRole allow="admin">
              <OfficerChrome>
                <AdminPanel initialTab="leads" />
              </OfficerChrome>
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/pipeline"
        element={
          <RequireAuth>
            <RequireRole allow="admin">
              <OfficerChrome>
                <AdminPanel initialTab="loans" />
              </OfficerChrome>
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/loan-products"
        element={
          <RequireAuth>
            <RequireRole allow="admin">
              <LoanProductsPage />
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/officer-chat"
        element={
          <RequireAuth>
            <RequireRole allow="admin">
              <OfficerChatPage />
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to={isLoggedIn ? (role === 'admin' ? '/dashboard' : '/') : '/login'} replace />} />
    </Routes>
  );
}

export default App;
