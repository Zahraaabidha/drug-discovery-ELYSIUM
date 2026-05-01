import { useEffect, useRef, useCallback } from "react";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";

// Register fcose once
try { cytoscape.use(fcose); } catch {}

interface GraphViewerProps {
  nodes: any[];
  edges: any[];
  mode?: string;
  maxNodes?: number;
  denseMode?: boolean;
  onNodeSelect?: (node: { id: string; label?: string; type?: string; data?: any } | null) => void;
  height?: number;
}

const shorten = (s: string, type: string, dense: boolean): string => {
  if (type === "targets") return s.length > 16 ? s.slice(0, 14) + "…" : s;
  if (type === "drugs") return s.length > 12 ? s.slice(0, 10) + "…" : s;
  if (dense) return s.length > 8 ? s.slice(0, 6) + "…" : s; // show short label in dense mode
  return ""; // molecules: no label in clean mode
};

export default function GraphViewer({
  nodes, edges, mode = "agent", maxNodes = 40, denseMode = false,
  onNodeSelect, height = 520
}: GraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const build = useCallback(() => {
    if (!containerRef.current) return;
    cyRef.current?.destroy();
    cyRef.current = null;

    if (!nodes?.length) return;

    const nodeIdSet = new Set<string>();
    let cyNodes: any[] = [];

    nodes.forEach((node: any) => {
      if (!node || typeof node !== "object") return;
      const raw = node.data ?? node;
      const nodeId: string = raw._id ?? raw.id ?? null;
      if (!nodeId) return;

      nodeIdSet.add(nodeId);
      if (raw._key) {
        nodeIdSet.add(raw._key);
        const col = nodeId.split("/")[0];
        if (col) nodeIdSet.add(`${col}/${raw._key}`);
      }

      const fullLabel: string = raw.label ?? raw.name ?? raw.symbol ?? raw.smiles ?? raw._key ?? nodeId;
      const type: string = raw.type ?? (nodeId.includes("/") ? nodeId.split("/")[0] : "molecules");
      const score: number | null = raw.score ?? null;

      cyNodes.push({
        data: { id: nodeId, label: shorten(fullLabel, type, denseMode), fullLabel, type, score },
        _type: type, _score: score ?? 0,
      });
    });

    // Limit molecule nodes — keep all targets/drugs, limit molecules by score
    const nonMol = cyNodes.filter(n => n._type !== "molecules");
    const molNodes = cyNodes
      .filter(n => n._type === "molecules")
      .sort((a, b) => b._score - a._score)
      .slice(0, Math.max(0, maxNodes - nonMol.length));
    cyNodes = [...nonMol, ...molNodes];

    const visibleIds = new Set(cyNodes.map(n => n.data.id));

    const cyEdges = edges
      .map((edge: any) => {
        if (!edge || typeof edge !== "object") return null;
        const raw = edge.data ?? edge;
        const source: string = raw._from ?? raw.source ?? null;
        const target: string = raw._to ?? raw.target ?? null;
        if (!source || !target) return null;
        if (!visibleIds.has(source) || !visibleIds.has(target)) return null;
        const edgeId: string = raw._id ?? raw.id ?? `${source}__${target}`;
        return { data: { id: edgeId, source, target, edgeType: raw.type ?? raw.label ?? "rel" } };
      })
      .filter(Boolean);

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...cyNodes, ...cyEdges],
      style: [
        // ── Base molecule node (no label) ──────────────────────────────
        {
          selector: "node",
          style: {
            "background-color": "#e5e7eb",
            "border-width": 1.5,
            "border-color": "#d1d5db",
            label: "",            // hidden by default
            width: 18,
            height: 18,
            "overlay-opacity": 0,
          }
        },
        // ── Target node ────────────────────────────────────────────────
        {
          selector: 'node[type="targets"]',
          style: {
            "background-color": "#111827",
            "border-color": "#111827",
            "border-width": 0,
            label: "data(label)",
            "font-size": "10px",
            "font-family": "Inter, sans-serif",
            "font-weight": "700",
            "text-valign": "center",
            "text-halign": "center",
            color: "#ffffff",
            width: 52,
            height: 52,
          }
        },
        // ── Drug node ──────────────────────────────────────────────────
        {
          selector: 'node[type="drugs"]',
          style: {
            "background-color": "#7c3aed",
            "border-color": "#6d28d9",
            "border-width": 0,
            label: "data(label)",
            "font-size": "8px",
            "font-family": "Inter, sans-serif",
            "font-weight": "600",
            "text-valign": "center",
            "text-halign": "center",
            color: "#ffffff",
            width: 38,
            height: 38,
          }
        },
        // ── High-score molecule (top quartile) ─────────────────────────
        {
          selector: "node[type='molecules'][score >= 0.75]",
          style: {
            "background-color": "#a78bfa",
            "border-color": "#7c3aed",
            width: 22,
            height: 22,
          }
        },
        {
          selector: "node[type='molecules'][score >= 0.5][score < 0.75]",
          style: {
            "background-color": "#c4b5fd",
            "border-color": "#a78bfa",
            width: 18,
            height: 18,
          }
        },
        // ── Selected ───────────────────────────────────────────────────
        {
          selector: "node:selected",
          style: {
            "background-color": "#7c3aed",
            "border-color": "#4c1d95",
            "border-width": 3,
            label: "data(label)",
            "font-size": "9px",
            "font-family": "Inter, sans-serif",
            "font-weight": "600",
            color: "#1e1b4b",
            "text-valign": "bottom",
            "text-margin-y": 6,
            width: 28,
            height: 28,
            "z-index": 999,
          }
        },
        {
          selector: 'node[type="targets"]:selected, node[type="drugs"]:selected',
          style: {
            "border-width": 3,
            "border-color": "#4c1d95",
            "text-valign": "center",
            "text-margin-y": 0,
            width: 56,
            height: 56,
          }
        },
        // ── Edges ──────────────────────────────────────────────────────
        {
          selector: "edge",
          style: {
            width: 1,
            "line-color": "#e5e7eb",
            "target-arrow-color": "#e5e7eb",
            "target-arrow-shape": "none",
            "curve-style": "haystack",
            opacity: 0.5,
          }
        },
        {
          selector: 'edge[edgeType="BINDS"]',
          style: {
            "line-color": "#ddd6fe",
            width: 1.5,
            opacity: 0.8,
            "curve-style": "haystack",
          }
        },
        {
          selector: 'edge[edgeType="SIMILAR_TO"]',
          style: {
            "line-color": "#d1fae5",
            "line-style": "dashed",
            "line-dash-pattern": [4, 4],
            opacity: 0.5,
            "curve-style": "haystack",
          }
        },
        // ── Hover ──────────────────────────────────────────────────────
        {
          selector: "node.hover",
          style: {
            "border-color": "#7c3aed",
            "border-width": 2,
            label: "data(fullLabel)",
            "font-size": "8px",
            "font-family": "Inter, sans-serif",
            color: "#4c1d95",
            "text-valign": "bottom",
            "text-margin-y": 5,
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.9,
            "text-background-padding": "2px",
            "text-max-width": "120px",
            "text-wrap": "ellipsis",
            "z-index": 500,
          }
        },
      ],
      layout: denseMode ? {
        name: "cose",
        animate: false,
        padding: 20,
        nodeRepulsion: () => 2000,
        idealEdgeLength: () => 40,
        edgeElasticity: () => 100,
        gravity: 1,
        numIter: 800,
      } as any : {
        name: "fcose",
        quality: "proof",
        randomize: true,
        animate: false,
        padding: 60,
        nodeSeparation: 120,
        idealEdgeLength: 100,
        edgeElasticity: 0.45,
        nodeRepulsion: 6500,
        gravity: 0.25,
        gravityRange: 3.8,
        numIter: 2500,
        tile: true,
        tilingPaddingVertical: 20,
        tilingPaddingHorizontal: 20,
      } as any,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      minZoom: 0.15,
      maxZoom: 4,
      wheelSensitivity: 0.3,
    });

    // Hover: show label on mouseover
    cy.on("mouseover", "node", evt => {
      evt.target.addClass("hover");
    });
    cy.on("mouseout", "node", evt => {
      evt.target.removeClass("hover");
    });

    // Click to select / inspect
    cy.on("tap", "node", evt => {
      const n = evt.target;
      onNodeSelect?.({
        id: n.data("id"),
        label: n.data("fullLabel"),
        type: n.data("type"),
        data: n.data(),
      });
    });

    cy.on("tap", evt => {
      if (evt.target === cy) onNodeSelect?.(null);
    });

    cyRef.current = cy;
  }, [nodes, edges, mode, maxNodes, onNodeSelect]);

  useEffect(() => {
    build();
    return () => { cyRef.current?.destroy(); cyRef.current = null; };
  }, [build]);

  if (!nodes?.length) {
    return (
      <div style={{ height }} className="flex items-center justify-center rounded-2xl border border-neutral-100 bg-neutral-50">
        <div className="text-center">
          <div className="w-10 h-10 rounded-xl bg-neutral-100 flex items-center justify-center mx-auto mb-3">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="19" r="2"/>
              <path d="M7 11.5l10-5M7 12.5l10 5"/>
            </svg>
          </div>
          <p className="text-sm text-neutral-400 font-medium">No graph data</p>
          <p className="text-xs text-neutral-300 mt-1">Run a discovery first to populate the graph</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ position: "relative" }}>
      <div ref={containerRef}
        style={{ width: "100%", height, borderRadius: "16px", background: "#fafafa", border: "1px solid #f3f4f6" }}/>
      {/* Zoom hint */}
      <div className="absolute bottom-3 left-3 flex items-center gap-1.5 bg-white/80 backdrop-blur-sm border border-neutral-100 rounded-lg px-2.5 py-1.5">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/><path d="M11 8v6M8 11h6"/>
        </svg>
        <span className="text-[9px] text-neutral-400 font-medium">Scroll to zoom · drag to pan · click node to inspect</span>
      </div>
    </div>
  );
}