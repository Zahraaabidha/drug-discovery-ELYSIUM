import { vi } from "vitest";

export type Handler = (url: URL, init?: RequestInit) => unknown | { __status: number; body: unknown };
export interface Call { method: string; path: string; query: URLSearchParams; body: any; }

/** Replace global fetch with a router. Keys are "METHOD /path" (exact path match). */
export function mockApi(routes: Record<string, Handler>) {
  const calls: Call[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === "string" ? input : input.toString());
    const method = (init?.method ?? "GET").toUpperCase();
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path: url.pathname, query: url.searchParams, body });
    const handler = routes[`${method} ${url.pathname}`];
    if (!handler) return new Response(JSON.stringify({ detail: `unmocked ${method} ${url.pathname}` }), { status: 404, headers: { "content-type": "application/json" } });
    const out: any = handler(url, init);
    const status = out && typeof out === "object" && "__status" in out ? out.__status : 200;
    const payload = out && typeof out === "object" && "__status" in out ? out.body : out;
    return new Response(JSON.stringify(payload), { status, headers: { "content-type": "application/json" } });
  }));
  return calls;
}

export const physchem = (over: Partial<any> = {}) => ({
  mol_weight: 180.16, logp: 1.31, tpsa: 63.6, hbd: 1, hba: 3, rotatable_bonds: 3, heavy_atoms: 13, ring_count: 1,
  lipinski_violations: 0, lipinski_pass: true, ...over,
});

export const compound = (over: Partial<any> = {}) => ({
  id: 1, name: "Aspirin", inchikey: "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", canonical_smiles: "CC(=O)Oc1ccccc1C(=O)O",
  origin: "reference", formula: "C9H8O4", physchem: physchem(), n_experimental: 0, n_predictions: 0,
  sources: [{ source_db: "elysium_reference", external_id: "aspirin" }], generation_method: null, generation_run_id: null, ...over,
});

export const stats = (over: Partial<any> = {}) => ({
  compounds: 3, by_origin: { reference: 2, external: 0, generated: 1 }, by_source: { elysium_reference: 2, elysium_generator: 1 },
  bioactivities: 0, predictions: 1, collections: 0, annotations: 0, supported_targets: ["EGFR", "DRD2"],
  index: { size: 3, embeddings: false }, ...over,
});
