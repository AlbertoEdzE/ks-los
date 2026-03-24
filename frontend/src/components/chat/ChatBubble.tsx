/**
 * Chat Bubble Component
 * 
 * Renders individual chat messages with support for metadata-rich assistant responses.
 * Displays structured data (recommendations, checklists, snapshots) as styled cards.
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

export interface ChatBubbleProps {
  message: V2Message;
  isLatest?: boolean;
}

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

/**
 * Chat Bubble Component
 * 
 * Renders user and assistant messages with distinct styling.
 * Assistant messages can include rich metadata cards.
 */
export const ChatBubble: React.FC<ChatBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  
  const metadata = parseMetadata(message.metadata);

  return (
    <div 
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
      data-testid={isUser ? 'user-message' : 'assistant-message'}
    >
      {/* Avatar */}
      <div 
        className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser 
            ? 'bg-blue-600 text-white' 
            : 'bg-gradient-to-br from-blue-500 to-blue-600 text-white'
        }`}
      >
        {isUser ? (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        )}
      </div>

      {/* Message Content */}
      <div className={`flex flex-col gap-2 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Bubble */}
        <div 
          className={`rounded-2xl px-4 py-3 ${
            isUser 
              ? 'bg-blue-600 text-white rounded-tr-sm' 
              : 'bg-white border border-gray-200/40 text-gray-800 rounded-tl-sm shadow-sm'
          }`}
        >
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>

        {/* Metadata Cards (Assistant Only) */}
        {!isUser && metadata && (
          <div className="flex flex-col gap-3 w-full">
            {/* Loan Recommendations */}
            {Array.isArray(metadata.loanRecommendations) && metadata.loanRecommendations.length > 0 && (
              <div className="rounded-xl bg-white border border-gray-200/40 shadow-sm overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/50">
                  <h4 className="text-sm font-semibold text-gray-800">Recommended Products</h4>
                </div>
                <div className="divide-y divide-gray-100">
                  {metadata.loanRecommendations.map((rec, idx: number) => {
                    const recRecord = asRecord(rec);
                    if (!recRecord) return null;
                    const productName =
                      typeof recRecord.productName === 'string'
                        ? recRecord.productName
                        : typeof recRecord.name === 'string'
                          ? recRecord.name
                          : null;
                    const type = typeof recRecord.type === 'string' ? recRecord.type : null;
                    const estimatedRate = typeof recRecord.estimatedRate === 'string' ? recRecord.estimatedRate : null;
                    const estimatedEmi = typeof recRecord.estimatedEmi === 'string' ? recRecord.estimatedEmi : null;
                    const tenure = typeof recRecord.tenure === 'string' ? recRecord.tenure : null;
                    const recommendation = typeof recRecord.recommendation === 'string' ? recRecord.recommendation : null;

                    return (
                      <div key={idx} className="p-4 hover:bg-gray-50/50 transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <p className="font-semibold text-gray-800">{productName ?? 'Recommendation'}</p>
                          {type && <p className="text-xs text-gray-500">{type}</p>}
                        </div>
                        {estimatedRate && (
                          <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-1 rounded">
                            {estimatedRate}
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                        {estimatedEmi && (
                          <div>
                            <span className="text-gray-400">EMI:</span>{' '}
                            <span className="font-semibold text-gray-800">{estimatedEmi}</span>
                          </div>
                        )}
                        {tenure && (
                          <div>
                            <span className="text-gray-400">Tenure:</span>{' '}
                            <span className="font-semibold text-gray-800">{tenure}</span>
                          </div>
                        )}
                      </div>
                      {recommendation && (
                        <p className="text-xs text-gray-500 mt-2 italic">{recommendation}</p>
                      )}
                    </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Documents Checklist */}
            {(() => {
              const checklist = asRecord(metadata.documentsChecklist);
              const requiredNow = Array.isArray(checklist?.requiredNow) ? checklist.requiredNow : null;
              if (!requiredNow || requiredNow.length === 0) return null;
              return (
              <div className="rounded-xl bg-white border border-gray-200/40 shadow-sm overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-100 bg-amber-50/50">
                  <h4 className="text-sm font-semibold text-amber-800 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Required Documents
                  </h4>
                </div>
                <div className="divide-y divide-gray-100">
                  {requiredNow.map((doc, idx: number) => {
                    const docRecord = asRecord(doc);
                    if (!docRecord) return null;
                    const name = typeof docRecord.name === 'string' ? docRecord.name : 'Document';
                    const description = typeof docRecord.description === 'string' ? docRecord.description : null;
                    return (
                      <div key={idx} className="p-3 flex items-start gap-3">
                      <div className="shrink-0 w-5 h-5 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center mt-0.5">
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-800">{name}</p>
                        {description && <p className="text-xs text-gray-500">{description}</p>}
                      </div>
                    </div>
                    );
                  })}
                </div>
              </div>
              );
            })()}

            {/* Loan Application Result */}
            {asRecord(metadata.loanApplication) && (
              <div className={`rounded-xl border shadow-sm overflow-hidden ${
                (metadata.loanApplication as Record<string, unknown>).success === true
                  ? 'bg-emerald-50/50 border-emerald-200/50' 
                  : 'bg-red-50/50 border-red-200/50'
              }`}>
                {(() => {
                  const loanApplication = metadata.loanApplication as Record<string, unknown>;
                  const success = loanApplication.success === true;
                  const message = typeof loanApplication.message === 'string' ? loanApplication.message : null;
                  const loanId = typeof loanApplication.loanId === 'string' ? loanApplication.loanId : null;
                  const approvalTier = typeof loanApplication.approvalTier === 'string' ? loanApplication.approvalTier : null;
                  return (
                <div className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    {success ? (
                      <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    )}
                    <p className={`font-semibold ${
                      success ? 'text-emerald-800' : 'text-red-800'
                    }`}>
                      {message ?? 'Application Submitted'}
                    </p>
                  </div>
                  {loanId && (
                    <p className="text-xs text-gray-600">
                      Loan ID: <span className="font-mono">{loanId}</span>
                    </p>
                  )}
                  {approvalTier && (
                    <p className="text-xs text-gray-600 mt-1">
                      Tier: <span className="font-semibold">{approvalTier}</span>
                    </p>
                  )}
                </div>
                  );
                })()}
              </div>
            )}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[10px] text-gray-400 px-1">
          {message.createdAt 
            ? new Date(message.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : ''}
        </span>
      </div>
    </div>
  );
};

export default ChatBubble;
