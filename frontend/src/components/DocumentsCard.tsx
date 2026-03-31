import { useEffect, useState } from 'react';

interface DocumentItem {
  name: string;
  status: 'required' | 'optional';
  description: string;
  uploaded?: boolean;
}

interface DocumentsChecklist {
  identity: DocumentItem[];
  income: DocumentItem[];
  business?: DocumentItem[];
  property?: DocumentItem[];
  vehicle?: DocumentItem[];
}

interface DocumentsCardProps {
  checklist: DocumentsChecklist;
  onUpload?: (documentName: string) => void;
  busyDocumentName?: string | null;
  disableUpload?: boolean;
  collapsible?: boolean;
  defaultOpen?: boolean;
}

export function DocumentsCard({
  checklist,
  onUpload,
  busyDocumentName = null,
  disableUpload = false,
  collapsible = false,
  defaultOpen = false,
}: DocumentsCardProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  useEffect(() => {
    setIsOpen(defaultOpen);
  }, [defaultOpen]);

  const renderDocumentSection = (title: string, documents: DocumentItem[]) => (
    <div className="mb-4">
      <h4 className="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
        {title}
      </h4>
      <div className="space-y-2">
        {documents.map((doc, idx) => (
          <div
            key={idx}
            className="flex items-start justify-between p-3 rounded-xl bg-white/60 dark:bg-white/5 border border-slate-200/60 dark:border-white/10"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-slate-900 dark:text-white">{doc.name}</p>
                {doc.status === 'required' && (
                  <span className="text-[9px] font-semibold text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30 px-1.5 py-0.5 rounded">
                    REQUIRED
                  </span>
                )}
                {doc.status === 'optional' && (
                  <span className="text-[9px] font-semibold text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                    OPTIONAL
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{doc.description}</p>
            </div>
            <button
              onClick={() => onUpload?.(doc.name)}
              disabled={disableUpload}
              className="ml-3 px-3 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {busyDocumentName === doc.name ? 'Uploading…' : doc.uploaded ? 'Replace' : 'Upload'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );

  const allDocuments = [
    ...checklist.identity,
    ...checklist.income,
    ...(checklist.business || []),
    ...(checklist.property || []),
    ...(checklist.vehicle || []),
  ];
  const totalCount = allDocuments.length;
  const requiredCount = allDocuments.filter((d) => d.status === 'required').length;

  const header = (
    <div className="flex items-center gap-2">
      <div className="w-8 h-8 rounded-xl bg-slate-600 dark:bg-slate-500 flex items-center justify-center">
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      </div>
      <div className="min-w-0">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Required Documents</h3>
        <div className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
          {requiredCount} required • {totalCount} total
        </div>
      </div>
    </div>
  );

  const content = (
    <>
      {renderDocumentSection('Identity Documents', checklist.identity)}
      {renderDocumentSection('Income Documents', checklist.income)}
      {checklist.business && renderDocumentSection('Business Documents', checklist.business)}
      {checklist.property && renderDocumentSection('Property Documents', checklist.property)}
      {checklist.vehicle && renderDocumentSection('Vehicle Documents', checklist.vehicle)}

      <div className="mt-4 p-3 rounded-xl bg-blue-50/80 dark:bg-blue-900/20 border border-blue-200/60 dark:border-blue-500/20">
        <p className="text-xs text-blue-800 dark:text-blue-300">
          <strong>Tip:</strong> Upload clear photos or PDFs. Documents are processed using OCR for faster verification.
        </p>
      </div>
    </>
  );

  if (collapsible) {
    return (
      <details
        open={isOpen}
        onToggle={(e) => setIsOpen((e.currentTarget as HTMLDetailsElement).open)}
        data-testid="documents-card"
        className="my-4 rounded-2xl border border-slate-200/60 dark:border-white/10 bg-white/80 dark:bg-white/5 p-5 shadow-sm"
      >
        <summary className="list-none cursor-pointer select-none">
          <div className="flex items-center justify-between gap-3">
            {header}
            <div className="shrink-0 flex items-center gap-2 text-[11px] font-semibold text-slate-600 dark:text-slate-300">
              <span>{isOpen ? 'Click to collapse' : 'Click to expand'}</span>
              <svg
                className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </summary>
        <div className="mt-4">{content}</div>
      </details>
    );
  }

  return (
    <div
      data-testid="documents-card"
      className="my-4 rounded-2xl border border-slate-200/60 dark:border-white/10 bg-white/80 dark:bg-white/5 p-5 shadow-sm"
    >
      <div className="mb-4">{header}</div>
      {content}
    </div>
  );
}
