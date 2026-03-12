import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient, OFFICER_HEADERS } from "@/lib/queryClient";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  Edit3,
  Save,
  X,
  IndianRupee,
  Briefcase,
  Home,
  FileText,
  Shield,
  TrendingUp,
  Percent,
  Calendar,
  Target,
  AlertCircle,
  Phone,
  Mail,
  UserCheck,
  Building2,
} from "lucide-react";
import type { Loan } from "@shared/schema";
import { LoanTypeIcon } from "./loan-type-icon";

export function EditableLoanCard({ loan, onClose }: { loan: Loan; onClose?: () => void }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<Partial<Loan>>({});
  const { toast } = useToast();
  const [localLoan, setLocalLoan] = useState<Loan>(loan);

  useEffect(() => {
    setLocalLoan(loan);
  }, [loan]);

  const updateLoan = useMutation({
    mutationFn: async (data: Partial<Loan>) => {
      const res = await apiRequest("PATCH", `/api/loans/${localLoan.id}`, data, OFFICER_HEADERS);
      return res.json();
    },
    onSuccess: (updatedLoan: Loan) => {
      setLocalLoan(updatedLoan);
      queryClient.invalidateQueries({ queryKey: ["/api/loans"] });
      setIsEditing(false);
      setEditData({});
      toast({ title: "Loan Updated", description: "Changes saved successfully." });
    },
    onError: (error: Error) => {
      toast({ title: "Error", description: error.message, variant: "destructive" });
    },
  });

  const startEdit = () => {
    setEditData({
      borrowerName: localLoan.borrowerName,
      borrowerEmail: localLoan.borrowerEmail,
      borrowerPhone: localLoan.borrowerPhone,
      loanType: localLoan.loanType,
      loanAmount: localLoan.loanAmount,
      interestRate: localLoan.interestRate,
      tenure: localLoan.tenure,
      monthlyEmi: localLoan.monthlyEmi,
      purpose: localLoan.purpose,
      employmentType: localLoan.employmentType,
      monthlyIncome: localLoan.monthlyIncome,
      existingDebts: localLoan.existingDebts,
      creditScore: localLoan.creditScore,
      collateral: localLoan.collateral,
      downPayment: localLoan.downPayment,
      propertyValue: localLoan.propertyValue,
      ltv: localLoan.ltv,
      notes: localLoan.notes,
    });
    setIsEditing(true);
  };

  const handleSave = () => {
    updateLoan.mutate(editData);
  };

  const fields: { key: keyof Loan; label: string; icon: any }[] = [
    { key: "borrowerName", label: "Borrower Name", icon: UserCheck },
    { key: "borrowerEmail", label: "Email", icon: Mail },
    { key: "borrowerPhone", label: "Phone", icon: Phone },
    { key: "loanType", label: "Loan Type", icon: FileText },
    { key: "loanAmount", label: "Loan Amount", icon: IndianRupee },
    { key: "interestRate", label: "Interest Rate", icon: Percent },
    { key: "tenure", label: "Tenure", icon: Calendar },
    { key: "monthlyEmi", label: "Monthly EMI", icon: TrendingUp },
    { key: "purpose", label: "Purpose", icon: Target },
    { key: "employmentType", label: "Employment", icon: Briefcase },
    { key: "monthlyIncome", label: "Monthly Income", icon: IndianRupee },
    { key: "existingDebts", label: "Existing Debts", icon: AlertCircle },
    { key: "creditScore", label: "Credit Score", icon: Shield },
    { key: "collateral", label: "Collateral", icon: Building2 },
    { key: "downPayment", label: "Down Payment", icon: IndianRupee },
    { key: "propertyValue", label: "Property Value", icon: Home },
    { key: "ltv", label: "LTV Ratio", icon: Percent },
  ];

  const statusColors: Record<string, string> = {
    draft: "bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-transparent",
    active: "bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border-transparent",
    approved: "bg-green-50 dark:bg-green-500/10 text-green-700 dark:text-green-400 border-transparent",
    rejected: "bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-400 border-transparent",
  };

  return (
    <div data-testid={`loan-card-${localLoan.id}`} className="glass-card bg-white dark:bg-[#1a1a1a] rounded-3xl border border-slate-200/40 dark:border-white/[0.04] shadow-sm overflow-hidden anim-float-in">
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-500/10 dark:to-indigo-500/10 px-4 py-3 border-b border-gray-100/60 dark:border-white/[0.04]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-blue-100 dark:bg-blue-500/20 flex items-center justify-center text-blue-600 dark:text-blue-400">
              <LoanTypeIcon type={localLoan.loanType} />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{localLoan.borrowerName}</h4>
              <p className="text-[10px] text-gray-500 dark:text-gray-400">{localLoan.loanType} — {localLoan.loanAmount}</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <Badge className={`text-[10px] border ${statusColors[localLoan.status] || statusColors.draft}`}>
              {localLoan.status}
            </Badge>
            {isEditing ? (
              <>
                <Button data-testid="button-save-loan" variant="ghost" size="icon" className="h-7 w-7 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-500/10" onClick={handleSave} disabled={updateLoan.isPending}>
                  <Save className="w-3.5 h-3.5" />
                </Button>
                <Button data-testid="button-cancel-edit" variant="ghost" size="icon" className="h-7 w-7 text-gray-400 hover:bg-gray-50 dark:hover:bg-white/10" onClick={() => { setIsEditing(false); setEditData({}); }}>
                  <X className="w-3.5 h-3.5" />
                </Button>
              </>
            ) : (
              <Button data-testid="button-edit-loan" variant="ghost" size="icon" className="h-7 w-7 text-gray-400 hover:bg-gray-50 dark:hover:bg-white/10 hover:text-blue-600 dark:hover:text-blue-400" onClick={startEdit}>
                <Edit3 className="w-3.5 h-3.5" />
              </Button>
            )}
            {onClose && (
              <Button variant="ghost" size="icon" className="h-7 w-7 text-gray-400 hover:bg-gray-50 dark:hover:bg-white/10" onClick={onClose}>
                <X className="w-3.5 h-3.5" />
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="p-3 space-y-0.5 max-h-[400px] overflow-y-auto">
        {fields.map(({ key, label, icon: Icon }) => {
          const value = isEditing ? (editData[key] as string) || "" : (localLoan[key] as string) || "";
          if (!isEditing && !value) return null;

          return (
            <div key={key} className="flex items-start gap-2 py-1.5 px-2 rounded-xl hover:bg-gray-50 dark:hover:bg-white/5 transition-colors group">
              <Icon className="w-3.5 h-3.5 text-gray-400 dark:text-gray-500 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-[10px] text-gray-400 dark:text-gray-500 font-medium uppercase tracking-wider">{label}</p>
                {isEditing ? (
                  <input
                    data-testid={`input-loan-${key}`}
                    type="text"
                    value={value}
                    onChange={(e) => setEditData(prev => ({ ...prev, [key]: e.target.value }))}
                    className="glass-input w-full text-xs text-gray-800 dark:text-gray-200 bg-white dark:bg-white/5 border border-slate-200/40 dark:border-white/[0.04] rounded-lg px-2 py-1 mt-0.5 focus:outline-none focus:ring-1 focus:ring-blue-300 dark:focus:ring-blue-500/30 focus:border-blue-300 dark:focus:border-blue-500/30"
                  />
                ) : (
                  <p className="text-xs text-gray-700 dark:text-gray-300 break-words">{value}</p>
                )}
              </div>
            </div>
          );
        })}

        {(isEditing ? true : !!localLoan.notes) && (
          <div className="py-1.5 px-2 rounded-xl hover:bg-gray-50 dark:hover:bg-white/5">
            <div className="flex items-start gap-2">
              <FileText className="w-3.5 h-3.5 text-gray-400 dark:text-gray-500 mt-0.5 shrink-0" />
              <div className="flex-1">
                <p className="text-[10px] text-gray-400 dark:text-gray-500 font-medium uppercase tracking-wider">AI Notes</p>
                {isEditing ? (
                  <textarea
                    data-testid="input-loan-notes"
                    value={(editData.notes as string) || ""}
                    onChange={(e) => setEditData(prev => ({ ...prev, notes: e.target.value }))}
                    className="glass-input w-full text-xs text-gray-800 dark:text-gray-200 bg-white dark:bg-white/5 border border-slate-200/40 dark:border-white/[0.04] rounded-lg px-2 py-1 mt-0.5 focus:outline-none focus:ring-1 focus:ring-blue-300 dark:focus:ring-blue-500/30 resize-none"
                    rows={3}
                  />
                ) : (
                  <p className="text-xs text-gray-600 dark:text-gray-400 italic">{localLoan.notes}</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
