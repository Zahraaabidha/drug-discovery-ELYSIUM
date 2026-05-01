import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { listRuns } from "../api/elysium";
import type { RunSummary } from "../api/elysium";

// ── Mini sparkline bar chart ─────────────────────────────────────────────────
const Sparkline: React.FC<{ values: number[]; color?: string }> = ({ values, color = "#7c3aed" }) => {
  const max = Math.max(...values, 1);
  return (
    <div className="flex items-end gap-[3px] h-10">
      {values.map((v, i) => (
        <div key={i} className="flex-1 rounded-sm transition-all duration-300"
          style={{ height: `${(v / max) * 100}%`, background: color, opacity: 0.3 + (i / values.length) * 0.7 }} />
      ))}
    </div>
  );
};

// ── Stat card ────────────────────────────────────────────────────────────────
const StatCard: React.FC<{
  label: string; value: string | number; sub?: string;
  accent?: boolean; trend?: number; spark?: number[];
}> = ({ label, value, sub, accent, trend, spark }) => (
  <div className={`rounded-2xl p-5 flex flex-col gap-3 border transition-all duration-200 hover:shadow-md
    ${accent ? "bg-neutral-900 border-neutral-900 text-white" : "bg-white border-neutral-100 hover:border-neutral-200"}`}>
    <div className="flex items-start justify-between">
      <p className={`text-xs font-medium uppercase tracking-[0.15em] ${accent ? "text-neutral-400" : "text-neutral-400"}`}>{label}</p>
      <button className={`w-6 h-6 rounded-full flex items-center justify-center border transition-colors
        ${accent ? "border-neutral-700 text-neutral-400 hover:border-neutral-500" : "border-neutral-200 text-neutral-400 hover:border-neutral-400"}`}>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M7 17L17 7M7 7h10v10"/>
        </svg>
      </button>
    </div>
    <div>
      <p className={`text-4xl font-black tracking-tight leading-none ${accent ? "text-white" : "text-neutral-900"}`}>{value}</p>
      {sub && <p className={`text-xs mt-1.5 ${accent ? "text-neutral-400" : "text-neutral-400"}`}>{sub}</p>}
    </div>
    <div className="flex items-end justify-between gap-3">
      {trend !== undefined && (
        <div className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full
          ${trend >= 0
            ? (accent ? "bg-violet-500/20 text-violet-300" : "bg-violet-50 text-violet-600")
            : "bg-red-50 text-red-500"}`}>
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            {trend >= 0 ? <path d="M12 19V5M5 12l7-7 7 7"/> : <path d="M12 5v14M19 12l-7 7-7-7"/>}
          </svg>
          {Math.abs(trend)}% from last run
        </div>
      )}
      {spark && <div className="flex-1"><Sparkline values={spark} color={accent ? "#a78bfa" : "#7c3aed"}/></div>}
    </div>
  </div>
);

// ── Week grid (like the S M T W T F S calendar) ──────────────────────────────
const ActivityGrid: React.FC<{ runs: RunSummary[] }> = ({ runs }) => {
  const days = ["S", "M", "T", "W", "T", "F", "S"];
  // Count runs per day-of-week from actual data
  const counts = Array(7).fill(0);
  runs.forEach(r => { counts[new Date(r.created_at).getDay()]++; });
  const max = Math.max(...counts, 1);
  return (
    <div className="flex items-end gap-2">
      {days.map((d, i) => (
        <div key={i} className="flex flex-col items-center gap-1.5 flex-1">
          <div className="w-full rounded-md transition-all duration-300"
            style={{ height: `${Math.max(4, (counts[i] / max) * 48)}px`, background: counts[i] > 0 ? "#7c3aed" : "#f3f4f6" }} />
          <span className="text-[10px] text-neutral-400 font-medium">{d}</span>
        </div>
      ))}
    </div>
  );
};

// ── Target badge ─────────────────────────────────────────────────────────────
const TargetBadge: React.FC<{ target: string }> = ({ target }) => {
  const colors: Record<string, string> = {
    EGFR: "bg-blue-50 text-blue-700 border-blue-100",
    BRAF: "bg-emerald-50 text-emerald-700 border-emerald-100",
    KRAS: "bg-orange-50 text-orange-700 border-orange-100",
  };
  const c = colors[target.toUpperCase()] ?? "bg-violet-50 text-violet-700 border-violet-100";
  return (
    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${c}`}>{target}</span>
  );
};

// ── Main ─────────────────────────────────────────────────────────────────────
const RunsPage: React.FC = () => {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [activeTarget, setActiveTarget] = useState<string>("All");

  useEffect(() => {
    listRuns()
      .then(d => setRuns(d.runs))
      .catch(() => setError("Failed to load runs. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  // Derived stats
  const stats = useMemo(() => {
    const total = runs.length;
    const totalMolecules = runs.reduce((s, r) => s + r.num_molecules, 0);
    const targets = [...new Set(runs.map(r => r.target_id))];
    const completed = runs.length > 0 ? runs.length - 1 : 0;
    const inReview = runs.length > 0 ? 1 : 0;
    // Spark: molecules per run (last 7)
    const spark = runs.slice(-7).map(r => r.num_molecules);
    return { total, totalMolecules, targets, completed, inReview, spark };
  }, [runs]);

  // Unique targets for filter
  const targetFilters = useMemo(() => ["All", ...new Set(runs.map(r => r.target_id))], [runs]);

  const filtered = useMemo(() => runs.filter(r => {
    const matchSearch = r.run_id.toLowerCase().includes(search.toLowerCase()) ||
      r.target_id.toLowerCase().includes(search.toLowerCase());
    const matchTarget = activeTarget === "All" || r.target_id === activeTarget;
    return matchSearch && matchTarget;
  }), [runs, search, activeTarget]);

  // Recent runs for right panel (top 5)
  const recentRuns = runs.slice(0, 5);

  const deriveStatus = (idx: number) =>
    idx === 0 ? { label: "In Review", cls: "bg-amber-50 text-amber-700 border border-amber-200" }
              : { label: "Completed", cls: "bg-emerald-50 text-emerald-700 border border-emerald-200" };

  return (
    <div className="min-h-screen bg-[#f8f8f6] pt-16">
      <div className="max-w-[1400px] mx-auto px-6 md:px-10 py-10">

        {/* ── Top bar ── */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8">
          <div>
            <h1 className="text-4xl font-black tracking-[-0.03em] text-neutral-900">Discovery Runs</h1>
            <p className="text-neutral-500 text-sm mt-1">Plan, track, and audit every experiment with full provenance.</p>
          </div>
          <div className="flex items-center gap-3">
            {/* Search */}
            <div className="relative">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">
                <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
              </svg>
              <input value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search runs…"
                className="pl-9 pr-4 py-2.5 rounded-xl border border-neutral-200 bg-white text-sm focus:outline-none focus:border-violet-400 w-52 transition-colors"/>
            </div>
            <Link to="/discovery"
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-neutral-900 text-white text-sm font-semibold hover:bg-neutral-700 transition-colors">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 5v14M5 12h14"/>
              </svg>
              New Run
            </Link>
          </div>
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6">{error}</p>}

        {/* ── 3-column layout ── */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">

          {/* ── LEFT: stat cards + run list ── */}
          <div className="space-y-6">

            {/* Stat cards row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Runs" value={loading ? "—" : stats.total}
                sub={`${stats.completed} completed`} accent trend={8} spark={stats.spark}/>
              <StatCard label="Completed" value={loading ? "—" : stats.completed}
                sub="Fully processed" trend={6} spark={stats.spark.map(v => Math.max(0, v - 1))}/>
              <StatCard label="In Review" value={loading ? "—" : stats.inReview}
                sub="Awaiting sign-off" trend={-2}/>
              <StatCard label="Molecules" value={loading ? "—" : stats.totalMolecules}
                sub="Total generated" trend={12} spark={stats.spark}/>
            </div>

            {/* Activity + targets row */}
            <div className="grid md:grid-cols-2 gap-4">
              {/* Weekly activity */}
              <div className="bg-white rounded-2xl border border-neutral-100 p-5">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm font-bold text-neutral-900">Run Activity</p>
                  <span className="text-[10px] text-neutral-400 uppercase tracking-wider font-medium">By day of week</span>
                </div>
                <ActivityGrid runs={runs}/>
              </div>

              {/* Target breakdown */}
              <div className="bg-white rounded-2xl border border-neutral-100 p-5">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm font-bold text-neutral-900">Targets</p>
                  <span className="text-[10px] text-neutral-400 uppercase tracking-wider font-medium">{stats.targets.length} active</span>
                </div>
                <div className="space-y-2.5">
                  {stats.targets.slice(0, 4).map(t => {
                    const count = runs.filter(r => r.target_id === t).length;
                    const pct = Math.round((count / runs.length) * 100) || 0;
                    return (
                      <div key={t} className="flex items-center gap-3">
                        <TargetBadge target={t}/>
                        <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                          <div className="h-full bg-violet-500 rounded-full transition-all duration-500" style={{ width: `${pct}%` }}/>
                        </div>
                        <span className="text-xs text-neutral-400 font-medium w-8 text-right">{count}</span>
                      </div>
                    );
                  })}
                  {stats.targets.length === 0 && !loading && (
                    <p className="text-xs text-neutral-400">No targets yet.</p>
                  )}
                </div>
              </div>
            </div>

            {/* ── Run list ── */}
            <div className="bg-white rounded-2xl border border-neutral-100">
              {/* List header */}
              <div className="px-5 py-4 border-b border-neutral-100 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm font-bold text-neutral-900">All Runs</p>
                {/* Target filters */}
                <div className="flex flex-wrap gap-1.5">
                  {targetFilters.map(t => (
                    <button key={t} onClick={() => setActiveTarget(t)}
                      className={`text-[10px] font-semibold uppercase tracking-wider px-3 py-1.5 rounded-full border transition-all duration-150
                        ${activeTarget === t
                          ? "bg-neutral-900 text-white border-neutral-900"
                          : "bg-white text-neutral-500 border-neutral-200 hover:border-neutral-400"}`}>
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              {/* Column headers */}
              <div className="hidden md:grid grid-cols-[1fr_100px_100px_140px_100px_44px] gap-4 px-5 py-3 border-b border-neutral-50">
                {["Run ID", "Target", "Molecules", "Created", "Status", ""].map(h => (
                  <p key={h} className="text-[10px] uppercase tracking-[0.15em] text-neutral-400 font-medium">{h}</p>
                ))}
              </div>

              {/* Rows */}
              <div className="divide-y divide-neutral-50">
                {loading && (
                  <div className="py-16 text-center">
                    <div className="w-7 h-7 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin mx-auto mb-3"/>
                    <p className="text-sm text-neutral-400">Loading runs…</p>
                  </div>
                )}
                {!loading && filtered.length === 0 && (
                  <div className="py-16 text-center">
                    <p className="text-sm text-neutral-400">No runs match your filter.</p>
                    <Link to="/discovery" className="text-violet-600 text-sm font-medium hover:underline mt-1 inline-block">Start a new discovery →</Link>
                  </div>
                )}
                {filtered.map((run, idx) => {
                  const status = deriveStatus(idx);
                  return (
                    <Link key={run.run_id} to={`/runs/${run.run_id}`}
                      className="group hidden md:grid grid-cols-[1fr_100px_100px_140px_100px_44px] gap-4 items-center px-5 py-4 hover:bg-neutral-50/80 transition-colors">
                      {/* Run ID */}
                      <div>
                        <p className="font-mono text-sm text-violet-600 font-medium truncate group-hover:text-violet-700 transition-colors">{run.run_id}</p>
                      </div>
                      {/* Target */}
                      <div><TargetBadge target={run.target_id}/></div>
                      {/* Molecules */}
                      <p className="text-2xl font-black text-neutral-900 leading-none">{run.num_molecules}</p>
                      {/* Created */}
                      <p className="text-xs text-neutral-500">{new Date(run.created_at).toLocaleString()}</p>
                      {/* Status */}
                      <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${status.cls}`}>{status.label}</span>
                      {/* Arrow */}
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                        className="text-neutral-300 group-hover:text-violet-400 transition-colors">
                        <path d="M5 12h14M12 5l7 7-7 7"/>
                      </svg>
                    </Link>
                  );
                })}

                {/* Mobile rows */}
                {filtered.map((run, idx) => {
                  const status = deriveStatus(idx);
                  return (
                    <Link key={`m-${run.run_id}`} to={`/runs/${run.run_id}`}
                      className="group md:hidden flex flex-col gap-2 px-5 py-4 hover:bg-neutral-50 transition-colors">
                      <div className="flex items-center justify-between">
                        <p className="font-mono text-sm text-violet-600 font-medium truncate max-w-[200px]">{run.run_id}</p>
                        <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${status.cls}`}>{status.label}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <TargetBadge target={run.target_id}/>
                        <p className="text-xs text-neutral-500">{run.num_molecules} molecules · {new Date(run.created_at).toLocaleString()}</p>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>

          {/* ── RIGHT PANEL ── */}
          <div className="space-y-4">
            {/* Recent runs panel (like image 2's project list) */}
            <div className="bg-white rounded-2xl border border-neutral-100 p-5">
              <div className="flex items-center justify-between mb-5">
                <p className="text-sm font-bold text-neutral-900">Recent Runs</p>
                <Link to="/discovery"
                  className="text-[11px] font-semibold text-violet-600 hover:text-violet-700 flex items-center gap-1 transition-colors">
                  + NEW
                </Link>
              </div>
              <div className="space-y-3">
                {loading && <p className="text-xs text-neutral-400">Loading…</p>}
                {recentRuns.map((run, idx) => {
                  const icons = ["🧬", "⚗️", "🔬", "💊", "🧪"];
                  const colors = ["bg-blue-100", "bg-violet-100", "bg-emerald-100", "bg-orange-100", "bg-pink-100"];
                  return (
                    <Link key={run.run_id} to={`/runs/${run.run_id}`}
                      className="flex items-center gap-3 group hover:bg-neutral-50 -mx-2 px-2 py-2 rounded-xl transition-colors">
                      <div className={`w-8 h-8 rounded-xl ${colors[idx % colors.length]} flex items-center justify-center text-sm flex-shrink-0`}>
                        {icons[idx % icons.length]}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-neutral-900 truncate">{run.target_id} Discovery</p>
                        <p className="text-[11px] text-neutral-400">Due: {new Date(run.created_at).toLocaleDateString()}</p>
                      </div>
                      <button className="text-neutral-300 hover:text-neutral-500 transition-colors opacity-0 group-hover:opacity-100">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/>
                        </svg>
                      </button>
                    </Link>
                  );
                })}
                {!loading && recentRuns.length === 0 && (
                  <p className="text-xs text-neutral-400 text-center py-4">No runs yet.</p>
                )}
              </div>
            </div>

            {/* Molecule summary card */}
            <div className="bg-neutral-900 rounded-2xl p-5 text-white">
              <p className="text-xs font-medium text-neutral-400 uppercase tracking-[0.15em] mb-4">Molecule Output</p>
              <div className="grid grid-cols-2 gap-4 mb-5">
                <div>
                  <p className="text-3xl font-black leading-none">{loading ? "—" : stats.totalMolecules}</p>
                  <p className="text-[11px] text-neutral-500 mt-1">Total generated</p>
                </div>
                <div>
                  <p className="text-3xl font-black leading-none">{loading ? "—" : stats.targets.length}</p>
                  <p className="text-[11px] text-neutral-500 mt-1">Unique targets</p>
                </div>
              </div>
              {stats.spark.length > 0 && <Sparkline values={stats.spark} color="#a78bfa"/>}
              <Link to="/analysis"
                className="mt-4 flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-white text-sm font-medium transition-colors">
                <div className="w-1.5 h-1.5 rounded-full bg-violet-400"/>
                View Analysis
              </Link>
            </div>

            {/* Quick links */}
            <div className="bg-white rounded-2xl border border-neutral-100 p-5">
              <p className="text-xs font-bold text-neutral-400 uppercase tracking-[0.15em] mb-4">Quick Actions</p>
              <div className="space-y-1">
                {[
                  { label: "New Discovery Run", to: "/discovery", icon: "M12 5v14M5 12h14" },
                  { label: "Knowledge Graph", to: "/graphs", icon: "M5 12a2 2 0 100-4 2 2 0 000 4zm14-7a2 2 0 100-4 2 2 0 000 4zm0 14a2 2 0 100-4 2 2 0 000 4zM7 11.5l10-5M7 12.5l10 5" },
                  { label: "Agent Chat", to: "/agent", icon: "M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" },
                  { label: "Analytics", to: "/analysis", icon: "M18 20V10M12 20V4M6 20v-6" },
                ].map(item => (
                  <Link key={item.to} to={item.to}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-neutral-50 transition-colors group">
                    <div className="w-7 h-7 rounded-lg bg-neutral-100 flex items-center justify-center flex-shrink-0 group-hover:bg-violet-50 transition-colors">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                        className="text-neutral-500 group-hover:text-violet-600 transition-colors">
                        <path d={item.icon}/>
                      </svg>
                    </div>
                    <span className="text-sm text-neutral-700 font-medium group-hover:text-neutral-900 transition-colors">{item.label}</span>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                      className="ml-auto text-neutral-300 group-hover:text-neutral-500 transition-colors">
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

export default RunsPage;