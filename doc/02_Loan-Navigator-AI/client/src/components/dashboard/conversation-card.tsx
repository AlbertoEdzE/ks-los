import { Badge } from "@/components/ui/badge";
import { MessageSquare, Gauge, Target } from "lucide-react";
import type { Conversation } from "@shared/schema";

interface ConversationCardProps {
  conversation: Conversation;
  isSelected: boolean;
  onClick: () => void;
}

export function ConversationCard({ conversation, isSelected, onClick }: ConversationCardProps) {
  const intent = conversation.intentSummary as Record<string, string> | null;
  const urgencyColors: Record<string, string> = {
    low: "bg-slate-100 dark:bg-slate-400/15 text-slate-700 dark:text-slate-300",
    medium: "bg-amber-100 dark:bg-amber-400/20 text-amber-800 dark:text-amber-300",
    high: "bg-orange-100 dark:bg-orange-400/20 text-orange-800 dark:text-orange-300",
    critical: "bg-red-100 dark:bg-red-400/20 text-red-700 dark:text-red-300",
  };
  const statusConfig: Record<string, { label: string; cls: string }> = {
    active: { label: "Active", cls: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-500/20" },
    reviewing: { label: "Review", cls: "bg-blue-500/15 text-blue-600 dark:text-blue-400 ring-1 ring-blue-500/20" },
    qualified: { label: "Qualified", cls: "bg-violet-500/15 text-violet-600 dark:text-violet-400 ring-1 ring-violet-500/20" },
    archived: { label: "Archived", cls: "bg-gray-200 dark:bg-white/10 text-gray-500 dark:text-gray-400" },
  };
  const status = statusConfig[conversation.status] || statusConfig.active;

  return (
    <div
      data-testid={`card-conversation-${conversation.id}`}
      className={`cursor-pointer transition-all duration-300 ease-out rounded-xl p-3.5 ${
        isSelected
          ? "bg-blue-500/10 dark:bg-blue-500/[0.15] ring-1 ring-blue-400/30 dark:ring-blue-400/25 shadow-lg shadow-blue-500/10"
          : "hover:bg-white/80 dark:hover:bg-white/[0.06]"
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-1.5">
        <div className="flex items-center gap-2.5">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            isSelected ? "bg-blue-500 dark:bg-blue-500" : "bg-gray-100 dark:bg-[#252538]"
          }`}>
            <MessageSquare className={`w-3.5 h-3.5 ${isSelected ? "text-white" : "text-gray-500 dark:text-slate-400"}`} />
          </div>
          <div>
            <p className={`font-semibold text-[13px] leading-tight ${isSelected ? "text-blue-700 dark:text-blue-300" : "text-gray-900 dark:text-white"}`}>
              {conversation.borrowerName || `Lead #${conversation.id.slice(0, 8)}`}
            </p>
            <p className="text-[10px] text-gray-500 dark:text-slate-500 mt-0.5">
              {conversation.createdAt
                ? new Date(conversation.createdAt).toLocaleDateString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
                : "Just now"}
            </p>
          </div>
        </div>
        <Badge className={`text-[9px] font-bold px-2 py-0.5 rounded-full border-0 ${status.cls}`}>
          {status.label}
        </Badge>
      </div>

      {intent?.purpose && intent.purpose !== "Unknown" && (
        <p className="text-[11px] text-gray-600 dark:text-slate-400 mb-1.5 line-clamp-1 pl-[42px]">
          {intent.purpose}
        </p>
      )}

      <div className="flex items-center gap-1.5 pl-[42px]">
        {intent?.urgency && intent.urgency !== "Unknown" && (
          <Badge className={`text-[9px] font-semibold border-0 px-1.5 py-0 rounded-full ${urgencyColors[intent.urgency] || ""}`}>
            {intent.urgency.charAt(0).toUpperCase() + intent.urgency.slice(1)}
          </Badge>
        )}
        {conversation.seriousnessScore != null && conversation.seriousnessScore > 0 && (
          <Badge className="text-[9px] gap-0.5 bg-gray-100 dark:bg-white/[0.08] text-gray-700 dark:text-slate-300 border-0 px-1.5 py-0 rounded-full font-semibold">
            <Gauge className="w-2.5 h-2.5" />
            {conversation.seriousnessScore}%
          </Badge>
        )}
        {conversation.fitScore != null && conversation.fitScore > 0 && (
          <Badge className="text-[9px] gap-0.5 bg-gray-100 dark:bg-white/[0.08] text-gray-700 dark:text-slate-300 border-0 px-1.5 py-0 rounded-full font-semibold">
            <Target className="w-2.5 h-2.5" />
            {conversation.fitScore}%
          </Badge>
        )}
      </div>
    </div>
  );
}
