import { Bot, User, Banknote } from "lucide-react";
import type { Message, LoanProduct } from "@shared/schema";
import { LoanCard } from "./loan-card";

export function ChatBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const meta = message.metadata as any;
  const recommendations = meta?.loanRecommendations as LoanProduct[] | null;

  return (
    <div
      data-testid={`message-${message.id}`}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""} mb-5 anim-float-in`}
    >
      <div
        className={`w-9 h-9 rounded-2xl flex items-center justify-center shrink-0 shadow-sm ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-white dark:bg-[#1a1a1a] border border-slate-200/60 dark:border-white/[0.04] text-slate-500 dark:text-slate-400"
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      <div className={`flex flex-col gap-2 max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`${isUser ? "glass-bubble-user" : "glass-bubble-bot"} rounded-3xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
            isUser
              ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-br-lg"
              : "bg-white dark:bg-[#1a1a1a] border border-slate-200/60 dark:border-white/[0.04] text-gray-700 dark:text-slate-200 rounded-bl-lg"
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {recommendations && recommendations.length > 0 && (
          <div className="w-full space-y-3 mt-1">
            <div className="flex items-center gap-2 text-xs font-medium text-blue-600 dark:text-blue-400 pl-1">
              <Banknote className="w-3.5 h-3.5" />
              Recommended Borrowing Paths
              <div className="flex-1 h-px bg-gradient-to-r from-blue-300/40 dark:from-blue-500/20 to-transparent" />
            </div>
            <div className="grid gap-3">
              {recommendations.map((product, i) => (
                <LoanCard key={i} product={product} index={i} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
