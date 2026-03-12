import { useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient, OFFICER_HEADERS } from "@/lib/queryClient";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Eye, Edit3, Trash2, CheckCircle2 } from "lucide-react";
import type { CatalogProduct } from "@shared/schema";
import { getCategoryMeta, formatTenure } from "./constants";
import { CategoryIcon, StatusBadge, RiskBadge } from "./badges";

export function ProductCard({ product, onEdit, onView }: { product: CatalogProduct; onEdit: () => void; onView: () => void }) {
  const meta = getCategoryMeta(product.category);
  const { toast } = useToast();

  const deleteMutation = useMutation({
    mutationFn: async () => {
      await apiRequest("DELETE", `/api/catalog-products/${product.id}`, undefined, OFFICER_HEADERS);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/catalog-products"] });
      toast({ title: "Product Deleted" });
    },
  });

  return (
    <div
      data-testid={`product-card-${product.id}`}
      className="group bg-white dark:bg-[#161820] rounded-2xl ring-1 ring-black/[0.03] dark:ring-white/[0.04] hover:ring-black/[0.06] dark:hover:ring-white/[0.06] shadow-sm hover:shadow-lg hover:shadow-slate-200/50 dark:hover:shadow-black/30 transition-all duration-300 overflow-hidden"
    >
      <div
        className="h-1 w-full"
        style={{ background: `linear-gradient(90deg, ${meta.color}, ${meta.color}88)` }}
      />
      <div className="px-5 py-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3 min-w-0">
            <CategoryIcon category={product.category} />
            <div className="min-w-0">
              <h3 className="font-semibold text-sm text-slate-800 dark:text-white truncate">{product.name}</h3>
              <p className="text-[10px] text-slate-400 dark:text-slate-500 font-mono tracking-wide">{product.code}</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 shrink-0 ml-2">
            <StatusBadge status={product.status} />
            <RiskBadge grade={product.riskGrade} />
          </div>
        </div>

        {product.description && (
          <p className="text-[12px] text-slate-500 dark:text-slate-400 mb-3 line-clamp-2 leading-relaxed">{product.description}</p>
        )}

        <div className="grid grid-cols-3 gap-2 mb-3">
          <div className="text-center p-2.5 rounded-xl bg-slate-50/80 dark:bg-white/[0.03]">
            <p className="text-[9px] text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-0.5 font-semibold">Rate</p>
            <p className="text-xs font-bold text-slate-800 dark:text-slate-100">{product.baseInterestRate || "—"}</p>
            {product.maxInterestRate && <p className="text-[9px] text-slate-400 dark:text-slate-500">to {product.maxInterestRate}</p>}
          </div>
          <div className="text-center p-2.5 rounded-xl bg-slate-50/80 dark:bg-white/[0.03]">
            <p className="text-[9px] text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-0.5 font-semibold">Amount</p>
            <p className="text-xs font-bold text-slate-800 dark:text-slate-100">{product.minAmount || "—"}</p>
            {product.maxAmount && <p className="text-[9px] text-slate-400 dark:text-slate-500">to {product.maxAmount}</p>}
          </div>
          <div className="text-center p-2.5 rounded-xl bg-slate-50/80 dark:bg-white/[0.03]">
            <p className="text-[9px] text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-0.5 font-semibold">Tenure</p>
            <p className="text-xs font-bold text-slate-800 dark:text-slate-100">{formatTenure(product.minTenureMonths)}</p>
            {product.maxTenureMonths && <p className="text-[9px] text-slate-400 dark:text-slate-500">to {formatTenure(product.maxTenureMonths)}</p>}
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5 mb-3">
          {product.collateralRequired && (
            <Badge className="text-[9px] bg-slate-500/8 text-slate-500 dark:text-slate-400 border-transparent font-medium">Collateral</Badge>
          )}
          {product.insuranceRequired && (
            <Badge className="text-[9px] bg-violet-500/10 text-violet-500 dark:text-violet-400 border-transparent font-medium">Insurance</Badge>
          )}
          {product.minCreditScore && (
            <Badge className="text-[9px] bg-blue-500/8 text-blue-500 dark:text-blue-400 border-transparent font-medium">
              CIBIL {product.minCreditScore}+
            </Badge>
          )}
          {product.processingFeePercent && (
            <Badge className="text-[9px] bg-amber-500/8 text-amber-600 dark:text-amber-400 border-transparent font-medium">
              Fee {product.processingFeePercent}
            </Badge>
          )}
        </div>

        {product.features && product.features.length > 0 && (
          <div className="space-y-1 mb-1">
            {product.features.slice(0, 2).map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px] text-sky-600 dark:text-sky-400">
                <CheckCircle2 className="w-3 h-3 shrink-0" />
                <span className="truncate">{f}</span>
              </div>
            ))}
            {product.features.length > 2 && (
              <p className="text-[10px] text-slate-400 dark:text-slate-500 pl-5">+{product.features.length - 2} more</p>
            )}
          </div>
        )}
      </div>

      <div className="px-4 py-2.5 border-t border-slate-100/80 dark:border-white/[0.04] flex items-center gap-1.5">
        <Button
          data-testid={`button-view-product-${product.id}`}
          variant="ghost"
          size="sm"
          onClick={onView}
          className="flex-1 rounded-xl text-[11px] h-8 gap-1.5 text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-white/[0.04]"
        >
          <Eye className="w-3.5 h-3.5" /> View
        </Button>
        <Button
          data-testid={`button-edit-product-${product.id}`}
          variant="ghost"
          size="sm"
          onClick={onEdit}
          className="flex-1 rounded-xl text-[11px] h-8 gap-1.5 text-blue-500 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-500/10"
        >
          <Edit3 className="w-3.5 h-3.5" /> Edit
        </Button>
        <Button
          data-testid={`button-delete-product-${product.id}`}
          variant="ghost"
          size="sm"
          onClick={() => { if (confirm("Delete this product?")) deleteMutation.mutate(); }}
          className="rounded-xl text-[11px] h-8 text-red-400 dark:text-red-400/70 hover:text-red-600 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-500/10 px-2"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </Button>
      </div>
    </div>
  );
}
