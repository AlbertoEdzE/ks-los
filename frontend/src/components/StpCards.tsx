import React, { useState, useRef, useEffect } from 'react';

interface STPCheckpoint {
  name: string;
  status: 'pending' | 'processing' | 'passed' | 'failed';
  details?: string;
}

interface StpProcessingCardProps {
  checkpoints: STPCheckpoint[];
  inProgress?: boolean;
  completed?: boolean;
  approved?: boolean;
  bureauScore?: number;
}

export function StpProcessingCard({ 
  checkpoints, 
  completed,
  approved,
  bureauScore 
}: StpProcessingCardProps) {
  const getCheckpointIcon = (checkpoint: STPCheckpoint) => {
    if (checkpoint.status === 'processing') {
      return (
        <div className="w-5 h-5 rounded-full border-2 border-blue-600 dark:border-blue-400 border-t-transparent animate-spin" />
      );
    }
    if (checkpoint.status === 'passed') {
      return (
        <svg className="w-5 h-5 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
      );
    }
    if (checkpoint.status === 'failed') {
      return (
        <svg className="w-5 h-5 text-red-600 dark:text-red-400" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
        </svg>
      );
    }
    return (
      <div className="w-5 h-5 rounded-full border-2 border-slate-300 dark:border-slate-600" />
    );
  };

  const getCheckpointStyles = (checkpoint: STPCheckpoint) => {
    if (checkpoint.status === 'processing') {
      return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-500/30';
    }
    if (checkpoint.status === 'passed') {
      return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-500/30';
    }
    if (checkpoint.status === 'failed') {
      return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-500/30';
    }
    return 'bg-slate-50 dark:bg-white/5 border-slate-200 dark:border-white/10';
  };

  return (
    <div
      data-testid="stp-processing-card"
      className="my-4 rounded-2xl border border-slate-200/60 dark:border-white/10 bg-white/80 dark:bg-white/5 p-5 shadow-sm"
    >
      <div className="flex items-center gap-2 mb-4">
        <div className={`w-8 h-8 rounded-xl ${completed ? (approved ? 'bg-green-600' : 'bg-red-600') : 'bg-blue-600'} flex items-center justify-center`}>
          {completed ? (
            approved ? (
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            )
          ) : (
            <svg className="w-4 h-4 text-white animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          )}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
            {completed ? (approved ? 'Approval Complete' : 'Review Required') : 'Automated Underwriting'}
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {completed 
              ? approved 
                ? `Credit Score: ${bureauScore || 720} (Good)` 
                : 'Manual review needed'
              : 'Processing your application...'}
          </p>
        </div>
      </div>

      <div className="space-y-2">
        {checkpoints.map((checkpoint, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-3 p-3 rounded-xl border ${getCheckpointStyles(checkpoint)} transition-all`}
          >
            {getCheckpointIcon(checkpoint)}
            <div className="flex-1">
              <p className="text-xs font-medium text-slate-900 dark:text-white">{checkpoint.name}</p>
              {checkpoint.details && (
                <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">{checkpoint.details}</p>
              )}
            </div>
            {checkpoint.status === 'processing' && (
              <span className="text-[10px] font-medium text-blue-600 dark:text-blue-400">Processing...</span>
            )}
            {checkpoint.status === 'passed' && (
              <span className="text-[10px] font-medium text-green-600 dark:text-green-400">Passed</span>
            )}
            {checkpoint.status === 'failed' && (
              <span className="text-[10px] font-medium text-red-600 dark:text-red-400">Failed</span>
            )}
          </div>
        ))}
      </div>

      {completed && approved && bureauScore && (
        <div className="mt-4 p-4 rounded-xl bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/10 border border-green-200/60 dark:border-green-500/30">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-green-800 dark:text-green-300">Congratulations!</p>
              <p className="text-sm text-green-700 dark:text-green-400 mt-0.5">Your loan has been approved</p>
            </div>
            <div className="text-right">
              <p className="text-[10px] uppercase tracking-wider text-green-600 dark:text-green-400">Credit Score</p>
              <p className="text-2xl font-bold text-green-700 dark:text-green-300">{bureauScore}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface AffordabilityCardProps {
  monthlyIncome: number;
  monthlyEmi: number;
  existingDebts?: number;
  foir: number;
  dti?: number;
  approved?: boolean;
}

export function AffordabilityCard({ 
  monthlyIncome, 
  monthlyEmi, 
  existingDebts = 0,
  foir,
  dti,
  approved 
}: AffordabilityCardProps) {
  const totalObligations = monthlyEmi + existingDebts;
  const remainingIncome = monthlyIncome - totalObligations;

  return (
    <div
      data-testid="affordability-card"
      className="my-4 rounded-2xl border border-slate-200/60 dark:border-white/10 bg-white/80 dark:bg-white/5 p-5 shadow-sm"
    >
      <div className="flex items-center gap-2 mb-4">
        <div className={`w-8 h-8 rounded-xl ${approved ? 'bg-green-600' : 'bg-amber-600'} flex items-center justify-center`}>
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 36v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        </div>
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Affordability Assessment</h3>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Monthly Income</p>
          <p className="text-lg font-bold text-slate-900 dark:text-white">${monthlyIncome.toLocaleString()}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Total Obligations</p>
          <p className="text-lg font-bold text-slate-900 dark:text-white">${totalObligations.toLocaleString()}</p>
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-slate-600 dark:text-slate-400">FOIR (Fixed Obligation to Income Ratio)</p>
            <p className={`text-xs font-semibold ${foir > 50 ? 'text-red-600' : 'text-green-600'}`}>
              {foir.toFixed(1)}%
            </p>
          </div>
          <div className="h-2 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
            <div 
              className={`h-full ${foir > 50 ? 'bg-red-500' : 'bg-green-500'} transition-all`}
              style={{ width: `${Math.min(foir, 100)}%` }}
            />
          </div>
        </div>

        {dti && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs text-slate-600 dark:text-slate-400">DTI (Debt-to-Income)</p>
              <p className={`text-xs font-semibold ${dti > 43 ? 'text-red-600' : 'text-green-600'}`}>
                {dti.toFixed(1)}%
              </p>
            </div>
            <div className="h-2 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
              <div 
                className={`h-full ${dti > 43 ? 'bg-red-500' : 'bg-green-500'} transition-all`}
                style={{ width: `${Math.min(dti, 100)}%` }}
              />
            </div>
          </div>
        )}

        <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200/60 dark:border-blue-500/30">
          <div className="flex items-center justify-between">
            <p className="text-xs text-blue-800 dark:text-blue-300">Remaining Monthly Income</p>
            <p className="text-sm font-bold text-blue-900 dark:text-blue-100">${remainingIncome.toLocaleString()}</p>
          </div>
        </div>
      </div>

      {approved && (
        <div className="mt-4 p-3 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200/60 dark:border-green-500/30">
          <p className="text-xs text-green-800 dark:text-green-300">
            ✓ Affordability criteria met. Loan is within comfortable repayment capacity.
          </p>
        </div>
      )}
    </div>
  );
}

interface TermsAcceptanceCardProps {
  loanAmount: number;
  interestRate: number;
  tenure: number;
  monthlyEmi: number;
  totalInterest: number;
  totalRepayment: number;
  onAccept?: (signature: string) => void;
}

export function TermsAcceptanceCard({
  loanAmount,
  interestRate,
  tenure,
  monthlyEmi,
  totalInterest,
  totalRepayment,
  onAccept
}: TermsAcceptanceCardProps) {
  const [signature, setSignature] = useState<string | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);

  const startDrawing = (e: React.MouseEvent | React.TouchEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = 'touches' in e ? e.touches[0].clientX - rect.left : e.clientX - rect.left;
    const y = 'touches' in e ? e.touches[0].clientY - rect.top : e.clientY - rect.top;

    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#1e40af';
    setIsDrawing(true);
  };

  const draw = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = 'touches' in e ? e.touches[0].clientX - rect.left : e.clientX - rect.left;
    const y = 'touches' in e ? e.touches[0].clientY - rect.top : e.clientY - rect.top;

    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearSignature = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setSignature(null);
  };

  const saveSignature = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    setSignature(canvas.toDataURL());
  };

  const handleAccept = () => {
    if (signature && agreed) {
      onAccept?.(signature);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatMaybeCurrency = (amount: number) => {
    if (!Number.isFinite(amount) || amount <= 0) return '—';
    return formatCurrency(amount);
  };

  const formatMaybePercent = (rate: number) => {
    if (!Number.isFinite(rate) || rate <= 0) return '—';
    return `${rate.toFixed(2)}%`;
  };

  const formatMaybeYears = (years: number) => {
    if (!Number.isFinite(years) || years <= 0) return '—';
    return `${years} years`;
  };

  const hasPricing = loanAmount > 0 && interestRate > 0 && tenure > 0 && monthlyEmi > 0;

  return (
    <div
      data-testid="terms-acceptance-card"
      className="my-4 rounded-2xl border border-blue-200/60 dark:border-blue-500/20 bg-gradient-to-br from-blue-50/80 to-indigo-50/60 dark:from-blue-900/20 dark:to-indigo-900/10 p-5 shadow-sm"
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100">Accept Loan Terms</h3>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="p-3 rounded-xl bg-white/60 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Loan Amount</p>
          <p className="text-sm font-bold text-slate-900 dark:text-white">{formatMaybeCurrency(loanAmount)}</p>
        </div>
        <div className="p-3 rounded-xl bg-white/60 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Interest Rate</p>
          <p className="text-sm font-bold text-blue-600 dark:text-blue-400">{formatMaybePercent(interestRate)}</p>
        </div>
        <div className="p-3 rounded-xl bg-white/60 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Tenure</p>
          <p className="text-sm font-bold text-slate-900 dark:text-white">{formatMaybeYears(tenure)}</p>
        </div>
        <div className="p-3 rounded-xl bg-white/60 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Monthly EMI</p>
          <p className="text-sm font-bold text-blue-600 dark:text-blue-400">{formatMaybeCurrency(monthlyEmi)}</p>
        </div>
        <div className="p-3 rounded-xl bg-white/60 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Total Interest</p>
          <p className="text-sm font-bold text-amber-600 dark:text-amber-400">{formatMaybeCurrency(totalInterest)}</p>
        </div>
        <div className="p-3 rounded-xl bg-white/60 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Total Repayment</p>
          <p className="text-sm font-bold text-slate-900 dark:text-white">{formatMaybeCurrency(totalRepayment)}</p>
        </div>
      </div>

      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full py-2 px-3 text-xs font-medium text-blue-600 dark:text-blue-400 bg-white/60 dark:bg-white/5 rounded-xl mb-4 hover:bg-white/80 dark:hover:bg-white/10 transition-colors"
      >
        {expanded ? 'Hide' : 'View'} Terms & Conditions {expanded ? '↑' : '↓'}
      </button>

      {expanded && (
        <div className="mb-4 p-4 rounded-xl bg-white/60 dark:bg-white/5 max-h-48 overflow-y-auto">
          <h4 className="text-xs font-semibold text-slate-900 dark:text-white mb-2">Loan Agreement Terms</h4>
          <ol className="text-xs text-slate-600 dark:text-slate-400 space-y-1 list-decimal list-inside">
            <li>Borrower agrees to repay the loan amount with interest as specified above</li>
            <li>Monthly EMI will be automatically debited from the registered account</li>
            <li>Late payment fees may apply for missed or delayed payments</li>
            <li>Prepayment is allowed after 6 months with 2% penalty</li>
            <li>Default may result in legal action and credit score impact</li>
            <li>Lender reserves the right to recall the loan under breach of terms</li>
          </ol>
        </div>
      )}

      <div className="mb-4">
        <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">Electronic Signature</p>
        <div className="p-3 rounded-xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10">
          <canvas
            ref={canvasRef}
            width={400}
            height={120}
            className="w-full h-32 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-white/10 cursor-crosshair touch-none"
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            onTouchStart={startDrawing}
            onTouchMove={draw}
            onTouchEnd={stopDrawing}
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={clearSignature}
              className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-white/5 rounded-lg hover:bg-slate-200 dark:hover:bg-white/10 transition-colors"
            >
              Clear
            </button>
            <button
              onClick={saveSignature}
              disabled={!signature}
              className="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Save Signature
            </button>
          </div>
        </div>
      </div>

      <label className="flex items-center gap-2 mb-4 cursor-pointer">
        <input
          type="checkbox"
          checked={agreed}
          onChange={(e) => setAgreed(e.target.checked)}
          className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
        />
        <span className="text-xs text-slate-700 dark:text-slate-300">
          I have read and agree to the Terms & Conditions
        </span>
      </label>

      <button
        onClick={handleAccept}
        disabled={!signature || !agreed || !hasPricing}
        className="w-full py-3 px-4 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-600/20"
      >
        Accept Terms & Receive Funds
      </button>
    </div>
  );
}

interface DisbursementConfirmationCardProps {
  amount: number;
  transactionRef: string;
  accountNumber: string;
  firstEmiDate: string;
  emiAmount: number;
}

export function DisbursementConfirmationCard({
  amount,
  transactionRef,
  accountNumber,
  firstEmiDate,
  emiAmount
}: DisbursementConfirmationCardProps) {
  useEffect(() => {
    // Trigger confetti animation
    const triggerConfetti = () => {
      if (typeof window !== 'undefined') {
        // Simple confetti using canvas
        const canvas = document.createElement('canvas');
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.pointerEvents = 'none';
        canvas.style.zIndex = '9999';
        document.body.appendChild(canvas);

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        type ConfettiParticle = {
          x: number;
          y: number;
          vx: number;
          vy: number;
          color: string;
          size: number;
        };

        const particles: ConfettiParticle[] = [];
        for (let i = 0; i < 100; i++) {
          particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height - canvas.height,
            vx: Math.random() * 4 - 2,
            vy: Math.random() * 4 + 2,
            color: `hsl(${Math.random() * 360}, 100%, 50%)`,
            size: Math.random() * 8 + 4
          });
        }

        const animate = () => {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          particles.forEach((p) => {
            ctx.fillStyle = p.color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
            p.x += p.vx;
            p.y += p.vy;
            if (p.y > canvas.height) p.y = -10;
          });
          requestAnimationFrame(animate);
        };

        animate();

        setTimeout(() => {
          document.body.removeChild(canvas);
        }, 5000);
      }
    };

    triggerConfetti();
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div
      data-testid="disbursement-confirmation-card"
      className="my-4 rounded-2xl border border-green-200/60 dark:border-green-500/20 bg-gradient-to-br from-green-50/80 to-emerald-50/60 dark:from-green-900/20 dark:to-emerald-900/10 p-6 shadow-sm"
    >
      <div className="text-center mb-4">
        <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-green-600 flex items-center justify-center animate-bounce">
          <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        </div>
        <h3 className="text-xl font-bold text-green-900 dark:text-green-100">🎉 Loan Disbursed!</h3>
        <p className="text-sm text-green-700 dark:text-green-300 mt-1">Funds have been credited to your account</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-xl bg-white/60 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Amount Credited</p>
          <p className="text-lg font-bold text-green-600 dark:text-green-400">{formatCurrency(amount)}</p>
        </div>
        <div className="p-3 rounded-xl bg-white/60 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Transaction Ref</p>
          <p className="text-xs font-mono font-bold text-slate-900 dark:text-white">{transactionRef}</p>
        </div>
        <div className="p-3 rounded-xl bg-white/60 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Account</p>
          <p className="text-sm font-bold text-slate-900 dark:text-white">****{accountNumber}</p>
        </div>
        <div className="p-3 rounded-xl bg-white/60 dark:bg-white/5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">First EMI Date</p>
          <p className="text-sm font-bold text-slate-900 dark:text-white">{firstEmiDate}</p>
        </div>
      </div>

      <div className="mt-4 p-4 rounded-xl bg-white/60 dark:bg-white/5 border border-slate-200 dark:border-white/10">
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-700 dark:text-slate-300">Monthly EMI Amount</p>
          <p className="text-lg font-bold text-slate-900 dark:text-white">{formatCurrency(emiAmount)}</p>
        </div>
      </div>

      <div className="mt-4 p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200/60 dark:border-blue-500/30">
        <p className="text-xs text-blue-800 dark:text-blue-300">
          💡 <strong>Tip:</strong> Set up auto-pay to never miss an EMI and build a strong credit history!
        </p>
      </div>
    </div>
  );
}
