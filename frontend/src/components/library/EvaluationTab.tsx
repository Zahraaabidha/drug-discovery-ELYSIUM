import { useCallback, useEffect, useState } from "react";
import { errorMessage, listEvaluations, runEvaluation, type EvaluationReport } from "../../api/library";
import { Btn, Card, ErrorBox, Label, NumInput, Select, Spinner } from "./ui";

const num = (v: unknown) => (typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(3)) : v == null ? "–" : String(v));

function Metrics({ r }: { r: EvaluationReport }) {
  const m = r.metrics ?? {};
  const flat = Object.entries(m).filter(([, v]) => typeof v !== "object" || v === null);
  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {flat.map(([k, v]) => (
          <div key={k} className="bg-[#F8F9FA] rounded-2xl border border-black/5 p-3">
            <dt className="text-[9px] uppercase tracking-widest opacity-40">{k.replace(/_/g, " ")}</dt>
            <dd className="text-sm font-bold">{num(v)}</dd>
          </div>))}
      </dl>
      <details className="text-[11px]"><summary className="cursor-pointer opacity-60">Parameters &amp; dataset</summary>
        <pre className="bg-[#F8F9FA] rounded-2xl p-3 overflow-x-auto mt-2">{JSON.stringify({ parameters: r.parameters, dataset: r.dataset }, null, 2)}</pre></details>
      <p className="text-[11px] text-amber-800 bg-amber-50 border border-amber-100 rounded-2xl px-4 py-3"><b>Limitations.</b> {r.limitations}</p>
    </div>
  );
}

export default function EvaluationTab({ targets }: { targets: string[] }) {
  const [reports, setReports] = useState<EvaluationReport[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [n, setN] = useState<number | undefined>(100);
  const [seed, setSeed] = useState<number | undefined>(0);
  const [queries, setQueries] = useState<number | undefined>(50);
  const [dtiTarget, setDtiTarget] = useState(targets[0] ?? "EGFR");

  const refresh = useCallback(() => listEvaluations().then(setReports).catch(e => setError(errorMessage(e))), []);
  useEffect(() => { refresh(); }, [refresh]);

  const run = async (kind: "generation" | "similarity" | "dti", body: any) => {
    setBusy(kind); setError(null);
    try { await runEvaluation(kind, body); await refresh(); } catch (e) { setError(errorMessage(e)); } finally { setBusy(null); }
  };

  return (
    <div className="space-y-6">
      <p className="text-xs opacity-60 max-w-3xl">These evaluations check specific, documented properties of the pipeline on data in this registry. They are not claims of real-world effectiveness; each report lists its own limitations.</p>
      <div className="grid lg:grid-cols-3 gap-6">
        <Card title="Generation quality">
          <p className="text-[11px] opacity-50 mb-3">Validity, uniqueness, novelty vs. the registry, diversity and property distributions.</p>
          <div className="grid grid-cols-2 gap-3 mb-3"><NumInput id="ev-n" label="Molecules" value={n} onChange={setN} /><NumInput id="ev-seed" label="Seed" value={seed} onChange={setSeed} /></div>
          <Btn disabled={busy !== null} onClick={() => run("generation", { num_molecules: n ?? 100, seed: seed ?? 0 })}>{busy === "generation" ? "Running…" : "Run"}</Btn>
        </Card>
        <Card title="Similarity retrieval">
          <p className="text-[11px] opacity-50 mb-3">FAISS vs. exact Tanimoto recall@k, and identity retrieval under SMILES re-writing.</p>
          <NumInput id="ev-q" label="Queries" value={queries} onChange={setQueries} />
          <div className="mt-3"><Btn disabled={busy !== null} onClick={() => run("similarity", { n_queries: queries ?? 50, k: 10, seed: seed ?? 0 })}>{busy === "similarity" ? "Running…" : "Run"}</Btn></div>
        </Card>
        <Card title="DTI prediction vs. measurements">
          <p className="text-[11px] opacity-50 mb-3">Compares DeepPurpose predictions with measured Ki/Kd in the registry. Import data for the target first.</p>
          <Label htmlFor="ev-target">Target</Label>
          <Select id="ev-target" value={dtiTarget} onChange={e => setDtiTarget(e.target.value)}>{targets.map(t => <option key={t}>{t}</option>)}</Select>
          <div className="mt-3"><Btn disabled={busy !== null} onClick={() => run("dti", { target: dtiTarget })}>{busy === "dti" ? "Running…" : "Run"}</Btn></div>
        </Card>
      </div>
      <ErrorBox message={error} />
      {!reports ? <Spinner /> : reports.length === 0 ? <p className="text-sm opacity-50">No evaluation reports yet.</p> : reports.map(r => (
        <Card key={r.id} title={`${r.kind} evaluation · ${new Date(r.created_at).toLocaleString()}`}><Metrics r={r} /></Card>))}
    </div>
  );
}
