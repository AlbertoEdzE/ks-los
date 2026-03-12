import { Bot, Settings } from "lucide-react";
import type { Message } from "@shared/schema";
import { PhaseActionResult } from "./phase-action-result";
import { LoanActionResult } from "./loan-action-result";

export function OfficerChatBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const meta = message.metadata as any;

  return (
    <div
      data-testid={`officer-message-${message.id}`}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""} mb-5 anim-float-in`}
    >
      <div
        className={`w-9 h-9 rounded-2xl flex items-center justify-center shrink-0 border shadow-sm ${
          isUser
            ? "bg-blue-500 border-blue-400 text-white"
            : "bg-white dark:bg-[#1a1a1a] border-slate-200/40 dark:border-white/[0.04] text-gray-500 dark:text-gray-400"
        }`}
      >
        {isUser ? <Settings className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      <div className={`flex flex-col gap-1 max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-3xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
            isUser
              ? "glass-bubble-user bg-blue-500 text-white rounded-br-lg"
              : "glass-bubble-bot bg-white dark:bg-[#1a1a1a] border border-slate-200/40 dark:border-white/[0.04] text-gray-700 dark:text-gray-200 rounded-bl-lg"
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {!isUser && <PhaseActionResult metadata={meta} />}
        {!isUser && <LoanActionResult metadata={meta} />}
      </div>
    </div>
  );
}
