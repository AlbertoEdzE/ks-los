interface ScoreRingProps {
  score: number;
  label: string;
  color: string;
  glowColor: string;
}

export function ScoreRing({ score, label, color, glowColor }: ScoreRingProps) {
  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-[76px] h-[76px]">
        <div className={`absolute inset-0 rounded-full ${glowColor} blur-xl opacity-30`} />
        <svg className="w-[76px] h-[76px] -rotate-90 relative z-10" viewBox="0 0 68 68">
          <circle cx="34" cy="34" r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="4" />
          <circle cx="34" cy="34" r={radius} fill="none" stroke={color} strokeWidth="4.5" strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" className="transition-all duration-1000 ease-out" />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center z-20">
          <span className="text-lg font-bold text-gray-900 dark:text-white">{score}</span>
        </div>
      </div>
      <span className="text-[10px] uppercase tracking-widest text-gray-500 dark:text-slate-400 font-semibold">{label}</span>
    </div>
  );
}
