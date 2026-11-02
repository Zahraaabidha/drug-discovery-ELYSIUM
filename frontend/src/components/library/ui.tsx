import React from "react";
import { Link } from "react-router-dom";
import { API_BASE_URL } from "../../api/client";
import type { CompoundSummary, Origin } from "../../api/library";

export const ORIGIN_STYLE: Record<Origin, { label: string; cls: string; title: string }> = {
  reference: { label: "Reference", cls: "bg-black text-white", title: "Known drug / curated reference compound" },
  external: { label: "External", cls: "bg-emerald-50 text-emerald-700 border border-emerald-200", title: "Imported from PubChem / ChEMBL / BindingDB or added by a user" },
  generated: { label: "Generated", cls: "bg-amber-50 text-amber-700 border border-amber-200", title: "Produced by an ELYSIUM generator (computational, not synthesised)" },
};

export const OriginBadge: React.FC<{ origin: Origin }> = ({ origin }) => {
  const s = ORIGIN_STYLE[origin];
  return (
    <span title={s.title} data-testid="origin-badge"
      className={`inline-block text-[9px] font-bold tracking-widest uppercase px-2.5 py-1 rounded-full ${s.cls}`}>
      {s.label}
    </span>
  );
};

export const EvidenceBadge: React.FC<{ kind: "experimental" | "computational_prediction" | string }> = ({ kind }) => (
  kind === "experimental"
    ? <span className="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">Experimental</span>
    : <span title="Model output - not experimental confirmation"
        className="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">Predicted</span>
);

export const Card: React.FC<{ title?: string; right?: React.ReactNode; className?: string; children: React.ReactNode }> = ({ title, right, className = "", children }) => (
  <section className={`bg-white rounded-[28px] border border-black/5 p-6 ${className}`}>
    {(title || right) && (
      <div className="flex items-center justify-between mb-4">
        {title && <h2 className="text-[10px] font-bold tracking-widest uppercase opacity-50">{title}</h2>}
        {right}
      </div>
    )}
    {children}
  </section>
);

export const Label: React.FC<{ children: React.ReactNode; htmlFor?: string }> = ({ children, htmlFor }) => (
  <label htmlFor={htmlFor} className="block text-[9px] font-bold tracking-widest uppercase opacity-40 mb-1">{children}</label>
);

const inputCls = "w-full bg-[#F8F9FA] border border-black/5 rounded-xl py-2 px-3 text-xs font-medium focus:outline-none focus:border-black/20";

export const TextInput: React.FC<React.InputHTMLAttributes<HTMLInputElement>> = (props) => (
  <input {...props} className={`${inputCls} ${props.className ?? ""}`} />
);

export const Select: React.FC<React.SelectHTMLAttributes<HTMLSelectElement>> = (props) => (
  <select {...props} className={`${inputCls} ${props.className ?? ""}`} />
);

/** Numeric input that reports `undefined` when empty (so the filter is simply not sent). */
export const NumInput: React.FC<{ id: string; label: string; value: number | undefined; onChange: (v: number | undefined) => void; step?: number }> =
  ({ id, label, value, onChange, step = 1 }) => (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <TextInput id={id} type="number" step={step} value={value ?? ""} placeholder="any"
        onChange={e => onChange(e.target.value === "" ? undefined : Number(e.target.value))} />
    </div>
  );

export const Btn: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "dark" | "light" | "danger" }> = ({ variant = "dark", className = "", ...p }) => {
  const v = variant === "dark" ? "bg-black text-white hover:bg-black/80" : variant === "danger" ? "bg-red-50 text-red-600 hover:bg-red-100 border border-red-100" : "bg-white border border-black/10 hover:bg-black/5";
  return <button {...p} className={`px-4 py-2 rounded-full text-[10px] font-bold tracking-widest uppercase transition-all disabled:opacity-40 disabled:cursor-not-allowed ${v} ${className}`} />;
};

export const ErrorBox: React.FC<{ message: string | null }> = ({ message }) =>
  message ? <div role="alert" className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-2xl px-4 py-3 whitespace-pre-wrap">{message}</div> : null;

export const Spinner: React.FC<{ label?: string }> = ({ label = "Loading…" }) => (
  <div className="flex items-center gap-2 text-xs opacity-50 py-6" role="status">
    <div className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />{label}
  </div>
);

export const MolThumb: React.FC<{ smiles: string; size?: number }> = ({ smiles, size = 56 }) => (
  <img src={`${API_BASE_URL}/molecule/image?smiles=${encodeURIComponent(smiles)}`} alt="structure" width={size} height={size}
    loading="lazy" className="rounded-xl border border-black/5 bg-white object-contain"
    style={{ width: size, height: size }} onError={e => { (e.target as HTMLImageElement).style.visibility = "hidden"; }} />
);

export const fmt = (v: number | null | undefined, d = 2) => (v === null || v === undefined ? "–" : v.toFixed(d));
export const fmtNm = (v: number) => (v >= 100 ? v.toFixed(0) : v >= 1 ? v.toFixed(1) : v.toPrecision(2));

export const PropChips: React.FC<{ c: CompoundSummary }> = ({ c }) => (
  <div className="flex flex-wrap gap-1.5 text-[10px]">
    {[["MW", fmt(c.physchem.mol_weight, 1)], ["logP", fmt(c.physchem.logp)], ["TPSA", fmt(c.physchem.tpsa, 1)],
      ["HBD", String(c.physchem.hbd)], ["HBA", String(c.physchem.hba)], ["RotB", String(c.physchem.rotatable_bonds)]].map(([k, v]) => (
      <span key={k} className="bg-[#F8F9FA] border border-black/5 rounded-lg px-2 py-0.5"><span className="opacity-40">{k}</span> <b>{v}</b></span>
    ))}
    <span className={`rounded-lg px-2 py-0.5 border ${c.physchem.lipinski_pass ? "bg-green-50 border-green-100 text-green-700" : "bg-red-50 border-red-100 text-red-600"}`}>
      Lipinski {c.physchem.lipinski_pass ? "pass" : `fail (${c.physchem.lipinski_violations})`}
    </span>
  </div>
);

export const CompoundLink: React.FC<{ c: Pick<CompoundSummary, "id" | "name" | "inchikey"> }> = ({ c }) => (
  <Link to={`/library/${c.id}`} className="font-bold text-xs hover:underline">{c.name || c.inchikey.slice(0, 14)}</Link>
);
