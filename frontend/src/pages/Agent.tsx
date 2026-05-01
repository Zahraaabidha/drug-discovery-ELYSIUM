import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Activity, Compass, BarChart3, Bot, Microscope, Home,
  Settings, HelpCircle, LogOut, Send, Paperclip, Wrench,
  Scale, ShieldAlert, HeartPulse, CheckCircle2, FileText,
  ChevronRight, X, Info, Search, Bell, Mail, Plus
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { agentChat } from "../api/elysium";

// ── Sidebar item ───────────────────────────────────────────────────────────
const SidebarItem = ({ icon: Icon, label, active = false, to }: {
  icon: any; label: string; active?: boolean; to?: string;
}) => (
  <Link to={to || "#"} className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all
    ${active ? "bg-black text-white" : "text-black/40 hover:bg-black/5 hover:text-black"}`}>
    <Icon size={20} strokeWidth={active ? 2 : 1.5} />
    <span className="text-sm font-medium">{label}</span>
  </Link>
);

// ── Markdown-lite renderer ─────────────────────────────────────────────────
// Converts **bold**, ### headings, * bullets, --- separators
const MarkdownText = ({ text }: { text: string }) => {
  const lines = text.split("\n");
  return (
    <div className="space-y-1.5">
      {lines.map((line, i) => {
        // Horizontal rule
        if (/^---+$/.test(line.trim())) return <hr key={i} className="border-black/10 my-2"/>;
        // H3
        if (line.startsWith("### ")) return (
          <p key={i} className="text-sm font-bold mt-3 mb-1">{renderInline(line.slice(4))}</p>
        );
        // H2
        if (line.startsWith("## ")) return (
          <p key={i} className="text-base font-bold mt-3 mb-1">{renderInline(line.slice(3))}</p>
        );
        // Bullet
        if (line.startsWith("* ") || line.startsWith("- ")) return (
          <div key={i} className="flex gap-2">
            <span className="text-black/30 flex-shrink-0 mt-0.5">•</span>
            <p className="text-sm leading-relaxed">{renderInline(line.slice(2))}</p>
          </div>
        );
        // Empty line → spacer
        if (line.trim() === "") return <div key={i} className="h-1"/>;
        // Normal
        return <p key={i} className="text-sm leading-relaxed">{renderInline(line)}</p>;
      })}
    </div>
  );
};

function renderInline(text: string): React.ReactNode {
  // Split on **bold** patterns
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={i} className="font-bold">{part.slice(2, -2)}</strong>;
    return <span key={i}>{part}</span>;
  });
}

// ── Tool trace ─────────────────────────────────────────────────────────────
const ToolTrace = ({ evidence }: { evidence?: Array<{ tool: string; input: any; result: any }> }) => {
  const [open, setOpen] = useState(false);
  if (!evidence?.length) return null;
  return (
    <div className="mt-2">
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-[10px] text-black/30 hover:text-black/60 transition-colors font-bold uppercase tracking-wider">
        <ChevronRight size={10} className={`transition-transform ${open ? "rotate-90" : ""}`}/>
        {evidence.length} tool{evidence.length > 1 ? "s" : ""} used
      </button>
      {open && (
        <div className="mt-2 space-y-1.5">
          {evidence.map((e, i) => (
            <div key={i} className="flex items-start gap-2 bg-black/[0.03] border border-black/5 rounded-2xl px-4 py-3">
              <div className="w-5 h-5 rounded-md bg-purple-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Wrench size={10} className="text-purple-600"/>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-bold text-purple-600 uppercase tracking-wider">{e.tool}</p>
                <p className="text-[10px] text-black/40 font-mono mt-0.5 truncate">{JSON.stringify(e.input)}</p>
              </div>
              <span className="text-[9px] bg-green-50 text-green-600 border border-green-100 px-2 py-0.5 rounded-full font-bold flex-shrink-0">done</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ── Message types ──────────────────────────────────────────────────────────
interface Message {
  role: "user" | "assistant";
  content: string;
  evidence?: Array<{ tool: string; input: any; result: any }>;
}

// ── Bubble ─────────────────────────────────────────────────────────────────
const Bubble = ({ msg }: { msg: Message }) => {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`w-9 h-9 rounded-2xl flex items-center justify-center flex-shrink-0 text-xs font-bold shadow-sm mt-0.5
        ${isUser ? "bg-black text-white" : "bg-purple-500 text-white"}`}>
        {isUser ? "U" : "AI"}
      </div>
      <div className={`flex-1 max-w-[80%] flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
        <p className={`text-[10px] font-bold uppercase tracking-wider opacity-40 ${isUser ? "text-right" : ""}`}>
          {isUser ? "You" : "ELYSIUM Agent"}
        </p>
        <div className={`rounded-2xl px-5 py-4 ${isUser
          ? "bg-black text-white rounded-tr-sm text-sm leading-relaxed"
          : "bg-white border border-black/5 text-black rounded-tl-sm shadow-sm"}`}>
          {isUser ? msg.content : <MarkdownText text={msg.content}/>}
        </div>
        {!isUser && <ToolTrace evidence={msg.evidence}/>}
      </div>
    </div>
  );
};

// ── Typing indicator ───────────────────────────────────────────────────────
const Typing = () => (
  <div className="flex gap-3">
    <div className="w-9 h-9 rounded-2xl bg-purple-500 flex items-center justify-center text-white text-xs font-bold shadow-sm flex-shrink-0">AI</div>
    <div className="bg-white border border-black/5 rounded-2xl rounded-tl-sm px-5 py-4 flex items-center gap-1.5 shadow-sm">
      {[0, 150, 300].map(d => (
        <div key={d} className="w-2 h-2 rounded-full bg-black/20 animate-bounce" style={{animationDelay:`${d}ms`}}/>
      ))}
    </div>
  </div>
);

// ── Constants ──────────────────────────────────────────────────────────────
const STORAGE_KEY = "elysium_agent_messages";
const SESSION_KEY = "elysium_agent_session";

const CHIPS = [
  { icon: Scale,        label: "Compare",      query: "What are the top 3 molecules for EGFR by binding score?" },
  { icon: ShieldAlert,  label: "Troubleshoot", query: "Show ADMET stats for EGFR" },
  { icon: HeartPulse,   label: "Health",       query: "Which molecules are most similar to Aspirin?" },
  { icon: CheckCircle2, label: "Fact Check",   query: "Summarise all discovery runs so far" },
  { icon: FileText,     label: "Summarize",    query: "What molecules have Lipinski violations?" },
];

// ── Main ───────────────────────────────────────────────────────────────────
export default function Agent() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); }
    catch { return []; }
  });
  const [sessionId, setSessionId] = useState<string | undefined>(
    () => localStorage.getItem(SESSION_KEY) || undefined
  );
  const [sending, setSending] = useState(false);
  const [showInfo, setShowInfo] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const hasMessages = messages.length > 0;

  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(messages)); }, [messages]);
  useEffect(() => { if (sessionId) localStorage.setItem(SESSION_KEY, sessionId); }, [sessionId]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, sending]);

  const handleSend = async (text?: string) => {
    const txt = (text ?? inputRef.current?.value ?? "").trim();
    if (!txt || sending) return;
    if (!text && inputRef.current) inputRef.current.value = "";
    setSending(true);
    setMessages(prev => [...prev, { role: "user", content: txt }]);
    try {
      const res = await agentChat({ prompt: txt, session_id: sessionId });
      if (res.session_id) setSessionId(res.session_id);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: res.answer,
        evidence: res.evidence ?? [],
      }]);
    } catch (e: any) {
      const msg = e?.message || "Request failed";
      const isNotFound = msg.includes("Not Found") || msg.includes("404");
      setMessages(prev => [...prev, {
        role: "assistant",
        content: isNotFound
          ? "⚠️ Backend not reachable at /chat/message.\n\nCheck that:\n1. Your backend is running (`uvicorn app.main:app --reload`)\n2. `frontend/.env` has `VITE_API_BASE_URL=http://localhost:8000`\n3. Restart Vite after changing .env"
          : "⚠️ " + msg,
      }]);
    } finally {
      setSending(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSessionId(undefined);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(SESSION_KEY);
  };

  return (
    <div className="flex min-h-screen bg-[#F8F9FA] text-[#111111] font-sans p-4 md:p-6 gap-6">

      {/* ── Sidebar ── */}
      <aside className="w-64 bg-white rounded-[40px] border border-black/5 p-8 flex flex-col justify-between hidden lg:flex flex-shrink-0">
        <div className="space-y-12">
          <Link to="/" className="flex items-center gap-2 px-4">
            <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-white rounded-full"/>
            </div>
            <span className="text-lg font-bold tracking-tighter">ELYSIUM</span>
          </Link>
          <div className="space-y-8">
            <div className="space-y-2">
              <p className="px-4 text-[10px] font-bold tracking-widest uppercase opacity-20">Menu</p>
              <SidebarItem icon={Home}      label="Home"      to="/" />
              <SidebarItem icon={Activity}  label="Runs"      to="/discovery" />
              <SidebarItem icon={Compass}   label="Discovery" to="/dashboard" />
              <SidebarItem icon={BarChart3} label="Graphs"    to="/graphs" />
              <SidebarItem icon={Bot}       label="Agent"     to="/agent" active />
              <SidebarItem icon={Microscope}label="Analysis"  to="/analysis" />
            </div>
            <div className="space-y-2">
              <p className="px-4 text-[10px] font-bold tracking-widest uppercase opacity-20">General</p>
              <SidebarItem icon={Settings}  label="Settings" />
              <SidebarItem icon={HelpCircle}label="Help" />
              <SidebarItem icon={LogOut}    label="Logout" />
            </div>
          </div>
        </div>
        {/* Sidebar promo card */}
        <div className="bg-black rounded-[32px] p-6 relative overflow-hidden group">
          <div className="relative z-10 space-y-4">
            <div className="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center">
              <Bot size={18} className="text-white"/>
            </div>
            <p className="text-white text-sm font-medium leading-tight">ELYSIUM Agent</p>
            <p className="text-white/40 text-[10px]">LLM-powered with live molecular tool access</p>
            <button onClick={clearChat}
              className="w-full py-3 bg-white text-black rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-white/90 transition-all">
              New Chat
            </button>
          </div>
          <div className="absolute -bottom-4 -right-4 w-24 h-24 bg-purple-500/20 blur-2xl rounded-full group-hover:scale-150 transition-transform duration-1000"/>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="flex-1 flex flex-col gap-6 min-w-0">

        {/* Header bar */}
        <header className="flex items-center justify-between gap-6">
          <div className="flex-1 max-w-xl relative">
            <Search className="absolute left-6 top-1/2 -translate-y-1/2 text-black/20" size={18}/>
            <input
              placeholder="Search task"
              className="w-full bg-white border border-black/5 rounded-full py-4 pl-14 pr-20 text-sm focus:outline-none focus:border-black/20 transition-all"
            />
            <div className="absolute right-6 top-1/2 -translate-y-1/2 flex items-center gap-1 text-[10px] font-bold opacity-20">
              <span className="border border-black/20 rounded px-1">⌘</span>
              <span>F</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {hasMessages && (
              <button onClick={clearChat}
                className="flex items-center gap-2 px-4 py-2.5 bg-white border border-black/5 rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-black/5 transition-all">
                <X size={11}/> New Chat
              </button>
            )}
            <button onClick={() => setShowInfo(true)}
              className="w-12 h-12 bg-white rounded-full border border-black/5 flex items-center justify-center hover:bg-black/5 transition-all">
              <Info size={18} className="text-black/40"/>
            </button>
            <button className="w-12 h-12 bg-white rounded-full border border-black/5 flex items-center justify-center hover:bg-black/5 transition-all">
              <Mail size={18} className="text-black/40"/>
            </button>
            <button className="w-12 h-12 bg-white rounded-full border border-black/5 flex items-center justify-center hover:bg-black/5 transition-all relative">
              <Bell size={18} className="text-black/40"/>
              <div className="absolute top-3 right-3 w-2 h-2 bg-purple-500 rounded-full border-2 border-white"/>
            </button>
            <div className="flex items-center gap-3 pl-4 border-l border-black/5">
              <div className="hidden sm:block text-right">
                <p className="text-sm font-bold">Researcher</p>
                <p className="text-[10px] opacity-40">ELYSIUM Agent</p>
              </div>
              <div className="w-12 h-12 rounded-full bg-black flex items-center justify-center">
                <Bot size={20} className="text-white"/>
              </div>
            </div>
          </div>
        </header>

        {/* ── Chat area ── */}
        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="w-full max-w-3xl flex flex-col gap-8">

            {/* Hero — only when empty */}
            {!hasMessages && (
              <div className="text-center space-y-4 relative pt-8">
                <motion.div
                  animate={{ y: [0, -8, 0], scale: [1, 1.03, 1] }}
                  transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                  className="absolute -right-10 -top-4 w-32 h-32 bg-blue-400/15 rounded-full blur-3xl pointer-events-none"/>
                <h2 className="text-2xl font-medium text-blue-500">Hello, Researcher</h2>
                <h1 className="text-5xl font-display font-medium tracking-tight">How can I help you today?</h1>
              </div>
            )}

            {/* Messages */}
            {hasMessages && (
              <div className="space-y-5 max-h-[55vh] overflow-y-auto scrollbar-hide pr-1">
                {messages.map((msg, i) => <Bubble key={i} msg={msg}/>)}
                {sending && <Typing/>}
                <div ref={bottomRef}/>
              </div>
            )}

            {/* Input box */}
            <div className="space-y-4">
              <div className="relative group">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500 rounded-[32px] opacity-20 group-focus-within:opacity-100 transition-opacity blur-sm"/>
                <div className="relative bg-white rounded-[30px] p-6 shadow-xl border border-black/5">
                  <textarea
                    ref={inputRef}
                    placeholder="Ask anything..."
                    className="w-full bg-transparent border-none focus:outline-none text-lg resize-none h-28 scrollbar-hide"
                    onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }}}
                  />
                  <div className="flex items-center justify-between pt-4 border-t border-black/5">
                    <div className="flex items-center gap-2">
                      <button className="p-2 hover:bg-black/5 rounded-lg transition-all flex items-center gap-2 text-[10px] font-bold tracking-widest uppercase opacity-40">
                        <Paperclip size={16}/> Attach
                      </button>
                      <button className="p-2 hover:bg-black/5 rounded-lg transition-all flex items-center gap-2 text-[10px] font-bold tracking-widest uppercase opacity-40">
                        <Wrench size={16}/> Tools
                      </button>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="px-3 py-1.5 bg-black/5 rounded-lg text-[10px] font-bold tracking-widest uppercase opacity-40">
                        ELYSIUM AGENT
                      </span>
                      <button onClick={() => handleSend()} disabled={sending}
                        className="w-10 h-10 bg-black text-white rounded-full flex items-center justify-center hover:bg-black/80 transition-all disabled:opacity-50">
                        {sending
                          ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
                          : <Send size={16}/>}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Chips — only when empty */}
              {!hasMessages && (
                <div className="flex flex-wrap justify-center gap-2">
                  {CHIPS.map((c, i) => (
                    <button key={i} onClick={() => handleSend(c.query)}
                      className="flex items-center gap-2 px-4 py-2.5 bg-white border border-black/5 rounded-xl text-[10px] font-bold tracking-widest uppercase hover:bg-black/5 transition-all">
                      <c.icon size={14} className="opacity-40"/> {c.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* ── Info modal — FIXED: proper centering with z-index ── */}
      <AnimatePresence>
        {showInfo && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setShowInfo(false)}
              className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[200]"/>
            {/* Modal — fixed to viewport center */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              className="fixed inset-0 flex items-center justify-center z-[201] p-6 pointer-events-none">
              <div className="w-full max-w-md bg-[#111111] text-white rounded-[40px] p-10 shadow-2xl pointer-events-auto">
                <button onClick={() => setShowInfo(false)}
                  className="absolute top-6 right-6 w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-all">
                  <X size={20}/>
                </button>
                <div className="space-y-8">
                  <div className="space-y-2">
                    <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-white/40">How it works</p>
                    <h2 className="text-2xl font-display font-medium">Agent Intelligence</h2>
                  </div>
                  <div className="space-y-6">
                    {[
                      "Your query goes to POST /chat/message on your FastAPI backend.",
                      "The LLM (via OpenRouter) picks from 4 tools: get_top_molecules, get_similar_to_drug, get_runs_summary, get_admet_stats.",
                      "Selected tools query your live SQLite database for real molecular data.",
                      "A grounded response is synthesised from actual run data — no hallucination.",
                    ].map((t, i) => (
                      <div key={i} className="flex gap-5">
                        <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0 text-xs font-bold">{i+1}</div>
                        <p className="text-sm text-white/60 leading-relaxed">{t}</p>
                      </div>
                    ))}
                  </div>
                  <div className="bg-white/5 rounded-2xl p-4 space-y-2">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-white/30">Chat persistence</p>
                    <p className="text-xs text-white/50 leading-relaxed">Conversation saved in browser storage across page changes. "New Chat" clears it.</p>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

    </div>
  );
}