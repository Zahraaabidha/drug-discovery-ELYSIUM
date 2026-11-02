import { useState } from "react";
import { errorMessage, similaritySearch, type SimilarityHit, type SimilarityResponse } from "../../api/library";
import { Btn, Card, CompoundLink, ErrorBox, Label, MolThumb, NumInput, OriginBadge, Select, Spinner, TextInput } from "./ui";

const METHOD_TITLE: Record<string, string> = {
  fingerprint: "Morgan fingerprint · Tanimoto",
  embedding: "ChemBERTa embedding · cosine",
};

const Hits = ({ hits }: { hits: SimilarityHit[] }) =>
  hits.length === 0 ? <p className="text-xs opacity-50 py-4">No neighbours found.</p> : (
    <ol className="divide-y divide-black/5" aria-label="Similar compounds">
      {hits.map((h, i) => (
        <li key={h.compound.id} className="flex items-center gap-4 py-3">
          <span className="w-6 text-[10px] font-bold opacity-30">{i + 1}</span>
          <MolThumb smiles={h.compound.canonical_smiles} size={48} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2"><CompoundLink c={h.compound} /><OriginBadge origin={h.compound.origin} /></div>
            <p className="font-mono text-[10px] opacity-40 truncate">{h.compound.canonical_smiles}</p>
          </div>
          <div className="w-32">
            <div className="h-1.5 bg-black/5 rounded-full overflow-hidden"><div className="h-full bg-purple-500" style={{ width: `${Math.max(0, h.similarity) * 100}%` }} /></div>
            <p className="text-[11px] font-bold text-right mt-1" data-testid="similarity-value">{h.similarity.toFixed(3)}</p>
          </div>
        </li>
      ))}
    </ol>
  );

export default function SimilarityTab({ initialSmiles = "" }: { initialSmiles?: string }) {
  const [smiles, setSmiles] = useState(initialSmiles);
  const [k, setK] = useState<number | undefined>(10);
  const [method, setMethod] = useState("fingerprint");
  const [origin, setOrigin] = useState("");
  const [res, setRes] = useState<SimilarityResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!smiles.trim()) { setError("Enter a SMILES string."); return; }
    setLoading(true); setError(null);
    try {
      setRes(await similaritySearch({ smiles: smiles.trim(), k: k ?? 10, method, origin: origin || undefined }));
    } catch (err) { setError(errorMessage(err)); setRes(null); } finally { setLoading(false); }
  };

  return (
    <div className="space-y-6">
      <Card title="Similarity search">
        <form onSubmit={run} className="grid grid-cols-1 md:grid-cols-6 gap-4 items-end">
          <div className="md:col-span-3">
            <Label htmlFor="sim-smiles">Query SMILES</Label>
            <TextInput id="sim-smiles" value={smiles} onChange={e => setSmiles(e.target.value)} placeholder="CC(=O)Oc1ccccc1C(=O)O" className="font-mono" />
          </div>
          <NumInput id="sim-k" label="Top-k" value={k} onChange={setK} />
          <div>
            <Label htmlFor="sim-method">Method</Label>
            <Select id="sim-method" value={method} onChange={e => setMethod(e.target.value)}>
              <option value="fingerprint">Fingerprint (Tanimoto)</option>
              <option value="embedding">ChemBERTa embedding</option>
              <option value="both">Both (compare)</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="sim-origin">Restrict to</Label>
            <Select id="sim-origin" value={origin} onChange={e => setOrigin(e.target.value)}>
              <option value="">All origins</option><option value="reference">Reference</option>
              <option value="external">External</option><option value="generated">Generated</option>
            </Select>
          </div>
          <div className="md:col-span-6"><Btn type="submit" disabled={loading}>{loading ? "Searching…" : "Search"}</Btn></div>
        </form>
      </Card>
      <ErrorBox message={error} />
      {loading && <Spinner label="Searching registry…" />}
      {res && (
        <>
          <p className="text-[10px] opacity-40">Searched {res.registry_size} registry compounds. Similarity reflects structure/representation only - it is not evidence of shared biological activity.</p>
          <div className={`grid gap-6 ${Object.keys(res.results).length > 1 ? "lg:grid-cols-2" : ""}`}>
            {Object.entries(res.results).map(([m, hits]) => (
              <Card key={m} title={METHOD_TITLE[m] ?? m}><Hits hits={hits ?? []} /></Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
