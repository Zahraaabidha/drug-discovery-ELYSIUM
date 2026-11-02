from .arangodb_client import get_arango_db

GRAPH_NAME = "elysium_graph"

# Vertex collections
#   targets    - supported protein targets (UniProt)
#   drugs      - named reference drugs (key = lower-case name)
#   compounds  - registry compounds with experimental evidence (key = InChIKey)
#   molecules  - ELYSIUM-generated molecules (key = <run_id>_<index>)
#   pathways   - Reactome pathways
#   diseases   - kept for backward compatibility; only populated from cited sources
VERTEX_COLLECTIONS = ["targets", "drugs", "compounds", "molecules", "pathways", "diseases"]

# Every edge carries `evidence_type`
# ("experimental" | "computational_prediction" | "database_annotation") plus provenance.
EDGE_DEFINITIONS = [
    {"edge_collection": "binds",
     "from_vertex_collections": ["drugs", "molecules", "compounds"], "to_vertex_collections": ["targets"]},
    {"edge_collection": "participates_in",
     "from_vertex_collections": ["targets"], "to_vertex_collections": ["pathways"]},
    {"edge_collection": "similar_to",
     "from_vertex_collections": ["molecules"], "to_vertex_collections": ["drugs", "compounds"]},
    {"edge_collection": "treats",
     "from_vertex_collections": ["drugs"], "to_vertex_collections": ["diseases"]},
    {"edge_collection": "associated_with",
     "from_vertex_collections": ["targets"], "to_vertex_collections": ["diseases"]},
]


def init_arango_schema():
    """Create the database, collections and the named 'elysium_graph' graph (idempotent;
    upgrades graphs created by earlier versions with the new collections/definitions)."""
    db = get_arango_db(create=True)

    for name in VERTEX_COLLECTIONS:
        if not db.has_collection(name):
            db.create_collection(name)
    for d in EDGE_DEFINITIONS:
        if not db.has_collection(d["edge_collection"]):
            db.create_collection(d["edge_collection"], edge=True)

    if not db.has_graph(GRAPH_NAME):
        db.create_graph(GRAPH_NAME, edge_definitions=EDGE_DEFINITIONS)
    else:
        graph = db.graph(GRAPH_NAME)
        existing = {d["edge_collection"]: d for d in graph.edge_definitions()}
        for d in EDGE_DEFINITIONS:
            cur = existing.get(d["edge_collection"])
            if cur is None:
                graph.create_edge_definition(**d)
            elif (set(cur["from_vertex_collections"]) != set(d["from_vertex_collections"])
                  or set(cur["to_vertex_collections"]) != set(d["to_vertex_collections"])):
                graph.replace_edge_definition(**d)
    return db


if __name__ == "__main__":
    init_arango_schema()
    print("ArangoDB schema ready")
