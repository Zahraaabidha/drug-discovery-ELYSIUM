# Theriac — Computational drug-discovery research framework

FastAPI · SQLite (SQLAlchemy + Alembic) · ArangoDB · RDKit · DeepPurpose · ChemBERTa · FAISS · React + Tailwind

> **Status: research prototype.** Theriac organises compounds, measured data and model predictions so they can be
> explored and compared. Predicted binding values are model outputs, **not** experimental results, and generated
> molecules are unsynthesised ideas. On the one target benchmarked so far the DTI model is only weakly predictive
> (see [Evaluation results](#evaluation-results)).

## Contents

1. [Objectives](#objectives) · 2. [Features](#features) · 3. [Architecture](#architecture) · 4. [Technology stack](#technology-stack)
5. [Databases](#databases) · 6. [Scientific integrations](#scientific-integrations) · 7. [Workflows](#workflows)
8. [Installation](#installation) · 9. [Configuration](#configuration) · 10. [Docker](#docker) · 11. [API usage](#api-usage)
12. [Testing](#testing) · 13. [Evaluation results](#evaluation-results) · 14. [Limitations](#limitations) · 15. [Future work](#future-work)

## Objectives

* Keep **one persistent registry** of every compound — known drugs, externally sourced compounds and newly generated
  molecules — with identity, provenance, properties and history.
* Keep **experimental evidence** (measured IC50/Ki/Kd from ChEMBL and BindingDB) strictly separate from
  **computational predictions** (DeepPurpose), in the database, API, graph and UI.
* Make runs **reproducible** (seed, parameters, models, data sources, metrics) and results **honest** (no placeholder
  scores, no silent target substitution, no reference drug presented as a generated molecule).
* Provide measurable **evaluation** of generation, similarity retrieval and DTI prediction, with stated limitations.

## Features

| Area | What exists (verified by tests and a live run, see [Testing](#testing)) |
|---|---|
| Compound registry | Unique per standardised structure (InChIKey). Stores original SMILES, every source (database, external ID, URL, retrieval time), RDKit descriptors, annotations, collections and prediction history. Duplicates merge; a reference compound is never relabelled as generated. |
| External data | PubChem (structure/IDs by name), ChEMBL and BindingDB (exact IC50/Ki/Kd in nM per UniProt target), Reactome (pathways). Failures of a service are reported per source and never replaced by invented data. |
| Molecular analysis | RDKit standardisation/validation, Morgan fingerprints, Lipinski rule of five and basic physicochemical descriptors (**not** ADMET). ChemBERTa embeddings. FAISS: binary fingerprint index re-ranked with exact Tanimoto; inner-product embedding index. Top-k search and N-way comparison. |
| Generation | RDKit functional-group edits + BRICS recombination of registry seed molecules, seeded RNG. Validity, uniqueness and novelty (against the registry) are measured per run. Returns fewer molecules rather than padding with reference drugs. |
| DTI prediction | DeepPurpose pretrained BindingDB ensemble → predicted Kd (nM), pKd, model name/version stored. Unsupported target → HTTP 422. Model failure → HTTP 502 and the run is stored as `failed`. No placeholder scorer exists. |
| Filtering | Backend filters (MW, logP, TPSA, HBD, HBA, rotatable bonds, Lipinski) applied to candidates before scoring; an impossible filter returns an empty result, not unfiltered molecules. The same filters exist in the Library API/UI. |
| Knowledge graph | ArangoDB `Theriac_graph` with targets, reference drugs, compounds with measurements, generated molecules and Reactome pathways. Every edge carries `evidence_type` (`experimental`, `computational_prediction`, `database_annotation`) and provenance. |
| Reproducible runs | Each run stores seed, request/generator parameters, models and versions, data sources, metrics, KG-sync status and `status` (`completed`, `failed`, `legacy_unverified`). |
| Evaluation | Generation quality, similarity retrieval (FAISS vs exact; identity under SMILES rewriting), DTI vs measured affinity, plus a time-split DTI benchmark against six or more baselines. Reports store parameters, dataset and limitations. |
| UI | **Compound Library** (`/library`): search, 15 filters, sorting, paging, compound profile (provenance, measurements vs predictions, similar compounds, notes), compare, similarity search, collections, annotations, data import, evaluation. Plus the existing Discovery, Runs, Graphs, Agent and Analysis pages (Discovery now offers the supported targets, real filters and a seed; Runs statistics are computed from stored runs). |

## Architecture

```
React (Vite) ──HTTP + X-API-KEY──▶ FastAPI ──▶ Relational DB (authoritative: compounds, evidence, runs)
                                      ├─────▶ FAISS indexes (derived from the registry)
                                      └─────▶ ArangoDB (biological relationships, evidence-typed edges)
```

The relational DB is the source of truth for identity, metadata, measurements and prediction history; ArangoDB
represents relationships and is updated idempotently from it.

## Technology stack

Python 3.11, FastAPI, SQLAlchemy 2, Alembic, python-arango, RDKit, DeepPurpose 0.1.5 (PyTorch 2.1), Hugging Face
Transformers (`seyonec/ChemBERTa-zinc-base-v1`), FAISS (CPU), SciPy, pytest · Node 20, React 19, Vite, Tailwind,
Cytoscape, Recharts, Vitest + Testing Library · Docker Compose, ArangoDB 3.11.

## Databases

* **Relational (SQLite by default, `DATABASE_URL`)** – tables `compounds`, `compound_sources`, `bioactivities`
  (experimental), `predictions` (computational), `discovery_runs`, `molecules`, `collections`, `collection_items`,
  `annotations`, `evaluation_reports`, plus the legacy `kg_nodes`/`kg_edges`. Schema is managed by Alembic migrations
  (`backend/alembic`, applied automatically at startup; `0003` marks pre-registry runs as `legacy_unverified`).
* **ArangoDB (`Theriac_kg`)** – vertex collections `targets`, `drugs`, `compounds`, `molecules`, `pathways`; edge
  collections `binds`, `participates_in`, `similar_to` (and legacy `treats`, `associated_with`, unused).
* **FAISS** – in-memory indexes rebuilt from the registry; ChemBERTa embeddings cached in `index_data/`.

## Scientific integrations

| Source | Used for | Credentials |
|---|---|---|
| UniProt | 10 supported target sequences (EGFR, DRD2, VEGFR2, ABL1, BRAF, HER2, ESR1, CDK2, BACE1, HIV1_PROTEASE) | none |
| PubChem PUG REST | structures and identifiers by name | none (optional `NCBI_API_KEY`) |
| ChEMBL | measured IC50/Ki/Kd (exact `=`, nM) | none |
| BindingDB | measured affinities (exact `=`) – the service intermittently returns empty responses; that is reported as an error for the source | none |
| Reactome | human pathways per UniProt accession | none |
| DeepPurpose pretrained weights | DTI prediction (trained on BindingDB) | none |

All calls are made by the backend; nothing secret reaches the browser.

## Workflows

1. **Build the library** – the bundled reference drugs are imported automatically. Add measured data with *Library → Data sources → Import measurements* (per target, ChEMBL and/or BindingDB), look up compounds in PubChem, or add your own SMILES.
2. **Explore** – search/filter the registry, open a compound profile, compare compounds, run a fingerprint/embedding similarity search, organise compounds into collections, add notes.
3. **Discover** – *Discovery* page: choose a supported target, count, optional filters and seed → molecules are generated, scored with DeepPurpose, registered as `generated`, compared with known compounds and written to the graph.
4. **Audit** – *Runs* and run detail show seed, parameters, models, data sources and metrics; compound profiles show the prediction history; *Graphs* show experimental vs predicted edges.
5. **Evaluate** – *Library → Evaluation* runs and stores the three evaluations.

## Installation

Prerequisites: Python 3.11, Node 20, Docker (for ArangoDB).

```bash
docker compose --env-file backend/.env up -d arangodb          # ArangoDB on :8529

cd backend
python -m venv venv
venv/Scripts/pip install -r requirements-dev.txt                # use venv/bin/pip on Linux/macOS
cp .env.example .env                                            # then edit (see Configuration)
venv/Scripts/python -m uvicorn app.main:app --port 8000

cd ../frontend
npm install
npm run dev -- --port 5174                                      # http://localhost:5174/library
```

At startup the backend applies migrations, imports the reference drugs and, if ArangoDB is reachable, creates the
graph schema. The DeepPurpose pretrained models must exist in
`backend/save_folder/pretrained_models/DeepPurpose_BindingDB` (or set `DEEPPURPOSE_MODEL_DIR`); they are downloaded
by DeepPurpose on first use and are not committed.

## Configuration

`backend/.env` (template: `backend/.env.example`; never commit real values):

| Variable | Purpose |
|---|---|
| `API_KEY` | required `X-API-KEY` on all routes except `/health`, API docs and molecule images |
| `ARANGO_HOST`, `ARANGO_PORT`, `ARANGO_USERNAME`, `ARANGO_PASSWORD`, `ARANGO_DB_NAME` (or `ARANGO_URL`) | ArangoDB connection |
| `DATABASE_URL` | relational DB (default `sqlite:///./Theriac.db`) |
| `OPENROUTER_API_KEY` | LLM for the chat agent (optional) |
| `CONTACT_EMAIL`, `NCBI_API_KEY`, `EXTERNAL_API_TIMEOUT` | optional settings for the public data APIs |
| `DEEPPURPOSE_MODEL_DIR`, `Theriac_INDEX_DIR`, `CORS_ORIGINS`, `LOG_LEVEL`, `Theriac_DISABLE_ARANGO` | paths and behaviour |

`frontend/.env`: `VITE_API_BASE_URL`, `VITE_API_KEY` (same value as `API_KEY`; it is baked in at build time).

## Docker

```bash
docker compose --env-file backend/.env up -d --build      # arangodb, backend (:8000), frontend (:5174)
docker compose --env-file backend/.env down               # stop; data is kept
```

* `--env-file` is required so the frontend image is built with the same `API_KEY` as the backend.
* The compose file bind-mounts `backend/Theriac.db` into the backend container, so the container and a local run share
  the same relational database (do not run both at once), and mounts `backend/save_folder` for the DeepPurpose models.
  ArangoDB data lives in the `arango_data` volume; ChemBERTa weights in `model_cache`; FAISS caches in `index_data`.
* The first ChemBERTa use in a fresh `model_cache` downloads the model from Hugging Face.

## API usage

Interactive documentation: `http://localhost:8000/docs`. Every request needs `X-API-KEY`.

```bash
H="X-API-KEY: $API_KEY"; J="Content-Type: application/json"

# supported targets
curl -H "$H" localhost:8000/targets

# import measured activity (ChEMBL + BindingDB) and look a compound up in PubChem
curl -H "$H" -H "$J" -d '{"target":"EGFR","sources":["chembl","bindingdb"],"max_records":300}' localhost:8000/library/import/target
curl -H "$H" -H "$J" -d '{"name":"imatinib"}' localhost:8000/library/import/pubchem

# search the registry with filters
curl -H "$H" "localhost:8000/library/compounds?origin=generated&max_mw=400&lipinski_pass=true&sort=mol_weight"
curl -H "$H" "localhost:8000/library/compounds?has_experimental=true&target=EGFR&q=gefitinib"

# compound profile (measurements and predictions are returned separately)
curl -H "$H" localhost:8000/library/compounds/42

# similarity search: fingerprint, embedding or both; compare compounds
curl -H "$H" -H "$J" -d '{"smiles":"CC(=O)Nc1ccc(O)cc1","k":5,"method":"both"}' localhost:8000/library/similarity
curl -H "$H" -H "$J" -d '{"compound_ids":[1,2,3]}' localhost:8000/library/compare

# reproducible discovery run
curl -H "$H" -H "$J" -d '{"target_id":"EGFR","num_molecules":5,"seed":123,"max_mw":450,"lipinski_only":true}' localhost:8000/discover

# evaluations and stored reports
curl -H "$H" -H "$J" -d '{"target":"EGFR"}' localhost:8000/evaluation/dti
curl -H "$H" localhost:8000/evaluation/reports
```

Errors: `401` bad key · `404` not found · `409` conflict or not enough data · `422` invalid input / unsupported target ·
`502` external service or DTI model failure · `503` embedding model unavailable.

## Testing

```bash
cd backend
venv/Scripts/python -m pytest -m "not slow and not network and not arango"   # fast, offline
venv/Scripts/python -m pytest -m slow      # real DeepPurpose + ChemBERTa
venv/Scripts/python -m pytest -m network   # live PubChem / ChEMBL / BindingDB / Reactome
venv/Scripts/python -m pytest -m arango    # real ArangoDB, database `Theriac_test` (dropped afterwards)
cd ../frontend && npm test && npx tsc -b && npm run build
```

Backend tests cover standardisation/dedup, parsers and idempotent ingestion, generation accounting and
reproducibility, enforced filters, honest failure handling, every Library endpoint and filter, FAISS vs exact search,
evaluations, migrations (fresh and legacy databases) and the Arango graph. A clearly labelled test double (`FakeDTI`) is
used only to test plumbing; the real model is covered by the `slow` tests. Frontend tests check that every filter
control reaches the API, evidence is rendered separately, and errors/empty states are shown.

## Evaluation results

Measured on 2026-11-02 on this project's registry (448 compounds: 49 reference, 394 external, 5 generated;
596 measurements for EGFR).

| Evaluation | Result |
|---|---|
| Generation (100 molecules, seed 0) | validity 0.75 · uniqueness 1.00 · novelty vs. registry 1.00 · internal diversity 0.88 |
| Similarity (100 queries, k=10) | FAISS vs exact Tanimoto recall@10 = 0.95 · fingerprint identity retrieval after SMILES rewriting = 1.00 · ChemBERTa identity with an un-canonicalised rewritten query = 0.17 |
| DTI vs measured affinity (EGFR, 231 compounds, ChEMBL + BindingDB) | Spearman ρ = 0.35 · Pearson r = 0.38 · RMSE 1.43 pKd units vs 1.47 for always predicting the mean |

The EGFR check above is a quick consistency test only. Novelty is relative to this registry only.

### DTI benchmark on later-published BindingDB data

A time-split benchmark (backend `app/benchmarks`, run on 2026-11-02) trains simple baselines on BindingDB records entered
up to 2021-05-31 and tests DeepPurpose (zero-shot, as shipped) and the baselines on identical, later-entered compounds that
have no recorded overlap before the cutoff. Primary benchmark: Ki/Kd for DRD2, CDK2, ESR1 and VEGFR2 (at least 200 training
and 100 test compounds); IC50 is reported separately. 95% bootstrap intervals in brackets.

| Target (test compounds) | DeepPurpose Spearman | Best trained baseline (Spearman) | DeepPurpose RMSE vs. predicting the mean |
|---|---|---|---|
| DRD2 (1,365) | 0.07 [0.02, 0.12] | 0.48 (kNN or random forest) | 1.23 vs 0.95 |
| CDK2 (700) | 0.22 [0.15, 0.29] | 0.35 (descriptor ridge) | 3.57 vs 1.69 |
| ESR1 (117) | −0.28 [−0.48, −0.08] | 0.43 (kNN) | 1.67 vs 1.07 |
| VEGFR2 (112) | 0.19 [0.02, 0.35] | 0.44 (random forest) | 1.88 vs 1.09 |

What this supports: the production DeepPurpose ensemble is significantly worse than the best trained baseline on all four
primary targets (and on the exploratory EGFR and ABL1) and on all eight IC50 targets; its predicted Kd values have a larger
error than simply predicting the training mean; and much of its apparent signal goes through molecular size. The
MPNN_CNN ensemble member returns different values for the same molecule depending on the batch and order it is scored in,
so predictions are not fully reproducible across batches. Variants without that member did better on DRD2 and CDK2, but they
were chosen after seeing the results, are not used in production and are not claimed as an improvement.

Whether DeepPurpose's training data overlapped these records is **unverified** (the package does not record it); "no evidence
of overlap" is not "unseen". Baselines are trained on the target's own data while DeepPurpose is not, test sets are small for
ESR1 and VEGFR2, and intervals ignore assay clustering. Predicted values should be used only as a weak, uncertain signal.

## Limitations

Predictions are not experiments; generated molecules are unsynthesised; only 10 targets are supported; descriptors are
not ADMET predictions; reference-library structures were typed by hand; BindingDB is intermittently unavailable; runs
created before the registry are kept but flagged `legacy_unverified`; a single shared API key and SQLite are not
production-grade security/scale.

## Future work

* Resolve the MPNN_CNN batch dependence and ensemble averaging in production scoring, calibrate predictions, and
  add an applicability-domain warning; then fine-tune or retrain and re-run the same benchmark.
* Verify DeepPurpose's training data overlap, and extend the benchmark with assay-level splits and more targets.
* Target-conditioned and learned generators, synthesisability and ADMET models with their own validation.
* More targets and structure-based features (binding-site constructs, mutants).
* User accounts and authorisation, PostgreSQL, scalable approximate FAISS indexes.
* Scheduled data refresh and versioned snapshots of external data.
