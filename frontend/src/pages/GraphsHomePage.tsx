import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import GraphViewer from "../components/GraphViewer";
import { API_BASE_URL, API_KEY } from "../api/client";

const modes = [
  { key: "agent", label: "Agent view", desc: "Highlights high-priority molecules in green, deprioritized in grey" },
  { key: "similarity", label: "Similarity view", desc: "Violet edges show ChemBERTa semantic similarity to known drugs" },
  { key: "target", label: "Target view", desc: "Anchors layout around the target node for structural inspection" },
];

const NodeInspector: React.FC<{ node: { id: string; label?: string; type?: string; data?: any } | null }> = ({ node }) => {
  if (!node) return (
    <div className="flex flex-col items-center justify-center h-full text-center py-12 px-4">
      <div className="w-10 h-10 rounded-xl bg-neutral-100 flex items-center justify-center mb-3">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
        </svg>
      </div>
      <p className="text-sm font-semibold text-neutral-500">Select a node</p>
      <p className="text-xs text-neutral-400 mt-1 leading-relaxed">Click any node in the graph to inspect its properties and agent annotations</p>
    </div>
  );

  const typeColors: Record<string, string> = {
    targets: "bg-neutral-900 text-white",
    drugs: "bg-violet-100 text-violet-700",
    molecules: "bg-emerald-50 text-emerald-700",
  };
  const typeColor = typeColors[node.type ?? ""] ?? "bg-neutral-100 text-neutral-600";

  const typeExplanation: Record<string, string> = {
    targets: "Anchor target protein for this discovery run. All generated molecules connect back to this node via BINDS edges.",
    drugs: "Known reference compound linked via similarity edges. Used to contextualize generated scaffolds.",
    molecules: "Generated candidate molecule. Score reflects predicted DTI binding affinity normalized to [0, 1].",
  };

  return (
    <div className="space-y-4 p-1">
      {/* Node header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full ${typeColor}`}>
            {node.type ?? "node"}
          </span>
        </div>
        <p className="text-sm font-mono text-neutral-700 break-all leading-relaxed bg-neutral-50 rounded-xl px-3 py-2 border border-neutral-100">
          {node.label ?? node.id}
        </p>
      </div>

      {/* Explanation */}
      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-1.5">What this node is</p>
        <p className="text-xs text-neutral-600 leading-relaxed">
          {typeExplanation[node.type ?? ""] ?? "A node in the knowledge graph with contextual edges connecting it to other entities."}
        </p>
      </div>

      {/* Score if available */}
      {node.data?.score !== null && node.data?.score !== undefined && (
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-1.5">Binding score</p>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
              <div className="h-full bg-violet-500 rounded-full" style={{ width: `${Math.round(node.data.score * 100)}%` }}/>
            </div>
            <span className="text-sm font-bold text-violet-600">{Number(node.data.score).toFixed(3)}</span>
          </div>
        </div>
      )}

      {/* Node ID */}
      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-1.5">Node ID</p>
        <p className="text-[10px] font-mono text-neutral-400 break-all">{node.id}</p>
      </div>
    </div>
  );
};

const GraphsHomePage: React.FC = () => {
  const [search] = useSearchParams();
  const initialTarget = search.get("target") || "EGFR";
  const [targetDraft, setTargetDraft] = useState(initialTarget);
  const [activeTarget, setActiveTarget] = useState(initialTarget);
  const [mode, setMode] = useState(modes[0].key);
  const [depth, setDepth] = useState(2);
  const [maxNodes, setMaxNodes] = useState(35);
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSelectedNode(null);
    try {
      const url = `${API_BASE_URL}/graph-view/target/${encodeURIComponent(activeTarget)}?depth=${depth}`;
      const res = await fetch(url, { headers: { "X-API-KEY": API_KEY } });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setNodes(Array.isArray(data?.nodes) ? data.nodes : []);
      setEdges(Array.isArray(data?.edges) ? data.edges : []);
    } catch (err: any) {
      setError(err?.message || "Unable to load graph");
      setNodes([]); setEdges([]);
    } finally {
      setLoading(false);
    }
  }, [activeTarget, depth]);

  useEffect(() => { fetchGraph(); }, [fetchGraph]);

  const activeMode = useMemo(() => modes.find(m => m.key === mode), [mode]);

  const stats = useMemo(() => {
    const targets = nodes.filter((n: any) => (n.data ?? n).type === "targets").length;
    const drugs = nodes.filter((n: any) => (n.data ?? n).type === "drugs").length;
    const molecules = nodes.filter((n: any) => (n.data ?? n).type === "molecules").length;
    return { targets, drugs, molecules, edges: edges.length };
  }, [nodes, edges]);

  return (
    <div className="min-h-screen bg-[#f8f8f6] pt-16">
      <div className="max-w-[1400px] mx-auto px-6 md:px-10 py-10">

        {/* Header */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-neutral-400 mb-2 font-medium">Graph Explorer</p>
            <h1 className="text-4xl font-black tracking-[-0.03em] text-neutral-900">Knowledge graph</h1>
            <p className="text-sm text-neutral-500 mt-1 max-w-lg">
              Compare how agents traverse targets, generated molecules, and known drugs.
            </p>
          </div>
          <Link to="/discovery"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-neutral-900 text-white text-sm font-semibold hover:bg-neutral-700 transition-colors self-start">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14M5 12h14"/></svg>
            New Discovery
          </Link>
        </div>

        {/* Controls bar */}
        <div className="bg-white rounded-2xl border border-neutral-100 p-5 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            {/* Target input */}
            <div className="flex items-center gap-2">
              <label className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium">Target</label>
              <input value={targetDraft} onChange={e => setTargetDraft(e.target.value)}
                onKeyDown={e => e.key === "Enter" && setActiveTarget(targetDraft.trim() || "EGFR")}
                className="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm font-semibold w-28 focus:outline-none focus:border-violet-400 transition-colors"/>
            </div>

            {/* Depth */}
            <div className="flex items-center gap-3">
              <label className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium">Depth</label>
              <input type="range" min={1} max={5} value={depth} onChange={e => setDepth(Number(e.target.value))}
                className="w-24 accent-violet-600"/>
              <span className="text-sm font-bold text-neutral-700 w-4">{depth}</span>
            </div>

            {/* Max nodes */}
            <div className="flex items-center gap-3">
              <label className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium">Show</label>
              <input type="range" min={10} max={80} step={5} value={maxNodes} onChange={e => setMaxNodes(Number(e.target.value))}
                className="w-24 accent-violet-600"/>
              <span className="text-xs font-bold text-neutral-700 whitespace-nowrap">{maxNodes} nodes</span>
            </div>

            {/* Mode buttons */}
            <div className="flex gap-1.5 ml-2">
              {modes.map(m => (
                <button key={m.key} onClick={() => setMode(m.key)}
                  className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-150
                    ${mode === m.key ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"}`}>
                  {m.label}
                </button>
              ))}
            </div>

            {/* Refresh */}
            <button onClick={() => setActiveTarget(targetDraft.trim() || "EGFR")}
              className="ml-auto flex items-center gap-2 px-4 py-2 rounded-xl border border-neutral-200 text-sm font-medium text-neutral-700 hover:border-neutral-400 transition-colors">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                className={loading ? "animate-spin" : ""}>
                <path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 005.64 5.64L1 10M23 14l-4.64 4.36A9 9 0 013.51 15"/>
              </svg>
              {loading ? "Loading…" : "Refresh"}
            </button>
          </div>

          {/* Mode description */}
          {activeMode && (
            <p className="text-xs text-neutral-400 mt-3 pt-3 border-t border-neutral-50">{activeMode.desc}</p>
          )}
          {error && <p className="text-xs text-red-600 mt-2 bg-red-50 px-3 py-2 rounded-xl border border-red-100">{error}</p>}
        </div>

        {/* Graph stats */}
        {nodes.length > 0 && (
          <div className="grid grid-cols-4 gap-3 mb-6">
            {[
              { label: "Total nodes", value: nodes.length },
              { label: "Molecules", value: stats.molecules },
              { label: "Known drugs", value: stats.drugs },
              { label: "Edges", value: stats.edges },
            ].map(s => (
              <div key={s.label} className="bg-white rounded-xl border border-neutral-100 px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.15em] text-neutral-400 font-medium">{s.label}</p>
                <p className="text-2xl font-black text-neutral-900 mt-0.5">{s.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Main 2-col layout */}
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">

          {/* Graph canvas */}
          <div className="bg-white rounded-2xl border border-neutral-100 p-4">
            {loading ? (
              <div className="flex items-center justify-center h-[520px]">
                <div className="text-center">
                  <div className="w-8 h-8 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin mx-auto mb-3"/>
                  <p className="text-sm text-neutral-400">Building graph…</p>
                </div>
              </div>
            ) : (
              <GraphViewer nodes={nodes} edges={edges} mode={mode} maxNodes={maxNodes} onNodeSelect={setSelectedNode} height={520}/>
            )}
          </div>

          {/* Right panel */}
          <div className="space-y-4">
            {/* Node inspector */}
            <div className="bg-white rounded-2xl border border-neutral-100 p-5 min-h-[200px]">
              <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-4">Node Inspector</p>
              <NodeInspector node={selectedNode}/>
            </div>

            {/* Legend */}
            <div className="bg-white rounded-2xl border border-neutral-100 p-5">
              <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-3">Legend</p>
              <div className="space-y-2.5">
                {[
                  { color: "bg-neutral-900", label: "Target protein", desc: "Anchor node" },
                  { color: "bg-violet-600", label: "Known drug", desc: "Reference compound" },
                  { color: "bg-neutral-200", label: "Generated molecule", desc: "Candidate scaffold" },
                  { color: "bg-violet-200 border border-violet-300", label: "Selected node", desc: "Active selection" },
                ].map(item => (
                  <div key={item.label} className="flex items-center gap-3">
                    <div className={`w-4 h-4 rounded-full flex-shrink-0 ${item.color}`}/>
                    <div>
                      <p className="text-xs font-semibold text-neutral-700">{item.label}</p>
                      <p className="text-[10px] text-neutral-400">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-4 border-t border-neutral-100 space-y-2">
                <p className="text-[10px] uppercase tracking-[0.15em] text-neutral-400 font-medium">Edge types</p>
                {[
                  { color: "bg-violet-400", label: "BINDS", desc: "DTI binding relationship" },
                  { color: "bg-emerald-300", label: "SIMILAR_TO", desc: "Similarity edge (dashed)" },
                ].map(e => (
                  <div key={e.label} className="flex items-center gap-3">
                    <div className={`w-8 h-0.5 rounded-full flex-shrink-0 ${e.color}`}/>
                    <div>
                      <span className="text-[10px] font-bold text-neutral-600">{e.label}</span>
                      <span className="text-[10px] text-neutral-400 ml-1">· {e.desc}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick nav */}
            <div className="bg-white rounded-2xl border border-neutral-100 p-5">
              <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-3">Quick Actions</p>
              <div className="space-y-1">
                {[
                  { label: "View all runs", to: "/runs" },
                  { label: "Start discovery", to: "/discovery" },
                  { label: "Ask the agent", to: "/agent" },
                ].map(l => (
                  <Link key={l.to} to={l.to}
                    className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-neutral-50 transition-colors group">
                    <span className="text-sm text-neutral-700 font-medium group-hover:text-neutral-900">{l.label}</span>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                      className="text-neutral-300 group-hover:text-neutral-500 transition-colors">
                      <path d="M5 12h14M12 5l7 7-7 7"/>
                    </svg>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GraphsHomePage;