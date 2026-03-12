import { Home, Car, Briefcase, GraduationCap, HeartPulse, Wallet } from "lucide-react";
import ksqLogo from "@assets/image_1773224776245.png";

const QUICK_PROMPTS = [
  { icon: Home, label: "Home Loan", prompt: "I'm looking to buy a home", color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-50 dark:bg-blue-950/50 border-blue-200/60 dark:border-blue-800/40 hover:bg-blue-100 dark:hover:bg-blue-900/40" },
  { icon: Car, label: "Auto Loan", prompt: "I want to finance a car purchase", color: "text-cyan-600 dark:text-cyan-400", bg: "bg-cyan-50 dark:bg-cyan-950/50 border-cyan-200/60 dark:border-cyan-800/40 hover:bg-cyan-100 dark:hover:bg-cyan-900/40" },
  { icon: Briefcase, label: "Business Loan", prompt: "I need funding to grow my business", color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-50 dark:bg-amber-950/50 border-amber-200/60 dark:border-amber-800/40 hover:bg-amber-100 dark:hover:bg-amber-900/40" },
  { icon: GraduationCap, label: "Education", prompt: "I need an education loan for studies", color: "text-purple-600 dark:text-purple-400", bg: "bg-purple-50 dark:bg-purple-950/50 border-purple-200/60 dark:border-purple-800/40 hover:bg-purple-100 dark:hover:bg-purple-900/40" },
  { icon: HeartPulse, label: "Medical", prompt: "I need funds for a medical expense", color: "text-rose-600 dark:text-rose-400", bg: "bg-rose-50 dark:bg-rose-950/50 border-rose-200/60 dark:border-rose-800/40 hover:bg-rose-100 dark:hover:bg-rose-900/40" },
  { icon: Wallet, label: "Personal Loan", prompt: "I need a personal loan", color: "text-indigo-600 dark:text-indigo-400", bg: "bg-indigo-50 dark:bg-indigo-950/50 border-indigo-200/60 dark:border-indigo-800/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/40" },
];

interface WelcomeStateProps {
  onPromptClick: (prompt: string) => void;
  isExiting: boolean;
}

export function WelcomeState({ onPromptClick, isExiting }: WelcomeStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-16 px-4 ${isExiting ? "anim-welcome-exit" : "animate-in fade-in duration-700"}`}>
      <div className="w-16 h-16 rounded-3xl bg-white dark:bg-white/10 flex items-center justify-center shadow-lg shadow-slate-200/50 dark:shadow-black/30 mb-6">
        <img src={ksqLogo} alt="KSquare" className="w-10 h-10 object-contain dark:brightness-0 dark:invert" />
      </div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2 tracking-tight" data-testid="text-welcome-title">
        Welcome to LoanAssist
      </h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 text-center max-w-md mb-8 leading-relaxed">
        Your personal loan advisor. Tell me what you need, and I'll find the smartest path to get you there.
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 max-w-lg w-full">
        {QUICK_PROMPTS.map((item, i) => (
          <button
            key={i}
            data-testid={`button-quick-prompt-${i}`}
            onClick={() => onPromptClick(item.prompt)}
            className={`glass-card flex flex-col items-center gap-2 p-4 rounded-3xl border shadow-sm ${item.bg} transition-all duration-200 hover:scale-[1.03] hover:shadow-md group cursor-pointer`}
          >
            <item.icon className={`w-5 h-5 ${item.color} group-hover:scale-110 transition-transform`} />
            <span className="text-xs font-medium text-gray-600 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white transition-colors">{item.label}</span>
          </button>
        ))}
      </div>
      <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-8">
        Or simply type what you need below — I'll understand.
      </p>
    </div>
  );
}
