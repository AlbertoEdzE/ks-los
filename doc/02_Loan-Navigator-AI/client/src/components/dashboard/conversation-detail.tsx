import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  MessageSquare,
  TrendingUp,
  Target,
  AlertCircle,
  CheckCircle2,
  Clock,
  Banknote,
  Brain,
  Gauge,
  Lightbulb,
  Eye,
  UserCheck,
  Zap,
  Sparkles,
  ShieldCheck,
  Users,
} from "lucide-react";
import type { Conversation, Message, LoanProduct } from "@shared/schema";
import { GlassPanel } from "@/components/layout/glass-panel";
import { ScoreRing } from "./score-ring";
import { IntentField } from "./intent-field";
import { EmptyState } from "./empty-state";

export function ConversationDetail({ conversationId }: { conversationId: string }) {
  const { toast } = useToast();

  const conversationQuery = useQuery<Conversation>({ queryKey: ["/api/conversations", conversationId] });
  const messagesQuery = useQuery<Message[]>({ queryKey: ["/api/conversations", conversationId, "messages"] });

  const updateStatus = useMutation({
    mutationFn: async (status: string) => {
      const res = await apiRequest("PATCH", `/api/conversations/${conversationId}`, { status });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/conversations", conversationId] });
      queryClient.invalidateQueries({ queryKey: ["/api/conversations"] });
      toast({ title: "Status updated" });
    },
  });

  if (conversationQuery.isLoading) {
    return (
      <div className="space-y-4 p-6">
        <div className="h-8 w-48 rounded-lg bg-gray-200 dark:bg-white/10 animate-pulse" />
        <div className="h-32 w-full rounded-xl bg-gray-200 dark:bg-white/10 animate-pulse" />
      </div>
    );
  }

  const conversation = conversationQuery.data;
  if (!conversation) return <EmptyState />;

  const intent = conversation.intentSummary as any;
  const products = conversation.recommendedProducts as LoanProduct[] | null;
  const msgs = messagesQuery.data || [];

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white" data-testid="text-lead-title">
              {conversation.borrowerName || `Lead #${conversation.id.slice(0, 8)}`}
            </h2>
            <p className="text-sm text-gray-600 dark:text-slate-400">
              Conversation started{" "}
              {conversation.createdAt
                ? new Date(conversation.createdAt).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" })
                : "recently"}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              data-testid="button-mark-reviewing"
              variant="outline"
              size="sm"
              onClick={() => updateStatus.mutate("reviewing")}
              disabled={conversation.status === "reviewing"}
              className="bg-white dark:bg-[#1e1e30] border-gray-300 dark:border-[#3a3a50] text-gray-800 dark:text-white hover:bg-gray-50 dark:hover:bg-[#252540] shadow-sm"
            >
              <Eye className="w-3.5 h-3.5 mr-1.5" />
              Review
            </Button>
            <Button
              data-testid="button-mark-qualified"
              size="sm"
              onClick={() => updateStatus.mutate("qualified")}
              disabled={conversation.status === "qualified"}
              className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white hover:from-blue-600 hover:to-indigo-700 border-0 shadow-lg shadow-blue-500/25"
            >
              <UserCheck className="w-3.5 h-3.5 mr-1.5" />
              Qualify
            </Button>
          </div>
        </div>

        {(conversation.seriousnessScore || conversation.fitScore) && (
          <GlassPanel className="p-6">
            <div className="flex items-center gap-10 justify-center">
              {conversation.seriousnessScore != null && (
                <ScoreRing score={conversation.seriousnessScore} label="Seriousness" color="#22c55e" glowColor="bg-green-400" />
              )}
              {conversation.fitScore != null && (
                <ScoreRing score={conversation.fitScore} label="Fit Score" color="#3b82f6" glowColor="bg-blue-400" />
              )}
            </div>
          </GlassPanel>
        )}

        {conversation.nextConversationAngle && (
          <GlassPanel className="bg-blue-50/80 dark:bg-blue-500/[0.08] border-blue-200/50 dark:border-blue-400/20">
            <div className="p-4 flex items-start gap-3">
              <div className="p-2 rounded-xl bg-blue-100 dark:bg-blue-500/20">
                <Lightbulb className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-blue-700 dark:text-blue-400 mb-1">Suggested Approach</p>
                <p className="text-sm text-gray-800 dark:text-slate-200 leading-relaxed">{conversation.nextConversationAngle}</p>
              </div>
            </div>
          </GlassPanel>
        )}

        {intent && (
          <GlassPanel>
            <div className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <Brain className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <h3 className="text-sm font-bold text-gray-900 dark:text-white">Intent Summary</h3>
              </div>
              <div className="grid grid-cols-2 gap-x-6">
                <IntentField label="Purpose" value={intent.purpose} icon={Target} />
                <IntentField label="Urgency" value={intent.urgency} icon={Zap} />
                <IntentField label="Monthly Income" value={intent.monthlyIncome} icon={Banknote} />
                <IntentField label="Loan Amount" value={intent.loanAmount} icon={TrendingUp} />
                <IntentField label="Existing Debts" value={intent.existingDebts} icon={AlertCircle} />
                <IntentField label="Employment" value={intent.employmentType} icon={Users} />
                <IntentField label="Preferred Tenure" value={intent.preferredTenure} icon={Clock} />
                <IntentField label="Collateral" value={intent.collateralAvailable} icon={ShieldCheck} />
                <IntentField label="Credit History" value={intent.creditHistory} icon={CheckCircle2} />
                <IntentField label="Affordability" value={intent.affordability} icon={Gauge} />
              </div>
            </div>
          </GlassPanel>
        )}

        {products && products.length > 0 && (
          <GlassPanel>
            <div className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <h3 className="text-sm font-bold text-gray-900 dark:text-white">AI-Recommended Products</h3>
              </div>
              <div className="space-y-3">
                {products.map((product, i) => (
                  <div
                    key={i}
                    data-testid={`product-recommendation-${i}`}
                    className="p-4 rounded-xl bg-gray-50 dark:bg-[#1a1a2e]/60 border border-gray-100 dark:border-[#2a2a3d]/60 hover:bg-gray-100 dark:hover:bg-[#1e1e35]/80 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <p className="font-semibold text-sm text-gray-900 dark:text-white">{product.name}</p>
                        <p className="text-xs text-gray-500 dark:text-slate-400">{product.type}</p>
                      </div>
                      <Badge className="text-[10px] bg-gray-200 dark:bg-white/[0.1] text-gray-700 dark:text-slate-300 border-0 font-semibold">
                        {product.approvalSpeed}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <span className="text-gray-500 dark:text-slate-500">Rate:</span>{" "}
                        <span className="font-semibold text-gray-800 dark:text-white">{product.estimatedRate}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-slate-500">EMI:</span>{" "}
                        <span className="font-semibold text-gray-800 dark:text-white">{product.estimatedEmi}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-slate-500">Tenure:</span>{" "}
                        <span className="font-semibold text-gray-800 dark:text-white">{product.tenure}</span>
                      </div>
                    </div>
                    <p className="text-xs text-blue-600 dark:text-blue-400 mt-2.5 flex items-center gap-1.5 font-medium">
                      <Sparkles className="w-3 h-3" />
                      {product.recommendation}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </GlassPanel>
        )}

        <GlassPanel>
          <div className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <MessageSquare className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <h3 className="text-sm font-bold text-gray-900 dark:text-white" data-testid="tab-transcript">Chat Transcript</h3>
            </div>
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
              {messagesQuery.isLoading ? (
                <div className="space-y-3">
                  <div className="h-12 w-full rounded-xl bg-gray-200 dark:bg-white/10 animate-pulse" />
                  <div className="h-12 w-3/4 rounded-xl bg-gray-200 dark:bg-white/10 animate-pulse" />
                </div>
              ) : msgs.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-slate-400 text-center py-4">No messages yet</p>
              ) : (
                msgs.map((msg) => (
                  <div key={msg.id} className={`flex gap-2.5 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-[9px] font-bold ${
                      msg.role === "user"
                        ? "bg-blue-500 text-white"
                        : "bg-gray-200 dark:bg-[#252538] text-gray-600 dark:text-slate-300"
                    }`}>
                      {msg.role === "user" ? "B" : "AI"}
                    </div>
                    <div className={`text-[13px] p-3.5 rounded-xl max-w-[85%] leading-relaxed ${
                      msg.role === "user"
                        ? "bg-blue-500 text-white text-right"
                        : "bg-gray-100 dark:bg-[#1a1a2e]/80 border border-gray-200/50 dark:border-[#2a2a3d]/50 text-gray-800 dark:text-slate-200"
                    }`}>
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      <p className={`text-[10px] mt-1.5 ${msg.role === "user" ? "text-blue-200" : "text-gray-400 dark:text-slate-500"}`}>
                        {msg.createdAt ? new Date(msg.createdAt).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : ""}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </GlassPanel>
      </div>
    </div>
  );
}
