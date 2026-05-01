import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { listRuns, getRun } from "../api/elysium";
import type { Molecule, RunSummary } from "../api/elysium";

// ── Types ─────────────────────────────────────────────────────────────────
interface RunWithMolecules extends RunSummary { molecules: Molecule[]; }

// ── Helpers ───────────────────────────────────────────────────────────────
const avg = (arr: number[]) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
const round2 = (n: number) => Math.round(n * 100) / 100;

// ── Inline bar chart (horizontal) ────────────────────────────────────────
const HBar: React.FC<{ value: number; max: number; color?: string; label?: string }> = ({
  value, max, color = "#7c3aed", label
}) => {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      {label && <span className="text-xs text-neutral-500 w-16 text-right flex-shrink-0">{label}</span>}
      <div className="flex-1 h-2 bg-neutral-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }}/>
      </div>
      <span className="text-xs font-bold text-neutral-700 w-10 flex-shrink-0">{round2(value)}</span>
    </div>
  );
};

// ── Score bucket bar chart (vertical, SVG) ────────────────────────────────
const ScoreHistogram: React.FC<{ molecules: Molecule[] }> = ({ molecules }) => {
  const buckets = [
    { label: "0–0.2", min: 0, max: 0.2 },
    { label: "0.2–0.4", min: 0.2, max: 0.4 },
    { label: "0.4–0.6", min: 0.4, max: 0.6 },
    { label: "0.6–0.8", min: 0.6, max: 0.8 },
    { label: "0.8–1.0", min: 0.8, max: 1.01 },
  ];

  const counts = buckets.map(b =>
    molecules.filter(m => m.score >= b.min && m.score < b.max).length
  );
  const maxCount = Math.max(...counts, 1);
  const W = 300; const H = 120; const barW = 42; const gap = 12;
  const totalW = buckets.length * (barW + gap) - gap;
  const offsetX = (W - totalW) / 2;

  return (
    <svg viewBox={`0 0 ${W} ${H + 30}`} className="w-full" style={{ maxHeight: 160 }}>
      {counts.map((c, i) => {
        const barH = maxCount > 0 ? (c / maxCount) * H : 0;
        const x = offsetX + i * (barW + gap);
        const isHigh = i >= 3;
        return (
          <g key={i}>
            <rect x={x} y={H - barH} width={barW} height={barH} rx="4"
              fill={isHigh ? "#7c3aed" : "#e5e7eb"} />
            {c > 0 && (
              <text x={x + barW / 2} y={H - barH - 5} textAnchor="middle"
                fontSize="9" fill="#6b7280" fontFamily="Inter, sans-serif" fontWeight="600">{c}</text>
            )}
            <text x={x + barW / 2} y={H + 16} textAnchor="middle"
              fontSize="8" fill="#9ca3af" fontFamily="Inter, sans-serif">{buckets[i].label}</text>
          </g>
        );
      })}
    </svg>
  );
};

// ── Score over time line chart ────────────────────────────────────────────
const ScoreTimeline: React.FC<{ runs: RunWithMolecules[] }> = ({ runs }) => {
  const sorted = [...runs].sort((a, b) =>
    new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
  const points = sorted.map(r => avg(r.molecules.map(m => m.score)));

  if (points.length < 2) return (
    <div className="flex items-center justify-center h-24 text-xs text-neutral-400">
      Need at least 2 runs to show trend
    </div>
  );

  const W = 320; const H = 90; const pad = 20;
  const minV = Math.min(...points) * 0.9;
  const maxV = Math.max(...points) * 1.05;
  const toX = (i: number) => pad + (i / (points.length - 1)) * (W - pad * 2);
  const toY = (v: number) => H - pad - ((v - minV) / (maxV - minV)) * (H - pad * 2);

  const pathD = points.map((v, i) => `${i === 0 ? "M" : "L"} ${toX(i)} ${toY(v)}`).join(" ");
  const areaD = pathD + ` L ${toX(points.length - 1)} ${H - pad} L ${toX(0)} ${H - pad} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 120 }}>
      <defs>
        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.15"/>
          <stop offset="100%" stopColor="#7c3aed" stopOpacity="0"/>
        </linearGradient>
      </defs>
      <path d={areaD} fill="url(#areaGrad)"/>
      <path d={pathD} fill="none" stroke="#7c3aed" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      {points.map((v, i) => (
        <circle key={i} cx={toX(i)} cy={toY(v)} r="3.5"
          fill="white" stroke="#7c3aed" strokeWidth="2"/>
      ))}
      {/* Labels */}
      {points.map((v, i) => (
        <text key={`l${i}`} x={toX(i)} y={toY(v) - 8} textAnchor="middle"
          fontSize="8" fill="#7c3aed" fontFamily="Inter, sans-serif" fontWeight="700">
          {v.toFixed(2)}
        </text>
      ))}
    </svg>
  );
};

// ── ADMET donut (Lipinski pass/fail) ──────────────────────────────────────
const LipinskiDonut: React.FC<{ pass: number; fail: number }> = ({ pass, fail }) => {
  const total = pass + fail;
  if (total === 0) return null;
  const pct = pass / total;
  const r = 36; const cx = 50; const cy = 50;
  const circ = 2 * Math.PI * r;
  const dash = pct * circ;
  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 100 100" className="w-20 h-20 flex-shrink-0" style={{ transform: "rotate(-90deg)" }}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f3f4f6" strokeWidth="10"/>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#7c3aed" strokeWidth="10"
          strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"/>
      </svg>
      <div>
        <p className="text-3xl font-black text-neutral-900 leading-none">{Math.round(pct * 100)}%</p>
        <p className="text-xs text-neutral-400 mt-1">Lipinski pass rate</p>
        <p className="text-[10px] text-neutral-300 mt-0.5">{pass} pass · {fail} fail</p>
      </div>
    </div>
  );
};

// ── Stat card ─────────────────────────────────────────────────────────────
const StatCard: React.FC<{ label: string; value: string; sub?: string; accent?: boolean }> = ({
  label, value, sub, accent
}) => (
  <div className={`rounded-2xl p-5 border ${accent ? "bg-neutral-900 border-neutral-900" : "bg-white border-neutral-100"}`}>
    <p className="text-[10px] uppercase tracking-[0.15em] text-neutral-400 font-medium mb-2">{label}</p>
    <p className={`text-4xl font-black tracking-tight leading-none ${accent ? "text-white" : "text-neutral-900"}`}>{value}</p>
    {sub && <p className={`text-xs mt-1.5 ${accent ? "text-neutral-500" : "text-neutral-400"}`}>{sub}</p>}
  </div>
);

// ── Loading skeleton ──────────────────────────────────────────────────────
const Skeleton: React.FC<{ className?: string }> = ({ className = "" }) => (
  <div className={`bg-neutral-100 rounded-xl animate-pulse ${className}`}/>
);

// ── Main ──────────────────────────────────────────────────────────────────
const AnalysisPage: React.FC = () => {
  const [runs, setRuns] = useState<RunWithMolecules[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const { runs: summaries } = await listRuns();
        // Fetch molecules for each run (cap at 20 runs to avoid hammering backend)
        const detailed = await Promise.all(
          summaries.slice(0, 20).map(async s => {
            try {
              const r = await getRun(s.run_id);
              return { ...s, molecules: r.molecules ?? [] };
            } catch {
              return { ...s, molecules: [] };
            }
          })
        );
        setRuns(detailed);
      } catch (e: any) {
        setError(e?.message || "Failed to load data");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // ── Computed stats ────────────────────────────────────────────────────
  const allMolecules = useMemo(() => runs.flatMap(r => r.molecules), [runs]);

  const globalStats = useMemo(() => {
    const scores = allMolecules.map(m => m.score);
    const lipinskiPass = allMolecules.filter(m => m.admet?.lipinski_pass).length;
    const lipinskiFail = allMolecules.filter(m => m.admet && !m.admet.lipinski_pass).length;
    const targets = [...new Set(runs.map(r => r.target_id))];
    return {
      avgScore: avg(scores),
      maxScore: scores.length ? Math.max(...scores) : 0,
      lipinskiPass, lipinskiFail,
      lipinskiPct: allMolecules.filter(m => m.admet).length > 0
        ? Math.round((lipinskiPass / allMolecules.filter(m => m.admet).length) * 100)
        : 0,
      totalMolecules: allMolecules.length,
      targets,
    };
  }, [runs, allMolecules]);

  // Per-target stats
  const targetStats = useMemo(() => {
    const targets = [...new Set(runs.map(r => r.target_id))];
    return targets.map(t => {
      const mols = runs.filter(r => r.target_id === t).flatMap(r => r.molecules);
      const withAdmet = mols.filter(m => m.admet);
      return {
        target: t,
        count: mols.length,
        avgScore: round2(avg(mols.map(m => m.score))),
        maxScore: mols.length ? round2(Math.max(...mols.map(m => m.score))) : 0,
        avgMW: round2(avg(withAdmet.map(m => m.admet!.molecular_weight))),
        avgLogP: round2(avg(withAdmet.map(m => m.admet!.logp))),
        avgTPSA: round2(avg(withAdmet.map(m => m.admet!.tpsa))),
        lipinskiPct: withAdmet.length
          ? Math.round((withAdmet.filter(m => m.admet!.lipinski_pass).length / withAdmet.length) * 100)
          : 0,
        runs: runs.filter(r => r.target_id === t).length,
      };
    });
  }, [runs]);

  // Top 5 candidates across all runs
  const topCandidates = useMemo(() =>
    [...allMolecules]
      .sort((a, b) => b.score - a.score)
      .slice(0, 5)
      .map(m => {
        const run = runs.find(r => r.molecules.includes(m));
        return { ...m, target: run?.target_id ?? "—" };
      }),
    [allMolecules, runs]
  );

  // ADMET distributions
  const admetMols = useMemo(() => allMolecules.filter(m => m.admet), [allMolecules]);
  const mwBuckets = useMemo(() => {
    const bs = [200, 300, 400, 500];
    return [
      { label: "<200", count: admetMols.filter(m => m.admet!.molecular_weight < 200).length },
      { label: "200–300", count: admetMols.filter(m => m.admet!.molecular_weight >= 200 && m.admet!.molecular_weight < 300).length },
      { label: "300–400", count: admetMols.filter(m => m.admet!.molecular_weight >= 300 && m.admet!.molecular_weight < 400).length },
      { label: "400–500", count: admetMols.filter(m => m.admet!.molecular_weight >= 400 && m.admet!.molecular_weight < 500).length },
      { label: ">500", count: admetMols.filter(m => m.admet!.molecular_weight >= 500).length },
    ];
  }, [admetMols]);

  if (error) return (
    <div className="min-h-screen bg-[#f8f8f6] pt-16 flex items-center justify-center">
      <div className="text-center">
        <p className="text-red-600 text-sm bg-red-50 border border-red-100 rounded-xl px-4 py-3">{error}</p>
        <Link to="/discovery" className="text-violet-600 text-sm font-medium mt-3 inline-block hover:underline">
          Start a discovery run →
        </Link>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#f8f8f6] pt-16">
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-10 space-y-8">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-neutral-400 mb-2 font-medium">Analytics</p>
            <h1 className="text-4xl font-black tracking-[-0.03em] text-neutral-900">Exploratory analytics</h1>
            <p className="text-sm text-neutral-500 mt-1 max-w-lg">
              Live statistics computed from all discovery runs. Updates automatically as new runs complete.
            </p>
          </div>
          <Link to="/discovery"
            className="hidden md:inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-neutral-900 text-white text-sm font-semibold hover:bg-neutral-700 transition-colors">
            New Run
          </Link>
        </div>

        {/* ── STAT CARDS ── */}
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array(4).fill(0).map((_, i) => <Skeleton key={i} className="h-28"/>)}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Avg Binding Score" value={globalStats.avgScore.toFixed(3)}
              sub={`Max ${globalStats.maxScore.toFixed(3)}`} accent/>
            <StatCard label="Lipinski Compliance"
              value={`${globalStats.lipinskiPct}%`}
              sub={`${globalStats.lipinskiPass} of ${globalStats.lipinskiPass + globalStats.lipinskiFail} candidates`}/>
            <StatCard label="Total Molecules" value={globalStats.totalMolecules.toString()}
              sub={`Across ${runs.length} runs`}/>
            <StatCard label="Active Targets" value={globalStats.targets.length.toString()}
              sub={globalStats.targets.join(", ")}/>
          </div>
        )}

        {/* ── ROW 1: Score distribution + Timeline ── */}
        <div className="grid md:grid-cols-2 gap-5">

          {/* Score histogram */}
          <div className="bg-white rounded-2xl border border-neutral-100 p-6">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-base font-bold text-neutral-900 tracking-tight">Score distributions</h2>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider font-medium">
                {allMolecules.length} molecules
              </span>
            </div>
            <p className="text-xs text-neutral-400 mb-5">Binding affinity bucket distribution (normalised 0–1)</p>
            {loading ? <Skeleton className="h-32"/> : (
              allMolecules.length > 0
                ? <ScoreHistogram molecules={allMolecules}/>
                : <p className="text-xs text-neutral-400 text-center py-10">No data yet</p>
            )}
            {!loading && allMolecules.length > 0 && (
              <div className="mt-3 flex items-center gap-4 pt-3 border-t border-neutral-50">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-sm bg-[#7c3aed]"/>
                  <span className="text-[10px] text-neutral-500">High affinity (≥0.6)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-sm bg-[#e5e7eb]"/>
                  <span className="text-[10px] text-neutral-500">Lower affinity</span>
                </div>
              </div>
            )}
          </div>

          {/* Score over time */}
          <div className="bg-white rounded-2xl border border-neutral-100 p-6">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-base font-bold text-neutral-900 tracking-tight">Score trend</h2>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider font-medium">
                Run-to-run
              </span>
            </div>
            <p className="text-xs text-neutral-400 mb-5">Average binding score per discovery run over time</p>
            {loading ? <Skeleton className="h-32"/> : <ScoreTimeline runs={runs}/>}
          </div>
        </div>

        {/* ── ROW 2: ADMET breakdown ── */}
        <div className="grid md:grid-cols-3 gap-5">

          {/* Lipinski donut */}
          <div className="bg-white rounded-2xl border border-neutral-100 p-6">
            <h2 className="text-base font-bold text-neutral-900 tracking-tight mb-1">Lipinski compliance</h2>
            <p className="text-xs text-neutral-400 mb-5">Rule-of-five pass rate across all candidates</p>
            {loading ? <Skeleton className="h-24"/> : (
              globalStats.lipinskiPass + globalStats.lipinskiFail > 0
                ? <LipinskiDonut pass={globalStats.lipinskiPass} fail={globalStats.lipinskiFail}/>
                : <p className="text-xs text-neutral-400 text-center py-8">No ADMET data yet</p>
            )}
          </div>

          {/* MW distribution */}
          <div className="bg-white rounded-2xl border border-neutral-100 p-6">
            <h2 className="text-base font-bold text-neutral-900 tracking-tight mb-1">MW distribution</h2>
            <p className="text-xs text-neutral-400 mb-5">Molecular weight spread across all runs (Da)</p>
            {loading ? <Skeleton className="h-24"/> : (
              admetMols.length > 0 ? (
                <div className="space-y-2.5">
                  {mwBuckets.map(b => (
                    <HBar key={b.label} label={b.label}
                      value={b.count} max={Math.max(...mwBuckets.map(x => x.count), 1)}
                      color="#7c3aed"/>
                  ))}
                </div>
              ) : <p className="text-xs text-neutral-400 text-center py-8">No ADMET data yet</p>
            )}
          </div>

          {/* ADMET averages */}
          <div className="bg-white rounded-2xl border border-neutral-100 p-6">
            <h2 className="text-base font-bold text-neutral-900 tracking-tight mb-1">ADMET summary</h2>
            <p className="text-xs text-neutral-400 mb-5">Mean property values across all candidates</p>
            {loading ? <Skeleton className="h-24"/> : (
              admetMols.length > 0 ? (
                <div className="space-y-3">
                  {[
                    { label: "Avg MW", value: round2(avg(admetMols.map(m => m.admet!.molecular_weight))), unit: "Da", max: 500 },
                    { label: "Avg logP", value: round2(avg(admetMols.map(m => m.admet!.logp))), unit: "", max: 5 },
                    { label: "Avg TPSA", value: round2(avg(admetMols.map(m => m.admet!.tpsa))), unit: "Ų", max: 140 },
                    { label: "Avg HBD", value: round2(avg(admetMols.map(m => m.admet!.hbd))), unit: "", max: 5 },
                    { label: "Avg HBA", value: round2(avg(admetMols.map(m => m.admet!.hba))), unit: "", max: 10 },
                  ].map(s => (
                    <div key={s.label} className="flex items-center gap-3">
                      <span className="text-[10px] text-neutral-400 w-16 flex-shrink-0 font-medium">{s.label}</span>
                      <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                        <div className="h-full bg-violet-400 rounded-full"
                          style={{ width: `${Math.min((s.value / s.max) * 100, 100)}%` }}/>
                      </div>
                      <span className="text-xs font-bold text-neutral-700 w-16 flex-shrink-0">
                        {s.value}{s.unit}
                      </span>
                    </div>
                  ))}
                </div>
              ) : <p className="text-xs text-neutral-400 text-center py-8">No ADMET data yet</p>
            )}
          </div>
        </div>

        {/* ── TARGET COMPARISON TABLE ── */}
        <div className="bg-white rounded-2xl border border-neutral-100 overflow-hidden">
          <div className="px-6 py-5 border-b border-neutral-50 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-neutral-900 tracking-tight">Per-target comparison</h2>
              <p className="text-xs text-neutral-400 mt-0.5">ADMET and binding stats grouped by target protein</p>
            </div>
            <span className="text-[10px] text-neutral-400 uppercase tracking-wider font-medium">
              {targetStats.length} targets
            </span>
          </div>
          {loading ? (
            <div className="p-6 space-y-3">
              {Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-10"/>)}
            </div>
          ) : targetStats.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-50">
                    {["Target", "Runs", "Molecules", "Avg Score", "Max Score", "Avg MW (Da)", "Avg logP", "Avg TPSA (Ų)", "Lipinski %"].map(h => (
                      <th key={h} className="text-left px-5 py-3 text-[10px] uppercase tracking-[0.15em] text-neutral-400 font-medium whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-50">
                  {targetStats.map((t, i) => (
                    <tr key={t.target} className="hover:bg-neutral-50/50 transition-colors group">
                      <td className="px-5 py-4">
                        <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border
                          ${i === 0 ? "bg-blue-50 text-blue-700 border-blue-100"
                          : i === 1 ? "bg-emerald-50 text-emerald-700 border-emerald-100"
                          : "bg-orange-50 text-orange-700 border-orange-100"}`}>
                          {t.target}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-neutral-600 font-medium">{t.runs}</td>
                      <td className="px-5 py-4 text-2xl font-black text-neutral-900 leading-none">{t.count}</td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                            <div className="h-full bg-violet-500 rounded-full"
                              style={{ width: `${t.avgScore * 100}%` }}/>
                          </div>
                          <span className="text-xs font-bold text-violet-600">{t.avgScore}</span>
                        </div>
                      </td>
                      <td className="px-5 py-4 text-xs font-bold text-emerald-600">{t.maxScore}</td>
                      <td className="px-5 py-4 text-xs text-neutral-600">{t.avgMW}</td>
                      <td className="px-5 py-4 text-xs text-neutral-600">{t.avgLogP}</td>
                      <td className="px-5 py-4 text-xs text-neutral-600">{t.avgTPSA}</td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-12 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${t.lipinskiPct >= 85 ? "bg-emerald-500" : "bg-amber-400"}`}
                              style={{ width: `${t.lipinskiPct}%` }}/>
                          </div>
                          <span className={`text-xs font-bold ${t.lipinskiPct >= 85 ? "text-emerald-600" : "text-amber-500"}`}>
                            {t.lipinskiPct}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-12 text-center">
              <p className="text-sm text-neutral-400">No run data yet.</p>
              <Link to="/discovery" className="text-violet-600 text-sm font-medium hover:underline mt-1 inline-block">
                Start a discovery run →
              </Link>
            </div>
          )}
        </div>

        {/* ── TOP CANDIDATES LEADERBOARD ── */}
        <div className="bg-white rounded-2xl border border-neutral-100 overflow-hidden">
          <div className="px-6 py-5 border-b border-neutral-50">
            <h2 className="text-base font-bold text-neutral-900 tracking-tight">Top candidates</h2>
            <p className="text-xs text-neutral-400 mt-0.5">Highest binding scores across all discovery runs</p>
          </div>
          {loading ? (
            <div className="p-6 space-y-3">
              {Array(5).fill(0).map((_, i) => <Skeleton key={i} className="h-12"/>)}
            </div>
          ) : topCandidates.length > 0 ? (
            <div className="divide-y divide-neutral-50">
              {topCandidates.map((m, i) => (
                <div key={i} className="px-6 py-4 flex items-center gap-5 hover:bg-neutral-50/50 transition-colors">
                  <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-black flex-shrink-0
                    ${i === 0 ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-500"}`}>
                    {i + 1}
                  </span>
                  <p className="font-mono text-xs text-neutral-500 flex-1 truncate min-w-0">{m.smiles}</p>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-violet-600 bg-violet-50 border border-violet-100 px-2 py-0.5 rounded-full flex-shrink-0">
                    {m.target}
                  </span>
                  <div className="flex items-center gap-2 flex-shrink-0 w-36">
                    <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${m.score >= 0.85 ? "bg-emerald-500" : "bg-violet-500"}`}
                        style={{ width: `${m.score * 100}%` }}/>
                    </div>
                    <span className={`text-xs font-black ${m.score >= 0.85 ? "text-emerald-600" : "text-violet-600"}`}>
                      {m.score.toFixed(3)}
                    </span>
                  </div>
                  {m.admet && (
                    <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border flex-shrink-0
                      ${m.admet.lipinski_pass ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "bg-red-50 text-red-500 border-red-100"}`}>
                      {m.admet.lipinski_pass ? "Lipinski ✓" : "Lipinski ✗"}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="px-6 py-12 text-center">
              <p className="text-sm text-neutral-400">No molecules yet.</p>
            </div>
          )}
        </div>

        {/* ── SIMILARITY SECTION ── */}
        <div className="bg-white rounded-2xl border border-neutral-100 p-6">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-base font-bold text-neutral-900 tracking-tight">Similarity trends</h2>
          </div>
          <p className="text-xs text-neutral-400 mb-6">How frequently candidates align with known reference drugs (fingerprint similarity)</p>
          {loading ? <Skeleton className="h-24"/> : (
            (() => {
              const withSim = allMolecules.filter(m => m.similar_drug?.similarity !== null);
              if (!withSim.length) return <p className="text-xs text-neutral-400 text-center py-8">No similarity data yet</p>;
              const drugCounts: Record<string, number> = {};
              withSim.forEach(m => {
                const name = m.similar_drug!.name;
                drugCounts[name] = (drugCounts[name] ?? 0) + 1;
              });
              const sorted = Object.entries(drugCounts).sort((a, b) => b[1] - a[1]).slice(0, 8);
              const maxC = sorted[0]?.[1] ?? 1;
              return (
                <div className="grid md:grid-cols-2 gap-3">
                  {sorted.map(([drug, count]) => (
                    <div key={drug} className="flex items-center gap-3">
                      <span className="text-xs font-semibold text-neutral-700 w-28 flex-shrink-0 truncate">{drug}</span>
                      <div className="flex-1 h-2 bg-neutral-100 rounded-full overflow-hidden">
                        <div className="h-full bg-violet-300 rounded-full transition-all duration-700"
                          style={{ width: `${(count / maxC) * 100}%` }}/>
                      </div>
                      <span className="text-xs font-bold text-neutral-500 w-6 flex-shrink-0 text-right">{count}</span>
                    </div>
                  ))}
                </div>
              );
            })()
          )}
        </div>

      </div>
    </div>
  );
};

export default AnalysisPage;