import { Home, Car, GraduationCap, Building2, CreditCard } from "lucide-react";

export function LoanTypeIcon({ type }: { type: string }) {
  const t = type.toLowerCase();
  if (t.includes("home") || t.includes("mortgage")) return <Home className="w-3.5 h-3.5" />;
  if (t.includes("car") || t.includes("auto") || t.includes("vehicle")) return <Car className="w-3.5 h-3.5" />;
  if (t.includes("education") || t.includes("student")) return <GraduationCap className="w-3.5 h-3.5" />;
  if (t.includes("business")) return <Building2 className="w-3.5 h-3.5" />;
  return <CreditCard className="w-3.5 h-3.5" />;
}
