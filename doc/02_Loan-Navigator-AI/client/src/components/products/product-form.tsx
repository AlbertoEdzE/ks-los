import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient, OFFICER_HEADERS } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { X, Save, Plus, IndianRupee, Clock, FileText } from "lucide-react";
import type { CatalogProduct } from "@shared/schema";
import { CATEGORIES, RISK_GRADES, STATUSES } from "./constants";
import { CategoryIcon } from "./badges";

const EMPTY_FORM: Partial<CatalogProduct> = {
  name: "",
  code: "",
  category: "home_loan",
  description: "",
  minAmount: "",
  maxAmount: "",
  minTenureMonths: 12,
  maxTenureMonths: 240,
  baseInterestRate: "",
  maxInterestRate: "",
  processingFeePercent: "",
  prepaymentPenalty: "",
  minCreditScore: 650,
  maxLtv: "",
  minIncome: "",
  collateralRequired: false,
  requiredDocuments: [],
  eligibilityCriteria: [],
  features: [],
  targetSegment: "",
  riskGrade: "A",
  insuranceRequired: false,
  status: "draft",
};

export function ProductForm({ product, onClose, isNew }: { product?: CatalogProduct; onClose: () => void; isNew: boolean }) {
  const [form, setForm] = useState<Partial<CatalogProduct>>(product || EMPTY_FORM);
  const [docInput, setDocInput] = useState("");
  const [eligInput, setEligInput] = useState("");
  const [featureInput, setFeatureInput] = useState("");
  const { toast } = useToast();

  const mutation = useMutation({
    mutationFn: async (data: Partial<CatalogProduct>) => {
      if (isNew) {
        const res = await apiRequest("POST", "/api/catalog-products", data, OFFICER_HEADERS);
        return res.json();
      } else {
        const res = await apiRequest("PATCH", `/api/catalog-products/${product!.id}`, data, OFFICER_HEADERS);
        return res.json();
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/catalog-products"] });
      toast({ title: isNew ? "Product Created" : "Product Updated", description: `${form.name} saved successfully.` });
      onClose();
    },
    onError: (error: Error) => {
      toast({ title: "Error", description: error.message, variant: "destructive" });
    },
  });

  const handleSubmit = () => {
    if (!form.name?.trim() || !form.code?.trim()) {
      toast({ title: "Validation Error", description: "Name and Product Code are required.", variant: "destructive" });
      return;
    }
    mutation.mutate(form);
  };

  const addToArray = (field: "requiredDocuments" | "eligibilityCriteria" | "features", value: string, setter: (v: string) => void) => {
    if (!value.trim()) return;
    setForm(prev => ({ ...prev, [field]: [...(prev[field] || []), value.trim()] }));
    setter("");
  };

  const removeFromArray = (field: "requiredDocuments" | "eligibilityCriteria" | "features", index: number) => {
    setForm(prev => ({ ...prev, [field]: (prev[field] || []).filter((_, i) => i !== index) }));
  };

  const Field = ({ label, children, span = 1 }: { label: string; children: React.ReactNode; span?: number }) => (
    <div className={span === 2 ? "col-span-2" : ""}>
      <label className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider block mb-1.5">{label}</label>
      {children}
    </div>
  );

  const inputCls = "w-full text-sm text-slate-800 dark:text-slate-100 bg-slate-50/80 dark:bg-white/[0.04] border-0 ring-1 ring-slate-200/60 dark:ring-white/[0.06] rounded-xl px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/30 dark:focus:ring-blue-400/20 placeholder:text-slate-300 dark:placeholder:text-slate-600 transition-all";
  const selectCls = `${inputCls} appearance-none`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 backdrop-blur-md p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-[#161820] rounded-2xl shadow-2xl dark:shadow-black/60 w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col ring-1 ring-black/[0.03] dark:ring-white/[0.04]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-gradient-to-r from-slate-50 to-blue-50/60 dark:from-[#1a1d28] dark:to-[#1a2235] px-6 py-4 border-b border-slate-100 dark:border-white/[0.06] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <CategoryIcon category={form.category || "other"} />
            <div>
              <h2 className="font-bold text-lg text-slate-800 dark:text-white">{isNew ? "New Loan Product" : "Edit Product"}</h2>
              <p className="text-xs text-slate-400 dark:text-slate-500">{isNew ? "Configure product parameters" : form.name}</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" className="rounded-xl text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/[0.06]" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Product Name *">
              <input data-testid="input-product-name" value={form.name || ""} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="e.g. Pradhan Mantri Awas Home Loan" className={inputCls} />
            </Field>
            <Field label="Product Code *">
              <input data-testid="input-product-code" value={form.code || ""} onChange={e => setForm(p => ({ ...p, code: e.target.value.toUpperCase() }))} placeholder="e.g. HL-PMAY-001" className={inputCls} />
            </Field>
            <Field label="Category">
              <select data-testid="select-category" value={form.category || ""} onChange={e => setForm(p => ({ ...p, category: e.target.value }))} className={selectCls}>
                {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </Field>
            <Field label="Status">
              <select data-testid="select-status" value={form.status || "draft"} onChange={e => setForm(p => ({ ...p, status: e.target.value }))} className={selectCls}>
                {STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
              </select>
            </Field>
            <Field label="Description" span={2}>
              <textarea data-testid="input-description" value={form.description || ""} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} placeholder="Brief description of this product..." rows={2} className={`${inputCls} resize-none`} />
            </Field>
          </div>

          <div className="border-t border-slate-100 dark:border-white/[0.04] pt-5">
            <h3 className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <IndianRupee className="w-3.5 h-3.5 text-blue-500 dark:text-blue-400" /> Pricing & Amounts
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Min Loan Amount">
                <input value={form.minAmount || ""} onChange={e => setForm(p => ({ ...p, minAmount: e.target.value }))} placeholder="₹3,00,000" className={inputCls} />
              </Field>
              <Field label="Max Loan Amount">
                <input value={form.maxAmount || ""} onChange={e => setForm(p => ({ ...p, maxAmount: e.target.value }))} placeholder="₹5,00,00,000" className={inputCls} />
              </Field>
              <Field label="Base Interest Rate (p.a.)">
                <input value={form.baseInterestRate || ""} onChange={e => setForm(p => ({ ...p, baseInterestRate: e.target.value }))} placeholder="8.50%" className={inputCls} />
              </Field>
              <Field label="Max Interest Rate (p.a.)">
                <input value={form.maxInterestRate || ""} onChange={e => setForm(p => ({ ...p, maxInterestRate: e.target.value }))} placeholder="14.00%" className={inputCls} />
              </Field>
              <Field label="Processing Fee (%)">
                <input value={form.processingFeePercent || ""} onChange={e => setForm(p => ({ ...p, processingFeePercent: e.target.value }))} placeholder="0.50%" className={inputCls} />
              </Field>
              <Field label="Prepayment Penalty">
                <input value={form.prepaymentPenalty || ""} onChange={e => setForm(p => ({ ...p, prepaymentPenalty: e.target.value }))} placeholder="Nil / 2% of outstanding" className={inputCls} />
              </Field>
            </div>
          </div>

          <div className="border-t border-slate-100 dark:border-white/[0.04] pt-5">
            <h3 className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" /> Tenure & Eligibility
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Min Tenure (months)">
                <input type="number" value={form.minTenureMonths || ""} onChange={e => setForm(p => ({ ...p, minTenureMonths: parseInt(e.target.value) || 0 }))} placeholder="12" className={inputCls} />
              </Field>
              <Field label="Max Tenure (months)">
                <input type="number" value={form.maxTenureMonths || ""} onChange={e => setForm(p => ({ ...p, maxTenureMonths: parseInt(e.target.value) || 0 }))} placeholder="360" className={inputCls} />
              </Field>
              <Field label="Min Credit Score">
                <input type="number" value={form.minCreditScore || ""} onChange={e => setForm(p => ({ ...p, minCreditScore: parseInt(e.target.value) || 0 }))} placeholder="650" className={inputCls} />
              </Field>
              <Field label="Min Monthly Income">
                <input value={form.minIncome || ""} onChange={e => setForm(p => ({ ...p, minIncome: e.target.value }))} placeholder="₹25,000" className={inputCls} />
              </Field>
              <Field label="Max LTV Ratio">
                <input value={form.maxLtv || ""} onChange={e => setForm(p => ({ ...p, maxLtv: e.target.value }))} placeholder="80%" className={inputCls} />
              </Field>
              <Field label="Risk Grade">
                <select value={form.riskGrade || ""} onChange={e => setForm(p => ({ ...p, riskGrade: e.target.value }))} className={selectCls}>
                  <option value="">Select</option>
                  {RISK_GRADES.map(g => <option key={g} value={g}>{g}</option>)}
                </select>
              </Field>
              <Field label="Target Segment">
                <input value={form.targetSegment || ""} onChange={e => setForm(p => ({ ...p, targetSegment: e.target.value }))} placeholder="Salaried professionals, Self-employed" className={inputCls} />
              </Field>
              <div className="flex items-center gap-6 pt-5">
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                  <input type="checkbox" checked={form.collateralRequired || false} onChange={e => setForm(p => ({ ...p, collateralRequired: e.target.checked }))} className="rounded border-slate-300 dark:border-slate-600 accent-blue-500" />
                  Collateral Required
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 cursor-pointer">
                  <input type="checkbox" checked={form.insuranceRequired || false} onChange={e => setForm(p => ({ ...p, insuranceRequired: e.target.checked }))} className="rounded border-slate-300 dark:border-slate-600 accent-blue-500" />
                  Insurance Required
                </label>
              </div>
            </div>
          </div>

          <div className="border-t border-slate-100 dark:border-white/[0.04] pt-5">
            <h3 className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-violet-500 dark:text-violet-400" /> Documents & Criteria
            </h3>
            <div className="space-y-4">
              <Field label="Required Documents" span={2}>
                <div className="flex gap-2 mb-2">
                  <input value={docInput} onChange={e => setDocInput(e.target.value)} onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addToArray("requiredDocuments", docInput, setDocInput))} placeholder="Add document (press Enter)" className={inputCls} />
                  <Button variant="ghost" size="sm" onClick={() => addToArray("requiredDocuments", docInput, setDocInput)} className="rounded-xl shrink-0 text-slate-400 hover:text-blue-500 hover:bg-blue-500/10"><Plus className="w-4 h-4" /></Button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {(form.requiredDocuments || []).map((doc, i) => (
                    <Badge key={i} className="text-[11px] bg-violet-500/10 text-violet-600 dark:text-violet-300 border-transparent gap-1 font-medium">
                      {doc}
                      <button onClick={() => removeFromArray("requiredDocuments", i)} className="hover:text-red-400 ml-0.5"><X className="w-3 h-3" /></button>
                    </Badge>
                  ))}
                </div>
              </Field>
              <Field label="Eligibility Criteria" span={2}>
                <div className="flex gap-2 mb-2">
                  <input value={eligInput} onChange={e => setEligInput(e.target.value)} onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addToArray("eligibilityCriteria", eligInput, setEligInput))} placeholder="Add criteria (press Enter)" className={inputCls} />
                  <Button variant="ghost" size="sm" onClick={() => addToArray("eligibilityCriteria", eligInput, setEligInput)} className="rounded-xl shrink-0 text-slate-400 hover:text-blue-500 hover:bg-blue-500/10"><Plus className="w-4 h-4" /></Button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {(form.eligibilityCriteria || []).map((c, i) => (
                    <Badge key={i} className="text-[11px] bg-blue-500/10 text-blue-600 dark:text-blue-300 border-transparent gap-1 font-medium">
                      {c}
                      <button onClick={() => removeFromArray("eligibilityCriteria", i)} className="hover:text-red-400 ml-0.5"><X className="w-3 h-3" /></button>
                    </Badge>
                  ))}
                </div>
              </Field>
              <Field label="Key Features" span={2}>
                <div className="flex gap-2 mb-2">
                  <input value={featureInput} onChange={e => setFeatureInput(e.target.value)} onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addToArray("features", featureInput, setFeatureInput))} placeholder="Add feature (press Enter)" className={inputCls} />
                  <Button variant="ghost" size="sm" onClick={() => addToArray("features", featureInput, setFeatureInput)} className="rounded-xl shrink-0 text-slate-400 hover:text-blue-500 hover:bg-blue-500/10"><Plus className="w-4 h-4" /></Button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {(form.features || []).map((f, i) => (
                    <Badge key={i} className="text-[11px] bg-sky-500/10 text-sky-600 dark:text-sky-300 border-transparent gap-1 font-medium">
                      {f}
                      <button onClick={() => removeFromArray("features", i)} className="hover:text-red-400 ml-0.5"><X className="w-3 h-3" /></button>
                    </Badge>
                  ))}
                </div>
              </Field>
            </div>
          </div>
        </div>

        <div className="shrink-0 px-6 py-4 border-t border-slate-100 dark:border-white/[0.06] flex items-center justify-end gap-3 bg-slate-50/50 dark:bg-white/[0.02]">
          <Button variant="ghost" onClick={onClose} className="rounded-xl text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300">Cancel</Button>
          <Button
            data-testid="button-save-product"
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg shadow-blue-600/20 dark:shadow-blue-900/40 gap-2 border-0"
          >
            <Save className="w-4 h-4" />
            {mutation.isPending ? "Saving..." : isNew ? "Create Product" : "Save Changes"}
          </Button>
        </div>
      </div>
    </div>
  );
}
