#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\agents\discovery_agent.py
"""
ELYSIUM Discovery Agent — LLM-powered via OpenRouter.
Fixed model names for current OpenRouter API (April 2026).
"""

import os
import json
import time
import requests
from typing import List, Dict, Any, Optional, cast
from sqlalchemy.orm import Session
from ..models import DiscoveryRun, MoleculeRecord


# ── Tool implementations ───────────────────────────────────────────────────────

def tool_get_top_molecules(db: Session, target_id: str, limit: int = 5) -> Dict:
    runs = db.query(DiscoveryRun).filter(
        DiscoveryRun.target_id == target_id.upper()
    ).order_by(DiscoveryRun.created_at.desc()).limit(10).all()

    molecules = []
    seen = set()
    for run in runs:
        for m in sorted(run.molecules, key=lambda x: x.score, reverse=True):
            score = float(cast(float, m.score))
            tanimoto_fp = cast(Optional[float], m.tanimoto_fp)
            lipinski_pass = bool(cast(int, m.admet_lipinski_pass))
            if m.smiles not in seen:
                seen.add(m.smiles)
                molecules.append({
                    "smiles": m.smiles,
                    "score": round(score, 3),
                    "scorer": m.scorer_used,
                    "similar_drug_fp": m.similar_drug_fp,
                    "tanimoto_fp": round(tanimoto_fp, 3) if tanimoto_fp is not None else None,
                    "similar_drug_semantic": m.similar_drug_semantic,
                    "admet_mw": m.admet_mw,
                    "admet_logp": m.admet_logp,
                    "admet_lipinski_pass": lipinski_pass,
                    "run_id": run.id[:8],
                })
    molecules.sort(key=lambda x: x["score"], reverse=True)
    return {"target_id": target_id, "molecules": molecules[:limit]}


def tool_get_similar_to_drug(db: Session, drug_name: str, limit: int = 5) -> Dict:
    records = db.query(MoleculeRecord).filter(
        MoleculeRecord.similar_drug_fp == drug_name
    ).order_by(MoleculeRecord.score.desc()).limit(limit).all()

    return {
        "drug_name": drug_name,
        "molecules": [
            {
                "smiles": m.smiles,
                "score": round(float(cast(float, m.score)), 3),
                "tanimoto": round(float(cast(float, m.tanimoto_fp)), 3) if m.tanimoto_fp is not None else None,
                "admet_mw": m.admet_mw,
                "admet_lipinski_pass": bool(cast(int, m.admet_lipinski_pass)),
                "run_id": m.run_id[:8],
            }
            for m in records
        ]
    }


def tool_get_runs_summary(db: Session) -> Dict:
    runs = db.query(DiscoveryRun).all()
    all_mols = db.query(MoleculeRecord).all()
    total = len(all_mols)
    lipinski_pass = sum(1 for m in all_mols if bool(cast(int, m.admet_lipinski_pass)))
    scores = [float(cast(float, m.score)) for m in all_mols]

    return {
        "total_runs": len(runs),
        "total_molecules": total,
        "lipinski_pass_count": lipinski_pass,
        "lipinski_pass_rate_pct": round((lipinski_pass / total) * 100, 1) if total else 0,
        "avg_score": round(sum(scores) / len(scores), 3) if scores else 0,
        "targets_explored": list(set(r.target_id for r in runs)),
    }


def tool_get_admet_stats(db: Session, target_id: str) -> Dict:
    runs = db.query(DiscoveryRun).filter(
        DiscoveryRun.target_id == target_id.upper()
    ).all()
    mols = []
    for run in runs:
        mols.extend(run.molecules)

    if not mols:
        return {"target_id": target_id, "error": "No molecules found"}

    mws   = [float(cast(float, m.admet_mw))   for m in mols if m.admet_mw   is not None]
    logps = [float(cast(float, m.admet_logp))  for m in mols if m.admet_logp is not None]
    tpsas = [float(cast(float, m.admet_tpsa))  for m in mols if m.admet_tpsa is not None]
    passes = sum(1 for m in mols if bool(cast(int, m.admet_lipinski_pass)))

    return {
        "target_id": target_id,
        "total_molecules": len(mols),
        "lipinski_pass": passes,
        "lipinski_pass_rate_pct": round(passes / len(mols) * 100, 1),
        "avg_mw":   round(sum(mws)   / len(mws),   2) if mws   else None,
        "avg_logp": round(sum(logps) / len(logps), 2) if logps else None,
        "avg_tpsa": round(sum(tpsas) / len(tpsas), 2) if tpsas else None,
    }


def execute_tool(tool_name: str, tool_input: Dict, db: Session) -> Any:
    if tool_name == "get_top_molecules":
        return tool_get_top_molecules(db, tool_input.get("target_id", "EGFR"), tool_input.get("limit", 5))
    elif tool_name == "get_similar_to_drug":
        return tool_get_similar_to_drug(db, tool_input.get("drug_name", ""), tool_input.get("limit", 5))
    elif tool_name == "get_runs_summary":
        return tool_get_runs_summary(db)
    elif tool_name == "get_admet_stats":
        return tool_get_admet_stats(db, tool_input.get("target_id", "EGFR"))
    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ── LLM call via OpenRouter ────────────────────────────────────────────────────

def call_llm(messages: List[Dict], api_key: str) -> str:
    # Updated model IDs — verified working on OpenRouter as of April 2026
    models = [
        "google/gemini-2.0-flash-lite-001",
        "google/gemma-3-4b-it",
        "google/gemma-3-12b-it",
        "meta-llama/llama-3.2-3b-instruct",
        "meta-llama/llama-3.1-8b-instruct",
        "qwen/qwen-2.5-7b-instruct",
        "microsoft/phi-3-mini-128k-instruct",
        "mistralai/mistral-small-3.1-24b-instruct",
        "meta-llama/llama-3.3-70b-instruct",
    ]

    last_error = None
    for model in models:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5173",
                    "X-Title": "ELYSIUM Drug Discovery",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "messages": messages,
                },
                timeout=30,
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                if content and len(content.strip()) > 0:
                    return content

            elif response.status_code == 429:
                last_error = f"{model}: rate-limited (429) — trying next"
                continue  # skip immediately

            elif response.status_code == 404:
                last_error = f"{model}: not found (404) — trying next"
                continue  # model renamed or removed

            else:
                last_error = f"{model} returned {response.status_code}: {response.text[:150]}"

        except requests.Timeout:
            last_error = f"{model}: timeout"
            continue
        except Exception as e:
            last_error = str(e)
            continue

        time.sleep(0.3)

    raise Exception(f"All models failed. Last error: {last_error}")


# ── Main agent ─────────────────────────────────────────────────────────────────

def run_agent(prompt: str, db: Session) -> Dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return {
            "prompt": prompt,
            "steps": ["No OPENROUTER_API_KEY found in .env"],
            "evidence": [],
            "answer": "Agent not configured. Add OPENROUTER_API_KEY to your .env file."
        }

    steps = []
    evidence = []

    # Step 1 — Ask LLM which tool to call
    tool_selection_prompt = f"""You are a drug discovery AI assistant with access to these tools:

1. get_top_molecules(target_id, limit) — get top scoring molecules for a protein target
2. get_similar_to_drug(drug_name, limit) — find molecules similar to a known drug
3. get_runs_summary() — get statistics across all discovery runs
4. get_admet_stats(target_id) — get ADMET property statistics for a target

User question: {prompt}

Respond with ONLY a JSON object selecting the best tool(s) to answer this question.
Format:
{{
  "tools": [
    {{"name": "tool_name", "input": {{"param": "value"}}}}
  ],
  "reasoning": "brief explanation"
}}

Available targets: EGFR, BRAF, KRAS, ALK, TP53
Available drugs: Ibuprofen, Aspirin, Paracetamol, Caffeine, Lidocaine, Propranolol, Gefitinib, Erlotinib

Only respond with valid JSON. No other text."""

    messages = [{"role": "user", "content": tool_selection_prompt}]

    try:
        tool_selection_response = call_llm(messages, api_key)
        steps.append(f"LLM tool selection: {tool_selection_response[:200]}")

        # Parse JSON from LLM response
        clean = tool_selection_response.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        tool_plan = json.loads(clean)
        reasoning = tool_plan.get("reasoning", "")
        steps.append(f"Agent reasoning: {reasoning}")

        # Step 2 — Execute tools
        tool_results = []
        for tool_call in tool_plan.get("tools", []):
            tool_name  = tool_call["name"]
            tool_input = tool_call.get("input", {})
            steps.append(f"Executing: {tool_name}({tool_input})")

            result = execute_tool(tool_name, tool_input, db)
            evidence.append({"tool": tool_name, "input": tool_input, "result": result})
            tool_results.append(f"Tool {tool_name} returned: {json.dumps(result)}")

        # Step 3 — Synthesise answer
        synthesis_prompt = f"""You are ELYSIUM, an AI drug discovery assistant.

The user asked: {prompt}

You retrieved this data from the molecular database:
{chr(10).join(tool_results)}

Write a clear, informative answer for a drug discovery researcher.
Explain the scientific significance. Use the actual numbers. Be specific."""

        try:
            final_answer = call_llm([{"role": "user", "content": synthesis_prompt}], api_key)
            steps.append("LLM synthesised final answer from tool results")
        except Exception:
            steps.append("LLM synthesis failed — returning structured data")
            final_answer = (
                f"Retrieved {len(evidence)} tool results.\n\n"
                + "\n\n".join(
                    f"**{e['tool']}**: {json.dumps(e['result'], indent=2)}"
                    for e in evidence
                )
            )

        return {
            "prompt": prompt,
            "steps": steps,
            "evidence": evidence,
            "answer": final_answer,
        }

    except json.JSONDecodeError as e:
        steps.append(f"JSON parse error: {e}")
        return {
            "prompt": prompt,
            "steps": steps,
            "evidence": evidence,
            "answer": "Agent could not parse tool selection. Try rephrasing your question."
        }
    except Exception as e:
        steps.append(f"Agent error: {str(e)}")
        return {
            "prompt": prompt,
            "steps": steps,
            "evidence": evidence,
            "answer": f"Agent encountered an error: {str(e)}"
        }