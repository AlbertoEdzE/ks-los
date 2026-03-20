import React, { useMemo, useRef, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  onConversationUpdated?: (conversation: V2Conversation) => void;
  onPhasesUpdated?: (phases: V2Phase[]) => void;
  conversation?: V2Conversation | null;
  phases?: V2Phase[] | null;
  resetSignal?: number;
}

type V2ChatRole = 'user' | 'assistant';

export type V2Conversation = {
  id: string;
  borrowerName?: string | null;
  status?: string | null;
  chatRole?: string | null;
  currentPhaseId?: string | null;
  seriousnessScore?: number | null;
  fitScore?: number | null;
  intentSummary?: unknown;
  approvalProbability?: number | null;
  recommendedProducts?: unknown;
  nextConversationAngle?: string | null;
  assignedOfficer?: string | null;
  createdAt?: string | null;
};

export type V2Phase = {
  id: string;
  name: string;
  description?: string | null;
  sortOrder: number;
  isActive: boolean;
  color?: string | null;
  icon?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};

type V2Message = {
  id: string;
  conversationId: string;
  role: V2ChatRole;
  content: string;
  metadata?: unknown;
  createdAt?: string | null;
};

type V2Loan = {
  id: string;
  borrowerName?: string | null;
  loanType?: string | null;
  loanAmount?: string | null;
  employmentType?: string | null;
  catalogProductCode?: string | null;
  stpProcessingStatus?: string | null;
  stpProcessingLog?: unknown;
  stpPayload?: unknown;
  termsAcceptedAt?: string | null;
  disbursement?: unknown;
  currentPhaseId?: string | null;
  status?: string | null;
  conversationId?: string | null;
  documentChecklist?: unknown;
};

type V2LoanDocument = {
  id: string;
  loanId: string;
  category?: string | null;
  documentType?: string | null;
  status?: string | null;
  reviewNote?: string | null;
  fileName?: string | null;
  originalName?: string | null;
  mimeType?: string | null;
  fileSize?: number | null;
  uploadedAt?: string | null;
  reviewedAt?: string | null;
};

type V2LoanApplicationMeta = {
  success?: boolean;
  loanId?: string;
  stpApproved?: boolean;
  stpCompleted?: boolean;
  awaitingAcceptance?: boolean;
  bureauReport?: unknown;
  stpSteps?: Array<{ ruleGroup?: string; phase?: string; passed?: number; total?: number }>;
  audit?: Array<{ ts?: string; ruleGroup?: string; phase?: string; passed?: number; total?: number }>;
  affordability?: unknown;
  liabilityComparison?: unknown;
  disbursement?: {
    reference?: string;
    status?: string;
    amount?: string;
    currency?: string;
    method?: string;
    disbursedAt?: string;
  } | null;
  approval?: {
    rate?: string | null;
    tenure?: string | null;
    emi?: string | null;
    conditions?: string[] | null;
  } | null;
};

const getLoanApplicationMeta = (metadata: unknown): V2LoanApplicationMeta | null => {
  if (!metadata || typeof metadata !== 'object') return null;
  const la = (metadata as { loanApplication?: unknown }).loanApplication;
  if (!la || typeof la !== 'object') return null;
  return la as V2LoanApplicationMeta;
};

const DisbursementConfirmationCard: React.FC<{ loanApplication: V2LoanApplicationMeta }> = ({ loanApplication }) => {
  const d = loanApplication.disbursement;
  if (!d || !loanApplication.stpCompleted) return null;
  const a = loanApplication.approval;
  return (
    <div className="w-full mt-2" data-testid="disbursement-confirmation-card">
      <div className="rounded-2xl overflow-hidden shadow-lg shadow-emerald-500/10 dark:shadow-emerald-500/5 border border-emerald-200/50 dark:border-emerald-500/10 bg-white dark:bg-[#111113]">
        <div className="bg-gradient-to-br from-[#1B2A4A] via-[#0a3d7c] to-[#005EA6] p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-extrabold text-white">Funds Credited Successfully</div>
              <div className="mt-0.5 text-[11px] text-white/60">Congratulations! Your loan has been disbursed</div>
            </div>
            <div className="px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-400/30 text-[9px] font-extrabold text-emerald-200 uppercase tracking-wider">
              Verified
            </div>
          </div>

          <div className="mt-4 text-center py-3 rounded-xl bg-white/[0.06]">
            <div className="text-[10px] text-white/45 uppercase tracking-[0.2em]">Amount Credited</div>
            <div className="mt-1 text-3xl font-black text-white tracking-tight" data-testid="text-disbursed-amount">
              {d.amount}
            </div>
            <div className="mt-1 text-xs text-white/55">{d.currency || '—'} · Direct Bank Transfer</div>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2">
            <div className="rounded-xl bg-white/[0.08] px-3 py-2 text-center">
              <div className="text-[9px] text-white/45 uppercase tracking-wider">Transaction Ref</div>
              <div className="mt-0.5 text-[11px] font-mono font-bold text-white" data-testid="text-disbursement-ref">
                {d.reference}
              </div>
            </div>
            <div className="rounded-xl bg-white/[0.08] px-3 py-2 text-center">
              <div className="text-[9px] text-white/45 uppercase tracking-wider">Transfer Date</div>
              <div className="mt-0.5 text-[11px] font-bold text-white">{d.disbursedAt ? new Date(d.disbursedAt).toLocaleDateString() : '—'}</div>
            </div>
          </div>
        </div>

        {a ? (
          <div className="border-t border-slate-100 dark:border-white/[0.04]">
            <div className="px-4 py-2 bg-slate-50/80 dark:bg-white/[0.02] border-b border-slate-100 dark:border-white/[0.04]">
              <div className="text-[10px] font-extrabold text-slate-700 dark:text-slate-300 uppercase tracking-wider">Approved Loan Terms</div>
            </div>
            <div className="grid grid-cols-3 divide-x divide-slate-100 dark:divide-white/[0.04]">
              <div className="p-3 text-center">
                <div className="text-[9px] text-slate-500 dark:text-slate-400">Rate</div>
                <div className="mt-0.5 text-xs font-extrabold text-slate-800 dark:text-slate-200">{a.rate || 'N/A'}</div>
              </div>
              <div className="p-3 text-center">
                <div className="text-[9px] text-slate-500 dark:text-slate-400">Tenure</div>
                <div className="mt-0.5 text-xs font-extrabold text-slate-800 dark:text-slate-200">{a.tenure || 'N/A'}</div>
              </div>
              <div className="p-3 text-center">
                <div className="text-[9px] text-slate-500 dark:text-slate-400">Monthly EMI</div>
                <div className="mt-0.5 text-xs font-extrabold text-slate-800 dark:text-slate-200">{a.emi || 'N/A'}</div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

const StpOfferCard: React.FC<{
  loanApplication: V2LoanApplicationMeta;
  conversationId: string | null;
  loanId: string | null | undefined;
  onAccepted: () => Promise<void>;
}> = ({ loanApplication, conversationId, loanId, onAccepted }) => {
  if (!loanApplication.awaitingAcceptance) return null;
  const a = loanApplication.approval;
  if (!a) return null;
  const steps = Array.isArray(loanApplication.stpSteps) ? loanApplication.stpSteps : [];
  const conditions = Array.isArray(a.conditions) ? a.conditions : [];
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [sigDrawing, setSigDrawing] = useState(false);
  const [sigHasInk, setSigHasInk] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sigCanvasRef = useRef<HTMLCanvasElement>(null);
  const bureauReport = (loanApplication as { bureauReport?: unknown }).bureauReport;
  const affordability = (loanApplication as { affordability?: unknown }).affordability;
  const liabilityComparison = (loanApplication as { liabilityComparison?: unknown }).liabilityComparison;

  const extractFacts = (prefix: string, obj: unknown) => {
    if (!obj || typeof obj !== 'object') return [] as Array<{ label: string; value: string }>;
    const entries = Object.entries(obj as Record<string, unknown>)
      .filter(([, v]) => ['string', 'number', 'boolean'].includes(typeof v))
      .slice(0, 3)
      .map(([k, v]) => ({ label: `${prefix} ${k}`, value: String(v) }));
    return entries;
  };

  const facts = [
    ...extractFacts('Bureau', bureauReport),
    ...extractFacts('Affordability', affordability),
    ...extractFacts('Liability', liabilityComparison),
  ].slice(0, 6);

  const clearSignature = () => {
    const c = sigCanvasRef.current;
    if (!c) return;
    const ctx = c.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, c.width, c.height);
    setSigHasInk(false);
  };

  const acceptTerms = async () => {
    if (!conversationId || !loanId) return;
    const c = sigCanvasRef.current;
    if (!c) return;
    setError(null);
    setBusy(true);
    try {
      const signature = c.toDataURL('image/png');
      const res = await fetch(`http://localhost:8000/api/loans/${loanId}/accept-terms`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'X-Conversation-ID': conversationId },
        body: JSON.stringify({ signature }),
      });
      if (!res.ok) {
        const raw = await res.text().catch(() => '');
        setError(raw ? `Submit failed: ${raw}` : `Submit failed (${res.status}).`);
        return;
      }
      await onAccepted();
    } catch {
      setError('Submit failed due to a network error.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="w-full mt-2" data-testid="stp-offer-card">
      <div className="rounded-2xl overflow-hidden shadow-lg shadow-blue-500/10 dark:shadow-blue-500/5 border border-blue-200/50 dark:border-blue-500/10 bg-white dark:bg-[#111113]">
        <div className="bg-gradient-to-br from-[#1B2A4A] via-[#0a3d7c] to-[#005EA6] p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-extrabold text-white">Automated Assessment Complete</div>
              <div className="mt-0.5 text-[11px] text-white/60">Review terms and accept to authorize disbursement</div>
            </div>
            <div className="px-2 py-0.5 rounded-full bg-blue-500/20 border border-blue-400/30 text-[9px] font-extrabold text-blue-200 uppercase tracking-wider">
              Offer Ready
            </div>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-2">
            <div className="rounded-xl bg-white/[0.08] px-3 py-2 text-center">
              <div className="text-[9px] text-white/45 uppercase tracking-wider">Rate</div>
              <div className="mt-0.5 text-xs font-extrabold text-white" data-testid="text-offer-rate">
                {a.rate || 'N/A'}
              </div>
            </div>
            <div className="rounded-xl bg-white/[0.08] px-3 py-2 text-center">
              <div className="text-[9px] text-white/45 uppercase tracking-wider">Tenure</div>
              <div className="mt-0.5 text-xs font-extrabold text-white" data-testid="text-offer-tenure">
                {a.tenure || 'N/A'}
              </div>
            </div>
            <div className="rounded-xl bg-white/[0.08] px-3 py-2 text-center">
              <div className="text-[9px] text-white/45 uppercase tracking-wider">Monthly EMI</div>
              <div className="mt-0.5 text-xs font-extrabold text-white" data-testid="text-offer-emi">
                {a.emi || 'N/A'}
              </div>
            </div>
          </div>

          {conditions.length > 0 ? (
            <div className="mt-3 rounded-xl bg-white/[0.06] border border-white/[0.08] px-3 py-2">
              <div className="text-[9px] text-white/45 uppercase tracking-wider">Conditions</div>
              <div className="mt-1 space-y-1">
                {conditions.slice(0, 4).map((c) => (
                  <div key={c} className="text-[11px] text-white/80">
                    • {c}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {facts.length > 0 ? (
            <div className="mt-3 rounded-xl bg-white/[0.06] border border-white/[0.08] px-3 py-2">
              <div className="text-[9px] text-white/45 uppercase tracking-wider">Signals</div>
              <div className="mt-1 grid gap-1">
                {facts.map((f) => (
                  <div key={`${f.label}:${f.value}`} className="text-[11px] text-white/80">
                    • {f.label}: {f.value}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <div className="border-t border-slate-100 dark:border-white/[0.04]">
          <div className="px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs font-extrabold tracking-tight text-slate-800 dark:text-slate-200">Accept Terms</div>
              <button
                type="button"
                onClick={clearSignature}
                className="text-[11px] font-bold text-slate-600 dark:text-slate-300"
                data-testid="button-terms-clear"
              >
                Clear
              </button>
            </div>

            <div className="mt-2 flex items-start gap-2">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                data-testid="checkbox-terms-accept"
              />
              <div className="text-[11px] text-slate-600 dark:text-slate-300">
                I accept the offer terms and authorize disbursement.
              </div>
            </div>

            <div className="mt-2">
              <canvas
                ref={sigCanvasRef}
                width={520}
                height={160}
                className="w-full h-[160px] rounded-xl border border-slate-200/60 dark:border-white/[0.06] bg-white dark:bg-black/20 touch-none"
                data-testid="canvas-terms-signature"
                onPointerDown={(e) => {
                  const c = sigCanvasRef.current;
                  if (!c) return;
                  const ctx = c.getContext('2d');
                  if (!ctx) return;
                  const rect = c.getBoundingClientRect();
                  ctx.beginPath();
                  ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
                  ctx.lineWidth = 2.2;
                  ctx.lineCap = 'round';
                  ctx.strokeStyle = '#0f172a';
                  setSigDrawing(true);
                }}
                onPointerMove={(e) => {
                  if (!sigDrawing) return;
                  const c = sigCanvasRef.current;
                  if (!c) return;
                  const ctx = c.getContext('2d');
                  if (!ctx) return;
                  const rect = c.getBoundingClientRect();
                  ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
                  ctx.stroke();
                  setSigHasInk(true);
                }}
                onPointerUp={() => setSigDrawing(false)}
                onPointerLeave={() => setSigDrawing(false)}
              />
            </div>

            {error ? <div className="mt-2 text-[11px] text-red-600 dark:text-red-400">{error}</div> : null}

            <div className="mt-3 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => void acceptTerms()}
                disabled={!conversationId || !loanId || !termsAccepted || !sigHasInk || busy}
                className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-[11px] font-extrabold text-white shadow-lg shadow-blue-600/20 disabled:opacity-40 disabled:cursor-not-allowed"
                data-testid="button-terms-accept"
              >
                {busy ? 'Submitting…' : 'Accept & Disburse'}
              </button>
            </div>
          </div>
        </div>

        {steps.length > 0 ? (
          <div className="border-t border-slate-100 dark:border-white/[0.04]">
            <div className="px-4 py-2 bg-slate-50/80 dark:bg-white/[0.02] border-b border-slate-100 dark:border-white/[0.04]">
              <div className="text-[10px] font-extrabold text-slate-700 dark:text-slate-300 uppercase tracking-wider">Automated Checks</div>
            </div>
            <div className="px-4 py-3 grid gap-2">
              {steps.map((s, idx) => {
                const passed = (s.passed || 0) >= (s.total || 1);
                return (
                  <div key={`${s.ruleGroup || 'rg'}-${idx}`} className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">{s.phase || 'Check'}</div>
                      <div className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">{s.ruleGroup || '—'}</div>
                    </div>
                    <div className={`shrink-0 text-[11px] font-extrabold ${passed ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'}`}>
                      {passed ? 'Passed' : 'Review'}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

const STORAGE_KEY = 'v2_borrower_conversation_id';

type ViewState = 'welcome' | 'exiting' | 'chat';

const getActorRole = (metadata: unknown): string | null => {
  if (!metadata || typeof metadata !== 'object') return null;
  const role = (metadata as { actorRole?: unknown }).actorRole;
  return typeof role === 'string' ? role : null;
};

const isOfficerOnlyMessage = (message: V2Message): boolean => {
  const actorRole = getActorRole(message.metadata);
  return actorRole === 'officer' || actorRole === 'officer_assistant';
};

const DEFAULT_QUICK_PROMPTS: Array<{ title: string; prompt: string }> = [
  { title: 'Home Loan', prompt: 'I want a home loan to buy a house.' },
  { title: 'Car Loan', prompt: 'I need a car loan for a vehicle purchase.' },
  { title: 'Personal Loan', prompt: 'I need a personal loan for an urgent expense.' },
  { title: 'Debt Consolidation', prompt: 'I want to consolidate multiple debts into one EMI.' },
];

type DocumentCategory = {
  key: string;
  label: string;
  icon: string;
  types: Array<{ key: string; label: string; required: boolean }>;
};

const getDocumentCategories = (loanType: string, employmentType: string): DocumentCategory[] => {
  const lt = (loanType || '').toLowerCase();
  const et = (employmentType || '').toLowerCase();

  const categories: DocumentCategory[] = [
    {
      key: 'identity',
      label: 'Identity & Address',
      icon: '🪪',
      types: [
        { key: 'national_id', label: 'National ID or Passport', required: true },
        { key: 'proof_of_address', label: 'Proof of Address (utility bill, < 3 months)', required: false },
      ],
    },
  ];

  if (et.includes('salaried') || et.includes('employed') || !et.includes('self')) {
    categories.push({
      key: 'income_salaried',
      label: 'Income & Employment',
      icon: '💼',
      types: [
        { key: 'job_letter', label: 'Job Letter (position, salary, tenure)', required: true },
        { key: 'pay_slips', label: "Last 3 Months' Pay Slips", required: false },
        { key: 'bank_statements', label: "Last 6 Months' Bank Statements", required: false },
        { key: 'nis_record', label: 'NIS/NI Contributions Record', required: false },
      ],
    });
  } else {
    categories.push({
      key: 'income_self_employed',
      label: 'Business & Income',
      icon: '🏢',
      types: [
        { key: 'business_registration', label: 'Business Registration Certificate', required: false },
        { key: 'financial_statements', label: "Last 2 Years' Financial Statements", required: false },
        { key: 'tax_returns', label: 'Tax Returns / Tax Compliance Certificate', required: false },
        { key: 'bank_statements_business', label: "Last 6 Months' Business Bank Statements", required: false },
        { key: 'bank_statements_personal', label: "Last 6 Months' Personal Bank Statements", required: false },
      ],
    });
  }

  if (lt.includes('home') || lt.includes('property') || lt.includes('mortgage')) {
    categories.push({
      key: 'property',
      label: 'Property Documents',
      icon: '🏠',
      types: [
        { key: 'sale_agreement', label: 'Agreement / Contract of Sale', required: false },
        { key: 'valuation_report', label: 'Property Valuation Report', required: false },
        { key: 'title_deed', label: 'Title Search / Deed', required: false },
        { key: 'surveyor_report', label: "Surveyor's Report", required: false },
        { key: 'down_payment_proof', label: 'Proof of Down Payment', required: false },
      ],
    });
  }

  if (lt.includes('vehicle') || lt.includes('car') || lt.includes('auto')) {
    categories.push({
      key: 'vehicle',
      label: 'Vehicle Documents',
      icon: '🚗',
      types: [
        { key: 'dealer_invoice', label: 'Pro-forma Invoice or Dealer Quotation', required: false },
        { key: 'vehicle_registration', label: 'Vehicle Registration (if used)', required: false },
      ],
    });
  }

  return categories;
};

export const ChatInterface: React.FC<Props> = ({ onConversationUpdated, onPhasesUpdated, resetSignal }) => {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<V2Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [viewState, setViewState] = useState<ViewState>('welcome');
  const [loan, setLoan] = useState<V2Loan | null>(null);
  const [ui2Docs, setUi2Docs] = useState<V2LoanDocument[]>([]);
  const [ui2DocsLoading, setUi2DocsLoading] = useState(false);
  const [ui2DocsError, setUi2DocsError] = useState<string | null>(null);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [docsOpen, setDocsOpen] = useState(false);
  const [uploadingType, setUploadingType] = useState<string | null>(null);
  const [stpBusy, setStpBusy] = useState(false);
  const [stpError, setStpError] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const requestGenRef = useRef(0);
  const exitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const docsPanelRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingUploadRef = useRef<{ category: string; documentType: string } | null>(null);

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 18) return 'Good Afternoon';
    return 'Good Evening';
  }, []);

  const scrollToBottom = () => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages, loading, viewState]);

  const refreshLoan = async (activeConversationId: string): Promise<V2Loan | null> => {
    try {
      const res = await fetch(`http://localhost:8000/api/conversations/${activeConversationId}/loan`);
      if (!res.ok) {
        if (res.status === 404) setLoan(null);
        return null;
      }
      const data = (await res.json()) as V2Loan;
      setLoan(data);
      return data;
    } catch {
      return null;
    }
  };

  const refreshMessages = async (activeConversationId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/conversations/${activeConversationId}/messages`);
      if (!res.ok) return;
      const next = (await res.json()) as V2Message[];
      setMessages(next.filter((m) => !isOfficerOnlyMessage(m)));
    } catch {
    }
  };

  const refreshUi2Docs = async (activeConversationId: string, activeLoanId: string) => {
    setUi2DocsError(null);
    setUi2DocsLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/documents/loan/${activeLoanId}`, {
        headers: { 'X-Conversation-ID': activeConversationId },
      });
      if (!res.ok) {
        const raw = await res.text().catch(() => '');
        setUi2DocsError(raw ? `Failed to load documents: ${raw}` : `Failed to load documents (${res.status}).`);
        setUi2Docs([]);
        return;
      }
      setUi2Docs((await res.json()) as V2LoanDocument[]);
    } catch {
      setUi2DocsError('Failed to load documents due to a network error.');
      setUi2Docs([]);
    } finally {
      setUi2DocsLoading(false);
    }
  };

  useEffect(() => {
    if (!conversationId || !loan?.id) return;
    void refreshUi2Docs(conversationId, loan.id);
  }, [conversationId, loan?.id]);

  useEffect(() => {
    if (!loan) return;
    const st = (loan.stpProcessingStatus || '').toLowerCase();
    if (st && ['awaiting_documents', 'processing', 'awaiting_acceptance', 'completed'].includes(st)) setDocsOpen(true);
  }, [loan?.stpProcessingStatus]);

  useEffect(() => {
    if (ui2Docs.length > 0) setDocsOpen(true);
  }, [ui2Docs.length]);

  const triggerUi2Upload = (category: string, documentType: string) => {
    pendingUploadRef.current = { category, documentType };
    fileInputRef.current?.click();
  };

  const uploadUi2Document = async (file: File) => {
    if (!conversationId || !loan?.id) return;
    const pending = pendingUploadRef.current;
    if (!pending) return;
    setUploadingType(pending.documentType);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('loanId', loan.id);
      fd.append('category', pending.category);
      fd.append('documentType', pending.documentType);
      const res = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        headers: { 'X-Conversation-ID': conversationId },
        body: fd,
      });
      if (!res.ok) {
        const raw = await res.text().catch(() => '');
        setUi2DocsError(raw ? `Upload failed: ${raw}` : `Upload failed (${res.status}).`);
        return;
      }
      await refreshUi2Docs(conversationId, loan.id);
      await refreshLoan(conversationId);
      await refreshMessages(conversationId);
    } catch {
      setUi2DocsError('Upload failed due to a network error.');
    } finally {
      setUploadingType(null);
      pendingUploadRef.current = null;
    }
  };

  const deleteUi2Document = async (docId: string) => {
    if (!conversationId || !loan?.id) return;
    try {
      const res = await fetch(`http://localhost:8000/api/documents/${docId}`, {
        method: 'DELETE',
        headers: { 'X-Conversation-ID': conversationId },
      });
      if (!res.ok) return;
      await refreshUi2Docs(conversationId, loan.id);
    } catch {
    }
  };

  const downloadUi2Document = async (docId: string, filename: string) => {
    if (!conversationId) return;
    try {
      const res = await fetch(`http://localhost:8000/api/documents/${docId}/download`, {
        headers: { 'X-Conversation-ID': conversationId },
      });
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
    } catch {
    }
  };

  useEffect(() => {
    return () => {
      if (exitTimerRef.current) clearTimeout(exitTimerRef.current);
    };
  }, []);

  useEffect(() => {
    const fetchJson = async <T,>(url: string, init?: RequestInit): Promise<{ ok: true; value: T } | { ok: false; status: number }> => {
      try {
        const res = await fetch(url, init);
        if (!res.ok) return { ok: false, status: res.status };
        return { ok: true, value: (await res.json()) as T };
      } catch {
        return { ok: false, status: 0 };
      }
    };

    const bootstrap = async () => {
      setBootstrapping(true);
      if (typeof resetSignal === 'number') {
        window.localStorage.removeItem(STORAGE_KEY);
      }

      const storedId = window.localStorage.getItem(STORAGE_KEY);
      const activeConversationId: string | null = storedId || null;

      if (!activeConversationId) {
        setConversationId(null);
        setMessages([]);
        setLoan(null);
        setViewState('welcome');
        setBootstrapping(false);
        return;
      }

      const phasesRes = await fetchJson<V2Phase[]>('http://localhost:8000/api/phases/active');
      if (phasesRes.ok) onPhasesUpdated?.(phasesRes.value);

      const existing = await fetchJson<V2Conversation>(`http://localhost:8000/api/conversations/${activeConversationId}`);
      if (!existing.ok) {
        window.localStorage.removeItem(STORAGE_KEY);
        setConversationId(null);
        setMessages([]);
        setViewState('welcome');
        setBootstrapping(false);
        return;
      }

      onConversationUpdated?.(existing.value);
      setConversationId(activeConversationId);
      setViewState('chat');
      void refreshLoan(activeConversationId);

      const msgsRes = await fetchJson<V2Message[]>(`http://localhost:8000/api/conversations/${activeConversationId}/messages`);
      if (msgsRes.ok) {
        setMessages(msgsRes.value.filter((m) => !isOfficerOnlyMessage(m)));
      } else {
        setMessages([
          {
            id: 'messages-error',
            conversationId: activeConversationId,
            role: 'assistant',
            content: 'Unable to load chat history. Please refresh.',
            createdAt: null,
          },
        ]);
      }

      setBootstrapping(false);
    };

    void bootstrap();
  }, [onConversationUpdated, onPhasesUpdated, resetSignal]);

  const transitionToChat = () => {
    if (exitTimerRef.current) clearTimeout(exitTimerRef.current);
    setViewState('exiting');
    exitTimerRef.current = setTimeout(() => {
      setViewState('chat');
      exitTimerRef.current = null;
    }, 400);
  };

  const sendToExisting = async (activeConversationId: string, content: string) => {
    const now = Date.now();
    const userMsg: V2Message = {
      id: `temp-user-${now}`,
      conversationId: activeConversationId,
      role: 'user',
      content,
      createdAt: new Date(now).toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`http://localhost:8000/api/conversations/${activeConversationId}/messages`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ content }),
      });

      if (!res.ok) {
        const raw = await res.text().catch(() => '');
        let detail = raw;
        try {
          const parsed = JSON.parse(raw) as { detail?: unknown };
          if (typeof parsed?.detail === 'string') detail = parsed.detail;
        } catch {
        }
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            conversationId: activeConversationId,
            role: 'assistant',
            content: detail ? `Request failed (${res.status}): ${detail}` : `Request failed (${res.status}). Please try again.`,
            createdAt: null,
          },
        ]);
        return;
      }

      const payload = (await res.json()) as { message?: V2Message };
      if (payload.message && payload.message.role && payload.message.content && !isOfficerOnlyMessage(payload.message as V2Message)) {
        setMessages((prev) => [...prev, payload.message as V2Message]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            conversationId: activeConversationId,
            role: 'assistant',
            content: 'No assistant response was returned. Please try again.',
            createdAt: null,
          },
        ]);
      }

      const refreshed = await fetch(`http://localhost:8000/api/conversations/${activeConversationId}`);
      if (refreshed.ok) {
        onConversationUpdated?.((await refreshed.json()) as V2Conversation);
      }
      await refreshLoan(activeConversationId);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          conversationId: activeConversationId,
          role: 'assistant',
          content: 'Network error. Please try again.',
          createdAt: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const startConversationAndSend = async (firstMessage: string) => {
    if (loading || bootstrapping) return;
    const gen = ++requestGenRef.current;
    transitionToChat();
    setLoading(true);
    try {
      const createRes = await fetch('http://localhost:8000/api/conversations', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (!createRes.ok) {
        if (gen !== requestGenRef.current) return;
        setMessages([
          {
            id: 'bootstrap-error',
            conversationId: 'unknown',
            role: 'assistant',
            content: 'Unable to start a conversation right now. Please refresh and try again.',
            createdAt: null,
          },
        ]);
        setConversationId(null);
        setViewState('welcome');
        return;
      }

      const createdPayload = (await createRes.json()) as { conversation?: V2Conversation };
      const created = createdPayload.conversation;
      if (!created?.id) {
        if (gen !== requestGenRef.current) return;
        setMessages([
          {
            id: 'bootstrap-error',
            conversationId: 'unknown',
            role: 'assistant',
            content: 'Conversation creation returned an invalid response. Please refresh.',
            createdAt: null,
          },
        ]);
        setConversationId(null);
        setViewState('welcome');
        return;
      }

      if (gen !== requestGenRef.current) return;
      window.localStorage.setItem(STORAGE_KEY, created.id);
      setConversationId(created.id);
      onConversationUpdated?.(created);
      void refreshLoan(created.id);

      const phasesRes = await fetch(`http://localhost:8000/api/phases/active`);
      if (phasesRes.ok) {
        onPhasesUpdated?.((await phasesRes.json()) as V2Phase[]);
      }

      await sendToExisting(created.id, firstMessage);
    } finally {
      if (gen === requestGenRef.current) {
        setLoading(false);
      }
    }
  };

  const handleSend = async (text: string) => {
    const content = text.trim();
    if (!content || loading || bootstrapping) return;
    if (!conversationId) {
      await startConversationAndSend(content);
      return;
    }
    if (viewState !== 'chat') setViewState('chat');
    await sendToExisting(conversationId, content);
  };

  const canSend = input.trim().length > 0 && !loading && !bootstrapping;

  const runStp = async () => {
    if (!conversationId || !loan?.id) return;
    setStpError(null);
    setStpBusy(true);
    try {
      const latestLoan = await refreshLoan(conversationId);
      await refreshMessages(conversationId);
      const currentStatus = (latestLoan?.stpProcessingStatus || '').toLowerCase();
      if (['awaiting_acceptance', 'completed', 'processing'].includes(currentStatus)) return;
      const res = await fetch(`http://localhost:8000/api/loans/${loan.id}/stp-process`, {
        method: 'POST',
        headers: { 'X-Conversation-ID': conversationId },
      });
      if (!res.ok) {
        const raw = await res.text().catch(() => '');
        setStpError(raw ? `STP failed: ${raw}` : `STP failed (${res.status}).`);
        await refreshLoan(conversationId);
        await refreshMessages(conversationId);
        return;
      }
      await refreshLoan(conversationId);
      await refreshMessages(conversationId);
    } catch {
      setStpError('STP failed due to a network error.');
    } finally {
      setStpBusy(false);
    }
  };

  const bubbleClassForRole = useMemo(() => {
    return {
      user:
        'glass-bubble-user ml-auto max-w-[85%] rounded-3xl rounded-br-lg px-4 py-3 text-sm leading-relaxed text-white bg-gradient-to-r from-blue-600 to-indigo-600 shadow-lg shadow-blue-600/20 dark:shadow-blue-900/40',
      assistant:
        'glass-bubble-bot max-w-[85%] rounded-3xl rounded-bl-lg px-4 py-3 text-sm leading-relaxed bg-white dark:bg-white/[0.05] border border-slate-200/60 dark:border-white/[0.06] text-slate-800 dark:text-slate-200 shadow-sm',
    } as const;
  }, []);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto px-4 md:px-0 relative z-10" ref={scrollRef}>
        <div className="max-w-2xl mx-auto py-6 space-y-0">
          {bootstrapping ? (
            <div className="space-y-4">
              <div className="flex gap-3">
                <div className="w-9 h-9 rounded-2xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                <div className="space-y-2">
                  <div className="h-20 w-72 rounded-3xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                </div>
              </div>
            </div>
          ) : viewState === 'welcome' || viewState === 'exiting' ? (
            <div className={`${viewState === 'exiting' ? 'anim-welcome-exit' : ''}`}>
              <div className="anim-float-in">
                <div className="rounded-3xl bg-white/95 dark:bg-[#151520]/80 backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-xl shadow-black/[0.04] dark:shadow-black/40 p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-2xl font-extrabold tracking-tight text-[#1B2A4A] dark:text-white" data-testid="borrower-greeting">
                        {greeting}
                      </h2>
                      <p className="text-sm text-[#1B2A4A]/55 dark:text-white/55 mt-1" data-testid="borrower-greeting-subtitle">
                        How can I help you today?
                      </p>
                    </div>
                    <div className="w-11 h-11 rounded-2xl bg-slate-100 dark:bg-white/10 flex items-center justify-center shrink-0">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500 dark:text-slate-300">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                      </svg>
                    </div>
                  </div>

                  <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {[
                      {
                        title: 'Home Loan',
                        prompt: 'I want a home loan to buy a house.',
                        description: 'Purchase, refinance, construction, or equity release.',
                        icon: '🏠',
                        gradient: 'from-[#0078D4] to-[#005EA6]',
                        chip: 'Most common',
                      },
                      {
                        title: 'Car Loan',
                        prompt: 'I need a car loan for a vehicle purchase.',
                        description: 'New or used vehicles with flexible tenure options.',
                        icon: '🚗',
                        gradient: 'from-[#1B2A4A] to-[#111827]',
                        chip: 'Fast approval',
                      },
                      {
                        title: 'Personal Loan',
                        prompt: 'I need a personal loan for an urgent expense.',
                        description: 'Emergency funds, medical, travel, or home improvements.',
                        icon: '💳',
                        gradient: 'from-[#0078D4] to-[#1B2A4A]',
                        chip: 'Flexible',
                      },
                      {
                        title: 'Debt Consolidation',
                        prompt: 'I want to consolidate multiple debts into one EMI.',
                        description: 'Combine payments and reduce monthly burden.',
                        icon: '🧾',
                        gradient: 'from-[#005EA6] to-[#003a69]',
                        chip: 'Lower stress',
                      },
                    ].map((c) => (
                      <button
                        key={c.title}
                        type="button"
                        disabled={loading}
                        onClick={() => {
                          void handleSend(c.prompt);
                        }}
                        className="group relative overflow-hidden rounded-3xl border border-gray-200/60 dark:border-white/[0.08] bg-white/80 dark:bg-white/[0.05] p-6 text-left shadow-sm hover:shadow-xl hover:scale-[1.01] transition-all duration-500"
                        data-testid={`borrower-quickstart-${c.title.toLowerCase().replace(/\s+/g, '-')}`}
                      >
                        <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl ${c.gradient} opacity-[0.12] dark:opacity-[0.10] rounded-bl-full`} />
                        <div className="relative">
                          <div className="flex items-start justify-between gap-3">
                            <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${c.gradient} flex items-center justify-center text-white text-xl shadow-lg`}>
                              {c.icon}
                            </div>
                            <div className="px-2 py-1 rounded-full bg-[#D6E4F0]/70 dark:bg-[#0078D4]/[0.14] border border-[#0078D4]/15 dark:border-[#0078D4]/20 text-[10px] font-bold text-[#0078D4] dark:text-[#4da3e8]">
                              {c.chip}
                            </div>
                          </div>
                          <div className="mt-4">
                            <div className="text-base font-extrabold text-[#1B2A4A] dark:text-white">{c.title}</div>
                            <div className="mt-1 text-sm text-[#1B2A4A]/55 dark:text-white/55 leading-relaxed">{c.description}</div>
                          </div>
                          <div className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-[#0078D4] dark:text-[#4da3e8]">
                            Get started <span className="translate-y-[1px]">→</span>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : messages.length === 0 && loading ? (
            <div className="space-y-4 anim-chat-enter">
              <div className="flex gap-3">
                <div className="w-9 h-9 rounded-2xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                <div className="space-y-2">
                  <div className="h-20 w-72 rounded-3xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                </div>
              </div>
            </div>
          ) : (
            <div className="anim-chat-enter space-y-4">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className="max-w-[85%]">
                    <div data-testid={`chat-message-${msg.role}`} className={`chat-message-content ${msg.role === 'user' ? bubbleClassForRole.user : bubbleClassForRole.assistant}`}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                    {msg.role === 'assistant' ? (() => {
                      const loanApp = getLoanApplicationMeta(msg.metadata);
                      if (!loanApp) return null;
                      if (loanApp.awaitingAcceptance)
                        return (
                          <StpOfferCard
                            loanApplication={loanApp}
                            conversationId={conversationId}
                            loanId={loan?.id}
                            onAccepted={async () => {
                              if (!conversationId) return;
                              await refreshLoan(conversationId);
                              await refreshMessages(conversationId);
                            }}
                          />
                        );
                      if (loanApp.stpCompleted && loanApp.disbursement) return <DisbursementConfirmationCard loanApplication={loanApp} />;
                      return null;
                    })() : null}
                  </div>
                </div>
              ))}
              {loading ? (
                <div className="flex justify-start">
                  <div className={bubbleClassForRole.assistant}>
                    <div className="flex gap-1.5 items-center">
                      <div className="w-1.5 h-1.5 bg-slate-400/70 dark:bg-slate-500 rounded-full" style={{ animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0s' }} />
                      <div className="w-1.5 h-1.5 bg-slate-400/70 dark:bg-slate-500 rounded-full" style={{ animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.16s' }} />
                      <div className="w-1.5 h-1.5 bg-slate-400/70 dark:bg-slate-500 rounded-full" style={{ animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.32s' }} />
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="glass-header relative z-10 border-t border-slate-200/40 dark:border-white/[0.04] p-4 bg-white/70 dark:bg-[#141414]/80 backdrop-blur-xl">
        <div className="max-w-2xl mx-auto">
          {viewState === 'chat' && conversationId && loan?.id && docsOpen ? (
            <div
              ref={docsPanelRef}
              className="mb-3 rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] p-3"
              data-testid="borrower-doc-upload-panel"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="text-xs font-extrabold tracking-tight text-slate-800 dark:text-slate-200">Your Documents</div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500">{loan?.catalogProductCode ? `Product: ${loan.catalogProductCode}` : ' '}</div>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  e.currentTarget.value = '';
                  void uploadUi2Document(f);
                }}
                data-testid="input-file-upload"
              />

              {ui2DocsError ? <div className="mt-2 text-[11px] text-red-600 dark:text-red-400">{ui2DocsError}</div> : null}
              {stpError ? <div className="mt-2 text-[11px] text-red-600 dark:text-red-400">{stpError}</div> : null}

              {(() => {
                const categories = getDocumentCategories(loan.loanType || '', loan.employmentType || '');
                const getDocsForType = (documentType: string) =>
                  ui2Docs.filter((d) => (d.documentType || '').toLowerCase() === documentType.toLowerCase());

                const totalRequired = categories.flatMap((c) => c.types.filter((t) => t.required)).length;
                const uploadedRequired = categories.flatMap((c) => c.types.filter((t) => t.required && getDocsForType(t.key).length > 0)).length;
                const progressPercent = totalRequired > 0 ? Math.round((uploadedRequired / totalRequired) * 100) : 0;
                const stpStatus = (loan.stpProcessingStatus || '').toLowerCase();
                const isStpReady = totalRequired > 0 && uploadedRequired >= totalRequired;
                const canRunStp = isStpReady && stpStatus !== 'awaiting_acceptance' && stpStatus !== 'completed' && !stpBusy;

                return (
                  <div className="mt-3 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="text-[11px] text-slate-500 dark:text-slate-400">
                        {uploadedRequired} of {totalRequired} required uploaded
                      </div>
                      <div className="text-[11px] font-extrabold text-blue-700 dark:text-blue-400">{progressPercent}%</div>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 dark:bg-white/[0.06] overflow-hidden">
                      <div className="h-full rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 transition-all" style={{ width: `${progressPercent}%` }} />
                    </div>

                    {ui2DocsLoading ? <div className="text-[11px] text-slate-500 dark:text-slate-400">Loading documents…</div> : null}
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-[11px] text-slate-500 dark:text-slate-400">
                        Automated checks: {stpStatus ? stpStatus.replaceAll('_', ' ') : 'not started'}
                      </div>
                      <button
                        type="button"
                        disabled={!canRunStp}
                        onClick={() => void runStp()}
                        className="rounded-xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.06] px-3 py-1.5 text-[11px] font-bold text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
                        data-testid="button-run-stp"
                      >
                        {stpBusy ? 'Running…' : 'Run Checks'}
                      </button>
                    </div>

                    {categories.map((cat) => {
                      const isExpanded = expandedCategory === cat.key;
                      return (
                        <div key={cat.key} className="rounded-xl border border-slate-200/60 dark:border-white/[0.06] bg-white/70 dark:bg-white/[0.03]">
                          <button
                            type="button"
                            onClick={() => setExpandedCategory((v) => (v === cat.key ? null : cat.key))}
                            className="w-full px-3 py-2 flex items-center justify-between"
                            data-testid={`button-doc-category-${cat.key}`}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <div className="text-sm">{cat.icon}</div>
                              <div className="text-xs font-extrabold tracking-tight text-slate-800 dark:text-slate-200 truncate">{cat.label}</div>
                            </div>
                            <div className="text-[11px] text-slate-400 dark:text-slate-500">{isExpanded ? 'Hide' : 'Show'}</div>
                          </button>

                          {!isExpanded ? null : (
                            <div className="px-3 pb-3 grid gap-2">
                              {cat.types.map((t) => {
                                const docsForType = getDocsForType(t.key);
                                const latest = docsForType[0] || null;
                                const status = latest?.status || (t.required ? 'missing' : 'optional');
                                const busy = uploadingType === t.key;
                                return (
                                  <div key={t.key} className="rounded-xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] px-3 py-2">
                                    <div className="flex items-start justify-between gap-3">
                                      <div className="min-w-0">
                                        <div className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">
                                          {t.label}
                                          {t.required ? <span className="ml-2 text-[10px] text-amber-700 dark:text-amber-400">Required</span> : null}
                                        </div>
                                        <div className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">Status: {status}</div>
                                      </div>
                                      <div className="shrink-0 flex items-center gap-2">
                                        <button
                                          type="button"
                                          disabled={busy || loading || bootstrapping}
                                          onClick={() => triggerUi2Upload(cat.key, t.key)}
                                          className="rounded-lg border border-slate-200/60 dark:border-white/[0.06] bg-white/90 dark:bg-white/[0.06] px-2 py-1 text-[10px] font-bold text-slate-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
                                          data-testid={`button-doc-upload-${cat.key}-${t.key}`}
                                        >
                                          Upload
                                        </button>
                                      </div>
                                    </div>

                                    {docsForType.length > 0 ? (
                                      <div className="mt-2 grid gap-1">
                                        {docsForType.slice(0, 3).map((d) => (
                                          <div key={d.id} className="flex items-center justify-between gap-2 text-[11px] text-slate-600 dark:text-slate-300">
                                            <div className="min-w-0 truncate">{d.originalName || d.fileName || 'document'}</div>
                                            <div className="shrink-0 flex items-center gap-2">
                                              <button
                                                type="button"
                                                onClick={() => void downloadUi2Document(d.id, d.originalName || d.fileName || 'document')}
                                                className="text-[11px] font-bold text-blue-700 dark:text-blue-400"
                                                data-testid={`button-doc-download-${d.id}`}
                                              >
                                                Download
                                              </button>
                                              <button
                                                type="button"
                                                onClick={() => void deleteUi2Document(d.id)}
                                                className="text-[11px] font-bold text-red-700 dark:text-red-400"
                                                data-testid={`button-doc-delete-${d.id}`}
                                              >
                                                Delete
                                              </button>
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    ) : null}

                                    {busy ? <div className="mt-2 text-[10px] text-slate-400 dark:text-slate-500">Uploading…</div> : null}
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
            </div>
          ) : null}

          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                data-testid="input-chat-message"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    void handleSend(input);
                  }
                }}
                placeholder={viewState === 'welcome' ? "Tell me what you're looking for..." : 'Type your message...'}
                disabled={loading || bootstrapping}
                rows={1}
                className="glass-input w-full resize-none rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.04] px-4 py-3 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-400/30 focus:border-blue-300 dark:focus:border-blue-500/30 transition-all placeholder:text-slate-400 dark:placeholder:text-slate-500 disabled:opacity-50 shadow-sm"
                style={{ minHeight: '48px', maxHeight: '120px' }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = '48px';
                  target.style.height = Math.min(target.scrollHeight, 120) + 'px';
                }}
              />
            </div>

            <button
              type="button"
              onClick={() => {
                setDocsOpen(true);
                setTimeout(() => docsPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
              }}
              disabled={viewState !== 'chat' || bootstrapping}
              className="rounded-2xl h-12 w-12 bg-white/90 dark:bg-white/[0.06] hover:bg-slate-50 dark:hover:bg-white/[0.09] text-slate-700 dark:text-slate-200 shadow-sm transition-all duration-200 border border-slate-200/60 dark:border-white/[0.06] disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
              aria-label="Attachments"
              data-testid="button-attachments"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.44 11.05 12.25 20.24a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
              </svg>
            </button>

            <button
              data-testid="button-send-message"
              type="button"
              onClick={() => void handleSend(input)}
              disabled={!canSend}
              className="rounded-2xl h-12 w-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg shadow-blue-600/20 dark:shadow-blue-900/40 transition-all duration-200 border-0 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
              aria-label="Send"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
          <p className="text-[10px] text-slate-400 dark:text-slate-500 text-center mt-2.5">
            AI-powered recommendations are estimates. Final terms subject to verification.
          </p>
        </div>
      </div>
    </div>
  );
};
