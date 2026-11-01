# ELYSIUM — AI-Driven Drug Discovery Toolkit

An agentic platform for small-molecule discovery:
**FastAPI · ArangoDB · RDKit · DeepPurpose · ChemBERTa · React + Tailwind**

## Pipeline

1. Pick a target protein (EGFR, DRD2, VEGFR2, ABL1, BRAF, HER2, ESR1, CDK2, BACE1, HIV1_PROTEASE — real UniProt sequences in `backend/app/data/target_sequences.json`).
2. **Generate** novel molecules (RDKit mutation + BRICS recombination of library drugs, de-duplicated against the library).
3. **Score** binding with the pretrained DeepPurpose BindingDB ensemble (predicted Kd → 0-1 score via pKd).
4. **Filter / profile** with RDKit ADMET + Lipinski.
5. **Compare** with known drugs (Morgan fingerprint Tanimoto + ChemBERTa cosine similarity).
6. **Store** the run in SQLite and the knowledge graph in ArangoDB (`elysium_graph`: targets, drugs, diseases, molecules; edges `binds`, `treats`, `associated_with`, `similar_to`).
7. **Explore** in the React UI (runs, analytics, interactive graph) or ask the LLM agent in natural language.

## Run locally

```bash
docker compose up -d arangodb                  # ArangoDB on :8529
cd backend && venv/Scripts/python -m uvicorn app.main:app --port 8000
cd frontend && npm install && npm run dev -- --port 5174
```

The backend creates the `elysium_kg` database, collections, graph and seed data on startup
(or run `python -m app.kg_seed`). Browse it at http://localhost:8529 (user `root`).

## Run everything in Docker

```bash
docker compose --env-file backend/.env up --build
```

`--env-file` is required so the frontend build gets the same `API_KEY` as the backend.
Pretrained models are mounted from `backend/save_folder` (not baked into the image).

## Configuration (`backend/.env`)

| Var | Purpose |
|---|---|
| `API_KEY` | required `X-API-KEY` header on all routes except `/health`, docs and molecule images |
| `ARANGO_HOST` / `ARANGO_PORT` (or `ARANGO_URL`), `ARANGO_USERNAME`, `ARANGO_PASSWORD`, `ARANGO_DB_NAME` | ArangoDB connection |
| `OPENROUTER_API_KEY` | LLM for the agent chat |
| `CORS_ORIGINS` | comma-separated allowed origins (default: local frontend) |

Frontend: `frontend/.env` needs `VITE_API_BASE_URL` and `VITE_API_KEY` (same value as `API_KEY`).

## Roadmap

- Target-conditioned generation (transformer / reinforcement learning)
- Natural-language agent over the knowledge graph
- Tests and CI, richer ADMET models
