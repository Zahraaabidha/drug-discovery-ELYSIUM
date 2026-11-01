# app/arangodb_client.py
import os

from arango import ArangoClient


def _settings():
    """Read settings lazily so .env / docker env are honoured, with
    ARANGO_URL or ARANGO_HOST+ARANGO_PORT, and ARANGO_USERNAME or ARANGO_USER."""
    host = os.getenv("ARANGO_HOST", "127.0.0.1")
    port = os.getenv("ARANGO_PORT", "8529")
    return {
        "url": os.getenv("ARANGO_URL") or f"http://{host}:{port}",
        "username": os.getenv("ARANGO_USERNAME") or os.getenv("ARANGO_USER", "root"),
        "password": os.getenv("ARANGO_PASSWORD", "changeme"),
        "db": os.getenv("ARANGO_DB_NAME", "elysium_kg"),
    }


def get_arango_db(create: bool = False):
    """Return a handle to the ELYSIUM ArangoDB database.
    With create=True the database is created first if it does not exist."""
    cfg = _settings()
    client = ArangoClient(hosts=cfg["url"])
    if create:
        sys_db = client.db("_system", username=cfg["username"], password=cfg["password"])
        if not sys_db.has_database(cfg["db"]):
            sys_db.create_database(cfg["db"])
    return client.db(cfg["db"], username=cfg["username"], password=cfg["password"])
