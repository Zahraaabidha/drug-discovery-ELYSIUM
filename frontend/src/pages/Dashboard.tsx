import { useState, useEffect } from "react";
import { motion } from "motion/react";
import { 
  Activity,
  Compass,
  BarChart3,
  Bot,
  Microscope,
  Home,
  Settings, 
  HelpCircle, 
  LogOut, 
  Search, 
  Mail, 
  Bell,
  Plus,
  ArrowUpRight,
  Play,
  Pause,
  Square,
  MoreHorizontal
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { discoverMolecules, listRuns } from "../api/elysium";
import type { RunSummary } from "../api/elysium";
import { API_BASE_URL } from "../api/client";
import type { Molecule } from "../api/elysium";

const SidebarItem = ({ icon: Icon, label, active = false, count, to }: { icon: any, label: string, active?: boolean, count?: string, to?: string }) => (
  <Link to={to || "#"} className={`flex items-center justify-between px-4 py-3 rounded-xl cursor-pointer transition-all ${active ? 'bg-black text-white' : 'text-black/40 hover:bg-black/5 hover:text-black'}`}>
    <div className="flex items-center gap-3">
      <Icon size={20} strokeWidth={active ? 2 : 1.5} />
      <span className="text-sm font-medium">{label}</span>
    </div>
    {count && (
      <span className={`text-[10px] px-2 py-0.5 rounded-full ${active ? 'bg-white/20' : 'bg-black/5 text-black/60'}`}>
        {count}
      </span>
    )}
  </Link>
);

const StatCard = ({ title, value, change, trend, active = false }: { title: string, value: string, change: string, trend: 'up' | 'down', active?: boolean }) => (
  <div className={`p-6 rounded-[32px] border border-black/5 flex flex-col justify-between min-h-[180px] transition-all ${active ? 'bg-black text-white' : 'bg-white hover:shadow-lg'}`}>
    <div className="flex justify-between items-start">
      <span className={`text-xs font-medium ${active ? 'opacity-60' : 'opacity-40'}`}>{title}</span>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${active ? 'bg-white/10' : 'bg-black/5'}`}>
        <ArrowUpRight size={16} className={active ? 'text-white' : 'text-black'} />
      </div>
    </div>
    <div className="space-y-2">
      <div className="text-4xl font-display font-medium">{value}</div>
      <div className="flex items-center gap-2">
        <div className={`flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full ${active ? 'bg-white/10 text-white' : 'bg-purple-50 text-purple-600'}`}>
          <ArrowUpRight size={10} />
          {change}
        </div>
        <span className={`text-[10px] ${active ? 'opacity-40' : 'opacity-20'}`}>Increased from last month</span>
      </div>
    </div>
  </div>
);


// ── Expandable molecule result card ──────────────────────────────────────
const MolResultCard: React.FC<{ m: any; rank: number; target: string }> = ({ m, rank, target }) => {
  const [expanded, setExpanded] = useState(false);
  const isTop = rank <= 3;
  const scoreColor = m.score >= 0.85 ? "text-green-600" : "text-purple-600";
  const barColor = m.score >= 0.85 ? "bg-green-500" : "bg-purple-500";

  return (
    <div className={`rounded-[24px] border overflow-hidden transition-all ${isTop ? "border-purple-100" : "border-black/5"} bg-white`}>
      {/* Collapsed row */}
      <div className="flex items-center gap-4 px-5 py-4">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${isTop ? "bg-black text-white" : "bg-black/5 text-black/40"}`}>
          {rank}
        </div>
        <p className="font-mono text-[11px] text-black/50 flex-1 truncate min-w-0">{m.smiles}</p>
        <span className="text-[9px] font-bold text-purple-600 bg-purple-50 border border-purple-100 px-2.5 py-1 rounded-full flex-shrink-0">{target}</span>
        <div className="flex items-center gap-3 flex-shrink-0 w-32">
          <div className="flex-1 h-1.5 bg-black/5 rounded-full overflow-hidden">
            <div className={`h-full ${barColor} rounded-full`} style={{width: `${m.score * 100}%`}}/>
          </div>
          <span className={`text-[11px] font-bold w-10 text-right ${scoreColor}`}>{m.score.toFixed(3)}</span>
        </div>
        <button onClick={() => setExpanded(!expanded)}
          className="w-7 h-7 rounded-lg bg-black/5 hover:bg-black/10 flex items-center justify-center transition-colors flex-shrink-0">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
            className={`transition-transform ${expanded ? "rotate-180" : ""}`}>
            <path d="M6 9l6 6 6-6"/>
          </svg>
        </button>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-black/5 px-5 py-5 bg-[#F8F9FA] space-y-4">
          <div className="flex gap-5 items-start">
            {m.smiles && (
              <img
                src={`${API_BASE_URL}/molecule/image?smiles=${encodeURIComponent(m.smiles)}`}
                alt="molecule"
                className="w-24 h-24 rounded-2xl border border-black/5 bg-white object-contain flex-shrink-0"
                onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
            )}
            <div className="flex-1 min-w-0 space-y-3">
              <div>
                <p className="text-[9px] font-bold tracking-widests uppercase opacity-30 mb-1.5">Binding Score</p>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-1.5 bg-black/10 rounded-full overflow-hidden">
                    <div className={`h-full ${barColor} rounded-full`} style={{width: `${m.score * 100}%`}}/>
                  </div>
                  <span className={`text-sm font-bold ${scoreColor}`}>{m.score.toFixed(3)}</span>
                </div>
              </div>
              {m.similar_drug && (
                <div className="flex items-center gap-3">
                  <p className="text-[9px] font-bold tracking-widests uppercase opacity-30 w-20 flex-shrink-0">Similar To</p>
                  <span className="text-xs font-bold">{m.similar_drug.name}</span>
                  {m.similar_drug.similarity != null && (
                    <span className="text-[9px] font-bold text-purple-500 ml-auto">Tanimoto {m.similar_drug.similarity.toFixed(2)}</span>
                  )}
                </div>
              )}
            </div>
          </div>
          {m.admet && (
            <div className="flex flex-wrap gap-2">
              {[
                { k: "MW", v: `${m.admet.molecular_weight.toFixed(1)} Da` },
                { k: "logP", v: m.admet.logp.toFixed(2) },
                { k: "HBD", v: m.admet.hbd },
                { k: "HBA", v: m.admet.hba },
                { k: "TPSA", v: `${m.admet.tpsa.toFixed(1)} Ų` },
              ].map(p => (
                <div key={p.k} className="flex flex-col items-center bg-white border border-black/5 rounded-xl px-3 py-2 min-w-[56px]">
                  <span className="text-[8px] uppercase tracking-wider opacity-30 font-bold">{p.k}</span>
                  <span className="text-[11px] font-bold mt-0.5">{p.v}</span>
                </div>
              ))}
              <div className={`flex flex-col items-center rounded-xl px-3 py-2 min-w-[56px] border ${m.admet.lipinski_pass ? "bg-green-50 border-green-100" : "bg-red-50 border-red-100"}`}>
                <span className="text-[8px] uppercase tracking-wider font-bold opacity-50">Lipinski</span>
                <span className={`text-[11px] font-bold mt-0.5 ${m.admet.lipinski_pass ? "text-green-600" : "text-red-500"}`}>
                  {m.admet.lipinski_pass ? "Pass" : "Fail"}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [lipinski, setLipinski] = useState(true);
  const [admet, setAdmet] = useState(false);
  const [targetInput, setTargetInput] = useState("EGFR");
  const [molCount, setMolCount] = useState(7);
  const [loading, setLoading] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [results, setResults] = useState<Molecule[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [recentRuns, setRecentRuns] = useState<RunSummary[]>([]);

  useEffect(() => {
    listRuns().then(d => setRecentRuns(d.runs.slice(0, 5))).catch(console.error);
  }, [runId]);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const res = await discoverMolecules({
        target_id: targetInput,
        num_molecules: molCount,
        lipinski_only: lipinski,
      });
      setRunId(res.run_id);
      setResults(res.molecules);
    } catch (e: any) {
      setError(e?.message || "Discovery failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-[#F8F9FA] text-[#111111] font-sans p-4 md:p-6 gap-6">
      {/* Sidebar */}
      <aside className="w-64 bg-white rounded-[40px] border border-black/5 p-8 flex flex-col justify-between hidden lg:flex">
        <div className="space-y-12">
          <Link to="/" className="flex items-center gap-2 px-4">
            <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-white rounded-full" />
            </div>
            <span className="text-lg font-bold tracking-tighter">ELYSIUM</span>
          </Link>

          <div className="space-y-8">
            <div className="space-y-2">
              <p className="px-4 text-[10px] font-bold tracking-widest uppercase opacity-20">Menu</p>
              <SidebarItem icon={Home} label="Home" to="/" />
              <SidebarItem icon={Activity} label="Runs" to="/discovery" />
              <SidebarItem icon={Compass} label="Discovery" to="/dashboard" active />
              <SidebarItem icon={BarChart3} label="Graphs" to="/graphs" />
              <SidebarItem icon={Bot} label="Agent" to="/agent" />
              <SidebarItem icon={Microscope} label="Analysis" to="/analysis" />
            </div>

            <div className="space-y-2">
              <p className="px-4 text-[10px] font-bold tracking-widest uppercase opacity-20">General</p>
              <SidebarItem icon={Settings} label="Settings" />
              <SidebarItem icon={HelpCircle} label="Help" />
              <SidebarItem icon={LogOut} label="Logout" />
            </div>
          </div>
        </div>

        {/* Promo Card */}
        <div className="bg-black rounded-[32px] p-6 relative overflow-hidden group">
          <div className="relative z-10 space-y-4">
            <div className="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-white rounded-sm" />
            </div>
            <p className="text-white text-sm font-medium leading-tight">Download our <br /> Mobile App</p>
            <p className="text-white/40 text-[10px]">Get easy in another way</p>
            <button className="w-full py-3 bg-white text-black rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-white/90 transition-all">
              Download
            </button>
          </div>
          <div className="absolute -bottom-4 -right-4 w-24 h-24 bg-purple-500/20 blur-2xl rounded-full group-hover:scale-150 transition-transform duration-1000" />
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col gap-6">
        {/* Header */}
        <header className="flex items-center justify-between gap-6">
          <div className="flex-1 max-w-xl relative">
            <Search className="absolute left-6 top-1/2 -translate-y-1/2 text-black/20" size={18} />
            <input 
              type="text" 
              placeholder="Search task" 
              className="w-full bg-white border border-black/5 rounded-full py-4 pl-14 pr-20 text-sm focus:outline-none focus:border-black/20 transition-all"
            />
            <div className="absolute right-6 top-1/2 -translate-y-1/2 flex items-center gap-1 text-[10px] font-bold opacity-20">
              <span className="border border-black/20 rounded px-1">⌘</span>
              <span>F</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="w-12 h-12 bg-white rounded-full border border-black/5 flex items-center justify-center hover:bg-black/5 transition-all">
              <Mail size={18} className="text-black/40" />
            </button>
            <button className="w-12 h-12 bg-white rounded-full border border-black/5 flex items-center justify-center hover:bg-black/5 transition-all relative">
              <Bell size={18} className="text-black/40" />
              <div className="absolute top-3 right-3 w-2 h-2 bg-purple-500 rounded-full border-2 border-white" />
            </button>
            <div className="flex items-center gap-3 pl-4 border-l border-black/5">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-bold">Totok Michael</p>
                <p className="text-[10px] opacity-40">tmichael20@gmail.com</p>
              </div>
              <img 
                src="https://i.pravatar.cc/100?u=dashboard-user" 
                className="w-12 h-12 rounded-full border-2 border-white shadow-sm"
                alt="Profile"
                referrerPolicy="no-referrer"
              />
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <div className="flex-1 flex flex-col gap-6 overflow-y-auto scrollbar-hide">
          {/* Title & Actions */}
          <div className="flex justify-between items-end">
            <div className="space-y-1">
              <h1 className="text-4xl font-display font-medium tracking-tight">Discovery</h1>
              <p className="text-sm opacity-40">Define a target, set constraints, and run the pipeline.</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleRun}
                disabled={loading}
                className="px-6 py-3 bg-black text-white rounded-full text-[10px] font-bold tracking-widest uppercase flex items-center gap-2 hover:bg-black/80 transition-all disabled:opacity-50">
                <Plus size={14} />
                {loading ? "Running…" : "Run Pipeline"}
              </button>
              <button
                onClick={() => navigate("/discovery")}
                className="px-6 py-3 bg-white border border-black/5 rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-black/5 transition-all">
                View Runs
              </button>
            </div>
          </div>

          {/* Discovery Controls Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Box 1: Target & Molecule */}
            <div className="bg-white rounded-[32px] border border-black/5 p-6 flex flex-col justify-between min-h-[180px]">
              <div className="space-y-4">
                <div className="space-y-1">
                  <label className="text-[9px] font-bold tracking-widest uppercase opacity-40">Target Identifier</label>
                  <input 
                    type="text"
                    value={targetInput}
                    onChange={e => setTargetInput(e.target.value)}
                    className="w-full bg-[#F8F9FA] border border-black/5 rounded-xl py-2 px-3 text-xs font-medium focus:outline-none focus:border-black/10 transition-all"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] font-bold tracking-widest uppercase opacity-40">Molecule Count</label>
                  <input 
                    type="number"
                    value={molCount}
                    onChange={e => setMolCount(Number(e.target.value))}
                    className="w-full bg-[#F8F9FA] border border-black/5 rounded-xl py-2 px-3 text-xs font-medium focus:outline-none focus:border-black/10 transition-all"
                  />
                </div>
              </div>
            </div>

            {/* Box 2: Constraints */}
            <div className="bg-white rounded-[32px] border border-black/5 p-6 flex flex-col justify-between min-h-[180px]">
              <div className="space-y-4">
                <label className="text-[9px] font-bold tracking-widest uppercase opacity-40">Constraints</label>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-medium opacity-60">Lipinski</span>
                    <button 
                      onClick={() => setLipinski(!lipinski)}
                      className={`w-10 h-5 rounded-full transition-all relative ${lipinski ? 'bg-purple-500' : 'bg-black/10'}`}
                    >
                      <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-all ${lipinski ? 'left-5.5' : 'left-0.5'}`} />
                    </button>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-medium opacity-60">ADMET</span>
                    <button 
                      onClick={() => setAdmet(!admet)}
                      className={`w-10 h-5 rounded-full transition-all relative ${admet ? 'bg-purple-500' : 'bg-black/10'}`}
                    >
                      <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-all ${admet ? 'left-5.5' : 'left-0.5'}`} />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Box 3: Run Discovery */}
            <div onClick={handleRun} className="bg-black rounded-[32px] p-6 flex flex-col justify-between min-h-[180px] group cursor-pointer hover:bg-black/90 transition-all">
              <div className="flex justify-between items-start">
                <span className="text-[9px] font-bold tracking-widest uppercase text-white/40">Action</span>
                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                  {loading
                    ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
                    : <Play size={14} className="text-white" fill="currentColor" />}
                </div>
              </div>
              <div className="space-y-2">
                <h3 className="text-white text-lg font-display font-medium">{loading ? "Running…" : "Run Discovery"}</h3>
                {runId && <p className="text-white/40 text-[9px] truncate">ID: {runId}</p>}
                {error && <p className="text-red-400 text-[9px]">{error}</p>}
              </div>
            </div>

            {/* Box 4: Go Again */}
            <div onClick={() => { setResults([]); setRunId(null); setError(null); }} className="bg-white rounded-[32px] border border-black/5 p-6 flex flex-col justify-between min-h-[180px] group cursor-pointer hover:shadow-lg transition-all">
              <div className="flex justify-between items-start">
                <span className="text-[9px] font-bold tracking-widest uppercase opacity-40">Reset</span>
                <div className="w-8 h-8 rounded-full bg-black/5 flex items-center justify-center group-hover:rotate-180 transition-transform duration-500">
                  <Activity size={14} className="text-black" />
                </div>
              </div>
              <div className="space-y-1">
                <h3 className="text-lg font-display font-medium">Go Again</h3>
                <p className="text-[9px] opacity-40">Clear all parameters</p>
              </div>
            </div>
          </div>

          {/* Results Row */}
          <div className="flex-1 flex flex-col">
            <div className="bg-white rounded-[40px] border border-black/5 p-8 flex flex-col flex-1 min-h-[400px]">
              <div className="flex justify-between items-center mb-8">
                <h3 className="text-xl font-display font-medium">Results</h3>
                <span className="text-xs font-medium opacity-40">{results.length} molecules</span>
              </div>
              {results.length === 0 && !loading ? (
                <div className="flex-1 flex items-center justify-center border-2 border-dashed border-black/5 rounded-[32px]">
                  <p className="text-xs font-medium opacity-20">Run discovery to populate agent-ranked candidates.</p>
                </div>
              ) : loading ? (
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center space-y-3">
                    <div className="w-8 h-8 border-2 border-purple-200 border-t-purple-500 rounded-full animate-spin mx-auto"/>
                    <p className="text-xs opacity-40">Orchestrating pipeline…</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 overflow-y-auto">
                  {results.map((m, i) => (
                    <MolResultCard key={i} m={m} rank={i+1} target={targetInput} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Right Sidebar - Project List & Agent Plan */}
      <aside className="w-80 flex flex-col gap-6 hidden xl:flex">
        {/* Recent Runs */}
        <div className="bg-white rounded-[40px] border border-black/5 p-8 flex flex-col max-h-[450px]">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold">Recent Runs</h3>
            <Link to="/discovery"
              className="px-4 py-2 border border-black/5 rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-black/5 transition-all">
              View All
            </Link>
          </div>
          <div className="space-y-4 overflow-y-auto pr-2 scrollbar-hide">
            {recentRuns.length === 0 ? (
              <p className="text-xs opacity-30 text-center py-6">No runs yet. Run a discovery above.</p>
            ) : recentRuns.map((run, i) => {
              const icons = ["🧬", "⚗️", "🔬", "💊", "🧪"];
              return (
                <div key={run.run_id} onClick={() => navigate(`/runs/${run.run_id}`)}
                  className="flex items-center justify-between group cursor-pointer hover:-mx-2 hover:px-2 hover:bg-black/[0.02] rounded-2xl transition-all py-1">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center text-lg group-hover:bg-black group-hover:text-white transition-all">
                      {icons[i % icons.length]}
                    </div>
                    <div>
                      <p className="text-sm font-bold">{run.target_id} Discovery</p>
                      <p className="text-[10px] opacity-40">{new Date(run.created_at).toLocaleDateString()} · {run.num_molecules} molecules</p>
                    </div>
                  </div>
                  <MoreHorizontal size={16} className="opacity-20 group-hover:opacity-100 transition-opacity" />
                </div>
              );
            })}
          </div>
        </div>

        {/* Agent Plan Preview - Moved to Sidebar */}
        <div className="bg-white rounded-[40px] border border-black/5 p-8 space-y-8 flex-1">
          <div className="flex justify-between items-start">
            <div className="space-y-1">
              <p className="text-[10px] font-bold tracking-widest uppercase opacity-40">Agent Plan Preview</p>
              <h3 className="text-xl font-display font-medium">Planner outline</h3>
            </div>
            <span className="text-[10px] font-bold tracking-widest uppercase opacity-20">Auto</span>
          </div>

          <div className="space-y-5">
            {[
              "Sample candidate scaffolds",
              "Score binding with DeepPurpose",
              "Apply RDKit ADMET filters",
              "Attach nearest-known drug context"
            ].map((step, i) => (
              <div key={i} className="flex items-center gap-4 group">
                <div className="w-8 h-8 rounded-full bg-[#F8F9FA] flex-shrink-0 flex items-center justify-center text-[9px] font-bold opacity-40 group-hover:bg-black group-hover:text-white transition-all">
                  {i + 1}
                </div>
                <p className="text-[11px] font-medium opacity-40 group-hover:opacity-100 transition-opacity leading-tight">
                  {step}
                </p>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}