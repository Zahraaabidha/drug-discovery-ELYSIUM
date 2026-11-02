import { useEffect, useState } from "react";
import {
  addCompound, errorMessage, getLibraryTargets, importPubChem, importTarget, syncKnowledgeGraph,
  type TargetRow,
} from "../../api/library";
import { Btn, Card, ErrorBox, Label, NumInput, Select, TextInput } from "./ui";

const Result = ({ data }: { data: unknown }) => (
  <pre data-testid="import-result" className="mt-3 text-[10px] bg-[#F8F9FA] border border-black/5 rounded-2xl p-4 overflow-x-auto">{JSON.stringify(data, null, 2)}</pre>
);

export default function DataTab({ targets, onChanged }: { targets: string[]; onChanged: () => void }) {
  const [rows, setRows] = useState<TargetRow[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);

  const [pcName, setPcName] = useState("");
  const [smiles, setSmiles] = useState("");
  const [cname, setCname] = useState("");
  const [target, setTarget] = useState(targets[0] ?? "EGFR");
  const [chembl, setChembl] = useState(true);
  const [bdb, setBdb] = useState(true);
  const [max, setMax] = useState<number | undefined>(200);

  const refresh = () => getLibraryTargets().then(setRows).catch(() => setRows([]));
  useEffect(() => { refresh(); }, []);
  useEffect(() => { if (targets.length && !targets.includes(target)) setTarget(targets[0]); }, [targets, target]);

  const run = async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key); setError(null); setResult(null);
    try { setResult(await fn()); onChanged(); refresh(); } catch (e) { setError(errorMessage(e)); } finally { setBusy(null); }
  };

  const sources = [chembl && "chembl", bdb && "bindingdb"].filter(Boolean) as string[];

  return (
    <div className="grid lg:grid-cols-2 gap-6">
      <div className="space-y-6">
        <Card title="Import experimental activity for a target">
          <p className="text-[11px] opacity-50 mb-4">Retrieves measured IC50 / Ki / Kd values (exact "=" relations, nM) from public databases. Each record keeps its source database, external ID, assay reference and retrieval time.</p>
          <div className="grid grid-cols-2 gap-4">
            <div><Label htmlFor="imp-target">Target</Label>
              <Select id="imp-target" value={target} onChange={e => setTarget(e.target.value)}>{targets.map(t => <option key={t}>{t}</option>)}</Select></div>
            <NumInput id="imp-max" label="Max records / source" value={max} onChange={setMax} />
            <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={chembl} onChange={e => setChembl(e.target.checked)} /> ChEMBL</label>
            <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={bdb} onChange={e => setBdb(e.target.checked)} /> BindingDB</label>
          </div>
          <div className="flex gap-2 mt-4">
            <Btn disabled={busy !== null || sources.length === 0} onClick={() => run("target", () => importTarget(target, sources, max ?? 200))}>
              {busy === "target" ? "Importing…" : "Import measurements"}</Btn>
            <Btn variant="light" disabled={busy !== null} onClick={() => run("kg", () => syncKnowledgeGraph(target))}>
              {busy === "kg" ? "Syncing…" : "Sync to knowledge graph"}</Btn>
          </div>
        </Card>
        <Card title="Look up a compound in PubChem">
          <form className="flex gap-3 items-end" onSubmit={e => { e.preventDefault(); run("pubchem", () => importPubChem(pcName.trim())); }}>
            <div className="flex-1"><Label htmlFor="pc-name">Compound name</Label><TextInput id="pc-name" value={pcName} onChange={e => setPcName(e.target.value)} placeholder="e.g. imatinib" /></div>
            <Btn type="submit" disabled={busy !== null || !pcName.trim()}>{busy === "pubchem" ? "Searching…" : "Import"}</Btn>
          </form>
        </Card>
        <Card title="Add your own compound">
          <form className="grid grid-cols-3 gap-3 items-end" onSubmit={e => { e.preventDefault(); run("add", () => addCompound(smiles.trim(), cname.trim())); }}>
            <div className="col-span-2"><Label htmlFor="add-smiles">SMILES</Label><TextInput id="add-smiles" className="font-mono" value={smiles} onChange={e => setSmiles(e.target.value)} /></div>
            <div><Label htmlFor="add-name">Name (optional)</Label><TextInput id="add-name" value={cname} onChange={e => setCname(e.target.value)} /></div>
            <div className="col-span-3"><Btn type="submit" disabled={busy !== null || !smiles.trim()}>{busy === "add" ? "Adding…" : "Add to registry"}</Btn></div>
          </form>
        </Card>
        <ErrorBox message={error} />
        {result !== null && <Result data={result} />}
      </div>
      <Card title="Supported targets">
        <p className="text-[11px] opacity-50 mb-3">Only these targets can be predicted. Requests for any other target are rejected - no substitute target is used.</p>
        <table className="w-full text-xs" aria-label="Supported targets">
          <thead><tr className="text-left opacity-40"><th className="py-2">Target</th><th>UniProt</th><th className="text-right">Measured</th><th className="text-right">Predicted</th></tr></thead>
          <tbody>{rows.map(r => (
            <tr key={r.symbol} className="border-t border-black/5">
              <td className="py-2 font-bold">{r.symbol}</td><td className="opacity-60">{r.uniprot_id}</td>
              <td className="text-right text-emerald-700 font-bold">{r.experimental_measurements}</td>
              <td className="text-right text-amber-700 font-bold">{r.predictions}</td>
            </tr>))}</tbody>
        </table>
      </Card>
    </div>
  );
}
