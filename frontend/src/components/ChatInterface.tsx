import React, { useCallback, useMemo, useRef, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import * as Dialog from '@radix-ui/react-dialog';
import { LoanSnapshotCard } from './LoanSnapshotCard';
import { LoanCard } from './LoanCard';
import { DocumentsCard } from './DocumentsCard';
import { StpProcessingCard, AffordabilityCard } from './StpCards';

interface Props {
  onConversationUpdated?: (conversation: V2Conversation) => void;
  onPhasesUpdated?: (phases: V2Phase[]) => void;
  onMessagesUpdated?: (messages: V2Message[]) => void;
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

export type V2Message = {
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
  meta?: unknown;
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
  const meta = parseMetadata(metadata);
  if (!meta) return null;
  const laRaw = meta.loanApplication;
  const la = laRaw && typeof laRaw === 'object' ? (laRaw as Record<string, unknown>) : null;
  if (!la) return null;
  const merged: Record<string, unknown> = { ...la };
  if (typeof merged.awaitingAcceptance !== 'boolean' && typeof meta.awaitingAcceptance === 'boolean') {
    merged.awaitingAcceptance = meta.awaitingAcceptance;
  }
  if (typeof merged.stpCompleted !== 'boolean' && typeof meta.stpCompleted === 'boolean') {
    merged.stpCompleted = meta.stpCompleted;
  }
  if (typeof merged.stpApproved !== 'boolean' && typeof meta.stpApproved === 'boolean') {
    merged.stpApproved = meta.stpApproved;
  }
  if (typeof merged.loanId !== 'string' && typeof meta.loanId === 'string') {
    merged.loanId = meta.loanId;
  }
  if (typeof merged.success !== 'boolean' && typeof meta.success === 'boolean') {
    merged.success = meta.success;
  }
  return merged as V2LoanApplicationMeta;
};

const DisbursementConfirmationCard: React.FC<{ loanApplication: V2LoanApplicationMeta }> = ({ loanApplication }) => {
  const d = loanApplication.disbursement;
  if (!d || !loanApplication.stpCompleted) return null;
  const a = loanApplication.approval;
  const approvalRaw = a && typeof a === 'object' ? (a as unknown as Record<string, unknown>) : null;
  const approval = approvalRaw
    ? {
        rate: approvalRaw.rate ?? approvalRaw.interest_rate ?? approvalRaw.interestRate,
        tenure: approvalRaw.tenure ?? approvalRaw.tenure_years ?? approvalRaw.tenureYears,
        emi: approvalRaw.emi ?? approvalRaw.monthly_emi ?? approvalRaw.monthlyEmi,
      }
    : null;
  const showTerm = (v: unknown) => {
    if (typeof v === 'number') return v > 0 ? String(v) : 'N/A';
    if (typeof v !== 'string') return 'N/A';
    const t = v.trim();
    if (!t) return 'N/A';
    const digits = t.replace(/[^\d.]/g, '');
    if (digits && Number(digits) === 0) return 'N/A';
    return t;
  };
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

        {approval ? (
          <div className="border-t border-slate-100 dark:border-white/[0.04]">
            <div className="px-4 py-2 bg-slate-50/80 dark:bg-white/[0.02] border-b border-slate-100 dark:border-white/[0.04]">
              <div className="text-[10px] font-extrabold text-slate-700 dark:text-slate-300 uppercase tracking-wider">Approved Loan Terms</div>
            </div>
            <div className="grid grid-cols-3 divide-x divide-slate-100 dark:divide-white/[0.04]">
              <div className="p-3 text-center">
                <div className="text-[9px] text-slate-500 dark:text-slate-400">Rate</div>
                <div className="mt-0.5 text-xs font-extrabold text-slate-800 dark:text-slate-200">{showTerm(approval.rate)}</div>
              </div>
              <div className="p-3 text-center">
                <div className="text-[9px] text-slate-500 dark:text-slate-400">Tenure</div>
                <div className="mt-0.5 text-xs font-extrabold text-slate-800 dark:text-slate-200">{showTerm(approval.tenure)}</div>
              </div>
              <div className="p-3 text-center">
                <div className="text-[9px] text-slate-500 dark:text-slate-400">Monthly EMI</div>
                <div className="mt-0.5 text-xs font-extrabold text-slate-800 dark:text-slate-200">{showTerm(approval.emi)}</div>
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
  const a = loanApplication.approval;
  const steps = Array.isArray(loanApplication.stpSteps) ? loanApplication.stpSteps : [];
  const approvalRaw = a && typeof a === 'object' ? (a as unknown as Record<string, unknown>) : null;
  const approval = approvalRaw
    ? {
        rate: approvalRaw.rate ?? approvalRaw.interest_rate ?? approvalRaw.interestRate,
        tenure: approvalRaw.tenure ?? approvalRaw.tenure_years ?? approvalRaw.tenureYears,
        emi: approvalRaw.emi ?? approvalRaw.monthly_emi ?? approvalRaw.monthlyEmi,
        conditions: approvalRaw.conditions,
      }
    : null;
  const conditions = Array.isArray(approval?.conditions) ? approval.conditions : [];
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

  if (!loanApplication.awaitingAcceptance || !approval) return null;

  const showTerm = (v: unknown) => {
    if (typeof v === 'number') return v > 0 ? String(v) : '—';
    if (typeof v !== 'string') return '—';
    const t = v.trim();
    if (!t) return '—';
    const digits = t.replace(/[^\d.]/g, '');
    if (digits && Number(digits) === 0) return '—';
    return t;
  };

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
                {showTerm(approval.rate)}
              </div>
            </div>
            <div className="rounded-xl bg-white/[0.08] px-3 py-2 text-center">
              <div className="text-[9px] text-white/45 uppercase tracking-wider">Tenure</div>
              <div className="mt-0.5 text-xs font-extrabold text-white" data-testid="text-offer-tenure">
                {showTerm(approval.tenure)}
              </div>
            </div>
            <div className="rounded-xl bg-white/[0.08] px-3 py-2 text-center">
              <div className="text-[9px] text-white/45 uppercase tracking-wider">Monthly EMI</div>
              <div className="mt-0.5 text-xs font-extrabold text-white" data-testid="text-offer-emi">
                {showTerm(approval.emi)}
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
              <div className="text-xs font-extrabold tracking-tight text-slate-800 dark:text-slate-200">Accept Loan Terms</div>
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

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');

const asRecord = (value: unknown): Record<string, unknown> | null =>
  typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null;

const parseMetadata = (value: unknown): Record<string, unknown> | null => {
  if (typeof value === 'string') {
    try {
      return asRecord(JSON.parse(value));
    } catch {
      return null;
    }
  }
  return asRecord(value);
};

const getActorRole = (metadata: unknown): string | null => {
  if (!metadata || typeof metadata !== 'object') return null;
  const role = (metadata as { actorRole?: unknown }).actorRole;
  return typeof role === 'string' ? role : null;
};

const isOfficerOnlyMessage = (message: V2Message): boolean => {
  const actorRole = getActorRole(message.metadata);
  return actorRole === 'officer' || actorRole === 'officer_assistant';
};

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

export const ChatInterface: React.FC<Props> = ({ onConversationUpdated, onPhasesUpdated, onMessagesUpdated, resetSignal }) => {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversation, setConversation] = useState<V2Conversation | null>(null);
  const [messages, setMessages] = useState<V2Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [viewState, setViewState] = useState<ViewState>('welcome');
  const [loan, setLoan] = useState<V2Loan | null>(null);
  const [ui2Docs, setUi2Docs] = useState<V2LoanDocument[]>([]);
  const [uploadingType, setUploadingType] = useState<string | null>(null);
  const [uploadingChecklistName, setUploadingChecklistName] = useState<string | null>(null);
  const [dismissedDocPromptId, setDismissedDocPromptId] = useState<string | null>(null);
  const [ocrProcessing, setOcrProcessing] = useState<{ title: string; documentType: string; startedAt: number } | null>(null);
  const [docPreviewOpen, setDocPreviewOpen] = useState(false);
  const [docPreview, setDocPreview] = useState<{
    title: string;
    status: 'ok' | 'error' | 'none';
    error?: string;
    textPreview?: string;
    fields?: Record<string, unknown>;
  } | null>(null);
  const [lastExtraction, setLastExtraction] = useState<{
    title: string;
    documentType: string;
    status: 'ok' | 'error' | 'none';
    error?: string;
    textPreview?: string;
    fields?: Record<string, unknown>;
  } | null>(null);
  /* removed STP panel state */

  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const requestGenRef = useRef(0);
  const sendLockRef = useRef(false);
  const exitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  /* removed documents panel ref */
  const ocrFileInputRef = useRef<HTMLInputElement>(null);
  const pendingUploadRef = useRef<{ category: string; documentType: string } | null>(null);
  const pendingChecklistNameRef = useRef<string | null>(null);
  const autoDocsOpenedRef = useRef(false);

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 18) return 'Good Afternoon';
    return 'Good Evening';
  }, []);

  const lastAssistantMessageId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m?.role === 'assistant') return m.id;
    }
    return null;
  }, [messages]);

  const nextRequiredDoc = useMemo(() => {
    if (!loan) return null;
    const categories = getDocumentCategories(loan.loanType || '', loan.employmentType || '');
    const getDocsForType = (documentType: string) =>
      ui2Docs.filter((d) => (d.documentType || '').toLowerCase() === documentType.toLowerCase());

    for (const cat of categories) {
      for (const t of cat.types) {
        if (!t.required) continue;
        if (getDocsForType(t.key).length === 0) {
          return { categoryKey: cat.key, documentType: t.key, label: t.label };
        }
      }
    }
    return null;
  }, [loan, ui2Docs]);

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    // Only scroll if user is already near bottom (within 100px)
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    if (isNearBottom || loading) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    }
  }, [loading]);

  // Scroll only on new messages, not on every update
  useEffect(() => {
    scrollToBottom();
  }, [messages.length, scrollToBottom]);

  useEffect(() => {
    autoDocsOpenedRef.current = false;
  }, [conversationId]);

  const refreshLoan = async (activeConversationId: string): Promise<V2Loan | null> => {
    try {
      const res = await fetch(`http://localhost:8000/api/v3/conversations/${activeConversationId}/loan`);
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
      const res = await fetch(`http://localhost:8000/api/v3/conversations/${activeConversationId}/messages`);
      if (!res.ok) return;
      const next = (await res.json()) as V2Message[];
      setMessages(next.filter((m) => !isOfficerOnlyMessage(m)));
    } catch (e) {
      console.error(e);
    }
  };

  const refreshUi2Docs = async (activeConversationId: string, activeLoanId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/documents/loan/${activeLoanId}`, {
        headers: { 'X-Conversation-ID': activeConversationId },
      });
      if (!res.ok) {
        setUi2Docs([]);
        return null;
      }
      const next = (await res.json()) as V2LoanDocument[];
      setUi2Docs(next);
      return next;
    } catch {
      setUi2Docs([]);
      return null;
    }
  };

  useEffect(() => {
    if (!conversationId || !loan?.id) return;
    void refreshUi2Docs(conversationId, loan.id);
  }, [conversationId, loan?.id]);

  const triggerInlineUi2Upload = (category: string, documentType: string) => {
    pendingChecklistNameRef.current = null;
    pendingUploadRef.current = { category, documentType };
    ocrFileInputRef.current?.click();
  };

  const normalizeDocumentType = (name: string) => {
    const s = (name || '').trim().toLowerCase();
    if (!s) return 'document';
    return s.replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 64) || 'document';
  };

  const inferDocumentCategory = (name: string) => {
    const s = (name || '').toLowerCase();
    if (/(pan|aadhaar|aadhar|passport|national id|driver|license|licence|id card)/i.test(s)) return 'identity';
    if (/(salary|pay\\s*slip|payslip|pay slip|bank\\s*statement|statement)/i.test(s)) return 'income';
    if (/(property|title|valuation|deed)/i.test(s)) return 'property';
    if (/(vehicle|registration|invoice|dealer)/i.test(s)) return 'vehicle';
    return 'other';
  };

  const triggerChecklistUpload = (docName: string) => {
    const category = inferDocumentCategory(docName);
    const documentType = normalizeDocumentType(docName);
    pendingChecklistNameRef.current = docName;
    pendingUploadRef.current = { category, documentType };
    const el = ocrFileInputRef.current;
    if (el) {
      el.dataset.docName = docName;
      el.click();
      return;
    }
    ocrFileInputRef.current?.click();
  };

  const getDocExtraction = (doc: V2LoanDocument) => {
    type ExtractionStatus = 'ok' | 'error' | 'none';
    const meta = doc.meta && typeof doc.meta === 'object' ? (doc.meta as Record<string, unknown>) : null;
    const extraction = meta?.extraction && typeof meta.extraction === 'object' ? (meta.extraction as Record<string, unknown>) : null;
    const statusRaw = typeof extraction?.status === 'string' ? extraction.status : 'none';
    const status: ExtractionStatus = statusRaw === 'ok' || statusRaw === 'error' ? statusRaw : 'none';
    const textPreview = typeof extraction?.textPreview === 'string' ? extraction.textPreview : undefined;
    const error = typeof extraction?.error === 'string' ? extraction.error : undefined;
    const fields = extraction?.fields && typeof extraction.fields === 'object' ? (extraction.fields as Record<string, unknown>) : undefined;
    return { status, textPreview, error, fields };
  };

  const openDocPreview = (doc: V2LoanDocument) => {
    const title = doc.originalName || doc.fileName || 'document';
    const ex = getDocExtraction(doc);
    setDocPreview({
      title,
      status: ex.status,
      error: ex.error,
      textPreview: ex.textPreview,
      fields: ex.fields,
    });
    setDocPreviewOpen(true);
  };

  const openLastExtractionPreview = () => {
    if (!lastExtraction) return;
    setDocPreview({
      title: lastExtraction.title,
      status: lastExtraction.status,
      error: lastExtraction.error,
      textPreview: lastExtraction.textPreview,
      fields: lastExtraction.fields,
    });
    setDocPreviewOpen(true);
  };

  const uploadUi2Document = async (file: File) => {
    if (!conversationId || !loan?.id) return;
    const pending = pendingUploadRef.current;
    if (!pending) return;
    setLastExtraction(null);
    const checklistName = pendingChecklistNameRef.current;
    if (checklistName) setUploadingChecklistName(checklistName);
    setUploadingType(pending.documentType);
    setOcrProcessing({ title: file.name, documentType: pending.documentType, startedAt: Date.now() });
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
      if (!res.ok) return;
      const created = (await res.json().catch(() => null)) as V2LoanDocument | null;
      const nextDocs = await refreshUi2Docs(conversationId, loan.id);
      await refreshLoan(conversationId);
      await refreshMessages(conversationId);
      if (created && created.id) {
        const best = nextDocs?.find((d) => d.id === created.id) ?? created;
        const dt = (pending.documentType || '').toLowerCase();
        const shouldShowExtraction = dt.includes('id') || dt.includes('passport') || dt.includes('national') || dt.includes('job') || dt.includes('employment');
        if (shouldShowExtraction) {
          const title = best.originalName || best.fileName || 'document';
          let ex = getDocExtraction(best);
          setLastExtraction({
            title,
            documentType: pending.documentType,
            status: ex.status,
            error: ex.error,
            textPreview: ex.textPreview,
            fields: ex.fields,
          });
          const startedAt = Date.now();
          for (let i = 0; i < 30; i++) {
            if (Date.now() - startedAt > 30000) break;
            if (ex.status === 'ok' || ex.status === 'error') break;
            await new Promise((r) => setTimeout(r, 1000));
            const polled = await refreshUi2Docs(conversationId, loan.id);
            const latest = polled?.find((d) => d.id === created.id) ?? null;
            if (!latest) continue;
            const nextEx = getDocExtraction(latest);
            ex = nextEx;
            if (nextEx.status !== 'none') {
              setLastExtraction({
                title,
                documentType: pending.documentType,
                status: nextEx.status,
                error: nextEx.error,
                textPreview: nextEx.textPreview,
                fields: nextEx.fields,
              });
              break;
            }
          }
        }
      }
    } catch {
      /* no-op */
    } finally {
      setUploadingType(null);
      setUploadingChecklistName(null);
      pendingUploadRef.current = null;
      pendingChecklistNameRef.current = null;
      setOcrProcessing(null);
    }
  };

  /* removed panel-specific delete/download helpers */

  useEffect(() => {
    onMessagesUpdated?.(messages.filter((m) => !isOfficerOnlyMessage(m)));
  }, [messages, onMessagesUpdated]);

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
      setUi2Docs([]);
      if (typeof resetSignal === 'number') {
        window.localStorage.removeItem(STORAGE_KEY);
      }

      const storedId = window.localStorage.getItem(STORAGE_KEY);
      const activeConversationId: string | null = storedId || null;

      if (!activeConversationId) {
        setConversationId(null);
        setConversation(null);
        setMessages([]);
        setLoan(null);
        setUi2Docs([]);
        setViewState('welcome');
        setBootstrapping(false);
        return;
      }

      const phasesRes = await fetchJson<V2Phase[]>(`${API_BASE_URL}/api/phases/active`);
      if (phasesRes.ok) {
        onPhasesUpdated?.(phasesRes.value);
      }

      const existing = await fetchJson<V2Conversation>(`${API_BASE_URL}/api/v3/conversations/${activeConversationId}`);
      if (!existing.ok) {
        window.localStorage.removeItem(STORAGE_KEY);
        setConversationId(null);
        setConversation(null);
        setMessages([]);
        setLoan(null);
        setUi2Docs([]);
        setViewState('welcome');
        setBootstrapping(false);
        return;
      }

      onConversationUpdated?.(existing.value);
      setConversation(existing.value);
      setConversationId(activeConversationId);
      setViewState('chat');
      void refreshLoan(activeConversationId);

      const msgsRes = await fetchJson<V2Message[]>(`${API_BASE_URL}/api/v3/conversations/${activeConversationId}/messages`);
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
      const res = await fetch(`${API_BASE_URL}/api/v3/conversations/${activeConversationId}/messages`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-idempotency-key': userMsg.id },
        body: JSON.stringify({ content }),
      });

      if (!res.ok) {
        const raw = await res.text().catch(() => '');
        let detail = raw;
        try {
          const parsed = JSON.parse(raw) as { detail?: unknown };
          if (typeof parsed?.detail === 'string') detail = parsed.detail;
        } catch {
          detail = raw;
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

      const refreshed = await fetch(`${API_BASE_URL}/api/v3/conversations/${activeConversationId}`);
      if (refreshed.ok) {
        const nextConversation = (await refreshed.json()) as V2Conversation;
        onConversationUpdated?.(nextConversation);
        setConversation(nextConversation);
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
      const createRes = await fetch(`${API_BASE_URL}/api/v3/conversations`, {
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
      setConversation(created);
      setConversation(created);
      void refreshLoan(created.id);

      const phasesRes = await fetch(`${API_BASE_URL}/api/phases/active`);
      if (phasesRes.ok) {
        const phasesData = await phasesRes.json();
        onPhasesUpdated?.(phasesData);
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
    if (sendLockRef.current) return;
    sendLockRef.current = true;
    if (!conversationId) {
      try {
        await startConversationAndSend(content);
      } finally {
        sendLockRef.current = false;
      }
      return;
    }
    try {
      if (viewState !== 'chat') setViewState('chat');
      await sendToExisting(conversationId, content);
    } finally {
      sendLockRef.current = false;
    }
  };

  const canSend = input.trim().length > 0 && !loading && !bootstrapping && uploadingType === null && !ocrProcessing;

  const bubbleClassForRole = useMemo(() => {
    return {
      user:
        'glass-bubble-user ml-auto max-w-[85%] rounded-3xl rounded-br-lg px-4 py-3 text-sm leading-relaxed text-white bg-gradient-to-r from-blue-600 to-indigo-600 shadow-lg shadow-blue-600/20 dark:shadow-blue-900/40',
      assistant:
        'glass-bubble-bot max-w-[85%] rounded-3xl rounded-bl-lg px-4 py-3 text-sm leading-relaxed bg-white dark:bg-white/[0.05] border border-slate-200/60 dark:border-white/[0.06] text-slate-800 dark:text-slate-200 shadow-sm',
    } as const;
  }, []);

  const selectedPlanType = useMemo(() => {
    const intent = asRecord(conversation?.intentSummary);
    const selected = intent?.selectedPlan;
    if (typeof selected !== 'string') return null;
    const v = selected.trim().toLowerCase();
    return v === 'aggressive' || v === 'balanced' || v === 'conservative' ? v : null;
  }, [conversation?.intentSummary]);

  const isLoanSnapshot = (value: unknown): value is {
    loan_amount: number;
    down_payment: number;
    property_value: number;
    estimated_emi: number;
    tenure_years: number;
    interest_rate: number;
    total_interest: number;
    total_repayment: number;
    ltv_ratio: number;
    foir_ratio?: number;
    currency: string;
  } => {
    const snap = asRecord(value);
    if (!snap) return false;
    if (typeof snap.loan_amount !== 'number') return false;
    if (typeof snap.down_payment !== 'number') return false;
    if (typeof snap.property_value !== 'number') return false;
    if (typeof snap.estimated_emi !== 'number') return false;
    if (typeof snap.tenure_years !== 'number') return false;
    if (typeof snap.interest_rate !== 'number') return false;
    if (typeof snap.total_interest !== 'number') return false;
    if (typeof snap.total_repayment !== 'number') return false;
    if (typeof snap.ltv_ratio !== 'number') return false;
    if (typeof snap.currency !== 'string') return false;
    if (snap.foir_ratio !== undefined && typeof snap.foir_ratio !== 'number') return false;
    return true;
  };

  const isDocumentsChecklist = (value: unknown): value is {
    identity: Array<{ name: string; status: 'required' | 'optional'; description: string; uploaded?: boolean }>;
    income: Array<{ name: string; status: 'required' | 'optional'; description: string; uploaded?: boolean }>;
    business?: Array<{ name: string; status: 'required' | 'optional'; description: string; uploaded?: boolean }>;
    property?: Array<{ name: string; status: 'required' | 'optional'; description: string; uploaded?: boolean }>;
    vehicle?: Array<{ name: string; status: 'required' | 'optional'; description: string; uploaded?: boolean }>;
  } => {
    const checklist = asRecord(value);
    if (!checklist) return false;
    if (!Array.isArray(checklist.identity) || !Array.isArray(checklist.income)) return false;
    return true;
  };

  // Parse LNAI-style document_request XML tags from message content
  const parseDocumentRequests = (content: string): Array<{ type: string; label: string }> => {
    const requests: Array<{ type: string; label: string }> = [];
    const pattern = /<document_request\s+type=["']([^"']+)["']>([^<]+)<\/document_request>/gi;
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(content)) !== null) {
      requests.push({
        type: match[1].trim(),
        label: match[2].trim(),
      });
    }
    return requests;
  };

  // Strip XML tags from message content for clean display
  const stripXmlTags = (content: string): string => {
    if (!content) return content;
    // Remove XML tags with their content
    let cleaned = content.replace(/<loan_snapshot>[\s\S]*?<\/loan_snapshot>/gi, '');
    cleaned = cleaned.replace(/<loan_recommendation[^>]*>[\s\S]*?<\/loan_recommendation>/gi, '');
    cleaned = cleaned.replace(/<document_request[^>]*>[\s\S]*?<\/document_request>/gi, '');
    cleaned = cleaned.replace(/<documents_checklist>[\s\S]*?<\/documents_checklist>/gi, '');
    cleaned = cleaned.replace(/<stp_processing>[\s\S]*?<\/stp_processing>/gi, '');
    cleaned = cleaned.replace(/<terms_acceptance>[\s\S]*?<\/terms_acceptance>/gi, '');
    // Remove any remaining standalone XML tags
    cleaned = cleaned.replace(/<\/?[a-z][a-z0-9_-]*[^>]*\s*\/?>/gi, '');
    // Clean up extra whitespace and newlines
    cleaned = cleaned.replace(/\n\s*\n/g, '\n').replace(/\s+/g, ' ').trim();
    return cleaned;
  };

  const renderCardsForMessage = (msg: V2Message) => {
    const metadata = parseMetadata(msg.metadata);
    if (!metadata) return null;
    const cards: React.ReactNode[] = [];

    // Check for loan recommendations in multiple possible locations
    let loanRecommendations = Array.isArray(metadata.loanRecommendations) ? metadata.loanRecommendations : null;
    
    // Also check intentAnalysis for recommendations (LOS structure)
    if (!loanRecommendations) {
      const intentAnalysis = asRecord(metadata.intentAnalysis);
      if (intentAnalysis) {
        const intentSummary = asRecord(intentAnalysis.intentSummary);
        if (intentSummary && Array.isArray(intentSummary.recommendedProducts)) {
          loanRecommendations = intentSummary.recommendedProducts;
        }
      }
    }

    // Loan Snapshot Card - Show when we have snapshot data
    if (isLoanSnapshot(metadata.loanSnapshot)) {
      cards.push(<LoanSnapshotCard key="snapshot" snapshot={metadata.loanSnapshot} />);
    }

    // Loan Recommendations Cards - ALWAYS show when we have recommendations
    // Don't wait for user to be "ready" - show them as soon as data exists
    if (Array.isArray(loanRecommendations) && loanRecommendations.length > 0 && !metadata.selectedRecommendation) {
      const recs = loanRecommendations
        .map((rec) => {
          const r = asRecord(rec);
          if (!r) return null;
          const tenureRaw = r.tenure_years ?? r.tenureYears ?? r.maxTenureMonths ?? 240;
          const tenureNum = Number(tenureRaw);
          const tenureYears = Number.isFinite(tenureNum) ? (tenureNum > 60 ? tenureNum / 12 : tenureNum) : 0;
          const typeRaw = String(r.type || r.category || 'balanced').toLowerCase();
          const planType: 'aggressive' | 'balanced' | 'conservative' = (typeRaw.includes('aggressive') || typeRaw.includes('fast'))
            ? 'aggressive'
            : (typeRaw.includes('conservative') || typeRaw.includes('comfort'))
              ? 'conservative'
              : 'balanced';
          // Normalize LOS backend structure to expected format
          return {
            name: String(r.name || r.estimatedRate || 'Option'),
            type: planType,
            interest_rate: Number(r.interest_rate || r.baseInterestRate || 8.4),
            tenure_years: tenureYears,
            monthly_emi: Number(r.monthly_emi || r.estimatedEmi || 0),
            total_interest: Number(r.total_interest || 0),
            total_repayment: Number(r.total_repayment || 0),
            pros: Array.isArray(r.pros) ? r.pros : [String(r.approvalSpeed || 'Standard')],
            cons: Array.isArray(r.cons) ? r.cons : [String(r.prepaymentPenalty || 'Varies')],
            recommended: Boolean(r.recommended || false),
          };
        })
        .filter((rec): rec is NonNullable<typeof rec> => rec !== null);

      if (recs.length > 0) {
        cards.push(
          <div key="recs" className="w-full space-y-3 mt-1">
            <div className="flex items-center gap-2 text-xs font-medium text-[#0078D4] pl-1">
              <span>Recommended Options</span>
              <div className="flex-1 h-px bg-gradient-to-r from-[#0078D4]/30 to-transparent" />
            </div>
            <p className="text-[11px] text-[#1B2A4A]/50 dark:text-white/45 pl-1">Tap a card to select your preferred option</p>
            <div className="grid gap-3">
              {recs.map((rec, idx) => (
                <LoanCard
                  key={`rec-${rec.type}-${idx}`}
                  recommendation={rec}
                  selected={selectedPlanType === rec.type}
                  onSelect={(selected) => {
                    void handleSend(`I prefer the ${selected.name}`);
                  }}
                  disabled={msg.role !== 'assistant'}
                />
              ))}
            </div>
          </div>
        );
      }
    }

    // Documents Checklist Card
    if (isDocumentsChecklist(metadata.documentsChecklist)) {
      cards.push(
        <DocumentsCard
          key="documents"
          checklist={metadata.documentsChecklist}
          collapsible={true}
          defaultOpen={false}
          busyDocumentName={uploadingChecklistName}
          disableUpload={bootstrapping || loading || uploadingChecklistName !== null || uploadingType !== null || ocrProcessing !== null}
          onUpload={(docName) => triggerChecklistUpload(docName)}
        />
      );
    }

    // LNAI-style Document Request Cards (from XML tags)
    const docRequests = parseDocumentRequests(msg.content || '');
    if (docRequests.length > 0 && msg.role === 'assistant') {
      cards.push(
        <div key={`doc-requests-${msg.id}`} className="my-3 space-y-2">
          {docRequests.map((req, idx) => (
            <div
              key={`${msg.id}-doc-req-${idx}`}
              data-testid={`lnai-document-request-${req.type}`}
              className="rounded-2xl border border-blue-200/60 dark:border-blue-500/20 bg-blue-50/80 dark:bg-blue-900/20 p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-blue-600 dark:bg-blue-500 flex items-center justify-center shrink-0">
                      <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div>
                      <div className="text-xs font-extrabold tracking-tight text-blue-900 dark:text-blue-200">Document Request</div>
                      <div className="text-sm font-semibold text-blue-950 dark:text-white truncate">{req.label}</div>
                    </div>
                  </div>
                  <div className="mt-2 text-[11px] text-blue-800/80 dark:text-blue-300/80">
                    Upload this document using the paperclip button below, or click Upload to select it now.
                  </div>
                </div>
                <button
                  type="button"
                  disabled={bootstrapping || loading || uploadingType !== null || ocrProcessing !== null}
                  onClick={() => {
                    const category = req.type === 'national_id' || req.type === 'passport' || req.type === 'id' ? 'identity' : 'income';
                    triggerInlineUi2Upload(category, req.type);
                  }}
                  className="shrink-0 rounded-xl bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 text-[11px] font-extrabold disabled:opacity-40 disabled:cursor-not-allowed"
                  data-testid={`button-lnai-upload-${req.type}`}
                >
                  Upload
                </button>
              </div>
            </div>
          ))}
        </div>
      );
    }

    if (
      viewState === 'chat' &&
      msg.role === 'assistant' &&
      msg.id === lastAssistantMessageId &&
      loan?.id &&
      conversationId &&
      nextRequiredDoc &&
      dismissedDocPromptId !== msg.id
    ) {
      const asksForDocs = /\b(upload|document|documents|passport|payslip|pay slip|bank statement|job letter|proof of address|kyc|id)\b/i.test(
        msg.content || ''
      );
      if (asksForDocs) {
        cards.push(
          <div
            key="doc-prompt"
            data-testid="card-next-document"
            className="my-3 rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] p-4 shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-xs font-extrabold tracking-tight text-slate-800 dark:text-slate-200">Next document</div>
                <div className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-white truncate">{nextRequiredDoc.label}</div>
                <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                  Tap the paperclip (attachments) button, or use Upload to select the file.
                </div>
              </div>
              <button
                type="button"
                onClick={() => setDismissedDocPromptId(msg.id)}
                className="shrink-0 text-[11px] font-bold text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
              >
                Not now
              </button>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <button
                type="button"
                disabled={bootstrapping || loading || uploadingType !== null || ocrProcessing !== null}
                onClick={() => {
                  triggerInlineUi2Upload(nextRequiredDoc.categoryKey, nextRequiredDoc.documentType);
                }}
                className="rounded-xl bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 text-[11px] font-extrabold disabled:opacity-40 disabled:cursor-not-allowed"
                data-testid="button-upload-next-document"
              >
                Upload
              </button>
            </div>
          </div>
        );
      }
    }

    // STP Processing Card
    if (Array.isArray(metadata.stpCheckpoints)) {
      cards.push(
        <StpProcessingCard
          key="stp"
          checkpoints={metadata.stpCheckpoints}
          inProgress={metadata.stpInProgress === true}
          completed={metadata.stpCompleted === true}
          approved={metadata.stpApproved === true}
          bureauScore={typeof metadata.bureauScore === 'number' ? metadata.bureauScore : undefined}
        />
      );
    }

    // Affordability Card
    {
      const affordability = asRecord(metadata.affordability);
      const monthlyIncome = affordability?.monthlyIncome;
      const monthlyEmi = affordability?.monthlyEmi;
      const foir = affordability?.foir;
      if (typeof monthlyIncome === 'number' && typeof monthlyEmi === 'number' && typeof foir === 'number') {
        cards.push(
          <AffordabilityCard
            key="affordability"
            monthlyIncome={monthlyIncome}
            monthlyEmi={monthlyEmi}
            foir={foir}
            existingDebts={typeof affordability?.existingDebts === 'number' ? affordability.existingDebts : undefined}
            dti={typeof affordability?.dti === 'number' ? affordability.dti : undefined}
            approved={affordability?.approved === true}
          />
        );
      }
    }

    // Disbursement Confirmation Card
    if (metadata.disbursementCompleted === true) {
      const loanApp = getLoanApplicationMeta(metadata);
      if (loanApp?.stpCompleted && loanApp.disbursement) {
        cards.push(<DisbursementConfirmationCard key="disbursement" loanApplication={loanApp} />);
      }
    }

    return cards.length > 0 ? <div className="mt-3 space-y-3">{cards}</div> : null;
  };

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
                  <div className="w-full max-w-2xl">
                    <div data-testid={`chat-message-${msg.role}`} className={`chat-message-content ${msg.role === 'user' ? bubbleClassForRole.user : bubbleClassForRole.assistant}`}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{stripXmlTags(msg.content)}</ReactMarkdown>
                    </div>
                    {msg.role === 'assistant' && renderCardsForMessage(msg)}
                    {msg.role === 'assistant'
                      ? (() => {
                          const loanApp = getLoanApplicationMeta(msg.metadata);
                          if (!loanApp?.awaitingAcceptance) return null;
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
                        })()
                      : null}
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
              {lastExtraction ? (
                <div className="flex justify-start">
                  <div className="w-full max-w-2xl">
                    <div
                      data-testid="card-ocr-extraction"
                      className="my-3 rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] p-4 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-xs font-extrabold tracking-tight text-slate-800 dark:text-slate-200">Extracted information</div>
                          <div className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-white truncate">{lastExtraction.title}</div>
                          <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                            OCR status: {ocrProcessing ? 'processing' : lastExtraction.status}
                            {lastExtraction.documentType ? ` • type: ${lastExtraction.documentType}` : ''}
                          </div>
                        </div>
                        <div className="shrink-0 flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => openLastExtractionPreview()}
                            disabled={!lastExtraction.textPreview && (!lastExtraction.fields || Object.keys(lastExtraction.fields).length === 0)}
                            className="text-[11px] font-extrabold text-blue-700 hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-200 disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            View details
                          </button>
                          <button
                            type="button"
                            onClick={() => setLastExtraction(null)}
                            className="text-[11px] font-bold text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>

                      {lastExtraction.status === 'error' ? (
                        <div className="mt-3 text-[11px] text-rose-700 dark:text-rose-400">
                          {lastExtraction.error ? `Extraction failed: ${lastExtraction.error}` : 'Extraction failed.'}
                        </div>
                      ) : null}

                      {lastExtraction.fields && Object.keys(lastExtraction.fields).length > 0 ? (
                        <div className="mt-3 rounded-xl border border-slate-200/60 dark:border-white/[0.08] bg-white/70 dark:bg-white/[0.04] px-3 py-2">
                          <div className="text-xs font-extrabold text-slate-800 dark:text-slate-200">Fields</div>
                          <div className="mt-2 grid gap-2 text-[11px] text-slate-700 dark:text-slate-200">
                            {Object.entries(lastExtraction.fields).map(([k, v]) => (
                              <div key={k} className="flex items-start justify-between gap-3">
                                <div className="font-bold">{k}</div>
                                <div className="text-right break-words">{typeof v === 'string' ? v : JSON.stringify(v)}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      {lastExtraction.textPreview ? (
                        <div className="mt-3 rounded-xl border border-slate-200/60 dark:border-white/[0.08] bg-white/70 dark:bg-white/[0.04] px-3 py-2">
                          <div className="text-xs font-extrabold text-slate-800 dark:text-slate-200">Text preview</div>
                          <pre className="mt-2 whitespace-pre-wrap text-[11px] text-slate-700 dark:text-slate-200 max-h-[35vh] overflow-y-auto">
                            {lastExtraction.textPreview}
                          </pre>
                        </div>
                      ) : null}
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
          {/* Attachments panel removed in favor of inline chat document cards */}

          {ocrProcessing ? (
            <div
              data-testid="ocr-processing-banner"
              className="mb-3 rounded-2xl border border-blue-200/60 dark:border-blue-500/20 bg-blue-50/80 dark:bg-blue-900/20 px-4 py-3 shadow-sm"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="w-4 h-4 rounded-full border-2 border-blue-600 dark:border-blue-400 border-t-transparent animate-spin" />
                  <div className="text-xs font-extrabold text-blue-900 dark:text-blue-200 truncate">Processing document (OCR)</div>
                </div>
                <div className="shrink-0 text-[11px] font-bold text-blue-700 dark:text-blue-300">Working…</div>
              </div>
              <div className="mt-1 text-[11px] text-blue-800/80 dark:text-blue-300/80 truncate">
                {ocrProcessing.title}
              </div>
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
              <input
                ref={ocrFileInputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files && e.target.files[0];
                  if (!f) return;
                  e.currentTarget.value = '';
                  void uploadUi2Document(f);
                }}
              />
            </div>
            <button
              type="button"
              onClick={() => {
                if (viewState !== 'chat' || !conversationId || !loan?.id) return;
                const target = nextRequiredDoc
                  ? { category: nextRequiredDoc.categoryKey, documentType: nextRequiredDoc.documentType }
                  : { category: 'other', documentType: 'document' };
                pendingUploadRef.current = target;
                ocrFileInputRef.current?.click();
              }}
              disabled={viewState !== 'chat' || bootstrapping || !conversationId || !loan?.id || uploadingType !== null || ocrProcessing !== null}
              className={`rounded-2xl h-12 w-12 shadow-sm transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center ${
                'bg-white/90 dark:bg-white/[0.06] hover:bg-slate-50 dark:hover:bg-white/[0.09] text-slate-700 dark:text-slate-200 border border-slate-200/60 dark:border-white/[0.06]'
              }`}
              aria-label="Attachments"
              aria-pressed={false}
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

      <Dialog.Root open={docPreviewOpen} onOpenChange={setDocPreviewOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-[92vw] max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-slate-200/60 dark:border-white/[0.08] bg-white dark:bg-[#111113] p-4 shadow-2xl">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <Dialog.Title className="text-sm font-extrabold text-slate-900 dark:text-white truncate">
                  {docPreview?.title || 'Document preview'}
                </Dialog.Title>
                <Dialog.Description className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                  {docPreview?.status === 'ok'
                    ? 'Text extracted successfully.'
                    : docPreview?.status === 'error'
                      ? `Text extraction failed: ${docPreview?.error || 'unknown error'}`
                      : 'No extracted text available for this file.'}
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button type="button" className="text-xs font-bold text-slate-600 dark:text-slate-300">
                  Close
                </button>
              </Dialog.Close>
            </div>

            <div className="mt-3 grid gap-3">
              {docPreview?.fields ? (
                <div className="rounded-xl border border-slate-200/60 dark:border-white/[0.08] bg-white/70 dark:bg-white/[0.04] px-3 py-2">
                  <div className="text-xs font-extrabold text-slate-800 dark:text-slate-200">Extracted fields</div>
                  <div className="mt-1 grid gap-1 text-[11px] text-slate-600 dark:text-slate-300">
                    {Object.entries(docPreview.fields).map(([k, v]) => (
                      <div key={k} className="flex items-start justify-between gap-3">
                        <div className="font-bold">{k}</div>
                        <div className="text-right break-words">{typeof v === 'string' ? v : JSON.stringify(v)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {docPreview?.textPreview ? (
                <div className="rounded-xl border border-slate-200/60 dark:border-white/[0.08] bg-white/70 dark:bg-white/[0.04] px-3 py-2">
                  <div className="text-xs font-extrabold text-slate-800 dark:text-slate-200">Extracted text preview</div>
                  <pre className="mt-2 whitespace-pre-wrap text-[11px] text-slate-700 dark:text-slate-200 max-h-[50vh] overflow-y-auto">
                    {docPreview.textPreview}
                  </pre>
                </div>
              ) : null}

              {!docPreview?.fields && !docPreview?.textPreview ? (
                <div className="text-xs text-slate-500 dark:text-slate-400">Nothing to preview for this file.</div>
              ) : null}
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
};
