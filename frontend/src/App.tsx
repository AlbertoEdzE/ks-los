import React, { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { ChatInterface, type V2Conversation, type V2Message as V2ChatMessage, type V2Phase } from './components/ChatInterface';
import { BorrowerJourneyTracker } from './components/chat';
import './App.css';
import { ConfigurationPanel } from './components/ConfigurationPanel';
import { MetricsPanel } from './components/MetricsPanel';
import MetricsDashboard from './components/MetricsDashboard';
import { SimulatorPanel } from './components/SimulatorPanel';
import { SyntheticDataControl } from './components/SyntheticDataControl';
import { TrainingPanel } from './components/TrainingPanel';
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CheckCircle2 } from 'lucide-react';
import { DocumentsCard } from './components/DocumentsCard';

type LoginPageProps = {
  mode: 'select' | 'borrower-login' | 'officer-login' | 'borrower-register' | 'officer-register' | 'borrower-forgot' | 'officer-forgot';
  username: string;
  password: string;
  loginError: string;
  onSubmit: (e: React.FormEvent) => void;
  onUsernameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onModeChange: (mode: LoginPageProps['mode']) => void;
  onClearError: () => void;
};

function LoginPage({ mode, username, password, loginError, onSubmit, onUsernameChange, onPasswordChange, onModeChange, onClearError }: LoginPageProps) {
  return (
    <div className="min-h-screen flex flex-col bg-[#f8f9fc] dark:bg-[#0d0d10] relative overflow-hidden">
      <div className="absolute top-[-200px] left-1/4 w-[600px] h-[600px] bg-[#0078D4]/[0.06] dark:bg-[#0078D4]/[0.04] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-150px] right-1/4 w-[500px] h-[500px] bg-indigo-200/30 dark:bg-[#0078D4]/[0.03] rounded-full blur-[100px] pointer-events-none" />

      <header className="relative z-10 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-2xl bg-white dark:bg-white/[0.07] flex items-center justify-center shadow-sm border border-gray-200/60 dark:border-white/[0.08]">
            <span className="text-sm font-black tracking-tight text-[#1B2A4A] dark:text-white">KS</span>
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight text-[#1B2A4A] dark:text-white">LoanAssist AI</h1>
            <p className="text-xs text-[#1B2A4A]/45 dark:text-white/45">by KSquare</p>
          </div>
        </div>
      </header>

      <div className="flex-1 flex items-center justify-center relative z-10 px-4">
        {mode === 'select' ? (
          <div className="w-full max-w-4xl">
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#D6E4F0] dark:bg-[#0078D4]/[0.12] border border-[#0078D4]/15 dark:border-[#0078D4]/20 mb-6">
                <span className="text-xs font-medium text-[#0078D4] dark:text-[#4da3e8]">AI-Powered Loan Origination</span>
              </div>
              <h2 className="text-3xl md:text-4xl font-bold text-[#1B2A4A] dark:text-white mb-3 tracking-tight">Welcome to LoanAssist</h2>
              <p className="text-[#1B2A4A]/55 dark:text-white/55 text-base max-w-lg mx-auto">
                Choose how you'd like to continue. Whether you're applying for a loan or managing applications, we've got you covered.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
              <button
                type="button"
                data-testid="select-borrower"
                onClick={() => {
                  onClearError();
                  onUsernameChange('');
                  onPasswordChange('');
                  onModeChange('borrower-login');
                }}
                className="group relative overflow-hidden rounded-3xl bg-white/80 dark:bg-white/[0.06] backdrop-blur-xl border border-gray-200/60 dark:border-white/[0.08] p-8 text-left shadow-xl shadow-black/[0.04] dark:shadow-black/40 hover:shadow-2xl hover:scale-[1.02] transition-all duration-500"
              >
                <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-[#D6E4F0] dark:from-[#0078D4]/[0.06] to-transparent rounded-bl-full" />
                <div className="relative">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#0078D4] to-[#005EA6] flex items-center justify-center mb-5 shadow-lg shadow-[#0078D4]/25">
                    <span className="text-white font-black text-xl">B</span>
                  </div>
                  <h3 className="text-xl font-bold text-[#1B2A4A] dark:text-white mb-2">Loan Applicant</h3>
                  <p className="text-sm text-[#1B2A4A]/60 dark:text-white/55 mb-5 leading-relaxed">
                    Apply for loans, track your application status, and get AI-powered guidance throughout the process.
                  </p>
                  <div className="mt-6 flex items-center gap-2 text-[#0078D4] font-medium text-sm">
                    Continue as Applicant <span className="translate-y-[1px]">→</span>
                  </div>
                </div>
              </button>

              <button
                type="button"
                data-testid="select-officer"
                onClick={() => {
                  onClearError();
                  onUsernameChange('');
                  onPasswordChange('');
                  onModeChange('officer-login');
                }}
                className="group relative overflow-hidden rounded-3xl bg-white/80 dark:bg-white/[0.06] backdrop-blur-xl border border-gray-200/60 dark:border-white/[0.08] p-8 text-left shadow-xl shadow-black/[0.04] dark:shadow-black/40 hover:shadow-2xl hover:scale-[1.02] transition-all duration-500"
              >
                <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-[#D6E4F0] dark:from-[#1B2A4A]/10 to-transparent rounded-bl-full" />
                <div className="relative">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#1B2A4A] to-[#1e1e22] flex items-center justify-center mb-5 shadow-lg shadow-[#1B2A4A]/25">
                    <span className="text-white font-black text-xl">O</span>
                  </div>
                  <h3 className="text-xl font-bold text-[#1B2A4A] dark:text-white mb-2">Loan Officer</h3>
                  <p className="text-sm text-[#1B2A4A]/60 dark:text-white/55 mb-5 leading-relaxed">
                    Manage loan applications, get AI-powered analysis, and streamline your origination workflow.
                  </p>
                  <div className="mt-6 flex items-center gap-2 text-[#1B2A4A] dark:text-[#4da3e8] font-medium text-sm">
                    Continue as Officer <span className="translate-y-[1px]">→</span>
                  </div>
                </div>
              </button>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-md">
            <button
              type="button"
              onClick={() => {
                onClearError();
                onModeChange('select');
              }}
              className="mb-6 text-sm text-[#1B2A4A]/50 dark:text-white/55 hover:text-[#0078D4] flex items-center gap-1 transition-colors"
              data-testid="button-back"
            >
              <span className="translate-y-[1px]">←</span> Back
            </button>

            <div className="rounded-3xl bg-white/80 dark:bg-white/[0.06] backdrop-blur-xl border border-gray-200/60 dark:border-white/[0.08] p-8 shadow-2xl shadow-black/[0.06] dark:shadow-black/40">
              <div className="text-center mb-8">
                <div
                  className={`w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center shadow-lg ${
                    mode.startsWith('borrower')
                      ? 'bg-gradient-to-br from-[#0078D4] to-[#005EA6] shadow-[#0078D4]/25'
                      : 'bg-gradient-to-br from-[#1B2A4A] to-[#1e1e22] shadow-[#1B2A4A]/25'
                  }`}
                >
                  <span className="text-white font-black text-xl">{mode.startsWith('borrower') ? 'B' : 'O'}</span>
                </div>
                <h2 className="text-xl font-bold text-[#1B2A4A] dark:text-white">Welcome Back</h2>
                <p className="text-sm text-[#1B2A4A]/50 dark:text-white/55 mt-1">
                  {mode.startsWith('borrower') ? 'Loan Applicant Portal' : 'Loan Officer Portal'}
                </p>
              </div>

              <form onSubmit={onSubmit} className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor="login-username" className="text-sm font-medium text-[#1B2A4A]/70 dark:text-white/70">
                    Username
                  </label>
                  <input
                    id="login-username"
                    type="text"
                    value={username}
                    onChange={(e) => onUsernameChange(e.target.value)}
                    placeholder="Enter username"
                    autoComplete="username"
                    className="w-full px-4 py-3 rounded-2xl border border-gray-200/60 dark:border-white/[0.10] bg-white/70 dark:bg-white/[0.03] text-[#1B2A4A] dark:text-white placeholder:text-[#1B2A4A]/35 dark:placeholder:text-white/35 outline-none focus:ring-2 focus:ring-[#0078D4]/30"
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="login-password" className="text-sm font-medium text-[#1B2A4A]/70 dark:text-white/70">
                    Password
                  </label>
                  <input
                    id="login-password"
                    type="password"
                    value={password}
                    onChange={(e) => onPasswordChange(e.target.value)}
                    placeholder="Enter password"
                    autoComplete="current-password"
                    className="w-full px-4 py-3 rounded-2xl border border-gray-200/60 dark:border-white/[0.10] bg-white/70 dark:bg-white/[0.03] text-[#1B2A4A] dark:text-white placeholder:text-[#1B2A4A]/35 dark:placeholder:text-white/35 outline-none focus:ring-2 focus:ring-[#0078D4]/30"
                  />
                </div>

                {loginError ? <div style={{ color: '#b91c1c', fontSize: '13px', fontWeight: 600 }}>{loginError}</div> : null}

                <button
                  type="submit"
                  className="w-full rounded-2xl bg-gradient-to-r from-[#0078D4] to-[#005EA6] px-4 py-3 text-sm font-extrabold text-white shadow-lg shadow-[#0078D4]/20"
                >
                  Sign In
                </button>

                <div className="pt-2 text-center text-[11px] text-[#1B2A4A]/35 dark:text-white/35">
                  {mode.startsWith('borrower') ? (
                    <>
                      Forgot password?{' '}
                      <button type="button" className="text-[#0078D4] font-semibold" onClick={() => onModeChange('borrower-forgot')}>
                        Reset
                      </button>
                      <div className="mt-2">
                        Don&apos;t have an account?{' '}
                        <button type="button" className="text-[#0078D4] font-semibold" onClick={() => onModeChange('borrower-register')}>
                          Create one
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      Forgot password?{' '}
                      <button type="button" className="text-[#0078D4] font-semibold" onClick={() => onModeChange('officer-forgot')}>
                        Reset
                      </button>
                      <div className="mt-2">
                        Don&apos;t have an account?{' '}
                        <button type="button" className="text-[#0078D4] font-semibold" onClick={() => onModeChange('officer-register')}>
                          Create one
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </form>
            </div>
          </div>
        )}
      </div>

      <footer className="relative z-10 text-center py-4">
        <p className="text-xs text-[#1B2A4A]/30 dark:text-white/55">Powered by KSquare Technologies</p>
      </footer>
    </div>
  );
}

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [role, setRole] = useState<'user' | 'admin'>('user');
  const [authMode, setAuthMode] = useState<LoginPageProps['mode']>('select');
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

  React.useEffect(() => {
    if (location.pathname !== '/login') return;
    const params = new URLSearchParams(location.search);
    const raw = params.get('mode');
    const next = (raw || '').trim();
    const allowed: LoginPageProps['mode'][] = [
      'select',
      'borrower-login',
      'officer-login',
      'borrower-register',
      'officer-register',
      'borrower-forgot',
      'officer-forgot',
    ];
    if (next && allowed.includes(next as LoginPageProps['mode'])) {
      if (authMode !== (next as LoginPageProps['mode'])) setAuthMode(next as LoginPageProps['mode']);
      return;
    }
    if (!next) {
      const adminRoutes = new Set([
        '/dashboard',
        '/pipeline',
        '/loan-products',
        '/officer-chat',
        '/synthetic-data',
        '/training',
        '/metrics',
        '/simulator',
        '/configuration',
      ]);
      if (fromPath && adminRoutes.has(fromPath) && authMode === 'select') {
        setAuthMode('officer-login');
        return;
      }
      return;
    }
    const adminRoutes = new Set([
      '/dashboard',
      '/pipeline',
      '/loan-products',
      '/officer-chat',
      '/synthetic-data',
      '/training',
      '/metrics',
      '/simulator',
      '/configuration',
    ]);
    if (adminRoutes.has(next) && authMode !== 'select') setAuthMode('select');
  }, [authMode, fromPath, location.pathname, location.search]);

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

    const normalizedUsername = username.trim();
    const normalizedPassword = password;

    if (authMode === 'select') {
      setLoginError('Choose Loan Applicant or Loan Officer to continue.');
      return;
    }

    if (authMode.endsWith('register') || authMode.endsWith('forgot')) {
      setLoginError('This workflow is not implemented yet in this build.');
      return;
    }

    if (authMode.startsWith('officer')) {
      const validOfficer =
        (normalizedUsername === 'officer' && normalizedPassword === 'Password123!') ||
        (normalizedUsername === 'admin' && normalizedPassword === 'admin123');
      if (!validOfficer) {
        setLoginError('Invalid credentials.');
        return;
      }
      setRole('admin');
      setIsLoggedIn(true);
      setLoginError('');
      navigate(resolvePostLoginPath('admin'), { replace: true });
      return;
    }

    if (authMode.startsWith('borrower')) {
      const validBorrower =
        (normalizedUsername === 'borrower' && normalizedPassword === 'Password123!') ||
        (normalizedUsername === 'demo' && normalizedPassword === 'demo123');
      if (!validBorrower) {
        setLoginError('Invalid credentials.');
        return;
      }
      setRole('user');
      setIsLoggedIn(true);
      setLoginError('');
      navigate(resolvePostLoginPath('user'), { replace: true });
      return;
    }

    setLoginError('Choose Loan Applicant or Loan Officer to continue.');
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setRole('user');
    setAuthMode('select');
    setUsername('');
    setPassword('');
    setLoginError('');
    navigate('/login', { replace: true });
  };

  const BorrowerHomePage = () => {
    const [phases, setPhases] = useState<V2Phase[]>([]);
    const [conversation, setConversation] = useState<V2Conversation | null>(null);
    const [visibleMessages, setVisibleMessages] = useState<V2ChatMessage[]>([]);
    const [resetSignal, setResetSignal] = useState(0);
    const [stickyCalculated, setStickyCalculated] = useState<Record<string, unknown> | null>(null);
    const [stickyIntentSummary, setStickyIntentSummary] = useState<Record<string, unknown> | null>(null);
    const routeLocation = useLocation();
    const [designOverlayOpacity, setDesignOverlayOpacity] = useState(0.5);
    const [designOverlayName, setDesignOverlayName] = useState('');
    const [metricsOpen, setMetricsOpen] = useState(false);

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
      const base =
        (import.meta.env.VITE_OVERLAY_DIR as string | undefined) ??
        '/Users/alberto/Documents/projects/ks-los/doc/01_execution/image';
      const p = `${base}/${name}`;
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

    const parseMeta = (raw: unknown): Record<string, unknown> | null => {
      if (!raw) return null;
      if (typeof raw === 'string') {
        try {
          return JSON.parse(raw) as Record<string, unknown>;
        } catch {
          return null;
        }
      }
      if (typeof raw === 'object') return raw as Record<string, unknown>;
      return null;
    };

    const latestCalculated = React.useMemo(() => {
      const msgs = visibleMessages.slice().reverse();
      for (const m of msgs) {
        if (m.role !== 'assistant') continue;
        const meta = parseMeta(m.metadata);
        const calc = meta?.calculatedMetrics ?? meta?.calculated_metrics;
        if (calc && typeof calc === 'object') {
          return calc as Record<string, unknown>;
        }
      }
      return null;
    }, [visibleMessages]);

    const latestIntentSummary = React.useMemo(() => {
      const msgs = visibleMessages.slice().reverse();
      for (const m of msgs) {
        if (m.role !== 'assistant') continue;
        const meta = parseMeta(m.metadata);
        const intent = meta?.intentAnalysis ?? meta?.intent_analysis;
        if (!intent || typeof intent !== 'object') continue;
        const summary = (intent as Record<string, unknown>).intentSummary;
        if (summary && typeof summary === 'object') {
          return summary as Record<string, unknown>;
        }
      }
      return null;
    }, [visibleMessages]);

    const metricsApplicationId = React.useMemo(() => {
      const fromConversation = (conversation as unknown as Record<string, unknown> | null)?.applicationId ?? (conversation as unknown as Record<string, unknown> | null)?.application_id;
      if (typeof fromConversation === 'string' && fromConversation.trim()) return fromConversation.trim();
      const msgs = visibleMessages.slice().reverse();
      for (const m of msgs) {
        if (m.role !== 'assistant') continue;
        const meta = parseMeta(m.metadata);
        const raw = meta?.application_id ?? meta?.applicationId;
        if (typeof raw === 'string' && raw.trim()) return raw.trim();
      }
      return null;
    }, [conversation, visibleMessages]);

    React.useEffect(() => {
      if (latestCalculated) setStickyCalculated(latestCalculated);
    }, [latestCalculated]);

    React.useEffect(() => {
      if (latestIntentSummary) setStickyIntentSummary(latestIntentSummary);
    }, [latestIntentSummary]);

    React.useEffect(() => {
      setStickyCalculated(null);
      setStickyIntentSummary(null);
    }, [resetSignal]);

    const approvalProbability = React.useMemo(() => {
      const raw = conversation?.approvalProbability as unknown;
      if (typeof raw === 'number') return raw;
      if (raw && typeof raw === 'object' && typeof (raw as { probability?: unknown }).probability === 'number') {
        return (raw as { probability: number }).probability;
      }

      const calc = latestCalculated as unknown;
      if (calc && typeof calc === 'object') {
        const c = calc as Record<string, unknown>;
        const fromCalc = c.approvalProbability ?? c.approval_probability;
        if (typeof fromCalc === 'number') {
          if (fromCalc >= 0 && fromCalc <= 1) return fromCalc;
          if (fromCalc > 1 && fromCalc <= 100) return fromCalc / 100;
        }
      }

      return null;
    }, [conversation?.approvalProbability, latestCalculated]);

    const nextConversationAngle = React.useMemo(() => {
      const fromConv = conversation?.nextConversationAngle;
      if (typeof fromConv === 'string' && fromConv.trim()) return fromConv.trim();
      const source = latestIntentSummary ?? stickyIntentSummary;
      const fromMsg = source?.nextConversationAngle;
      if (typeof fromMsg === 'string' && fromMsg.trim()) return fromMsg.trim();
      return null;
    }, [conversation?.nextConversationAngle, latestIntentSummary, stickyIntentSummary]);

    const seriousnessScore = React.useMemo(() => {
      const fromConv = conversation?.seriousnessScore ?? (conversation as unknown as Record<string, unknown> | null)?.seriousness_score;
      if (typeof fromConv === 'number') return fromConv;
      const source = latestIntentSummary ?? stickyIntentSummary;
      const fromMsg = source?.seriousnessScore ?? (source as unknown as Record<string, unknown> | null)?.seriousness_score;
      if (typeof fromMsg === 'number') return fromMsg;
      return null;
    }, [conversation, latestIntentSummary, stickyIntentSummary]);

    const fitScore = React.useMemo(() => {
      const fromConv = conversation?.fitScore ?? (conversation as unknown as Record<string, unknown> | null)?.fit_score;
      if (typeof fromConv === 'number') return fromConv;
      const source = latestIntentSummary ?? stickyIntentSummary;
      const fromMsg = source?.fitScore ?? (source as unknown as Record<string, unknown> | null)?.fit_score;
      if (typeof fromMsg === 'number') return fromMsg;
      return null;
    }, [conversation, latestIntentSummary, stickyIntentSummary]);

    const approvalTopBlockers = React.useMemo(() => {
      const raw = conversation?.approvalProbability as unknown;
      if (!raw || typeof raw !== 'object') return [];
      const items = (raw as { topBlockers?: unknown }).topBlockers;
      if (!Array.isArray(items)) return [];
      return items
        .filter((i) => i && typeof i === 'object' && typeof (i as { title?: unknown }).title === 'string')
        .slice(0, 3) as Array<Record<string, unknown>>;
    }, [conversation?.approvalProbability]);

    const approvalTopActions = React.useMemo(() => {
      const raw = conversation?.approvalProbability as unknown;
      if (!raw || typeof raw !== 'object') return [];
      const items = (raw as { topActions?: unknown }).topActions;
      if (!Array.isArray(items)) return [];
      return items
        .filter((i) => i && typeof i === 'object' && typeof (i as { title?: unknown }).title === 'string')
        .slice(0, 3) as Array<Record<string, unknown>>;
    }, [conversation?.approvalProbability]);

    const stpTier = React.useMemo(() => {
      const source = latestCalculated ?? stickyCalculated;
      const v = source?.stpTier ?? source?.stp_tier;
      return typeof v === 'string' ? v : null;
    }, [latestCalculated, stickyCalculated]);

    const riskGrade = React.useMemo(() => {
      const source = latestCalculated ?? stickyCalculated;
      const v = source?.riskGrade ?? source?.risk_grade;
      return typeof v === 'string' ? v : null;
    }, [latestCalculated, stickyCalculated]);

    const foir = React.useMemo(() => {
      const source = latestCalculated ?? stickyCalculated;
      const v = source?.foir;
      if (typeof v !== 'number') return null;
      if (v <= 0) return null;
      return v;
    }, [latestCalculated, stickyCalculated]);

    const recommendedProducts = React.useMemo(() => {
      const raw =
        (conversation as unknown as Record<string, unknown> | null)?.recommendedProducts ??
        (latestIntentSummary as unknown as Record<string, unknown> | null)?.recommendedProducts ??
        (stickyIntentSummary as unknown as Record<string, unknown> | null)?.recommendedProducts;
      if (!Array.isArray(raw)) return [];

      const formatRate = (v: unknown) => {
        if (typeof v === 'number' && Number.isFinite(v) && v > 0) return `${v.toFixed(2)}%`;
        if (typeof v !== 'string') return '';
        const t = v.trim();
        return t;
      };

      const formatTenure = (v: unknown) => {
        if (typeof v === 'number' && Number.isFinite(v) && v > 0) return `${v} yrs`;
        if (typeof v !== 'string') return '';
        const t = v.trim();
        return t;
      };

      const formatEmi = (v: unknown) => {
        if (typeof v === 'number' && Number.isFinite(v) && v > 0) return new Intl.NumberFormat('en-US').format(v);
        if (typeof v !== 'string') return '';
        const t = v.trim();
        return t;
      };

      return raw
        .map((item, idx) => {
          const r = item && typeof item === 'object' ? (item as Record<string, unknown>) : null;
          if (!r) return null;
          const nameRaw = r.name ?? r.title ?? r.type ?? r.category;
          const name = typeof nameRaw === 'string' && nameRaw.trim() ? nameRaw.trim() : `Recommendation ${idx + 1}`;
          const recommendation = typeof r.recommendation === 'string' ? r.recommendation : typeof r.summary === 'string' ? r.summary : '';

          const rate =
            r.estimatedRate ??
            r.estimated_rate ??
            r.interest_rate ??
            r.baseInterestRate ??
            r.base_interest_rate ??
            r.rate;
          const tenure = r.tenure ?? r.tenure_years ?? r.tenureYears ?? r.term;
          const emi = r.estimatedEmi ?? r.estimated_emi ?? r.monthly_emi ?? r.emi;

          const estimatedRate = formatRate(rate);
          const tenureLabel = formatTenure(tenure);
          const estimatedEmi = formatEmi(emi);

          return {
            name,
            recommendation,
            estimatedRate,
            tenure: tenureLabel,
            estimatedEmi,
          };
        })
        .filter((x): x is NonNullable<typeof x> => x !== null);
    }, [conversation, latestIntentSummary, stickyIntentSummary]);

    const handleNewChat = () => {
      setConversation(null);
      setPhases([]);
      setResetSignal((v) => v + 1);
      setStickyCalculated(null);
      setStickyIntentSummary(null);
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

        <header className="glass-header relative z-30 shrink-0 border-b border-slate-200/40 dark:border-white/[0.04] px-6 py-4 flex items-center justify-between bg-white/70 dark:bg-[#141414]/80 backdrop-blur-xl">
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
              onClick={() => setMetricsOpen(true)}
              className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm"
              data-testid="button-show-metrics"
            >
              Show metrics
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

        <Dialog.Root open={metricsOpen} onOpenChange={setMetricsOpen}>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/45 z-[90]" />
            <Dialog.Content className="fixed left-1/2 top-1/2 w-[96vw] max-w-6xl -translate-x-1/2 -translate-y-1/2 rounded-3xl border border-slate-200/60 dark:border-white/[0.08] bg-white dark:bg-[#111113] p-4 shadow-2xl max-h-[92vh] overflow-y-auto z-[100]">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <Dialog.Title className="text-sm font-extrabold text-slate-900 dark:text-white truncate">Metrics</Dialog.Title>
                  <Dialog.Description className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                    Application and portfolio metrics for this session.
                  </Dialog.Description>
                </div>
                <Dialog.Close asChild>
                  <button type="button" className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm">
                    Close
                  </button>
                </Dialog.Close>
              </div>

              <div className="mt-4">
                <MetricsDashboard applicationId={metricsApplicationId ?? undefined} isAdmin={false} autoRefresh />
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>

        {role === 'user' ? (
          <BorrowerJourneyTracker currentPhaseName={activePhases[currentIndex]?.name || null} messages={visibleMessages} />
        ) : activePhases.length > 0 && conversation?.currentPhaseId ? (
          <div data-testid="phase-progress-tracker" className="glass-header relative z-30 shrink-0 border-b border-slate-200/40 dark:border-white/[0.04] bg-white/50 dark:bg-white/[0.02] backdrop-blur-sm">
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
                        <Link
                          to={`/phases/${p.id}`}
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
                        </Link>
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

        <div className="flex-1 min-h-0 relative z-10 overflow-hidden">
          <div className="h-full max-w-6xl mx-auto px-4 md:px-6 py-6 flex flex-col">
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 flex-1 min-h-0">
              <div className="min-h-0 rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-xl shadow-black/[0.04] dark:shadow-black/40 overflow-hidden flex flex-col">
                <ChatInterface
                  onConversationUpdated={setConversation}
                  onPhasesUpdated={setPhases}
                  onMessagesUpdated={setVisibleMessages}
                  resetSignal={resetSignal}
                />
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
                      {approvalTopBlockers.length === 0 && approvalTopActions.length === 0 ? null : (
                        <div className="mt-3 grid grid-cols-1 gap-3" data-testid="approval-navigator">
                          {approvalTopBlockers.length === 0 ? null : (
                            <div data-testid="approval-top-blockers">
                              <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Top blockers</div>
                              <div className="mt-1 grid gap-1.5">
                                {approvalTopBlockers.map((b, idx) => {
                                  const title = typeof b.title === 'string' ? b.title : '';
                                  const detail = typeof b.detail === 'string' ? b.detail : '';
                                  return (
                                    <div key={`${title}-${idx}`} className="text-xs text-slate-700 dark:text-slate-200" data-testid={`approval-blocker-${idx}`}>
                                      <div className="font-semibold">{title}</div>
                                      {detail ? <div className="text-[11px] text-slate-500 dark:text-slate-400">{detail}</div> : null}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                          {approvalTopActions.length === 0 ? null : (
                            <div data-testid="approval-top-actions">
                              <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Next actions</div>
                              <div className="mt-1 grid gap-1.5">
                                {approvalTopActions.map((a, idx) => {
                                  const title = typeof a.title === 'string' ? a.title : '';
                                  const detail = typeof a.detail === 'string' ? a.detail : '';
                                  return (
                                    <div key={`${title}-${idx}`} className="text-xs text-slate-700 dark:text-slate-200" data-testid={`approval-action-${idx}`}>
                                      <div className="font-semibold">{title}</div>
                                      {detail ? <div className="text-[11px] text-slate-500 dark:text-slate-400">{detail}</div> : null}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">STP Tier</div>
                        <div className="mt-1 text-xl font-black tracking-tight text-slate-900 dark:text-white" data-testid="stp-tier">
                          {stpTier ? stpTier : '—'}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Risk Grade</div>
                        <div className="mt-1 text-xl font-black tracking-tight text-slate-900 dark:text-white" data-testid="risk-grade">
                          {riskGrade ? riskGrade : '—'}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">FOIR</div>
                        <div className="mt-1 text-xl font-black tracking-tight text-slate-900 dark:text-white" data-testid="foir">
                          {foir === null ? '—' : `${foir.toFixed(1)}%`}
                        </div>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                      <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Next Conversation Angle</div>
                      <div className="mt-1 text-sm font-semibold text-slate-800 dark:text-slate-200" data-testid="next-conversation-angle">
                        {nextConversationAngle || '—'}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Seriousness Score</div>
                        <div className="mt-1 text-xl font-black tracking-tight text-slate-900 dark:text-white" data-testid="seriousness-score">
                          {seriousnessScore === null ? '—' : seriousnessScore}
                        </div>
                      </div>

                      <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-3">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Fit Score</div>
                        <div className="mt-1 text-xl font-black tracking-tight text-slate-900 dark:text-white" data-testid="fit-score">
                          {fitScore === null ? '—' : fitScore}
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

                  <div data-testid="recommended-products" className="mt-4 grid gap-3">
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
    const officerHeaders = React.useMemo<Record<string, string>>(() => ({ Authorization: 'Bearer loan-officer-access' }), []);
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

    const approvalTopBlockers = React.useMemo(() => {
      const raw = selected?.approvalProbability as unknown;
      if (!raw || typeof raw !== 'object') return [];
      const items = (raw as { topBlockers?: unknown }).topBlockers;
      if (!Array.isArray(items)) return [];
      return items
        .filter((i) => i && typeof i === 'object' && typeof (i as { title?: unknown }).title === 'string')
        .slice(0, 3) as Array<Record<string, unknown>>;
    }, [selected?.approvalProbability]);

    const approvalTopActions = React.useMemo(() => {
      const raw = selected?.approvalProbability as unknown;
      if (!raw || typeof raw !== 'object') return [];
      const items = (raw as { topActions?: unknown }).topActions;
      if (!Array.isArray(items)) return [];
      return items
        .filter((i) => i && typeof i === 'object' && typeof (i as { title?: unknown }).title === 'string')
        .slice(0, 3) as Array<Record<string, unknown>>;
    }, [selected?.approvalProbability]);

    const recommendedProducts = React.useMemo(() => {
      const raw = (selected as unknown as Record<string, unknown> | null)?.recommendedProducts;
      if (!Array.isArray(raw)) return [];

      const formatRate = (v: unknown) => {
        if (typeof v === 'number' && Number.isFinite(v) && v > 0) return `${v.toFixed(2)}%`;
        if (typeof v !== 'string') return '';
        return v.trim();
      };

      return raw
        .map((item, idx) => {
          const r = item && typeof item === 'object' ? (item as Record<string, unknown>) : null;
          if (!r) return null;
          const nameRaw = r.name ?? r.title ?? r.type ?? r.category;
          const name = typeof nameRaw === 'string' && nameRaw.trim() ? nameRaw.trim() : `Recommendation ${idx + 1}`;
          const rate =
            r.estimatedRate ??
            r.estimated_rate ??
            r.interest_rate ??
            r.baseInterestRate ??
            r.base_interest_rate ??
            r.rate;
          return { ...r, name, estimatedRate: formatRate(rate) };
        })
        .filter((x): x is NonNullable<typeof x> => x !== null);
    }, [selected]);

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
                      {approvalTopBlockers.length === 0 && approvalTopActions.length === 0 ? null : (
                        <div style={{ marginTop: '10px', display: 'grid', gap: '10px' }} data-testid="approval-navigator-officer">
                          {approvalTopBlockers.length === 0 ? null : (
                            <div data-testid="approval-top-blockers-officer">
                              <div style={{ fontSize: '0.8rem', fontWeight: 900, color: '#374151', marginBottom: '6px' }}>Top blockers</div>
                              <div style={{ display: 'grid', gap: '8px' }}>
                                {approvalTopBlockers.map((b, idx) => {
                                  const title = typeof b.title === 'string' ? b.title : '';
                                  const detail = typeof b.detail === 'string' ? b.detail : '';
                                  return (
                                    <div key={`${title}-${idx}`} data-testid={`approval-blocker-officer-${idx}`}>
                                      <div style={{ fontWeight: 800, color: '#111827', fontSize: '0.9rem' }}>{title}</div>
                                      {detail ? <div style={{ color: '#6b7280', fontSize: '0.85rem', marginTop: '2px' }}>{detail}</div> : null}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                          {approvalTopActions.length === 0 ? null : (
                            <div data-testid="approval-top-actions-officer">
                              <div style={{ fontSize: '0.8rem', fontWeight: 900, color: '#374151', marginBottom: '6px' }}>Next actions</div>
                              <div style={{ display: 'grid', gap: '8px' }}>
                                {approvalTopActions.map((a, idx) => {
                                  const title = typeof a.title === 'string' ? a.title : '';
                                  const detail = typeof a.detail === 'string' ? a.detail : '';
                                  return (
                                    <div key={`${title}-${idx}`} data-testid={`approval-action-officer-${idx}`}>
                                      <div style={{ fontWeight: 800, color: '#111827', fontSize: '0.9rem' }}>{title}</div>
                                      {detail ? <div style={{ color: '#6b7280', fontSize: '0.85rem', marginTop: '2px' }}>{detail}</div> : null}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
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
    const officerHeaders = React.useMemo<Record<string, string>>(() => ({ Authorization: 'Bearer loan-officer-access' }), []);
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
        underwritingMemo?: unknown;
      }>
    >([]);
    const [selectedId, setSelectedId] = useState<string>('');
    const selected = React.useMemo(() => loans.find((l) => l.id === selectedId) || null, [loans, selectedId]);
    const [memoBusy, setMemoBusy] = useState(false);
    const [docUploadBusy, setDocUploadBusy] = useState<Record<string, boolean>>({});
    const [docUploadError, setDocUploadError] = useState<Record<string, string>>({});
    const [signatureBusy, setSignatureBusy] = useState(false);
    const sigCanvasRef = React.useRef<HTMLCanvasElement | null>(null);
    const [sigDrawing, setSigDrawing] = useState(false);
    const [sigHasInk, setSigHasInk] = useState(false);
    type V2LoanDocument = {
      id: string;
      loanId: string;
      category?: string | null;
      documentType?: string | null;
      status?: string | null;
      reviewNote?: string | null;
      originalName?: string | null;
      fileName?: string | null;
      uploadedAt?: string | null;
      reviewedAt?: string | null;
    };
    const [v2Docs, setV2Docs] = useState<V2LoanDocument[]>([]);
    const [v2DocsLoading, setV2DocsLoading] = useState(false);
    const [v2DocsError, setV2DocsError] = useState('');
    const [v2ReviewBusy, setV2ReviewBusy] = useState<Record<string, boolean>>({});
    const [v2ReviewNoteDraft, setV2ReviewNoteDraft] = useState<Record<string, string>>({});

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

    const refreshV2Docs = React.useCallback(
      async (loanId: string) => {
        setV2DocsError('');
        setV2DocsLoading(true);
        try {
          const res = await fetch(`http://localhost:8000/api/documents/loan/${loanId}`, { headers: officerHeaders });
          if (!res.ok) {
            const t = await res.text();
            setV2DocsError(t || `Failed to load documents (${res.status})`);
            setV2Docs([]);
            return;
          }
          setV2Docs((await res.json()) as V2LoanDocument[]);
        } catch (e: unknown) {
          setV2DocsError(e instanceof Error ? e.message : 'Failed to load documents');
          setV2Docs([]);
        } finally {
          setV2DocsLoading(false);
        }
      },
      [officerHeaders],
    );

    React.useEffect(() => {
      if (!selected?.id) {
        setV2Docs([]);
        return;
      }
      void refreshV2Docs(selected.id);
    }, [selected?.id, refreshV2Docs]);

    const reviewV2Doc = async (docId: string, status: string) => {
      setV2ReviewBusy((prev) => ({ ...prev, [docId]: true }));
      try {
        const res = await fetch(`http://localhost:8000/api/documents/${docId}/review`, {
          method: 'PATCH',
          headers: { ...officerHeaders, 'content-type': 'application/json' },
          body: JSON.stringify({ status, reviewNote: v2ReviewNoteDraft[docId] || '' }),
        });
        if (!res.ok) return;
        const updated = (await res.json()) as V2LoanDocument;
        setV2Docs((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
      } finally {
        setV2ReviewBusy((prev) => ({ ...prev, [docId]: false }));
      }
    };

    const downloadV2Doc = async (docId: string, filename: string) => {
      try {
        const res = await fetch(`http://localhost:8000/api/documents/${docId}/download`, { headers: officerHeaders });
        if (!res.ok) return;
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || 'document';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      } catch (e) {
        console.error(e);
      }
    };

    const phasesById = React.useMemo(() => {
      const out: Record<string, (typeof phases)[number]> = {};
      for (const p of phases) out[p.id] = p;
      return out;
    }, [phases]);

    const activePhaseIds = React.useMemo(() => {
      const ids = new Set<string>();
      for (const p of phases) {
        if (p.isActive !== false) ids.add(p.id);
      }
      return ids;
    }, [phases]);

    const orderedPhaseIds = React.useMemo(() => {
      return [...phases]
        .filter((p) => p.isActive !== false)
        .sort((a, b) => (a.sortOrder || 0) - (b.sortOrder || 0))
        .map((p) => p.id);
    }, [phases]);

    const grouped = React.useMemo(() => {
      const groups: Record<string, typeof loans> = { unassigned: [] };
      for (const pid of orderedPhaseIds) groups[pid] = [];
      for (const l of loans) {
        const pid = l.currentPhaseId || '';
        if (pid && activePhaseIds.has(pid)) {
          if (!groups[pid]) groups[pid] = [];
          groups[pid].push(l);
        } else {
          groups.unassigned.push(l);
        }
      }
      return groups;
    }, [loans, orderedPhaseIds, activePhaseIds]);

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
          const uploadRaw = item?.upload;
          const upload = uploadRaw && typeof uploadRaw === 'object' ? (uploadRaw as Record<string, unknown>) : null;
          const uploadedFileName = typeof upload?.fileName === 'string' ? upload.fileName : '';
          const uploadedAt = typeof upload?.uploadedAt === 'string' ? upload.uploadedAt : '';
          const extractedPreview = typeof upload?.extractedPreview === 'string' ? upload.extractedPreview : '';
          return { name, status: status as DocumentStatus, uploadedFileName, uploadedAt, extractedPreview };
        })
        .filter((x) => Boolean(x.name));
    }, [selected?.documentChecklist]);

    const underwritingMemo = React.useMemo(() => {
      const raw = selected?.underwritingMemo as unknown;
      if (!raw || typeof raw !== 'object') return null;
      const memo = raw as Record<string, unknown>;
      const sectionsRaw = memo.sections;
      const sections = Array.isArray(sectionsRaw)
        ? sectionsRaw
            .map((s) => (s && typeof s === 'object' ? (s as Record<string, unknown>) : null))
            .filter(Boolean)
            .map((s) => {
              const title = typeof s?.title === 'string' ? s.title : '';
              const bullets = Array.isArray(s?.bullets) ? s.bullets.filter((b): b is string => typeof b === 'string') : [];
              return { title, bullets };
            })
            .filter((s) => Boolean(s.title))
        : [];
      const flags = Array.isArray(memo.flags) ? memo.flags.filter((f): f is string => typeof f === 'string') : [];
      const nextActions = Array.isArray(memo.nextActions) ? memo.nextActions.filter((a): a is string => typeof a === 'string') : [];
      const disclaimer = typeof memo.disclaimer === 'string' ? memo.disclaimer : '';
      const generatedAt = typeof memo.generatedAt === 'string' ? memo.generatedAt : '';
      return { sections, flags, nextActions, disclaimer, generatedAt };
    }, [selected?.underwritingMemo]);

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

    const uploadDoc = async (docName: string, file: File) => {
      if (!selected) return;
      setDocUploadBusy((prev) => ({ ...prev, [docName]: true }));
      setDocUploadError((prev) => ({ ...prev, [docName]: '' }));
      try {
        const fd = new FormData();
        fd.append('name', docName);
        fd.append('file', file);
        const res = await fetch(`http://localhost:8000/api/loans/${selected.id}/documents/upload`, {
          method: 'POST',
          headers: officerHeaders,
          body: fd,
        });
        if (!res.ok) {
          const t = await res.text();
          setDocUploadError((prev) => ({ ...prev, [docName]: t || `Upload failed (${res.status})` }));
          return;
        }
        const updated = (await res.json()) as (typeof loans)[number];
        setLoans((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      } finally {
        setDocUploadBusy((prev) => ({ ...prev, [docName]: false }));
      }
    };

    const uploadSignature = async (blob: Blob) => {
      if (!selected) return;
      setSignatureBusy(true);
      try {
        const fd = new FormData();
        fd.append('file', new File([blob], 'signature.png', { type: 'image/png' }));
        const res = await fetch(`http://localhost:8000/api/loans/${selected.id}/signature`, {
          method: 'POST',
          headers: officerHeaders,
          body: fd,
        });
        if (!res.ok) return;
        const updated = (await res.json()) as (typeof loans)[number];
        setLoans((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      } finally {
        setSignatureBusy(false);
      }
    };

    const generateMemo = async () => {
      if (!selected) return;
      setMemoBusy(true);
      try {
        const res = await fetch(`http://localhost:8000/api/loans/${selected.id}/underwriting-memo`, {
          method: 'POST',
          headers: { ...officerHeaders, 'content-type': 'application/json' },
        });
        if (!res.ok) return;
        const updated = (await res.json()) as (typeof loans)[number];
        setLoans((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      } finally {
        setMemoBusy(false);
      }
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
                    <button
                      type="button"
                      onClick={() => navigate(`/phases/${pid}`)}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        padding: '10px 14px',
                        background: '#f9fafb',
                        border: 'none',
                        borderBottom: '1px solid #f3f4f6',
                        fontWeight: 900,
                        cursor: 'pointer',
                      }}
                      data-testid={`pipeline-phase-header-${pid}`}
                    >
                      {phasesById[pid]?.name || 'Phase'} ({grouped[pid]?.length || 0})
                    </button>
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
                        {checklistItems.map((i, idx) => (
                          <div
                            key={i.name}
                            style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: '10px', alignItems: 'start' }}
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
                              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                <label htmlFor={`file-doc-${selected.id}-${idx}`}>
                                  <button
                                    type="button"
                                    disabled={Boolean(docUploadBusy[i.name])}
                                    style={{
                                      border: '1px solid #e5e7eb',
                                      borderRadius: '10px',
                                      padding: '6px 10px',
                                      backgroundColor: docUploadBusy[i.name] ? '#f3f4f6' : '#ffffff',
                                      cursor: docUploadBusy[i.name] ? 'not-allowed' : 'pointer',
                                      fontWeight: 800,
                                    }}
                                    data-testid={`button-doc-upload-${idx}`}
                                  >
                                    Upload
                                  </button>
                                </label>
                                <input
                                  id={`file-doc-${selected.id}-${idx}`}
                                  type="file"
                                  style={{ display: 'none' }}
                                  onChange={(e) => {
                                    const f = e.target.files?.[0];
                                    e.target.value = '';
                                    if (f) void uploadDoc(i.name, f);
                                  }}
                                  data-testid={`input-doc-upload-${idx}`}
                                />
                                {docUploadBusy[i.name] ? <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>Extracting…</div> : null}
                              </div>
                              <div style={{ fontSize: '0.85rem', color: '#6b7280' }} data-testid={`doc-status-${i.name}`}>
                                {i.status}
                              </div>
                              {docUploadError[i.name] ? <div style={{ fontSize: '0.85rem', color: '#b91c1c' }}>{docUploadError[i.name]}</div> : null}
                              {i.uploadedFileName ? (
                                <div style={{ fontSize: '0.85rem', color: '#111827' }} data-testid={`doc-uploaded-file-${idx}`}>
                                  File: {i.uploadedFileName}
                                </div>
                              ) : null}
                              {i.uploadedAt ? (
                                <div style={{ fontSize: '0.85rem', color: '#6b7280' }} data-testid={`doc-uploaded-at-${idx}`}>
                                  Uploaded: {i.uploadedAt}
                                </div>
                              ) : null}
                              {i.extractedPreview ? (
                                <div
                                  style={{
                                    fontSize: '0.85rem',
                                    color: '#111827',
                                    backgroundColor: '#ffffff',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '10px',
                                    padding: '8px 10px',
                                    whiteSpace: 'pre-wrap',
                                    maxHeight: '160px',
                                    overflowY: 'auto',
                                  }}
                                  data-testid={`doc-extracted-preview-${idx}`}
                                >
                                  {i.extractedPreview}
                                </div>
                              ) : null}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div style={{ border: '1px solid #f3f4f6', borderRadius: '10px', padding: '12px', backgroundColor: '#fafafa' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 900, color: '#111827', marginBottom: '10px' }} data-testid="text-v2-documents-title">
                      Documents (UI2)
                    </div>
                    {v2DocsLoading ? <div style={{ color: '#6b7280' }}>Loading…</div> : null}
                    {v2DocsError ? <div style={{ color: '#b91c1c', fontWeight: 700 }}>{v2DocsError}</div> : null}
                    {!v2DocsLoading && !v2DocsError && v2Docs.length === 0 ? <div style={{ color: '#6b7280' }}>No uploaded documents.</div> : null}
                    {v2Docs.length > 0 ? (
                      <div style={{ display: 'grid', gap: '10px' }}>
                        {v2Docs.map((d) => {
                          const fileLabel = d.originalName || d.fileName || 'document';
                          const status = d.status || 'uploaded';
                          return (
                            <div key={d.id} style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px', background: '#ffffff' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', gap: '10px' }}>
                                <div style={{ minWidth: 0 }}>
                                  <div style={{ fontWeight: 900, color: '#111827', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {fileLabel}
                                  </div>
                                  <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '4px' }}>
                                    {d.category || '—'} · {d.documentType || '—'} · status: {status}
                                  </div>
                                </div>
                                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                                  <button
                                    type="button"
                                    onClick={() => void downloadV2Doc(d.id, fileLabel)}
                                    style={{ border: 'none', background: 'transparent', padding: 0, color: '#2563eb', fontWeight: 800, cursor: 'pointer' }}
                                    data-testid={`button-v2-doc-download-${d.id}`}
                                  >
                                    Download
                                  </button>
                                </div>
                              </div>

                              <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr 120px', gap: '10px', marginTop: '10px', alignItems: 'center' }}>
                                <select
                                  value={status}
                                  onChange={(e) => setV2Docs((prev) => prev.map((x) => (x.id === d.id ? { ...x, status: e.target.value } : x)))}
                                  disabled={Boolean(v2ReviewBusy[d.id])}
                                  style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid #e5e7eb', backgroundColor: '#ffffff' }}
                                  data-testid={`select-v2-doc-status-${d.id}`}
                                >
                                  <option value="uploaded">uploaded</option>
                                  <option value="approved">approved</option>
                                  <option value="rejected">rejected</option>
                                  <option value="needs_reupload">needs_reupload</option>
                                </select>
                                <input
                                  value={v2ReviewNoteDraft[d.id] ?? d.reviewNote ?? ''}
                                  onChange={(e) => setV2ReviewNoteDraft((prev) => ({ ...prev, [d.id]: e.target.value }))}
                                  placeholder="Review note (optional)"
                                  style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid #e5e7eb' }}
                                  data-testid={`input-v2-doc-review-note-${d.id}`}
                                />
                                <button
                                  type="button"
                                  onClick={() => void reviewV2Doc(d.id, (v2Docs.find((x) => x.id === d.id)?.status as string) || status)}
                                  disabled={Boolean(v2ReviewBusy[d.id])}
                                  style={{
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '10px',
                                    padding: '8px 10px',
                                    backgroundColor: v2ReviewBusy[d.id] ? '#f3f4f6' : '#ffffff',
                                    cursor: v2ReviewBusy[d.id] ? 'not-allowed' : 'pointer',
                                    fontWeight: 900,
                                  }}
                                  data-testid={`button-v2-doc-review-${d.id}`}
                                >
                                  Save
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : null}
                  </div>

                  <div style={{ border: '1px solid #f3f4f6', borderRadius: '10px', padding: '12px', backgroundColor: '#fafafa' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 900, color: '#111827' }} data-testid="text-signature-title">
                        Signature
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          type="button"
                          onClick={() => {
                            const c = sigCanvasRef.current;
                            if (!c) return;
                            const ctx = c.getContext('2d');
                            if (!ctx) return;
                            ctx.clearRect(0, 0, c.width, c.height);
                            setSigHasInk(false);
                          }}
                          style={{
                            border: '1px solid #e5e7eb',
                            borderRadius: '10px',
                            padding: '8px 10px',
                            backgroundColor: '#ffffff',
                            cursor: 'pointer',
                            fontWeight: 800,
                          }}
                          data-testid="button-signature-clear"
                        >
                          Clear
                        </button>
                        <button
                          type="button"
                          disabled={!sigHasInk || signatureBusy}
                          onClick={() => {
                            const c = sigCanvasRef.current;
                            if (!c) return;
                            c.toBlob((blob) => {
                              if (!blob) return;
                              void uploadSignature(blob);
                            }, 'image/png');
                          }}
                          style={{
                            border: '1px solid #e5e7eb',
                            borderRadius: '10px',
                            padding: '8px 10px',
                            backgroundColor: !sigHasInk || signatureBusy ? '#f3f4f6' : '#ffffff',
                            cursor: !sigHasInk || signatureBusy ? 'not-allowed' : 'pointer',
                            fontWeight: 800,
                          }}
                          data-testid="button-signature-save"
                        >
                          Save
                        </button>
                      </div>
                    </div>
                    <div style={{ marginTop: '10px' }}>
                      <canvas
                        ref={sigCanvasRef}
                        width={520}
                        height={160}
                        style={{ width: '100%', height: '160px', backgroundColor: '#ffffff', border: '1px solid #e5e7eb', borderRadius: '10px' }}
                        onMouseDown={(e) => {
                          const c = sigCanvasRef.current;
                          if (!c) return;
                          const rect = c.getBoundingClientRect();
                          const ctx = c.getContext('2d');
                          if (!ctx) return;
                          ctx.lineWidth = 2;
                          ctx.lineCap = 'round';
                          ctx.strokeStyle = '#111827';
                          ctx.beginPath();
                          ctx.moveTo(((e.clientX - rect.left) / rect.width) * c.width, ((e.clientY - rect.top) / rect.height) * c.height);
                          setSigDrawing(true);
                          setSigHasInk(true);
                        }}
                        onMouseMove={(e) => {
                          if (!sigDrawing) return;
                          const c = sigCanvasRef.current;
                          if (!c) return;
                          const rect = c.getBoundingClientRect();
                          const ctx = c.getContext('2d');
                          if (!ctx) return;
                          ctx.lineTo(((e.clientX - rect.left) / rect.width) * c.width, ((e.clientY - rect.top) / rect.height) * c.height);
                          ctx.stroke();
                        }}
                        onMouseUp={() => setSigDrawing(false)}
                        onMouseLeave={() => setSigDrawing(false)}
                        data-testid="canvas-signature"
                      />
                    </div>
                    {signatureBusy ? <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '8px' }}>Uploading…</div> : null}
                  </div>

                  <div style={{ border: '1px solid #f3f4f6', borderRadius: '10px', padding: '12px', backgroundColor: '#fafafa' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 900, color: '#111827' }} data-testid="text-underwriting-memo-title">
                        Underwriting Memo
                      </div>
                      <button
                        type="button"
                        onClick={() => void generateMemo()}
                        disabled={memoBusy}
                        style={{
                          border: '1px solid #e5e7eb',
                          borderRadius: '10px',
                          padding: '8px 10px',
                          backgroundColor: memoBusy ? '#f3f4f6' : '#ffffff',
                          cursor: memoBusy ? 'not-allowed' : 'pointer',
                          fontWeight: 800,
                        }}
                        data-testid="button-generate-underwriting-memo"
                      >
                        {underwritingMemo ? 'Regenerate' : 'Generate'}
                      </button>
                    </div>

                    {!underwritingMemo ? (
                      <div style={{ color: '#6b7280', marginTop: '10px' }}>No memo generated yet.</div>
                    ) : (
                      <div style={{ display: 'grid', gap: '12px', marginTop: '10px' }} data-testid="underwriting-memo">
                        {underwritingMemo.generatedAt ? (
                          <div style={{ fontSize: '0.85rem', color: '#6b7280' }} data-testid="underwriting-memo-generated-at">
                            Generated: {underwritingMemo.generatedAt}
                          </div>
                        ) : null}
                        {underwritingMemo.flags.length > 0 ? (
                          <div style={{ display: 'grid', gap: '6px' }} data-testid="underwriting-memo-flags">
                            <div style={{ fontSize: '0.8rem', fontWeight: 900, color: '#111827' }}>Flags</div>
                            <ul style={{ margin: 0, paddingLeft: '18px', color: '#111827' }}>
                              {underwritingMemo.flags.map((f, idx) => (
                                <li key={`${f}-${idx}`} data-testid={`underwriting-memo-flag-${idx}`}>
                                  {f}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {underwritingMemo.nextActions.length > 0 ? (
                          <div style={{ display: 'grid', gap: '6px' }} data-testid="underwriting-memo-next-actions">
                            <div style={{ fontSize: '0.8rem', fontWeight: 900, color: '#111827' }}>Next Actions</div>
                            <ul style={{ margin: 0, paddingLeft: '18px', color: '#111827' }}>
                              {underwritingMemo.nextActions.map((a, idx) => (
                                <li key={`${a}-${idx}`} data-testid={`underwriting-memo-next-action-${idx}`}>
                                  {a}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {underwritingMemo.sections.map((s, idx) => (
                          <div key={`${s.title}-${idx}`} style={{ display: 'grid', gap: '6px' }} data-testid={`underwriting-memo-section-${idx}`}>
                            <div style={{ fontSize: '0.8rem', fontWeight: 900, color: '#111827' }}>{s.title}</div>
                            {s.bullets.length === 0 ? null : (
                              <ul style={{ margin: 0, paddingLeft: '18px', color: '#111827' }}>
                                {s.bullets.map((b, j) => (
                                  <li key={`${b}-${j}`} data-testid={`underwriting-memo-section-${idx}-bullet-${j}`}>
                                    {b}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                        {underwritingMemo.disclaimer ? (
                          <div style={{ fontSize: '0.85rem', color: '#6b7280' }} data-testid="underwriting-memo-disclaimer">
                            {underwritingMemo.disclaimer}
                          </div>
                        ) : null}
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
          headers: { Authorization: 'Bearer loan-officer-access' },
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
          headers: { 'content-type': 'application/json', Authorization: 'Bearer loan-officer-access' },
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
          headers: { 'content-type': 'application/json', Authorization: 'Bearer loan-officer-access' },
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

    const officerHeaders = React.useMemo<Record<string, string>>(() => ({ Authorization: 'Bearer loan-officer-access' }), []);

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
      const path = location.pathname || '/';
      const officerOnly =
        path === '/dashboard' ||
        path === '/pipeline' ||
        path === '/loan-products' ||
        path === '/officer-chat' ||
        path === '/synthetic-data' ||
        path === '/training' ||
        path === '/metrics' ||
        path === '/simulator' ||
        path === '/configuration' ||
        path.startsWith('/phases/');
      const mode = officerOnly ? 'officer-login' : 'borrower-login';
      return <Navigate to={`/login?mode=${encodeURIComponent(mode)}`} replace state={{ from: location }} />;
    }
    return children;
  };

  const RequireRole: React.FC<{ allow: 'admin' | 'user'; children: React.ReactElement }> = ({ allow, children }) => {
    if (role !== allow) {
      return <Navigate to={role === 'admin' ? '/dashboard' : '/'} replace />;
    }
    return children;
  };

  type PhaseKnowledge = {
    timeline: string;
    summary: string;
    activities: string[];
    documents: string[];
    stakeholders: string[];
    bottlenecks: string[];
  };

  type PhaseDetailResponse = {
    phase: V2Phase;
    knowledge: PhaseKnowledge;
    metrics: { loanCount: number; conversationCount: number };
  };

  const PhaseDetailPage = () => {
    const params = useParams<{ id: string }>();
    const phaseId = (params.id || '').trim();
    const [phases, setPhases] = useState<V2Phase[] | null>(null);
    const [loading, setLoading] = useState(true);
    const [detail, setDetail] = useState<PhaseDetailResponse | null>(null);
    const [detailLoading, setDetailLoading] = useState(true);
    const [error, setError] = useState<string>('');
    const [detailError, setDetailError] = useState<string>('');

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

    React.useEffect(() => {
      let mounted = true;
      const run = async () => {
        if (!phaseId) {
          setDetail(null);
          setDetailLoading(false);
          setDetailError('Missing phase id');
          return;
        }
        setDetailLoading(true);
        setDetailError('');
        try {
          const res = await fetch(`http://localhost:8000/api/phases/${encodeURIComponent(phaseId)}/detail`);
          if (!res.ok) throw new Error(`Failed to load phase details (${res.status})`);
          const payload = (await res.json()) as PhaseDetailResponse;
          if (!mounted) return;
          setDetail(payload);
        } catch (e) {
          if (!mounted) return;
          setDetail(null);
          setDetailError(e instanceof Error ? e.message : 'Failed to load phase details');
        } finally {
          if (mounted) setDetailLoading(false);
        }
      };
      run();
      return () => {
        mounted = false;
      };
    }, [phaseId]);

    const activePhases = React.useMemo(() => {
      return (phases || [])
        .filter((p) => p.isActive)
        .slice()
        .sort((a, b) => a.sortOrder - b.sortOrder);
    }, [phases]);

    const phase = React.useMemo(() => {
      if (detail?.phase) return detail.phase;
      if (!phases || !phaseId) return null;
      return phases.find((p) => p.id === phaseId) || null;
    }, [detail, phases, phaseId]);

    const homeHref = role === 'admin' ? '/dashboard' : '/';

    if (loading || detailLoading) {
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
              {detailError || error ? detailError || error : 'The requested loan phase could not be found.'}
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

    const knowledge: PhaseKnowledge = detail?.knowledge || {
      timeline: 'Varies',
      summary: phase.description || '—',
      activities: [],
      documents: [],
      stakeholders: [],
      bottlenecks: [],
    };

    const metrics = detail?.metrics || { loanCount: 0, conversationCount: 0 };
    const phaseColor = phase.color || '#3b82f6';

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
                    {phase.icon || phase.sortOrder}
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
                <div
                  className="rounded-2xl px-3 py-1.5 text-[11px] font-semibold border"
                  style={{ backgroundColor: `${phaseColor}18`, color: phaseColor, borderColor: `${phaseColor}40` }}
                  data-testid="phase-timeline"
                >
                  {knowledge.timeline}
                </div>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4">
              <div className="grid gap-4">
                <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] p-5">
                  <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white" data-testid="card-summary">
                    Overview
                  </div>
                  <div className="mt-2 text-sm text-slate-600 dark:text-slate-300 leading-relaxed" data-testid="text-phase-summary">
                    {knowledge.summary}
                  </div>
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.02] px-4 py-3">
                      <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Loans In Phase</div>
                      <div className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200" data-testid="phase-loan-count">
                        {metrics.loanCount}
                      </div>
                    </div>
                    <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.02] px-4 py-3">
                      <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Conversations In Phase</div>
                      <div className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-200" data-testid="phase-conversation-count">
                        {metrics.conversationCount}
                      </div>
                    </div>
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

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] p-5" data-testid="card-activities">
                  <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Key Activities</div>
                  {knowledge.activities.length ? (
                    <ul className="mt-3 space-y-2.5">
                      {knowledge.activities.map((activity, i) => (
                        <li key={i} className="flex items-start gap-2.5" data-testid={`text-activity-${i}`}>
                          <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400/80 shrink-0" />
                          <span className="text-sm text-slate-600 dark:text-slate-300">{activity}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No configured activities for this phase.</div>
                  )}
                  </div>

                <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] p-5" data-testid="card-documents">
                  <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Required Documents</div>
                  {knowledge.documents.length ? (
                    <ul className="mt-3 space-y-2.5">
                      {knowledge.documents.map((doc, i) => (
                        <li key={i} className="flex items-start gap-2.5" data-testid={`text-document-${i}`}>
                          <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-violet-400/80 shrink-0" />
                          <span className="text-sm text-slate-600 dark:text-slate-300">{doc}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No configured documents for this phase.</div>
                  )}
                </div>

                <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] p-5" data-testid="card-stakeholders">
                  <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Stakeholders Involved</div>
                  {knowledge.stakeholders.length ? (
                    <ul className="mt-3 space-y-2.5">
                      {knowledge.stakeholders.map((person, i) => (
                        <li key={i} className="flex items-start gap-2.5" data-testid={`text-stakeholder-${i}`}>
                          <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-sky-400/80 shrink-0" />
                          <span className="text-sm text-slate-600 dark:text-slate-300">{person}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No configured stakeholders for this phase.</div>
                  )}
                </div>

                <div className="rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] p-5" data-testid="card-bottlenecks">
                  <div className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">Common Bottlenecks</div>
                  {knowledge.bottlenecks.length ? (
                    <ul className="mt-3 space-y-2.5">
                      {knowledge.bottlenecks.map((issue, i) => (
                        <li key={i} className="flex items-start gap-2.5" data-testid={`text-bottleneck-${i}`}>
                          <span className="mt-0.5 h-2.5 w-2.5 rounded-full bg-amber-400/80 shrink-0" />
                          <span className="text-sm text-slate-600 dark:text-slate-300">{issue}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mt-3 text-sm text-slate-500 dark:text-slate-400">No configured bottlenecks for this phase.</div>
                  )}
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
            mode={authMode}
            username={username}
            password={password}
            loginError={loginError}
            onSubmit={handleLogin}
            onUsernameChange={setUsername}
            onPasswordChange={setPassword}
            onModeChange={(nextMode) => {
              setAuthMode(nextMode);
              const qs = nextMode === 'select' ? '' : `?mode=${encodeURIComponent(nextMode)}`;
              navigate(`/login${qs}`, { replace: true });
            }}
            onClearError={() => setLoginError('')}
          />
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
        path="/borrower"
        element={
          <RequireAuth>
            <RequireRole allow="user">
              <BorrowerHomePage />
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/borrower/apply"
        element={
          <RequireAuth>
            <RequireRole allow="user">
              <BorrowerApplyPage />
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/borrower/thank-you"
        element={
          <RequireAuth>
            <RequireRole allow="user">
              <BorrowerThankYouPage />
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/borrower/applications"
        element={
          <RequireAuth>
            <RequireRole allow="user">
              <BorrowerApplicationsPage />
            </RequireRole>
          </RequireAuth>
        }
      />
      <Route
        path="/borrower/application/:id"
        element={
          <RequireAuth>
            <RequireRole allow="user">
              <BorrowerApplicationDetailPage />
            </RequireRole>
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
                <div className="space-y-6">
                  <MetricsDashboard isAdmin autoRefresh />
                  <MetricsPanel />
                </div>
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

function BorrowerApplyPage() {
  const navigate = useNavigate();
  const [name, setName] = React.useState('');
  const [email, setEmail] = React.useState('');
  const [phone, setPhone] = React.useState('');
  const [loanType, setLoanType] = React.useState('Home Loan');
  const [amount, setAmount] = React.useState('');
  const [error, setError] = React.useState('');
  const API_BASE_URL =
    (import.meta.env.VITE_API_URL as string | undefined) ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');
  const STORAGE_KEY = 'v2_borrower_conversation_id';
  const submitApplication = useMutation({
    mutationFn: async (payload: {
      borrowerName: string;
      borrowerEmail: string | null;
      borrowerPhone: string | null;
      loanType: string;
      loanAmount: string;
      catalogProductCode: string | null;
    }) => {
      const existingConv = ((): string | null => {
        try {
          return window.localStorage.getItem(STORAGE_KEY) || null;
        } catch {
          return null;
        }
      })();
      const headers: Record<string, string> = { 'content-type': 'application/json' };
      if (existingConv) headers['X-Conversation-ID'] = existingConv;
      const res = await fetch(`${API_BASE_URL}/api/borrower/applications`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to submit (${res.status})`);
      }
      return (await res.json()) as { conversationId: string; loan: { id: string } };
    },
    onSuccess: (payload) => {
      try {
        window.localStorage.setItem(STORAGE_KEY, payload.conversationId);
      } catch (e) {
        void e;
      }
      toast.success('Application submitted');
      navigate('/borrower/thank-you', { replace: true });
    },
    onError: (e: unknown) => {
      setError(e instanceof Error ? e.message : 'Submit failed');
    },
  });
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const trimmedName = name.trim();
    const trimmedEmail = email.trim();
    const trimmedAmount = amount.trim();
    if (!trimmedName || !trimmedEmail || !trimmedAmount) return;
    submitApplication.mutate({
      borrowerName: trimmedName,
      borrowerEmail: trimmedEmail,
      borrowerPhone: phone.trim() || null,
      loanType,
      loanAmount: trimmedAmount,
      catalogProductCode: null,
    });
  };
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d]">
      <header className="glass-header border-b border-slate-200/40 dark:border-white/[0.04] px-6 py-4 flex items-center justify-between bg-white/70 dark:bg-[#141414]/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-white dark:bg-white/10 flex items-center justify-center shadow-sm">
            <span className="text-sm font-black tracking-tight text-slate-900 dark:text-white">KS</span>
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight text-slate-900 dark:text-white">LoanAssist AI</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Start your application</p>
          </div>
        </div>
        <Link to="/" className="no-underline">
          <span className="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm">
            Back to Home
          </span>
        </Link>
      </header>
      <div className="max-w-3xl mx-auto p-6">
        <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-xl p-6">
          <h2 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-white mb-1">Quick Apply</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Share a few details to get started. You can complete the rest in chat.</p>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-300">Full name</label>
              <input value={name} onChange={(e)=>setName(e.target.value)} className="mt-1 w-full px-4 py-3 rounded-2xl border border-slate-200/60 dark:border-white/[0.10] bg-white/70 dark:bg-white/[0.03] text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-blue-500/20" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-300">Email</label>
              <input type="email" value={email} onChange={(e)=>setEmail(e.target.value)} className="mt-1 w-full px-4 py-3 rounded-2xl border border-slate-200/60 dark:border-white/[0.10] bg-white/70 dark:bg-white/[0.03] text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-blue-500/20" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-300">Phone</label>
              <input value={phone} onChange={(e)=>setPhone(e.target.value)} className="mt-1 w-full px-4 py-3 rounded-2xl border border-slate-200/60 dark:border-white/[0.10] bg-white/70 dark:bg-white/[0.03] text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-blue-500/20" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 dark:text-slate-300">Loan type</label>
              <select value={loanType} onChange={(e)=>setLoanType(e.target.value)} className="mt-1 w-full px-4 py-3 rounded-2xl border border-slate-200/60 dark:border-white/[0.10] bg-white/70 dark:bg-white/[0.03] text-slate-900 dark:text-white outline-none">
                <option>Home Loan</option>
                <option>Personal Loan</option>
                <option>Auto Loan</option>
                <option>Business Loan</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="text-xs font-medium text-slate-600 dark:text-slate-300">Desired amount</label>
              <input value={amount} onChange={(e)=>setAmount(e.target.value)} placeholder="$20,000" className="mt-1 w-full px-4 py-3 rounded-2xl border border-slate-200/60 dark:border-white/[0.10] bg-white/70 dark:bg-white/[0.03] text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-blue-500/20" />
            </div>
            <div className="md:col-span-2">
              {error ? <div className="mb-2 text-sm font-semibold text-red-600 dark:text-red-400">{error}</div> : null}
              <button type="submit" disabled={submitApplication.isPending} className="w-full rounded-2xl bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-3 text-sm font-extrabold text-white shadow-lg shadow-blue-600/20">
                {submitApplication.isPending ? 'Submitting…' : 'Submit Application'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function BorrowerThankYouPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d]">
      <div className="max-w-lg mx-auto p-6 pt-20">
        <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-xl p-6 text-center">
          <div className="w-14 h-14 rounded-2xl mx-auto mb-4 bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/25">
            <CheckCircle2 className="w-7 h-7 text-white" />
          </div>
          <h2 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-white mb-1">Thanks! We received your details</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-5">Check your borrower home for next steps or continue in chat for guidance.</p>
          <Link to="/" className="no-underline inline-block rounded-2xl bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-3 text-sm font-extrabold text-white shadow-lg shadow-blue-600/20">Go to Borrower Home</Link>
        </div>
      </div>
    </div>
  );
}

function BorrowerApplicationsPage() {
  const API_BASE_URL =
    (import.meta.env.VITE_API_URL as string | undefined) ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');
  const STORAGE_KEY = 'v2_borrower_conversation_id';
  const convId = React.useMemo(() => {
    try {
      return window.localStorage.getItem(STORAGE_KEY) || null;
    } catch {
      return null;
    }
  }, []);
  const appsQuery = useQuery({
    queryKey: ['borrowerApplications', convId],
    enabled: !!convId,
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/borrower/applications`, { headers: { 'X-Conversation-ID': convId! } });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to load (${res.status})`);
      }
      return (await res.json()) as Array<{ id: string; loanType?: string | null; loanAmount?: string | null; status?: string | null }>;
    },
    staleTime: 10_000,
    gcTime: 5 * 60_000,
  });
  const items = appsQuery.data ?? [];
  const error = appsQuery.error instanceof Error ? appsQuery.error.message : '';
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d]">
      <div className="max-w-4xl mx-auto p-6">
        <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-xl p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-white">Your Applications</h2>
            <Link to="/borrower/apply" className="no-underline rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm">New Application</Link>
          </div>
          {error ? <div className="mt-3 text-sm font-semibold text-red-600 dark:text-red-400">{error}</div> : null}
          {appsQuery.isLoading ? <div className="mt-4 text-slate-500 dark:text-slate-400">Loading…</div> : null}
          {!appsQuery.isLoading && items.length === 0 ? (
            <div className="mt-4 rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-8 text-center text-slate-500 dark:text-slate-400">
              {convId ? 'No applications to show yet.' : 'Start an application to see it here.'}
            </div>
          ) : null}
          <div className="mt-4 grid gap-3">
            {items.map((it) => (
              <Link
                to={`/borrower/application/${it.id}`}
                key={it.id}
                className="no-underline rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03] px-4 py-4 flex items-center justify-between"
              >
                <div className="min-w-0">
                  <div className="text-sm font-extrabold text-slate-900 dark:text-white">Application {it.id.slice(0, 8)}</div>
                  <div className="mt-0.5 text-xs text-slate-600 dark:text-slate-400">
                    {it.loanType || '—'} · {it.loanAmount || '—'}
                  </div>
                </div>
                <div className="shrink-0 text-[11px] font-extrabold text-slate-700 dark:text-slate-300">{it.status || '—'}</div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function BorrowerApplicationDetailPage() {
  const { id } = useParams();
  const [error, setError] = React.useState('');
  const [pendingDoc, setPendingDoc] = React.useState<string | null>(null);
  const [dropFile, setDropFile] = React.useState<File | null>(null);
  const [docPickerOpen, setDocPickerOpen] = React.useState(false);
  const [dragActive, setDragActive] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);
  const API_BASE_URL =
    (import.meta.env.VITE_API_URL as string | undefined) ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');
  const STORAGE_KEY = 'v2_borrower_conversation_id';
  const qc = useQueryClient();
  const convId = React.useMemo(() => {
    try {
      return window.localStorage.getItem(STORAGE_KEY) || null;
    } catch {
      return null;
    }
  }, []);
  const loanQuery = useQuery({
    queryKey: ['borrowerApplication', convId, id],
    enabled: !!convId && !!id,
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/borrower/applications/${id}`, { headers: { 'X-Conversation-ID': convId! } });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Failed to load (${res.status})`);
      }
      return (await res.json()) as Record<string, unknown>;
    },
    staleTime: 10_000,
    gcTime: 5 * 60_000,
  });
  const loan = loanQuery.data ?? null;
  const items = React.useMemo(() => {
    const cl = (loan as { documentChecklist?: unknown } | null)?.documentChecklist;
    const arr = (cl && typeof cl === 'object' ? (cl as { items?: unknown }).items : null) as Array<Record<string, unknown>> | null;
    const docs = Array.isArray(arr) ? arr : [];
    const mapped = docs.map((d) => {
      const name = String(d.name ?? 'Document');
      const status = String(d.status ?? 'missing').toLowerCase();
      const uploaded = status !== 'missing';
      return { name, status: uploaded ? 'optional' as const : 'required' as const, description: '', uploaded };
    });
    return {
      identity: mapped,
      income: [] as Array<{ name: string; status: 'required' | 'optional'; description: string; uploaded?: boolean }>,
    };
  }, [loan]);
  const uploadDocument = useMutation({
    mutationFn: async (payload: { docName: string; file: File; category?: string }) => {
      if (!id || !convId) throw new Error('Missing application context');
      const form = new FormData();
      form.append('loanId', id);
      const deriveCategory = () => {
        const n = payload.docName.toLowerCase();
        const inIdentity = items.identity.some((x) => x.name.toLowerCase() === n);
        const inIncome = items.income.some((x) => x.name.toLowerCase() === n);
        if (inIncome) return 'income';
        if (inIdentity) return 'identity';
        return 'identity';
      };
      form.append('category', payload.category || deriveCategory());
      const typeKey = payload.docName.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
      form.append('documentType', typeKey || 'document');
      form.append('file', payload.file, payload.file.name);
      const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: 'POST',
        headers: { 'X-Conversation-ID': convId },
        body: form,
      });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        throw new Error(t || `Upload failed (${res.status})`);
      }
      return true;
    },
    onSuccess: () => {
      setPendingDoc(null);
      setDropFile(null);
      setDocPickerOpen(false);
      toast.success('Document uploaded');
      void qc.invalidateQueries({ queryKey: ['borrowerApplication', convId, id] });
      void qc.invalidateQueries({ queryKey: ['borrowerApplications', convId] });
    },
    onError: (e: unknown) => {
      setError(e instanceof Error ? e.message : 'Upload failed');
      toast.error('Upload failed');
    },
  });
  const missingDocs = React.useMemo(() => items.identity.filter((d) => !d.uploaded).map((d) => d.name), [items.identity]);
  const onUpload = React.useCallback((docName: string) => {
    if (uploadDocument.isPending) return;
    setPendingDoc(docName);
    const el = fileInputRef.current;
    if (el) {
      el.value = '';
      el.click();
    }
  }, [uploadDocument.isPending]);
  const handleFile = React.useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!e.target.files || e.target.files.length === 0 || !pendingDoc) return;
      const f = e.target.files[0]!;
      const n = pendingDoc.toLowerCase();
      const inIncome = items.income.some((x) => x.name.toLowerCase() === n);
      const category = inIncome ? 'income' : 'identity';
      uploadDocument.mutate({ docName: pendingDoc, file: f, category });
    },
    [pendingDoc, uploadDocument, items.income],
  );
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d]">
      <div className="max-w-4xl mx-auto p-6">
        <div className="rounded-3xl bg-white/80 dark:bg-white/[0.04] backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-xl p-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-white">Application #{id}</h2>
            <Link to="/borrower/applications" className="no-underline rounded-2xl px-3 py-2 text-xs font-semibold bg-white/80 dark:bg-white/[0.06] border border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm">Back to list</Link>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">Upload required documents to progress your application.</p>
          {error ? <div className="mb-3 text-sm font-semibold text-red-600 dark:text-red-400">{error}</div> : null}
          {loanQuery.isLoading ? <div className="text-slate-500 dark:text-slate-400">Loading…</div> : null}
          {!loanQuery.isLoading ? (
            <>
              <div
                className={`mb-4 rounded-2xl border border-dashed px-5 py-4 ${dragActive ? 'border-blue-400 bg-blue-50/70 dark:bg-blue-900/20' : 'border-slate-200/60 dark:border-white/[0.08] bg-white/60 dark:bg-white/[0.03]'}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragActive(true);
                }}
                onDragLeave={() => setDragActive(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragActive(false);
                  const f = e.dataTransfer.files && e.dataTransfer.files[0];
                  if (!f) return;
                  if (uploadDocument.isPending) return;
                  setDropFile(f);
                  if (missingDocs.length === 1) {
                    const dn = missingDocs[0]!;
                    const n = dn.toLowerCase();
                    const inIncome = items.income.some((x) => x.name.toLowerCase() === n);
                    const category = inIncome ? 'income' : 'identity';
                    uploadDocument.mutate({ docName: dn, file: f, category });
                    return;
                  }
                  setDocPickerOpen(true);
                }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-extrabold text-slate-900 dark:text-white">Drag & drop documents</div>
                    <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                      Drop a PDF or image here, then choose which requirement it satisfies.
                    </div>
                  </div>
                  <div className="text-[11px] font-extrabold text-slate-700 dark:text-slate-300">
                    {uploadDocument.isPending ? 'Uploading…' : 'Ready'}
                  </div>
                </div>
              </div>

              <DocumentsCard checklist={items} onUpload={onUpload} busyDocumentName={uploadDocument.isPending ? pendingDoc : null} disableUpload={uploadDocument.isPending} />

              <Dialog.Root open={docPickerOpen} onOpenChange={setDocPickerOpen}>
                <Dialog.Portal>
                  <Dialog.Overlay className="fixed inset-0 bg-black/40" />
                  <Dialog.Content className="fixed left-1/2 top-1/2 w-[92vw] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-slate-200/60 dark:border-white/[0.08] bg-white dark:bg-[#111113] p-4 shadow-2xl">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <Dialog.Title className="text-sm font-extrabold text-slate-900 dark:text-white">Select document type</Dialog.Title>
                        <Dialog.Description className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                          Choose which checklist item this file should satisfy.
                        </Dialog.Description>
                      </div>
                      <Dialog.Close asChild>
                        <button type="button" className="text-xs font-bold text-slate-600 dark:text-slate-300">
                          Close
                        </button>
                      </Dialog.Close>
                    </div>
                    <div className="mt-3 grid gap-2">
                      {missingDocs.length ? (
                        missingDocs.map((d) => (
                          <button
                            key={d}
                            type="button"
                            disabled={!dropFile || uploadDocument.isPending}
                            onClick={() => {
                              if (!dropFile) return;
                              const n = d.toLowerCase();
                              const inIncome = items.income.some((x) => x.name.toLowerCase() === n);
                              const category = inIncome ? 'income' : 'identity';
                              uploadDocument.mutate({ docName: d, file: dropFile, category });
                            }}
                            className="text-left rounded-xl border border-slate-200/60 dark:border-white/[0.08] bg-white/70 dark:bg-white/[0.04] px-3 py-2 text-xs font-bold text-slate-800 dark:text-slate-200 disabled:opacity-50"
                          >
                            {d}
                          </button>
                        ))
                      ) : (
                        <div className="text-xs text-slate-500 dark:text-slate-400">No missing checklist items.</div>
                      )}
                    </div>
                  </Dialog.Content>
                </Dialog.Portal>
              </Dialog.Root>
            </>
          ) : null}
          <input ref={fileInputRef} type="file" onChange={handleFile} className="hidden" />
        </div>
      </div>
    </div>
  );
}
