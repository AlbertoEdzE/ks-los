import { CheckCircle2, XCircle } from "lucide-react";
import { EditableLoanCard } from "./editable-loan-card";

export function LoanActionResult({ metadata }: { metadata: any }) {
  const loanActionData = metadata?.loanAction;
  if (!loanActionData) return null;

  if (loanActionData.loan) {
    return <EditableLoanCard loan={loanActionData.loan} />;
  }

  return (
    <div className={`mt-2 p-3 rounded-2xl border ${
      loanActionData.success
        ? "bg-blue-50 dark:bg-blue-500/[0.06] border-blue-200/40 dark:border-blue-500/10"
        : "bg-red-50 dark:bg-red-500/10 border-red-200/40 dark:border-red-500/10"
    }`}>
      <div className="flex items-center gap-2 text-xs font-medium mb-1">
        {loanActionData.success ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
        ) : (
          <XCircle className="w-3.5 h-3.5 text-red-500 dark:text-red-400" />
        )}
        <span className={loanActionData.success ? "text-blue-700 dark:text-blue-400" : "text-red-600 dark:text-red-400"}>
          {loanActionData.success ? "Loan Created" : "Loan Action Failed"}
        </span>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400">{loanActionData.message}</p>
    </div>
  );
}
