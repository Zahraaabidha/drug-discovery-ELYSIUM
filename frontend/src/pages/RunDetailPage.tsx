import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getRun } from "../api/elysium";
import type { DiscoverResponse, Molecule } from "../api/elysium";
import { API_BASE_URL } from "../api/client";
import {
  Activity, Compass, BarChart3, Bot, Microscope, Home,
  Settings, HelpCircle, LogOut, ArrowUpRight, ChevronRight
} from "lucide-react";

// ── Sidebar ───────────────────────────────────────────────────────────────
const SidebarItem = ({ icon: Icon, label, active = false, to }: { icon: any; label: string; active?: boolean; to?: string }) => (
  <Link to={to || "#"} className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${active ? "bg-black text-white" : "text-black/40 hover:bg-black/5 hover:text-black"}`}>
    <Icon size={20} strokeWidth={active ? 2 : 1.5} />
    <span className="text-sm font-medium">{label}</span>
  </Link>
);

// ── Score bar ─────────────────────────────────────────────────────────────
const ScoreBar: React.FC<{ score: number }> = ({ score }) => {
  const pct = Math.round(score * 100);
  const color = pct >= 85 ? "bg-green-500" : pct >= 65 ? "bg-purple-500" : "bg-amber-400";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-black/5 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-sm font-bold tabular-nums ${pct >= 85 ? "text-green-600" : "text-purple-600"}`}>
        {score.toFixed(3)}
      </span>
    </div>
  );
};

// ── Molecule card ─────────────────────────────────────────────────────────
const MolCard: React.FC<{ m: Molecule; rank: number; target: string }> = ({ m, rank, target }) => {
  const [expanded, setExpanded] = useState(false);
  const isTop = rank <= 3;

  return (
    <div className={`bg-white rounded-[32px] border transition-all duration-200 overflow-hidden
      ${isTop ? "border-purple-100 shadow-sm" : "border-black/5"}`}>
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0
              ${isTop ? "bg-black text-white" : "bg-black/5 text-black/40"}`}>
              {rank}
            </div>
            <p className="font-mono text-[11px] text-black/50 truncate">{m.smiles}</p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-[9px] font-bold text-purple-600 bg-purple-50 border border-purple-100 px-2.5 py-1 rounded-full">{target}</span>
            <button onClick={() => setExpanded(!expanded)}
              className="w-7 h-7 rounded-lg bg-black/5 hover:bg-black/10 flex items-center justify-center transition-colors">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                className={`transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}>
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </button>
          </div>
        </div>

        {/* Molecule image + score + similarity */}
        <div className="flex gap-5 items-start">
          {m.smiles && (
            <img
              src={`${API_BASE_URL}/molecule/image?smiles=${encodeURIComponent(m.smiles)}`}
              alt="molecule structure"
              className="w-24 h-24 rounded-2xl border border-black/5 bg-black/[0.02] object-contain flex-shrink-0"
              onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          )}
          <div className="flex-1 min-w-0 space-y-3">
            <div>
              <p className="text-[10px] font-bold tracking-widest uppercase opacity-40 mb-1.5">Binding score</p>
              <ScoreBar score={m.score} />
            </div>

            {/* Similar drug */}
            {m.similar_drug && (
              <div className="flex items-center gap-3">
                <p className="text-[10px] font-bold tracking-widest uppercase opacity-30 w-20 flex-shrink-0">Similar to</p>
                <span className="text-xs font-bold text-black/70">{m.similar_drug.name}</span>
                {m.similar_drug.similarity !== null && m.similar_drug.similarity !== undefined && (
                  <span className="text-[9px] font-bold text-purple-500 ml-auto">
                    Tanimoto {m.similar_drug.similarity.toFixed(2)}
                  </span>
                )}
              </div>
            )}
            {m.similar_drug_semantic && m.similar_drug_semantic.name !== m.similar_drug?.name && (
              <div className="flex items-center gap-3">
                <p className="text-[10px] font-bold tracking-widests uppercase opacity-30 w-20 flex-shrink-0">ChemBERTa</p>
                <span className="text-xs font-bold text-black/70">{m.similar_drug_semantic.name}</span>
                {m.similar_drug_semantic.semantic_similarity !== null && m.similar_drug_semantic.semantic_similarity !== undefined && (
                  <span className="text-[9px] font-bold text-indigo-500 ml-auto">
                    Cos {m.similar_drug_semantic.semantic_similarity.toFixed(2)}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Expanded ADMET */}
      {expanded && m.admet && (
        <div className="border-t border-black/5 px-6 py-4 bg-[#F8F9FA]">
          <p className="text-[10px] font-bold tracking-widests uppercase opacity-30 mb-3">ADMET Profile</p>
          <div className="flex flex-wrap gap-2 mb-3">
            {[
              { label: "MW", value: `${m.admet.molecular_weight.toFixed(1)} Da` },
              { label: "logP", value: m.admet.logp.toFixed(2) },
              { label: "HBD", value: m.admet.hbd },
              { label: "HBA", value: m.admet.hba },
              { label: "TPSA", value: `${m.admet.tpsa.toFixed(1)} Ų` },
              { label: "RotB", value: m.admet.rotatable_bonds },
            ].map(p => (
              <div key={p.label} className="flex flex-col items-center bg-white border border-black/5 rounded-xl px-3 py-2 min-w-[56px]">
                <span className="text-[8px] uppercase tracking-wider text-black/30 font-bold">{p.label}</span>
                <span className="text-xs font-bold text-black/70 mt-0.5">{p.value}</span>
              </div>
            ))}
            <div className={`flex flex-col items-center rounded-xl px-3 py-2 min-w-[56px] border
              ${m.admet.lipinski_pass ? "bg-green-50 border-green-100" : "bg-red-50 border-red-100"}`}>
              <span className="text-[8px] uppercase tracking-wider font-bold opacity-60">Lipinski</span>
              <span className={`text-xs font-bold mt-0.5 ${m.admet.lipinski_pass ? "text-green-600" : "text-red-500"}`}>
                {m.admet.lipinski_pass ? "Pass" : "Fail"}
              </span>
            </div>
          </div>
          {m.notes && <p className="text-[10px] text-black/40 leading-relaxed">{m.notes}</p>}
        </div>
      )}
    </div>
  );
};

// ── Main ──────────────────────────────────────────────────────────────────
const RunDetailPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<DiscoverResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    getRun(runId)
      .then(setRun)
      .catch(() => setError("Failed to load run."))
      .finally(() => setLoading(false));
  }, [runId]);

  const molecules: Molecule[] = run?.molecules ?? [];
  const topCandidates = molecules.slice(0, 3);
  const similar = molecules.filter(m => !!m.similar_drug && !topCandidates.includes(m));
  const exploratory = molecules.filter(m => !topCandidates.includes(m) && !similar.includes(m));

  const reasoningSteps = [
    "Planner decomposed request into generate → score → persist",
    "DeepPurpose attempted binding predictions; stub fallback available",
    "RDKit ADMET summary attached to each candidate",
    "Similarity + KG edges persisted for subsequent analyses",
  ];

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
        <div className="bg-black rounded-[32px] p-6 relative overflow-hidden">
          <div className="relative z-10 space-y-4">
            <div className="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-white rounded-sm" />
            </div>
            <p className="text-white text-sm font-medium leading-tight">Run complete</p>
            <p className="text-white/40 text-[10px]">{molecules.length} candidates generated</p>
            <button onClick={() => navigate("/discovery")}
              className="w-full py-3 bg-white text-black rounded-full text-[10px] font-bold tracking-widest uppercase hover:bg-white/90 transition-all">
              New Run
            </button>
          </div>
          <div className="absolute -bottom-4 -right-4 w-24 h-24 bg-purple-500/20 blur-2xl rounded-full" />
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col gap-6 min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="text-[10px] font-bold tracking-widests uppercase opacity-30 mb-1">Run summary</p>
            <h1 className="text-4xl font-display font-medium tracking-tight">
              Run {runId?.slice(0, 8)}
            </h1>
            {run && (
              <p className="text-sm opacity-40 mt-1">
                Target <span className="font-bold opacity-80">{run.target_id}</span> · {run.num_molecules} molecules
              </p>
            )}
          </div>
          <div className="flex gap-3">
            <button onClick={() => run?.target_id && navigate(`/graphs?target=${encodeURIComponent(run.target_id)}`)}
              className="px-5 py-2.5 rounded-full border border-black/10 text-sm font-medium hover:border-black/30 transition-colors">
              View graph
            </button>
            <Link to="/discovery" className="px-5 py-2.5 rounded-full bg-black text-white text-sm font-medium hover:bg-black/80 transition-colors">
              ← All runs
            </Link>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center space-y-3">
              <div className="w-8 h-8 border-2 border-purple-200 border-t-purple-500 rounded-full animate-spin mx-auto"/>
              <p className="text-sm opacity-40">Loading run…</p>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-100 rounded-2xl px-5 py-4">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {!loading && !error && (
          <>
            {/* Agent reasoning */}
            <div className="bg-white rounded-[32px] border border-black/5 p-7">
              <p className="text-[10px] font-bold tracking-widests uppercase opacity-30 mb-4">Agent Reasoning</p>
              <div className="space-y-3">
                {reasoningSteps.map((step, i) => (
                  <div key={i} className="flex items-start gap-4">
                    <div className="w-7 h-7 rounded-full bg-[#F8F9FA] border border-black/5 flex items-center justify-center text-[9px] font-bold opacity-40 flex-shrink-0 mt-0.5">
                      {i + 1}
                    </div>
                    <p className="text-xs text-black/60 leading-relaxed">{step}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Top candidates */}
            {topCandidates.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4 px-1">
                  <p className="text-[10px] font-bold tracking-widests uppercase opacity-30">Top Candidates</p>
                  <p className="text-[10px] opacity-30">Highest composite score</p>
                </div>
                <div className="space-y-3">
                  {topCandidates.map((m, i) => (
                    <MolCard key={i} m={m} rank={i + 1} target={run?.target_id ?? "—"} />
                  ))}
                </div>
              </div>
            )}

            {/* Similar to known drugs */}
            {similar.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4 px-1">
                  <p className="text-[10px] font-bold tracking-widests uppercase opacity-30">Similar to Known Drugs</p>
                  <p className="text-[10px] opacity-30">Repositioning hypotheses</p>
                </div>
                <div className="grid md:grid-cols-2 gap-3">
                  {similar.slice(0, 4).map((m, i) => (
                    <MolCard key={i} m={m} rank={topCandidates.length + i + 1} target={run?.target_id ?? "—"} />
                  ))}
                </div>
              </div>
            )}

            {/* Exploratory */}
            {exploratory.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-4 px-1">
                  <p className="text-[10px] font-bold tracking-widests uppercase opacity-30">Exploratory Set</p>
                  <p className="text-[10px] opacity-30">Diverse scaffolds</p>
                </div>
                <div className="space-y-3">
                  {exploratory.map((m, i) => (
                    <MolCard key={i} m={m} rank={topCandidates.length + similar.length + i + 1} target={run?.target_id ?? "—"} />
                  ))}
                </div>
              </div>
            )}

            {molecules.length === 0 && (
              <div className="bg-white rounded-[32px] border border-black/5 p-12 text-center">
                <p className="text-sm opacity-40">No molecules in this run.</p>
              </div>
            )}
          </>
        )}
      </main>

      {/* Right summary panel */}
      <aside className="w-72 flex-col gap-4 hidden xl:flex">
        {/* Run stats */}
        <div className="bg-white rounded-[40px] border border-black/5 p-7 space-y-5">
          <p className="text-[10px] font-bold tracking-widests uppercase opacity-30">Run Stats</p>
          {[
            { label: "Run ID", value: runId ? runId.slice(0, 16) + "…" : "—" },
            { label: "Target", value: run?.target_id ?? "—" },
            { label: "Molecules", value: String(molecules.length) },
            { label: "Top score", value: molecules.length ? Math.max(...molecules.map(m => m.score)).toFixed(3) : "—" },
            { label: "Avg score", value: molecules.length ? (molecules.reduce((a, b) => a + b.score, 0) / molecules.length).toFixed(3) : "—" },
            { label: "Lipinski pass", value: molecules.filter(m => m.admet?.lipinski_pass).length + " / " + molecules.filter(m => m.admet).length },
          ].map(s => (
            <div key={s.label} className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-widest opacity-30">{s.label}</span>
              <span className="text-xs font-bold">{s.value}</span>
            </div>
          ))}
        </div>

        {/* Score distribution mini */}
        <div className="bg-white rounded-[40px] border border-black/5 p-7">
          <p className="text-[10px] font-bold tracking-widests uppercase opacity-30 mb-4">Score Distribution</p>
          <div className="flex items-end gap-1.5 h-16">
            {[0, 0.2, 0.4, 0.6, 0.8].map((min, i) => {
              const count = molecules.filter(m => m.score >= min && m.score < min + 0.2).length;
              const maxCount = Math.max(...[0, 0.2, 0.4, 0.6, 0.8].map(x => molecules.filter(m => m.score >= x && m.score < x + 0.2).length), 1);
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div className={`w-full rounded-t-sm ${min >= 0.6 ? "bg-purple-500" : "bg-black/10"} transition-all`}
                    style={{ height: `${(count / maxCount) * 56}px`, minHeight: count > 0 ? "4px" : "0" }}/>
                  <span className="text-[8px] opacity-30">{Math.round(min * 10) / 10}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Quick actions */}
        <div className="bg-white rounded-[40px] border border-black/5 p-7">
          <p className="text-[10px] font-bold tracking-widests uppercase opacity-30 mb-4">Actions</p>
          <div className="space-y-2">
            {[
              { label: "View in graph", action: () => run?.target_id && navigate(`/graphs?target=${encodeURIComponent(run.target_id)}`) },
              { label: "Run analysis", action: () => navigate("/analysis") },
              { label: "New discovery", action: () => navigate("/dashboard") },
              { label: "Ask the agent", action: () => navigate("/agent") },
            ].map(a => (
              <button key={a.label} onClick={a.action}
                className="w-full flex items-center justify-between px-4 py-3 rounded-2xl border border-black/5 hover:bg-black/5 transition-all group text-sm font-medium text-left">
                {a.label}
                <ChevronRight size={14} className="opacity-20 group-hover:opacity-60 transition-opacity"/>
              </button>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
};

export default RunDetailPage;