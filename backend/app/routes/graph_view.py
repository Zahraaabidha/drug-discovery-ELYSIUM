#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\routes\graph_view.py
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import logging
from app.arangodb_client import get_arango_db

log = logging.getLogger(__name__)

router = APIRouter(prefix="/graph-view", tags=["graph"])


def _empty(target_id: str, depth: int):
    return JSONResponse(content={
        "nodes": [],
        "edges": [],
        "metadata": {"target": target_id, "depth": depth}
    })


def _serialize_doc(doc) -> dict:
    """Convert ArangoDB cursor document to a plain dict, explicitly preserving _id."""
    d = dict(doc)
    # Explicitly copy system fields that python-arango sometimes strips
    for field in ("_id", "_key", "_from", "_to"):
        if hasattr(doc, field) and field not in d:
            d[field] = getattr(doc, field)
    return d


@router.get("/target/{target_id}")
def get_target_graph_view(target_id: str, depth: int = Query(2, ge=1, le=5)):
    try:
        db = get_arango_db()
    except Exception as exc:
        print(f"[graph_view] DB connection failed: {exc}")
        return _empty(target_id, depth)

    # ── 1. Resolve target ────────────────────────────────────────────────
    try:
        cur = db.aql.execute(
            """
            FOR t IN targets
                FILTER t._key == @tid OR t.symbol == @tid OR t.name == @tid
                LIMIT 1
                RETURN {
                    id:         t._id,
                    _id:        t._id,
                    _key:       t._key,
                    name:       t.name,
                    symbol:     t.symbol,
                    uniprot_id: t.uniprot_id,
                    type:       "targets"
                }
            """,
            bind_vars={"tid": target_id},
        )
        target_docs = list(cur)
    except Exception as exc:
        print(f"[graph_view] Target lookup failed: {exc}")
        return _empty(target_id, depth)

    if not target_docs:
        print(f"[graph_view] Target '{target_id}' not found")
        return _empty(target_id, depth)

    target_doc = dict(target_docs[0])
    target_arango_id: str = target_doc["_id"]
    print(f"[graph_view] Target resolved: {target_arango_id}")
    print(f"[graph_view] Target doc: {target_doc}")

    nodes: dict[str, dict] = {target_arango_id: target_doc}
    edges: list[dict] = []

    # ── 2. Molecules bound to target ─────────────────────────────────────
    try:
        cur = db.aql.execute(
            """
            FOR e IN binds
                FILTER e._to == @tid OR e._from == @tid
                LET mol_id = (e._to == @tid) ? e._from : e._to
                FOR m IN molecules
                    FILTER m._id == mol_id
                    RETURN {
                        mol: {
                            id:        m._id,
                            _id:       m._id,
                            _key:      m._key,
                            smiles:    m.smiles,
                            score:     m.score,
                            run_id:    m.run_id,
                            target_id: m.target_id,
                            type:      "molecules"
                        },
                        edge: {
                            id:    e._id,
                            _id:   e._id,
                            _key:  e._key,
                            _from: e._from,
                            _to:   e._to,
                            type:  "binds",
                            evidence_type: e.evidence_type,
                            predicted_kd_nm: e.predicted_kd_nm,
                            model: e.model
                        }
                    }
            """,
            bind_vars={"tid": target_arango_id},
        )
        mol_rows = list(cur)
        print(f"[graph_view] Found {len(mol_rows)} bound molecules")
        if mol_rows:
            print(f"[graph_view] Sample mol: {dict(mol_rows[0]['mol'])}")
    except Exception as exc:
        print(f"[graph_view] Molecule query failed: {exc}")
        mol_rows = []

    mol_ids: list[str] = []
    for row in mol_rows:
        mol = dict(row["mol"])
        edge = dict(row["edge"])
        if mol.get("_id"):
            nodes[mol["_id"]] = mol
            mol_ids.append(mol["_id"])
        if edge.get("_from") and edge.get("_to"):
            edges.append(edge)

    # ── 2b. Experimentally measured compounds (ChEMBL / BindingDB) ──────
    try:
        cur = db.aql.execute(
            """
            FOR e IN binds
                FILTER e._to == @tid AND e.evidence_type == "experimental"
                SORT e.best_value_nm ASC
                LIMIT 25
                FOR c IN compounds
                    FILTER c._id == e._from
                    RETURN {
                        node: { id: c._id, _id: c._id, _key: c._key, smiles: c.smiles,
                                name: c.name, origin: c.origin, type: "compounds" },
                        edge: { id: e._id, _id: e._id, _key: e._key, _from: e._from, _to: e._to,
                                type: "binds", evidence_type: e.evidence_type,
                                best_value_nm: e.best_value_nm, best_type: e.best_type,
                                n_measurements: e.n_measurements }
                    }
            """,
            bind_vars={"tid": target_arango_id},
        )
        for row in cur:
            node, edge = dict(row["node"]), dict(row["edge"])
            nodes[node["_id"]] = node
            edges.append(edge)
    except Exception as exc:
        log.warning("Experimental compound query failed: %s", exc)

    # ── 3. Similar drugs ─────────────────────────────────────────────────
    if mol_ids and depth >= 2:
        try:
            cur = db.aql.execute(
                """
                FOR mol_id IN @mol_ids
                    FOR e IN similar_to
                        FILTER e._from == mol_id OR e._to == mol_id
                        LET drug_id = (e._from == mol_id) ? e._to : e._from
                        FOR d IN drugs
                            FILTER d._id == drug_id
                            RETURN {
                                drug: {
                                    id:   d._id,
                                    _id:  d._id,
                                    _key: d._key,
                                    name: d.name,
                                    type: "drugs"
                                },
                                edge: {
                                    id:    e._id,
                                    _id:   e._id,
                                    _key:  e._key,
                                    _from: e._from,
                                    _to:   e._to,
                                    type:  "similar_to"
                                }
                            }
                """,
                bind_vars={"mol_ids": mol_ids},
            )
            sim_rows = list(cur)
            print(f"[graph_view] Found {len(sim_rows)} similar drugs")
        except Exception as exc:
            print(f"[graph_view] Similarity query failed: {exc}")
            sim_rows = []

        for row in sim_rows:
            drug = dict(row["drug"])
            edge = dict(row["edge"])
            if drug.get("_id"):
                nodes[drug["_id"]] = drug
            if edge.get("_from") and edge.get("_to"):
                edges.append(edge)

    # ── 4. Filter edges so both endpoints exist ──────────────────────────
    node_id_set = set(nodes.keys())
    valid_edges = [
        e for e in edges
        if e.get("_from") in node_id_set and e.get("_to") in node_id_set
    ]

    node_list = list(nodes.values())
    print(f"[graph_view] Returning {len(node_list)} nodes, {len(valid_edges)} edges")
    if node_list:
        print(f"[graph_view] First node: {node_list[0]}")

    import json
    payload = json.dumps({
        "nodes": node_list,
        "edges": valid_edges,
        "metadata": {"target": target_id, "depth": depth},
    })
    return JSONResponse(content=json.loads(payload))