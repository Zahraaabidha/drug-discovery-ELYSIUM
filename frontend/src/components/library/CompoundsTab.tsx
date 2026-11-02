import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  addToCollection, errorMessage, listCollections, listCompounds,
  type CollectionRow, type CompoundList, type Filters, type Stats, type Origin,
} from "../../api/library";
import { Btn, Card, CompoundLink, ErrorBox, Label, MolThumb, NumInput, OriginBadge, PropChips, Select, Spinner, TextInput } from "./ui";

export const PAGE_SIZE = 25;
const DEFAULTS: Filters = { sort: "id", order: "asc" };

export default function CompoundsTab({ stats, onCompare }: { stats: Stats | null; onCompare: (ids: number[]) => void }) {
  const [filters, setFilters] = useState<Filters>(DEFAULTS);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [data, setData] = useState<CompoundList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [collections, setCollections] = useState<CollectionRow[]>([]);
  const [targetCollection, setTargetCollection] = useState<string>("");
  const [notice, setNotice] = useState<string | null>(null);

  const set = <K extends keyof Filters>(k: K, v: Filters[K]) => { setFilters(f => ({ ...f, [k]: v })); setPage(0); };

  // debounce the free-text search
  useEffect(() => {
    const t = setTimeout(() => { setFilters(f => ({ ...f, q: query || undefined })); setPage(0); }, 250);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => { listCollections().then(setCollections).catch(() => setCollections([])); }, []);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    listCompounds({ ...filters, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
      .then(setData).catch(e => setError(errorMessage(e))).finally(() => setLoading(false));
  }, [filters, page]);
  useEffect(load, [load]);

  const toggle = (id: number) => setSelected(s => (s.includes(id) ? s.filter(x => x !== id) : [...s, id]));
  const reset = () => { setFilters(DEFAULTS); setQuery(""); setPage(0); };
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  const addSelected = async () => {
    if (!targetCollection || selected.length === 0) return;
    try {
      await Promise.all(selected.map(id => addToCollection(Number(targetCollection), id)));
      setNotice(`Added ${selected.length} compound(s) to the collection.`);
      setSelected([]);
    } catch (e) { setError(errorMessage(e)); }
  };

  return (
    <div className="space-y-6">
      <Card title="Search & filters" right={<Btn variant="light" onClick={reset}>Reset</Btn>}>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div className="col-span-2">
            <Label htmlFor="lib-search">Search name, SMILES, InChIKey or external ID</Label>
            <TextInput id="lib-search" type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="e.g. gefitinib, CHEMBL939, XGALLCVXEZPNRQ" />
          </div>
          <div>
            <Label htmlFor="f-origin">Origin</Label>
            <Select id="f-origin" value={filters.origin ?? ""} onChange={e => set("origin", (e.target.value || undefined) as Origin | undefined)}>
              <option value="">All</option><option value="reference">Reference</option>
              <option value="external">External</option><option value="generated">Generated</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="f-source">Source database</Label>
            <Select id="f-source" value={filters.source_db ?? ""} onChange={e => set("source_db", e.target.value || undefined)}>
              <option value="">All</option>
              {Object.keys(stats?.by_source ?? {}).map(s => <option key={s} value={s}>{s}</option>)}
            </Select>
          </div>
          <NumInput id="f-min-mw" label="Min MW" value={filters.min_mw} onChange={v => set("min_mw", v)} />
          <NumInput id="f-max-mw" label="Max MW" value={filters.max_mw} onChange={v => set("max_mw", v)} />
          <NumInput id="f-min-logp" label="Min logP" step={0.1} value={filters.min_logp} onChange={v => set("min_logp", v)} />
          <NumInput id="f-max-logp" label="Max logP" step={0.1} value={filters.max_logp} onChange={v => set("max_logp", v)} />
          <NumInput id="f-max-tpsa" label="Max TPSA" value={filters.max_tpsa} onChange={v => set("max_tpsa", v)} />
          <NumInput id="f-max-hbd" label="Max HBD" value={filters.max_hbd} onChange={v => set("max_hbd", v)} />
          <NumInput id="f-max-hba" label="Max HBA" value={filters.max_hba} onChange={v => set("max_hba", v)} />
          <NumInput id="f-max-rotb" label="Max rotatable bonds" value={filters.max_rotatable_bonds} onChange={v => set("max_rotatable_bonds", v)} />
          <div>
            <Label htmlFor="f-lip">Lipinski</Label>
            <Select id="f-lip" value={filters.lipinski_pass === undefined ? "" : String(filters.lipinski_pass)}
              onChange={e => set("lipinski_pass", e.target.value === "" ? undefined : e.target.value === "true")}>
              <option value="">Any</option><option value="true">Pass</option><option value="false">Fail</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="f-target">Target (for evidence filters)</Label>
            <Select id="f-target" value={filters.target ?? ""} onChange={e => set("target", e.target.value || undefined)}>
              <option value="">Any target</option>
              {(stats?.supported_targets ?? []).map(t => <option key={t} value={t}>{t}</option>)}
            </Select>
          </div>
          <div>
            <Label htmlFor="f-exp">Experimental data</Label>
            <Select id="f-exp" value={filters.has_experimental === undefined ? "" : String(filters.has_experimental)}
              onChange={e => set("has_experimental", e.target.value === "" ? undefined : e.target.value === "true")}>
              <option value="">Any</option><option value="true">Has measurements</option><option value="false">None</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="f-pred">Predictions</Label>
            <Select id="f-pred" value={filters.has_prediction === undefined ? "" : String(filters.has_prediction)}
              onChange={e => set("has_prediction", e.target.value === "" ? undefined : e.target.value === "true")}>
              <option value="">Any</option><option value="true">Has predictions</option><option value="false">None</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="f-col">Collection</Label>
            <Select id="f-col" value={filters.collection_id ?? ""} onChange={e => set("collection_id", e.target.value ? Number(e.target.value) : undefined)}>
              <option value="">All</option>
              {collections.map(c => <option key={c.id} value={c.id}>{c.name} ({c.size})</option>)}
            </Select>
          </div>
          <div>
            <Label htmlFor="f-sort">Sort by</Label>
            <Select id="f-sort" value={filters.sort} onChange={e => set("sort", e.target.value)}>
              <option value="id">Added</option><option value="name">Name</option><option value="mol_weight">MW</option>
              <option value="logp">logP</option><option value="tpsa">TPSA</option><option value="lipinski_violations">Lipinski violations</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="f-order">Order</Label>
            <Select id="f-order" value={filters.order} onChange={e => set("order", e.target.value as "asc" | "desc")}>
              <option value="asc">Ascending</option><option value="desc">Descending</option>
            </Select>
          </div>
        </div>
        <p className="text-[10px] opacity-40 mt-3">Descriptors are basic RDKit physicochemical properties (not ADMET predictions).</p>
      </Card>

      {error && <ErrorBox message={error} />}
      {notice && <p role="status" className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-2xl px-4 py-3">{notice}</p>}

      <Card
        title={data ? `${data.total} compound${data.total === 1 ? "" : "s"}` : "Compounds"}
        right={
          <div className="flex items-center gap-2 flex-wrap justify-end">
            <span className="text-[10px] opacity-40">{selected.length} selected</span>
            <Btn variant="light" disabled={selected.length < 2 || selected.length > 8} onClick={() => onCompare(selected)}>Compare</Btn>
            <Select aria-label="Collection to add to" value={targetCollection} onChange={e => setTargetCollection(e.target.value)} className="!w-40">
              <option value="">Add to collection…</option>
              {collections.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
            <Btn variant="light" disabled={!targetCollection || selected.length === 0} onClick={addSelected}>Add</Btn>
          </div>
        }>
        {loading ? <Spinner /> : !data || data.items.length === 0 ? (
          <p className="text-sm opacity-50 py-8 text-center">No compounds match these filters.</p>
        ) : (
          <ul className="divide-y divide-black/5" aria-label="Compounds">
            {data.items.map(c => (
              <li key={c.id} className="flex items-center gap-4 py-3">
                <input type="checkbox" aria-label={`Select ${c.name || c.inchikey}`} checked={selected.includes(c.id)} onChange={() => toggle(c.id)} />
                <MolThumb smiles={c.canonical_smiles} />
                <div className="flex-1 min-w-0 space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <CompoundLink c={c} /><OriginBadge origin={c.origin} />
                    {c.n_experimental > 0 && <span className="text-[9px] font-bold text-emerald-700">{c.n_experimental} measured</span>}
                    {c.n_predictions > 0 && <span className="text-[9px] font-bold text-amber-700">{c.n_predictions} predicted</span>}
                  </div>
                  <p className="font-mono text-[10px] opacity-40 truncate">{c.canonical_smiles}</p>
                  <PropChips c={c} />
                </div>
                <Link to={`/library/${c.id}`} className="text-[10px] font-bold uppercase tracking-widest opacity-50 hover:opacity-100">Profile →</Link>
              </li>
            ))}
          </ul>
        )}
        {data && data.total > PAGE_SIZE && (
          <div className="flex items-center justify-between pt-4">
            <Btn variant="light" disabled={page === 0} onClick={() => setPage(p => p - 1)}>Previous</Btn>
            <span className="text-[10px] opacity-50">Page {page + 1} of {totalPages}</span>
            <Btn variant="light" disabled={page + 1 >= totalPages} onClick={() => setPage(p => p + 1)}>Next</Btn>
          </div>
        )}
      </Card>
    </div>
  );
}
