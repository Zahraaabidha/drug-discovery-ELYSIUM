import pytest

from app import models as m
from app.services import chem, registry

ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O"
ASPIRIN_ALT = "OC(=O)c1ccccc1OC(C)=O"          # same molecule, different string


def test_standardise_same_molecule_same_inchikey():
    a, b = chem.standardise(ASPIRIN), chem.standardise(ASPIRIN_ALT)
    assert a.inchikey == b.inchikey == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
    assert a.canonical_smiles == b.canonical_smiles
    assert b.original_smiles == ASPIRIN_ALT            # original preserved


def test_standardise_strips_salts_and_neutralises():
    salt = chem.standardise("CC(=O)OC1=CC=CC=C1C(=O)[O-].[Na+]")
    assert salt.inchikey == chem.standardise(ASPIRIN).inchikey


@pytest.mark.parametrize("bad", ["", "not-a-smiles", "C1CC", None])
def test_invalid_smiles_rejected(bad):
    with pytest.raises(chem.InvalidMolecule):
        chem.standardise(bad)


def test_physchem_values_for_aspirin():
    pc = chem.physchem(ASPIRIN)
    assert pc.mol_weight == pytest.approx(180.159, abs=0.01)
    assert pc.hbd == 1 and pc.hba == 3
    assert pc.lipinski_pass and pc.lipinski_violations == 0


def test_lipinski_violation_counted():
    big = "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"  # logP > 5, MW > 500
    pc = chem.physchem(big)
    assert pc.lipinski_violations >= 1 and not pc.lipinski_pass


def test_register_deduplicates_and_keeps_provenance(db):
    c1, created1 = registry.register_compound(db, ASPIRIN, origin=m.ORIGIN_EXTERNAL, source_db="pubchem", external_id="2244")
    c2, created2 = registry.register_compound(db, ASPIRIN_ALT, origin=m.ORIGIN_EXTERNAL, source_db="chembl", external_id="CHEMBL25")
    assert c1.id == c2.id and not created2
    assert c1.origin == m.ORIGIN_REFERENCE            # already imported as a reference drug; origin is not overwritten
    srcs = {(s.source_db, s.external_id, s.original_smiles) for s in c1.sources}
    assert ("chembl", "CHEMBL25", ASPIRIN_ALT) in srcs and ("pubchem", "2244", ASPIRIN) in srcs


def test_same_source_not_duplicated(db):
    c, _ = registry.register_compound(db, "CCO", origin=m.ORIGIN_EXTERNAL, source_db="user_upload")
    registry.register_compound(db, "OCC", origin=m.ORIGIN_EXTERNAL, source_db="user_upload")
    assert len([s for s in c.sources if s.source_db == "user_upload"]) == 1


def test_generated_never_overrides_reference_origin(db):
    c, created = registry.register_compound(db, ASPIRIN, origin=m.ORIGIN_GENERATED, source_db=registry.GENERATOR_SOURCE,
                                            generation_method="x", generation_run_id=None)
    assert not created and c.origin == m.ORIGIN_REFERENCE and c.generation_method is None


def test_reference_import_idempotent(db):
    n = db.query(m.Compound).count()
    stats = registry.import_reference_collections(db)
    assert db.query(m.Compound).count() == n
    assert stats["created"] == 0 and stats["invalid"] == 0
    assert db.query(m.Compound).filter_by(origin=m.ORIGIN_REFERENCE).count() == n


def test_unknown_origin_rejected(db):
    with pytest.raises(ValueError):
        registry.register_compound(db, "CCO", origin="made_up", source_db="x")


def test_prediction_records_units_and_evidence_type(db):
    c, _ = registry.register_compound(db, "CCCCO", origin=m.ORIGIN_GENERATED, source_db="elysium_generator")
    p = registry.record_prediction(db, c, target_symbol="EGFR", uniprot_id="P00533", model_name="M", model_version="1",
                                   value_nm=10.0, run_id=None)
    assert p.units == "nM" and p.evidence_type == "computational_prediction"
    assert p.pkd == pytest.approx(8.0)
