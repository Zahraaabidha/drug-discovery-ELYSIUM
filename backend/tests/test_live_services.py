"""Live calls to the real public scientific services (no credentials needed).
Run with: pytest -m network. A degraded service SKIPS (it is never faked)."""
import pytest

from app.services.sources import bindingdb, chembl, pubchem, reactome
from app.services.sources.http import ExternalServiceError

pytestmark = pytest.mark.network


def test_pubchem_gefitinib():
    c = pubchem.fetch_by_name("gefitinib")[0]
    assert c.inchikey == "XGALLCVXEZPNRQ-UHFFFAOYSA-N" and c.cid == "123631"


def test_chembl_egfr_activities():
    target, acts = chembl.fetch_activities("P00533", max_records=15)
    assert target == "CHEMBL203" and len(acts) == 15
    assert all(a.value_nm > 0 and a.relation == "=" and a.standard_type in ("IC50", "Ki", "Kd") for a in acts)


def test_reactome_egfr_pathways():
    paths = reactome.fetch_pathways("P00533")
    assert paths and any("EGFR" in p.name or "ERBB" in p.name.upper() for p in paths)


def test_bindingdb_egfr():
    try:
        acts = bindingdb.fetch_activities("P00533", cutoff_nm=10, max_records=20)
    except ExternalServiceError as exc:
        pytest.skip(f"BindingDB unavailable: {exc}")
    assert acts and all(a.relation == "=" and a.value_nm > 0 for a in acts)
