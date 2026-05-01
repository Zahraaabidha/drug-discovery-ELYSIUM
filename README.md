# 🌌 ELYSIUM — AI-Driven Drug Discovery Toolkit  
**An agentic, modular platform for small-molecule discovery powered by  
FastAPI · ArangoDB · RDKit · DeepPurpose · FAISS · React + Tailwind**

---

## 🚀 1. Overview

**ELYSIUM** is a next-generation **AI-driven drug discovery and knowledge-graph system**, designed to generate, score, and analyze small-molecule candidates for a target protein.

Its pipeline integrates:

- **Molecular generation (stubbed generator → pluggable transformer later)**
- **DeepPurpose-based DTI scoring**
- **RDKit ADMET + Lipinski filtering**
- **Chemical + semantic similarity search (fingerprint + chemBERTa)**
- **Graph-structured knowledge storage (ArangoDB + SQL KG)**
- **FAISS vector index for semantic retrieval**
- **Async discovery jobs with background processing**
- **Interactive React/Tailwind UI**

The goal is to create a **realistic, extensible drug discovery agent** capable of:
- Querying targets  
- Generating molecules  
- Ranking multi-objectively  
- Linking results across a biological knowledge graph  
- Responding to natural language queries (*planned in Phase 8*)

---

## 🎯 2. Problem Statement

Modern drug discovery suffers from:

### ❗ Slow, expensive molecule screening  
Wet-lab screening is costly and often requires months.

### ❗ Poor integration between models & data  
AI tools generate molecules, but connecting them to:
- targets  
- known drugs  
- ADMET  
- structural similarity  
is difficult.

### ❗ Lack of explainability  
Researchers need *why* a molecule was chosen, not just *what*.

### **ELYSIUM solves these problems by unifying generation, scoring, similarity, ADMET, and graph-based reasoning into one workflow.**

---

## 🏥 3. Target Industry  
- **Industry:** Pharmaceutical · Biotechnology  
- **Type:** B2B  
- **User Group:** Computational chemists, AI drug-discovery researchers  
- **Department:** R&D / Computational Biology / Discovery Informatics  

---

## 🧪 4. Solution Scenario (User Flow)

1. User enters a **target protein ID** (e.g., *EGFR*).  
2. System generates **candidate SMILES molecules**.  
3. DeepPurpose scores binding affinity.  
4. RDKit performs **Lipinski + ADMET filtering**.  
5. Similarity engine finds **closest known drug** (fingerprint + chemBERTa).  

