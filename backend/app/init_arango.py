from .arangodb_client import get_arango_db

def init_arango_schema():
    db = get_arango_db()

    for name in ["targets", "drugs", "diseases", "molecules"]:
        if not db.has_collection(name):
            db.create_collection(name)

    for name in ["binds", "treats", "associated_with", "similar_to"]:
        if not db.has_collection(name):
            db.create_collection(name, edge=True)

if __name__ == "__main__":
    init_arango_schema()
