from .arangodb_client import get_arango_db

GRAPH_NAME = "elysium_graph"
VERTEX_COLLECTIONS = ["targets", "drugs", "diseases", "molecules"]
EDGE_DEFINITIONS = [
    {"edge_collection": "binds", "from_vertex_collections": ["drugs", "molecules"], "to_vertex_collections": ["targets"]},
    {"edge_collection": "treats", "from_vertex_collections": ["drugs"], "to_vertex_collections": ["diseases"]},
    {"edge_collection": "associated_with", "from_vertex_collections": ["targets"], "to_vertex_collections": ["diseases"]},
    {"edge_collection": "similar_to", "from_vertex_collections": ["molecules"], "to_vertex_collections": ["drugs"]},
]


def init_arango_schema():
    """Create the database, collections and the named 'elysium_graph' graph."""
    db = get_arango_db(create=True)

    for name in VERTEX_COLLECTIONS:
        if not db.has_collection(name):
            db.create_collection(name)
    for d in EDGE_DEFINITIONS:
        if not db.has_collection(d["edge_collection"]):
            db.create_collection(d["edge_collection"], edge=True)

    if not db.has_graph(GRAPH_NAME):
        db.create_graph(GRAPH_NAME, edge_definitions=EDGE_DEFINITIONS)
    return db


if __name__ == "__main__":
    init_arango_schema()
    print("ArangoDB schema ready")
