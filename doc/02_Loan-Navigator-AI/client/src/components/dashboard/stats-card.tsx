import { GlassPanel } from "@/components/layout/glass-panel";

interface StatsCardProps {
  icon: any;
  label: string;
  value: string | number;
  color: string;
  iconColor: string;
}

export function StatsCard({ icon: Icon, label, value, color, iconColor }: StatsCardProps) {
  return (
    <GlassPanel className="hover:scale-[1.02] transition-all duration-200">
      <div className="p-4 flex items-center gap-3.5">
        <div className={`p-2.5 rounded-xl ${color}`}>
          <Icon className={`w-5 h-5 ${iconColor}`} />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white" data-testid={`text-stat-${label.toLowerCase().replace(/\s/g, '-')}`}>{value}</p>
          <p className="text-[11px] font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide">{label}</p>
        </div>
      </div>
    </GlassPanel>
  );
}
