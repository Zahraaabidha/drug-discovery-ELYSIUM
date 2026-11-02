"""Test configuration.

Tests run against a temporary SQLite database and never touch elysium.db. ArangoDB bootstrap at
app import is disabled; Arango-dependent tests are marked `arango` and use their own database.

`FakeDTI` is an explicitly labelled TEST DOUBLE that lets the pipeline plumbing be tested without
the 5-model DeepPurpose ensemble. Its numbers are meaningless and it is used ONLY in tests; the
real model is exercised by tests marked `slow`.
"""
import hashlib
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="elysium_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["ELYSIUM_DISABLE_ARANGO"] = "1"
os.environ["ELYSIUM_INDEX_DIR"] = str(_TMP / "index")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import models as m  # noqa: E402
from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import registry, scoring  # noqa: E402
from app.services.dti_deeppurpose import kd_to_result  # noqa: E402
from app.services.similarity_index import index as similarity_index  # noqa: E402


class FakeDTI:
    """TEST DOUBLE - deterministic pseudo-Kd derived from the SMILES hash. Not a scientific model."""
    name = "FakeDTI(test-double)"

    def model_info(self):
        return {"model_name": "FakeDTI test double", "model_version": "0", "aggregation": "n/a",
                "output": "predicted Kd (nM)", "members": []}

    def predict(self, smiles_list, target_sequence, target_id):
        out = []
        for s in smiles_list:
            h = int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)
            out.append(kd_to_result(s, 1.0 + (h % 100000) / 10.0))
        return out


class FailingDTI(FakeDTI):
    name = "FailingDTI(test-double)"

    def predict(self, *a, **kw):
        raise scoring.ScoringError("simulated model failure")


@pytest.fixture(scope="session")
def api_headers():
    key = os.getenv("API_KEY")
    return {"X-API-KEY": key} if key else {}


@pytest.fixture()
def db():
    """Fresh registry (reference collections imported) for every test."""
    with engine.begin() as conn:
        for table in reversed(m.Base.metadata.sorted_tables):
            conn.execute(table.delete())
    session = SessionLocal()
    registry.import_reference_collections(session)
    similarity_index.rebuild(session)
    yield session
    session.close()


@pytest.fixture()
def client(db, api_headers):
    scoring.set_scorer(FakeDTI())
    with TestClient(app, headers=api_headers) as c:
        yield c
    scoring.set_scorer(None)


@pytest.fixture()
def failing_client(db, api_headers):
    scoring.set_scorer(FailingDTI())
    with TestClient(app, headers=api_headers, raise_server_exceptions=False) as c:
        yield c
    scoring.set_scorer(None)
