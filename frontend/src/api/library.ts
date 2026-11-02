import { apiFetch } from "./client";

/* ─── Types ─────────────────────────────────────────────────────────────── */
export type Origin = "reference" | "external" | "generated";

export interface PhysChem {
  mol_weight: number; logp: number; tpsa: number; hbd: number; hba: number;
  rotatable_bonds: number; heavy_atoms: number; ring_count: number;
  lipinski_violations: number; lipinski_pass: boolean;
}
export interface SourceRef { source_db: string; external_id: string; }
export interface CompoundSummary {
  id: number; name: string | null; inchikey: string; canonical_smiles: string; origin: Origin;
  formula: string | null; physchem: PhysChem; n_experimental: number; n_predictions: number;
  sources: SourceRef[]; generation_method: string | null; generation_run_id: string | null;
}
export interface CompoundList { total: number; limit: number; offset: number; items: CompoundSummary[]; }

export interface Experimental {
  id: number; target: string; uniprot_id: string | null; source_db: string; external_id: string;
  type: string; relation: string | null; value_nm: number; pvalue: number | null;
  assay_ref: string | null; evidence_type: string; retrieved_at: string;
}
export interface PredictionRow {
  id: number; run_id: string | null; target: string; uniprot_id: string | null; model: string;
  model_version: string | null; predicted_kd: number; units: string; pkd: number | null;
  evidence_type: string; created_at: string;
}
export interface CompoundProfile extends CompoundSummary {
  original_smiles: string; created_at: string;
  sources_detail: { source_db: string; external_id: string; original_smiles: string; url: string | null; retrieved_at: string; note: string | null }[];
  experimental_bioactivity: Experimental[];
  predictions: PredictionRow[];
  annotations: { id: number; author: string | null; text: string; created_at: string }[];
  collections: { id: number; name: string }[];
  evidence_notice: string;
}

export interface Filters {
  q?: string; origin?: Origin | ""; source_db?: string;
  min_mw?: number; max_mw?: number; min_logp?: number; max_logp?: number;
  max_tpsa?: number; max_hbd?: number; max_hba?: number; max_rotatable_bonds?: number;
  lipinski_pass?: boolean; has_experimental?: boolean; has_prediction?: boolean;
  target?: string; collection_id?: number; sort?: string; order?: "asc" | "desc";
  limit?: number; offset?: number;
}

export interface Stats {
  compounds: number; by_origin: Record<string, number>; by_source: Record<string, number>;
  bioactivities: number; predictions: number; collections: number; annotations: number;
  supported_targets: string[]; index: { size: number; embeddings: boolean };
}
export interface SimilarityHit { similarity: number; method: string; compound: CompoundSummary; }
export interface SimilarityResponse {
  query_smiles: string; k: number; registry_size: number;
  results: { fingerprint?: SimilarityHit[]; embedding?: SimilarityHit[] };
  notes: Record<string, string>;
}
export interface CompareResponse {
  compounds: CompoundSummary[]; tanimoto_matrix: number[][];
  per_target: Record<string, Record<string, {
    experimental_best: { type: string; value_nm: number; source_db: string } | null;
    latest_prediction: { predicted_kd_nm: number; pkd: number; model: string } | null;
  }>>;
}
export interface CollectionRow { id: number; name: string; description: string | null; size: number; }
export interface EvaluationReport {
  id: number; kind: string; created_at: string; parameters: any; dataset: any; metrics: any; limitations: string;
}
export interface TargetRow { symbol: string; uniprot_id: string; experimental_measurements: number; predictions: number; }

/* ─── Helpers ───────────────────────────────────────────────────────────── */
export function buildQuery(params: Record<string, unknown>): string {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "" || (typeof v === "number" && Number.isNaN(v))) return;
    sp.set(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/** Turn an API error body ({"detail": ...}) into a readable message. */
export function errorMessage(e: unknown): string {
  const raw = e instanceof Error ? e.message : String(e);
  try {
    const j = JSON.parse(raw);
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) return j.detail.map((d: any) => d.msg ?? JSON.stringify(d)).join("; ");
    if (j.detail?.message) return j.detail.message;
  } catch { /* not JSON */ }
  return raw;
}

const post = (path: string, body: unknown) => apiFetch(path, { method: "POST", body: JSON.stringify(body) });

/* ─── API ───────────────────────────────────────────────────────────────── */
export const getLibraryStats = (): Promise<Stats> => apiFetch("/library/stats");
export const getLibraryTargets = (): Promise<TargetRow[]> => apiFetch("/library/targets");
export const listCompounds = (f: Filters): Promise<CompoundList> => apiFetch(`/library/compounds${buildQuery(f as any)}`);
export const getCompound = (id: number): Promise<CompoundProfile> => apiFetch(`/library/compounds/${id}`);
export const addCompound = (smiles: string, name?: string) => post("/library/compounds", { smiles, name: name || undefined });
export const similaritySearch = (body: { smiles?: string; compound_id?: number; k: number; method: string; origin?: string }): Promise<SimilarityResponse> =>
  post("/library/similarity", body);
export const compareCompounds = (compound_ids: number[]): Promise<CompareResponse> => post("/library/compare", { compound_ids });

export const listCollections = (): Promise<CollectionRow[]> => apiFetch("/library/collections");
export const createCollection = (name: string, description?: string) => post("/library/collections", { name, description });
export const deleteCollection = (id: number) => apiFetch(`/library/collections/${id}`, { method: "DELETE" });
export const addToCollection = (collectionId: number, compoundId: number) =>
  post(`/library/collections/${collectionId}/items`, { compound_id: compoundId });
export const removeFromCollection = (collectionId: number, compoundId: number) =>
  apiFetch(`/library/collections/${collectionId}/items/${compoundId}`, { method: "DELETE" });

export const addAnnotation = (compoundId: number, text: string, author?: string) =>
  post(`/library/compounds/${compoundId}/annotations`, { text, author: author || undefined });
export const deleteAnnotation = (id: number) => apiFetch(`/library/annotations/${id}`, { method: "DELETE" });

export const importPubChem = (name: string) => post("/library/import/pubchem", { name });
export const importTarget = (target: string, sources: string[], max_records: number) =>
  post("/library/import/target", { target, sources, max_records });
export const syncKnowledgeGraph = (target: string) => post("/library/kg/sync", { target });

export const runEvaluation = (kind: "generation" | "similarity" | "dti", body: any): Promise<EvaluationReport> =>
  post(`/evaluation/${kind}`, body);
export const listEvaluations = (kind?: string): Promise<EvaluationReport[]> => apiFetch(`/evaluation/reports${buildQuery({ kind })}`);
export const getSupportedTargets = (): Promise<{ symbol: string; uniprot_id: string }[]> => apiFetch("/targets");
