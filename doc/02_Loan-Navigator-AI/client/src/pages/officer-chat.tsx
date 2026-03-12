import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient, OFFICER_HEADERS } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { ThemeToggle } from "@/components/theme-provider";
import {
  Send,
  MessageSquarePlus,
  LayoutDashboard,
  Workflow,
  MessageSquare,
  FileText,
} from "lucide-react";
import { Link } from "wouter";
import type { Message, LoanPhase, Loan } from "@shared/schema";
import ksqLogo from "@assets/image_1773224776245.png";
import { LifecyclePipeline } from "@/components/officer/lifecycle-pipeline";
import { LoansPanel } from "@/components/officer/loans-panel";
import { OfficerChatBubble } from "@/components/officer/officer-chat-bubble";
import { OfficerTypingIndicator } from "@/components/officer/officer-typing-indicator";

export default function OfficerChat() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [sidebarTab, setSidebarTab] = useState<"pipeline" | "loans">("pipeline");
  const scrollRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const phasesQuery = useQuery<LoanPhase[]>({
    queryKey: ["/api/phases"],
    refetchInterval: 5000,
  });

  const loansQuery = useQuery<Loan[]>({
    queryKey: ["/api/loans"],
    refetchInterval: 5000,
    queryFn: async () => {
      const res = await fetch("/api/loans", { headers: OFFICER_HEADERS });
      if (!res.ok) throw new Error("Failed to fetch loans");
      return res.json();
    },
  });

  const createConversation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/conversations", { chatRole: "officer" }, OFFICER_HEADERS);
      return res.json();
    },
    onSuccess: (data) => {
      setConversationId(data.conversation.id);
    },
    onError: (error: Error) => {
      toast({ title: "Error", description: error.message, variant: "destructive" });
    },
  });

  const messagesQuery = useQuery<Message[]>({
    queryKey: ["/api/conversations", conversationId, "messages"],
    enabled: !!conversationId,
    refetchInterval: false,
  });

  const sendMessage = useMutation({
    mutationFn: async (content: string) => {
      const res = await apiRequest("POST", `/api/conversations/${conversationId}/messages`, { content }, OFFICER_HEADERS);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/conversations", conversationId, "messages"] });
      queryClient.invalidateQueries({ queryKey: ["/api/phases"] });
      queryClient.invalidateQueries({ queryKey: ["/api/loans"] });
    },
    onError: (error: Error) => {
      toast({ title: "Error", description: error.message, variant: "destructive" });
    },
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messagesQuery.data, sendMessage.isPending]);

  useEffect(() => {
    if (!conversationId) {
      createConversation.mutate();
    }
  }, []);

  const handleSend = () => {
    if (!input.trim() || sendMessage.isPending) return;
    sendMessage.mutate(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    setConversationId(null);
    setInput("");
    createConversation.mutate();
  };

  const isLoading = createConversation.isPending || messagesQuery.isLoading;
  const messages = messagesQuery.data || [];
  const phases = phasesQuery.data || [];

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d] relative overflow-hidden">
      <div className="absolute top-[-200px] left-1/4 w-[600px] h-[600px] bg-blue-200/15 dark:bg-blue-500/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-150px] right-1/4 w-[500px] h-[500px] bg-indigo-200/10 dark:bg-indigo-500/3 rounded-full blur-[100px] pointer-events-none" />

      <div className="glass-surface w-[340px] shrink-0 border-r border-slate-200/40 dark:border-white/[0.04] flex flex-col bg-white/70 dark:bg-[#141414]/80 backdrop-blur-xl relative z-10">
        <div className="p-4 border-b border-slate-200/40 dark:border-white/[0.04]">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-9 h-9 rounded-2xl bg-white dark:bg-white/10 flex items-center justify-center shadow-sm">
              <img src={ksqLogo} alt="KSquare" className="w-6 h-6 object-contain dark:brightness-0 dark:invert" />
            </div>
            <div>
              <h2 className="font-semibold text-sm text-gray-900 dark:text-white">Officer Workspace</h2>
              <p className="text-[10px] text-gray-500 dark:text-gray-400">Pipeline & loan management</p>
            </div>
          </div>
          <div className="flex gap-1 bg-gray-100 dark:bg-white/8 rounded-2xl p-0.5">
            <button
              data-testid="tab-pipeline"
              onClick={() => setSidebarTab("pipeline")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-xl text-[11px] font-medium transition-all ${
                sidebarTab === "pipeline"
                  ? "bg-white dark:bg-white/15 text-gray-900 dark:text-white shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
              }`}
            >
              <Workflow className="w-3 h-3" />
              Pipeline
            </button>
            <button
              data-testid="tab-loans"
              onClick={() => setSidebarTab("loans")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-xl text-[11px] font-medium transition-all ${
                sidebarTab === "loans"
                  ? "bg-white dark:bg-white/15 text-gray-900 dark:text-white shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
              }`}
            >
              <FileText className="w-3 h-3" />
              Loans
              {(loansQuery.data?.length || 0) > 0 && (
                <span className="bg-blue-500 text-white text-[9px] rounded-full w-4 h-4 flex items-center justify-center">
                  {loansQuery.data?.length}
                </span>
              )}
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {sidebarTab === "pipeline" ? (
            phasesQuery.isLoading ? (
              <div className="p-4 space-y-2">
                {Array(5).fill(0).map((_, i) => (
                  <div key={i} className="h-10 rounded-2xl bg-gray-100 dark:bg-white/8 animate-pulse" />
                ))}
              </div>
            ) : (
              <LifecyclePipeline phases={phases} />
            )
          ) : (
            loansQuery.isLoading ? (
              <div className="p-4 space-y-2">
                {Array(3).fill(0).map((_, i) => (
                  <div key={i} className="h-14 rounded-2xl bg-gray-100 dark:bg-white/8 animate-pulse" />
                ))}
              </div>
            ) : (
              <LoansPanel loans={loansQuery.data || []} />
            )
          )}
        </div>
        <div className="p-3 border-t border-slate-200/40 dark:border-white/[0.04] space-y-2">
          <Link href="/dashboard">
            <Button data-testid="link-officer-dashboard" variant="outline" size="sm" className="w-full gap-2 bg-white/80 dark:bg-white/[0.06] border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm text-xs">
              <LayoutDashboard className="w-3.5 h-3.5" />
              Officer Dashboard
            </Button>
          </Link>
          <Link href="/">
            <Button data-testid="link-borrower-chat" variant="outline" size="sm" className="w-full gap-2 bg-white/80 dark:bg-white/[0.06] border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm text-xs">
              <MessageSquare className="w-3.5 h-3.5" />
              Borrower Chat
            </Button>
          </Link>
        </div>
      </div>

      <div className="flex-1 flex flex-col relative z-10">
        <header className="glass-header border-b border-slate-200/40 dark:border-white/[0.04] px-6 py-4 flex items-center justify-between bg-white/70 dark:bg-[#141414]/80 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-white dark:bg-white/10 flex items-center justify-center shadow-sm">
              <img src={ksqLogo} alt="KSquare" className="w-7 h-7 object-contain dark:brightness-0 dark:invert" />
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-tight text-gray-900 dark:text-white" data-testid="text-officer-chat-title">
                Loan Officer Assistant
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">Manage pipeline & create loans via chat</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button
              data-testid="button-officer-new-chat"
              variant="outline"
              size="sm"
              onClick={handleNewChat}
              className="gap-2 bg-white/80 dark:bg-white/[0.06] border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm"
            >
              <MessageSquarePlus className="w-4 h-4" />
              New Session
            </Button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-4 md:px-0" ref={scrollRef}>
          <div className="max-w-2xl mx-auto py-6 space-y-0">
            {isLoading ? (
              <div className="space-y-4">
                <div className="flex gap-3">
                  <div className="w-9 h-9 rounded-2xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                  <div className="h-20 w-72 rounded-3xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <OfficerChatBubble key={msg.id} message={msg} />
                ))}
                {sendMessage.isPending && <OfficerTypingIndicator />}
              </>
            )}
          </div>
        </div>

        <div className="glass-header border-t border-slate-200/40 dark:border-white/[0.04] p-4 bg-white/70 dark:bg-[#141414]/80 backdrop-blur-xl">
          <div className="max-w-2xl mx-auto">
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <textarea
                  data-testid="input-officer-chat-message"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="e.g. Create a home loan for Rajesh Kumar, 45 lakhs, IT professional earning 1.5L/month"
                  disabled={sendMessage.isPending || isLoading}
                  rows={1}
                  className="glass-input w-full resize-none rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.04] px-4 py-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-400/30 dark:focus:ring-blue-500/20 focus:border-blue-300 dark:focus:border-blue-500/30 transition-all placeholder:text-gray-400 dark:placeholder:text-gray-500 disabled:opacity-50 shadow-sm"
                  style={{ minHeight: "48px", maxHeight: "120px" }}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;
                    target.style.height = "48px";
                    target.style.height = Math.min(target.scrollHeight, 120) + "px";
                  }}
                />
              </div>
              <Button
                data-testid="button-officer-send"
                onClick={handleSend}
                disabled={!input.trim() || sendMessage.isPending || isLoading}
                size="icon"
                className="rounded-2xl h-12 w-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg shadow-blue-600/20 dark:shadow-blue-900/40 transition-all duration-200 border-0 disabled:opacity-30"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-[10px] text-gray-400 dark:text-gray-500 text-center mt-2.5">
              Create loans, manage pipeline phases, or ask about loan processing — all through chat.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
