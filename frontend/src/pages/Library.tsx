import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { errorMessage, getLibraryStats, type Stats } from "../api/library";
import { LibraryShell } from "../components/library/LibraryShell";
import CompoundsTab from "../components/library/CompoundsTab";
import SimilarityTab from "../components/library/SimilarityTab";
import CollectionsTab from "../components/library/CollectionsTab";
import DataTab from "../components/library/DataTab";
import EvaluationTab from "../components/library/EvaluationTab";
import ComparePanel from "../components/library/ComparePanel";
import { ErrorBox } from "../components/library/ui";

const TABS = [
  { id: "compounds", label: "Compounds" },
  { id: "similarity", label: "Similarity search" },
  { id: "collections", label: "Collections" },
  { id: "data", label: "Data sources" },
  { id: "evaluation", label: "Evaluation" },
] as const;

const StatTile = ({ label, value, sub }: { label: string; value: number | string; sub?: string }) => (
  <div className="bg-white rounded-[24px] border border-black/5 p-5">
    <p className="text-[9px] font-bold tracking-widest uppercase opacity-40">{label}</p>
    <p className="text-3xl font-medium mt-1" data-testid={`stat-${label.toLowerCase().replace(/\s+/g, "-")}`}>{value}</p>
    {sub && <p className="text-[10px] opacity-40 mt-0.5">{sub}</p>}
  </div>
);

export default function Library() {
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find(t => t.id === params.get("tab"))?.id ?? "compounds") as (typeof TABS)[number]["id"];
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<number[] | null>(null);

  const refreshStats = useCallback(() => {
    getLibraryStats().then(setStats).catch(e => setError(errorMessage(e)));
  }, []);
  useEffect(refreshStats, [refreshStats]);

  const o = stats?.by_origin ?? {};
  return (
    <LibraryShell title="Compound Library" subtitle="One registry for reference, external and generated molecules, with provenance and clearly separated experimental and predicted evidence.">
      <ErrorBox message={error} />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatTile label="Compounds" value={stats?.compounds ?? "–"} />
        <StatTile label="Reference" value={o.reference ?? 0} sub="known drugs" />
        <StatTile label="External" value={o.external ?? 0} sub="PubChem / ChEMBL / BindingDB" />
        <StatTile label="Generated" value={o.generated ?? 0} sub="computational, unsynthesised" />
        <StatTile label="Measurements" value={stats?.bioactivities ?? "–"} sub={`${stats?.predictions ?? 0} model predictions`} />
      </div>

      <div role="tablist" aria-label="Library sections" className="flex gap-2 flex-wrap">
        {TABS.map(t => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setParams({ tab: t.id })}
            className={`px-5 py-2.5 rounded-full text-[10px] font-bold tracking-widest uppercase transition-all ${tab === t.id ? "bg-black text-white" : "bg-white border border-black/5 hover:bg-black/5"}`}>
            {t.label}
          </button>))}
      </div>

      {compareIds && <ComparePanel ids={compareIds} onClose={() => setCompareIds(null)} />}
      <div role="tabpanel">
        {tab === "compounds" && <CompoundsTab stats={stats} onCompare={setCompareIds} />}
        {tab === "similarity" && <SimilarityTab initialSmiles={params.get("smiles") ?? ""} />}
        {tab === "collections" && <CollectionsTab onChanged={refreshStats} />}
        {tab === "data" && <DataTab targets={stats?.supported_targets ?? []} onChanged={refreshStats} />}
        {tab === "evaluation" && <EvaluationTab targets={stats?.supported_targets ?? []} />}
      </div>
    </LibraryShell>
  );
}
