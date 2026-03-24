import { Check } from 'lucide-react';
import type { V2Message } from './ChatInterface';

const BORROWER_JOURNEY_STEPS = [
  { key: 'need', label: 'Tell us your need' },
  { key: 'eligibility', label: 'Check eligibility' },
  { key: 'documents', label: 'Share documents' },
  { key: 'review', label: 'Review in progress' },
  { key: 'offer', label: 'Offer ready' },
  { key: 'checks', label: 'Final checks' },
  { key: 'disbursement', label: 'Disbursement' },
];

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null;
}

function deriveJourneyStep(messages: V2Message[], currentPhaseName?: string | null): number {
  let maxStep = 0;

  if (messages.some((m) => m.role === 'user' && typeof m.content === 'string' && m.content.trim().length > 0)) {
    maxStep = Math.max(maxStep, 1);
  }

  if (messages.some((m) => m.role === 'user' && typeof m.content === 'string' && /^uploaded\s+"?/i.test(m.content.trim()))) {
    maxStep = Math.max(maxStep, 2);
  }

  for (const msg of messages) {
    if (msg.role !== 'assistant' || !msg.metadata) continue;
    let meta: unknown;
    try {
      meta = typeof msg.metadata === 'string' ? JSON.parse(msg.metadata) : msg.metadata;
    } catch {
      continue;
    }
    const metaRecord = asRecord(meta);
    const la = asRecord(metaRecord?.loanApplication);
    const snap = asRecord(metaRecord?.loanSnapshot);
    const docs = asRecord(metaRecord?.documentsChecklist);

    if (la?.stpCompleted === true && la?.disbursement != null) {
      maxStep = Math.max(maxStep, 6);
      continue;
    }
    if (la?.stpApproved === true && la?.awaitingAcceptance === true) {
      maxStep = Math.max(maxStep, 4);
      continue;
    }
    if (la?.stpApproved === true && la?.approval != null) {
      maxStep = Math.max(maxStep, 4);
      continue;
    }
    if (la?.stpApproved === true && la?.stpSteps != null) {
      maxStep = Math.max(maxStep, 3);
      continue;
    }
    if (la?.success === true) {
      maxStep = Math.max(maxStep, 2);
      continue;
    }
    if (docs) {
      maxStep = Math.max(maxStep, 2);
      continue;
    }
    if (snap) {
      maxStep = Math.max(maxStep, 1);
      continue;
    }
  }

  if (maxStep > 0) return maxStep;

  if (currentPhaseName) {
    const name = currentPhaseName.toLowerCase();
    if (name.includes('disbursement') || name.includes('closing') || name.includes('funded')) return 6;
    if (name.includes('legal') || name.includes('security') || name.includes('pre-disbursement')) return 5;
    if (name.includes('approval') || name.includes('offer') || name.includes('conditional') || name.includes('sanction')) return 4;
    if (name.includes('review') || name.includes('valuation') || name.includes('property')) return 3;
    if (name.includes('document') || name.includes('verification') || name.includes('credit') || name.includes('appraisal')) return 2;
    if (name.includes('application') || name.includes('submission') || name.includes('eligibility')) return 1;
  }

  return 0;
}

interface BorrowerJourneyTrackerProps {
  currentPhaseName?: string | null;
  currentStepIndex?: number;
  messages?: V2Message[];
}

export function BorrowerJourneyTracker({ currentPhaseName, currentStepIndex, messages }: BorrowerJourneyTrackerProps) {
  const derivedStep = messages ? deriveJourneyStep(messages, currentPhaseName) : undefined;
  let currentIdx = currentStepIndex ?? derivedStep ?? 0;
  if (currentIdx < 0) currentIdx = 0;

  return (
    <div
      data-testid="borrower-journey-tracker"
      className="relative z-10 border-b border-slate-200/40 dark:border-white/[0.04] bg-white/50 dark:bg-white/[0.02] backdrop-blur-sm"
    >
      <div className="max-w-3xl mx-auto px-4 py-3">
        <div className="flex items-center gap-1.5 mb-2.5">
          <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Your Loan Journey
          </span>
          <span className="text-[10px] text-slate-400 dark:text-slate-500 ml-auto">
            Step {currentIdx + 1} of {BORROWER_JOURNEY_STEPS.length}
          </span>
        </div>

        <div className="overflow-x-auto scrollbar-hide -mx-1 px-1">
          <div className="flex items-start min-w-max gap-0">
            {BORROWER_JOURNEY_STEPS.map((step, i) => {
              const isCompleted = i < currentIdx;
              const isCurrent = i === currentIdx;

              return (
                <div key={step.key} className="flex items-start" data-testid={`journey-step-${i}`}>
                  <div className="flex flex-col items-center" style={{ minWidth: '76px' }}>
                    <div className="relative">
                      {isCurrent && (
                        <div
                          className="absolute inset-0 w-8 h-8 -m-1 rounded-full bg-blue-400/15 animate-ping"
                          style={{ animationDuration: '2s' }}
                        />
                      )}
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
                          <Check className="w-3 h-3" strokeWidth={3} />
                        ) : (
                          <span>{i + 1}</span>
                        )}
                      </div>
                    </div>
                    <p
                      className={`text-[9px] mt-1.5 text-center leading-tight max-w-[72px] transition-colors duration-300 ${
                        isCurrent
                          ? 'font-semibold text-blue-700 dark:text-blue-400'
                          : isCompleted
                            ? 'font-medium text-blue-600 dark:text-blue-500'
                            : 'text-slate-400 dark:text-slate-500'
                      }`}
                    >
                      {step.label}
                    </p>
                  </div>
                  {i < BORROWER_JOURNEY_STEPS.length - 1 && (
                    <div className="flex items-center pt-3 -mx-0.5">
                      <div
                        className={`h-[2px] w-6 transition-colors duration-500 ${
                          i < currentIdx ? 'bg-blue-500' : 'bg-slate-200 dark:bg-white/[0.06]'
                        }`}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
