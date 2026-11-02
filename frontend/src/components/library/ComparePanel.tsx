import { useEffect, useState } from "react";
import { compareCompounds, errorMessage, type CompareResponse } from "../../api/library";
import { Btn, Card, CompoundLink, ErrorBox, fmt, fmtNm, MolThumb, OriginBadge, Spinner } from "./ui";

const ROWS: [string, (c: CompareResponse["compounds"][number]) => string][] = [
  ["Formula", c => c.formula ?? "–"],
  ["Molecular weight", c => fmt(c.physchem.mol_weight, 2)],
  ["logP", c => fmt(c.physchem.logp)],
  ["TPSA", c => fmt(c.physchem.tpsa, 1)],
  ["H-bond donors", c => String(c.physchem.hbd)],
  ["H-bond acceptors", c => String(c.physchem.hba)],
  ["Rotatable bonds", c => String(c.physchem.rotatable_bonds)],
  ["Lipinski violations", c => String(c.physchem.lipinski_violations)],
];

export default function ComparePanel({ ids, onClose }: { ids: number[]; onClose: () => void }) {
  const [data, setData] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null); setError(null);
    compareCompounds(ids).then(setData).catch(e => setError(errorMessage(e)));
  }, [ids]);

  return (
    <Card title={`Compare ${ids.length} compounds`} right={<Btn variant="light" onClick={onClose}>Close</Btn>}>
      <ErrorBox message={error} />
      {!data && !error && <Spinner />}
      {data && (
        <div className="space-y-8 overflow-x-auto">
          <table className="w-full text-xs" aria-label="Property comparison">
            <thead>
              <tr><th className="text-left p-2 w-40" />
                {data.compounds.map(c => (
                  <th key={c.id} className="p-2 text-left align-top">
                    <MolThumb smiles={c.canonical_smiles} size={72} />
                    <div className="mt-2"><CompoundLink c={c} /></div><OriginBadge origin={c.origin} />
                  </th>))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map(([label, f]) => (
                <tr key={label} className="border-t border-black/5">
                  <td className="p-2 opacity-50">{label}</td>
                  {data.compounds.map(c => <td key={c.id} className="p-2 font-medium">{f(c)}</td>)}
                </tr>))}
            </tbody>
          </table>

          <div>
            <h3 className="text-[10px] font-bold tracking-widest uppercase opacity-50 mb-2">Pairwise Tanimoto (Morgan r=2)</h3>
            <table className="text-xs" aria-label="Tanimoto matrix">
              <tbody>
                {data.tanimoto_matrix.map((row, i) => (
                  <tr key={i}>
                    <th className="pr-3 text-left font-medium">{data.compounds[i].name || data.compounds[i].inchikey.slice(0, 8)}</th>
                    {row.map((v, j) => (
                      <td key={j} className="p-2 text-center rounded" style={{ background: `rgba(124,58,237,${v * 0.35})` }}>{v.toFixed(2)}</td>))}
                  </tr>))}
              </tbody>
            </table>
          </div>

          <div>
            <h3 className="text-[10px] font-bold tracking-widest uppercase opacity-50 mb-2">Target evidence</h3>
            {Object.keys(data.per_target).length === 0 ? (
              <p className="text-xs opacity-50">No measured or predicted target data for these compounds.</p>
            ) : Object.entries(data.per_target).map(([target, byCompound]) => (
              <table key={target} className="w-full text-xs mb-4" aria-label={`Evidence for ${target}`}>
                <thead><tr className="text-left"><th className="p-2">{target}</th>
                  {data.compounds.map(c => <th key={c.id} className="p-2">{c.name || c.inchikey.slice(0, 8)}</th>)}</tr></thead>
                <tbody>
                  <tr className="border-t border-black/5"><td className="p-2 opacity-50">Experimental (best)</td>
                    {data.compounds.map(c => { const e = byCompound[String(c.id)]?.experimental_best;
                      return <td key={c.id} className="p-2">{e ? <span className="text-emerald-700 font-bold">{e.type} {fmtNm(e.value_nm)} nM <span className="opacity-50 font-normal">({e.source_db})</span></span> : "–"}</td>; })}
                  </tr>
                  <tr className="border-t border-black/5"><td className="p-2 opacity-50">Predicted Kd (model)</td>
                    {data.compounds.map(c => { const p = byCompound[String(c.id)]?.latest_prediction;
                      return <td key={c.id} className="p-2">{p ? <span className="text-amber-700 font-bold">{fmtNm(p.predicted_kd_nm)} nM <span className="opacity-50 font-normal">(computational)</span></span> : "–"}</td>; })}
                  </tr>
                </tbody>
              </table>))}
          </div>
        </div>
      )}
    </Card>
  );
}
