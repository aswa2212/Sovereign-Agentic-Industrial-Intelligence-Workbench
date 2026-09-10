# System Architecture Overview — SIH26117

## 1. High-Level Pipeline

The workbench follows a strict unidirectional dispatch and execution pattern:

```
[ User Request ]
       │
       ▼
 [ Frontend UI ]
       │  (REST / WebSocket)
       ▼
 [ API Gateway ]
       │
       ▼
 [ Task Router ] ────► Determines optimal model profile & task domain
       │
       ▼
 [ Agent Orchestrator ] ◄────► [ Local Tools Engine ]
 (State-Machine Planner)        ├── Sandboxed Python Runner
       │                        ├── Sovereign RAG Store
       │                        └── Ingestion & Vision Parser
       ▼
 [ Local Model Manager ]
 (Unified ModelHandle)
       │
       ▼
 [ Local Inference (Ollama) ]
 (DeepSeek-R1 / Qwen2.5-Coder / Qwen2.5-VL)
       │
       ▼ (Structured JSON)
 [ Deliverables Factory ] ───► Deterministic DOCX, XLSX, PPTX
```

## 2. Core Architectural Decoupling Rules

1. **Router vs. Agent:**
   - **Router:** Static/Dynamic classification of *which capability or model* is required (e.g. Reasoning, Coding, Vision). It has no multi-step memory.
   - **Agent Orchestrator:** Explicit state-machine managing *the multi-step sequence* (Plan $\rightarrow$ Act $\rightarrow$ Observe $\rightarrow$ Reflect). It invokes the Router and tools as needed.
2. **Model Manager:**
   - Exposes a unified `ModelHandle` interface.
   - Handles the physical interaction with the local inference engine (Ollama).
   - Manages memory swapping on 8 GB hardware to prevent CUDA OOM.
3. **Office Deliverable Generation:**
   - Never allow an LLM to directly emit binary office document bytes.
   - LLMs output structured JSON schema validated by Pydantic.
   - Deterministic Python scripts (`python-docx`, `openpyxl`, `python-pptx`) generate the final styled files.
4. **Air-Gap Verification:**
   - The Network Monitor inspects socket bindings and traffic to guarantee zero outbound connections.
   - Audit Logger records immutable event traces for every operation.
