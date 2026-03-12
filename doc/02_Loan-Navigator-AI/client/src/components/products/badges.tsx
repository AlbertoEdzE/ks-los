import { Badge } from "@/components/ui/badge";
import { getCategoryMeta } from "./constants";

export function CategoryIcon({ category, size = "md" }: { category: string; size?: "sm" | "md" | "lg" }) {
  const meta = getCategoryMeta(category);
  const Icon = meta.icon;
  const sizeMap = { sm: "w-4 h-4", md: "w-5 h-5", lg: "w-6 h-6" };
  const containerMap = { sm: "w-7 h-7 rounded-lg", md: "w-10 h-10 rounded-xl", lg: "w-12 h-12 rounded-xl" };

  return (
    <div
      className={`${containerMap[size]} flex items-center justify-center shrink-0`}
      style={{ backgroundColor: `${meta.color}18`, color: meta.color }}
    >
      <Icon className={sizeMap[size]} />
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-amber-500/10 text-amber-600 dark:text-amber-300 border-transparent",
    active: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-300 border-transparent",
    suspended: "bg-red-500/10 text-red-600 dark:text-red-300 border-transparent",
    archived: "bg-slate-500/10 text-slate-500 dark:text-slate-400 border-transparent",
  };
  return (
    <Badge className={`text-[10px] font-semibold capitalize px-2 py-0.5 border ${colors[status] || colors.draft}`}>
      {status}
    </Badge>
  );
}

export function RiskBadge({ grade }: { grade: string | null }) {
  if (!grade) return null;
  const colors: Record<string, string> = {
    AAA: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-300",
    AA: "bg-green-500/10 text-green-600 dark:text-green-300",
    A: "bg-sky-500/10 text-sky-600 dark:text-sky-300",
    BBB: "bg-blue-500/10 text-blue-600 dark:text-blue-300",
    BB: "bg-amber-500/10 text-amber-600 dark:text-amber-300",
    B: "bg-orange-500/10 text-orange-600 dark:text-orange-300",
    C: "bg-red-500/10 text-red-600 dark:text-red-300",
  };
  return (
    <Badge className={`text-[10px] font-mono font-bold border-transparent px-2 py-0.5 ${colors[grade] || colors.BBB}`}>
      {grade}
    </Badge>
  );
}
