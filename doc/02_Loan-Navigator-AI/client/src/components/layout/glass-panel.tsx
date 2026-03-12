interface GlassPanelProps {
  children: React.ReactNode;
  className?: string;
}

export function GlassPanel({ children, className = "" }: GlassPanelProps) {
  return (
    <div className={`rounded-2xl bg-white/95 dark:bg-[#151520]/80 backdrop-blur-2xl border border-gray-200/50 dark:border-[#2a2a3d]/60 shadow-xl shadow-black/[0.04] dark:shadow-black/40 ${className}`}>
      {children}
    </div>
  );
}
