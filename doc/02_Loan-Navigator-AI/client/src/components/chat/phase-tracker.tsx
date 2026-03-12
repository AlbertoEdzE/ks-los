import { Check } from "lucide-react";
import { Link } from "wouter";
import type { LoanPhase } from "@shared/schema";

interface PhaseProgressTrackerProps {
  phases: LoanPhase[];
  currentPhaseId: string | null;
}

export function PhaseProgressTracker({ phases, currentPhaseId }: PhaseProgressTrackerProps) {
  const activePhases = phases
    .filter(p => p.isActive)
    .sort((a, b) => a.sortOrder - b.sortOrder);

  if (activePhases.length === 0) return null;

  const rawIndex = currentPhaseId
    ? activePhases.findIndex(p => p.id === currentPhaseId)
    : 0;
  const currentIndex = rawIndex >= 0 ? rawIndex : 0;

  return (
    <div data-testid="phase-progress-tracker" className="glass-header relative z-10 border-b border-slate-200/40 dark:border-white/[0.04] bg-white/50 dark:bg-white/[0.02] backdrop-blur-sm">
      <div className="max-w-3xl mx-auto px-4 py-3">
        <div className="flex items-center gap-1.5 mb-2.5">
          <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Your Loan Journey</span>
          <span className="text-[10px] text-slate-400 dark:text-slate-500 ml-auto">
            Step {Math.max(currentIndex + 1, 1)} of {activePhases.length}
          </span>
        </div>

        <div className="overflow-x-auto scrollbar-hide -mx-1 px-1">
          <div className="flex items-start min-w-max gap-0">
            {activePhases.map((phase, i) => {
              const isCompleted = i < currentIndex;
              const isCurrent = i === currentIndex;

              return (
                <div key={phase.id} className="flex items-start" data-testid={`phase-step-${i}`}>
                  <Link href={`/phases/${phase.id}`}>
                    <div className="flex flex-col items-center cursor-pointer hover:opacity-80 transition-opacity" style={{ minWidth: "72px" }}>
                      <div className="relative">
                        {isCurrent && (
                          <div className="absolute inset-0 w-8 h-8 -m-1 rounded-full bg-blue-400/15 animate-ping" style={{ animationDuration: "2s" }} />
                        )}
                        <div
                          className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-500 ${
                            isCompleted
                              ? "bg-blue-600 text-white shadow-sm shadow-blue-200/50 dark:shadow-blue-900/30"
                              : isCurrent
                                ? "bg-blue-600 text-white shadow-md shadow-blue-200/50 dark:shadow-blue-900/30 ring-2 ring-blue-100 dark:ring-blue-500/15"
                                : "bg-slate-100 dark:bg-white/[0.06] text-slate-400 dark:text-slate-500"
                          }`}
                        >
                          {isCompleted ? (
                            <Check className="w-3 h-3" strokeWidth={3} />
                          ) : (
                            <span>{i + 1}</span>
                          )}
                        </div>
                      </div>
                      <p className={`text-[9px] mt-1.5 text-center leading-tight max-w-[68px] transition-colors duration-300 ${
                        isCurrent
                          ? "font-semibold text-blue-700 dark:text-blue-400"
                          : isCompleted
                            ? "font-medium text-blue-600 dark:text-blue-500"
                            : "text-slate-400 dark:text-slate-500"
                      }`}>
                        {phase.name}
                      </p>
                    </div>
                  </Link>
                  {i < activePhases.length - 1 && (
                    <div className="flex items-center pt-3 -mx-0.5">
                      <div className={`h-[2px] w-6 transition-colors duration-500 ${
                        i < currentIndex ? "bg-blue-500" : "bg-slate-200 dark:bg-white/[0.06]"
                      }`} />
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
}
