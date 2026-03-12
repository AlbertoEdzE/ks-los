import { MessageSquare } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8">
      <div className="w-20 h-20 rounded-2xl bg-gray-100 dark:bg-[#1a1a2e] flex items-center justify-center mb-5">
        <MessageSquare className="w-9 h-9 text-gray-400 dark:text-slate-500" />
      </div>
      <h3 className="font-bold text-lg mb-1.5 text-gray-900 dark:text-white">Select a Lead</h3>
      <p className="text-sm text-gray-600 dark:text-slate-400 max-w-xs leading-relaxed">
        Choose a conversation from the left to view intent analysis, scores, and AI-recommended products.
      </p>
    </div>
  );
}
