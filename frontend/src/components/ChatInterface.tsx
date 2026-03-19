import React, { useMemo, useRef, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  onConversationUpdated?: (conversation: V2Conversation) => void;
  onPhasesUpdated?: (phases: V2Phase[]) => void;
  resetSignal?: number;
}

type V2ChatRole = 'user' | 'assistant';

export type V2Conversation = {
  id: string;
  borrowerName?: string | null;
  status?: string | null;
  chatRole?: string | null;
  currentPhaseId?: string | null;
  seriousnessScore?: number | null;
  fitScore?: number | null;
  intentSummary?: unknown;
  approvalProbability?: number | null;
  recommendedProducts?: unknown;
  nextConversationAngle?: string | null;
  assignedOfficer?: string | null;
  createdAt?: string | null;
};

export type V2Phase = {
  id: string;
  name: string;
  description?: string | null;
  sortOrder: number;
  isActive: boolean;
  color?: string | null;
  icon?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};

type V2Message = {
  id: string;
  conversationId: string;
  role: V2ChatRole;
  content: string;
  metadata?: unknown;
  createdAt?: string | null;
};

const STORAGE_KEY = 'v2_borrower_conversation_id';

type ViewState = 'welcome' | 'exiting' | 'chat';

const getActorRole = (metadata: unknown): string | null => {
  if (!metadata || typeof metadata !== 'object') return null;
  const role = (metadata as { actorRole?: unknown }).actorRole;
  return typeof role === 'string' ? role : null;
};

const isOfficerOnlyMessage = (message: V2Message): boolean => {
  const actorRole = getActorRole(message.metadata);
  return actorRole === 'officer' || actorRole === 'officer_assistant';
};

const DEFAULT_QUICK_PROMPTS: Array<{ title: string; prompt: string }> = [
  { title: 'Home Loan', prompt: 'I want a home loan to buy a house.' },
  { title: 'Car Loan', prompt: 'I need a car loan for a vehicle purchase.' },
  { title: 'Personal Loan', prompt: 'I need a personal loan for an urgent expense.' },
  { title: 'Debt Consolidation', prompt: 'I want to consolidate multiple debts into one EMI.' },
];

export const ChatInterface: React.FC<Props> = ({ onConversationUpdated, onPhasesUpdated, resetSignal }) => {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<V2Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [viewState, setViewState] = useState<ViewState>('welcome');

  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const requestGenRef = useRef(0);
  const exitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scrollToBottom = () => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages, loading, viewState]);

  useEffect(() => {
    return () => {
      if (exitTimerRef.current) clearTimeout(exitTimerRef.current);
    };
  }, []);

  useEffect(() => {
    const fetchJson = async <T,>(url: string, init?: RequestInit): Promise<{ ok: true; value: T } | { ok: false; status: number }> => {
      try {
        const res = await fetch(url, init);
        if (!res.ok) return { ok: false, status: res.status };
        return { ok: true, value: (await res.json()) as T };
      } catch {
        return { ok: false, status: 0 };
      }
    };

    const bootstrap = async () => {
      setBootstrapping(true);
      if (typeof resetSignal === 'number') {
        window.localStorage.removeItem(STORAGE_KEY);
      }

      const storedId = window.localStorage.getItem(STORAGE_KEY);
      const activeConversationId: string | null = storedId || null;

      if (!activeConversationId) {
        setConversationId(null);
        setMessages([]);
        setViewState('welcome');
        setBootstrapping(false);
        return;
      }

      const phasesRes = await fetchJson<V2Phase[]>('http://localhost:8000/api/phases/active');
      if (phasesRes.ok) onPhasesUpdated?.(phasesRes.value);

      const existing = await fetchJson<V2Conversation>(`http://localhost:8000/api/conversations/${activeConversationId}`);
      if (!existing.ok) {
        window.localStorage.removeItem(STORAGE_KEY);
        setConversationId(null);
        setMessages([]);
        setViewState('welcome');
        setBootstrapping(false);
        return;
      }

      onConversationUpdated?.(existing.value);
      setConversationId(activeConversationId);
      setViewState('chat');

      const msgsRes = await fetchJson<V2Message[]>(`http://localhost:8000/api/conversations/${activeConversationId}/messages`);
      if (msgsRes.ok) {
        setMessages(msgsRes.value.filter((m) => !isOfficerOnlyMessage(m)));
      } else {
        setMessages([
          {
            id: 'messages-error',
            conversationId: activeConversationId,
            role: 'assistant',
            content: 'Unable to load chat history. Please refresh.',
            createdAt: null,
          },
        ]);
      }

      setBootstrapping(false);
    };

    void bootstrap();
  }, [onConversationUpdated, onPhasesUpdated, resetSignal]);

  const transitionToChat = () => {
    if (exitTimerRef.current) clearTimeout(exitTimerRef.current);
    setViewState('exiting');
    exitTimerRef.current = setTimeout(() => {
      setViewState('chat');
      exitTimerRef.current = null;
    }, 400);
  };

  const sendToExisting = async (activeConversationId: string, content: string) => {
    const now = Date.now();
    const userMsg: V2Message = {
      id: `temp-user-${now}`,
      conversationId: activeConversationId,
      role: 'user',
      content,
      createdAt: new Date(now).toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`http://localhost:8000/api/conversations/${activeConversationId}/messages`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ content }),
      });

      if (!res.ok) {
        const raw = await res.text().catch(() => '');
        let detail = raw;
        try {
          const parsed = JSON.parse(raw) as { detail?: unknown };
          if (typeof parsed?.detail === 'string') detail = parsed.detail;
        } catch {
          // ignore
        }
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            conversationId: activeConversationId,
            role: 'assistant',
            content: detail ? `Request failed (${res.status}): ${detail}` : `Request failed (${res.status}). Please try again.`,
            createdAt: null,
          },
        ]);
        return;
      }

      const payload = (await res.json()) as { message?: V2Message };
      if (payload.message && payload.message.role && payload.message.content && !isOfficerOnlyMessage(payload.message as V2Message)) {
        setMessages((prev) => [...prev, payload.message as V2Message]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            conversationId: activeConversationId,
            role: 'assistant',
            content: 'No assistant response was returned. Please try again.',
            createdAt: null,
          },
        ]);
      }

      const refreshed = await fetch(`http://localhost:8000/api/conversations/${activeConversationId}`);
      if (refreshed.ok) {
        onConversationUpdated?.((await refreshed.json()) as V2Conversation);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          conversationId: activeConversationId,
          role: 'assistant',
          content: 'Network error. Please try again.',
          createdAt: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const startConversationAndSend = async (firstMessage: string) => {
    if (loading || bootstrapping) return;
    const gen = ++requestGenRef.current;
    transitionToChat();
    setLoading(true);
    try {
      const createRes = await fetch('http://localhost:8000/api/conversations', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (!createRes.ok) {
        if (gen !== requestGenRef.current) return;
        setMessages([
          {
            id: 'bootstrap-error',
            conversationId: 'unknown',
            role: 'assistant',
            content: 'Unable to start a conversation right now. Please refresh and try again.',
            createdAt: null,
          },
        ]);
        setConversationId(null);
        setViewState('welcome');
        return;
      }

      const createdPayload = (await createRes.json()) as { conversation?: V2Conversation };
      const created = createdPayload.conversation;
      if (!created?.id) {
        if (gen !== requestGenRef.current) return;
        setMessages([
          {
            id: 'bootstrap-error',
            conversationId: 'unknown',
            role: 'assistant',
            content: 'Conversation creation returned an invalid response. Please refresh.',
            createdAt: null,
          },
        ]);
        setConversationId(null);
        setViewState('welcome');
        return;
      }

      if (gen !== requestGenRef.current) return;
      window.localStorage.setItem(STORAGE_KEY, created.id);
      setConversationId(created.id);
      onConversationUpdated?.(created);

      const phasesRes = await fetch(`http://localhost:8000/api/phases/active`);
      if (phasesRes.ok) {
        onPhasesUpdated?.((await phasesRes.json()) as V2Phase[]);
      }

      await sendToExisting(created.id, firstMessage);
    } finally {
      if (gen === requestGenRef.current) {
        setLoading(false);
      }
    }
  };

  const handleSend = async (text: string) => {
    const content = text.trim();
    if (!content || loading || bootstrapping) return;
    if (!conversationId) {
      await startConversationAndSend(content);
      return;
    }
    if (viewState !== 'chat') setViewState('chat');
    await sendToExisting(conversationId, content);
  };

  const canSend = input.trim().length > 0 && !loading && !bootstrapping;

  const bubbleClassForRole = useMemo(() => {
    return {
      user:
        'glass-bubble-user ml-auto max-w-[85%] rounded-3xl rounded-br-lg px-4 py-3 text-sm leading-relaxed text-white bg-gradient-to-r from-blue-600 to-indigo-600 shadow-lg shadow-blue-600/20 dark:shadow-blue-900/40',
      assistant:
        'glass-bubble-bot max-w-[85%] rounded-3xl rounded-bl-lg px-4 py-3 text-sm leading-relaxed bg-white dark:bg-white/[0.05] border border-slate-200/60 dark:border-white/[0.06] text-slate-800 dark:text-slate-200 shadow-sm',
    } as const;
  }, []);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto px-4 md:px-0 relative z-10" ref={scrollRef}>
        <div className="max-w-2xl mx-auto py-6 space-y-0">
          {bootstrapping ? (
            <div className="space-y-4">
              <div className="flex gap-3">
                <div className="w-9 h-9 rounded-2xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                <div className="space-y-2">
                  <div className="h-20 w-72 rounded-3xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                </div>
              </div>
            </div>
          ) : viewState === 'welcome' || viewState === 'exiting' ? (
            <div className={`${viewState === 'exiting' ? 'anim-welcome-exit' : ''}`}>
              <div className="anim-float-in">
                <div className="rounded-3xl bg-white/95 dark:bg-[#151520]/80 backdrop-blur-2xl border border-slate-200/60 dark:border-white/[0.06] shadow-xl shadow-black/[0.04] dark:shadow-black/40 p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">Tell me what you need</h2>
                      <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        I’ll recommend borrowing paths and next steps based on your goals and constraints.
                      </p>
                    </div>
                    <div className="w-11 h-11 rounded-2xl bg-slate-100 dark:bg-white/10 flex items-center justify-center shrink-0">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500 dark:text-slate-300">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                      </svg>
                    </div>
                  </div>

                  <div className="mt-5 grid grid-cols-2 gap-3">
                    {DEFAULT_QUICK_PROMPTS.map((p) => (
                      <button
                        key={p.title}
                        type="button"
                        disabled={loading}
                        onClick={() => {
                          void handleSend(p.prompt);
                        }}
                        className="text-left rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white/80 dark:bg-white/[0.04] px-4 py-3 hover:bg-slate-50 dark:hover:bg-white/[0.06] transition-colors"
                      >
                        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{p.title}</div>
                        <div className="mt-1 text-sm text-slate-800 dark:text-slate-200 leading-snug">{p.prompt}</div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : messages.length === 0 && loading ? (
            <div className="space-y-4 anim-chat-enter">
              <div className="flex gap-3">
                <div className="w-9 h-9 rounded-2xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                <div className="space-y-2">
                  <div className="h-20 w-72 rounded-3xl bg-gray-100 dark:bg-white/10 animate-pulse" />
                </div>
              </div>
            </div>
          ) : (
            <div className="anim-chat-enter space-y-4">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div data-testid={`chat-message-${msg.role}`} className={`chat-message-content ${msg.role === 'user' ? bubbleClassForRole.user : bubbleClassForRole.assistant}`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  </div>
                </div>
              ))}
              {loading ? (
                <div className="flex justify-start">
                  <div className={bubbleClassForRole.assistant}>
                    <div className="flex gap-1.5 items-center">
                      <div className="w-1.5 h-1.5 bg-slate-400/70 dark:bg-slate-500 rounded-full" style={{ animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0s' }} />
                      <div className="w-1.5 h-1.5 bg-slate-400/70 dark:bg-slate-500 rounded-full" style={{ animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.16s' }} />
                      <div className="w-1.5 h-1.5 bg-slate-400/70 dark:bg-slate-500 rounded-full" style={{ animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.32s' }} />
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="glass-header relative z-10 border-t border-slate-200/40 dark:border-white/[0.04] p-4 bg-white/70 dark:bg-[#141414]/80 backdrop-blur-xl">
        <div className="max-w-2xl mx-auto">
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                data-testid="input-chat-message"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    void handleSend(input);
                  }
                }}
                placeholder={viewState === 'welcome' ? "Tell me what you're looking for..." : 'Type your message...'}
                disabled={loading || bootstrapping}
                rows={1}
                className="glass-input w-full resize-none rounded-2xl border border-slate-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.04] px-4 py-3 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-400/30 focus:border-blue-300 dark:focus:border-blue-500/30 transition-all placeholder:text-slate-400 dark:placeholder:text-slate-500 disabled:opacity-50 shadow-sm"
                style={{ minHeight: '48px', maxHeight: '120px' }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = '48px';
                  target.style.height = Math.min(target.scrollHeight, 120) + 'px';
                }}
              />
            </div>

            <button
              data-testid="button-send-message"
              type="button"
              onClick={() => void handleSend(input)}
              disabled={!canSend}
              className="rounded-2xl h-12 w-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg shadow-blue-600/20 dark:shadow-blue-900/40 transition-all duration-200 border-0 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
              aria-label="Send"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
          <p className="text-[10px] text-slate-400 dark:text-slate-500 text-center mt-2.5">
            AI-powered recommendations are estimates. Final terms subject to verification.
          </p>
        </div>
      </div>
    </div>
  );
};
