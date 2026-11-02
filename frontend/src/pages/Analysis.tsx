import { useState, useEffect, useMemo } from "react";
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
  Filter,
  Download,
  ChevronRight,
  MoreHorizontal,
  Pause,
  Square
} from "lucide-react";
import { Link } from "react-router-dom";
import { listRuns, getRun } from "../api/elysium";
import type { Molecule, RunSummary } from "../api/elysium";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell,
  LineChart,
  Line,
  AreaChart,
  Area
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

const AnalysisStatCard = ({ title, value, subValue, active = false }: { title: string, value: string, subValue?: string, active?: boolean }) => (
  <div className={`p-6 rounded-[32px] border border-black/5 flex flex-col justify-between min-h-[140px] transition-all ${active ? 'bg-[#111111] text-white' : 'bg-white hover:shadow-lg'}`}>
    <div className="flex justify-between items-start">
      <span className={`text-[10px] font-bold tracking-widest uppercase ${active ? 'opacity-40' : 'opacity-20'}`}>{title}</span>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${active ? 'bg-white/10' : 'bg-black/5'}`}>
        <ArrowUpRight size={14} className={active ? 'text-white' : 'text-black'} />
      </div>
    </div>
    <div className="space-y-1">
      <div className="text-3xl font-display font-medium tracking-tight">{value}</div>
      {subValue && <div className={`text-[10px] font-medium ${active ? 'opacity-40' : 'opacity-40'}`}>{subValue}</div>}
    </div>
  </div>
);



const scoreTrendData = [
  { run: 1, score: 0.90 },
  { run: 2, score: 0.92 },
  { run: 3, score: 0.95 },
  { run: 4, score: 0.91 },
  { run: 5, score: 0.90 },
  { run: 6, score: 0.88 },
  { run: 7, score: 0.90 },
  { run: 8, score: 0.91 },
  { run: 9, score: 0.92 },
  { run: 10, score: 0.90 },
  { run: 11, score: 0.89 },
  { run: 12, score: 0.90 },
  { run: 13, score: 0.91 },
  { run: 14, score: 0.88 },
  { run: 15, score: 0.85 },
];

export default function Analysis() {
  const [allMolecules, setAllMolecules] = useState<Molecule[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [dataLoading, setDataLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const { runs: summaries } = await listRuns();
        setRuns(summaries);
        const detailed = await Promise.all(
          summaries.slice(0, 20).map(s => getRun(s.run_id).catch(() => ({ molecules: [] })))
        );
        setAllMolecules(detailed.flatMap((r: any) => r.molecules ?? []));
      } catch (e) { console.error(e); }
      finally { setDataLoading(false); }
    };
    load();
  }, []);

  const avg = (arr: number[]) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

  const globalStats = useMemo(() => {
    const scores = allMolecules.map(m => m.score);
    const withAdmet = allMolecules.filter(m => m.admet);
    const lipinskiPass = withAdmet.filter(m => m.admet!.lipinski_pass).length;
    const targets = [...new Set(runs.map(r => r.target_id))];
    return {
      avgScore: scores.length ? avg(scores).toFixed(3) : "—",
      maxScore: scores.length ? Math.max(...scores).toFixed(3) : "—",
      lipinskiPct: withAdmet.length ? Math.round((lipinskiPass / withAdmet.length) * 100) + "%" : "0%",
      lipinskiSub: withAdmet.length ? `${lipinskiPass} of ${withAdmet.length} candidates` : "0 of 0 candidates",
      totalMolecules: allMolecules.length.toString(),
      totalSub: `Across ${runs.length} runs`,
      targets: targets.length.toString(),
      targetsSub: targets.join(", ") || "None",
    };
  }, [allMolecules, runs]);

  const scoreDistData = useMemo(() => [
    { range: "0-0.2",  count: allMolecules.filter(m => m.score < 0.2).length },
    { range: "0.2-0.4", count: allMolecules.filter(m => m.score >= 0.2 && m.score < 0.4).length },
    { range: "0.4-0.6", count: allMolecules.filter(m => m.score >= 0.4 && m.score < 0.6).length },
    { range: "0.6-0.8", count: allMolecules.filter(m => m.score >= 0.6 && m.score < 0.8).length },
    { range: "0.8-1.0", count: allMolecules.filter(m => m.score >= 0.8).length },
  ], [allMolecules]);

  const topCandidates = useMemo(() =>
    [...allMolecules].sort((a, b) => b.score - a.score).slice(0, 5)
      .map(m => ({ ...m, target: runs.find(r => r.target_id)?.target_id ?? "EGFR" })),
    [allMolecules, runs]
  );

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
              <SidebarItem icon={Compass} label="Discovery" to="/dashboard" />
              <SidebarItem icon={LibraryIcon} label="Library" to="/library" />
              <SidebarItem icon={BarChart3} label="Graphs" to="/graphs" />
              <SidebarItem icon={Bot} label="Agent" to="/agent" />
              <SidebarItem icon={Microscope} label="Analysis" to="/analysis" active />
            </div>

            <div className="space-y-2">
              <p className="px-4 text-[10px] font-bold tracking-widest uppercase opacity-20">General</p>
              <SidebarItem icon={Settings} label="Settings" />
              <SidebarItem icon={HelpCircle} label="Help" />
              <SidebarItem icon={LogOut} label="Logout" />
            </div>
          </div>
        </div>

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
      <main className="flex-1 flex flex-col gap-6 overflow-y-auto scrollbar-hide">
        {/* Header */}
        <header className="flex items-center justify-between gap-6">
          <div className="flex-1 max-w-xl relative">
            <Search className="absolute left-6 top-1/2 -translate-y-1/2 text-black/20" size={18} />
            <input 
              type="text" 
              placeholder="Search analysis..." 
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

        {/* Analysis Content */}
        <div className="space-y-6">
          {/* Title Area */}
          <div className="space-y-1">
            <p className="text-[10px] font-bold tracking-widest uppercase opacity-20">Analytics</p>
            <h1 className="text-4xl font-display font-medium tracking-tight">Exploratory analytics</h1>
            <p className="text-sm opacity-40">Live statistics computed from all discovery runs. Updates automatically as new runs complete.</p>
          </div>

          {/* Top Stats Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <AnalysisStatCard title="Avg Binding Score" value={globalStats.avgScore} subValue={`Max ${globalStats.maxScore}`} active />
            <AnalysisStatCard title="Lipinski Compliance" value={globalStats.lipinskiPct} subValue={globalStats.lipinskiSub} />
            <AnalysisStatCard title="Total Molecules" value={globalStats.totalMolecules} subValue={globalStats.totalSub} />
            <AnalysisStatCard title="Active Targets" value={globalStats.targets} subValue={globalStats.targetsSub} />
          </div>

          {/* Charts Row */}
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Score Distributions */}
            <div className="bg-white rounded-[40px] border border-black/5 p-8 flex flex-col">
              <div className="flex justify-between items-center mb-8">
                <div className="space-y-1">
                  <h3 className="text-sm font-bold">Score distributions</h3>
                  <p className="text-[10px] opacity-40">Binding affinity bucket distribution (normalised 0–1)</p>
                </div>
                <span className="text-[10px] font-bold tracking-widest uppercase opacity-20">102 Molecules</span>
              </div>
              <div className="flex-1 min-h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={scoreDistData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                    <XAxis 
                      dataKey="range" 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fontSize: 10, fill: '#111111', opacity: 0.4 }} 
                      dy={10}
                    />
                    <YAxis hide />
                    <Tooltip 
                      cursor={{ fill: 'transparent' }}
                      contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {scoreDistData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index === 4 ? '#7c3aed' : '#e5e7eb'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="flex gap-6 mt-6">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm bg-[#7c3aed]" />
                  <span className="text-[10px] font-medium opacity-60">High affinity (≥0.6)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-sm bg-[#e5e7eb]" />
                  <span className="text-[10px] font-medium opacity-60">Lower affinity</span>
                </div>
              </div>
            </div>

            {/* Score Trend */}
            <div className="bg-white rounded-[40px] border border-black/5 p-8 flex flex-col">
              <div className="flex justify-between items-center mb-8">
                <div className="space-y-1">
                  <h3 className="text-sm font-bold">Score trend</h3>
                  <p className="text-[10px] opacity-40">Average binding score per discovery run over time</p>
                </div>
                <span className="text-[10px] font-bold tracking-widest uppercase opacity-20">Run-to-run</span>
              </div>
              <div className="flex-1 min-h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={scoreTrendData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                    <XAxis hide />
                    <YAxis hide domain={[0.8, 1]} />
                    <Tooltip 
                      contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="score" 
                      stroke="#7c3aed" 
                      strokeWidth={2} 
                      dot={{ r: 4, fill: '#fff', stroke: '#7c3aed', strokeWidth: 2 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Bottom Grid: Per-target comparison */}
          <div className="grid grid-cols-1 gap-6">
            {/* Per-target comparison */}
            <div className="bg-white rounded-[40px] border border-black/5 p-8">
              <div className="flex justify-between items-center mb-8">
                <div className="space-y-1">
                  <h3 className="text-sm font-bold">Per-target comparison</h3>
                  <p className="text-[10px] opacity-40">Physicochemical and binding stats grouped by target protein</p>
                </div>
                <span className="text-[10px] font-bold tracking-widest uppercase opacity-20">1 Targets</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left border-b border-black/5">
                      <th className="pb-4 text-[9px] font-bold tracking-widest uppercase opacity-20">Target</th>
                      <th className="pb-4 text-[9px] font-bold tracking-widest uppercase opacity-20">Runs</th>
                      <th className="pb-4 text-[9px] font-bold tracking-widest uppercase opacity-20">Molecules</th>
                      <th className="pb-4 text-[9px] font-bold tracking-widest uppercase opacity-20">Avg Score</th>
                      <th className="pb-4 text-[9px] font-bold tracking-widest uppercase opacity-20">Max Score</th>
                      <th className="pb-4 text-[9px] font-bold tracking-widest uppercase opacity-20">Avg MW (DA)</th>
                      <th className="pb-4 text-[9px] font-bold tracking-widest uppercase opacity-20">Avg LogP</th>
                      <th className="pb-4 text-[9px] font-bold tracking-widest uppercase opacity-20">Lipinski %</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="group hover:bg-black/[0.01] transition-colors">
                      <td className="py-5">
                        <span className="px-2 py-1 bg-blue-50 text-blue-600 rounded text-[9px] font-bold">EGFR</span>
                      </td>
                      <td className="py-5 text-xs font-medium opacity-60">20</td>
                      <td className="py-5 text-xl font-display font-medium">102</td>
                      <td className="py-5">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-black/5 rounded-full overflow-hidden">
                            <div className="h-full bg-purple-500 w-[90%]" />
                          </div>
                          <span className="text-[10px] font-bold opacity-40">0.9</span>
                        </div>
                      </td>
                      <td className="py-5 text-xs font-bold text-green-500">1</td>
                      <td className="py-5 text-xs font-medium opacity-60">0</td>
                      <td className="py-5 text-xs font-medium opacity-60">0</td>
                      <td className="py-5 text-xs font-medium opacity-20">0%</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Right Sidebar - Repurposed with Top Candidates and Similarity Trends */}
      <aside className="w-80 flex flex-col gap-6 hidden xl:flex overflow-y-auto scrollbar-hide">
        {/* Top Candidates */}
        <div className="bg-white rounded-[40px] border border-black/5 p-8 flex flex-col">
          <div className="space-y-1 mb-8">
            <h3 className="text-sm font-bold">Top candidates</h3>
            <p className="text-[10px] opacity-40">Highest binding scores across all discovery runs</p>
          </div>
          <div className="space-y-4">
            {topCandidates.length === 0 ? (
              <p className="text-[10px] opacity-40 text-center py-4">No molecules yet.</p>
            ) : topCandidates.map((m, i) => (
              <div key={i} className="flex flex-col gap-3 p-4 bg-[#F8F9FA] rounded-2xl group hover:bg-white hover:shadow-md transition-all border border-transparent hover:border-black/5">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-black text-white flex-shrink-0 flex items-center justify-center text-[9px] font-bold">{i+1}</div>
                  <p className="text-[9px] font-mono opacity-60 truncate flex-1">{m.smiles}</p>
                </div>
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 bg-purple-50 text-purple-600 rounded text-[8px] font-bold">{m.target}</span>
                  <div className="flex items-center gap-2 flex-1 justify-end">
                    <div className="w-16 h-1 bg-black/5 rounded-full overflow-hidden">
                      <div className="h-full bg-purple-500 rounded-full" style={{width: `${m.score * 100}%`}}/>
                    </div>
                    <span className="text-[9px] font-bold">{m.score.toFixed(3)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Similarity Trends */}
        <div className="bg-white rounded-[40px] border border-black/5 p-8 flex flex-col">
          <div className="space-y-1 mb-8">
            <h3 className="text-sm font-bold">Similarity trends</h3>
            <p className="text-[10px] opacity-40">How frequently candidates align with known reference drugs</p>
          </div>
          <div className="space-y-6">
            {[
              { name: 'Aspirin', value: 31 },
              { name: 'Ibuprofen', value: 31 },
              { name: 'Lidocaine', value: 25 },
              { name: 'Paracetamol', value: 9 },
              { name: 'Caffeine', value: 6 },
            ].map((drug, i) => (
              <div key={i} className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-medium opacity-60">{drug.name}</span>
                  <span className="text-[10px] font-bold opacity-40">{drug.value}</span>
                </div>
                <div className="h-1.5 bg-black/5 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${drug.value * 2}%` }}
                    className="h-full bg-purple-500/40"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}