import { apiFetch } from "./client";

/* ─── ADMET ─────────────────────────────────────────────────────────────── */
export interface ADMET {
  molecular_weight: number; logp: number; hbd: number; hba: number;
  rotatable_bonds: number; tpsa: number; lipinski_violations: number; lipinski_pass: boolean;
}

/* ─── Molecules ─────────────────────────────────────────────────────────── */
export interface SimilarDrug {
  name: string; smiles: string; indication: string | null;
  similarity: number | null; semantic_similarity: number | null;
}
export interface Molecule {
  smiles: string; score: number; source: string; notes: string | null;
  similar_drug: SimilarDrug | null; similar_drug_semantic: SimilarDrug | null;
  admet: ADMET | null;
}

/* ─── Discovery ─────────────────────────────────────────────────────────── */
export interface DiscoverRequest {
  target_id: string; num_molecules: number; lipinski_only?: boolean;
}
export interface DiscoverResponse {
  run_id: string; target_id: string; num_molecules: number; molecules: Molecule[];
}

/* ─── Batch discovery ───────────────────────────────────────────────────── */
export interface BatchDiscoverRequest {
  targets: string[]; num_molecules: number; lipinski_only?: boolean;
}
export interface BatchDiscoverResponse {
  runs: Array<{ target_id: string; run_id: string; num_molecules: number }>;
}

/* ─── Runs ──────────────────────────────────────────────────────────────── */
export interface RunSummary {
  run_id: string; target_id: string; num_molecules: number; created_at: string;
}
export interface RunsListResponse { runs: RunSummary[]; }

/* ─── Graph ─────────────────────────────────────────────────────────────── */
export interface TargetGraphEntry {
  run_id: string; molecule_index: number; smiles: string;
  score: number; similar_drug: SimilarDrug | null;
}
export interface TargetGraphResponse { target_id: string; molecules: TargetGraphEntry[]; }
export interface DrugGraphEntry {
  target_id: string; run_id: string; molecule_index: number; smiles: string; score: number;
}
export interface DrugGraphResponse { drug_name: string; molecules: DrugGraphEntry[]; }

/* ─── Agent / Chat ──────────────────────────────────────────────────────── */
export interface ChatMessage {
  role: "user" | "assistant"; content: string;
}
export interface AgentTool {
  name: string; args?: Record<string, any>; result?: any;
}
export interface AgentChatRequest {
  prompt: string;
  session_id?: string;
}
export interface AgentChatResponse {
  answer: string;
  session_id: string;
  steps?: string[];
  evidence?: Array<{ tool: string; input: any; result: any }>;
  history?: Array<{ role: string; content: string }>;
}

/* ─── Health ────────────────────────────────────────────────────────────── */
export interface HealthResponse {
  status: string; version?: string; db?: string; arango?: string;
}

/* ═══════════════════════════════════════════════════════════════════════════
   API FUNCTIONS
═══════════════════════════════════════════════════════════════════════════ */

// Discovery
export const discoverMolecules = (p: DiscoverRequest): Promise<DiscoverResponse> =>
  apiFetch("/discover", { method: "POST", body: JSON.stringify(p) });

export const batchDiscover = (p: BatchDiscoverRequest): Promise<BatchDiscoverResponse> =>
  apiFetch("/discover/batch", { method: "POST", body: JSON.stringify(p) });

// Runs
export const listRuns = (): Promise<RunsListResponse> => apiFetch("/runs");
export const getRun = (id: string): Promise<DiscoverResponse> => apiFetch(`/runs/${id}`);
export const deleteRun = (id: string): Promise<void> => apiFetch(`/runs/${id}`, { method: "DELETE" });
export const exportRunCSV = (id: string): string =>
  `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/runs/${id}/export`;

// Graph
export const getTargetGraph = (t: string): Promise<TargetGraphResponse> =>
  apiFetch(`/graph/target/${encodeURIComponent(t)}`);
export const getDrugGraph = (d: string): Promise<DrugGraphResponse> =>
  apiFetch(`/graph/drug/${encodeURIComponent(d)}`);

// Agent
export const agentChat = (p: AgentChatRequest): Promise<AgentChatResponse> =>
  apiFetch("/chat/message", { method: "POST", body: JSON.stringify(p) });

// Health
export const getHealth = (): Promise<HealthResponse> => apiFetch("/health");