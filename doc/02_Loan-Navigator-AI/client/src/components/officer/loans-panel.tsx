import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { FileText } from "lucide-react";
import type { Loan } from "@shared/schema";
import { LoanTypeIcon } from "./loan-type-icon";
import { EditableLoanCard } from "./editable-loan-card";

export function LoansPanel({ loans }: { loans: Loan[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Loan Applications</h3>
        <Badge className="text-[10px] bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border-transparent ml-auto">
          {loans.length} Total
        </Badge>
      </div>

      {loans.length === 0 ? (
        <div className="text-center py-6">
          <FileText className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-xs text-gray-400 dark:text-gray-500">No loans created yet</p>
          <p className="text-[10px] text-gray-300 dark:text-gray-600 mt-1">Ask the AI to create one</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {loans.map((loan) => (
            <div key={loan.id}>
              <button
                data-testid={`loan-sidebar-item-${loan.id}`}
                onClick={() => setExpandedId(expandedId === loan.id ? null : loan.id)}
                className="w-full flex items-center gap-2 p-2.5 rounded-2xl bg-gray-50 dark:bg-white/[0.03] border border-gray-100/60 dark:border-white/[0.04] hover:bg-gray-100 dark:hover:bg-white/[0.06] transition-colors text-left"
              >
                <div className="w-7 h-7 rounded-xl bg-blue-50 dark:bg-blue-500/15 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                  <LoanTypeIcon type={loan.loanType} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 dark:text-gray-200 truncate">{loan.borrowerName}</p>
                  <p className="text-[10px] text-gray-400 dark:text-gray-500 truncate">{loan.loanType} — {loan.loanAmount}</p>
                </div>
                <Badge className={`text-[9px] border shrink-0 ${
                  loan.status === "draft" ? "bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border-transparent" :
                  loan.status === "active" ? "bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 border-transparent" :
                  "bg-gray-50 dark:bg-white/[0.04] text-gray-500 dark:text-gray-400 border-transparent"
                }`}>
                  {loan.status}
                </Badge>
              </button>
              {expandedId === loan.id && (
                <div className="mt-1.5 ml-2">
                  <EditableLoanCard loan={loan} onClose={() => setExpandedId(null)} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
