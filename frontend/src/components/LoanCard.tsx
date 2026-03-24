import { Clock, ShieldCheck, Sparkles, TrendingDown, Check } from 'lucide-react';

interface LoanRecommendation {
  name: string;
  type: 'aggressive' | 'balanced' | 'conservative';
  interest_rate: number;
  tenure_years: number;
  monthly_emi: number;
  total_interest: number;
  total_repayment: number;
  pros: string[];
  cons: string[];
  recommended: boolean;
}

interface LoanCardProps {
  recommendation: LoanRecommendation;
  onSelect?: (recommendation: LoanRecommendation) => void;
  disabled?: boolean;
  selected?: boolean;
}

const ACCENTS = [
  {
    border: 'border-[#0078D4]/20 dark:border-[#0078D4]/30',
    glow: 'shadow-[#0078D4]/[0.06]',
    icon: 'text-[#0078D4]',
    bg: 'bg-[#D6E4F0] dark:bg-[#0078D4]/[0.15]',
    selectedBorder: 'border-[#0078D4] dark:border-[#0078D4]',
    selectedBg: 'bg-[#0078D4]/[0.04] dark:bg-[#0078D4]/[0.08]',
  },
  {
    border: 'border-[#1B2A4A]/20 dark:border-white/[0.08]',
    glow: 'shadow-[#1B2A4A]/[0.06]',
    icon: 'text-[#1B2A4A] dark:text-[#4da3e8]',
    bg: 'bg-gray-50/80 dark:bg-white/[0.05]',
    selectedBorder: 'border-[#1B2A4A] dark:border-[#4da3e8]',
    selectedBg: 'bg-[#1B2A4A]/[0.03] dark:bg-[#4da3e8]/[0.06]',
  },
  {
    border: 'border-[#0078D4]/15 dark:border-[#0078D4]/20',
    glow: 'shadow-[#0078D4]/[0.04]',
    icon: 'text-[#0078D4]/80',
    bg: 'bg-[#D6E4F0]/60 dark:bg-[#0078D4]/10',
    selectedBorder: 'border-[#0078D4]/70 dark:border-[#0078D4]/60',
    selectedBg: 'bg-[#0078D4]/[0.03] dark:bg-[#0078D4]/[0.06]',
  },
];

const ICONS = [TrendingDown, Clock, ShieldCheck];

const typeIndex = (type: LoanRecommendation['type']) => {
  if (type === 'aggressive') return 0;
  if (type === 'balanced') return 1;
  return 2;
};

export function LoanCard({ recommendation, onSelect, disabled, selected }: LoanCardProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const idx = typeIndex(recommendation.type);
  const Icon = ICONS[idx % 3];
  const accent = ACCENTS[idx % 3];
  const selectable = !disabled && typeof onSelect === 'function';

  return (
    <div
      data-testid={`loan-card-${recommendation.type}`}
      onClick={selectable ? () => onSelect(recommendation) : undefined}
      className={`relative p-4 rounded-3xl bg-white dark:bg-white/[0.06] border shadow-sm transition-all duration-300 group overflow-hidden ${
        selected
          ? `${accent.selectedBorder} ${accent.selectedBg} shadow-md ring-1 ring-[#0078D4]/30 dark:ring-[#0078D4]/20`
          : `${accent.border} ${accent.glow} hover:shadow-md`
      } ${selectable ? 'cursor-pointer hover:scale-[1.01] active:scale-[0.99]' : ''} ${disabled ? 'opacity-50' : ''}`}
    >
      {selected ? (
        <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-[#0078D4] flex items-center justify-center shadow-sm shadow-[#0078D4]/30 z-20">
          <Check className="w-3.5 h-3.5 text-white" strokeWidth={3} />
        </div>
      ) : null}

      <div className="relative z-10">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-2xl ${accent.bg} border ${accent.border} ${accent.icon}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div>
              <h4 className="font-semibold text-sm text-[#1B2A4A] dark:text-white">{recommendation.name}</h4>
              {recommendation.recommended ? (
                <p className="text-xs text-[#1B2A4A]/40 dark:text-white/50">Recommended</p>
              ) : (
                <p className="text-xs text-[#1B2A4A]/40 dark:text-white/50">{recommendation.type}</p>
              )}
            </div>
          </div>
          <span className="text-[10px] bg-gray-50/80 dark:bg-white/[0.05] text-[#1B2A4A]/60 dark:text-white/55 px-2 py-1 rounded-full">
            {recommendation.recommended ? 'Top match' : 'Option'}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 mb-3">
          {[
            { label: 'Rate', value: `${recommendation.interest_rate.toFixed(1)}%` },
            { label: 'Tenure', value: `${recommendation.tenure_years} yrs` },
            { label: 'EMI', value: `${formatCurrency(recommendation.monthly_emi)}/mo` },
          ].map((item, i) => (
            <div
              key={i}
              className="text-center p-2.5 rounded-2xl bg-gray-50/80 dark:bg-white/[0.04] border border-gray-200/60 dark:border-white/[0.06]"
            >
              <p className="text-[9px] text-[#1B2A4A]/40 dark:text-white/55 uppercase tracking-widest mb-0.5">{item.label}</p>
              <p className="text-sm font-bold text-[#1B2A4A] dark:text-white">{item.value}</p>
            </div>
          ))}
        </div>

        <div className={`flex items-center gap-2 text-xs font-medium ${accent.icon} ${accent.bg} rounded-2xl p-2.5 border ${accent.border}`}>
          <Sparkles className="w-3.5 h-3.5" />
          Compare this option to your priorities
        </div>

        {selectable && !selected ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect(recommendation);
            }}
            className="mt-3 w-full py-2.5 rounded-2xl border-2 border-dashed border-[#0078D4]/30 dark:border-[#0078D4]/20 text-[#0078D4] text-xs font-semibold hover:bg-[#0078D4]/[0.06] dark:hover:bg-[#0078D4]/10 hover:border-[#0078D4]/50 transition-all duration-200"
          >
            Select This Plan
          </button>
        ) : null}

        {selected ? (
          <div className="mt-3 w-full py-2.5 rounded-2xl bg-[#0078D4] text-white text-xs font-semibold text-center shadow-sm shadow-[#0078D4]/25">
            Selected
          </div>
        ) : null}
      </div>
    </div>
  );
}
