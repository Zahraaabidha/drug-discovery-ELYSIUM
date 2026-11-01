import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import GraphViewer from "../components/GraphViewer";
import { API_BASE_URL, API_KEY } from "../api/client";

export default function TargetGraphPage() {
  const { targetId } = useParams<{ targetId: string }>();
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [depth, setDepth] = useState(2);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchGraph = async (signal: AbortSignal) => {
    if (!targetId) {
      setNodes([]);
      setEdges([]);
      return;
    }
    setError(null);
    console.log("[TargetGraph] API base", API_BASE_URL);
    console.log("[TargetGraph] fetching", { targetId, depth });
    try {
      const url = `${API_BASE_URL}/graph-view/target/${encodeURIComponent(targetId)}?depth=${depth}`;
      const res = await fetch(url, { signal, headers: { "X-API-KEY": API_KEY } });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const data = await res.json();
      console.log("[TargetGraph] raw response", data);
      const safeNodes = Array.isArray(data?.nodes) ? data.nodes : [];
      const safeEdges = Array.isArray(data?.edges) ? data.edges : [];
      console.log("[TargetGraph] parsed nodes", safeNodes.length);
      console.log("[TargetGraph] parsed edges", safeEdges.length);
      setNodes(safeNodes);
      setEdges(safeEdges);
    } catch (err: any) {
      if (err?.name === "AbortError") {
        return;
      }
      console.error("[TargetGraph] fetch error", err);
      setError(err?.message || "Failed to load graph");
      setNodes([]);
      setEdges([]);
    }
  };

  useEffect(() => {
    if (!targetId) return;
    setLoading(true);
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const timeout = setTimeout(() => {
      fetchGraph(controller.signal)
        .catch((err) => {
          if (err?.name !== "AbortError") {
            console.error("[TargetGraph] unexpected error", err);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 200);
    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [targetId, depth]);

  return (
    <section className="max-w-6xl mx-auto px-6 py-10 space-y-6">
      <header>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Target view</p>
        <h1 className="text-3xl font-serif text-slate-900">{targetId}</h1>
        <div className="mt-4 flex flex-wrap items-center gap-4">
          <label className="text-sm text-slate-600">
            Depth {depth}
            <input
              type="range"
              min={1}
              max={4}
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              className="mt-2"
            />
          </label>
          {loading && <span className="text-sm text-slate-500">Loading…</span>}
          {error && <span className="text-sm text-amber-600">{error}</span>}
        </div>
      </header>

      <div className="flex flex-col gap-3">
        <GraphViewer nodes={nodes} edges={edges} />
        {!loading && !error && ((!Array.isArray(nodes) || nodes.length === 0) && (!Array.isArray(edges) || edges.length === 0)) && (
          <p className="text-sm text-slate-500">No graph data available for this target.</p>
        )}
      </div>
    </section>
  );
}
