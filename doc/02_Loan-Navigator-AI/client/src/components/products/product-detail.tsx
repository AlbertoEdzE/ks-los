import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  X,
  Edit3,
  CheckCircle2,
  FileText,
  Shield,
  TrendingUp,
  Percent,
  Clock,
  IndianRupee,
  Target,
  Users,
  AlertCircle,
  Building2,
  Star,
} from "lucide-react";
import type { CatalogProduct } from "@shared/schema";
import { getCategoryMeta, formatTenure } from "./constants";
import { CategoryIcon, StatusBadge, RiskBadge } from "./badges";

export function ProductDetail({ product, onClose, onEdit }: { product: CatalogProduct; onClose: () => void; onEdit: () => void }) {
  const meta = getCategoryMeta(product.category);

  const InfoRow = ({ icon: Icon, label, value }: { icon: any; label: string; value: string | number | null | undefined }) => {
    if (!value && value !== 0) return null;
    return (
      <div className="flex items-start gap-3 py-2.5">
        <div className="p-1.5 rounded-lg bg-slate-100/80 dark:bg-white/[0.04]">
          <Icon className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-slate-400 dark:text-slate-500 font-semibold mb-0.5">{label}</p>
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{value}</p>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 backdrop-blur-md p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-[#161820] rounded-2xl shadow-2xl dark:shadow-black/60 w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col ring-1 ring-black/[0.03] dark:ring-white/[0.04]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative px-6 py-5 border-b border-slate-100 dark:border-white/[0.06] flex items-center justify-between overflow-hidden">
          <div className="absolute inset-0 opacity-[0.04] dark:opacity-[0.08]" style={{ background: `linear-gradient(135deg, ${meta.color}, transparent 60%)` }} />
          <div className="relative flex items-center gap-3">
            <CategoryIcon category={product.category} size="lg" />
            <div>
              <h2 className="font-bold text-xl text-slate-800 dark:text-white">{product.name}</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-slate-400 dark:text-slate-500 font-mono">{product.code}</span>
                <StatusBadge status={product.status} />
                <RiskBadge grade={product.riskGrade} />
              </div>
            </div>
          </div>
          <div className="relative flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={onEdit} className="rounded-xl gap-1.5 text-blue-500 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-500/10">
              <Edit3 className="w-3.5 h-3.5" /> Edit
            </Button>
            <Button variant="ghost" size="icon" className="rounded-xl text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/[0.06]" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {product.description && (
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{product.description}</p>
          )}

          <div className="grid grid-cols-3 gap-3">
            <div className="text-center p-4 rounded-xl bg-slate-50/80 dark:bg-white/[0.03]">
              <Percent className="w-5 h-5 mx-auto mb-1.5 text-blue-500 dark:text-blue-400" />
              <p className="text-[9px] text-slate-400 dark:text-slate-500 uppercase tracking-widest font-semibold">Interest Rate</p>
              <p className="text-lg font-bold text-slate-800 dark:text-white mt-0.5">{product.baseInterestRate || "—"}</p>
              {product.maxInterestRate && <p className="text-[10px] text-slate-400 dark:text-slate-500">up to {product.maxInterestRate}</p>}
            </div>
            <div className="text-center p-4 rounded-xl bg-slate-50/80 dark:bg-white/[0.03]">
              <IndianRupee className="w-5 h-5 mx-auto mb-1.5 text-indigo-500 dark:text-indigo-400" />
              <p className="text-[9px] text-slate-400 dark:text-slate-500 uppercase tracking-widest font-semibold">Loan Range</p>
              <p className="text-lg font-bold text-slate-800 dark:text-white mt-0.5">{product.minAmount || "—"}</p>
              {product.maxAmount && <p className="text-[10px] text-slate-400 dark:text-slate-500">to {product.maxAmount}</p>}
            </div>
            <div className="text-center p-4 rounded-xl bg-slate-50/80 dark:bg-white/[0.03]">
              <Clock className="w-5 h-5 mx-auto mb-1.5 text-violet-500 dark:text-violet-400" />
              <p className="text-[9px] text-slate-400 dark:text-slate-500 uppercase tracking-widest font-semibold">Tenure</p>
              <p className="text-lg font-bold text-slate-800 dark:text-white mt-0.5">{formatTenure(product.minTenureMonths)}</p>
              {product.maxTenureMonths && <p className="text-[10px] text-slate-400 dark:text-slate-500">to {formatTenure(product.maxTenureMonths)}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-6">
            <InfoRow icon={Shield} label="Min Credit Score" value={product.minCreditScore} />
            <InfoRow icon={TrendingUp} label="Max LTV" value={product.maxLtv} />
            <InfoRow icon={IndianRupee} label="Min Income" value={product.minIncome} />
            <InfoRow icon={Percent} label="Processing Fee" value={product.processingFeePercent} />
            <InfoRow icon={AlertCircle} label="Prepayment Penalty" value={product.prepaymentPenalty} />
            <InfoRow icon={Users} label="Target Segment" value={product.targetSegment} />
          </div>

          <div className="flex gap-3">
            {product.collateralRequired && (
              <div className="flex items-center gap-2 text-xs font-medium text-blue-600 dark:text-blue-300 bg-blue-500/10 rounded-xl px-3 py-2">
                <Building2 className="w-3.5 h-3.5" /> Collateral Required
              </div>
            )}
            {product.insuranceRequired && (
              <div className="flex items-center gap-2 text-xs font-medium text-violet-600 dark:text-violet-300 bg-violet-500/10 rounded-xl px-3 py-2">
                <Shield className="w-3.5 h-3.5" /> Insurance Required
              </div>
            )}
          </div>

          {product.features && product.features.length > 0 && (
            <div>
              <h4 className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <Star className="w-3.5 h-3.5 text-sky-500 dark:text-sky-400" /> Key Features
              </h4>
              <div className="space-y-1.5">
                {product.features.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-sky-600 dark:text-sky-300">
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                    {f}
                  </div>
                ))}
              </div>
            </div>
          )}

          {product.requiredDocuments && product.requiredDocuments.length > 0 && (
            <div>
              <h4 className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <FileText className="w-3.5 h-3.5 text-violet-500 dark:text-violet-400" /> Required Documents
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {product.requiredDocuments.map((d, i) => (
                  <Badge key={i} className="text-[11px] bg-violet-500/10 text-violet-600 dark:text-violet-300 border-transparent font-medium">
                    {d}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {product.eligibilityCriteria && product.eligibilityCriteria.length > 0 && (
            <div>
              <h4 className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <Target className="w-3.5 h-3.5 text-blue-500 dark:text-blue-400" /> Eligibility Criteria
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {product.eligibilityCriteria.map((c, i) => (
                  <Badge key={i} className="text-[11px] bg-blue-500/10 text-blue-600 dark:text-blue-300 border-transparent font-medium">
                    {c}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
