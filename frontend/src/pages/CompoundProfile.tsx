import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  addAnnotation, addToCollection, deleteAnnotation, errorMessage, getCompound, listCollections, similaritySearch,
  type CollectionRow, type CompoundProfile as Profile, type SimilarityHit,
} from "../api/library";
import { LibraryShell } from "../components/library/LibraryShell";
import {
  Btn, Card, CompoundLink, ErrorBox, EvidenceBadge, fmt, fmtNm, Label, MolThumb, OriginBadge, PropChips, Select, Spinner, TextInput,
} from "../components/library/ui";

const KV = ({ k, v }: { k: string; v: React.ReactNode }) => (
  <div className="flex justify-between gap-4 py-1.5 border-b border-black/5 text-xs"><span className="opacity-50">{k}</span><span className="font-medium text-right break-all">{v}</span></div>
);

export default function CompoundProfile() {
  const { compoundId } = useParams();
  const id = Number(compoundId);
  const [p, setP] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [author, setAuthor] = useState("");
  const [cols, setCols] = useState<CollectionRow[]>([]);
  const [colId, setColId] = useState("");
  const [neighbours, setNeighbours] = useState<SimilarityHit[] | null>(null);

  const load = useCallback(() => {
    getCompound(id).then(setP).catch(e => setError(errorMessage(e)));
  }, [id]);
  useEffect(load, [load]);
  useEffect(() => { listCollections().then(setCols).catch(() => setCols([])); }, []);
  useEffect(() => {
    setNeighbours(null);
    similaritySearch({ compound_id: id, k: 5, method: "fingerprint" })
      .then(r => setNeighbours(r.results.fingerprint ?? [])).catch(() => setNeighbours([]));
  }, [id]);

  const annotate = async (e: React.FormEvent) => {
    e.preventDefault();
    try { await addAnnotation(id, note.trim(), author.trim()); setNote(""); load(); } catch (err) { setError(errorMessage(err)); }
  };
  const addCol = async () => {
    if (!colId) return;
    try { await addToCollection(Number(colId), id); setColId(""); load(); } catch (err) { setError(errorMessage(err)); }
  };

  if (error && !p) return <LibraryShell title="Compound"><ErrorBox message={error} /><Link to="/library" className="text-xs underline">← Back to library</Link></LibraryShell>;
  if (!p) return <LibraryShell title="Compound"><Spinner /></LibraryShell>;

  const targets = Array.from(new Set([...p.experimental_bioactivity.map(a => a.target), ...p.predictions.map(x => x.target)]));

  return (
    <LibraryShell title={p.name || p.inchikey} subtitle={p.formula ?? undefined}>
      <Link to="/library" className="text-[10px] font-bold uppercase tracking-widest opacity-50 hover:opacity-100">← Library</Link>
      <ErrorBox message={error} />
      <div className="grid xl:grid-cols-3 gap-6">
        <div className="space-y-6">
          <Card title="Identity">
            <div className="flex gap-4 mb-4"><MolThumb smiles={p.canonical_smiles} size={140} /><div className="space-y-2"><OriginBadge origin={p.origin} /><PropChips c={p} /></div></div>
            <KV k="InChIKey" v={p.inchikey} />
            <KV k="Standardised SMILES" v={<span className="font-mono text-[10px]">{p.canonical_smiles}</span>} />
            <KV k="Original SMILES" v={<span className="font-mono text-[10px]">{p.original_smiles}</span>} />
            <KV k="Heavy atoms / rings" v={`${p.physchem.heavy_atoms} / ${p.physchem.ring_count}`} />
            <KV k="Registered" v={new Date(p.created_at).toLocaleString()} />
            {p.origin === "generated" && <>
              <KV k="Generation method" v={p.generation_method} />
              <KV k="Discovery run" v={p.generation_run_id ? <Link className="underline" to={`/runs/${p.generation_run_id}`}>{p.generation_run_id.slice(0, 8)}…</Link> : "–"} />
            </>}
            <p className="text-[10px] opacity-40 mt-3">Basic RDKit physicochemical descriptors; not ADMET predictions.</p>
            <div className="mt-4"><Link className="text-[10px] font-bold uppercase tracking-widest underline" to={`/library?tab=similarity&smiles=${encodeURIComponent(p.canonical_smiles)}`}>Run a similarity search →</Link></div>
          </Card>

          <Card title="Provenance">
            <ul className="space-y-3" aria-label="Sources">
              {p.sources_detail.map((s, i) => (
                <li key={i} className="text-xs bg-[#F8F9FA] rounded-2xl p-3 border border-black/5">
                  <div className="flex justify-between"><b>{s.source_db}</b><span className="opacity-40">{new Date(s.retrieved_at).toLocaleDateString()}</span></div>
                  {s.external_id && <div className="opacity-60">ID: {s.url ? <a className="underline" href={s.url} target="_blank" rel="noreferrer">{s.external_id}</a> : s.external_id}</div>}
                  <div className="font-mono text-[10px] opacity-50 break-all">as received: {s.original_smiles}</div>
                  {s.note && <div className="opacity-50 mt-1">{s.note}</div>}
                </li>))}
            </ul>
          </Card>

          <Card title="Collections">
            <div className="flex flex-wrap gap-2 mb-3">{p.collections.length === 0 ? <span className="text-xs opacity-40">Not in any collection</span> :
              p.collections.map(c => <span key={c.id} className="text-[10px] font-bold bg-black text-white rounded-full px-3 py-1">{c.name}</span>)}</div>
            <div className="flex gap-2">
              <Select aria-label="Add to collection" value={colId} onChange={e => setColId(e.target.value)}>
                <option value="">Add to collection…</option>{cols.filter(c => !p.collections.some(x => x.id === c.id)).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </Select>
              <Btn variant="light" disabled={!colId} onClick={addCol}>Add</Btn>
            </div>
          </Card>
        </div>

        <div className="xl:col-span-2 space-y-6">
          <p className="text-[11px] bg-white rounded-2xl border border-black/5 px-4 py-3 opacity-70">{p.evidence_notice}</p>

          <Card title="Experimental bioactivity" right={<EvidenceBadge kind="experimental" />}>
            {p.experimental_bioactivity.length === 0 ? <p className="text-sm opacity-50">No experimental measurements recorded for this compound. Import data for a target in the “Data sources” tab.</p> : (
              <table className="w-full text-xs" aria-label="Experimental bioactivity">
                <thead><tr className="text-left opacity-40"><th className="py-2">Target</th><th>Type</th><th>Value</th><th>pValue</th><th>Source</th><th>Reference</th></tr></thead>
                <tbody>{p.experimental_bioactivity.map(a => (
                  <tr key={a.id} className="border-t border-black/5">
                    <td className="py-2 font-bold">{a.target}</td><td>{a.type}</td><td>{a.relation ?? "="} {fmtNm(a.value_nm)} nM</td>
                    <td>{fmt(a.pvalue)}</td><td>{a.source_db} <span className="opacity-40">{a.external_id.slice(0, 18)}</span></td><td className="opacity-60">{a.assay_ref ?? "–"}</td>
                  </tr>))}</tbody>
              </table>)}
          </Card>

          <Card title="Prediction history" right={<EvidenceBadge kind="computational_prediction" />}>
            {p.predictions.length === 0 ? <p className="text-sm opacity-50">No model predictions for this compound yet.</p> : (
              <table className="w-full text-xs" aria-label="Prediction history">
                <thead><tr className="text-left opacity-40"><th className="py-2">Target</th><th>Predicted Kd</th><th>pKd</th><th>Model</th><th>Run</th><th>When</th></tr></thead>
                <tbody>{p.predictions.map(x => (
                  <tr key={x.id} className="border-t border-black/5">
                    <td className="py-2 font-bold">{x.target}</td><td>{fmtNm(x.predicted_kd)} {x.units}</td><td>{fmt(x.pkd)}</td>
                    <td title={x.model}>{x.model.slice(0, 30)}{x.model_version ? ` v${x.model_version}` : ""}</td>
                    <td>{x.run_id ? <Link className="underline" to={`/runs/${x.run_id}`}>{x.run_id.slice(0, 8)}</Link> : "–"}</td>
                    <td className="opacity-50">{new Date(x.created_at).toLocaleString()}</td>
                  </tr>))}</tbody>
              </table>)}
            {targets.length > 0 && <p className="text-[10px] opacity-40 mt-3">Predictions are computational estimates and are not experimental confirmation of binding.</p>}
          </Card>

          <Card title="Most similar compounds in the registry">
            {!neighbours ? <Spinner /> : neighbours.length === 0 ? <p className="text-sm opacity-50">No neighbours.</p> : (
              <ul className="divide-y divide-black/5" aria-label="Nearest compounds">{neighbours.map(h => (
                <li key={h.compound.id} className="flex items-center gap-3 py-2"><MolThumb smiles={h.compound.canonical_smiles} size={40} />
                  <div className="flex-1"><CompoundLink c={h.compound} /> <OriginBadge origin={h.compound.origin} /></div>
                  <span className="text-xs font-bold">{h.similarity.toFixed(3)}</span></li>))}</ul>)}
          </Card>

          <Card title="Annotations">
            <ul className="space-y-3 mb-4" aria-label="Annotations">
              {p.annotations.length === 0 && <li className="text-xs opacity-40">No notes yet.</li>}
              {p.annotations.map(a => (
                <li key={a.id} className="text-xs bg-[#F8F9FA] rounded-2xl p-3 border border-black/5 flex justify-between gap-3">
                  <div><p>{a.text}</p><p className="opacity-40 text-[10px] mt-1">{a.author || "anonymous"} · {new Date(a.created_at).toLocaleString()}</p></div>
                  <button aria-label="Delete annotation" className="text-red-500 text-[10px] font-bold" onClick={async () => { await deleteAnnotation(a.id); load(); }}>Delete</button>
                </li>))}
            </ul>
            <form onSubmit={annotate} className="grid grid-cols-4 gap-3 items-end">
              <div className="col-span-3"><Label htmlFor="note-text">Add a note</Label><TextInput id="note-text" value={note} onChange={e => setNote(e.target.value)} /></div>
              <div><Label htmlFor="note-author">Author</Label><TextInput id="note-author" value={author} onChange={e => setAuthor(e.target.value)} /></div>
              <div className="col-span-4"><Btn type="submit" disabled={!note.trim()}>Save note</Btn></div>
            </form>
          </Card>
        </div>
      </div>
    </LibraryShell>
  );
}
