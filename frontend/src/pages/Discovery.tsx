import { useState, useEffect } from "react";
import { Database as LibraryIcon } from "lucide-react";
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
  MoreHorizontal,
  Filter,
  Download,
  ChevronRight
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { listRuns } from "../api/elysium";
import type { RunSummary } from "../api/elysium";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from 'recharts';

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

const DiscoveryStatCard = ({ title, value, subValue, change, chartData, active = false }: { title: string, value: string, subValue?: string, change?: string, chartData?: any[], active?: boolean }) => (
  <div className={`p-6 rounded-[32px] border border-black/5 flex flex-col justify-between min-h-[180px] transition-all ${active ? 'bg-[#111111] text-white' : 'bg-white hover:shadow-lg'}`}>
    <div className="flex justify-between items-start">
      <span className={`text-[10px] font-bold tracking-widest uppercase ${active ? 'opacity-40' : 'opacity-20'}`}>{title}</span>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${active ? 'bg-white/10' : 'bg-black/5'}`}>
        <ArrowUpRight size={14} className={active ? 'text-white' : 'text-black'} />
      </div>
    </div>
    
    <div className="flex items-end justify-between gap-4">
      <div className="space-y-1">
        <div className="text-4xl font-display font-medium tracking-tight">{value}</div>
        {subValue && <div className={`text-[10px] font-medium ${active ? 'opacity-40' : 'opacity-40'}`}>{subValue}</div>}
      </div>
      
      {chartData && (
        <div className="w-16 h-12 flex items-end gap-1">
          {chartData.map((val, i) => (
            <div 
              key={i} 
              className={`w-1 rounded-full ${active ? 'bg-purple-500' : 'bg-purple-200'}`} 
              style={{ height: `${val}%` }} 
            />
          ))}
        </div>
      )}
    </div>
  </div>
);




export default function Discovery() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    listRuns()
      .then(d => setRuns(d.runs))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const [targetFilter, setTargetFilter] = useState<string>("");
  const filtered = runs.filter(r =>
    (!targetFilter || r.target_id === targetFilter) &&
    (r.run_id.toLowerCase().includes(search.toLowerCase()) ||
     r.target_id.toLowerCase().includes(search.toLowerCase()))
  );

  // All figures below are computed from the runs returned by the API (most recent 50).
  const totalMolecules = runs.reduce((n, r) => n + r.num_molecules, 0);
  const byTarget = Object.entries(runs.reduce<Record<string, number>>((acc, r) => { acc[r.target_id] = (acc[r.target_id] ?? 0) + 1; return acc; }, {}))
    .sort((a, b) => b[1] - a[1]);
  const maxTargetRuns = byTarget[0]?.[1] ?? 1;
  const DAYS = ["S", "M", "T", "W", "T", "F", "S"];
  const runActivityData = DAYS.map((day, i) => ({ day, runs: runs.filter(r => new Date(r.created_at).getDay() === i).length }));
  const maxDayRuns = Math.max(1, ...runActivityData.map(d => d.runs));

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
              <SidebarItem icon={Activity} label="Runs" to="/discovery" active />
              <SidebarItem icon={Compass} label="Discovery" to="/dashboard" />
              <SidebarItem icon={LibraryIcon} label="Library" to="/library" />
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
              placeholder="Search runs..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-white border border-black/5 rounded-full py-4 pl-14 pr-20 text-sm focus:outline-none focus:border-black/20 transition-all"
            />
            <div className="absolute right-6 top-1/2 -translate-y-1/2 flex items-center gap-1 text-[10px] font-bold opacity-20">
              <span className="border border-black/20 rounded px-1">⌘</span>
              <span>F</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="px-6 py-4 bg-black text-white rounded-full text-[10px] font-bold tracking-widest uppercase flex items-center gap-2 hover:bg-black/80 transition-all">
              <Plus size={14} />
              New Run
            </button>
            <div className="flex items-center gap-3 pl-4 border-l border-black/5">
              <img 
                src="https://i.pravatar.cc/100?u=dashboard-user" 
                className="w-12 h-12 rounded-full border-2 border-white shadow-sm"
                alt="Profile"
                referrerPolicy="no-referrer"
              />
            </div>
          </div>
        </header>

        {/* Discovery Content */}
        <div className="flex-1 flex flex-col gap-6 overflow-y-auto scrollbar-hide">
          {/* Title */}
          <div className="space-y-1">
            <h1 className="text-4xl font-display font-medium tracking-tight">Discovery Runs</h1>
            <p className="text-sm opacity-40">Plan, track, and audit every experiment with full provenance.</p>
          </div>

          {/* Stats Grid (computed from the API response) */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <DiscoveryStatCard title="Runs" value={String(runs.length)} subValue="most recent 50 shown" active />
            <DiscoveryStatCard title="Targets" value={String(byTarget.length)} subValue="distinct targets screened" />
            <DiscoveryStatCard title="Molecules" value={String(totalMolecules)} subValue="stored across these runs" />
          </div>

          {/* Middle Row: Activity & Targets */}
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Run Activity */}
            <div className="lg:col-span-2 bg-white rounded-[40px] border border-black/5 p-8 flex flex-col">
              <div className="flex justify-between items-center mb-8">
                <h3 className="text-sm font-bold">Run Activity</h3>
                <span className="text-[10px] font-bold tracking-widest uppercase opacity-20">Runs by day of week</span>
              </div>
              <div className="flex-1 min-h-[180px] flex items-end justify-between px-4">
                {runActivityData.map((item, i) => (
                  <div key={i} className="flex flex-col items-center gap-4 group">
                    <div className="relative w-12 flex items-end justify-center">
                      <motion.div 
                        initial={{ height: 0 }}
                        animate={{ height: `${Math.max(4, (item.runs / maxDayRuns) * 120)}px` }}
                        className="w-full bg-purple-500 rounded-xl group-hover:bg-purple-600 transition-colors"
                      />
                    </div>
                    <span className="text-[10px] font-bold opacity-40" title={`${item.runs} run(s)`}>{item.day}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Targets */}
            <div className="bg-white rounded-[40px] border border-black/5 p-8 flex flex-col">
              <div className="flex justify-between items-center mb-8">
                <h3 className="text-sm font-bold">Targets</h3>
                <span className="text-[10px] font-bold tracking-widest uppercase opacity-20">{byTarget.length} active</span>
              </div>
              <div className="space-y-6 flex-1 flex flex-col justify-center">
                {byTarget.length === 0 && <p className="text-xs opacity-40">No runs yet.</p>}
                {byTarget.map(([t, n]) => (
                  <div key={t} className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="px-3 py-1 bg-purple-50 text-purple-600 rounded-lg text-[10px] font-bold">{t}</span>
                      <span className="text-xs font-bold opacity-40">{n} run{n === 1 ? "" : "s"}</span>
                    </div>
                    <div className="h-2 bg-black/5 rounded-full overflow-hidden">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${(n / maxTargetRuns) * 100}%` }} className="h-full bg-purple-500 rounded-full" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* All Runs Table */}
          <div className="bg-white rounded-[40px] border border-black/5 p-8">
            <div className="flex justify-between items-center mb-8">
              <h3 className="text-sm font-bold">All Runs</h3>
              <div className="flex gap-2 flex-wrap">
                {["", ...byTarget.map(([t]) => t)].map(t => (
                  <button key={t || "all"} onClick={() => setTargetFilter(t)} aria-pressed={targetFilter === t}
                    className={`px-4 py-1.5 rounded-full text-[10px] font-bold tracking-widest uppercase transition-all ${targetFilter === t ? "bg-black text-white" : "bg-black/5 text-black/40 hover:bg-black/10"}`}>{t || "All"}</button>
                ))}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left border-b border-black/5">
                    <th className="pb-4 text-[10px] font-bold tracking-widest uppercase opacity-20">Run ID</th>
                    <th className="pb-4 text-[10px] font-bold tracking-widest uppercase opacity-20">Target</th>
                    <th className="pb-4 text-[10px] font-bold tracking-widest uppercase opacity-20">Molecules</th>
                    <th className="pb-4 text-[10px] font-bold tracking-widest uppercase opacity-20">Created</th>
                    <th className="pb-4 text-[10px] font-bold tracking-widest uppercase opacity-20">Status</th>
                    <th className="pb-4"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-black/5">
                  {loading ? (
                    <tr><td colSpan={6} className="py-12 text-center text-xs opacity-40">Loading runs…</td></tr>
                  ) : filtered.length === 0 ? (
                    <tr><td colSpan={6} className="py-12 text-center text-xs opacity-40">No runs found.</td></tr>
                  ) : filtered.map((run, i) => {
                    // real status recorded with the run (not inferred from position)
                    const STATUS: Record<string, [string, string]> = {
                      completed: ["Completed", "bg-green-50 text-green-600 border-green-100"],
                      failed: ["Failed", "bg-red-50 text-red-600 border-red-100"],
                      legacy_unverified: ["Legacy", "bg-yellow-50 text-yellow-700 border-yellow-100"],
                    };
                    const [status, statusColor] = STATUS[run.status ?? ""] ?? ["Unknown", "bg-black/5 text-black/50 border-black/10"];
                    return (
                    <tr key={run.run_id} onClick={() => navigate(`/runs/${run.run_id}`)} className="group hover:bg-black/[0.01] transition-colors cursor-pointer">
                      <td className="py-5">
                        <span className="text-xs font-medium text-purple-500 hover:underline">{run.run_id}</span>
                      </td>
                      <td className="py-5">
                        <span className="px-3 py-1 bg-purple-50 text-purple-600 rounded-lg text-[10px] font-bold">{run.target_id}</span>
                      </td>
                      <td className="py-5">
                        <span className="text-xl font-display font-medium">{run.num_molecules}</span>
                      </td>
                      <td className="py-5">
                        <span className="text-xs font-medium opacity-40">{new Date(run.created_at).toLocaleString()}</span>
                      </td>
                      <td className="py-5">
                        <span className={`px-4 py-1.5 rounded-full text-[10px] font-bold border ${statusColor}`}>{status}</span>
                      </td>
                      <td className="py-5 text-right">
                        <button className="w-8 h-8 rounded-full border border-black/5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all hover:bg-black hover:text-white">
                          <ChevronRight size={14} />
                        </button>
                      </td>
                    </tr>
                  );})}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>

      {/* Right Sidebar */}
      <aside className="w-80 flex flex-col gap-6 hidden xl:flex">
        {/* Recent Runs */}
        <div className="bg-white rounded-[40px] border border-black/5 p-8 flex flex-col max-h-[400px]">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold">Recent Runs</h3>
            <button className="text-[10px] font-bold tracking-widest uppercase text-purple-500 hover:text-purple-600">+ New</button>
          </div>
          <div className="space-y-6 overflow-y-auto pr-2 scrollbar-hide">
            {[1, 2, 3, 4, 5].map((_, i) => (
              <div key={i} className="flex items-center gap-4 group cursor-pointer">
                <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center text-lg group-hover:bg-purple-500 group-hover:text-white transition-all">
                  {i % 2 === 0 ? "🧬" : "🧪"}
                </div>
                <div>
                  <p className="text-sm font-bold">EGFR Discovery</p>
                  <p className="text-[10px] opacity-40">Due: 12/04/2026</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Molecule Output */}
        <div className="bg-[#111111] rounded-[40px] p-8 flex flex-col gap-8">
          <div className="space-y-1">
            <p className="text-[10px] font-bold tracking-widest uppercase text-white/40">Molecule Output</p>
            <div className="flex gap-8">
              <div>
                <div className="text-3xl font-display font-medium text-white">127</div>
                <p className="text-[9px] text-white/20">Total generated</p>
              </div>
              <div>
                <div className="text-3xl font-display font-medium text-white">1</div>
                <p className="text-[9px] text-white/20">Unique targets</p>
              </div>
            </div>
          </div>

          <div className="flex items-end justify-between h-20 gap-1 px-2">
            {[30, 50, 40, 60, 45, 70, 65].map((h, i) => (
              <div key={i} className="flex-1 bg-purple-500/40 rounded-t-sm" style={{ height: `${h}%` }} />
            ))}
          </div>

          <button className="w-full py-4 bg-white/5 border border-white/10 text-white rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-white/10 transition-all flex items-center justify-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-purple-500" />
            View Analysis
          </button>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-[40px] border border-black/5 p-8 flex-1 flex flex-col">
          <h3 className="text-[10px] font-bold tracking-widest uppercase opacity-20 mb-6">Quick Actions</h3>
          <div className="space-y-2 flex-1">
            {[
              { label: "New Discovery Run", icon: Plus },
              { label: "Knowledge Graph", icon: Compass },
              { label: "Agent Chat", icon: Bot },
              { label: "Analytics", icon: BarChart3 },
            ].map((action, i) => (
              <button key={i} className="w-full p-4 rounded-2xl border border-black/5 flex items-center justify-between group hover:bg-black/5 transition-all">
                <div className="flex items-center gap-4">
                  <div className="w-8 h-8 rounded-lg bg-black/5 flex items-center justify-center group-hover:bg-white transition-all">
                    <action.icon size={14} className="opacity-40" />
                  </div>
                  <span className="text-xs font-bold">{action.label}</span>
                </div>
                <ChevronRight size={14} className="opacity-10 group-hover:opacity-40 transition-opacity" />
              </button>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}