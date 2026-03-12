import {
  Home,
  Car,
  GraduationCap,
  Briefcase,
  HeartPulse,
  CreditCard,
  Building2,
  Wallet,
  Package,
  Gem,
} from "lucide-react";

export const CATEGORIES = [
  { value: "home_loan", label: "Home Loan", icon: Home, color: "#3b82f6" },
  { value: "auto_loan", label: "Auto Loan", icon: Car, color: "#0ea5e9" },
  { value: "personal_loan", label: "Personal Loan", icon: Wallet, color: "#6366f1" },
  { value: "business_loan", label: "Business Loan", icon: Briefcase, color: "#f59e0b" },
  { value: "education_loan", label: "Education Loan", icon: GraduationCap, color: "#8b5cf6" },
  { value: "medical_loan", label: "Medical Loan", icon: HeartPulse, color: "#ef4444" },
  { value: "gold_loan", label: "Gold Loan", icon: Gem, color: "#d97706" },
  { value: "lap", label: "Loan Against Property", icon: Building2, color: "#475569" },
  { value: "credit_line", label: "Credit Line", icon: CreditCard, color: "#ec4899" },
  { value: "other", label: "Other", icon: Package, color: "#64748b" },
];

export const RISK_GRADES = ["AAA", "AA", "A", "BBB", "BB", "B", "C"];
export const STATUSES = ["draft", "active", "suspended", "archived"];

export function getCategoryMeta(cat: string) {
  return CATEGORIES.find(c => c.value === cat) || CATEGORIES[CATEGORIES.length - 1];
}

export function formatTenure(months: number | null) {
  if (!months) return "—";
  if (months >= 12) return `${Math.floor(months / 12)} yr${months >= 24 ? "s" : ""}`;
  return `${months} mo`;
}
