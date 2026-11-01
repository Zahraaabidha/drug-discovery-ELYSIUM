import React, { useState, useRef, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { agentChat } from "../api/elysium";
import type { ChatMessage, AgentTool } from "../api/elysium";

// ── Suggested queries ─────────────────────────────────────────────────────
const SUGGESTIONS = [
  "What are the top 3 molecules for EGFR by binding score?",
  "Show me ADMET stats for the latest run",
  "Which molecules are most similar to Aspirin?",
  "Summarise all discovery runs so far",
  "What molecules have Lipinski violations?",
  "Compare binding scores across EGFR and BRAF runs",
];

// ── Tool call trace badge ─────────────────────────────────────────────────
const ToolTrace: React.FC<{ tools: AgentTool[] }> = ({ tools }) => {
  const [open, setOpen] = useState(false);
  if (!tools.length) return null;
  return (
    <div className="mt-2">
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-[10px] text-neutral-400 hover:text-neutral-600 transition-colors font-medium">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          className={`transition-transform ${open ? "rotate-90" : ""}`}>
          <path d="M9 18l6-6-6-6"/>
        </svg>
        {tools.length} tool{tools.length > 1 ? "s" : ""} used
      </button>
      {open && (
        <div className="mt-2 space-y-1.5">
          {tools.map((t, i) => (
            <div key={i} className="flex items-start gap-2 bg-neutral-50 border border-neutral-100 rounded-xl px-3 py-2">
              <div className="w-5 h-5 rounded-md bg-violet-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-bold text-violet-700 uppercase tracking-wider">{t.name}</p>
                {t.args && (
                  <p className="text-[10px] text-neutral-500 font-mono mt-0.5 truncate">
                    {JSON.stringify(t.args)}
                  </p>
                )}
              </div>
              <span className="text-[9px] bg-emerald-50 text-emerald-600 border border-emerald-100 px-1.5 py-0.5 rounded-full font-semibold flex-shrink-0">done</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ── Single message bubble ─────────────────────────────────────────────────
const MessageBubble: React.FC<{ msg: ChatMessage; tools?: AgentTool[] }> = ({ msg, tools }) => {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5
        ${isUser ? "bg-neutral-900" : "bg-violet-600"}`}>
        {isUser
          ? <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          : <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l3.5 7 7.5 1-5.5 5 1.5 7.5L12 19l-7 3.5L6.5 15 1 10l7.5-1z"/></svg>
        }
      </div>

      {/* Bubble */}
      <div className={`flex-1 max-w-[85%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        <p className={`text-[10px] font-semibold uppercase tracking-wider ${isUser ? "text-neutral-400 text-right" : "text-violet-500"}`}>
          {isUser ? "You" : "ELYSIUM Agent"}
        </p>
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed
          ${isUser
            ? "bg-neutral-900 text-white rounded-tr-sm"
            : "bg-white border border-neutral-100 text-neutral-800 rounded-tl-sm shadow-sm"
          }`}>
          {msg.content.split("\n").map((line, i) => (
            <React.Fragment key={i}>
              {line}
              {i < msg.content.split("\n").length - 1 && <br/>}
            </React.Fragment>
          ))}
        </div>
        {tools && tools.length > 0 && !isUser && <ToolTrace tools={tools}/>}
      </div>
    </div>
  );
};

// ── Typing indicator ──────────────────────────────────────────────────────
const TypingIndicator: React.FC = () => (
  <div className="flex gap-3">
    <div className="w-8 h-8 rounded-xl bg-violet-600 flex items-center justify-center flex-shrink-0">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2l3.5 7 7.5 1-5.5 5 1.5 7.5L12 19l-7 3.5L6.5 15 1 10l7.5-1z"/>
      </svg>
    </div>
    <div className="bg-white border border-neutral-100 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5 shadow-sm">
      {[0, 150, 300].map(d => (
        <div key={d} className="w-1.5 h-1.5 rounded-full bg-neutral-300 animate-bounce" style={{ animationDelay: `${d}ms` }}/>
      ))}
    </div>
  </div>
);

// ── Main ──────────────────────────────────────────────────────────────────
interface StoredMessage extends ChatMessage { tools?: AgentTool[]; }

const AgentPage: React.FC = () => {
  const [messages, setMessages] = useState<StoredMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setInput("");
    setError(null);

    const userMsg: StoredMessage = { role: "user", content: trimmed };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
            const res = await agentChat({
        prompt: trimmed,
        session_id: sessionId,
      });

      if (res.session_id) setSessionId(res.session_id);

      const assistantMsg: StoredMessage = {
        role: "assistant",
        content: res.answer,
        tools: (res.evidence ?? []).map(e => ({ name: e.tool, args: e.input, result: e.result })),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      setError(err?.message || "Agent request failed. Is the backend running?");
      // Remove the user message on failure
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [messages, sessionId, loading]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  const clearSession = () => {
    setMessages([]);
    setSessionId(undefined);
    setError(null);
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="min-h-screen bg-[#f8f8f6] pt-16 flex flex-col">
      <div className="max-w-5xl mx-auto w-full px-4 md:px-10 flex flex-col flex-1" style={{ height: "calc(100vh - 64px)" }}>

        {/* ── Header ── */}
        <div className="py-6 flex items-center justify-between flex-shrink-0">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-neutral-400 mb-1 font-medium">Agentic Interface</p>
            <h1 className="text-3xl font-black tracking-[-0.03em] text-neutral-900">Agent Chat</h1>
          </div>
          <div className="flex items-center gap-3">
            {sessionId && (
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white border border-neutral-100 text-xs text-neutral-400">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400"/>
                Session active
              </div>
            )}
            {messages.length > 0 && (
              <button onClick={clearSession}
                className="flex items-center gap-2 px-4 py-2 rounded-xl border border-neutral-200 text-sm font-medium text-neutral-600 hover:border-neutral-400 transition-colors bg-white">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>
                </svg>
                New session
              </button>
            )}
          </div>
        </div>

        {/* ── Main layout ── */}
        <div className="flex gap-5 flex-1 min-h-0 pb-4">

          {/* ── Chat column ── */}
          <div className="flex flex-col flex-1 min-w-0 min-h-0">
            {/* Messages area */}
            <div className="flex-1 overflow-y-auto min-h-0 bg-white rounded-3xl border border-neutral-100 p-5 mb-4">
              {isEmpty ? (
                /* Empty state */
                <div className="h-full flex flex-col items-center justify-center text-center px-8 py-12">
                  <div className="w-14 h-14 rounded-2xl bg-violet-50 border border-violet-100 flex items-center justify-center mb-5">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 2l3.5 7 7.5 1-5.5 5 1.5 7.5L12 19l-7 3.5L6.5 15 1 10l7.5-1z"/>
                    </svg>
                  </div>
                  <h2 className="text-xl font-black tracking-tight text-neutral-900 mb-2">ELYSIUM Agent</h2>
                  <p className="text-sm text-neutral-400 leading-relaxed max-w-xs mb-8">
                    Ask me anything about your discovery runs, molecules, ADMET profiles, or knowledge graph. I query live database evidence.
                  </p>
                  {/* Suggestion chips */}
                  <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                    {SUGGESTIONS.slice(0, 4).map(s => (
                      <button key={s} onClick={() => send(s)}
                        className="text-xs bg-neutral-50 border border-neutral-200 hover:border-violet-300 hover:bg-violet-50 hover:text-violet-700 text-neutral-600 px-3 py-2 rounded-xl transition-all duration-150 text-left font-medium">
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-5">
                  {messages.map((msg, i) => (
                    <MessageBubble key={i} msg={msg} tools={msg.tools}/>
                  ))}
                  {loading && <TypingIndicator/>}
                  <div ref={bottomRef}/>
                </div>
              )}
            </div>

            {/* Error */}
            {error && (
              <div className="mb-3 flex items-start gap-2 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0 mt-0.5">
                  <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>
                </svg>
                <p className="text-xs text-red-700 font-medium">{error}</p>
              </div>
            )}

            {/* Input area */}
            <div className="bg-white rounded-2xl border border-neutral-200 focus-within:border-violet-300 transition-colors flex-shrink-0">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your molecules, runs, ADMET data… (Enter to send, Shift+Enter for new line)"
                rows={3}
                className="w-full px-4 pt-4 pb-2 text-sm text-neutral-900 placeholder:text-neutral-400 resize-none focus:outline-none bg-transparent rounded-2xl"
              />
              <div className="flex items-center justify-between px-4 pb-3">
                <p className="text-[10px] text-neutral-400">
                  {sessionId ? `Session: ${sessionId.slice(0, 12)}…` : "New session"}
                </p>
                <button onClick={() => send(input)} disabled={!input.trim() || loading}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-neutral-900 text-white text-xs font-semibold hover:bg-neutral-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                  {loading
                    ? <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
                    : <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                  }
                  {loading ? "Thinking…" : "Send"}
                </button>
              </div>
            </div>
          </div>

          {/* ── Right panel ── */}
          <div className="hidden lg:flex flex-col gap-4 w-72 flex-shrink-0">

            {/* What the agent can do */}
            <div className="bg-white rounded-2xl border border-neutral-100 p-5">
              <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-4">Agent Tools</p>
              <div className="space-y-2.5">
                {[
                  { name: "get_top_molecules", desc: "Retrieve highest-scoring candidates for any target" },
                  { name: "get_similar_to_drug", desc: "Find molecules similar to a known reference drug" },
                  { name: "get_admet_stats", desc: "Aggregate ADMET statistics across runs" },
                  { name: "get_runs_summary", desc: "Overview of all discovery experiments" },
                ].map(t => (
                  <div key={t.name} className="flex items-start gap-2.5">
                    <div className="w-5 h-5 rounded-md bg-violet-50 border border-violet-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>
                      </svg>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-neutral-700 font-mono">{t.name}</p>
                      <p className="text-[10px] text-neutral-400 mt-0.5 leading-relaxed">{t.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Suggested queries */}
            <div className="bg-white rounded-2xl border border-neutral-100 p-5">
              <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-3">Try asking</p>
              <div className="space-y-1.5">
                {SUGGESTIONS.map(s => (
                  <button key={s} onClick={() => send(s)}
                    className="w-full text-left text-xs text-neutral-600 hover:text-violet-700 hover:bg-violet-50 px-3 py-2 rounded-xl border border-transparent hover:border-violet-100 transition-all duration-150 font-medium">
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* How it works */}
            <div className="bg-neutral-900 rounded-2xl p-5 text-white">
              <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-3">How it works</p>
              <div className="space-y-3">
                {[
                  { step: "1", text: "Your query is sent to Llama 3.3 70B via OpenRouter" },
                  { step: "2", text: "The model selects tools and generates a reasoning trace" },
                  { step: "3", text: "Tools query the live SQLite database for evidence" },
                  { step: "4", text: "A grounded response is synthesised from real data" },
                ].map(s => (
                  <div key={s.step} className="flex gap-2.5 items-start">
                    <span className="w-5 h-5 rounded-full bg-white/10 text-white/60 text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{s.step}</span>
                    <p className="text-xs text-neutral-400 leading-relaxed">{s.text}</p>
                  </div>
                ))}
              </div>
              <Link to="/runs" className="mt-4 flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-medium transition-colors">
                View discovery runs →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentPage;