import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { OFFICER_HEADERS } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/theme-provider";
import { ArrowLeft, Loader2, Layers } from "lucide-react";
import { Link } from "wouter";
import type { Loan, LoanPhase } from "@shared/schema";
import ksqLogo from "@assets/image_1773224776245.png";
import { LoanDetailPanel } from "@/components/pipeline/loan-detail-panel";
import { PhaseColumn, PipelineLoanCard } from "@/components/pipeline/pipeline-card";

const STATUS_OPTIONS = ["draft", "in-progress", "approved", "rejected", "disbursed"] as const;

export default function LoanPipeline() {
  const [selectedLoan, setSelectedLoan] = useState<Loan | null>(null);

  const { data: loans = [], isLoading: loansLoading } = useQuery<Loan[]>({
    queryKey: ["/api/loans"],
    queryFn: async () => {
      const res = await fetch("/api/loans", { headers: OFFICER_HEADERS });
      if (!res.ok) throw new Error("Failed to fetch loans");
      return res.json();
    },
  });

  const { data: phases = [], isLoading: phasesLoading } = useQuery<LoanPhase[]>({
    queryKey: ["/api/phases"],
  });

  const activePhases = phases.filter(p => p.isActive).sort((a, b) => a.sortOrder - b.sortOrder);
  const isLoading = loansLoading || phasesLoading;
  const unassignedLoans = loans.filter(l => !l.currentPhaseId || !activePhases.some(p => p.id === l.currentPhaseId));
  const totalByStatus = STATUS_OPTIONS.reduce((acc, s) => {
    acc[s] = loans.filter(l => l.status === s).length;
    return acc;
  }, {} as Record<string, number>);
  const updatedSelectedLoan = selectedLoan ? loans.find(l => l.id === selectedLoan.id) || null : null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0e1015] flex flex-col">
      <header className="shrink-0 px-6 py-3 border-b border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-[#161820]/80 backdrop-blur-xl flex items-center justify-between gap-3 sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <Link href="/dashboard">
            <Button variant="ghost" size="icon" data-testid="button-back-dashboard">
              <ArrowLeft className="w-4 h-4" />
            </Button>
          </Link>
          <img src={ksqLogo} alt="KSquare" className="h-8 w-8 rounded-lg object-contain dark:brightness-0 dark:invert" data-testid="img-logo" />
          <div>
            <h1 className="text-base font-bold text-slate-800 dark:text-white" data-testid="text-page-title">Loan Pipeline</h1>
            <p className="text-[11px] text-slate-400 dark:text-slate-500">Process loans through lifecycle phases</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            {STATUS_OPTIONS.map(s => (
              <div key={s} className="flex items-center gap-1 text-[10px] text-slate-400 dark:text-slate-500">
                <span className="capitalize font-medium">{s}:</span>
                <span className="font-bold text-slate-600 dark:text-slate-300" data-testid={`text-count-${s}`}>{totalByStatus[s] || 0}</span>
              </div>
            ))}
          </div>
          <ThemeToggle />
        </div>
      </header>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : (
        <div className="flex-1 overflow-x-auto p-6">
          <div className="flex gap-4 min-h-0">
            {activePhases.map((phase) => (
              <PhaseColumn
                key={phase.id}
                phase={phase}
                loans={loans}
                onSelectLoan={setSelectedLoan}
              />
            ))}

            {unassignedLoans.length > 0 && (
              <div className="flex flex-col min-w-[280px] max-w-[320px] shrink-0" data-testid="pipeline-column-unassigned">
                <div className="flex items-center gap-2 mb-3 px-1">
                  <div className="w-2.5 h-2.5 rounded-full shrink-0 bg-slate-400" />
                  <h3 className="text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider truncate">
                    Unassigned
                  </h3>
                  <Badge className="text-[10px] font-bold bg-slate-100 dark:bg-white/[0.06] text-slate-500 dark:text-slate-400 border-transparent ml-auto shrink-0">
                    {unassignedLoans.length}
                  </Badge>
                </div>
                <div className="flex-1 space-y-2 p-2 rounded-xl bg-slate-50/80 dark:bg-white/[0.02] min-h-[200px]">
                  {unassignedLoans.map(loan => (
                    <PipelineLoanCard
                      key={loan.id}
                      loan={loan}
                      onClick={() => setSelectedLoan(loan)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {loans.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <Layers className="w-12 h-12 text-slate-300 dark:text-slate-600 mb-4" />
              <h3 className="text-lg font-semibold text-slate-600 dark:text-slate-300 mb-1" data-testid="text-empty-state">No Loans in Pipeline</h3>
              <p className="text-sm text-slate-400 dark:text-slate-500 max-w-md">
                Create loans from the officer dashboard chat or process leads to see them appear here organized by phase.
              </p>
              <Link href="/dashboard">
                <Button variant="outline" className="mt-4" data-testid="button-go-dashboard">
                  <ArrowLeft className="w-4 h-4 mr-2" /> Back to Dashboard
                </Button>
              </Link>
            </div>
          )}
        </div>
      )}

      {updatedSelectedLoan && (
        <LoanDetailPanel
          loan={updatedSelectedLoan}
          phases={activePhases}
          onClose={() => setSelectedLoan(null)}
        />
      )}
    </div>
  );
}
