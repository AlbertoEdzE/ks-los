import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { ThemeToggle } from "@/components/theme-provider";
import { Send, MessageSquarePlus, LayoutDashboard } from "lucide-react";
import { Link } from "wouter";
import type { Message, LoanPhase, Conversation } from "@shared/schema";
import ksqLogo from "@assets/image_1773224776245.png";
import { PhaseProgressTracker } from "@/components/chat/phase-tracker";
import { ChatBubble } from "@/components/chat/chat-bubble";
import { TypingIndicator } from "@/components/chat/typing-indicator";
import { WelcomeState } from "@/components/chat/welcome-state";

type ViewState = "welcome" | "exiting" | "chat";

export default function ChatPage() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [viewState, setViewState] = useState<ViewState>("welcome");
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const requestGenRef = useRef(0);
  const exitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { toast } = useToast();

  const phasesQuery = useQuery<LoanPhase[]>({
    queryKey: ["/api/phases/active"],
    enabled: viewState === "chat",
  });

  const conversationQuery = useQuery<Conversation>({
    queryKey: ["/api/conversations", conversationId],
    enabled: !!conversationId,
  });

  const messagesQuery = useQuery<Message[]>({
    queryKey: ["/api/conversations", conversationId, "messages"],
    enabled: !!conversationId,
    refetchInterval: false,
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messagesQuery.data, isSending]);

  useEffect(() => {
    return () => {
      if (exitTimerRef.current) clearTimeout(exitTimerRef.current);
    };
  }, []);

  const transitionToChat = () => {
    if (exitTimerRef.current) clearTimeout(exitTimerRef.current);
    setViewState("exiting");
    exitTimerRef.current = setTimeout(() => {
      setViewState("chat");
      exitTimerRef.current = null;
    }, 400);
  };

  const startConversationAndSend = async (firstMessage: string) => {
    if (isSending) return;
    const gen = ++requestGenRef.current;
    transitionToChat();
    setIsSending(true);
    try {
      const createRes = await apiRequest("POST", "/api/conversations");
      const { conversation } = await createRes.json();
      if (gen !== requestGenRef.current) return;
      setConversationId(conversation.id);
      queryClient.invalidateQueries({ queryKey: ["/api/conversations"] });
      await queryClient.invalidateQueries({ queryKey: ["/api/conversations", conversation.id, "messages"] });
      const sendRes = await apiRequest("POST", `/api/conversations/${conversation.id}/messages`, { content: firstMessage });
      await sendRes.json();
      if (gen !== requestGenRef.current) return;
      await queryClient.invalidateQueries({ queryKey: ["/api/conversations", conversation.id, "messages"] });
      await queryClient.invalidateQueries({ queryKey: ["/api/conversations", conversation.id] });
      await queryClient.invalidateQueries({ queryKey: ["/api/conversations"] });
    } catch (error: any) {
      if (gen !== requestGenRef.current) return;
      setViewState("welcome");
      setConversationId(null);
      toast({ title: "Error", description: error.message, variant: "destructive" });
    } finally {
      if (gen === requestGenRef.current) {
        setIsSending(false);
      }
    }
  };

  const sendToExisting = async (content: string) => {
    if (!conversationId || isSending) return;
    const gen = ++requestGenRef.current;
    setIsSending(true);
    try {
      const res = await apiRequest("POST", `/api/conversations/${conversationId}/messages`, { content });
      await res.json();
      if (gen !== requestGenRef.current) return;
      await queryClient.invalidateQueries({ queryKey: ["/api/conversations", conversationId, "messages"] });
      await queryClient.invalidateQueries({ queryKey: ["/api/conversations", conversationId] });
      await queryClient.invalidateQueries({ queryKey: ["/api/conversations"] });
    } catch (error: any) {
      if (gen !== requestGenRef.current) return;
      toast({ title: "Error", description: error.message, variant: "destructive" });
    } finally {
      if (gen === requestGenRef.current) {
        setIsSending(false);
      }
    }
  };

  const handleSend = () => {
    if (!input.trim() || isSending) return;
    const message = input.trim();
    setInput("");
    if (!conversationId) {
      startConversationAndSend(message);
    } else {
      sendToExisting(message);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    requestGenRef.current++;
    if (exitTimerRef.current) {
      clearTimeout(exitTimerRef.current);
      exitTimerRef.current = null;
    }
    setConversationId(null);
    setInput("");
    setViewState("welcome");
    setIsSending(false);
  };

  const handleQuickPrompt = (prompt: string) => {
    if (isSending) return;
    startConversationAndSend(prompt);
  };

  const messages = messagesQuery.data || [];

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0d0d0d] dark:via-[#111] dark:to-[#0d0d0d] relative overflow-hidden">
      <div className="absolute top-[-200px] left-1/4 w-[600px] h-[600px] bg-blue-200/15 dark:bg-blue-500/[0.03] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-150px] right-1/4 w-[500px] h-[500px] bg-blue-200/15 dark:bg-blue-500/5 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-indigo-200/10 dark:bg-indigo-500/3 rounded-full blur-[150px] pointer-events-none" />

      <header className="glass-header relative z-10 border-b border-slate-200/40 dark:border-white/[0.04] px-6 py-4 flex items-center justify-between bg-white/70 dark:bg-[#141414]/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-white dark:bg-white/10 flex items-center justify-center shadow-sm">
            <img src={ksqLogo} alt="KSquare" className="w-7 h-7 object-contain dark:brightness-0 dark:invert" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight text-gray-900 dark:text-white" data-testid="text-app-title">LoanAssist AI</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">Smart loan guidance, personalized for you</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link href="/dashboard">
            <Button data-testid="link-dashboard" variant="outline" size="sm" className="gap-2 bg-white/80 dark:bg-white/[0.06] border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm">
              <LayoutDashboard className="w-4 h-4" />
              Officer Dashboard
            </Button>
          </Link>
          <Button
            data-testid="button-new-chat"
            variant="outline"
            size="sm"
            onClick={handleNewChat}
            className="gap-2 bg-white/80 dark:bg-white/[0.06] border-slate-200/60 dark:border-white/[0.06] text-slate-600 dark:text-slate-300 shadow-sm"
          >
            <MessageSquarePlus className="w-4 h-4" />
            New Chat
          </Button>
        </div>
      </header>

      {viewState === "chat" && phasesQuery.data && phasesQuery.data.length > 0 && (
        <PhaseProgressTracker
          phases={phasesQuery.data}
          currentPhaseId={conversationQuery.data?.currentPhaseId ?? null}
        />
      )}

      <div className="flex-1 overflow-y-auto px-4 md:px-0 relative z-10" ref={scrollRef}>
        <div className="max-w-2xl mx-auto py-6 space-y-0">
          {viewState === "welcome" || viewState === "exiting" ? (
            <WelcomeState onPromptClick={handleQuickPrompt} isExiting={viewState === "exiting"} />
          ) : messages.length === 0 && isSending ? (
            <div className="space-y-4 anim-chat-enter">
              <div className="flex gap-3">
                <div className="w-9 h-9 rounded-2xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                <div className="space-y-2">
                  <div className="h-20 w-72 rounded-3xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                </div>
              </div>
            </div>
          ) : (
            <div className="anim-chat-enter">
              {messages.map((msg) => (
                <ChatBubble key={msg.id} message={msg} />
              ))}
              {isSending && <TypingIndicator />}
            </div>
          )}
        </div>
      </div>

      <div className="glass-header relative z-10 border-t border-slate-200/40 dark:border-white/[0.04] p-4 bg-white/70 dark:bg-[#141414]/80 backdrop-blur-xl">
        <div className="max-w-2xl mx-auto">
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                data-testid="input-chat-message"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={viewState === "welcome" ? "Tell me what you're looking for..." : "Type your message..."}
                disabled={isSending}
                rows={1}
                className="glass-input w-full resize-none rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.04] px-4 py-3 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-400/30 focus:border-blue-300 dark:focus:border-blue-500/30 transition-all placeholder:text-gray-400 dark:placeholder:text-gray-500 disabled:opacity-50 shadow-sm"
                style={{ minHeight: "48px", maxHeight: "120px" }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = "48px";
                  target.style.height = Math.min(target.scrollHeight, 120) + "px";
                }}
              />
            </div>
            <Button
              data-testid="button-send-message"
              onClick={handleSend}
              disabled={!input.trim() || isSending}
              size="icon"
              className="rounded-2xl h-12 w-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg shadow-blue-600/20 dark:shadow-blue-900/40 transition-all duration-200 border-0 disabled:opacity-30"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-[10px] text-gray-400 dark:text-gray-500 text-center mt-2.5">
            AI-powered recommendations are estimates. Final terms subject to verification.
          </p>
        </div>
      </div>
    </div>
  );
}
