# SIH26117 — Sovereign On-Premise Agentic AI Workbench
## Complete Implementation Plan & Architecture Design (SIH 2026)

> **Problem Statement:** SIH26117 — Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs for Confidential Industrial Work
> **Sponsor:** Mangalore Refinery and Petrochemicals Limited (MRPL)
> **Prepared for:** SIH 2026 submission
> **Dev hardware:** Laptop — 16 GB RAM, NVIDIA RTX 4060 (8 GB VRAM)
> **Target/demo hardware (per PS):** Single workstation / edge server, 24–48 GB VRAM

---

## 0. How to use this document

This is written as a build plan, not just a theory report. Every section ends with **concrete artifacts** (files, configs, folders) you need to actually create. Nothing here is fixed — models, libraries, and even module boundaries can change as you build. What must **not** change is the set of non-negotiable judge-facing proofs (Section 12).

Since you said you don't want "just a report agent," this plan treats the workbench as a **real product with a UI, a backend, a router, an agent runtime, a sandbox, and a document factory** — not a single prompt-chaining script.

---

## 1. One-Line Pitch (memorize this)

> "A private, on-premise AI workbench for refineries and PSUs that never sends data outside the building — it automatically picks the right local model for each task, acts like an agent that plans and executes multi-step work using local tools, understands scanned reports and P&IDs, and hands back a finished Word/Excel/PPT file instead of just a chat reply."

---

## 2. Core Design Principles (write these on your architecture slide)

1. **Sovereignty by construction, not by policy.** Network isolation is enforced at the OS/container level, not just "we promise not to call the internet."
2. **Model-agnostic core.** The orchestrator never hardcodes a model name in business logic — it calls a `ModelHandle` interface. Swapping Qwen for Llama or a future model is a config change, not a code change.
3. **Router-first, not router-as-afterthought.** The router is a first-class subsystem with its own training data, its own evaluation set, its own fallback logic — not an `if "code" in prompt` statement.
4. **Two-tier hardware profile.** Everything you build must run in a **Dev Tier** (your 8 GB laptop) and scale to a **Target Tier** (24–48 GB workstation) via one config file, not a rewrite.
5. **Deterministic outputs, probabilistic reasoning.** LLMs decide *what* the answer is; plain Python code deterministically produces *the file*. Never let an LLM directly emit binary Office bytes.
6. **Agent, not chatbot.** Every non-trivial request goes through Plan → Act → Observe → Reflect, with visible intermediate steps (this is also your best demo material).
7. **Prove it, don't claim it.** Every security/sovereignty claim must have a corresponding dashboard metric or log artifact a judge can look at live.

---

## 3. Two-Tier Hardware Strategy (the detail most teams miss)

This is the single most important practical decision, because your dev machine (8 GB VRAM) cannot run the 14B–32B models the original research report recommends. Design for **both tiers from day one** using one `config/model_tiers.yaml` file that the Router and Model Manager read at startup.

### 3.1 Tier definitions

| Tier | Hardware | Purpose | Concurrency strategy |
|---|---|---|---|
| **Dev Tier** | Your laptop: 16 GB RAM, RTX 4060 8 GB VRAM | Daily development, unit tests, offline demo recording | One model resident in VRAM at a time; aggressive Q4 quantization; CPU-offload for anything vision-heavy |
| **Target Tier** | 24 GB workstation (RTX 3090/4090/A4000-5000) — borrow from college lab, rent a cloud GPU box for finale week, or use SIH-provided hardware if any | Grand Finale demo, judge-facing benchmarks | 2–3 models co-resident via quantized colocation + PagedAttention (vLLM) |
| **Stretch Tier** | 48 GB (A6000 / dual 4090) | Only mentioned in report/slides as "roadmap", not required to build | Full concurrent 32B reasoning + VL + coder |

**Practical note:** You do NOT need to buy a 24 GB GPU. Options, cheapest first: (a) college/lab workstation, (b) short-term GPU rental (RunPod/Vast.ai/Lambda — a few hours around demo day), (c) present Dev Tier live + a recorded Target Tier run as backup evidence. Judges care about **architecture that scales**, not that you personally own a 4090.

### 3.2 Dev Tier model set (fits comfortably in 8 GB, most run 4–6 GB)

| Role | Dev Tier model | Format | Approx VRAM |
|---|---|---|---|
| Router / planner (fast) | Qwen2.5-1.5B-Instruct or Llama-3.2-3B-Instruct | GGUF Q4_K_M | 1–2 GB |
| Reasoning (engineering calc) | DeepSeek-R1-Distill-Qwen-7B | GGUF Q4_K_M | ~4.5–5 GB |
| Coding | Qwen2.5-Coder-3B-Instruct (or 7B if swapped in serially) | GGUF Q4_K_M | 2–4.5 GB |
| Vision / OCR | Qwen2.5-VL-3B-Instruct | GGUF/AWQ Q4 | ~3–4 GB |
| Embeddings (RAG) | bge-small-en-v1.5 or nomic-embed-text | FP16, runs fine on CPU | ~0.2 GB / CPU |
| Reranker | bge-reranker-base | INT8, CPU is fine | CPU |
| Visual doc retrieval | Skip full ColPali on dev tier — use PyMuPDF text+layout extraction + direct VLM crop QA as a substitute (see 6.4) | — | — |

**Rule for the laptop:** never load two 3B+ models into VRAM simultaneously. Use **serial model swapping** (llama.cpp / Ollama `keep_alive` unload, or vLLM `--enforce-eager` + process restart) — the Model Manager (Section 5.3) hides this behind one interface so the rest of the app never notices.

### 3.3 Target Tier model set (from the research report, unchanged)

| Role | Model | VRAM |
|---|---|---|
| Planning/routing | DeepSeek-R1-Distill-Llama-8B | 6–8 GB |
| Deep reasoning | DeepSeek-R1-Distill-Qwen-14B (32B if 48 GB available) | 10–24 GB |
| Coding | Qwen2.5-Coder-7B/14B-Instruct | 6–12 GB |
| Vision/OCR | Qwen2.5-VL-7B-Instruct | 8–14 GB |
| Visual retrieval | ColPali (PaliGemma-based) | 4–6 GB |

Config sketch:

```yaml
# config/model_tiers.yaml
active_tier: dev   # dev | target | stretch
tiers:
  dev:
    max_concurrent_models: 1
    router_model: qwen2.5-1.5b-instruct-q4
    reasoning_model: deepseek-r1-distill-qwen-7b-q4
    coder_model: qwen2.5-coder-3b-instruct-q4
    vision_model: qwen2.5-vl-3b-instruct-q4
    embed_model: bge-small-en-v1.5
    visual_retrieval: disabled
  target:
    max_concurrent_models: 3
    router_model: deepseek-r1-distill-llama-8b
    reasoning_model: deepseek-r1-distill-qwen-14b
    coder_model: qwen2.5-coder-14b-instruct
    vision_model: qwen2.5-vl-7b-instruct
    embed_model: bge-base-en-v1.5
    visual_retrieval: colpali
```

**Artifact to create now:** `config/model_tiers.yaml`, `config/README.md` explaining tier switching.

---

## 4. High-Level System Architecture

```
                                   ┌───────────────────────────┐
                                   │        USER (Browser)     │
                                   └──────────────┬────────────┘
                                                  │ HTTPS (localhost / LAN only)
                                   ┌──────────────▼────────────┐
                                   │      FRONTEND (React)     │
                                   │  Chat + Task Timeline UI  │
                                   │  + Sovereignty Dashboard  │
                                   └──────────────┬────────────┘
                                                  │ REST/WebSocket
                                   ┌──────────────▼────────────┐
                                   │     API GATEWAY (FastAPI) │
                                   │  Auth · Rate limit · Logs │
                                   └──────────────┬────────────┘
                                                  │
                     ┌────────────────────────────┼────────────────────────────┐
                     │                            │                            │
           ┌─────────▼─────────┐        ┌─────────▼─────────┐        ┌─────────▼─────────┐
           │  INGESTION LAYER  │        │   ADVANCED ROUTER │        │   AGENT ORCHESTRATOR │
           │ PDF/Image/Text    │        │ (Sec. 7)          │        │ Plan-Act-Observe    │
           │ OCR + layout      │        └─────────┬─────────┘        │ -Reflect loop        │
           └─────────┬─────────┘                  │                  └─────────┬─────────┘
                     │                            ▼                            │
                     │                  ┌────────────────────┐                 │
                     │                  │   MODEL MANAGER    │◄────────────────┘
                     │                  │ (load/unload/serve) │
                     │                  └─────────┬──────────┘
                     │                            │
        ┌────────────┴──────┬──────────┬──────────┴─────────┬──────────────┐
        ▼                   ▼          ▼                    ▼              ▼
 ┌─────────────┐   ┌────────────────┐ ┌────────────┐ ┌───────────────┐ ┌──────────────┐
 │ RAG ENGINE  │   │ VISION / P&ID  │ │ CODER MODEL│ │ REASONING MDL │ │ ROUTER MODEL │
 │ Hybrid      │   │ PIPELINE       │ │            │ │               │ │ (fast/small) │
 │ BM25+Vector │   │ OCR+Symbol+RAG │ └──────┬─────┘ └───────────────┘ └──────────────┘
 └──────┬──────┘   └────────┬───────┘        │
        │                   │                ▼
        │                   │         ┌───────────────────┐
        │                   │         │  SECURE SANDBOX    │
        │                   │         │  gVisor, no network │
        │                   │         │  ephemeral tmpfs    │
        │                   │         └─────────┬──────────┘
        │                   │                   │
        └───────────┬───────┴───────────────────┘
                     ▼
           ┌───────────────────────┐
           │  STRUCTURED JSON      │
           │  (Pydantic-validated) │
           └──────────┬────────────┘
                       ▼
           ┌───────────────────────┐
           │ DOCUMENT FACTORY      │
           │ python-docx/xlsx/pptx │
           └──────────┬────────────┘
                       ▼
           ┌───────────────────────┐
           │   FINAL DELIVERABLE   │
           │  .docx / .xlsx / .pptx│
           └───────────────────────┘

  Cross-cutting (touches everything):
  🔒 NETWORK POLICY: default-deny egress, loopback-only for sandbox
  📊 OBSERVABILITY: GPU/VRAM, active model, sandbox syscalls, net bytes = 0
  🗄️ STORAGE: Postgres (metadata) + Qdrant/Chroma (vectors) + local disk (files)
  🪵 AUDIT LOG: every model call, tool call, file write — append-only
```

**Artifact to create now:** put this diagram (as an actual image, exported from draw.io/Excalidraw) into `docs/architecture.png` for your PPT — ASCII is fine for GitHub README but judges want a clean visual.

---

## 5. Module-by-Module Breakdown

### 5.1 Ingestion & Preprocessing Layer
**Purpose:** Turn any uploaded artifact into a normalized internal representation before anything else touches it.

- Accepts: PDF (native + scanned), DOCX, XLSX, PNG/JPG, CSV.
- Steps: file-type sniff → virus/malformed-file check → text-layer extraction (PyMuPDF) → if no text layer or low text density, mark as "scan" → route to OCR/Vision.
- Splits multi-page PDFs into per-page objects tagged with `page_id`, `has_text_layer`, `is_drawing` (heuristic: high line-density + low text-density → likely P&ID/schematic).
- **Basic detail people miss:** always store the *original file hash* (SHA-256) and keep an immutable copy in `storage/raw/`. Every downstream artifact references this hash, so you can always answer "which source produced this number" — critical for an audit-friendly PSU tool.

**Tech:** PyMuPDF (fitz), pdfplumber, Pillow, python-magic.
**Artifact:** `services/ingestion/`, `storage/raw/`, `storage/processed/`.

### 5.2 Advanced Router — see dedicated Section 7 (the centerpiece).

### 5.3 Model Manager
**Purpose:** Single choke-point that hides "which tier, which quantization, is it loaded" from the rest of the app.

- Exposes one interface: `ModelManager.get(role: str) -> ModelHandle`, where `role` is `"router" | "reasoning" | "coder" | "vision" | "embed"`.
- Internally decides: is target model already resident? If VRAM budget (from `model_tiers.yaml`) would be exceeded, **evict least-recently-used model first** (simple LRU), then load requested one.
- Wraps both llama.cpp/Ollama (dev tier, GGUF) and vLLM (target tier, AWQ/FP8) behind the same interface using an adapter pattern.
- Emits load/unload events to the Observability bus (Section 5.9) — this is what powers your live "active model" dashboard tile.

**Basic detail people miss:** set a **hard VRAM ceiling with headroom** (e.g., budget 6.5 GB usable out of 8 GB on the laptop) so you don't hit OOM mid-demo. Always test the worst-case combination (biggest reasoning model + biggest vision model requested back-to-back).

**Tech:** llama-cpp-python or Ollama HTTP API (dev), vLLM OpenAI-compatible server (target).
**Artifact:** `services/model_manager/manager.py`, `services/model_manager/adapters/{llamacpp.py, vllm.py}`.

### 5.4 Agent Orchestrator
**Purpose:** The "not just a report generator" part. Converts a user goal into a DAG of tool calls, executes it, checks results, retries on failure.

Loop per task:
1. **Plan:** router-model/planner produces a JSON plan: ordered list of `{step, tool, inputs, depends_on}`.
2. **Act:** orchestrator executes each step by calling a tool (RAG search, sandbox exec, vision extract, calculator, doc generator).
3. **Observe:** captures stdout/stderr/return JSON from the tool.
4. **Reflect:** a lightweight check step — did the calculation error out? Does a value violate a sanity bound (e.g., negative wall thickness)? If yes, re-plan that step (max 2 retries), else continue.
5. **Finalize:** once all steps succeed, compiled data goes to the Document Factory.

Represent plans as an explicit DAG (not a hidden chain-of-thought) so you can **render the plan in the UI live** — this is genuinely one of your best demo moments ("watch the agent decide what to do").

**Basic detail people miss:** cap total steps (e.g., 12) and total wall-clock time (e.g., 90s on dev tier) per task with a hard timeout, and always surface *why* an agent stopped (max retries / timeout / user cancel) instead of hanging silently.

**Tech:** plain Python state machine (don't over-engineer with a heavy agent framework at first — LangGraph is fine later, but a 200-line explicit state machine is easier to debug and demo).
**Artifact:** `services/agent/planner.py`, `services/agent/executor.py`, `services/agent/tools/`.

### 5.5 RAG / Knowledge Layer
**Purpose:** Ground answers in the org's own SOPs/manuals/history instead of the model's memory.

- **Hybrid retrieval:** BM25 (exact tag numbers like `P-204A`) + dense embeddings (semantic match, e.g. "pump overheating" → "excessive temperature at centrifugal pump").
- **Chunking:** page-aware, table-aware (don't blindly split mid-table); keep page image reference alongside text chunk so vision fallback is possible.
- **Reranking:** cross-encoder reranker on top-k candidates before they enter the LLM context — this alone measurably reduces hallucination.
- **Source citation:** every RAG answer must carry `{doc_id, page, chunk_id}` so the UI can show "grounded in: Maintenance-SOP-14.pdf, p.7".

**Tech:** BM25 via `rank_bm25` or Elasticsearch-lite (Tantivy/Meilisearch also fine and light), embeddings via bge-small (dev) / bge-base (target), Qdrant or Chroma as vector store, `bge-reranker` for reranking.
**Artifact:** `services/rag/index.py`, `services/rag/hybrid_search.py`, `services/rag/rerank.py`.

### 5.6 Multimodal / P&ID Vision Pipeline
**Purpose:** Handle scanned reports, handwritten logs, and dense engineering drawings — the hardest input type.

Sub-pipeline for P&IDs specifically (four-layer decomposition per the source research):
1. **Tiling:** split large-format drawings into overlapping high-res tiles (native VLMs downscale and lose small text/symbols — tiling avoids this).
2. **Text/tag OCR:** PaddleOCR or CRAFT on tiles for equipment tags, loop numbers.
3. **Symbol detection:** a small fine-tuned YOLO (or, if time-limited, a curated template-matching pass) for valves/pumps/instrument bubbles.
4. **Line tracing:** skeletonization to connect pipe segments across tiles into a graph (equipment ↔ pipe ↔ instrument).
5. **Graph assembly:** merge into a `networkx` graph so questions like "what feeds P-204A?" become a graph traversal, not a vague vision-model guess.

**Dev Tier reality check:** full ColPali + fine-tuned YOLO is a lot for an 8 GB laptop and a hackathon timeline. Prioritize in this order: (1) OCR + tag extraction — do this well, it's 80% of the value; (2) basic symbol detection on a hand-picked template library; (3) line tracing/graph — **build this as a stretch goal**, demo it on 1–2 curated sample P&IDs even if it's not fully general. Judges reward a working narrow demo over a broken general one.

**Tech:** PaddleOCR, OpenCV (skeletonization/morphology), networkx, Qwen2.5-VL for fallback natural-language QA over cropped regions.
**Artifact:** `services/vision/pid_pipeline/`, `services/vision/ocr.py`.

### 5.7 Secure Sandbox (Code Execution)
**Purpose:** Let the agent run Python/SQL for calculations without risking the host.

- Runtime: **gVisor (runsc)** as a drop-in Docker runtime replacement — best balance of isolation and latency for a single-workstation deployment (per the research report's own comparison table).
- Network: `--network none`; sandbox literally has no route to anywhere, verified by eBPF socket-syscall tracing (`tcp_v4_connect`, `udp_sendmsg`) logged to the audit trail.
- Filesystem: read-only root, `tmpfs` scratch space wiped on container exit; only whitelisted output files get copied back out.
- Resource limits: CPU/memory/PID caps via cgroups to block fork bombs / resource exhaustion.
- Library allowlist: only pre-approved packages (numpy, pandas, scipy, matplotlib) available inside the sandbox image — no `pip install` at runtime.

**Basic detail people miss:** log **every** sandbox invocation (code text, exit code, duration, stdout/stderr, byte count in/out) to an append-only audit log — this single log file is your strongest "trust us" artifact for judges and for a real PSU security team.

**Tech:** Docker + gVisor runtime, eBPF (bcc/bpftrace) for syscall tracing, cgroups v2.
**Artifact:** `sandbox/Dockerfile`, `sandbox/runsc_config.toml`, `services/sandbox/runner.py`, `logs/sandbox_audit.jsonl`.

### 5.8 Document Factory
**Purpose:** Deterministically turn validated structured data into real Office files — never let an LLM emit binary output directly.

Two-stage pipeline:
1. Reasoning model outputs JSON → validated against a strict **Pydantic schema** (reject and re-ask the model if validation fails).
2. A plain-Python template engine populates a pre-approved corporate template with that JSON.

| Output | Library | Notes |
|---|---|---|
| Word (.docx) | python-docx | Header/footer/signature-block templates per document type (approval note, inspection summary) |
| Excel (.xlsx) | openpyxl | Live formulas (not just hardcoded values!), conditional formatting for out-of-spec readings |
| PowerPoint (.pptx) | python-pptx | Corporate slide master, auto-embed charts/images from source pages |

**Basic detail people miss:** version your templates (`templates/approval_note_v1.docx`) and keep the JSON payload saved next to the generated file (`outputs/<task_id>/payload.json`) so regeneration/audit is trivial and you're not re-running the whole agent just to fix a typo in a template.

**Tech:** python-docx, openpyxl, python-pptx, Pydantic v2, Jinja2 (for any HTML/preview rendering).
**Artifact:** `services/docgen/`, `templates/`, `schemas/*.py` (Pydantic models).

### 5.9 Observability / Sovereignty Dashboard
**Purpose:** This is not a "nice to have" — it is literally one of the five official evaluation pillars. Build it early, not last.

Live tiles:
- GPU utilization %, VRAM used/total
- Active model(s) + which role invoked them
- Agent task timeline (plan steps, status, retries)
- Sandbox: last N executions, syscalls observed, network bytes TX/RX (must read **0**)
- RAG: last retrieval, sources cited
- System audit log tail

**Tech:** `nvidia-smi` polling (or `pynvml`), FastAPI WebSocket push to a small React dashboard panel, `psutil` for host stats.
**Artifact:** `services/observability/collector.py`, `frontend/src/components/Dashboard/`.

### 5.10 Frontend
**Purpose:** Employee-facing chat + task view + the dashboard above.

- Chat pane (like a familiar assistant UI — lowers adoption friction for engineers used to ChatGPT).
- **Task Timeline pane** next to chat showing the live agent plan (this doubles as your demo's best visual).
- File upload with drag-drop, preview of extracted OCR text/graph for verification.
- Output pane: preview + download link for generated .docx/.xlsx/.pptx.
- Sovereignty Dashboard as a persistent sidebar or a toggle-able panel.

**Tech:** React + Vite, Tailwind, WebSocket for streaming tokens and agent step updates.
**Artifact:** `frontend/` (standard Vite React app).

### 5.11 Storage & Data Layer
- **Postgres:** users, tasks, task steps, audit metadata, template registry.
- **Qdrant/Chroma:** vector index for RAG.
- **Local disk (encrypted volume if possible):** raw uploads, processed artifacts, generated outputs.
- **Redis (optional):** task queue / pub-sub for agent step updates to the frontend.

**Artifact:** `infra/docker-compose.yml` bringing up Postgres, Qdrant, Redis, backend, frontend, sandbox image — one command should stand up the whole stack (`docker compose up`).

### 5.12 Security, Auth, Audit
- Local auth (even a simple username/password + JWT is fine for a demo — real PSU deployment would hook into existing AD/LDAP, mention this as future work).
- Role-based access: engineer vs admin (admin sees full audit log + can manage templates/models).
- **Append-only audit log** for: logins, uploads, model calls, sandbox executions, document generations, downloads.
- Default-deny egress firewall rule at the host/container network level, with an explicit allowlist (empty by default) — this is your air-gap proof at the infrastructure layer, backing up the eBPF proof at the sandbox layer.

**Artifact:** `services/auth/`, `logs/audit.jsonl`, `infra/network_policy.md` (document exactly what firewall rules you applied, screenshot them).

---

## 6. Data Flow — Two Worked Examples

### 6.1 Example: Corrosion Inspection Report → Approval Note

```
Upload scanned PDF
   → Ingestion: detect scan, no text layer
   → Router: task="document extraction + calculation" → route to Vision model + Reasoning model
   → Vision (Qwen2.5-VL): OCR equipment tag, old/new thickness readings
   → Agent Plan: [extract data, calculate corrosion rate, check against threshold, cite SOP, draft note]
   → Sandbox: Python computes corrosion_rate = (t_old - t_new) / years; verifies against OISD threshold
   → RAG: retrieve relevant SOP clause on retirement thickness
   → Reasoning model: interprets result, drafts recommendation text
   → Pydantic validation of {equipment_id, readings, rate, recommendation, sop_ref}
   → Document Factory: python-docx populates Approval Note template
   → Output: signed-ready .docx + audit trail entry
   → Dashboard: shows 0 bytes network egress throughout
```

### 6.2 Example: "What feeds pump P-204A?" (P&ID query)

```
User question (no upload, refers to existing indexed P&ID)
   → Router: task="visual document QA" → route to RAG (visual) + Vision model
   → RAG: hybrid search finds candidate P&ID pages + tag index
   → Vision/graph pipeline: looks up P-204A node in pre-built pipe/instrument graph
   → Graph traversal: returns upstream equipment + connecting line numbers
   → Reasoning model: turns graph answer into a natural-language explanation with citations
   → Response streamed to chat with page-image citation (not raw quoted OCR text)
```

---

## 7. Advanced Model Routing — The Centerpiece (do this properly)

This is where most teams under-deliver by doing either (a) `if "code" in prompt: use coder_model` or (b) a single embedding-similarity lookup. Both are fragile and judges have seen them a hundred times. Build a **cascaded, multi-signal router** instead — this is genuinely closer to production research (RouteLLM, vLLM Semantic Router, and mechanistic/activation-based routing all combined, but kept practical).

### 7.1 Router architecture: 4 layers, cheapest first

```
Incoming request
      │
      ▼
┌─────────────────────────┐
│ Layer 0: Deterministic   │  file type / explicit tool mention / regex on
│ metadata pre-filter      │  code fences, file extensions, explicit user
│  (near-zero cost, <1ms)  │  intent flags ("/calc", "/code", uploaded .pdf image)
└───────────┬──────────────┘
     high confidence? ──Yes──► ROUTE (skip remaining layers)
      │ No / ambiguous
      ▼
┌─────────────────────────┐
│ Layer 1: Semantic router │  embed query with small embedding model,
│ (cosine similarity)      │  compare to curated centroid embeddings per
│  (~5-15ms)               │  task domain (coding / reasoning / vision-doc /
│                          │  admin-doc / search)
└───────────┬──────────────┘
     confident single match? ──Yes──► ROUTE
      │ No / close scores between domains
      ▼
┌─────────────────────────┐
│ Layer 2: Learned         │  small causal classifier (0.5–3B, same model
│ classifier (JSON router) │  as your "router role" model) outputs
│  (~50-150ms)             │  {"domain": "...", "confidence": 0.0-1.0,
│                          │   "suggested_model": "...", "reasoning": "..."}
└───────────┬──────────────┘
     confidence ≥ threshold? ──Yes──► ROUTE
      │ No (task looks hard / ambiguous / high stakes)
      ▼
┌─────────────────────────┐
│ Layer 3: Escalation /    │  RouteLLM-style win-probability estimate:
│ cascade decision         │  "would the bigger reasoning model meaningfully
│  (only for uncertain     │  outperform the default model on this query?"
│  cases — rare, so cost   │  If yes → escalate to bigger/slower model.
│  is acceptable)          │  If no → stay on cheap model, don't waste VRAM.
└───────────┬──────────────┘
      ▼
   FINAL ROUTE + fallback chain recorded
```

**Why this order matters:** Layer 0 catches the easy 40–60% of requests for free (an uploaded image obviously needs vision; a request with a `.py` code block obviously needs the coder). Layers 1–2 handle the rest with increasing cost only when needed. Layer 3 (the expensive "should we escalate" decision) only runs on genuinely ambiguous cases — which keeps average routing latency low even though the full pipeline is sophisticated. This tiered-cost design is itself worth stating explicitly to judges — it shows you understand routing is a **cost/quality trade-off system**, not a lookup table.

### 7.2 What each layer actually routes to

| Domain detected | Target role | Example trigger |
|---|---|---|
| Code / scripting / automation | `coder` | ".py mentioned", "write a script", code fence in input |
| Engineering calculation / root cause | `reasoning` | "calculate", "corrosion rate", "thermodynamic", numeric formulas present |
| Scanned doc / image / P&ID | `vision` | uploaded image/PDF-scan, "read this drawing" |
| Company knowledge lookup | `rag` (no generation model needed beyond a light synthesis pass) | "what does the SOP say about...", exact tag numbers |
| Administrative drafting (memo/PPT/summary) | `reasoning` (lighter) + `docgen` | "draft an approval note", "prepare a presentation" |
| Ambiguous / multi-domain | Agent decomposes into sub-tasks, each sub-task re-enters the router individually | "analyze this report and prepare documents" (spans vision + reasoning + docgen) |

### 7.3 Layer 2 in detail — the learned JSON classifier

Don't hand-write this as free-form prompting; treat it like a tiny structured-output task:

```
SYSTEM: You are a routing classifier. Given a user request, output ONLY JSON:
{"domain": "coding|reasoning|vision|rag|admin_doc|ambiguous",
 "confidence": <0-1>,
 "reason": "<one short phrase>"}

USER: <the raw request>
```

- Bootstrap training/eval data by hand-labeling ~150–300 example requests across your domains (you can generate synthetic variants with a bigger model, then hand-check them — do NOT skip the hand-check, mislabeled router training data is the #1 way this silently breaks).
- Evaluate router accuracy on a held-out set before the demo — put this **accuracy number on your slide** (e.g., "94% correct routing on 60 held-out test prompts"). A router with a measured accuracy number is far more convincing than a router you just assert works.
- Keep a `router_eval/` folder with the test set + a script that prints a confusion matrix. This is cheap to build and is a concrete "we validated this" artifact judges will notice.

### 7.4 Layer 3 in detail — escalation/cascade logic (RouteLLM-style, kept simple)

You don't need to replicate RouteLLM's full matrix-factorization training. A practical, defensible version:

1. Maintain a small **calibration set** of past (query, cheap-model-answer, expensive-model-answer, which-was-actually-better) triples — even 30–50 labeled examples is a legitimate start.
2. Train a tiny logistic regression (scikit-learn, seconds to train) on features: `[query_length, contains_numeric_formula, router_layer2_confidence, retrieved_context_length, domain_one_hot]` → predicts `P(expensive_model_wins)`.
3. If `P(expensive_model_wins) > threshold` (tune this threshold against your VRAM budget — this is literally a cost/quality knob you can show live), escalate.
4. Log every escalation decision with its probability score to the audit trail — another concrete "we can show our work" artifact.

This gives you a genuinely defensible answer to "how does your router decide when to use the big model vs the small one?" instead of "we just picked one."

### 7.5 Layer 4 — mechanistic/activation-based routing (stretch / R&D differentiator, mention don't over-build)

The source research describes routing using internal model activations (effective dimensionality, isotropy, Fisher separability of prefill hidden states) instead of surface text features. This is genuinely cutting-edge and **worth one slide as your "advanced R&D direction"** even if you don't fully implement it for the working demo:

- Concept: extract the router model's hidden state at the last prefill token; compute how "spread out" (isotropic) and how well-separated by task type that vector is; use that geometric signal, not just the text, to decide difficulty.
- If you have time: implement a minimal version — grab hidden states via `output_hidden_states=True` on your small router model, fit a simple linear probe (logistic regression) on top of them to predict "easy vs hard", and compare its accuracy to the plain text-embedding router (Layer 1). Even a small ablation table ("text-embedding router: 88% / activation-probe router: 91%") is an excellent research-flavored appendix slide and shows you didn't just copy the report — you tested its central claim.
- If you don't have time: present it honestly as future work with the math briefly explained. Judges respect an accurate "here's what we built vs. here's the research direction we'd extend to" distinction far more than an over-claimed feature that breaks under questioning.

### 7.6 Router self-improvement loop (nice differentiator, low effort)

- Log `(request, chosen_route, layer_that_decided, final_success/failure, user_thumbs_up/down)` for every task.
- Weekly (or on-demand) script re-trains the Layer 2 classifier and Layer 3 logistic regression on accumulated logs.
- Show this as "the router gets better with usage" — a genuinely nice narrative for judges, and technically trivial to implement given you already log everything for audit purposes anyway.

**Artifact to create now:** `services/router/{layer0_metadata.py, layer1_semantic.py, layer2_classifier.py, layer3_cascade.py, router.py}`, `router_eval/labeled_set.jsonl`, `router_eval/eval_report.py`.

---

## 8. Concrete Tech Stack Summary

| Layer | Choice | Why |
|---|---|---|
| Backend API | FastAPI (Python) | async, WebSocket support, matches ML stack |
| Frontend | React + Vite + Tailwind | fast to build, familiar chat-UI patterns |
| Model serving (dev) | Ollama / llama.cpp | easiest GGUF quantized serving on 8 GB VRAM |
| Model serving (target) | vLLM | PagedAttention, OpenAI-compatible, handles concurrent models |
| Vector DB | Qdrant (or Chroma for pure simplicity) | local, fast, easy filters for metadata |
| Relational DB | PostgreSQL | tasks, audit, users, templates |
| Queue/pubsub | Redis (optional) | live agent step streaming to UI |
| Sandbox runtime | Docker + gVisor (runsc) | best isolation/latency balance for single workstation |
| Syscall monitoring | eBPF (bcc/bpftrace) or simple `strace` fallback on dev laptop | proves zero-egress |
| OCR | PaddleOCR | strong on rotated/dense text |
| Doc generation | python-docx, openpyxl, python-pptx | deterministic Office file creation |
| Validation | Pydantic v2 | strict schema between reasoning and docgen stages |
| Containers/orchestration | Docker Compose (single workstation — no need for k8s) | matches "single workstation/edge server" requirement exactly |

---

## 9. Repository Structure (create this skeleton on day 1)

```
sih26117-workbench/
├── config/
│   ├── model_tiers.yaml
│   └── network_policy.yaml
├── frontend/                  # React app
├── services/
│   ├── ingestion/
│   ├── router/
│   ├── model_manager/
│   ├── agent/
│   │   └── tools/
│   ├── rag/
│   ├── vision/
│   │   └── pid_pipeline/
│   ├── sandbox/
│   ├── docgen/
│   ├── observability/
│   └── auth/
├── schemas/                   # Pydantic models
├── templates/                 # docx/xlsx/pptx templates
├── sandbox/                   # Dockerfile + runsc config for the exec sandbox
├── infra/
│   ├── docker-compose.yml
│   └── network_policy.md
├── router_eval/
├── logs/
│   ├── audit.jsonl
│   └── sandbox_audit.jsonl
├── storage/
│   ├── raw/
│   └── processed/
├── docs/
│   ├── architecture.png
│   └── demo_script.md
├── tests/
├── .env.example
├── README.md
└── requirements.txt
```

**Basic detail people miss:** a real `.env.example`, a real `README.md` with setup steps that actually work on a clean machine, and a `requirements.txt`/`pyproject.toml` that's pinned (not "latest"). Judges (and you, at 2am before the demo) will thank you.

---

## 10. Implementation Roadmap

### Phase 0 — Foundations (before hackathon / prep weeks)
- Repo skeleton, docker-compose stack up, Postgres/Qdrant running.
- Download and quantize dev-tier models; confirm each loads within VRAM budget on your laptop.
- Basic FastAPI + React "hello world" chat that echoes to one model. Get this working end-to-end first — it's your safety net.

### Phase 1 — Router + RAG MVP
- Layer 0 + Layer 1 router working with 3–4 domains.
- Ingestion for PDFs/images; RAG hybrid search over a small sample SOP corpus.
- Chat UI shows which model/domain was chosen for each message (transparency = good demo material even this early).

### Phase 2 — Agent + Sandbox
- Agent planner producing visible JSON plans; executor running at least 2 real tools (RAG search tool, sandbox calculator tool).
- gVisor sandbox running Python with network disabled; eBPF or simple network-namespace check confirming 0 egress; audit log populated.

### Phase 3 — Document Factory
- Pydantic schemas for at least 2 document types (approval note, calculation sheet).
- python-docx + openpyxl templates wired to real agent output on a sample corrosion-report scenario end-to-end.

### Phase 4 — Vision / P&ID pipeline
- OCR + tag extraction on sample scanned reports (prioritize this).
- Basic symbol detection + a hand-curated demo P&ID with a working "what feeds X" query, even if not fully general.

### Phase 5 — Dashboard, Layer 2/3 Router, Polish
- Sovereignty dashboard live (GPU/VRAM/model/sandbox/network tiles).
- Layer 2 learned classifier trained + evaluated (put the accuracy number in your deck).
- Layer 3 escalation logistic regression trained on a small calibration set.
- Record a full backup demo video (see Section 13) in case live GPU/network fails on stage.

### Phase 6 — Grand Finale prep (if selected)
- Move to Target Tier hardware (rented/borrowed 24 GB GPU), re-run all benchmarks, capture new VRAM numbers and screenshots for slides.
- Stress test: concurrent requests, worst-case model combination, timeout handling.
- Rehearse the exact demo script end-to-end at least 3 times, including one deliberate failure (e.g., unplug network) to show the audit log catching it.

---

## 11. API Sketch (key endpoints)

```
POST   /api/v1/tasks               # submit a new user request (text + optional files)
GET    /api/v1/tasks/{id}          # poll task status
WS     /api/v1/tasks/{id}/stream   # live plan steps + token streaming
GET    /api/v1/tasks/{id}/output   # download generated .docx/.xlsx/.pptx
POST   /api/v1/rag/search          # direct RAG query (debugging/demo)
GET    /api/v1/dashboard/metrics   # GPU/VRAM/model/sandbox/network snapshot
GET    /api/v1/router/eval         # last router accuracy report
GET    /api/v1/audit               # (admin-only) audit log viewer
```

---

## 12. Evaluation-Pillar Mapping (map every feature to a judge criterion)

| Judge pillar (from PS) | Feature that proves it | Concrete evidence to show live |
|---|---|---|
| Proof of sovereign air-gap | Default-deny network policy + eBPF/syscall trace on sandbox | Dashboard tile reading "0 bytes TX/RX" while a task runs; `tcpdump`/Wireshark window open during demo |
| Automated dynamic model routing | 4-layer cascade router (Section 7) | Live UI tag showing "routed to: Qwen2.5-Coder (Layer 0, file-type match)" per message; router accuracy report |
| End-to-end agentic execution | Agent Plan → Act → Observe → Reflect loop with visible DAG | Task Timeline panel showing real steps for the corrosion-report demo |
| Hardware bounding & memory efficiency | Two-tier config, LRU model eviction, quantization | Dashboard VRAM graph staying under budget through a multi-request session |
| Multimodal extraction quality | OCR + vision pipeline on real scanned samples | Side-by-side: scanned page vs extracted structured data |

---

## 13. Demo Script (rehearse this exact sequence)

1. Open Sovereignty Dashboard — point out network monitor reading 0/0 bytes. Start a packet capture window visibly.
2. Upload a scanned corrosion inspection PDF sample. Show ingestion detect "scan, no text layer."
3. Ask: *"Analyze this report and prepare an approval note."* Show the agent's live plan appear step by step.
4. Point out the router tag on each sub-step ("routed to Vision model," "routed to Reasoning model," "escalated to bigger model — confidence was low").
5. Show the sandbox execution log (Python calculation, 0 network bytes, exit code 0).
6. Show the RAG citation ("grounded in SOP-14.pdf, page 7").
7. Download the generated `.docx` — open it live, show it's a real formatted Word document, not markdown pasted in.
8. Ask a P&ID question ("what feeds P-204A?") to show the vision/graph pipeline separately.
9. Close with the router accuracy number and the "0 bytes network egress across the entire session" summary from the audit log.
10. One slide: two-tier hardware story — "built and tested on an 8GB laptop, same code scales to a 24–48GB workstation via one config change" — this directly answers the hardware-efficiency judging pillar and shows engineering maturity.

**Basic detail people miss:** have a **recorded backup video** of the full demo running on your laptop, playable offline, in case venue Wi-Fi/power/projector issues strike mid-demo (very common at SIH). Also carry the repo on a USB drive.

---

## 14. Integrating Your Existing Projects

You mentioned wanting to combine this with projects you've already built, but no specific project details are available to me in this conversation. Rather than guess, here's how to slot **anything** you've previously built into this architecture depending on its type:

- **Already have an OCR/vision pipeline?** → drop it in as the implementation behind Section 5.6/6.1, keep the same interface (`extract(page_image) -> StructuredExtraction`).
- **Already have a chatbot/RAG project?** → reuse it as the starting point for Section 5.5, then add the hybrid BM25+dense+rerank layers if it doesn't already have them.
- **Already have a document generator (docx/pptx automation)?** → reuse directly as Section 5.8, just add the Pydantic validation boundary in front of it.
- **Already have any agent/tool-calling project?** → reuse its executor as the base for Section 5.4, add the plan-visibility and reflect/retry loop if missing.
- **Already have a model-serving or LLM API wrapper?** → reuse as the adapter layer inside Section 5.3's Model Manager.

If you tell me what the previous project(s) actually do (stack, purpose, what's reusable), I can rewrite the relevant module section to specifically wire it in rather than this generic mapping.

---

## 15. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| 8 GB VRAM OOM mid-demo | Hard VRAM budget with headroom in Model Manager; test worst-case model combo beforehand; serial swap, never co-load two heavy models on dev tier |
| Router misclassifies live in front of judges | Show the measured accuracy number proactively; have Layer 0 catch the specific demo inputs deterministically as a safety net |
| Live network demo fails (venue Wi-Fi) | This project needs NO internet to run — that's the whole point; demo entirely offline, just make sure your own machine's Wi-Fi is off to visually prove it |
| P&ID pipeline too ambitious for the time you have | Scope to 1–2 curated sample drawings that work reliably rather than a general solver that's flaky |
| Sandbox breaks/crashes | Always test the sandbox in isolation with adversarial inputs (infinite loop, big allocation) before demo day; have resource limits actually enforced, not just configured |
| Judges ask "why not just use Ollama's built-in routing / Open WebUI?" | Have the comparison table (Section 16 below) ready — you should be able to name the exact gap you're filling |

---

## 16. Why This Isn't "Just Open WebUI" (keep this answer ready)

| Capability | Open WebUI / LibreChat | This workbench |
|---|---|---|
| Model routing | Manual dropdown | Automated 4-layer cascade router with measured accuracy |
| Agentic execution | None / bolt-on | Visible Plan-Act-Observe-Reflect loop |
| Code execution safety | None built-in | gVisor sandbox, network-disabled, eBPF-verified |
| Office deliverables | None | Deterministic docx/xlsx/pptx pipeline with schema validation |
| P&ID/engineering drawing understanding | Generic VLM pass-through | Tiling + OCR + symbol + graph pipeline |
| Air-gap proof | Assumed, not demonstrated | Live dashboard + audit log with byte-level network evidence |

---

## 17. Glossary (for teammates/judges unfamiliar with terms)

- **Air-gapped:** physically/logically isolated from any external network.
- **Quantization:** compressing model weights (e.g., 16-bit → 4-bit) to reduce memory use.
- **RAG:** Retrieval-Augmented Generation — search your own documents before answering.
- **Agentic:** the system plans and executes multi-step actions using tools, not just single-turn Q&A.
- **Sandbox:** an isolated environment where untrusted code runs without touching the real system.
- **P&ID:** Piping & Instrumentation Diagram — a plant's process/equipment/instrumentation map.
- **gVisor:** a user-space kernel that intercepts syscalls to isolate containers more strongly than plain Docker.
- **VRAM:** GPU memory, the main constraint for running local models.

---

## 18. Final Checklist Before Submission (the "basic details" safety net)

- [ ] README with one-command setup (`docker compose up`) that actually works from a clean clone
- [ ] `.env.example` with every required variable documented
- [ ] Pinned dependency versions
- [ ] Sample data included in repo (a couple of anonymized/synthetic scanned reports and one demo P&ID) so anyone can run the demo without your specific files
- [ ] Router evaluation report checked into the repo (`router_eval/eval_report.md`)
- [ ] Audit log sample checked in (`logs/audit_sample.jsonl`) showing a real run
- [ ] Architecture diagram exported as an actual image, not just ASCII
- [ ] Recorded backup demo video
- [ ] PPT with: problem, one-liner pitch, architecture diagram, router deep-dive slide, hardware two-tier slide, evaluation-pillar mapping slide, roadmap slide, team slide
- [ ] Team roles clearly assigned (who owns router, who owns sandbox, who owns docgen, who owns frontend, who owns vision pipeline) — judges sometimes ask this directly
- [ ] Cost/latency numbers measured, not guessed (average routing latency, average end-to-end task time on dev tier)
- [ ] License file + clear statement of which models are open-weight and their licenses (relevant for a PSU/defense pitch — show you thought about license compliance, not just capability)

---

## 19. Summary

You are building five layers stacked on top of each other:

```
INTELLIGENCE  (advanced 4-layer router + swappable open-weight models)
     ↓
AGENT         (plan → act → observe → reflect, visible, not hidden)
     ↓
KNOWLEDGE     (hybrid RAG grounded in the org's own documents)
     ↓
ACTION        (sandboxed tools: code execution, calculators, doc generation)
     ↓
SOVEREIGNTY   (air-gap enforced at OS level, proven live via dashboard + audit log)
```

Build it two-tiered from day one (8 GB laptop → 24-48 GB workstation), make the router genuinely multi-layered instead of a single lookup, and make every security/sovereignty claim backed by something a judge can watch happen live. That combination — not any single clever model — is what actually differentiates this submission.
