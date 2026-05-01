import React, { useMemo, useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { discoverMolecules } from "../api/elysium";
import type { Molecule } from "../api/elysium";
import MoleculeResultRow from "../components/MoleculeResultRow";
import { API_BASE_URL } from "../api/client";

const planSteps = [
  "Sample candidate scaffolds from curated libraries",
  "Score binding with DeepPurpose / fallback stub",
  "Apply RDKit ADMET & Lipinski filters",
  "Attach nearest-known drug context + KG edges",
];

// ── Animated pipeline step ───────────────────────────────────────────────────
const PipelineStep: React.FC<{
  num: number; text: string;
  state: "idle" | "active" | "done";
}> = ({ num, text, state }) => (
  <div className={`flex items-start gap-3 transition-all duration-300 ${state === "idle" ? "opacity-30" : "opacity-100"}`}>
    <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 transition-all duration-300 text-xs font-bold
      ${state === "done" ? "bg-emerald-100 text-emerald-600 border border-emerald-200"
        : state === "active" ? "bg-violet-100 text-violet-600 border border-violet-300 animate-pulse"
        : "bg-neutral-100 text-neutral-400 border border-neutral-200"}`}>
      {state === "done"
        ? <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
        : num}
    </div>
    <p className={`text-sm pt-0.5 ${state === "done" ? "text-neutral-500 line-through" : state === "active" ? "text-violet-700 font-medium" : "text-neutral-400"}`}>
      {text}
    </p>
  </div>
);

// ── Score bar ────────────────────────────────────────────────────────────────
const ScoreBar: React.FC<{ score: number }> = ({ score }) => {
  const pct = Math.round(score * 100);
  const color = pct >= 85 ? "bg-emerald-500" : pct >= 65 ? "bg-violet-500" : "bg-amber-400";
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-bold ${pct >= 85 ? "text-emerald-600" : pct >= 65 ? "text-violet-600" : "text-amber-500"}`}>
        {score.toFixed(3)}
      </span>
    </div>
  );
};

// ── ADMET pill ───────────────────────────────────────────────────────────────
const ADMETPill: React.FC<{ label: string; value: string | number; pass?: boolean }> = ({ label, value, pass }) => (
  <div className="flex flex-col items-center bg-neutral-50 border border-neutral-100 rounded-xl px-3 py-2 min-w-[60px]">
    <span className="text-[9px] uppercase tracking-wider text-neutral-400 font-medium">{label}</span>
    <span className={`text-sm font-bold mt-0.5 ${pass === true ? "text-emerald-600" : pass === false ? "text-red-500" : "text-neutral-800"}`}>
      {value}
    </span>
  </div>
);

// ── Molecule card ─────────────────────────────────────────────────────────────
const MoleculeCard: React.FC<{ molecule: Molecule; rank: number }> = ({ molecule: m, rank }) => {
  const [expanded, setExpanded] = useState(false);
  const isTop = rank <= 3;

  return (
    <div className={`rounded-2xl border transition-all duration-200 overflow-hidden
      ${isTop ? "border-violet-100 bg-white shadow-sm shadow-violet-50" : "border-neutral-100 bg-white"}`}>
      <div className="p-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {isTop && (
              <span className="text-[9px] font-bold uppercase tracking-wider bg-violet-600 text-white px-2 py-0.5 rounded-full flex-shrink-0">
                #{rank}
              </span>
            )}
            <p className="font-mono text-xs text-neutral-500 truncate">{m.smiles}</p>
          </div>
          <button onClick={() => setExpanded(!expanded)}
            className="flex-shrink-0 w-6 h-6 rounded-lg bg-neutral-100 hover:bg-neutral-200 flex items-center justify-center transition-colors">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
              className={`transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}>
              <path d="M6 9l6 6 6-6"/>
            </svg>
          </button>
        </div>

        {/* Molecule image + score */}
        <div className="flex gap-4 items-start">
          {m.smiles && (
            <img src={`${API_BASE_URL}/molecule/image?smiles=${encodeURIComponent(m.smiles)}`}
              alt="molecule" className="w-20 h-20 rounded-xl border border-neutral-100 bg-neutral-50 object-contain flex-shrink-0"
              onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}/>
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs text-neutral-500 font-medium">Binding score</span>
            </div>
            <ScoreBar score={m.score} />

            {/* Dual similarity */}
            {(m.similar_drug || m.similar_drug_semantic) && (
              <div className="mt-3 space-y-1.5">
                {m.similar_drug && (
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-medium w-20 flex-shrink-0">Fingerprint</span>
                    <span className="text-xs font-semibold text-neutral-800">{m.similar_drug.name}</span>
                    <span className="text-[10px] text-violet-600 font-bold ml-auto">
                      {m.similar_drug.similarity !== null ? `Tan ${m.similar_drug.similarity.toFixed(2)}` : "—"}
                    </span>
                  </div>
                )}
                {m.similar_drug_semantic && (
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-wider text-neutral-400 font-medium w-20 flex-shrink-0">ChemBERTa</span>
                    <span className="text-xs font-semibold text-neutral-800">{m.similar_drug_semantic.name}</span>
                    <span className="text-[10px] text-indigo-600 font-bold ml-auto">
                      {m.similar_drug_semantic.semantic_similarity !== null ? `Cos ${m.similar_drug_semantic.semantic_similarity.toFixed(2)}` : "—"}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Expanded ADMET section */}
      {expanded && m.admet && (
        <div className="border-t border-neutral-100 px-4 py-3 bg-neutral-50/50">
          <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-3">ADMET Profile</p>
          <div className="flex flex-wrap gap-2 mb-3">
            <ADMETPill label="MW" value={m.admet.molecular_weight.toFixed(1)} />
            <ADMETPill label="logP" value={m.admet.logp.toFixed(2)} />
            <ADMETPill label="HBD" value={m.admet.hbd} />
            <ADMETPill label="HBA" value={m.admet.hba} />
            <ADMETPill label="TPSA" value={m.admet.tpsa.toFixed(1)} />
            <ADMETPill label="RotB" value={m.admet.rotatable_bonds} />
            <ADMETPill label="Lipinski" value={m.admet.lipinski_pass ? "Pass" : "Fail"} pass={m.admet.lipinski_pass} />
          </div>
          {m.notes && <p className="text-xs text-neutral-500 leading-relaxed">{m.notes}</p>}
        </div>
      )}
    </div>
  );
};

// ── Range slider with label ───────────────────────────────────────────────────
const RangeField: React.FC<{
  label: string; min: number; max: number; step?: number;
  value: number; onChange: (v: number) => void; unit?: string;
}> = ({ label, min, max, step = 1, value, onChange, unit = "" }) => (
  <div>
    <div className="flex items-center justify-between mb-1">
      <label className="text-[10px] uppercase tracking-[0.15em] text-neutral-400 font-medium">{label}</label>
      <span className="text-xs font-bold text-neutral-700">{value}{unit}</span>
    </div>
    <input type="range" min={min} max={max} step={step} value={value}
      onChange={e => onChange(Number(e.target.value))}
      className="w-full h-1 accent-violet-600 cursor-pointer"/>
  </div>
);

// ── Toggle ────────────────────────────────────────────────────────────────────
const Toggle: React.FC<{ checked: boolean; onChange: (v: boolean) => void; label: string }> = ({ checked, onChange, label }) => (
  <label className="flex items-center gap-3 cursor-pointer">
    <div onClick={() => onChange(!checked)}
      className={`w-10 h-5 rounded-full transition-colors relative flex-shrink-0 ${checked ? "bg-violet-600" : "bg-neutral-200"}`}>
      <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-200 ${checked ? "translate-x-5" : "translate-x-0.5"}`}/>
    </div>
    <span className="text-sm text-neutral-700 font-medium">{label}</span>
  </label>
);

// ── Main ──────────────────────────────────────────────────────────────────────
const DiscoverPage: React.FC = () => {
  const [targetId, setTargetId] = useState("EGFR");
  const [numMolecules, setNumMolecules] = useState(5);
  const [lipinskiOnly, setLipinskiOnly] = useState(true);
  const [showAdmet, setShowAdmet] = useState(false);
  const [maxMW, setMaxMW] = useState(500);
  const [maxLogP, setMaxLogP] = useState(5);
  const [maxTPSA, setMaxTPSA] = useState(140);

  const [loading, setLoading] = useState(false);
  const [pipelineStep, setPipelineStep] = useState(-1); // -1 = idle, 0-3 = active step, 4 = done
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [results, setResults] = useState<Molecule[]>([]);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Animate pipeline steps while loading
  useEffect(() => {
    if (!loading) return;
    setPipelineStep(0);
    const timings = [800, 1800, 2800, 3600];
    const timers = timings.map((t, i) => setTimeout(() => setPipelineStep(i + 1), t));
    return () => timers.forEach(clearTimeout);
  }, [loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setRunId(null);
    setResults([]);
    setPipelineStep(0);
    try {
      const res = await discoverMolecules({ target_id: targetId, num_molecules: numMolecules, lipinski_only: lipinskiOnly });
      if (res?.run_id) setRunId(res.run_id);
      setResults(res?.molecules || []);
      setPipelineStep(4);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 200);
    } catch (err: any) {
      setError(err?.message || "Discovery failed");
      setPipelineStep(-1);
    } finally {
      setLoading(false);
    }
  };

  const [topCandidates, similarCandidates, exploratory] = useMemo(() => {
    const top = results.slice(0, 3);
    const sim = results.filter(m => !!m.similar_drug && !top.includes(m));
    const exp = results.filter(m => !top.includes(m) && !sim.includes(m));
    return [top, sim.slice(0, 4), exp];
  }, [results]);

  const stepState = (i: number): "idle" | "active" | "done" => {
    if (pipelineStep < 0) return "idle";
    if (i < pipelineStep) return "done";
    if (i === pipelineStep) return "active";
    return "idle";
  };

  return (
    <div className="min-h-screen bg-[#f8f8f6] pt-16">
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-12">

        {/* Header */}
        <div className="mb-10">
          <p className="text-xs uppercase tracking-[0.3em] text-neutral-400 mb-2 font-medium">Discovery Pipeline</p>
          <h1 className="text-5xl font-black tracking-[-0.03em] text-neutral-900">Target & constraints</h1>
        </div>

        <div className="grid gap-6 lg:grid-cols-[380px_1fr] items-start">

          {/* ── LEFT: Form ── */}
          <div className="space-y-4">
            <div className="bg-white rounded-3xl border border-neutral-100 p-6 space-y-5">
              {/* Target */}
              <div>
                <label className="block text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-2">Target Identifier</label>
                <input value={targetId} onChange={e => setTargetId(e.target.value)} placeholder="e.g. EGFR"
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm font-semibold text-neutral-900 focus:outline-none focus:border-violet-400 transition-colors placeholder:font-normal placeholder:text-neutral-400"/>
              </div>

              {/* Molecule count */}
              <div>
                <label className="block text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-2">Molecule Count</label>
                <input type="number" min={1} max={100} value={numMolecules} onChange={e => setNumMolecules(Number(e.target.value))}
                  className="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm font-semibold text-neutral-900 focus:outline-none focus:border-violet-400 transition-colors"/>
              </div>

              {/* Constraints */}
              <div className="rounded-2xl border border-neutral-100 bg-neutral-50 p-4 space-y-4">
                <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium">Constraints</p>
                <Toggle checked={lipinskiOnly} onChange={setLipinskiOnly} label="Enforce Lipinski compliance"/>
                <Toggle checked={showAdmet} onChange={setShowAdmet} label="Advanced ADMET filters"/>

                {/* Advanced ADMET sliders */}
                {showAdmet && (
                  <div className="pt-3 border-t border-neutral-200 space-y-4">
                    <p className="text-[10px] uppercase tracking-[0.15em] text-neutral-400 font-medium">ADMET Thresholds</p>
                    <RangeField label="Max MW" min={200} max={600} step={10} value={maxMW} onChange={setMaxMW} unit=" Da"/>
                    <RangeField label="Max logP" min={0} max={8} step={0.5} value={maxLogP} onChange={setMaxLogP}/>
                    <RangeField label="Max TPSA" min={40} max={200} step={5} value={maxTPSA} onChange={setMaxTPSA} unit=" Ų"/>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {[`MW ≤ ${maxMW}`, `logP ≤ ${maxLogP}`, `TPSA ≤ ${maxTPSA}`].map(t => (
                        <span key={t} className="text-[10px] bg-violet-50 text-violet-700 border border-violet-100 px-2 py-0.5 rounded-full font-medium">{t}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Submit */}
              <button type="button" onClick={handleSubmit} disabled={loading}
                className="w-full rounded-2xl bg-neutral-900 text-white text-sm font-bold py-4 hover:bg-neutral-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
                {loading
                  ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>Running pipeline…</>
                  : "Run Discovery"}
              </button>

              {error && <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-2">{error}</p>}
              {runId && (
                <p className="text-xs text-neutral-400">
                  Run ID: <Link to={`/runs/${runId}`} className="text-violet-600 font-semibold hover:underline">{runId.slice(0, 20)}…</Link>
                </p>
              )}
            </div>

            {/* Pipeline steps card — always visible, animates when running */}
            <div className="bg-white rounded-3xl border border-neutral-100 p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium mb-0.5">Agent Plan Preview</p>
                  <h3 className="text-base font-bold text-neutral-900">Planner outline</h3>
                </div>
                <span className="text-[9px] uppercase tracking-wider text-neutral-400">Auto-generated</span>
              </div>
              <div className="space-y-3">
                {planSteps.map((step, i) => (
                  <PipelineStep key={step} num={i + 1} text={step} state={stepState(i)}/>
                ))}
              </div>
              {pipelineStep === 4 && (
                <div className="mt-4 flex items-center gap-2 text-xs text-emerald-600 font-medium bg-emerald-50 border border-emerald-100 rounded-xl px-3 py-2">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
                  Pipeline complete · {results.length} candidates generated
                </div>
              )}
            </div>
          </div>

          {/* ── RIGHT: Results ── */}
          <div className="space-y-5" ref={resultsRef}>

            {/* Results header — sticky once run completes */}
            <div className={`bg-white rounded-3xl border border-neutral-100 p-6 transition-all duration-300 ${runId ? "border-violet-100" : ""}`}>
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xl font-bold text-neutral-900 tracking-tight">Results</h2>
                <div className="flex items-center gap-3">
                  {runId && (
                    <Link to={`/runs/${runId}`}
                      className="text-xs text-violet-600 font-semibold hover:underline flex items-center gap-1">
                      View full run
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                    </Link>
                  )}
                  <span className="text-sm text-neutral-400">{results.length} molecules</span>
                </div>
              </div>
              {runId && (
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] bg-violet-50 text-violet-700 border border-violet-100 px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider">{targetId}</span>
                  <span className="text-xs text-neutral-400 font-mono">{runId}</span>
                </div>
              )}

              {results.length === 0 && !loading && (
                <p className="text-sm text-neutral-400 text-center py-10">
                  Run discovery to populate agent-ranked candidates.
                </p>
              )}
              {loading && (
                <div className="py-10 text-center">
                  <div className="w-8 h-8 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin mx-auto mb-3"/>
                  <p className="text-sm text-neutral-400">Orchestrating pipeline…</p>
                </div>
              )}
            </div>

            {/* Top candidates */}
            {topCandidates.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-3 px-1">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium">Top Candidates</p>
                  <p className="text-[10px] text-neutral-400">Highest composite score</p>
                </div>
                <div className="space-y-3">
                  {topCandidates.map((m, i) => <MoleculeCard key={`top-${i}`} molecule={m} rank={i + 1}/>)}
                </div>
              </div>
            )}

            {/* Similar to known drugs */}
            {similarCandidates.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-3 px-1">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium">Similar to Known Drugs</p>
                  <p className="text-[10px] text-neutral-400">Repositioning hypotheses</p>
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  {similarCandidates.map((m, i) => <MoleculeCard key={`sim-${i}`} molecule={m} rank={topCandidates.length + i + 1}/>)}
                </div>
              </div>
            )}

            {/* Exploratory */}
            {exploratory.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-3 px-1">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400 font-medium">Exploratory Set</p>
                  <p className="text-[10px] text-neutral-400">Diverse scaffolds worth review</p>
                </div>
                <div className="space-y-3">
                  {exploratory.map((m, i) => <MoleculeCard key={`exp-${i}`} molecule={m} rank={topCandidates.length + similarCandidates.length + i + 1}/>)}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DiscoverPage;