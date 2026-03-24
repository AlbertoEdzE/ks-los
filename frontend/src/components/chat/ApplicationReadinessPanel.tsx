/**
 * Application Readiness Panel Component
 * 
 * Displays the borrower's application progress by analyzing conversation messages
 * to determine which required fields have been collected.
 * 
 * Ported from Loan-Navigator-AI with adaptations for KS-LOS frontend stack.
 */

import React from 'react';

// Type definitions
export interface V2Message {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: unknown;
  createdAt?: string | null;
}

export interface IntentAnalysis {
  purpose?: string;
  urgency?: 'low' | 'medium' | 'high' | 'critical';
  affordability?: string;
  monthlyIncome?: string;
  existingDebts?: string;
  loanAmount?: string;
  preferredTenure?: string;
  collateralAvailable?: string;
  employmentType?: string;
  creditHistory?: string;
  firstName?: string;
  lastName?: string;
  email?: string;
  phone?: string;
}

interface Field {
  label: string;
  icon: React.ReactNode;
  gathered: boolean;
}

export interface ApplicationReadinessPanelProps {
  /** Conversation messages for analysis */
  messages: V2Message[];
  /** Optional loan ID if application submitted */
  loanId?: string | null;
}

/**
 * Application Readiness Panel Component
 * 
 * Analyzes conversation to determine application completeness.
 * Shows gathered vs needed information with progress indicator.
 */
export const ApplicationReadinessPanel: React.FC<ApplicationReadinessPanelProps> = ({
  messages,
  loanId,
}) => {
  // Extract latest intent analysis from messages
  const latestIntent: IntentAnalysis | null = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      if (msg.role === 'assistant' && msg.metadata) {
        const meta = typeof msg.metadata === 'string' 
          ? JSON.parse(msg.metadata) 
          : msg.metadata;
        if (meta?.intentAnalysis) return meta.intentAnalysis as IntentAnalysis;
      }
    }
    return null;
  })();

  // Analyze text content for field detection
  const allText = messages
    .filter((m) => m.role === 'user')
    .map((m) => m.content)
    .join(' ')
    .toLowerCase();
  
  const allAssistantText = messages
    .filter((m) => m.role === 'assistant')
    .map((m) => m.content)
    .join(' ')
    .toLowerCase();
  
  const combinedText = allText + ' ' + allAssistantText;

  // Detect if AI has asked for and received name
  const aiAskedForName = messages.some((m, idx) => {
    if (m.role !== 'assistant') return false;
    const askedName = /your (full )?name|may i have your name|what('s| is) your name/i.test(m.content);
    if (!askedName) return false;
    const nextUserMsg = messages.slice(idx + 1).find((n) => n.role === 'user');
    return !!nextUserMsg;
  });

  const aiUsedName = /thank(s| you),?\s+[A-Z][a-z]/i.test(allAssistantText) ||
    /noted,?\s+[A-Z][a-z]|got it,?\s+[A-Z][a-z]|hello,?\s+[A-Z][a-z]|hi,?\s+[A-Z][a-z]/i.test(allAssistantText);

  // Field detection logic
  const hasName = !!(latestIntent?.firstName || latestIntent?.lastName) ||
    /my name is|i'm [a-z]|i am [a-z]|call me [a-z]/i.test(allText) ||
    aiAskedForName || aiUsedName;

  const hasPurpose = !!latestIntent?.purpose ||
    /home|personal|car|vehicle|business|education|property|mortgage|medical|consolidation|loan/i.test(allText);

  const hasEmployment = !!latestIntent?.employmentType ||
    /salaried|self.?employed|contractor|government|private|freelance|business owner|civil servant|employed/i.test(combinedText);

  const hasIncome = !!(latestIntent?.monthlyIncome) ||
    /salary|income|earn|monthly|make|paid|\$\s*\d|usd|ttd|jmd|gyd|\d+[\s,]*(?:per month|a month|monthly)/i.test(combinedText);

  const hasAmount = !!(latestIntent?.loanAmount) ||
    /\d+\s*(k|thousand|million|lakh|lac|m)\b/i.test(allText) || 
    /\$\s*[\d,]+/i.test(allText) ||
    /\d[\d,]*\s*(?:dollar|usd|ttd|gyd)/i.test(allText);

  const hasContact = /(@.*\.|\+\d|phone.*\d|email.*@)/i.test(allText) ||
    !!(latestIntent?.email || latestIntent?.phone);

  // Define fields with icons
  const fields: Field[] = [
    { 
      label: 'Your name', 
      icon: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>, 
      gathered: hasName 
    },
    { 
      label: 'What you need', 
      icon: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>, 
      gathered: hasPurpose 
    },
    { 
      label: 'Employment details', 
      icon: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>, 
      gathered: hasEmployment 
    },
    { 
      label: 'Income information', 
      icon: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>, 
      gathered: hasIncome 
    },
    { 
      label: 'Loan amount', 
      icon: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>, 
      gathered: hasAmount 
    },
    { 
      label: 'Contact details', 
      icon: <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>, 
      gathered: hasContact 
    },
  ];

  const gathered = fields.filter((f) => f.gathered);
  const needed = fields.filter((f) => !f.gathered);
  const progress = Math.round((gathered.length / fields.length) * 100);

  // Estimate loan amount and EMI
  const loanAmountStr = latestIntent?.loanAmount || '';
  const loanAmountMatch = loanAmountStr.match(/[\d,]+/) || allText.match(/\$\s*([\d,]+)/);
  const estimatedAmount = loanAmountMatch ? parseInt(loanAmountMatch[0].replace(/[,$]/g, '')) : null;

  let estimatedMonthly: string | null = null;
  if (estimatedAmount && estimatedAmount > 0) {
    const principal = estimatedAmount;
    const rate = 0.08 / 12; // 8% annual
    const tenure = 240; // 20 years
    const emi = Math.round((principal * rate * Math.pow(1 + rate, tenure)) / (Math.pow(1 + rate, tenure) - 1));
    estimatedMonthly = `$${emi.toLocaleString()}/mo`;
  }

  // Progress message
  const progressMessage = progress === 100
    ? "You're all set — we're preparing your application"
    : progress >= 60
      ? "Almost there — just a few more details"
      : progress >= 30
        ? "Good progress — keep going"
        : "Let's get started with a few details";

  return (
    <div className="space-y-4">
      {/* Main Readiness Card */}
      <div className="rounded-3xl bg-white border border-gray-200/40 shadow-sm shadow-gray-200/50 p-5">
        <h3 className="font-semibold text-sm text-gray-800 mb-1 flex items-center gap-2">
          <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Your Application
        </h3>
        <p className="text-[11px] text-gray-500 mb-4">{progressMessage}</p>

        {/* Progress Bar */}
        <div className="mb-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-gray-600 font-medium">Application readiness</span>
            <span className="text-sm font-bold text-blue-600">{progress}%</span>
          </div>
          <div className="h-2 rounded-full bg-blue-500/10 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-600 to-blue-700 transition-all duration-1000 shadow-sm shadow-blue-600/30"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Gathered Fields */}
        {gathered.length > 0 && (
          <div className="mb-4">
            <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider mb-2 flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              What we know
            </p>
            <div className="space-y-1.5">
              {gathered.map((field, i) => (
                <div 
                  key={i} 
                  className="flex items-center gap-2.5 p-2 rounded-lg bg-emerald-50/60 border border-emerald-200/40"
                >
                  <svg className="w-3.5 h-3.5 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-[11px] font-medium text-emerald-700">{field.label}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Needed Fields */}
        {needed.length > 0 && (
          <div className="mb-4">
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Still needed
            </p>
            <div className="space-y-1.5">
              {needed.map((field, i) => (
                <div 
                  key={i} 
                  className="flex items-center gap-2.5 p-2 rounded-lg bg-gray-50/60 border border-gray-100/40"
                >
                  <span className="text-gray-400 shrink-0">{field.icon}</span>
                  <span className="text-[11px] font-medium text-gray-500">{field.label}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Next Step Guidance */}
        {needed.length > 0 && (
          <div className="p-3 rounded-xl bg-blue-50/30 border border-blue-600/10">
            <p className="text-[10px] font-bold text-blue-600 mb-1 uppercase tracking-wider">Next step</p>
            <p className="text-[11px] text-blue-600/80">
              {needed[0].label === 'Your name' 
                ? "Share your name so we can personalise your experience" 
                : needed[0].label === 'What you need' 
                  ? "Tell us what kind of loan you're looking for" 
                  : needed[0].label === 'Employment details' 
                    ? "Let us know about your employment — it helps us find the best options" 
                    : needed[0].label === 'Income information' 
                      ? "Share your income details — this helps us estimate what you qualify for" 
                      : needed[0].label === 'Loan amount' 
                        ? "How much are you looking to borrow?" 
                        : "Share your email and phone so we can keep you updated"}
            </p>
          </div>
        )}

        {/* Completion Message */}
        {progress === 100 && !loanId && (
          <div className="p-3 rounded-xl bg-emerald-50/80 border border-emerald-200/50">
            <p className="text-[11px] text-emerald-700 font-medium flex items-center gap-1.5">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              All details received — your application is being prepared
            </p>
          </div>
        )}
      </div>

      {/* Loan Snapshot Card */}
      {(estimatedAmount || estimatedMonthly) && (
        <div className="rounded-3xl bg-white border border-gray-200/40 shadow-sm shadow-gray-200/50 p-5">
          <h3 className="font-semibold text-[11px] text-gray-500 mb-3 uppercase tracking-wider">Loan Snapshot</h3>
          <div className="space-y-3">
            {estimatedAmount && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-gray-500">Loan amount</span>
                <span className="text-sm font-bold text-gray-800">${estimatedAmount.toLocaleString()}</span>
              </div>
            )}
            {estimatedMonthly && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-gray-500">Est. monthly payment</span>
                <span className="text-sm font-bold text-blue-600">{estimatedMonthly}</span>
              </div>
            )}
            <p className="text-[9px] text-gray-400 italic">
              Estimate based on ~8% rate, 20yr tenure. Final terms may vary.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApplicationReadinessPanel;
