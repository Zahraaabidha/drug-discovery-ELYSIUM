#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\main.py
from dotenv import load_dotenv
load_dotenv()
import datetime as dt
import csv
import io
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import cast, Optional
from typing import List as PyList
from pydantic import BaseModel as PydanticBase
from .arangodb_client import get_arango_db
from fastapi import APIRouter


from .schemas import (
    DiscoveryRequest,
    DiscoveryResponse,
    DiscoveryRunListResponse,
    DiscoveryRunSummary,
    Molecule as MoleculeSchema,
    TargetGraphResponse, 
    DrugGraphResponse,      # <-- add this
)
from .models import DiscoveryRun
from .services.discovery import run_discovery
from .db import Base, engine, get_db
from . import models  # ensure models are imported so metadata knows them
from .similarity import find_combined_similar_drugs
from .services.kg import get_target_graph, get_drug_graph
from app.routes.molecule_image import router as molecule_image_router
from app.routes import graph_view

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ELYSIUM – AI-Driven Drug Discovery Toolkit",
    version="0.1.0",
    description="Backend API for ELYSIUM, a modular agentic drug discovery system."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(molecule_image_router)
app.include_router(graph_view.router)


# In-memory chat sessions (cleared on restart, fine for demo)
chat_sessions: dict = {}


class BatchDiscoverRequest(PydanticBase):
    targets: PyList[DiscoveryRequest]


class AgentRequest(PydanticBase):
    prompt: str
    session_id: Optional[str] = None


class ChatMessage(PydanticBase):
    role: str
    content: str


class ChatRequest(PydanticBase):
    prompt: str
    session_id: Optional[str] = None


class ChatResponse(PydanticBase):
    session_id: str
    answer: str
    steps: list
    evidence: list
    history: list

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "elysium-backend"}


@app.get("/health/full")
def health_full(db: Session = Depends(get_db)):
    status = {"sqlite": "ok", "arangodb": "unknown"}

    try:
        db.execute(text("SELECT 1"))
        status["sqlite"] = "ok"
    except Exception as e:
        status["sqlite"] = f"error: {str(e)}"

    try:
        arango = get_arango_db()
        arango.collections()
        status["arangodb"] = "ok"
    except Exception as e:
        status["arangodb"] = f"error: {str(e)}"

    overall = "ok" if all(v == "ok" for v in status.values()) else "degraded"
    return {"status": overall, "services": status}

@app.get("/runs", response_model=DiscoveryRunListResponse)
def list_runs(db: Session = Depends(get_db)):
    runs = (
        db.query(DiscoveryRun)
        .order_by(DiscoveryRun.created_at.desc())
        .limit(50)
        .all()
    )

    summaries = [
        DiscoveryRunSummary(
            run_id=cast(str, run.id),
            target_id=cast(str, run.target_id),
            num_molecules=cast(int, run.num_molecules),
            created_at=cast(dt.datetime, run.created_at),
        )
        for run in runs
    ]

    return DiscoveryRunListResponse(runs=summaries)

@app.get("/graph/target/{target_id}", response_model=TargetGraphResponse)
def graph_for_target(target_id: str, db: Session = Depends(get_db)):
    """
    Graph view: all generated molecules for a given target,
    along with their closest known drug (if available).
    """
    return get_target_graph(db, target_id)


@app.get("/graph/drug/{drug_name}", response_model=DrugGraphResponse)
def graph_for_drug(drug_name: str, db: Session = Depends(get_db)):
    """
    Graph view: all generated molecules across all targets
    that are similar to a given known drug.
    """
    return get_drug_graph(db, drug_name)


@app.get("/runs/{run_id}", response_model=DiscoveryResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    from .schemas import ADMETProperties, SimilarDrug

    run = db.query(DiscoveryRun).filter(DiscoveryRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    mol_objs = []
    for m in sorted(run.molecules, key=lambda m: m.score, reverse=True):
        # Rebuild ADMET from saved DB columns
        admet = None
        if m.admet_mw is not None:
            admet = ADMETProperties(
                molecular_weight=m.admet_mw,
                logp=m.admet_logp,
                hbd=m.admet_hbd,
                hba=m.admet_hba,
                rotatable_bonds=m.admet_rotatable_bonds or 0,
                tpsa=m.admet_tpsa,
                lipinski_violations=m.admet_lipinski_violations or 0,
                lipinski_pass=bool(m.admet_lipinski_pass),
            )

        # Rebuild fingerprint similar drug from saved DB columns
        fp_neighbor = None
        if m.similar_drug_fp:
            fp_neighbor = SimilarDrug(
                name=m.similar_drug_fp,
                smiles="",
                similarity=m.tanimoto_fp or 0.0,
            )

        # Rebuild semantic similar drug from saved DB columns
        sem_neighbor = None
        if m.similar_drug_semantic:
            sem_neighbor = SimilarDrug(
                name=m.similar_drug_semantic,
                smiles="",
                similarity=0.0,
                semantic_similarity=m.tanimoto_semantic,
            )

        mol_objs.append(
            MoleculeSchema(
                smiles=m.smiles,
                score=m.score,
                source=m.scorer_used or m.source,
                notes=m.notes,
                similar_drug=fp_neighbor,
                similar_drug_semantic=sem_neighbor,
                admet=admet,
            )
        )

    return DiscoveryResponse(
        run_id=cast(str, run.id),
        target_id=cast(str, run.target_id),
        num_molecules=cast(int, run.num_molecules),
        molecules=mol_objs,
    )


@app.get("/runs/{run_id}/export")
def export_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(DiscoveryRun).filter(DiscoveryRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "smiles", "score", "scorer_used",
        "similar_drug_fp", "tanimoto_fp",
        "similar_drug_semantic", "tanimoto_semantic",
        "admet_mw", "admet_logp", "admet_hbd", "admet_hba",
        "admet_tpsa", "admet_rotatable_bonds",
        "admet_lipinski_pass", "admet_lipinski_violations"
    ])

    for m in sorted(run.molecules, key=lambda x: x.score, reverse=True):
        writer.writerow([
            m.smiles, m.score, m.scorer_used,
            m.similar_drug_fp, m.tanimoto_fp,
            m.similar_drug_semantic, m.tanimoto_semantic,
            m.admet_mw, m.admet_logp, m.admet_hbd, m.admet_hba,
            m.admet_tpsa, m.admet_rotatable_bonds,
            m.admet_lipinski_pass, m.admet_lipinski_violations
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=run_{run_id[:8]}.csv"}
    )


@app.delete("/runs/{run_id}")
def delete_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(DiscoveryRun).filter(DiscoveryRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    db.delete(run)
    db.commit()
    return {"deleted": run_id}


@app.post("/discover/batch")
def discover_batch(payload: BatchDiscoverRequest, db: Session = Depends(get_db)):
    results = []
    for req in payload.targets:
        try:
            result = run_discovery(req, db)
            results.append({
                "target_id": req.target_id,
                "run_id": result.run_id,
                "num_molecules": result.num_molecules,
                "status": "ok"
            })
        except Exception as e:
            results.append({
                "target_id": req.target_id,
                "status": "error",
                "error": str(e)
            })

    return {
        "total_targets": len(payload.targets),
        "completed": sum(1 for r in results if r["status"] == "ok"),
        "results": results
    }


@app.post("/agent/query")
def agent_query(req: AgentRequest, db: Session = Depends(get_db)):
    from .agents.discovery_agent import run_agent
    return run_agent(req.prompt, db)


@app.post("/chat/message", response_model=ChatResponse)
def chat_message(req: ChatRequest, db: Session = Depends(get_db)):
    from .agents.discovery_agent import run_agent
    import uuid as uuid_lib

    # Get or create session
    session_id = req.session_id or str(uuid_lib.uuid4())
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    history = chat_sessions[session_id]

    # Build context-aware prompt
    if history:
        context = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in history[-6:]
        ])
        full_prompt = f"Previous conversation:\n{context}\n\nNew question: {req.prompt}"
    else:
        full_prompt = req.prompt

    # Run agent
    result = run_agent(full_prompt, db)

    # Save to history
    history.append({"role": "user", "content": req.prompt})
    history.append({"role": "assistant", "content": result["answer"]})
    chat_sessions[session_id] = history

    return ChatResponse(
        session_id=session_id,
        answer=result["answer"],
        steps=result["steps"],
        evidence=result["evidence"],
        history=history,
    )


@app.get("/chat/history/{session_id}")
def chat_history(session_id: str):
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "history": chat_sessions[session_id]}


@app.post("/discover", response_model=DiscoveryResponse)
def discover_molecules(
    payload: DiscoveryRequest,
    db: Session = Depends(get_db),
):
    return run_discovery(payload, db)