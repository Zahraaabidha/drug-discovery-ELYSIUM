// src/pages/DrugGraphPage.tsx
import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getDrugGraph } from "../api/elysium";
import type { DrugGraphResponse, DrugGraphEntry } from "../api/elysium";

const DrugGraphPage: React.FC = () => {
  const { drugName } = useParams<{ drugName: string }>();
  const [graph, setGraph] = useState<DrugGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!drugName) return;

    const fetchGraph = async () => {
      try {
        const decoded = decodeURIComponent(drugName);
        const data = await getDrugGraph(decoded);
        setGraph(data);
      } catch (err) {
        console.error(err);
        setError("Failed to load drug graph.");
      } finally {
        setLoading(false);
      }
    };

    fetchGraph();
  }, [drugName]);

  const entries: DrugGraphEntry[] = graph?.molecules ?? [];

  return (
    <div className="bg-slate-50">
      <section className="max-w-6xl mx-auto px-6 py-10 space-y-6">
        <header className="flex flex-col gap-2">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Similarity map</p>
          <h1 className="text-3xl font-serif text-slate-900">
            {graph?.drug_name ?? drugName}
          </h1>
          <div className="flex flex-wrap gap-3 text-sm text-slate-500">
            <Link to="/graphs" className="text-blue-600">← Graph explorer</Link>
            <Link to="/runs" className="text-slate-500">Runs</Link>
          </div>
        </header>

        {loading && <p className="text-sm text-slate-500">Loading graph…</p>}
        {error && (
          <p className="text-sm text-amber-600 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2">{error}</p>
        )}
        {!loading && !error && entries.length === 0 && (
          <p className="text-sm text-slate-500">No generated molecules are linked to this drug yet.</p>
        )}

        <div className="grid gap-4">
          {entries.map((e, idx) => (
            <article key={idx} className="bg-white border border-slate-200 rounded-2xl shadow-sm p-5 text-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-mono text-xs text-slate-500 break-all">{e.smiles}</p>
                  <p className="text-slate-600 mt-2">
                    Target <span className="font-semibold text-slate-900">{e.target_id}</span> · Run {" "}
                    <Link to={`/runs/${e.run_id}`} className="text-blue-600">
                      {e.run_id.slice(0, 8)}…
                    </Link>
                    {" "}· index {e.molecule_index}
                  </p>
                </div>
                <div className="text-sm text-slate-500">
                  Score
                  <p className="text-xl font-semibold text-slate-900">{e.score.toFixed(3)}</p>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
};

export default DrugGraphPage;