interface IntentFieldProps {
  label: string;
  value: string;
  icon: any;
}

export function IntentField({ label, value, icon: Icon }: IntentFieldProps) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-3 py-2.5">
      <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-500/10">
        <Icon className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-widest text-gray-500 dark:text-slate-500 font-semibold mb-0.5">{label}</p>
        <p className="text-sm font-medium text-gray-900 dark:text-white">{value}</p>
      </div>
    </div>
  );
}
