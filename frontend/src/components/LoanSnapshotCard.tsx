import { Calculator, Calendar, DollarSign, Percent, TrendingUp, CheckCircle2 } from 'lucide-react';

interface LoanSnapshot {
  loan_amount: number;
  down_payment: number;
  property_value: number;
  estimated_emi: number;
  tenure_years: number;
  interest_rate: number;
  total_interest: number;
  total_repayment: number;
  ltv_ratio: number;
  foir_ratio?: number;
  currency: string;
}

interface LoanSnapshotCardProps {
  snapshot: LoanSnapshot;
}

export function LoanSnapshotCard({ snapshot }: LoanSnapshotCardProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: snapshot.currency || 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const fields = [
    { label: 'Loan Amount', value: formatCurrency(snapshot.loan_amount), icon: DollarSign },
    { label: 'Estimated EMI', value: `${formatCurrency(snapshot.estimated_emi)}/mo`, icon: Calculator },
    { label: 'Tenure', value: `${snapshot.tenure_years} yrs`, icon: Calendar },
    { label: 'Rate Band', value: `${snapshot.interest_rate.toFixed(2)}%`, icon: Percent },
    { label: 'Down Payment', value: formatCurrency(snapshot.down_payment), icon: TrendingUp },
    { label: 'Asset Price', value: formatCurrency(snapshot.property_value), icon: DollarSign },
  ];

  return (
    <div data-testid="loan-snapshot-card" className="w-full mt-2">
      <div className="rounded-2xl overflow-hidden border border-[#0078D4]/20 dark:border-[#0078D4]/30 bg-gradient-to-br from-white to-[#D6E4F0]/30 dark:from-white/[0.06] dark:to-[#0078D4]/[0.08] shadow-sm">
        <div className="px-4 py-3 border-b border-[#0078D4]/10 dark:border-[#0078D4]/20 bg-[#0078D4]/[0.04] dark:bg-[#0078D4]/[0.06]">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-xl bg-[#0078D4] flex items-center justify-center shadow-sm">
              <Calculator className="w-3.5 h-3.5 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#1B2A4A] dark:text-white">Loan Snapshot</p>
              <p className="text-[11px] text-[#1B2A4A]/50 dark:text-white/50">Indicative terms</p>
            </div>
          </div>
        </div>

        <div className="p-4">
          <div className="grid grid-cols-2 gap-2.5">
            {fields.map((field, i) => {
              const Icon = field.icon;
              return (
                <div key={i} className="p-3 rounded-xl bg-white/70 dark:bg-white/[0.04] border border-gray-200/60 dark:border-white/[0.06]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Icon className="w-3 h-3 text-[#0078D4]/60" />
                    <p className="text-[10px] text-[#1B2A4A]/45 dark:text-white/45 uppercase tracking-wider font-medium">{field.label}</p>
                  </div>
                  <p className="text-sm font-bold text-[#1B2A4A] dark:text-white">{field.value}</p>
                </div>
              );
            })}
          </div>

          <div className="mt-3 flex items-center gap-2 px-3 py-2.5 rounded-xl bg-[#0078D4]/[0.06] dark:bg-[#0078D4]/[0.08] border border-[#0078D4]/10 dark:border-[#0078D4]/15">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#0078D4] shrink-0" />
            <p className="text-[11px] text-[#0078D4] dark:text-[#4da3e8] font-medium">Indicative estimate — final terms confirmed after review</p>
          </div>
        </div>
      </div>
    </div>
  );
}
