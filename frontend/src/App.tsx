import React, { useMemo, useState } from 'react';
import { ChatInterface, type V2Conversation, type V2Phase } from './components/ChatInterface';
import './App.css';
import { ConfigurationPanel } from './components/ConfigurationPanel';
import { MetricsPanel } from './components/MetricsPanel';
import { SimulatorPanel } from './components/SimulatorPanel';
import { SyntheticDataControl } from './components/SyntheticDataControl';
import { TrainingPanel } from './components/TrainingPanel';
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type LoginPageProps = {
  username: string;
  password: string;
  loginError: string;
  onSubmit: (e: React.FormEvent) => void;
  onUsernameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
};

function LoginPage({ username, password, loginError, onSubmit, onUsernameChange, onPasswordChange }: LoginPageProps) {
  return (
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
        <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label htmlFor="login-username" style={{ display: 'block', marginBottom: '8px', color: '#666' }}>
              Username
            </label>
            <input
              id="login-username"
              type="text"
              value={username}
              onChange={(e) => onUsernameChange(e.target.value)}
              style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
              placeholder="Enter username"
              autoComplete="username"
            />
          </div>
          <div>
            <label htmlFor="login-password" style={{ display: 'block', marginBottom: '8px', color: '#666' }}>
              Password
            </label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => onPasswordChange(e.target.value)}
              style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
              placeholder="Enter password"
              autoComplete="current-password"
            />
          </div>

          {loginError ? <div style={{ color: 'red', fontSize: '14px' }}>{loginError}</div> : null}
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
              fontWeight: 'bold',
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

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [role, setRole] = useState<'user' | 'admin'>('user');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');

  type Theme = 'light' | 'dark' | 'glass';
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      const stored = window.localStorage.getItem('loanassist-theme');
      if (stored === 'light' || stored === 'dark' || stored === 'glass') return stored;
    } catch {
      return 'glass';
    }
    return 'glass';
  });

  React.useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark', 'glass');

    if (theme === 'dark') {
      root.classList.add('dark');
    } else if (theme === 'glass') {
      root.classList.add('dark', 'glass');
    } else {
      root.classList.add('light');
    }

    try {
      window.localStorage.setItem('loanassist-theme', theme);
    } catch {
      return;
    }
  }, [theme]);

  const ThemeToggle = () => {
    const modes: Array<{ value: Theme; label: string }> = [
      { value: 'light', label: 'Light' },
      { value: 'dark', label: 'Dark' },
      { value: 'glass', label: 'Glass' },
    ];

    return (
      <div data-testid="theme-toggle" className="flex items-center gap-0.5 p-1 rounded-2xl bg-slate-100 dark:bg-white/10 border border-slate-200/60 dark:border-white/10 shadow-sm">
        {modes.map((m) => (
          <button
            key={m.value}
            type="button"
            data-testid={`theme-${m.value}`}
            onClick={() => setTheme(m.value)}
            className={`px-3 py-1.5 rounded-xl text-[11px] font-medium transition-all duration-300 ${
              theme === m.value
                ? 'bg-white dark:bg-white/20 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>
    );
  };

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

      if (
        fromPath === '/dashboard' ||
        fromPath === '/pipeline' ||
        fromPath === '/loan-products' ||
        fromPath === '/officer-chat' ||
        fromPath === '/synthetic-data' ||
        fromPath === '/training' ||
        fromPath === '/metrics' ||
        fromPath === '/simulator' ||
        fromPath === '/configuration'
      ) {
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

  const BorrowerHomePage = () => {
    const [phases, setPhases] = useState<V2Phase[]>([]);
    const [conversation, setConversation] = useState<V2Conversation | null>(null);
    const [resetSignal, setResetSignal] = useState(0);
    const routeLocation = useLocation();
    const [designOverlayOpacity, setDesignOverlayOpacity] = useState(0.5);
    const [designOverlayName, setDesignOverlayName] = useState('');

    React.useEffect(() => {
      const params = new URLSearchParams(routeLocation.search);
      const raw = (params.get('design') || '').trim();
      if (raw) setDesignOverlayName(raw);
      const opacityRaw = (params.get('opacity') || '').trim();
      const parsed = Number(opacityRaw);
      if (!Number.isNaN(parsed) && parsed >= 0 && parsed <= 1) setDesignOverlayOpacity(parsed);
    }, [routeLocation.search]);

    const designOverlaySrc = React.useMemo(() => {
      if (!import.meta.env.DEV) return null;
      const name = designOverlayName.trim();
      if (!name) return null;
      const p = `/Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/attached_assets/${name}`;
      return `/@fs${p}`;
    }, [designOverlayName]);

    const activePhases = React.useMemo(() => {
      return phases
        .filter((p) => p.isActive)
        .slice()
        .sort((a, b) => a.sortOrder - b.sortOrder);
    }, [phases]);

    const currentIndex = React.useMemo(() => {
      if (!activePhases.length) return 0;
      const phaseId = conversation?.currentPhaseId || null;
      const idx = phaseId ? activePhases.findIndex((p) => p.id === phaseId) : 0;
      return idx >= 0 ? idx : 0;
    }, [activePhases, conversation?.currentPhaseId]);

    const approvalProbability = React.useMemo(() => {
      const raw = conversation?.approvalProbability as unknown;
      if (typeof raw === 'number') return raw;
      if (raw && typeof raw === 'object' && typeof (raw as { probability?: unknown }).probability === 'number') {
        return (raw as { probability: number }).probability;
      }
      return null;
    }, [conversation?.approvalProbability]);

    const recommendedProducts = React.useMemo(() => {
      const raw = conversation?.recommendedProducts as unknown;
      return Array.isArray(raw) ? (raw as Array<Record<string, unknown>>) : [];
    }, [conversation?.recommendedProducts]);

    const handleNewChat = () => {
      setConversation(null);
      setPhases([]);
      setResetSignal((v) => v + 1);
    };

    return (
      <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d] relative overflow-hidden">
        {designOverlaySrc ? (
          <div className="absolute inset-0 z-20 pointer-events-none">
            <img src={designOverlaySrc} alt="" className="w-full h-full object-cover" style={{ opacity: designOverlayOpacity }} />
          </div>
        ) : null}

        <div className="absolute top-[-200px] left-1/4 w-[600px] h-[600px] bg-blue-200/15 dark:bg-blue-500/[0.03] rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-[-150px] right-1/4 w-[500px] h-[500px] bg-blue-200/15 dark:bg-blue-500/5 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-indigo-200/10 dark:bg-indigo-500/3 rounded-full blur-[150px] pointer-events-none" />

        <header className="glass-header relative z-10 border-b border-slate-200/40 dark:border-white/[0.04] px-6 py-4 flex items-center justify-between bg-white/70 dark:bg-[#141414]/80 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-white dark:bg-white/10 flex items-center justify-center shadow-sm">
              <span className="text-sm font-black tracking-tight text-slate-900 dark:text-white">KS</span>
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-tight text-slate-900 dark:text-white" data-testid="text-app-title">
                LoanAssist AI
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">Smart loan guidance, personalized for you</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            {import.meta.env.DEV ? (
              <div className="flex items-center gap-2 rounded-2xl px-3 py-2 bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] shadow-sm">
                <input
                  value={designOverlayName}
                  onChange={(e) => setDesignOverlayName(e.target.value)}
                  placeholder="design overlay png"
                  className="w-44 bg-transparent text-xs text-slate-600 dark:text-slate-300 placeholder:text-slate-400 dark:placeholder:text-slate-500 outline-none"
                />
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={designOverlayOpacity}
                  onChange={(e) => setDesignOverlayOpacity(Number(e.target.value))}
                  className="w-20"
                />
              </div>
            ) : null}
            {role === 'admin' ? (
              <Link to="/dashboard" className="no-underline">
                <span className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm">
                  Officer Dashboard
                </span>
              </Link>
            ) : null}
            <button
              data-testid="button-new-chat"
              type="button"
              onClick={handleNewChat}
              className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm"
            >
              New Chat
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm"
            >
              Logout
            </button>
          </div>
        </header>

        {activePhases.length > 0 && conversation?.currentPhaseId ? (
          <div data-testid="phase-progress-tracker" className="glass-header relative z-10 border-b border-slate-200/40 dark:border-white/[0.04] bg-white/50 dark:bg-white/[0.02] backdrop-blur-sm">
            <div className="max-w-3xl mx-auto px-4 py-3">
              <div className="flex items-center gap-1.5 mb-2.5">
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Your Loan Journey</span>
                <span className="text-[10px] text-slate-400 dark:text-slate-500 ml-auto">
                  Step {Math.max(currentIndex + 1, 1)} of {activePhases.length}
                </span>
              </div>

              <div className="overflow-x-auto scrollbar-hide -mx-1 px-1">
                <div className="flex items-start min-w-max gap-0">
                  {activePhases.map((p, i) => {
                    const isCompleted = i < currentIndex;
                    const isCurrent = i === currentIndex;
                    return (
                      <div key={p.id} className="flex items-start">
                        <button
                          type="button"
                          onClick={() => navigate(`/phases/${p.id}`)}
                          className="flex flex-col items-center"
                          style={{ minWidth: '72px' }}
                          data-testid={`phase-step-${i}`}
                        >
                          <div className="relative">
                            {isCurrent ? (
                              <div className="absolute inset-0 w-8 h-8 -m-1 rounded-full bg-blue-400/15 animate-ping" style={{ animationDuration: '2s' }} />
                            ) : null}
                            <div
                              className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-500 ${
                                isCompleted
                                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-200/50 dark:shadow-blue-900/30'
                                  : isCurrent
                                    ? 'bg-blue-600 text-white shadow-md shadow-blue-200/50 dark:shadow-blue-900/30 ring-2 ring-blue-100 dark:ring-blue-500/15'
                                    : 'bg-slate-100 dark:bg-white/[0.06] text-slate-400 dark:text-slate-500'
                              }`}
                            >
                              {isCompleted ? (
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                  <polyline points="20 6 9 17 4 12" />
                                </svg>
                              ) : (
                                <span>{i + 1}</span>
                              )}
                            </div>
                          </div>
                          <p
                            className={`text-[9px] mt-1.5 text-center leading-tight max-w-[68px] transition-colors duration-300 ${
                              isCurrent
                                ? 'font-semibold text-blue-700 dark:text-blue-400'
                                : isCompleted
                                  ? 'font-medium text-blue-600 dark:text-blue-500'
                                  : 'text-slate-400 dark:text-slate-500'
                            }`}
                          >
                            {p.name}
                          </p>
                        </button>
                        {i < activePhases.length - 1 ? (
                          <div className="flex items-center pt-3 -mx-0.5">
                            <div className={`h-[2px] w-6 transition-colors duration-500 ${i < currentIndex ? 'bg-blue-500' : 'bg-slate-200 dark:bg-white/[0.06]'}`} />
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        ) : null}

        <div className="flex-1 min-h-0 relative z-10">
          <div className="h-full max-w-6xl mx-auto px-4 md:px-6 py-6">
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 h-full min-h-0">
              <div className="min-h-0 rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-xl shadow-black/[0.04] dark:shadow-black/40 overflow-hidden flex">
                <ChatInterface onConversationUpdated={setConversation} onPhasesUpdated={setPhases} resetSignal={resetSignal} />
              </div>

              <div className="hidden lg:flex flex-col gap-4 min-h-0">
                <div
                  data-testid="card-insights"
                  className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Insights</h3>
                    <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Live</span>
                  </div>

                  <div className="mt-4 grid gap-3">
                    <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                      <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Approval Probability</div>
                      <div className="mt-1 text-2xl font-black tracking-tight text-slate-900 dark:text-white" data-testid="approval-probability">
                        {approvalProbability === null ? '—' : `${Math.round(approvalProbability * 100)}%`}
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                      <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Next Conversation Angle</div>
                      <div className="mt-1 text-sm font-semibold text-slate-800 dark:text-slate-200" data-testid="next-conversation-angle">
                        {conversation?.nextConversationAngle || '—'}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Seriousness Score</div>
                        <div className="mt-1 text-xl font-black tracking-tight text-slate-900 dark:text-white" data-testid="seriousness-score">
                          {typeof conversation?.seriousnessScore === 'number' ? conversation.seriousnessScore : '—'}
                        </div>
                      </div>

                      <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Fit Score</div>
                        <div className="mt-1 text-xl font-black tracking-tight text-slate-900 dark:text-white" data-testid="fit-score">
                          {typeof conversation?.fitScore === 'number' ? conversation.fitScore : '—'}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div
                  data-testid="card-recommendations"
                  className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-lg shadow-black/[0.04] dark:shadow-black/40 p-5 min-h-0 flex flex-col"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Recommended Products</h3>
                    <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                      {recommendedProducts.length === 0 ? '—' : `${recommendedProducts.length}`}
                    </span>
                  </div>

                  <div data-testid="recommended-products" className="mt-4 grid gap-3 overflow-y-auto min-h-0">
                    {recommendedProducts.length === 0 ? (
                      <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
                        No recommendations yet. Send a message to get started.
                      </div>
                    ) : (
                      recommendedProducts.map((p, idx) => {
                        const name = typeof p.name === 'string' ? p.name : `Recommendation ${idx + 1}`;
                        const recommendation = typeof p.recommendation === 'string' ? p.recommendation : '';
                        const estimatedRate = typeof p.estimatedRate === 'string' ? p.estimatedRate : '';
                        const tenure = typeof p.tenure === 'string' ? p.tenure : '';
                        const estimatedEmi = typeof p.estimatedEmi === 'string' ? p.estimatedEmi : '';

                        return (
                          <div
                            key={`${name}-${idx}`}
                            data-testid={`recommended-product-${idx}`}
                            className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3"
                          >
                            <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">{name}</div>
                            <div className="mt-1 text-[12px] text-slate-500 dark:text-slate-400">
                              {estimatedRate ? `Rate: ${estimatedRate}` : 'Rate: —'}
                              {tenure ? ` · Tenure: ${tenure}` : ''}
                              {estimatedEmi ? ` · EMI: ${estimatedEmi}` : ''}
                            </div>
                            {recommendation ? (
                              <div className="mt-2 text-[13px] leading-relaxed text-slate-700 dark:text-slate-300">{recommendation}</div>
                            ) : null}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const OfficerChrome: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <div>
      <div
        style={{
          padding: '12px 16px',
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
          <Link to="/synthetic-data">Synthetic Data</Link>
          <Link to="/training">ML Training</Link>
          <Link to="/metrics">Metrics</Link>
          <Link to="/simulator">Simulator</Link>
          <Link to="/configuration">Configuration</Link>
          <button type="button" onClick={handleLogout} style={{ padding: '6px 10px' }}>
            Logout
          </button>
        </div>
      </div>
      {children}
    </div>
  );

  type LeadStatus = 'active' | 'reviewing' | 'qualified' | 'closed';
  type DocumentStatus = 'missing' | 'submitted' | 'verified' | 'rejected';

  const DashboardPage = () => {
    const officerHeaders = React.useMemo<Record<string, string>>(() => ({ 'x-officer-role': 'loan-officer-access' }), []);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [leads, setLeads] = useState<V2Conversation[]>([]);
    const [selectedId, setSelectedId] = useState<string>('');
    const selected = React.useMemo(() => leads.find((l) => l.id === selectedId) || null, [leads, selectedId]);

    const [draftBorrowerName, setDraftBorrowerName] = useState('');
    const [draftAssignedOfficer, setDraftAssignedOfficer] = useState('');
    const [draftStatus, setDraftStatus] = useState<LeadStatus>('active');
    const [saving, setSaving] = useState(false);
    const [saveOk, setSaveOk] = useState(false);
    const [saveError, setSaveError] = useState('');

    const refresh = React.useCallback(async () => {
      setLoading(true);
      setError('');
      try {
        const res = await fetch('http://localhost:8000/api/conversations', { headers: officerHeaders });
        if (!res.ok) {
          const t = await res.text();
          setError(t || `Failed to load leads (${res.status})`);
          return;
        }
        const data = (await res.json()) as V2Conversation[];
        setLeads(data);
        if (!selectedId && data.length > 0) setSelectedId(data[0].id);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load leads');
      } finally {
        setLoading(false);
      }
    }, [officerHeaders, selectedId]);

    React.useEffect(() => {
      void refresh();
    }, [refresh]);

    React.useEffect(() => {
      if (!selected) return;
      setDraftBorrowerName(selected.borrowerName || '');
      setDraftAssignedOfficer(selected.assignedOfficer || '');
      setDraftStatus(((selected.status || 'active') as LeadStatus) || 'active');
      setSaveOk(false);
      setSaveError('');
    }, [selected]);

    const saveLead = async () => {
      if (!selected) return;
      setSaving(true);
      setSaveOk(false);
      setSaveError('');
      try {
        const res = await fetch(`http://localhost:8000/api/conversations/${selected.id}`, {
          method: 'PATCH',
          headers: { ...officerHeaders, 'content-type': 'application/json' },
          body: JSON.stringify({
            borrowerName: draftBorrowerName.trim() || null,
            assignedOfficer: draftAssignedOfficer.trim() || null,
            status: draftStatus,
          }),
        });
        if (!res.ok) {
          const t = await res.text();
          setSaveError(t || `Failed to save (${res.status})`);
          return;
        }
        const updated = (await res.json()) as V2Conversation;
        setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
        setSaveOk(true);
      } catch (e: unknown) {
        setSaveError(e instanceof Error ? e.message : 'Failed to save');
      } finally {
        setSaving(false);
      }
    };

    const probability = React.useMemo(() => {
      const raw = selected?.approvalProbability as unknown;
      if (typeof raw === 'number') return raw;
      if (raw && typeof raw === 'object' && typeof (raw as { probability?: unknown }).probability === 'number') {
        return (raw as { probability: number }).probability;
      }
      return null;
    }, [selected?.approvalProbability]);

    const recommendedProducts = React.useMemo(() => {
      const raw = selected?.recommendedProducts as unknown;
      return Array.isArray(raw) ? raw : [];
    }, [selected?.recommendedProducts]);

    return (
      <OfficerChrome>
        <div style={{ padding: '16px' }}>
          <h1 style={{ marginTop: 0 }}>Leads</h1>
          <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '16px', alignItems: 'start' }}>
            <div style={{ border: '1px solid #e5e7eb', borderRadius: '12px', background: '#fff' }}>
              <div style={{ padding: '12px 14px', borderBottom: '1px solid #e5e7eb', fontWeight: 900 }} data-testid="text-leads-title">
                Leads
              </div>
              {loading ? <div style={{ padding: '12px 14px', color: '#6b7280' }}>Loading…</div> : null}
              {error ? <div style={{ padding: '12px 14px', color: '#b91c1c' }}>{error}</div> : null}
              <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                {leads.map((l) => (
                  <button
                    key={l.id}
                    type="button"
                    onClick={() => setSelectedId(l.id)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      border: 'none',
                      borderBottom: '1px solid #f3f4f6',
                      backgroundColor: selectedId === l.id ? '#eff6ff' : '#ffffff',
                      padding: '12px 14px',
                      cursor: 'pointer',
                    }}
                    data-testid={`lead-row-${l.id}`}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                      <div style={{ fontWeight: 700, color: '#111827' }}>{l.borrowerName || `Lead #${l.id.slice(0, 8)}`}</div>
                      <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{l.status}</div>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '4px' }}>Officer: {l.assignedOfficer || 'Unassigned'}</div>
                  </button>
                ))}
                {!loading && leads.length === 0 ? <div style={{ padding: '12px 14px', color: '#6b7280' }}>No leads yet.</div> : null}
              </div>
            </div>

            <div style={{ border: '1px solid #e5e7eb', borderRadius: '12px', background: '#fff', padding: '18px' }}>
              <h2 style={{ marginTop: 0, marginBottom: '12px' }}>Lead Detail</h2>
              {!selected ? (
                <div style={{ color: '#6b7280' }}>Select a lead to edit.</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div style={{ gridColumn: '1 / -1', fontSize: '0.9rem', color: '#6b7280' }}>
                    ID: <span style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>{selected.id}</span>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>
                      Borrower Name
                    </label>
                    <input
                      value={draftBorrowerName}
                      onChange={(e) => setDraftBorrowerName(e.target.value)}
                      placeholder="e.g. Jane Doe"
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #e5e7eb' }}
                      data-testid="input-borrower-name"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>
                      Assigned Officer
                    </label>
                    <input
                      value={draftAssignedOfficer}
                      onChange={(e) => setDraftAssignedOfficer(e.target.value)}
                      placeholder="e.g. officer-1"
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #e5e7eb' }}
                      data-testid="input-assigned-officer"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>Status</label>
                    <select
                      value={draftStatus}
                      onChange={(e) => setDraftStatus(e.target.value as LeadStatus)}
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #e5e7eb', backgroundColor: '#ffffff' }}
                      data-testid="select-lead-status"
                    >
                      <option value="active">active</option>
                      <option value="reviewing">reviewing</option>
                      <option value="qualified">qualified</option>
                      <option value="closed">closed</option>
                    </select>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'end', gap: '10px' }}>
                    <button
                      type="button"
                      onClick={saveLead}
                      disabled={saving}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '8px',
                        border: '1px solid #e5e7eb',
                        background: saving ? '#f3f4f6' : '#111827',
                        color: saving ? '#6b7280' : '#ffffff',
                        cursor: saving ? 'not-allowed' : 'pointer',
                        fontWeight: 800,
                      }}
                      data-testid="button-save-lead"
                    >
                      {saving ? 'Saving…' : 'Save'}
                    </button>
                    {saveOk ? (
                      <div style={{ color: '#047857', fontWeight: 700 }} data-testid="text-save-ok">
                        Saved
                      </div>
                    ) : null}
                    {saveError ? <div style={{ color: '#b91c1c', fontWeight: 700 }}>{saveError}</div> : null}
                  </div>

                  <div style={{ gridColumn: '1 / -1', marginTop: '12px', display: 'grid', gap: '12px' }}>
                    <div style={{ border: '1px solid #f3f4f6', borderRadius: '10px', padding: '12px', backgroundColor: '#fafafa' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 900, color: '#111827', marginBottom: '8px' }} data-testid="text-approval-probability-title">
                        Approval Probability
                      </div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 900 }} data-testid="text-approval-probability-score">
                        {probability === null ? '—' : `${Math.round(probability * 100)}%`}
                      </div>
                    </div>

                    <div style={{ border: '1px solid #f3f4f6', borderRadius: '10px', padding: '12px', backgroundColor: '#fafafa' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 900, color: '#111827', marginBottom: '8px' }}>Recommended Products</div>
                      <div style={{ display: 'grid', gap: '8px' }}>
                        {recommendedProducts.length === 0 ? (
                          <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>No recommendations yet.</div>
                        ) : (
                          recommendedProducts.map((p, idx) => {
                            const item = p as Record<string, unknown>;
                            const name = typeof item.name === 'string' ? item.name : `Recommendation ${idx + 1}`;
                            const recommendation = typeof item.recommendation === 'string' ? item.recommendation : '';
                            return (
                              <div key={`${name}-${idx}`} style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px' }}>
                                <div style={{ fontWeight: 900, color: '#111827' }}>{name}</div>
                                {recommendation ? <div style={{ color: '#6b7280', marginTop: '4px', fontSize: '13px' }}>{recommendation}</div> : null}
                              </div>
                            );
                          })
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </OfficerChrome>
    );
  };

  const PipelinePage = () => {
    const officerHeaders = React.useMemo<Record<string, string>>(() => ({ 'x-officer-role': 'loan-officer-access' }), []);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [phases, setPhases] = useState<
      Array<{
        id: string;
        name: string;
        sortOrder?: number | null;
        isActive?: boolean | null;
      }>
    >([]);
    const [loans, setLoans] = useState<
      Array<{
        id: string;
        borrowerName?: string | null;
        loanType?: string | null;
        loanAmount?: string | null;
        catalogProductCode?: string | null;
        currentPhaseId?: string | null;
        status?: string | null;
        documentChecklist?: unknown;
      }>
    >([]);
    const [selectedId, setSelectedId] = useState<string>('');
    const selected = React.useMemo(() => loans.find((l) => l.id === selectedId) || null, [loans, selectedId]);

    const refreshPhases = React.useCallback(async () => {
      try {
        const res = await fetch('http://localhost:8000/api/phases');
        if (!res.ok) return;
        const data = (await res.json()) as typeof phases;
        setPhases(data);
      } catch {
        setPhases([]);
      }
    }, []);

    const refresh = React.useCallback(async () => {
      setLoading(true);
      setError('');
      try {
        const res = await fetch('http://localhost:8000/api/loans', { headers: officerHeaders });
        if (!res.ok) {
          const t = await res.text();
          setError(t || `Failed to load loans (${res.status})`);
          return;
        }
        const data = (await res.json()) as typeof loans;
        setLoans(data);
        if (!selectedId && data.length > 0) setSelectedId(data[0].id);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load loans');
      } finally {
        setLoading(false);
      }
    }, [officerHeaders, selectedId]);

    React.useEffect(() => {
      void refreshPhases();
      void refresh();
    }, [refresh, refreshPhases]);

    const phasesById = React.useMemo(() => {
      const out: Record<string, (typeof phases)[number]> = {};
      for (const p of phases) out[p.id] = p;
      return out;
    }, [phases]);

    const orderedPhaseIds = React.useMemo(() => {
      return [...phases]
        .sort((a, b) => (a.sortOrder || 0) - (b.sortOrder || 0))
        .map((p) => p.id);
    }, [phases]);

    const grouped = React.useMemo(() => {
      const groups: Record<string, typeof loans> = { unassigned: [] };
      for (const pid of orderedPhaseIds) groups[pid] = [];
      for (const l of loans) {
        const pid = l.currentPhaseId || '';
        if (pid && phasesById[pid]) {
          if (!groups[pid]) groups[pid] = [];
          groups[pid].push(l);
        } else {
          groups.unassigned.push(l);
        }
      }
      return groups;
    }, [loans, orderedPhaseIds, phasesById]);

    const checklistItems = React.useMemo(() => {
      const raw = selected?.documentChecklist as unknown;
      if (!raw || typeof raw !== 'object') return [];
      const items = (raw as { items?: unknown }).items;
      if (!Array.isArray(items)) return [];
      return items
        .map((x) => (x && typeof x === 'object' ? (x as Record<string, unknown>) : null))
        .filter(Boolean)
        .map((item) => {
          const name = typeof item?.name === 'string' ? item.name : '';
          const status = typeof item?.status === 'string' ? item.status : 'missing';
          return { name, status: status as DocumentStatus };
        })
        .filter((x) => Boolean(x.name));
    }, [selected?.documentChecklist]);

    const updateDocStatus = async (name: string, status: DocumentStatus) => {
      if (!selected) return;
      const res = await fetch(`http://localhost:8000/api/loans/${selected.id}/documents`, {
        method: 'PATCH',
        headers: { ...officerHeaders, 'content-type': 'application/json' },
        body: JSON.stringify({ name, status }),
      });
      if (!res.ok) return;
      const updated = (await res.json()) as (typeof loans)[number];
      setLoans((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    };

    const updateLoanPhase = async (phaseId: string | null) => {
      if (!selected) return;
      const res = await fetch(`http://localhost:8000/api/loans/${selected.id}`, {
        method: 'PATCH',
        headers: { ...officerHeaders, 'content-type': 'application/json' },
        body: JSON.stringify({ currentPhaseId: phaseId }),
      });
      if (!res.ok) return;
      const updated = (await res.json()) as (typeof loans)[number];
      setLoans((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    };

    return (
      <OfficerChrome>
        <div style={{ padding: '16px' }}>
          <h1 style={{ marginTop: 0 }}>Loans</h1>
          <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '16px', alignItems: 'start' }}>
            <div style={{ border: '1px solid #e5e7eb', borderRadius: '12px', background: '#fff' }}>
              <div style={{ padding: '12px 14px', borderBottom: '1px solid #e5e7eb', fontWeight: 900 }}>Pipeline</div>
              {loading ? <div style={{ padding: '12px 14px', color: '#6b7280' }}>Loading…</div> : null}
              {error ? <div style={{ padding: '12px 14px', color: '#b91c1c' }}>{error}</div> : null}
              <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                <div data-testid="pipeline-group-unassigned">
                  <div style={{ padding: '10px 14px', background: '#f9fafb', borderBottom: '1px solid #f3f4f6', fontWeight: 900 }}>
                    Unassigned ({grouped.unassigned.length})
                  </div>
                  {grouped.unassigned.map((l) => (
                    <button
                      key={l.id}
                      type="button"
                      onClick={() => setSelectedId(l.id)}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        border: 'none',
                        borderBottom: '1px solid #f3f4f6',
                        backgroundColor: selectedId === l.id ? '#eff6ff' : '#ffffff',
                        padding: '12px 14px',
                        cursor: 'pointer',
                      }}
                      data-testid={`loan-row-${l.id}`}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                        <div style={{ fontWeight: 800, color: '#111827' }}>{l.borrowerName || 'Borrower'}</div>
                        <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{l.status || '—'}</div>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '4px' }}>
                        {l.loanType || 'Loan'} · {l.loanAmount || '—'} {l.catalogProductCode ? `· ${l.catalogProductCode}` : ''}
                      </div>
                    </button>
                  ))}
                </div>

                {orderedPhaseIds.map((pid) => (
                  <div key={pid} data-testid={`pipeline-group-${pid}`}>
                    <div style={{ padding: '10px 14px', background: '#f9fafb', borderBottom: '1px solid #f3f4f6', fontWeight: 900 }}>
                      {phasesById[pid]?.name || 'Phase'} ({grouped[pid]?.length || 0})
                    </div>
                    {(grouped[pid] || []).map((l) => (
                      <button
                        key={l.id}
                        type="button"
                        onClick={() => setSelectedId(l.id)}
                        style={{
                          width: '100%',
                          textAlign: 'left',
                          border: 'none',
                          borderBottom: '1px solid #f3f4f6',
                          backgroundColor: selectedId === l.id ? '#eff6ff' : '#ffffff',
                          padding: '12px 14px',
                          cursor: 'pointer',
                        }}
                        data-testid={`loan-row-${l.id}`}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                          <div style={{ fontWeight: 800, color: '#111827' }}>{l.borrowerName || 'Borrower'}</div>
                          <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{l.status || '—'}</div>
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '4px' }}>
                          {l.loanType || 'Loan'} · {l.loanAmount || '—'} {l.catalogProductCode ? `· ${l.catalogProductCode}` : ''}
                        </div>
                      </button>
                    ))}
                  </div>
                ))}
                {!loading && loans.length === 0 ? <div style={{ padding: '12px 14px', color: '#6b7280' }}>No loans yet.</div> : null}
              </div>
            </div>

            <div style={{ border: '1px solid #e5e7eb', borderRadius: '12px', background: '#fff', padding: '18px' }}>
              <h2 style={{ marginTop: 0, marginBottom: '12px' }}>Loan Detail</h2>
              {!selected ? (
                <div style={{ color: '#6b7280' }}>Select a loan to review.</div>
              ) : (
                <div style={{ display: 'grid', gap: '14px' }}>
                  <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>
                    ID: <span style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>{selected.id}</span>
                  </div>

                  <div style={{ display: 'grid', gap: '6px' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 900, color: '#111827' }}>Phase</div>
                    <select
                      value={selected.currentPhaseId || ''}
                      onChange={(e) => void updateLoanPhase(e.target.value ? e.target.value : null)}
                      style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1px solid #e5e7eb', backgroundColor: '#ffffff' }}
                      data-testid="select-loan-phase"
                    >
                      <option value="">Unassigned</option>
                      {orderedPhaseIds.map((pid) => (
                        <option key={pid} value={pid}>
                          {phasesById[pid]?.name || 'Phase'}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div style={{ border: '1px solid #f3f4f6', borderRadius: '10px', padding: '12px', backgroundColor: '#fafafa' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 900, color: '#111827', marginBottom: '10px' }} data-testid="text-doc-checklist-title">
                      Document Checklist
                    </div>
                    {checklistItems.length === 0 ? (
                      <div style={{ color: '#6b7280' }}>No checklist available.</div>
                    ) : (
                      <div style={{ display: 'grid', gap: '10px' }}>
                        {checklistItems.map((i) => (
                          <div
                            key={i.name}
                            style={{ display: 'grid', gridTemplateColumns: '1fr 160px', gap: '10px', alignItems: 'center' }}
                          >
                            <div style={{ fontWeight: 700, color: '#111827' }}>{i.name}</div>
                            <div style={{ display: 'grid', gap: '4px' }}>
                              <select
                                value={i.status}
                                onChange={(e) => void updateDocStatus(i.name, e.target.value as DocumentStatus)}
                                style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid #e5e7eb', backgroundColor: '#ffffff' }}
                                data-testid={`select-doc-status-${i.name}`}
                              >
                                <option value="missing">missing</option>
                                <option value="submitted">submitted</option>
                                <option value="verified">verified</option>
                                <option value="rejected">rejected</option>
                              </select>
                              <div style={{ fontSize: '0.85rem', color: '#6b7280' }} data-testid={`doc-status-${i.name}`}>
                                {i.status}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </OfficerChrome>
    );
  };

  const LoanProductsPage = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [items, setItems] = useState<
      Array<{
        id: string;
        name: string;
        code: string;
        category?: string | null;
        description?: string | null;
        status?: string | null;
        baseInterestRate?: string | null;
        minAmount?: string | null;
        maxAmount?: string | null;
        collateralRequired?: boolean | null;
        insuranceRequired?: boolean | null;
        requiredDocuments?: unknown;
        eligibilityCriteria?: unknown;
        features?: unknown;
      }>
    >([]);
    const [mode, setMode] = useState<'none' | 'create' | 'edit'>('none');
    const [editingId, setEditingId] = useState<string | null>(null);
    const [formName, setFormName] = useState('');
    const [formCode, setFormCode] = useState('');
    const [formCategory, setFormCategory] = useState('home_loan');
    const [formStatus, setFormStatus] = useState('draft');
    const [formDescription, setFormDescription] = useState('');
    const [formBaseRate, setFormBaseRate] = useState('');
    const [formMinAmount, setFormMinAmount] = useState('');
    const [formMaxAmount, setFormMaxAmount] = useState('');
    const [formCollateralRequired, setFormCollateralRequired] = useState(false);
    const [formInsuranceRequired, setFormInsuranceRequired] = useState(false);
    const [formRequiredDocsText, setFormRequiredDocsText] = useState('');
    const [formEligibilityText, setFormEligibilityText] = useState('');
    const [formFeaturesText, setFormFeaturesText] = useState('');

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
        const data = (await res.json()) as Array<{
          id: string;
          name: string;
          code: string;
          category?: string | null;
          description?: string | null;
          status?: string | null;
          baseInterestRate?: string | null;
          minAmount?: string | null;
          maxAmount?: string | null;
          collateralRequired?: boolean | null;
          insuranceRequired?: boolean | null;
          requiredDocuments?: unknown;
          eligibilityCriteria?: unknown;
          features?: unknown;
        }>;
        setItems(data);
      } catch {
        setError('Failed to load');
      } finally {
        setLoading(false);
      }
    };

    const normalizeListText = (value: unknown) => {
      if (!Array.isArray(value)) return '';
      return value.filter((x) => typeof x === 'string').join('\n');
    };

    const resetForm = () => {
      setFormName('');
      setFormCode('');
      setFormCategory('home_loan');
      setFormStatus('draft');
      setFormDescription('');
      setFormBaseRate('');
      setFormMinAmount('');
      setFormMaxAmount('');
      setFormCollateralRequired(false);
      setFormInsuranceRequired(false);
      setFormRequiredDocsText('');
      setFormEligibilityText('');
      setFormFeaturesText('');
      setEditingId(null);
    };

    const openCreate = () => {
      resetForm();
      setMode('create');
    };

    const openEdit = (p: (typeof items)[number]) => {
      setFormName(p.name || '');
      setFormCode(p.code || '');
      setFormCategory(p.category || 'home_loan');
      setFormStatus(p.status || 'draft');
      setFormDescription(p.description || '');
      setFormBaseRate(p.baseInterestRate || '');
      setFormMinAmount(p.minAmount || '');
      setFormMaxAmount(p.maxAmount || '');
      setFormCollateralRequired(Boolean(p.collateralRequired));
      setFormInsuranceRequired(Boolean(p.insuranceRequired));
      setFormRequiredDocsText(normalizeListText(p.requiredDocuments));
      setFormEligibilityText(normalizeListText(p.eligibilityCriteria));
      setFormFeaturesText(normalizeListText(p.features));
      setEditingId(p.id);
      setMode('edit');
    };

    const parseListText = (text: string) =>
      text
        .split('\n')
        .map((x) => x.trim())
        .filter(Boolean);

    const validateForm = () => {
      if (!formName.trim()) return 'Name is required';
      if (!formCode.trim()) return 'Code is required';
      if (!formCategory.trim()) return 'Category is required';
      return null;
    };

    const saveCreate = async () => {
      const validation = validateForm();
      if (validation) {
        setError(validation);
        return;
      }
      setLoading(true);
      setError('');
      try {
        const payload = {
          name: formName.trim(),
          code: formCode.trim(),
          category: formCategory.trim(),
          status: formStatus.trim(),
          description: formDescription.trim() || null,
          baseInterestRate: formBaseRate.trim() || null,
          minAmount: formMinAmount.trim() || null,
          maxAmount: formMaxAmount.trim() || null,
          collateralRequired: formCollateralRequired,
          insuranceRequired: formInsuranceRequired,
          requiredDocuments: parseListText(formRequiredDocsText),
          eligibilityCriteria: parseListText(formEligibilityText),
          features: parseListText(formFeaturesText),
        };
        const res = await fetch('http://localhost:8000/api/catalog-products', {
          method: 'POST',
          headers: { 'content-type': 'application/json', 'x-officer-role': 'loan-officer-access' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const detail = await res.text();
          setError(detail || `Failed to create: ${res.status}`);
          return;
        }
        setMode('none');
        resetForm();
        await refresh();
      } catch {
        setError('Failed to create');
      } finally {
        setLoading(false);
      }
    };

    const saveEdit = async () => {
      const validation = validateForm();
      if (validation) {
        setError(validation);
        return;
      }
      if (!editingId) {
        setError('No product selected');
        return;
      }
      setLoading(true);
      setError('');
      try {
        const payload = {
          name: formName.trim(),
          code: formCode.trim(),
          category: formCategory.trim(),
          status: formStatus.trim(),
          description: formDescription.trim(),
          baseInterestRate: formBaseRate.trim(),
          minAmount: formMinAmount.trim(),
          maxAmount: formMaxAmount.trim(),
          collateralRequired: formCollateralRequired,
          insuranceRequired: formInsuranceRequired,
          requiredDocuments: parseListText(formRequiredDocsText),
          eligibilityCriteria: parseListText(formEligibilityText),
          features: parseListText(formFeaturesText),
        };
        const res = await fetch(`http://localhost:8000/api/catalog-products/${editingId}`, {
          method: 'PATCH',
          headers: { 'content-type': 'application/json', 'x-officer-role': 'loan-officer-access' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const detail = await res.text();
          setError(detail || `Failed to update: ${res.status}`);
          return;
        }
        setMode('none');
        resetForm();
        await refresh();
      } catch {
        setError('Failed to update');
      } finally {
        setLoading(false);
      }
    };

    React.useEffect(() => {
      void refresh();
    }, []);

    const formTitle = mode === 'create' ? 'Create Product' : mode === 'edit' ? 'Edit Product' : '';

    return (
      <OfficerChrome>
        <div style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
            <h1 style={{ margin: 0 }} data-testid="heading-loan-products">
              Loan Products
            </h1>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <button
                type="button"
                onClick={() => void refresh()}
                disabled={loading}
                style={{ padding: '8px 10px' }}
                data-testid="button-refresh-products"
              >
                Refresh
              </button>
              <button
                type="button"
                onClick={openCreate}
                disabled={loading}
                style={{ padding: '8px 10px', fontWeight: 800 }}
                data-testid="button-create-product"
              >
                New Product
              </button>
            </div>
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
          {mode !== 'none' ? (
            <div style={{ marginTop: '12px', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px' }} data-testid="product-form">
              <div style={{ fontWeight: 900, marginBottom: '10px' }}>{formTitle}</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div style={{ display: 'grid', gap: '6px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>Name</div>
                  <input
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
                    data-testid={mode === 'create' ? 'input-create-name' : 'input-edit-name'}
                  />
                </div>
                <div style={{ display: 'grid', gap: '6px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>Code</div>
                  <input
                    value={formCode}
                    onChange={(e) => setFormCode(e.target.value)}
                    style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
                    data-testid={mode === 'create' ? 'input-create-code' : 'input-edit-code'}
                  />
                </div>
                <div style={{ display: 'grid', gap: '6px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>Category</div>
                  <select
                    value={formCategory}
                    onChange={(e) => setFormCategory(e.target.value)}
                    style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
                    data-testid={mode === 'create' ? 'select-create-category' : 'select-edit-category'}
                  >
                    <option value="home_loan">home_loan</option>
                    <option value="auto_loan">auto_loan</option>
                    <option value="personal_loan">personal_loan</option>
                  </select>
                </div>
                <div style={{ display: 'grid', gap: '6px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>Status</div>
                  <select
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value)}
                    style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
                    data-testid={mode === 'create' ? 'select-create-status' : 'select-edit-status'}
                  >
                    <option value="draft">draft</option>
                    <option value="active">active</option>
                    <option value="inactive">inactive</option>
                  </select>
                </div>
                <div style={{ display: 'grid', gap: '6px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>Base Rate</div>
                  <input
                    value={formBaseRate}
                    onChange={(e) => setFormBaseRate(e.target.value)}
                    style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
                    placeholder="e.g. 8.40%"
                    data-testid={mode === 'create' ? 'input-create-base-rate' : 'input-edit-base-rate'}
                  />
                </div>
                <div style={{ display: 'grid', gap: '6px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>Min Amount</div>
                  <input
                    value={formMinAmount}
                    onChange={(e) => setFormMinAmount(e.target.value)}
                    style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
                    placeholder="e.g. ₹5,00,000"
                    data-testid={mode === 'create' ? 'input-create-min-amount' : 'input-edit-min-amount'}
                  />
                </div>
                <div style={{ display: 'grid', gap: '6px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>Max Amount</div>
                  <input
                    value={formMaxAmount}
                    onChange={(e) => setFormMaxAmount(e.target.value)}
                    style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db' }}
                    placeholder="e.g. ₹10,00,00,000"
                    data-testid={mode === 'create' ? 'input-create-max-amount' : 'input-edit-max-amount'}
                  />
                </div>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <label style={{ display: 'flex', gap: '8px', alignItems: 'center', color: '#374151' }}>
                    <input
                      type="checkbox"
                      checked={formCollateralRequired}
                      onChange={(e) => setFormCollateralRequired(e.target.checked)}
                      data-testid={mode === 'create' ? 'checkbox-create-collateral' : 'checkbox-edit-collateral'}
                    />
                    Collateral required
                  </label>
                  <label style={{ display: 'flex', gap: '8px', alignItems: 'center', color: '#374151' }}>
                    <input
                      type="checkbox"
                      checked={formInsuranceRequired}
                      onChange={(e) => setFormInsuranceRequired(e.target.checked)}
                      data-testid={mode === 'create' ? 'checkbox-create-insurance' : 'checkbox-edit-insurance'}
                    />
                    Insurance required
                  </label>
                </div>
              </div>
              <div style={{ display: 'grid', gap: '10px', marginTop: '10px' }}>
                <div style={{ display: 'grid', gap: '6px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>Description</div>
                  <textarea
                    value={formDescription}
                    onChange={(e) => setFormDescription(e.target.value)}
                    style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db', minHeight: '64px' }}
                    data-testid={mode === 'create' ? 'textarea-create-description' : 'textarea-edit-description'}
                  />
                </div>
                <div style={{ display: 'grid', gap: '6px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>Required Documents (one per line)</div>
                  <textarea
                    value={formRequiredDocsText}
                    onChange={(e) => setFormRequiredDocsText(e.target.value)}
                    style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db', minHeight: '84px' }}
                    data-testid={mode === 'create' ? 'textarea-create-required-docs' : 'textarea-edit-required-docs'}
                  />
                </div>
                <div style={{ display: 'grid', gap: '6px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>Eligibility Criteria (one per line)</div>
                  <textarea
                    value={formEligibilityText}
                    onChange={(e) => setFormEligibilityText(e.target.value)}
                    style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db', minHeight: '84px' }}
                    data-testid={mode === 'create' ? 'textarea-create-eligibility' : 'textarea-edit-eligibility'}
                  />
                </div>
                <div style={{ display: 'grid', gap: '6px' }}>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>Features (one per line)</div>
                  <textarea
                    value={formFeaturesText}
                    onChange={(e) => setFormFeaturesText(e.target.value)}
                    style={{ padding: '10px', borderRadius: '8px', border: '1px solid #d1d5db', minHeight: '84px' }}
                    data-testid={mode === 'create' ? 'textarea-create-features' : 'textarea-edit-features'}
                  />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => {
                    setMode('none');
                    resetForm();
                  }}
                  style={{ padding: '8px 10px' }}
                  data-testid={mode === 'create' ? 'button-cancel-create' : 'button-cancel-edit'}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => void (mode === 'create' ? saveCreate() : saveEdit())}
                  disabled={loading}
                  style={{ padding: '8px 10px', fontWeight: 800 }}
                  data-testid={mode === 'create' ? 'button-save-create' : 'button-save-edit'}
                >
                  Save
                </button>
              </div>
            </div>
          ) : null}
          <div style={{ marginTop: '12px', display: 'grid', gap: '10px' }}>
            {items.map((p) => (
              <div
                key={p.id}
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: '10px',
                  padding: '12px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: '12px',
                  alignItems: 'flex-start',
                }}
                data-testid={`loan-product-${p.code}`}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 900, color: '#111827' }}>{p.name}</div>
                  <div style={{ color: '#6b7280', marginTop: '2px' }}>
                    {p.code}
                    {p.category ? ` · ${p.category}` : ''}
                    {p.status ? ` · ${p.status}` : ''}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button
                    type="button"
                    onClick={() => openEdit(p)}
                    style={{ padding: '6px 10px' }}
                    data-testid={`button-edit-product-${p.id}`}
                  >
                    Edit
                  </button>
                </div>
              </div>
            ))}
            {!loading && !error && items.length === 0 ? <div style={{ color: '#6b7280' }}>No products.</div> : null}
          </div>
        </div>
      </OfficerChrome>
    );
  };

  type V2Message = {
    id: string;
    conversationId: string;
    role: 'user' | 'assistant';
    content: string;
    metadata?: unknown;
    createdAt: string | null;
  };

  const OfficerChatPage = () => {
    const [loadingLeads, setLoadingLeads] = useState(false);
    const [loadingMessages, setLoadingMessages] = useState(false);
    const [sending, setSending] = useState(false);
    const [error, setError] = useState('');
    const [leads, setLeads] = useState<V2Conversation[]>([]);
    const [selectedId, setSelectedId] = useState('');
    const [selected, setSelected] = useState<V2Conversation | null>(null);
    const [messages, setMessages] = useState<V2Message[]>([]);
    const [input, setInput] = useState('');
    const messagesEndRef = React.useRef<HTMLDivElement | null>(null);

    const officerHeaders = React.useMemo<Record<string, string>>(() => ({ 'x-officer-role': 'loan-officer-access' }), []);

    const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    React.useEffect(scrollToBottom, [messages]);

    const refreshLeads = React.useCallback(async (preferId?: string) => {
      setLoadingLeads(true);
      setError('');
      try {
        const res = await fetch('http://localhost:8000/api/conversations', { headers: officerHeaders });
        if (!res.ok) {
          const t = await res.text();
          setError(t || `Failed to load leads (${res.status})`);
          return;
        }
        const payload = (await res.json()) as V2Conversation[];
        setLeads(payload);
        const next = preferId || selectedId || (payload.length > 0 ? payload[0].id : '');
        if (next && next !== selectedId) setSelectedId(next);
        if (!next) {
          setSelected(null);
          setMessages([]);
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load leads');
      } finally {
        setLoadingLeads(false);
      }
    }, [officerHeaders, selectedId]);

    const loadThread = React.useCallback(async (conversationId: string) => {
      setLoadingMessages(true);
      setError('');
      try {
        const [convRes, msgsRes] = await Promise.all([
          fetch(`http://localhost:8000/api/conversations/${conversationId}`, { headers: officerHeaders }),
          fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`, { headers: officerHeaders }),
        ]);

        if (!convRes.ok) {
          const t = await convRes.text();
          setError(t || `Failed to load lead (${convRes.status})`);
          return;
        }
        if (!msgsRes.ok) {
          const t = await msgsRes.text();
          setError(t || `Failed to load messages (${msgsRes.status})`);
          return;
        }

        setSelected((await convRes.json()) as V2Conversation);
        setMessages((await msgsRes.json()) as V2Message[]);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load conversation');
      } finally {
        setLoadingMessages(false);
      }
    }, [officerHeaders]);

    React.useEffect(() => {
      void refreshLeads();
    }, [refreshLeads]);

    React.useEffect(() => {
      if (!selectedId) return;
      void loadThread(selectedId);
    }, [loadThread, selectedId]);

    const formatApprovalProbability = (value: unknown) => {
      if (typeof value === 'number' && Number.isFinite(value)) return `${Math.round(value * 100)}%`;
      if (typeof value === 'string') return value;
      if (value && typeof value === 'object' && typeof (value as { value?: unknown }).value === 'number') {
        const v = (value as { value: number }).value;
        return `${Math.round(v * 100)}%`;
      }
      return '—';
    };

    const latestActionResults = React.useMemo(() => {
      for (let i = messages.length - 1; i >= 0; i -= 1) {
        const m = messages[i];
        if (m.role !== 'assistant') continue;
        if (!m.metadata || typeof m.metadata !== 'object') continue;
        const raw = (m.metadata as { actionResults?: unknown }).actionResults;
        if (Array.isArray(raw)) return raw as Array<Record<string, unknown>>;
      }
      return null;
    }, [messages]);

    const latestLoanId = React.useMemo(() => {
      if (!latestActionResults) return null;
      const hit = latestActionResults.find((r) => r && typeof r === 'object' && typeof (r as { loanId?: unknown }).loanId === 'string');
      return hit ? ((hit as { loanId: string }).loanId || null) : null;
    }, [latestActionResults]);

    const handleSend = async () => {
      const text = input.trim();
      if (!text || sending || loadingMessages) return;
      if (!selectedId) {
        setError('Select a lead first.');
        return;
      }

      setSending(true);
      setError('');
      setInput('');

      const now = Date.now();
      const optimistic: V2Message = {
        id: `temp-user-${now}`,
        conversationId: selectedId,
        role: 'user',
        content: text,
        createdAt: new Date(now).toISOString(),
      };
      setMessages((prev) => [...prev, optimistic]);

      try {
        const res = await fetch(`http://localhost:8000/api/conversations/${selectedId}/messages`, {
          method: 'POST',
          headers: { ...officerHeaders, 'content-type': 'application/json' },
          body: JSON.stringify({ content: text }),
        });
        if (!res.ok) {
          const t = await res.text();
          setError(t || `Failed to send message (${res.status})`);
          return;
        }
        const payload = (await res.json()) as { message?: V2Message };
        if (payload.message?.id && payload.message.content) {
          setMessages((prev) => [...prev, payload.message as V2Message]);
        }
        await refreshLeads(selectedId);
        const refreshed = await fetch(`http://localhost:8000/api/conversations/${selectedId}`, { headers: officerHeaders });
        if (refreshed.ok) setSelected((await refreshed.json()) as V2Conversation);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to send message');
      } finally {
        setSending(false);
      }
    };

    return (
      <OfficerChrome>
        <div style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
            <h1 style={{ marginTop: 0, marginBottom: 0 }} data-testid="heading-officer-chat">
              Officer Chat
            </h1>
            <button type="button" onClick={() => void refreshLeads()} style={{ padding: '8px 10px' }} disabled={loadingLeads || loadingMessages || sending}>
              Refresh
            </button>
          </div>

          {error ? (
            <div style={{ marginTop: '12px', color: '#b91c1c', fontWeight: 700 }} data-testid="text-officer-chat-error">
              {error}
            </div>
          ) : null}

          <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: '16px', marginTop: '12px', alignItems: 'stretch' }}>
            <div style={{ border: '1px solid #e5e7eb', borderRadius: '12px', backgroundColor: '#ffffff', overflow: 'hidden' }}>
              <div style={{ padding: '12px 12px', borderBottom: '1px solid #e5e7eb', fontWeight: 800 }}>Leads</div>
              <div style={{ maxHeight: '70vh', overflowY: 'auto' }} data-testid="officer-chat-leads">
                {loadingLeads ? <div style={{ padding: '12px', color: '#6b7280' }}>Loading…</div> : null}
                {!loadingLeads && leads.length === 0 ? <div style={{ padding: '12px', color: '#6b7280' }}>No leads yet.</div> : null}
                {leads.map((l) => (
                  <button
                    key={l.id}
                    type="button"
                    onClick={() => setSelectedId(l.id)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      border: 'none',
                      borderBottom: '1px solid #f3f4f6',
                      backgroundColor: selectedId === l.id ? '#eff6ff' : '#ffffff',
                      padding: '12px 12px',
                      cursor: 'pointer',
                    }}
                    data-testid={`officer-chat-lead-${l.id}`}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                      <div style={{ fontWeight: 800, color: '#111827' }}>{l.borrowerName || `Lead #${l.id.slice(0, 8)}`}</div>
                      <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{l.status || '—'}</div>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '4px', display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                      <div>Officer: {l.assignedOfficer || 'Unassigned'}</div>
                      <div>Fit: {l.fitScore ?? '—'}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div style={{ border: '1px solid #e5e7eb', borderRadius: '12px', backgroundColor: '#ffffff', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '12px 14px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '12px' }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 900, color: '#111827', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {selected ? selected.borrowerName || `Lead #${selected.id.slice(0, 8)}` : 'Select a lead'}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '2px' }}>
                    Status: {selected?.status || '—'} · Approval: {formatApprovalProbability(selected?.approvalProbability)}
                  </div>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>Phase: {selected?.currentPhaseId || '—'}</div>
              </div>

              {latestActionResults && latestActionResults.length > 0 ? (
                <div style={{ padding: '10px 14px', borderBottom: '1px solid #e5e7eb', backgroundColor: '#ffffff' }} data-testid="officer-chat-action-results">
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center' }}>
                    <div style={{ fontWeight: 900, color: '#111827' }}>Action Results</div>
                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                      <Link to="/pipeline" style={{ fontSize: '0.85rem' }} data-testid="officer-chat-open-pipeline">
                        Open pipeline
                      </Link>
                      {latestLoanId ? (
                        <span style={{ fontSize: '0.85rem', color: '#6b7280' }} data-testid="officer-chat-last-loan">
                          Loan: {latestLoanId.slice(0, 8)}
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {latestActionResults.map((r, idx) => {
                      const row = r && typeof r === 'object' ? (r as Record<string, unknown>) : {};
                      const type = typeof row.type === 'string' ? row.type : 'unknown';
                      const status = typeof row.status === 'string' ? row.status : 'unknown';
                      const loanId = typeof row.loanId === 'string' ? row.loanId : null;
                      const phaseName = typeof row.phaseName === 'string' ? row.phaseName : null;
                      const errorText = typeof row.error === 'string' ? row.error : null;
                      const ok = status === 'success';
                      return (
                        <div
                          key={`${type}-${idx}`}
                          style={{
                            borderRadius: '10px',
                            padding: '8px 10px',
                            border: `1px solid ${ok ? '#d1fae5' : '#fee2e2'}`,
                            backgroundColor: ok ? '#ecfdf5' : '#fef2f2',
                            color: '#111827',
                            display: 'flex',
                            justifyContent: 'space-between',
                            gap: '12px',
                            alignItems: 'baseline',
                          }}
                          data-testid={`officer-chat-action-${idx}`}
                        >
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontWeight: 900 }}>
                              {type} · {status}
                            </div>
                            <div style={{ fontSize: '0.85rem', color: '#374151', marginTop: '2px' }}>
                              {loanId ? `Loan: ${loanId}` : null}
                              {loanId && phaseName ? ' · ' : null}
                              {phaseName ? `Phase: ${phaseName}` : null}
                              {!loanId && !phaseName ? '—' : null}
                            </div>
                            {errorText ? (
                              <div style={{ fontSize: '0.85rem', color: '#b91c1c', marginTop: '4px', fontWeight: 700 }}>{errorText}</div>
                            ) : null}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              <div
                style={{
                  flex: 1,
                  overflowY: 'auto',
                  padding: '16px',
                  backgroundColor: '#f9fafb',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
                data-testid="officer-chat-messages"
              >
                {loadingMessages ? <div style={{ color: '#6b7280' }}>Loading conversation…</div> : null}
                {!loadingMessages && !selected ? <div style={{ color: '#6b7280' }}>Choose a lead on the left to view the thread.</div> : null}
                {messages.map((m) => (
                  <div key={m.id} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                    <div
                      data-testid={`officer-chat-message-${m.role}`}
                      style={{
                        maxWidth: '80%',
                        padding: '12px 16px',
                        borderRadius: '16px',
                        borderBottomRightRadius: m.role === 'user' ? '4px' : '16px',
                        borderBottomLeftRadius: m.role === 'user' ? '16px' : '4px',
                        backgroundColor: m.role === 'user' ? '#4f46e5' : '#ffffff',
                        color: m.role === 'user' ? '#ffffff' : '#1f2937',
                        boxShadow: m.role === 'user' ? '0 1px 2px rgba(79, 70, 229, 0.2)' : '0 1px 2px rgba(0, 0, 0, 0.05)',
                        border: m.role === 'user' ? 'none' : '1px solid #e5e7eb',
                        fontSize: '14px',
                        lineHeight: '1.6',
                      }}
                    >
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              <div style={{ padding: '12px 14px', borderTop: '1px solid #e5e7eb', backgroundColor: '#ffffff' }}>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') void handleSend();
                    }}
                    placeholder={selected ? 'Type a message…' : 'Select a lead to send messages'}
                    disabled={!selected || sending}
                    style={{
                      flex: 1,
                      padding: '12px 14px',
                      borderRadius: '999px',
                      border: '1px solid #d1d5db',
                      backgroundColor: !selected ? '#f3f4f6' : '#ffffff',
                      outline: 'none',
                      fontSize: '14px',
                    }}
                    data-testid="officer-chat-input"
                  />
                  <button
                    type="button"
                    onClick={() => void handleSend()}
                    disabled={!selected || sending || !input.trim()}
                    style={{
                      padding: '12px 14px',
                      borderRadius: '999px',
                      border: 'none',
                      backgroundColor: !selected || sending || !input.trim() ? '#e5e7eb' : '#4f46e5',
                      color: '#ffffff',
                      fontWeight: 800,
                      cursor: !selected || sending || !input.trim() ? 'not-allowed' : 'pointer',
                      minWidth: '92px',
                    }}
                    data-testid="officer-chat-send"
                  >
                    Send
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </OfficerChrome>
    );
  };

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

  const PhaseDetailPage = () => {
    const params = useParams<{ id: string }>();
    const phaseId = (params.id || '').trim();
    const [phases, setPhases] = useState<V2Phase[] | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string>('');

    React.useEffect(() => {
      let mounted = true;
      const run = async () => {
        setLoading(true);
        setError('');
        try {
          const res = await fetch('http://localhost:8000/api/phases');
          if (!res.ok) throw new Error(`Failed to load phases (${res.status})`);
          const payload = (await res.json()) as V2Phase[];
          if (!mounted) return;
          setPhases(payload);
        } catch (e) {
          if (!mounted) return;
          setPhases([]);
          setError(e instanceof Error ? e.message : 'Failed to load phases');
        } finally {
          if (mounted) setLoading(false);
        }
      };
      run();
      return () => {
        mounted = false;
      };
    }, []);

    const activePhases = React.useMemo(() => {
      return (phases || [])
        .filter((p) => p.isActive)
        .slice()
        .sort((a, b) => a.sortOrder - b.sortOrder);
    }, [phases]);

    const phase = React.useMemo(() => {
      if (!phases || !phaseId) return null;
      return phases.find((p) => p.id === phaseId) || null;
    }, [phases, phaseId]);

    const homeHref = role === 'admin' ? '/dashboard' : '/';

    if (loading) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d]">
          <header className="sticky top-0 z-50 bg-white/80 dark:bg-[#0d0d0d]/80 backdrop-blur-xl border-b border-slate-200/60 dark:border-white/[0.06]">
            <div className="max-w-5xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Link to={homeHref} className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                  Back
                </Link>
                <span className="text-slate-300 dark:text-white/10">/</span>
                <span className="text-sm font-semibold text-slate-900 dark:text-white">Phase Details</span>
              </div>
              <div className="flex items-center gap-2">
                <ThemeToggle />
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm"
                >
                  Logout
                </button>
              </div>
            </div>
          </header>

          <main className="max-w-5xl mx-auto px-4 md:px-6 py-6">
            <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-xl shadow-black/[0.04] dark:shadow-black/40 p-6">
              <div className="h-7 w-52 bg-slate-200/70 dark:bg-white/[0.08] rounded-lg animate-pulse" />
              <div className="mt-3 h-4 w-96 max-w-full bg-slate-200/60 dark:bg-white/[0.06] rounded-lg animate-pulse" />
              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="h-40 bg-slate-200/40 dark:bg-white/[0.04] rounded-2xl animate-pulse" />
                <div className="h-40 bg-slate-200/40 dark:bg-white/[0.04] rounded-2xl animate-pulse" />
              </div>
            </div>
          </main>
        </div>
      );
    }

    if (!phase) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d] flex items-center justify-center px-4">
          <div className="max-w-md w-full rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-xl shadow-black/[0.04] dark:shadow-black/40 p-6 text-center">
            <div className="text-base font-extrabold tracking-tight text-slate-900 dark:text-white" data-testid="phase-not-found-title">
              Phase Not Found
            </div>
            <div className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              {error ? error : 'The requested loan phase could not be found.'}
            </div>
            <div className="mt-5 flex items-center justify-center gap-3">
              <Link
                to={homeHref}
                className="inline-flex items-center justify-center rounded-2xl px-4 py-2 text-xs font-semibold bg-blue-600 text-white shadow-sm"
              >
                Back to Home
              </Link>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d] relative overflow-hidden">
        <div className="absolute top-[-200px] left-1/4 w-[600px] h-[600px] bg-blue-200/15 dark:bg-blue-500/5 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-[-150px] right-1/4 w-[500px] h-[500px] bg-indigo-200/10 dark:bg-indigo-500/3 rounded-full blur-[100px] pointer-events-none" />

        <header className="sticky top-0 z-50 bg-white/80 dark:bg-[#0d0d0d]/80 backdrop-blur-xl border-b border-slate-200/60 dark:border-white/[0.06]">
          <div className="max-w-5xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-2 flex-wrap">
              <Link to={homeHref} className="text-sm font-semibold text-slate-700 dark:text-slate-200" data-testid="phase-back-link">
                Back
              </Link>
              <span className="text-slate-300 dark:text-white/10">/</span>
              <span className="text-sm font-semibold text-slate-900 dark:text-white">Phase Details</span>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm"
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        <main className="max-w-5xl mx-auto px-4 md:px-6 py-6 relative z-10">
          <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-xl shadow-black/[0.04] dark:shadow-black/40 p-6">
            <div className="flex items-start justify-between gap-6 flex-wrap">
              <div className="min-w-[220px]">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] flex items-center justify-center text-slate-700 dark:text-slate-200 font-black"
                    style={{ boxShadow: '0 10px 25px rgba(0,0,0,0.06)' }}
                    aria-hidden="true"
                  >
                    {phase.sortOrder}
                  </div>
                  <div>
                    <div className="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white" data-testid="phase-title">
                      {phase.name}
                    </div>
                    <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      {phase.description || '—'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <div
                  className={`rounded-2xl px-3 py-1.5 text-[11px] font-semibold border ${
                    phase.isActive
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200/70 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/20'
                      : 'bg-slate-50 text-slate-600 border-slate-200/70 dark:bg-white/[0.04] dark:text-slate-300 dark:border-white/[0.08]'
                  }`}
                  data-testid="phase-active-badge"
                >
                  {phase.isActive ? 'Active' : 'Inactive'}
                </div>
                <div className="rounded-2xl px-3 py-1.5 text-[11px] font-semibold bg-white/70 dark:bg-white/[0.03] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300">
                  Sort #{phase.sortOrder}
                </div>
                <div className="rounded-2xl px-3 py-1.5 text-[11px] font-semibold bg-white/70 dark:bg-white/[0.03] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300">
                  {phase.icon || '—'}
                </div>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4">
              <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] p-5">
                <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Operational Notes</div>
                <div className="mt-2 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                  This view is backed by the real phase catalog in the LOS database. Phase ordering and activation are used across borrower progress tracking and officer pipeline grouping.
                </div>
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.02] px-4 py-3">
                    <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Phase ID</div>
                    <div className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200 break-all" data-testid="phase-id">
                      {phase.id}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.02] px-4 py-3">
                    <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Last Updated</div>
                    <div className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200" data-testid="phase-updated-at">
                      {phase.updatedAt || phase.createdAt || '—'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] p-5">
                <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">All Active Phases</div>
                <div className="mt-3 grid gap-2" data-testid="phase-list">
                  {activePhases.map((p) => {
                    const selected = p.id === phase.id;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => navigate(`/phases/${p.id}`)}
                        className={`w-full text-left rounded-2xl px-3 py-2 border transition-colors ${
                          selected
                            ? 'bg-blue-50 border-blue-200/70 text-blue-800 dark:bg-blue-500/10 dark:border-blue-500/20 dark:text-blue-200'
                            : 'bg-white/70 border-slate-200/60 text-slate-700 hover:bg-white dark:bg-white/[0.02] dark:border-white/[0.06] dark:text-slate-200 dark:hover:bg-white/[0.04]'
                        }`}
                        data-testid={selected ? 'phase-list-item-selected' : undefined}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="text-xs font-semibold">{p.name}</div>
                          <div className="text-[10px] font-semibold opacity-70">#{p.sortOrder}</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  };

  return (
    <Routes>
      <Route
        path="/login"
        element={
          <LoginPage
            username={username}
            password={password}
            loginError={loginError}
            onSubmit={handleLogin}
            onUsernameChange={setUsername}
            onPasswordChange={setPassword}
          />
        }
      />
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
        path="/phases/:id"
        element={
          <RequireAuth>
            <PhaseDetailPage />
          </RequireAuth>
        }
      />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <RequireRole allow="admin">
              <DashboardPage />
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/pipeline"
        element={
          <RequireAuth>
            <RequireRole allow="admin">
              <PipelinePage />
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
      <Route
        path="/synthetic-data"
        element={
          <RequireAuth>
            <RequireRole allow="admin">
              <OfficerChrome>
                <SyntheticDataControl />
              </OfficerChrome>
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/training"
        element={
          <RequireAuth>
            <RequireRole allow="admin">
              <OfficerChrome>
                <TrainingPanel />
              </OfficerChrome>
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/metrics"
        element={
          <RequireAuth>
            <RequireRole allow="admin">
              <OfficerChrome>
                <MetricsPanel />
              </OfficerChrome>
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/simulator"
        element={
          <RequireAuth>
            <RequireRole allow="admin">
              <OfficerChrome>
                <SimulatorPanel />
              </OfficerChrome>
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/configuration"
        element={
          <RequireAuth>
            <RequireRole allow="admin">
              <OfficerChrome>
                <ConfigurationPanel />
              </OfficerChrome>
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to={isLoggedIn ? (role === 'admin' ? '/dashboard' : '/') : '/login'} replace />} />
    </Routes>
  );
}

export default App;
