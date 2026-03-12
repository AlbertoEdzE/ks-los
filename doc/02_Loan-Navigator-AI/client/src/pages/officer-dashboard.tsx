import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-provider";
import {
  Users,
  MessageSquare,
  TrendingUp,
  Flame,
  UserCheck,
  Gauge,
  Settings,
  Layers,
} from "lucide-react";
import type { Conversation } from "@shared/schema";
import { useState } from "react";
import { Link } from "wouter";
import ksqLogo from "@assets/image_1773224776245.png";
import { GlassPanel } from "@/components/layout/glass-panel";
import { StatsCard } from "@/components/dashboard/stats-card";
import { ConversationCard } from "@/components/dashboard/conversation-card";
import { ConversationDetail } from "@/components/dashboard/conversation-detail";
import { EmptyState } from "@/components/dashboard/empty-state";

export default function OfficerDashboard() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sidebarHovered, setSidebarHovered] = useState(false);

  const conversationsQuery = useQuery<Conversation[]>({ queryKey: ["/api/conversations"], refetchInterval: 10000 });

  const conversations = conversationsQuery.data || [];
  const activeCount = conversations.filter((c) => c.status === "active").length;
  const qualifiedCount = conversations.filter((c) => c.status === "qualified").length;
  const avgSeriousness =
    conversations.length > 0
      ? Math.round(
          conversations.filter((c) => c.seriousnessScore).reduce((sum, c) => sum + (c.seriousnessScore || 0), 0) /
            Math.max(conversations.filter((c) => c.seriousnessScore).length, 1)
        )
      : 0;

  const sidebarExpanded = !selectedId || sidebarHovered;

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30 dark:from-[#0b0b14] dark:via-[#0e0e1a] dark:to-[#0b0f1e] relative overflow-hidden">
      <div className="absolute top-[-200px] right-[-100px] w-[600px] h-[600px] bg-blue-300/10 dark:bg-blue-500/[0.05] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-100px] left-[-50px] w-[400px] h-[400px] bg-indigo-300/10 dark:bg-indigo-500/[0.04] rounded-full blur-[100px] pointer-events-none" />

      <header className="relative z-10 shrink-0 border-b border-gray-200/50 dark:border-[#1e1e30] px-6 py-3 flex items-center justify-between bg-white/80 dark:bg-[#0e0e1a]/90 backdrop-blur-2xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white dark:bg-[#1a1a2e] flex items-center justify-center border border-gray-200/50 dark:border-[#2a2a3d]">
            <img src={ksqLogo} alt="KSquare" className="w-6 h-6 object-contain dark:brightness-0 dark:invert" />
          </div>
          <div>
            <h1 className="font-bold text-base tracking-tight text-gray-900 dark:text-white" data-testid="text-dashboard-title">Officer Dashboard</h1>
            <p className="text-[11px] text-gray-500 dark:text-slate-500">AI-qualified leads & borrower insights</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <ThemeToggle />
          <Link href="/pipeline">
            <Button data-testid="link-pipeline" variant="ghost" size="sm" className="gap-1.5 text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-white/[0.06] text-xs h-8">
              <TrendingUp className="w-3.5 h-3.5" /> Pipeline
            </Button>
          </Link>
          <Link href="/loan-products">
            <Button data-testid="link-loan-products" variant="ghost" size="sm" className="gap-1.5 text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-white/[0.06] text-xs h-8">
              <Layers className="w-3.5 h-3.5" /> Products
            </Button>
          </Link>
          <Link href="/officer-chat">
            <Button data-testid="link-officer-chat" variant="ghost" size="sm" className="gap-1.5 text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-white/[0.06] text-xs h-8">
              <Settings className="w-3.5 h-3.5" /> Lifecycle
            </Button>
          </Link>
          <Link href="/">
            <Button data-testid="link-chat" variant="ghost" size="sm" className="gap-1.5 text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-white/[0.06] text-xs h-8">
              <MessageSquare className="w-3.5 h-3.5" /> Chat
            </Button>
          </Link>
        </div>
      </header>

      <div className="relative z-10 shrink-0 grid grid-cols-4 gap-3 px-6 pt-4 pb-0">
        <StatsCard icon={Users} label="Total Leads" value={conversations.length} color="bg-blue-100 dark:bg-blue-500/15" iconColor="text-blue-600 dark:text-blue-400" />
        <StatsCard icon={Flame} label="Active Chats" value={activeCount} color="bg-emerald-100 dark:bg-emerald-500/15" iconColor="text-emerald-600 dark:text-emerald-400" />
        <StatsCard icon={UserCheck} label="Qualified" value={qualifiedCount} color="bg-violet-100 dark:bg-violet-500/15" iconColor="text-violet-600 dark:text-violet-400" />
        <StatsCard icon={Gauge} label="Avg Score" value={`${avgSeriousness}%`} color="bg-amber-100 dark:bg-amber-500/15" iconColor="text-amber-600 dark:text-amber-400" />
      </div>

      <div className="flex-1 relative z-10 flex min-h-0 px-6 py-4 gap-4">
        <div
          className="shrink-0 flex flex-col transition-all duration-500 ease-in-out"
          style={{ width: sidebarExpanded ? "380px" : "220px" }}
          onMouseEnter={() => setSidebarHovered(true)}
          onMouseLeave={() => setSidebarHovered(false)}
        >
          <GlassPanel className="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="shrink-0 p-4 border-b border-gray-200/50 dark:border-[#1e1e30] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <h2 className="font-bold text-sm text-gray-900 dark:text-white">
                  {sidebarExpanded ? "Qualified Leads" : "Leads"}
                </h2>
              </div>
              <Badge className="text-[10px] font-bold bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 border-0 rounded-full px-2.5">
                {conversations.length}
              </Badge>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {conversationsQuery.isLoading ? (
                <div className="space-y-2 p-1">
                  {Array(5).fill(0).map((_, i) => (
                    <div key={i} className="h-16 rounded-xl bg-gray-200 dark:bg-white/[0.06] animate-pulse" />
                  ))}
                </div>
              ) : conversations.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Users className="w-8 h-8 text-gray-300 dark:text-slate-600 mb-2" />
                  <p className="text-sm font-medium text-gray-500 dark:text-slate-400">No leads yet</p>
                  <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">Leads appear as borrowers start chats</p>
                </div>
              ) : (
                conversations.map((conv) => (
                  <ConversationCard
                    key={conv.id}
                    conversation={conv}
                    isSelected={selectedId === conv.id}
                    onClick={() => setSelectedId(conv.id)}
                  />
                ))
              )}
            </div>
          </GlassPanel>
        </div>

        <div className="flex-1 min-w-0">
          <GlassPanel className="h-full overflow-hidden">
            {selectedId ? (
              <ConversationDetail conversationId={selectedId} />
            ) : (
              <EmptyState />
            )}
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}
