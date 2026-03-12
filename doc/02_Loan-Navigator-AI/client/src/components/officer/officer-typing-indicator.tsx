import { Bot } from "lucide-react";

export function OfficerTypingIndicator() {
  return (
    <div className="flex gap-3 mb-5">
      <div className="w-9 h-9 rounded-2xl flex items-center justify-center shrink-0 bg-white dark:bg-[#1a1a1a] border border-slate-200/40 dark:border-white/[0.04] text-gray-500 dark:text-gray-400 shadow-sm">
        <Bot className="w-4 h-4" />
      </div>
      <div className="glass-bubble-bot bg-white dark:bg-[#1a1a1a] border border-slate-200/40 dark:border-white/[0.04] rounded-3xl rounded-bl-lg px-5 py-3.5 shadow-sm">
        <div className="flex gap-1.5">
          <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: "0ms" }} />
          <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: "150ms" }} />
          <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  );
}
