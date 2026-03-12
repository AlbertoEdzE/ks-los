import { useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient, OFFICER_HEADERS } from "@/lib/queryClient";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  X,
  ChevronLeft,
  ChevronRight,
  User,
  IndianRupee,
  Briefcase,
  Clock,
  FileText,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  Layers,
  CreditCard,
  Phone,
  Mail,
  StickyNote,
} from "lucide-react";
import type { Loan, LoanPhase } from "@shared/schema";

const STATUS_OPTIONS = ["draft", "in-progress", "approved", "rejected", "disbursed"] as const;

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

function DetailRow({ icon: Icon, label, value }: { icon: any; label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-2">
      <Icon className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
      <div className="min-w-0">
        <p className="text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-wider">{label}</p>
        <p className="text-xs text-slate-700 dark:text-slate-200 truncate">{value}</p>
      </div>
    </div>
  );
}

export function LoanDetailPanel({
  loan,
  phases,
  onClose,
}: {
  loan: Loan;
  phases: LoanPhase[];
  onClose: () => void;
}) {
  const { toast } = useToast();
  const activePhases = phases.filter(p => p.isActive).sort((a, b) => a.sortOrder - b.sortOrder);
  const currentPhaseIdx = activePhases.findIndex(p => p.id === loan.currentPhaseId);
  const canAdvance = currentPhaseIdx >= 0 && currentPhaseIdx < activePhases.length - 1;
  const canRetreat = currentPhaseIdx > 0;

  const advanceMutation = useMutation({
    mutationFn: async (nextPhaseId: string) => {
      const res = await apiRequest("PATCH", `/api/loans/${loan.id}`, { currentPhaseId: nextPhaseId }, OFFICER_HEADERS);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/loans"] });
      toast({ title: "Phase Updated", description: "Loan moved to the next phase." });
    },
    onError: (error: Error) => {
      toast({ title: "Error", description: error.message, variant: "destructive" });
    },
  });

  const statusMutation = useMutation({
    mutationFn: async (newStatus: string) => {
      const res = await apiRequest("PATCH", `/api/loans/${loan.id}`, { status: newStatus }, OFFICER_HEADERS);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/loans"] });
      toast({ title: "Status Updated" });
    },
    onError: (error: Error) => {
      toast({ title: "Error", description: error.message, variant: "destructive" });
    },
  });

  const isPending = advanceMutation.isPending || statusMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 backdrop-blur-md p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-[#161820] rounded-2xl shadow-2xl dark:shadow-black/60 w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col ring-1 ring-black/[0.04] dark:ring-white/[0.06]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-gradient-to-r from-slate-50 to-blue-50/60 dark:from-[#1a1d28] dark:to-[#1a2235] px-6 py-4 border-b border-slate-100 dark:border-white/[0.06] flex items-center justify-between gap-2 shrink-0">
          <div className="min-w-0">
            <h2 className="font-bold text-lg text-slate-800 dark:text-white truncate" data-testid="text-loan-detail-name">{loan.borrowerName}</h2>
            <p className="text-xs text-slate-400 dark:text-slate-500">{loan.loanType} &middot; {loan.loanAmount}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} data-testid="button-close-detail">
            <X className="w-5 h-5" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          <div className="space-y-3">
            <h3 className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-blue-500" /> Current Phase
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {activePhases.map((phase, idx) => {
                const isCurrent = phase.id === loan.currentPhaseId;
                const isPast = currentPhaseIdx >= 0 && idx < currentPhaseIdx;
                return (
                  <Badge
                    key={phase.id}
                    data-testid={`badge-phase-${phase.id}`}
                    className={`text-[10px] font-medium border-transparent ${
                      isCurrent
                        ? "bg-blue-500/15 text-blue-600 dark:text-blue-300"
                        : isPast
                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                        : "bg-slate-100 dark:bg-white/[0.04] text-slate-400 dark:text-slate-500"
                    }`}
                  >
                    {idx + 1}. {phase.name}
                  </Badge>
                );
              })}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              data-testid="button-prev-phase"
              variant="outline"
              size="sm"
              disabled={!canRetreat || isPending}
              onClick={() => canRetreat && advanceMutation.mutate(activePhases[currentPhaseIdx - 1].id)}
            >
              <ChevronLeft className="w-4 h-4 mr-1" /> Previous Phase
            </Button>
            <Button
              data-testid="button-next-phase"
              size="sm"
              disabled={!canAdvance || isPending}
              onClick={() => canAdvance && advanceMutation.mutate(activePhases[currentPhaseIdx + 1].id)}
              className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-0"
            >
              Next Phase <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
            {isPending && <Loader2 className="w-4 h-4 animate-spin text-blue-500" />}
          </div>

          <div className="border-t border-slate-100 dark:border-white/[0.04] pt-4 space-y-3">
            <h3 className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5 text-amber-500" /> Status
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {STATUS_OPTIONS.map(s => {
                const Icon = statusIcon(s);
                const active = loan.status === s;
                return (
                  <Button
                    key={s}
                    data-testid={`button-status-${s}`}
                    variant={active ? "default" : "outline"}
                    size="sm"
                    disabled={isPending}
                    onClick={() => !active && statusMutation.mutate(s)}
                    className={active ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-0" : ""}
                  >
                    <Icon className="w-3.5 h-3.5 mr-1" />
                    <span className="capitalize">{s}</span>
                  </Button>
                );
              })}
            </div>
          </div>

          <div className="border-t border-slate-100 dark:border-white/[0.04] pt-4 space-y-2">
            <h3 className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <User className="w-3.5 h-3.5 text-indigo-500" /> Borrower Details
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <DetailRow icon={Mail} label="Email" value={loan.borrowerEmail} />
              <DetailRow icon={Phone} label="Phone" value={loan.borrowerPhone} />
              <DetailRow icon={Briefcase} label="Employment" value={loan.employmentType} />
              <DetailRow icon={IndianRupee} label="Monthly Income" value={loan.monthlyIncome} />
              <DetailRow icon={CreditCard} label="Credit Score" value={loan.creditScore} />
              <DetailRow icon={FileText} label="Purpose" value={loan.purpose} />
              <DetailRow icon={IndianRupee} label="Interest Rate" value={loan.interestRate} />
              <DetailRow icon={Clock} label="Tenure" value={loan.tenure} />
            </div>
            {loan.notes && (
              <div className="mt-3 p-3 rounded-xl bg-slate-50 dark:bg-white/[0.03]">
                <div className="flex items-center gap-1.5 mb-1">
                  <StickyNote className="w-3 h-3 text-slate-400" />
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Notes</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300">{loan.notes}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
