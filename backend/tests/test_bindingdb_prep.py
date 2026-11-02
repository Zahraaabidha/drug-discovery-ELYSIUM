"""Logic tests for the BindingDB benchmark preparation, on a tiny synthetic TSV that uses the real column
names. The synthetic rows only exercise filtering/splitting code; they are not scientific data."""
import json

import pandas as pd
import pytest

from app.benchmarks.bindingdb_prep import PREP_COLUMNS, PrepConfig, parse_value, prepare, sha256_file
from app.services import chem

COLS = list(PREP_COLUMNS)


def row(rid, smiles, acc, date, ki="", ic50="", kd="", org="Homo sapiens", pmid="", src="ChEMBL", doi="", pub="1/1/2015"):
    ik = chem.standardise(smiles).inchikey if smiles not in ("NOT_A_SMILES",) else "AAAAAAAAAAAAAA-BBBBBBBBBB-C"
    d = {"BindingDB Reactant_set_id": rid, "Ligand SMILES": smiles, "Ligand InChI Key": ik,
         "Target Source Organism According to Curator or DataSource": org, "Ki (nM)": ki, "IC50 (nM)": ic50, "Kd (nM)": kd,
         "Curation/DataSource": src, "Article DOI": doi, "PMID": pmid, "Patent Number": "", "Date of publication": pub,
         "Date in BindingDB": date, "ChEMBL ID of Ligand": "", "UniProt (SwissProt) Primary ID of Target Chain 1": acc}
    return [d[c] for c in COLS]


EGFR, DRD2 = "P00533", "P14416"
A = "CC(=O)Nc1ccc(O)cc1"                       # paracetamol : pre-cutoff EGFR Ki  -> train
B = "CCCCCCCCN"                               # pre-cutoff EGFR IC50, post-cutoff EGFR Ki -> tier B (excluded)
C = "CCCCCCCCCO"                              # pre-cutoff DRD2 only, post EGFR Ki -> tier C
D_PRE, D_POST = "N[C@@H](C)C(=O)O", "N[C@H](C)C(=O)O"   # stereoisomers share skeleton -> tier D
E = "c1ccc2c(c1)oc1ccccc12"                   # nothing before -> tier E
NOISY = "CCCCCCCN"                            # two post-cutoff values 5 log units apart


def build(tmp_path, extra=()):
    rows = [
        row("1", A, EGFR, "3/3/2015", ki="10"),
        row("2", A, EGFR, "3/4/2015", ki="12"),                         # replicate in the same window
        row("3", B, EGFR, "5/5/2016", ic50="50"),
        row("4", B, EGFR, "6/6/2023", ki="5"),
        row("5", C, DRD2, "1/1/2017", ki="30"),
        row("6", C, EGFR, "7/7/2023", kd="8"),
        row("7", D_PRE, DRD2, "2/2/2018", ki="100"),
        row("8", D_POST, EGFR, "8/8/2023", ki="40"),
        row("9", E, EGFR, "9/9/2024", ki="2.5", pmid="111"),
        row("10", E, EGFR, "9/9/2024", ki="2.5", pmid="111", src="BindingDB"),  # exact duplicate (other channel)
        row("11", E, EGFR, "9/9/2024", ki="2.5", pmid="222"),                  # same value, other publication
        # filtered out:
        row("12", A, EGFR, "3/3/2016", ki=">10000"),                    # inequality
        row("13", A, EGFR, "3/3/2016", ki="abc"),                       # unparseable
        row("14", A, EGFR, "3/3/2016", ki="1e-9"),                      # below range
        row("15", "NOT_A_SMILES", EGFR, "3/3/2016", ki="5"),            # invalid structure
        row("16", A, EGFR, "3/3/2016", ki="5", org="Rattus norvegicus"),
        row("17", A, "P99999", "3/3/2016", ki="5"),                     # unsupported target
        row("18", "c1ccccc1", EGFR, "3/3/2016", ki="5"),                # 6 heavy atoms: kept
        row("19", "C", EGFR, "3/3/2016", ki="5"),                       # 1 heavy atom: dropped
        row("20", NOISY, EGFR, "10/10/2024", ki="1"),                   # noisy replicate group (post)
        row("21", NOISY, EGFR, "10/10/2024", ki="100000", pmid="9"),
        *extra,
    ]
    p = tmp_path / "mini.tsv"
    pd.DataFrame(rows, columns=COLS).to_csv(p, sep="\t", index=False)
    return p


@pytest.fixture()
def out(tmp_path):
    src = build(tmp_path)
    cfg = PrepConfig(workers=1, min_heavy_atoms=6, min_train_compounds=1, min_test_compounds=1)
    manifest = prepare(src, tmp_path / "derived", cfg, expected_sha256=sha256_file(src))
    groups = pd.read_csv(tmp_path / "derived" / "groups.csv.gz")
    records = pd.read_csv(tmp_path / "derived" / "records.csv.gz")
    return manifest, groups, records, src


def ik(smiles):
    return chem.standardise(smiles).inchikey


@pytest.mark.parametrize("text,exp", [("5", ("=", 5.0)), (">10", (">", 10.0)), ("<=3", ("<", 3.0)), ("x", None), (None, None), ("nan", None)])
def test_parse_value(text, exp):
    assert parse_value(text) == exp


def test_stage_counts_are_monotonic_and_explain_every_removal(out):
    manifest, _, _, _ = out
    st = manifest["stage_counts"]
    c = st["counts"]
    assert c["s0_rows_in_file"]["ALL"] == 21
    assert c["s1_rows_matching_supported_target_uniprot"]["ALL"] == 20      # P99999 row excluded
    assert c["s2_rows_with_expected_organism"]["ALL"] == 19                           # rat row excluded
    assert c["s3_valid_standardised_structure_rows"]["ALL"] == 18           # invalid SMILES excluded
    assert c["s6_exact_relation_only"]["ALL"] == c["s5_parseable_value"]["ALL"] - 1     # one inequality
    assert c["s7_value_in_range"]["ALL"] == c["s6_exact_relation_only"]["ALL"] - 1      # 1e-9 nM
    assert c["s8_heavy_atom_range"]["ALL"] == c["s7_value_in_range"]["ALL"] - 1         # methane
    assert c["s9_after_exact_duplicate_removal"]["ALL"] == c["s8_heavy_atom_range"]["ALL"] - 1   # duplicate row
    totals = [c[s]["ALL"] for s in st["stages"][:5]]
    assert totals == sorted(totals, reverse=True)


def test_organism_rule_is_target_specific(tmp_path):
    hiv = "P03366"
    rows = [row("h1", "CC(C)CC(NC(=O)C(C)NC(=O)c1ccccc1)C(=O)O", hiv, "1/1/2015", ic50="5", org="Human immunodeficiency virus 1"),
            row("h2", "CC(C)CC(NC(=O)C(C)NC(=O)c1ccccc1)C(=O)O", hiv, "1/1/2015", ic50="6", org="Homo sapiens")]
    src = build(tmp_path, rows)
    m = prepare(src, tmp_path / "o", PrepConfig(workers=1))
    c = m["stage_counts"]["counts"]["s2_rows_with_expected_organism"]
    assert c["HIV1_PROTEASE"] == 1                                   # viral target keeps the viral record only


def test_duplicate_collapsed_but_provenance_kept_and_other_publication_preserved(out):
    _, _, records, _ = out
    e = records[records["inchikey"] == ik(E)]
    assert len(e) == 2                                                   # pmid 111 (merged) + pmid 222
    merged = e[e["pmid"] == 111].iloc[0]
    assert merged["dup_count"] == 2 and set(str(merged["merged_rids"]).split(";")) == {"9", "10"}
    assert "BindingDB" in merged["merged_sources"] and "ChEMBL" in merged["merged_sources"]


def test_replicates_are_aggregated_per_compound_and_window(out):
    _, groups, _, _ = out
    a = groups[(groups["ik_std"] == ik(A)) & (groups["bench"] == "KiKd") & (groups["window"] == "pre")]
    assert len(a) == 1
    g = a.iloc[0]
    import math
    # the aggregate is the median in pValue space (mean of the two middle values for 2 replicates)
    assert g["n_records"] == 2 and g["pvalue"] == pytest.approx(((9 - math.log10(10)) + (9 - math.log10(12))) / 2, abs=1e-6)


def test_overlap_tiers_and_roles(out):
    _, groups, _, _ = out
    post = groups[(groups["bench"] == "KiKd") & (groups["window"] == "post")].set_index("ik_std")
    assert post.loc[ik(B), "tier"] == "B" and post.loc[ik(B), "temporal_role"] == "excluded_compound_in_pre_cutoff_data"
    assert post.loc[ik(C), "tier"] == "C" and post.loc[ik(C), "temporal_role"] == "test_possible_overlap"
    assert post.loc[ik(D_POST), "tier"] == "D" and post.loc[ik(D_POST), "temporal_role"] == "test_primary"
    assert post.loc[ik(E), "tier"] == "E" and post.loc[ik(E), "temporal_role"] == "test_strict"


def test_noisy_replicates_excluded_from_test(out):
    _, groups, _, _ = out
    ccn = groups[(groups["ik_std"] == ik(NOISY)) & (groups["window"] == "post")].iloc[0]
    assert bool(ccn["noisy"]) and ccn["temporal_role"] == "excluded_noisy_replicates"


def test_ic50_is_a_separate_benchmark(out):
    _, groups, _, _ = out
    ic = groups[groups["bench"] == "IC50"]
    assert set(ic["ik_std"]) == {ik(B)} and (ic["window"] == "pre").all()
    assert not set(groups[groups["bench"] == "KiKd"]["types"]) & {"IC50"}


def test_no_test_compound_is_in_train_and_checks_pass(out):
    manifest, groups, _, _ = out
    assert manifest["leakage_checks"]["passed"] is True
    for (_, _), g in groups.groupby(["bench", "sym"]):          # separation is required per target
        train = set(g[g["temporal_role"] == "train"]["ik_std"])
        test = set(g[g["temporal_role"].str.startswith("test_")]["ik_std"])
        assert not (train & test)


def test_checks_detect_injected_leakage(out):
    from app.benchmarks.bindingdb_prep import leakage_checks
    _, groups, _, _ = out
    bad = groups.copy()
    victim = bad[bad["temporal_role"].str.startswith("test_")].iloc[0]
    clone = victim.copy()
    clone["temporal_role"], clone["window"] = "train", "pre"
    bad = pd.concat([bad, clone.to_frame().T], ignore_index=True)
    res = leakage_checks(bad)
    assert res["temporal_test_compounds_in_train"] >= 1 and res["passed"] is False


def test_scaffold_split_keeps_scaffold_groups_whole(tmp_path):
    scaffolds = ["c1ccccc1", "c1ccncc1", "C1CCCCC1", "c1ccoc1", "c1ccsc1", "C1CCNCC1", "c1ccc2ccccc2c1", "C1CCOC1", "n1cnccc1", "c1ccc2[nH]ccc2c1"]
    subs = ["C", "CC", "CCC", "CCCC", "CO", "CCO", "CN", "CCN", "CF", "CCl", "CBr"]
    extra = [row(f"s{si}_{k}", f"{s}{sub}", EGFR, "1/1/2016", ki=str(10 + k + si))
             for si, s in enumerate(scaffolds) for k, sub in enumerate(subs)]
    src = build(tmp_path, extra)
    prepare(src, tmp_path / "d2", PrepConfig(workers=1, min_train_compounds=1, min_test_compounds=1))
    g = pd.read_csv(tmp_path / "d2" / "groups.csv.gz")
    pre = g[(g["window"] == "pre") & (g["bench"] == "KiKd")].copy()
    pre["scaffold"] = pre["scaffold"].fillna("")
    folds = pre[pre["scaffold"] != ""].groupby("scaffold")["scaffold_split"].nunique()
    assert len(folds) >= len(scaffolds) and (folds == 1).all()
    assert "train" in set(pre["scaffold_split"]) and len(set(pre["scaffold_split"])) >= 2
    sizes = pre["scaffold_split"].value_counts(normalize=True)
    assert 0.6 < sizes["train"] < 0.95


def test_wrong_checksum_is_rejected(tmp_path):
    src = build(tmp_path)
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        prepare(src, tmp_path / "x", PrepConfig(workers=1), expected_sha256="0" * 64)


def test_manifest_is_reproducible(tmp_path):
    src = build(tmp_path)
    cfg = PrepConfig(workers=1, min_train_compounds=1, min_test_compounds=1)
    m1 = prepare(src, tmp_path / "r1", cfg)
    m2 = prepare(src, tmp_path / "r2", cfg)
    for k in ("stage_counts", "summary", "tier_counts_post_groups", "leakage_checks"):
        assert json.dumps(m1[k], sort_keys=True, default=int) == json.dumps(m2[k], sort_keys=True, default=int)
    g1 = pd.read_csv(tmp_path / "r1" / "groups.csv.gz").sort_values(["bench", "sym", "ik_std", "window"]).reset_index(drop=True)
    g2 = pd.read_csv(tmp_path / "r2" / "groups.csv.gz").sort_values(["bench", "sym", "ik_std", "window"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(g1, g2)
