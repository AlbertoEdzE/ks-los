import { Badge } from "@/components/ui/badge";
import { Workflow, ArrowRight } from "lucide-react";
import { Link } from "wouter";
import type { LoanPhase } from "@shared/schema";

export function LifecyclePipeline({ phases }: { phases: LoanPhase[] }) {
  const activePhases = phases.filter(p => p.isActive);
  const deactivatedPhases = phases.filter(p => !p.isActive);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <Workflow className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Loan Lifecycle Pipeline</h3>
        <Badge className="text-[10px] bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border-transparent ml-auto">
          {activePhases.length} Active
        </Badge>
      </div>

      <div className="space-y-1.5">
        {activePhases.map((phase, i) => (
          <div key={phase.id} className="flex items-center gap-2">
            <Link href={`/phases/${phase.id}`}>
              <div className="flex items-center gap-2 flex-1 p-2.5 rounded-2xl bg-gray-50 dark:bg-white/[0.03] border border-gray-100/60 dark:border-white/[0.04] hover:bg-blue-50 dark:hover:bg-white/[0.06] transition-colors group cursor-pointer" data-testid={`phase-link-${i}`}>
                <div
                  className="w-7 h-7 rounded-xl flex items-center justify-center text-[10px] font-bold border shrink-0"
                  style={{ backgroundColor: `${phase.color}15`, color: phase.color || "#0d9488", borderColor: `${phase.color}30` }}
                >
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 dark:text-gray-200 truncate">{phase.name}</p>
                  {phase.description && (
                    <p className="text-[10px] text-gray-400 dark:text-gray-500 truncate">{phase.description}</p>
                  )}
                </div>
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: phase.color || "#0d9488" }}
                />
              </div>
            </Link>
            {i < activePhases.length - 1 && (
              <ArrowRight className="w-3 h-3 text-gray-300 dark:text-gray-600 shrink-0 hidden sm:block" />
            )}
          </div>
        ))}
      </div>

      {deactivatedPhases.length > 0 && (
        <div className="pt-3 border-t border-gray-100/60 dark:border-white/[0.04]">
          <p className="text-[10px] uppercase tracking-widest text-gray-400 dark:text-gray-500 font-medium mb-2">
            Deactivated Phases
          </p>
          <div className="space-y-1">
            {deactivatedPhases.map((phase) => (
              <div key={phase.id} className="flex items-center gap-2 p-2 rounded-xl bg-gray-50 dark:bg-white/5 border border-gray-100/60 dark:border-white/[0.04] opacity-60">
                <div className="w-5 h-5 rounded flex items-center justify-center text-[9px] bg-gray-100 dark:bg-white/10 text-gray-400 dark:text-gray-500">
                  ×
                </div>
                <p className="text-[11px] text-gray-400 dark:text-gray-500 line-through">{phase.name}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
