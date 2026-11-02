import { useCallback, useEffect, useState } from "react";
import {
  createCollection, deleteCollection, errorMessage, listCollections, listCompounds, removeFromCollection,
  type CollectionRow, type CompoundSummary,
} from "../../api/library";
import { Btn, Card, CompoundLink, ErrorBox, Label, MolThumb, OriginBadge, Spinner, TextInput } from "./ui";

export default function CollectionsTab({ onChanged }: { onChanged: () => void }) {
  const [cols, setCols] = useState<CollectionRow[] | null>(null);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [open, setOpen] = useState<CollectionRow | null>(null);
  const [items, setItems] = useState<CompoundSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => listCollections().then(setCols).catch(e => setError(errorMessage(e))), []);
  useEffect(() => { refresh(); }, [refresh]);

  const loadItems = useCallback((c: CollectionRow) => {
    listCompounds({ collection_id: c.id, limit: 200 }).then(r => setItems(r.items)).catch(e => setError(errorMessage(e)));
  }, []);
  useEffect(() => { if (open) loadItems(open); }, [open, loadItems]);

  const create = async (e: React.FormEvent) => {
    e.preventDefault(); setError(null);
    try { await createCollection(name.trim(), desc.trim() || undefined); setName(""); setDesc(""); await refresh(); onChanged(); }
    catch (err) { setError(errorMessage(err)); }
  };
  const remove = async (c: CollectionRow) => {
    try { await deleteCollection(c.id); if (open?.id === c.id) setOpen(null); await refresh(); onChanged(); }
    catch (err) { setError(errorMessage(err)); }
  };
  const removeItem = async (cid: number) => {
    if (!open) return;
    try { await removeFromCollection(open.id, cid); loadItems(open); refresh(); } catch (err) { setError(errorMessage(err)); }
  };

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <div className="space-y-6">
        <Card title="New collection">
          <form onSubmit={create} className="space-y-3">
            <div><Label htmlFor="col-name">Name</Label><TextInput id="col-name" required value={name} onChange={e => setName(e.target.value)} placeholder="e.g. EGFR kinase set" /></div>
            <div><Label htmlFor="col-desc">Description</Label><TextInput id="col-desc" value={desc} onChange={e => setDesc(e.target.value)} /></div>
            <Btn type="submit" disabled={!name.trim()}>Create</Btn>
          </form>
        </Card>
        <ErrorBox message={error} />
      </div>
      <div className="lg:col-span-2 space-y-6">
        <Card title="Collections">
          {!cols ? <Spinner /> : cols.length === 0 ? <p className="text-sm opacity-50">No collections yet. Select compounds in the Compounds tab and add them to a collection.</p> : (
            <ul className="divide-y divide-black/5" aria-label="Collections">
              {cols.map(c => (
                <li key={c.id} className="flex items-center gap-3 py-3">
                  <button className="flex-1 text-left" onClick={() => setOpen(c)}>
                    <span className="font-bold text-sm">{c.name}</span> <span className="text-[10px] opacity-40">{c.size} compound{c.size === 1 ? "" : "s"}</span>
                    {c.description && <p className="text-[11px] opacity-50">{c.description}</p>}
                  </button>
                  <Btn variant="danger" aria-label={`Delete collection ${c.name}`} onClick={() => remove(c)}>Delete</Btn>
                </li>))}
            </ul>)}
        </Card>
        {open && (
          <Card title={`Contents: ${open.name}`}>
            {items.length === 0 ? <p className="text-sm opacity-50">This collection is empty.</p> : (
              <ul className="divide-y divide-black/5" aria-label="Collection contents">
                {items.map(c => (
                  <li key={c.id} className="flex items-center gap-3 py-2">
                    <MolThumb smiles={c.canonical_smiles} size={44} />
                    <div className="flex-1"><CompoundLink c={c} /> <OriginBadge origin={c.origin} /></div>
                    <Btn variant="light" onClick={() => removeItem(c.id)}>Remove</Btn>
                  </li>))}
              </ul>)}
          </Card>)}
      </div>
    </div>
  );
}
