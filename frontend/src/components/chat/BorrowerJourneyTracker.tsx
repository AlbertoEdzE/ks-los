/**
 * Borrower Journey Tracker Component
 * 
 * Displays a visual progress tracker showing the borrower's loan journey stage.
 * Derives current step from conversation messages and phase information.
 * 
 * Ported from Loan-Navigator-AI with adaptations for KS-LOS frontend stack.
 */

import React from 'react';

// Type definitions matching KS-LOS backend
export interface V2Message {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: unknown;
  createdAt?: string | null;
}

// Journey steps matching Caribbean loan origination workflow
const BORROWER_JOURNEY_STEPS = [
  { key: 'need', label: 'Tell us your need' },
  { key: 'eligibility', label: 'Check eligibility' },
  { key: 'documents', label: 'Share documents' },
  { key: 'review', label: 'Review in progress' },
  { key: 'offer', label: 'Offer ready' },
  { key: 'checks', label: 'Final checks' },
  { key: 'disbursement', label: 'Disbursement' },
];

type AgentStyle = {
  id: string;
  label: string;
  ringClass: string;
  badgeClass: string;
  lineClass: string;
};

const AGENT_STYLES: AgentStyle[] = [
  { id: 'intake', label: 'Intake Agent', ringClass: 'bg-sky-500/20 dark:bg-sky-400/15', badgeClass: 'bg-sky-500/40 dark:bg-sky-400/30', lineClass: 'bg-sky-500/70 dark:bg-sky-400/50' },
  { id: 'documents', label: 'Documents Agent', ringClass: 'bg-blue-500/20 dark:bg-blue-400/15', badgeClass: 'bg-blue-500/40 dark:bg-blue-400/30', lineClass: 'bg-blue-500/70 dark:bg-blue-400/50' },
  { id: 'underwriting', label: 'Underwriting Agent', ringClass: 'bg-indigo-500/20 dark:bg-indigo-400/15', badgeClass: 'bg-indigo-500/40 dark:bg-indigo-400/30', lineClass: 'bg-indigo-500/70 dark:bg-indigo-400/50' },
  { id: 'closing', label: 'Closing Agent', ringClass: 'bg-violet-500/20 dark:bg-violet-400/15', badgeClass: 'bg-violet-500/40 dark:bg-violet-400/30', lineClass: 'bg-violet-500/70 dark:bg-violet-400/50' },
];

function agentStyleForStepIndex(stepIndex: number): AgentStyle {
  if (stepIndex <= 1) return AGENT_STYLES[0];
  if (stepIndex === 2) return AGENT_STYLES[1];
  if (stepIndex <= 4) return AGENT_STYLES[2];
  return AGENT_STYLES[3];
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null;
}

/**
 * Derives the current journey step from conversation messages.
 * Analyzes loan application metadata to determine progress.
 * 
 * @param messages - Conversation messages to analyze
 * @param currentPhaseName - Optional current phase name for fallback
 * @returns Current step index (0-6)
 */
function deriveJourneyStep(
  messages: V2Message[],
  currentPhaseName?: string | null
): number {
  let maxStep = 0;

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

    // STP completion states
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
    
    // Standard application states
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

  // If no metadata-derived step, use phase name
  if (maxStep > 0) return maxStep;

  if (currentPhaseName) {
    const name = currentPhaseName.toLowerCase();
    if (name.includes('disbursement') || name.includes('closing') || name.includes('funded')) return 6;
    if (name.includes('legal') || name.includes('security') || name.includes('pre-disbursement')) return 5;
    if (name.includes('approval') || name.includes('offer') || name.includes('conditional')) return 4;
    if (name.includes('review') || name.includes('valuation') || name.includes('property')) return 3;
    if (name.includes('document') || name.includes('verification') || name.includes('credit')) return 2;
    if (name.includes('application') || name.includes('submission') || name.includes('eligibility')) return 1;
  }

  return 0;
}

export interface BorrowerJourneyTrackerProps {
  /** Current phase name from backend */
  currentPhaseName?: string | null;
  /** Override step index (optional) */
  currentStepIndex?: number;
  /** Conversation messages for derivation */
  messages?: V2Message[];
}

/**
 * Borrower Journey Tracker Component
 * 
 * Renders a horizontal progress tracker showing loan journey stages.
 * Auto-derives current step from conversation metadata or accepts manual override.
 */
export const BorrowerJourneyTracker: React.FC<BorrowerJourneyTrackerProps> = ({
  currentPhaseName,
  currentStepIndex,
  messages,
}) => {
  const derivedStep = messages ? deriveJourneyStep(messages, currentPhaseName) : undefined;
  let currentIdx = currentStepIndex ?? derivedStep ?? 0;
  
  // Clamp to valid range
  if (currentIdx < 0) currentIdx = 0;
  if (currentIdx >= BORROWER_JOURNEY_STEPS.length) currentIdx = BORROWER_JOURNEY_STEPS.length - 1;

  return (
    <div 
      data-testid="borrower-journey-tracker" 
      className="glass-header sticky top-0 z-40 shrink-0 border-b border-slate-200/40 dark:border-white/[0.04] bg-white/70 dark:bg-[#141414]/80 backdrop-blur-xl"
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
              const agentStyle = agentStyleForStepIndex(i);
 
              return (
                <div key={step.key} className="flex items-start" data-testid={`journey-step-${i}`}>
                  <div className="flex flex-col items-center" style={{ minWidth: '76px' }}>
                    <div className="relative">
                      {isCurrent && (
                        <div 
                          className="absolute inset-0 w-8 h-8 -m-1 rounded-full bg-blue-500/15 animate-ping" 
                          style={{ animationDuration: '2s' }} 
                        />
                      )}
                      <div className={`relative z-10 rounded-full p-[1.5px] ${agentStyle.ringClass}`} title={agentStyle.label}>
                        <div
                          className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-500 ${
                            isCompleted
                              ? 'bg-blue-600 text-white shadow-sm shadow-blue-200/50 dark:shadow-blue-900/30'
                              : isCurrent
                                ? 'bg-blue-600 text-white shadow-md shadow-blue-200/50 dark:shadow-blue-900/30 ring-2 ring-blue-100 dark:ring-blue-500/15'
                                : 'bg-slate-100 dark:bg-white/[0.06] text-slate-400 dark:text-slate-500'
                          }`}
                        >
                          {isCompleted ? (
                            <svg className="w-3 h-3" strokeWidth={3} viewBox="0 0 24 24" fill="none" stroke="currentColor">
                              <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          ) : (
                            <span>{i + 1}</span>
                          )}
                        </div>
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
                    <div className={`mt-1 h-[3px] w-6 rounded-full ${agentStyle.badgeClass}`} aria-hidden="true" />
                  </div>
 
                  {i < BORROWER_JOURNEY_STEPS.length - 1 && (
                    <div className="flex items-center pt-3 -mx-0.5">
                      <div 
                        className={`h-[2px] w-6 transition-colors duration-500 ${
                          i < currentIdx ? agentStyle.lineClass : 'bg-slate-200 dark:bg-white/[0.06]'
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
};

export default BorrowerJourneyTracker;
