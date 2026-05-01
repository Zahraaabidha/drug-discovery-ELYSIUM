import { useState, useEffect, useCallback } from "react";
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
  RefreshCw,
  ChevronRight,
  Info,
  Maximize2,
  Play
} from "lucide-react";
import { Link } from "react-router-dom";
import GraphViewer from "../components/GraphViewer";
import { API_BASE_URL } from "../api/client";
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
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

const GraphStat = ({ label, value, subValue, trend }: { label: string, value: string, subValue?: string, trend?: string }) => (
  <div className="space-y-1">
    <p className="text-[10px] font-bold tracking-widest uppercase opacity-40">{label}</p>
    <div className="flex items-baseline gap-2">
      <span className="text-xl font-display font-medium">{value}</span>
      {trend && (
        <span className="text-[10px] font-bold px-1.5 py-0.5 bg-black text-white rounded-md">{trend}</span>
      )}
    </div>
    {subValue && <p className="text-[10px] opacity-40">{subValue}</p>}
  </div>
);

const trendlineData = Array.from({ length: 20 }, (_, i) => ({
  x: i,
  y1: 20 + Math.sin(i * 0.5) * 10 + i * 2,
  y2: 15 + Math.cos(i * 0.5) * 8 + i * 1.5,
}));

const concentrationData = [
  { name: 'A', value: 40 },
  { name: 'B', value: 30 },
  { name: 'C', value: 20 },
  { name: 'D', value: 10 },
  { name: 'E', value: 5 },
];

const marketData = [
  { name: '2024', actual: 400, market: 240 },
  { name: '2025', actual: 300, market: 139 },
  { name: '2026', actual: 200, market: 980 },
];

export default function Graphs() {
  const [viewMode, setViewMode] = useState('agent');
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [target, setTarget] = useState("EGFR");
  const [depth, setDepth] = useState(2);
  const [maxNodes, setMaxNodes] = useState(35);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [denseMode, setDenseMode] = useState(false);

  const fetchGraph = useCallback(async () => {
    setLoadingGraph(true);
    setSelectedNode(null);
    try {
      const apiKey = import.meta.env.VITE_API_KEY || "changeme";
      const res = await fetch(`${API_BASE_URL}/graph-view/target/${encodeURIComponent(target)}?depth=${depth}`, {
        headers: { "X-API-KEY": apiKey }
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setNodes(Array.isArray(data?.nodes) ? data.nodes : []);
      setEdges(Array.isArray(data?.edges) ? data.edges : []);
    } catch (e) { console.error(e); }
    finally { setLoadingGraph(false); }
  }, [target, depth]);

  useEffect(() => { fetchGraph(); }, [fetchGraph]);

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
              <SidebarItem icon={BarChart3} label="Graphs" to="/graphs" active />
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

        {/* Graph Content */}
        <div className="flex-1 flex flex-col gap-6 overflow-y-auto scrollbar-hide">
          {/* Title & Actions */}
          <div className="flex justify-between items-end">
            <div className="space-y-1">
              <p className="text-[10px] font-bold tracking-[0.2em] uppercase opacity-20">Graph Explorer</p>
              <h1 className="text-4xl font-display font-medium tracking-tight">Knowledge graph</h1>
              <p className="text-sm opacity-40">Compare how agents traverse targets, generated molecules, and known drugs.</p>
            </div>
            <button className="px-6 py-3 bg-black text-white rounded-full text-[10px] font-bold tracking-widest uppercase flex items-center gap-2 hover:bg-black/80 transition-all">
              <Plus size={14} />
              New Discovery
            </button>
          </div>

          {/* Graph Explorer Controls (Inspired by Image 2) - MOVED TO START */}
          <div className="bg-white rounded-[40px] border border-black/5 p-8 space-y-6">
            <div className="flex flex-wrap items-center gap-8">
              <div className="flex items-center gap-4">
                <span className="text-[10px] font-bold tracking-widest uppercase opacity-20">Target</span>
                <input 
                  type="text" 
                  value={target}
                  onChange={e => setTarget(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && fetchGraph()}
                  className="bg-[#F8F9FA] border border-black/5 rounded-xl py-2 px-4 text-xs font-bold w-32 focus:outline-none"
                />
              </div>

              <div className="flex items-center gap-4">
                <span className="text-[10px] font-bold tracking-widests uppercase opacity-20">Depth</span>
                <div className="flex items-center gap-3">
                  <input type="range" min={1} max={5} value={depth}
                    onChange={e => setDepth(Number(e.target.value))}
                    className="w-32 accent-purple-500"/>
                  <span className="text-xs font-bold">{depth}</span>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <span className="text-[10px] font-bold tracking-widest uppercase opacity-20">Show</span>
                <div className="flex items-center gap-3">
                  <input type="range" min={10} max={80} step={5} value={maxNodes}
                    onChange={e => setMaxNodes(Number(e.target.value))}
                    className="w-32 accent-purple-500"/>
                  <span className="text-xs font-bold">{maxNodes} nodes</span>
                </div>
              </div>

              <div className="flex bg-black/5 p-1 rounded-xl">
                {['Agent view', 'Similarity view', 'Target view'].map((mode) => (
                  <button 
                    key={mode}
                    onClick={() => setViewMode(mode.toLowerCase().replace(' view','').replace(' ',''))}
                    className={`px-4 py-2 rounded-lg text-[10px] font-bold tracking-widest uppercase transition-all ${viewMode === mode.toLowerCase().replace(' view','').trim() ? 'bg-black text-white shadow-lg' : 'opacity-40 hover:opacity-100'}`}
                  >
                    {mode}
                  </button>
                ))}
              </div>

              <div className="ml-auto flex items-center gap-3">
                <button
                  onClick={() => setDenseMode(!denseMode)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-[10px] font-bold tracking-widest uppercase transition-all border ${denseMode ? "bg-black text-white border-black" : "border-black/10 text-black/50 hover:border-black/30 hover:text-black"}`}>
                  {denseMode ? "⬛ Dense ON" : "⬜ Dense OFF"}
                </button>
                <button
                  onClick={fetchGraph}
                  className="flex items-center gap-2 text-[10px] font-bold tracking-widest uppercase opacity-40 hover:opacity-100 transition-opacity">
                  <RefreshCw size={14} className={loadingGraph ? "animate-spin" : ""}/>
                  {loadingGraph ? "Loading…" : "Refresh"}
                </button>
              </div>
            </div>
            
            <p className="text-[10px] opacity-40">Highlights high-priority molecules in green, deprioritized in grey</p>
          </div>

          {/* Real Graph Visualization */}
          <div className="bg-white rounded-[40px] border border-black/5 overflow-hidden flex-1 min-h-[600px]">
            {loadingGraph ? (
              <div className="flex items-center justify-center h-[600px]">
                <div className="text-center space-y-3">
                  <div className="w-8 h-8 border-2 border-purple-200 border-t-purple-500 rounded-full animate-spin mx-auto"/>
                  <p className="text-xs font-medium opacity-40">Building graph…</p>
                </div>
              </div>
            ) : (
              <GraphViewer
                nodes={nodes}
                edges={edges}
                mode={viewMode}
                maxNodes={denseMode ? 999 : maxNodes}
                denseMode={denseMode}
                onNodeSelect={setSelectedNode}
                height={600}
              />
            )}
          </div>
        </div>
      </main>


      {/* Right Sidebar (Inspired by Image 2 & 3) */}
      <aside className="w-80 flex flex-col gap-6 hidden xl:flex overflow-y-auto scrollbar-hide">
        {/* Legend - MOVED TO TOP & SMALLER */}
        <div className="bg-white rounded-[40px] border border-black/5 p-6 space-y-4">
          <p className="text-[10px] font-bold tracking-widest uppercase opacity-20">Legend</p>
          <div className="space-y-3">
            {[
              { label: 'Target protein', sub: 'Anchor node', color: 'bg-black' },
              { label: 'Known drug', sub: 'Reference compound', color: 'bg-purple-500' },
              { label: 'Generated molecule', sub: 'Candidate scaffold', color: 'bg-black/10' },
              { label: 'Selected node', sub: 'Active selection', color: 'bg-purple-200' },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
                <div>
                  <p className="text-[11px] font-bold">{item.label}</p>
                  <p className="text-[9px] opacity-40">{item.sub}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Node Inspector */}
        <div className="bg-white rounded-[40px] border border-black/5 p-6 space-y-4">
          <p className="text-[10px] font-bold tracking-widest uppercase opacity-20">Node Inspector</p>
          {!selectedNode ? (
            <p className="text-[11px] opacity-40 text-center py-6">Click any node to inspect</p>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                  selectedNode.type === "targets" ? "bg-black text-white" :
                  selectedNode.type === "drugs" ? "bg-purple-50 text-purple-600" :
                  "bg-green-50 text-green-600"}`}>
                  {selectedNode.type ?? "node"}
                </span>
              </div>
              <div className="bg-[#F8F9FA] rounded-2xl p-4 font-mono text-[10px] break-all opacity-60">
                {selectedNode.label ?? selectedNode.id}
              </div>
              {selectedNode.data?.score !== null && selectedNode.data?.score !== undefined && (
                <div className="space-y-1">
                  <p className="text-[10px] font-bold tracking-widest uppercase opacity-20">Binding score</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-black/5 rounded-full overflow-hidden">
                      <div className="h-full bg-purple-500 rounded-full" style={{width: `${selectedNode.data.score * 100}%`}}/>
                    </div>
                    <span className="text-[10px] font-bold text-purple-600">{Number(selectedNode.data.score).toFixed(3)}</span>
                  </div>
                </div>
              )}
              <div className="space-y-1">
                <p className="text-[10px] font-bold tracking-widest uppercase opacity-20">Description</p>
                <p className="text-[11px] opacity-60 leading-relaxed">
                  {selectedNode.type === "targets" ? "Anchor target protein for this discovery run." :
                   selectedNode.type === "drugs" ? "Known reference compound linked via similarity edges." :
                   "Generated candidate molecule. Score reflects predicted DTI binding affinity."}
                </p>
              </div>
            </>
          )}
        </div>

        {/* Stats Boxes (Inspired by Image 3) */}
        <div className="grid grid-cols-1 gap-4">
          <div className="bg-white rounded-[32px] border border-black/5 p-6 flex flex-col justify-between min-h-[120px]">
            <p className="text-[10px] font-bold tracking-widest uppercase opacity-20">Total Nodes</p>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-display font-medium">564</span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 bg-black text-white rounded-md">8%</span>
            </div>
          </div>

          <div className="bg-black rounded-[32px] p-6 flex flex-col justify-between min-h-[120px] relative overflow-hidden">
            <div className="flex justify-between items-start relative z-10">
              <p className="text-[10px] font-bold tracking-widest uppercase text-white/40">Molecules</p>
              <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                <Play size={14} className="text-white fill-white" />
              </div>
            </div>
            <div className="relative z-10">
              <p className="text-2xl font-display font-medium text-white">561</p>
              <p className="text-[9px] text-white/20">Generated candidates</p>
            </div>
          </div>

          <div className="bg-white rounded-[32px] border border-black/5 p-6 flex flex-col justify-between min-h-[120px]">
            <div className="flex justify-between items-start">
              <p className="text-[10px] font-bold tracking-widest uppercase opacity-20">Stability</p>
              <div className="w-8 h-8 rounded-full bg-black/5 flex items-center justify-center">
                <Activity size={14} className="opacity-40" />
              </div>
            </div>
            <p className="text-2xl font-display font-medium">84%</p>
          </div>
        </div>
      </aside>
    </div>
  );
}