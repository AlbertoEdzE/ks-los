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
      className="relative z-10 border-b border-gray-200/60 bg-white/60 backdrop-blur-sm"
    >
      <div className="max-w-3xl mx-auto px-4 py-3">
        <div className="flex items-center gap-1.5 mb-2.5">
          <span className="text-[11px] font-semibold text-gray-600 uppercase tracking-wider">
            Your Loan Journey
          </span>
          <span className="text-[10px] text-gray-400 ml-auto">
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
                          className="absolute inset-0 w-8 h-8 -m-1 rounded-full bg-blue-500/15 animate-ping" 
                          style={{ animationDuration: '2s' }} 
                        />
                      )}
                      <div
                        className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-500 ${
                          isCompleted
                            ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/20'
                            : isCurrent
                              ? 'bg-blue-600 text-white shadow-md shadow-blue-600/25 ring-2 ring-gray-200'
                              : 'bg-gray-50/80 text-gray-400'
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
 
                    <p 
                      className={`text-[9px] mt-1.5 text-center leading-tight max-w-[72px] transition-colors duration-300 ${
                        isCurrent
                          ? 'font-semibold text-blue-600'
                          : isCompleted
                            ? 'font-medium text-blue-600/70'
                            : 'text-gray-400'
                      }`}
                    >
                      {step.label}
                    </p>
                  </div>
 
                  {i < BORROWER_JOURNEY_STEPS.length - 1 && (
                    <div className="flex items-center pt-3 -mx-0.5">
                      <div 
                        className={`h-[2px] w-6 transition-colors duration-500 ${
                          i < currentIdx ? 'bg-blue-600' : 'bg-gray-200'
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
