# SIH26117 — Sovereign On-Premise Agentic AI Workbench for MRPL

[![Smart India Hackathon 2026](https://img.shields.io/badge/SIH-2026-blue.svg)](https://www.sih.gov.in/)
[![Sponsor: MRPL](https://img.shields.io/badge/Sponsor-MRPL-green.svg)](https://www.mrpl.co.in/)
[![Architecture: Air--Gapped Sovereign](https://img.shields.io/badge/Security-Air--Gapped%20Sovereign-red.svg)]()
[![Hardware: Dev Tier 8GB VRAM](https://img.shields.io/badge/Hardware-RTX%204060%208GB-orange.svg)]()

> **Problem Statement ID:** SIH26117  
> **Problem Statement Title:** Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs for Confidential Industrial Work  
> **Sponsoring Organization:** Mangalore Refinery and Petrochemicals Limited (MRPL)  
> **Category:** Software / Smart Automation  

---

## 1. Executive Overview

Continuous-process hydrocarbon refining facilities such as Mangalore Refinery and Petrochemicals Limited (MRPL), defense manufacturing units, and public sector undertakings (PSUs) generate high volumes of sensitive operational data. This data includes:
- **Piping & Instrumentation Diagrams (P&IDs)** and mechanical schematics
- **Crude assay valuations** and linear programming blend models
- **Turnaround and shutdown schedules**
- **Commercial vendor bids and procurement evaluations**
- **Non-Destructive Testing (NDT) logs** and ultrasonic wall-thinning reports

Under Indian regulatory frameworks (NCIIPC, CERT-In, DPDPA, and OISD-163), this intelligence cannot be transmitted across public networks or processed via commercial cloud LLMs (such as ChatGPT, Claude, or public APIs). 

The **Sovereign On-Premise Agentic AI Workbench** is an enterprise-grade, air-gapped solution engineered to execute strictly within an organization's physical perimeter on local GPU infrastructure. It replaces shadow AI practices with an automated, sovereign platform that decomposes complex engineering workflows, routes tasks across specialized open-weight models, and produces verified, deterministic Office deliverables.

---

## 2. Core MVP Capabilities

The MVP demonstrates 5 non-negotiable architectural capabilities:

1. **Sovereign / Air-Gapped Operation:** Zero outbound internet calls or telemetry. Network isolation verified via active internal socket monitoring and verifiable audit logs.
2. **Dynamic Multi-Model Routing:** Transparent task classification directing inputs to specialized open-weight models (reasoning, coding, vision) rather than routing everything through a single monolithic model.
3. **Multi-Step Agentic Execution:** Explicit state-machine agent loop (Plan $\rightarrow$ Act $\rightarrow$ Observe $\rightarrow$ Reflect) executing local tools (file I/O, sandboxed computation, knowledge retrieval) with intermediate visibility.
4. **Multimodal Industrial Document Processing:** Localized extraction and visual question-answering for technical documents, tabular inspection logs, and engineering schematics.
5. **Deterministic Office Deliverable Generation:** Generation of production-grade Microsoft Word (`.docx`), Excel (`.xlsx`), and PowerPoint (`.pptx`) deliverables via deterministic Python engines validating structured Pydantic outputs (never raw LLM file generation).

---

## 3. High-Level Architecture

```
                       [ Web Frontend (React + TypeScript + Vite) ]
                                            │
                                            ▼
                              [ FastAPI Gateway / Router ]
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
          [ Dynamic Task Router ]                        [ Audit & Logging Engine ]
        (Classifies intent & domain)                   (Zero-leakage event ledger)
                     │
                     ▼
          [ Agent Orchestrator ] ◄───────────────────────┐
       (Explicit State-Machine Engine)                   │
                     │                                   │ Tool Feedback
       ┌─────────────┼─────────────┬─────────────┐       │
       ▼             ▼             ▼             ▼       │
   [ RAG /      [ Ingestion   [ Sandboxed    [ Deliverable ─┘
  Knowledge ]     & Vision ]    Python ]      Generator ]
                                               (.docx, .xlsx, .pptx)
                     │
                     ▼
        [ Local Model Manager ]
      (Unified ModelHandle Interface)
      (Serial Swapping / Colocation)
                     │
                     ▼
   [ Local Inference Engine (Ollama / llama.cpp / vLLM) ]
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   [Reasoning]    [Coding]     [Vision]
   DeepSeek-R1   Qwen2.5-     Qwen2.5-VL
     Distill       Coder
```

---

## 4. Hardware Strategy & Tiers

To ensure practical development while accommodating the competition target specification:

| Parameter | Dev Tier (Local Development) | Target Tier (Demonstrator / Lab) |
| :--- | :--- | :--- |
| **Hardware** | Laptop (16 GB RAM, RTX 4060 8 GB VRAM) | Workstation / Edge Server (24–48 GB VRAM) |
| **Execution Pattern** | **Serial Model Swapping:** One active model in VRAM at a time with fast offload | **Quantized Colocation:** 2–3 co-resident models in VRAM via PagedAttention |
| **Reasoning Model** | DeepSeek-R1-Distill-Qwen-7B (Q4_K_M, ~4.8 GB) | DeepSeek-R1-Distill-Qwen-14B / 32B |
| **Vision Model** | Qwen2.5-VL-3B-Instruct (Q4, ~3.2 GB) | Qwen2.5-VL-7B-Instruct (AWQ / FP8) |
| **Coding Model** | Qwen2.5-Coder-3B-Instruct (Q4, ~2.5 GB) | Qwen2.5-Coder-14B-Instruct |
| **Embeddings** | bge-small-en-v1.5 / nomic-embed-text (CPU / 0.2 GB) | bge-base-en-v1.5 / ColPali |

---

## 5. Directory Structure

```
SIH 2026/
├── backend/                  # FastAPI backend server
│   ├── app/
│   │   ├── api/              # HTTP and WebSocket route definitions
│   │   ├── core/             # Configuration, settings, security & air-gap guards
│   │   ├── models/           # Internal domain entities and DB definitions
│   │   ├── schemas/          # Pydantic schemas for validation and structured output
│   │   ├── services/         # Modular service layer
│   │   │   ├── router/       # Dynamic task router & intent classifier
│   │   │   ├── agent/        # State-machine agent orchestrator
│   │   │   ├── model_manager/# Unified ModelHandle interface & memory swapper
│   │   │   ├── rag/          # Local vector storage and dense retrieval
│   │   │   ├── ingestion/    # Document parser (PDF, text, OCR pipeline)
│   │   │   ├── vision/       # Multimodal visual analysis for schematics & logs
│   │   │   ├── sandbox/      # Safe local Python code execution engine
│   │   │   ├── deliverables/ # Deterministic Office builders (.docx, .xlsx, .pptx)
│   │   │   ├── audit/        # Tamper-evident logging and provenance trail
│   │   │   └── network/      # Host network monitor proving air-gapped operation
│   │   └── main.py           # FastAPI entry point
│   ├── tests/                # Automated unit and integration tests
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Environment variable template
│
├── frontend/                 # React + TypeScript + Vite user interface
│   ├── src/
│   │   ├── components/       # Reusable UI widgets (Agent graph, chat, file viewer)
│   │   ├── pages/            # View pages (Workbench, Deliverables, Audit, System)
│   │   ├── services/         # Backend API client bindings
│   │   ├── hooks/            # Custom React state hooks
│   │   ├── types/            # TypeScript interface definitions
│   │   └── App.tsx           # Main application shell
│   ├── public/               # Static assets
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Vite configuration and backend proxy
│
├── data/                     # Local data management (strictly ignored in git)
│   ├── raw/                  # Unprocessed incoming documents & P&IDs
│   ├── processed/            # Chunked text, normalized tables & crops
│   ├── knowledge/            # Sovereign vector index and RAG document store
│   └── samples/              # Test industrial sheets, sample P&IDs, NDT logs
│
├── models/                   # Model management and configuration
│   ├── configs/              # Tier configs (dev vs target) and model manifests
│   └── README.md             # Model procurement and quantization documentation
│
├── outputs/                  # Deterministically generated Office artifacts
│   ├── docx/                 # Generated executive memos & engineering notes
│   ├── xlsx/                 # Generated spreadsheets with active formulas
│   └── pptx/                 # Generated executive presentations
│
├── logs/                     # Local audit trails, routing decisions & network events
├── scripts/                  # Utility and setup automation scripts
│
├── experiments/              # Google Colab / standalone research and evaluation
│   ├── router/               # Router dataset, prompt benchmarks, routing accuracy
│   ├── rag/                  # Retrieval chunking experiments and evaluation
│   └── vision/               # Engineering drawing and OCR evaluation
│
├── docs/                     # Comprehensive documentation
│   ├── architecture/         # Architectural design decisions and data flows
│   ├── api/                  # API specifications and payload contracts
│   └── demo/                 # Demonstration runbooks and presentation material
│
├── docker/                   # Air-gapped container configurations
├── .gitignore                # Git exclusions (credentials, weights, outputs)
├── README.md                 # Project README
└── docker-compose.yml        # Air-gapped container composition placeholder
```

---

## 6. Architectural Principles

1. **Modular Decoupling:** Core logic does not depend directly on any single model family or API. The Model Manager provides a generic `ModelHandle` interface.
2. **Separation of Router and Agent:** The Router decides *which model/capability* executes a query; the Agent Orchestrator decides the *sequence of operational steps*.
3. **Structured Intermediate Representation:** LLMs output validated JSON conformant to Pydantic schemas. Python engines deterministically render `.docx`, `.xlsx`, and `.pptx` documents with native styles and formulas.
4. **Zero-Leakage Sovereign Ingestion:** Original uploaded files are preserved in an immutable state for auditing. No external telemetry or cloud fallbacks are permitted.
5. **Observable Execution Loop:** Every state transition in the agent orchestrator emits an event visible in the UI and recorded in the audit trail.

---

## 7. Getting Started

### Prerequisites
- Windows 11 / Linux
- NVIDIA GPU with CUDA support (e.g., RTX 4060 with $\ge$ 8 GB VRAM)
- Python 3.11+
- Node.js 22+
- [Ollama](https://ollama.ai/) installed locally

### Backend Setup (Development)
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Verification
Access the API health endpoint:
```
http://127.0.0.1:8000/health
```

---

## 8. License & Attribution
Developed for **Smart India Hackathon 2026** by Team for **Mangalore Refinery and Petrochemicals Limited (MRPL)**.
