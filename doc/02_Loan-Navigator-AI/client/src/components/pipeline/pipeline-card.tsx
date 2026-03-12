import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { FileText, Clock, CheckCircle2, XCircle, IndianRupee, AlertCircle, ArrowUpRight } from "lucide-react";
import type { Loan, LoanPhase } from "@shared/schema";

function statusColor(status: string) {
  switch (status) {
    case "draft": return "bg-slate-500/10 text-slate-500 dark:text-slate-400 border-transparent";
    case "in-progress": return "bg-blue-500/10 text-blue-600 dark:text-blue-300 border-transparent";
    case "approved": return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-300 border-transparent";
    case "rejected": return "bg-red-500/10 text-red-500 dark:text-red-400 border-transparent";
    case "disbursed": return "bg-violet-500/10 text-violet-600 dark:text-violet-300 border-transparent";
    default: return "bg-slate-500/10 text-slate-500 dark:text-slate-400 border-transparent";
  }
}

function statusIcon(status: string) {
  switch (status) {
    case "draft": return FileText;
    case "in-progress": return Clock;
    case "approved": return CheckCircle2;
    case "rejected": return XCircle;
    case "disbursed": return IndianRupee;
    default: return AlertCircle;
  }
}

export function PipelineLoanCard({ loan, onClick }: { loan: Loan; onClick: () => void }) {
  const StatusIcon = statusIcon(loan.status);
  return (
    <Card
      data-testid={`loan-card-${loan.id}`}
      className="p-3 cursor-pointer hover-elevate transition-all duration-200 bg-white dark:bg-[#1e2030] border-transparent"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-800 dark:text-white truncate" data-testid={`text-borrower-${loan.id}`}>
            {loan.borrowerName}
          </p>
          <p className="text-[11px] text-slate-400 dark:text-slate-500 truncate">{loan.loanType}</p>
        </div>
        <Badge className={`text-[9px] font-semibold capitalize shrink-0 ${statusColor(loan.status)}`}>
          <StatusIcon className="w-3 h-3 mr-0.5" />
          {loan.status}
        </Badge>
      </div>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-200">{loan.loanAmount}</span>
        <ArrowUpRight className="w-3.5 h-3.5 text-slate-300 dark:text-slate-600" />
      </div>
    </Card>
  );
}

export function PhaseColumn({
  phase,
  loans,
  onSelectLoan,
}: {
  phase: LoanPhase;
  loans: Loan[];
  onSelectLoan: (loan: Loan) => void;
}) {
  const phaseLoans = loans.filter(l => l.currentPhaseId === phase.id);

  return (
    <div
      className="flex flex-col min-w-[280px] max-w-[320px] shrink-0"
      data-testid={`pipeline-column-${phase.id}`}
    >
      <div className="flex items-center gap-2 mb-3 px-1">
        <div
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: phase.color || "#6366f1" }}
        />
        <h3 className="text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider truncate">
          {phase.name}
        </h3>
        <Badge className="text-[10px] font-bold bg-slate-100 dark:bg-white/[0.06] text-slate-500 dark:text-slate-400 border-transparent ml-auto shrink-0">
          {phaseLoans.length}
        </Badge>
      </div>

      <div className="flex-1 space-y-2 p-2 rounded-xl bg-slate-50/80 dark:bg-white/[0.02] min-h-[200px]">
        {phaseLoans.length === 0 && (
          <p className="text-[11px] text-slate-300 dark:text-slate-600 text-center pt-8">No loans</p>
        )}
        {phaseLoans.map(loan => (
          <PipelineLoanCard
            key={loan.id}
            loan={loan}
            onClick={() => onSelectLoan(loan)}
          />
        ))}
      </div>
    </div>
  );
}
