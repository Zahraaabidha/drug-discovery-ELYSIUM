# app/arangodb_client.py

from arango import ArangoClient
import os

# For now we read settings directly from environment variables.
# This avoids importing anything from core.config so the backend can
# run even if Arango is not set up yet.
ARANGO_URL = os.getenv("ARANGO_URL", "http://127.0.0.1:8529")
ARANGO_USERNAME = os.getenv("ARANGO_USERNAME", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "changeme")
ARANGO_DB_NAME = os.getenv("ARANGO_DB_NAME", "elysium_kg")


def get_arango_db():
    """
    Return a handle to the ELYSIUM ArangoDB database.

    This function is safe to have in the codebase even if you are not
    calling it yet. It will only try to connect if something actually
    imports and calls get_arango_db().
    """
    client = ArangoClient(hosts=ARANGO_URL)
    db = client.db(
        ARANGO_DB_NAME,
        username=ARANGO_USERNAME,
        password=ARANGO_PASSWORD,
    )
    return db