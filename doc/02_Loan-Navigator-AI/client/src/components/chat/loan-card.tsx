import { Badge } from "@/components/ui/badge";
import { TrendingDown, Clock, ShieldCheck, Sparkles } from "lucide-react";
import type { LoanProduct } from "@shared/schema";

const ACCENTS = [
  { border: "border-blue-200/60 dark:border-blue-800/40", glow: "shadow-blue-100/50 dark:shadow-blue-900/20", icon: "text-blue-600 dark:text-blue-400", bg: "bg-blue-50 dark:bg-blue-950/50" },
  { border: "border-indigo-200/60 dark:border-indigo-800/40", glow: "shadow-indigo-100/50 dark:shadow-indigo-900/20", icon: "text-indigo-600 dark:text-indigo-400", bg: "bg-indigo-50 dark:bg-indigo-950/50" },
  { border: "border-slate-200/60 dark:border-slate-700/40", glow: "shadow-slate-100/50 dark:shadow-slate-900/20", icon: "text-slate-600 dark:text-slate-400", bg: "bg-slate-50 dark:bg-slate-950/50" },
];
const ICONS = [TrendingDown, Clock, ShieldCheck];

export function LoanCard({ product, index }: { product: LoanProduct; index: number }) {
  const Icon = ICONS[index % 3];
  const accent = ACCENTS[index % 3];

  return (
    <div
      data-testid={`loan-card-${index}`}
      className={`glass-card relative p-4 rounded-3xl bg-white dark:bg-[#1a1a1a] ${accent.border} border shadow-sm ${accent.glow} transition-all duration-300 hover:shadow-md group overflow-hidden`}
    >
      <div className="relative z-10">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-2xl ${accent.bg} border ${accent.border} ${accent.icon}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-gray-900 dark:text-gray-100">{product.name}</h4>
              <p className="text-xs text-gray-400 dark:text-gray-500">{product.type}</p>
            </div>
          </div>
          <Badge className="text-[10px] bg-gray-50 dark:bg-white/5 text-gray-500 dark:text-gray-400 border-transparent">
            {product.approvalSpeed}
          </Badge>
        </div>

        <div className="grid grid-cols-3 gap-2 mb-3">
          {[
            { label: "Rate", value: product.estimatedRate },
            { label: "EMI", value: product.estimatedEmi },
            { label: "Tenure", value: product.tenure },
          ].map((item, i) => (
            <div key={i} className="text-center p-2.5 rounded-2xl bg-gray-50 dark:bg-white/[0.04] border border-gray-100/60 dark:border-white/[0.04]">
              <p className="text-[9px] text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-0.5">{item.label}</p>
              <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{item.value}</p>
            </div>
          ))}
        </div>

        <div className="space-y-1 mb-3">
          {Array.isArray(product.pros) && product.pros.map((pro, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-blue-700 dark:text-blue-400">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500 dark:bg-blue-400" />
              {pro}
            </div>
          ))}
          {Array.isArray(product.cons) && product.cons.map((con, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500 dark:bg-amber-400" />
              {con}
            </div>
          ))}
        </div>

        <div className={`flex items-center gap-2 text-xs font-medium ${accent.icon} ${accent.bg} rounded-2xl p-2.5 border ${accent.border}`}>
          <Sparkles className="w-3.5 h-3.5" />
          {product.recommendation}
        </div>
      </div>
    </div>
  );
}
