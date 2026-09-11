# SIH26117 — Sovereign Agentic Industrial Intelligence Workbench
## Exact MVP Project Definition, Architecture & PPT Reference

**Project:** SIH26117  
**Target Organization:** Mangalore Refinery and Petrochemicals Limited (MRPL)  
**Project Type:** Sovereign / Local / Air-Gap-Ready Agentic Industrial AI Workbench  
**Development Stage:** Focused MVP  
**Purpose of this document:** Single source of truth for understanding the project, preparing presentations, explaining the architecture, and guiding implementation.

---

# 1. Executive Definition

We are building a **sovereign, local-first agentic industrial intelligence workbench** for sensitive industrial environments such as MRPL.

The system allows an engineer or operator to provide industrial documents and a high-level objective. The workbench then:

1. ingests and understands the documents,
2. retrieves relevant organizational knowledge,
3. determines what type of task is being performed,
4. selects the appropriate local model capability,
5. plans and executes a bounded multi-step workflow,
6. uses only approved tools,
7. observes and validates intermediate and final results,
8. preserves evidence and provenance,
9. generates structured, business-ready deliverables,
10. provides audit and sovereignty evidence.

The core MVP is deliberately **not** a complete refinery enterprise platform. It is a focused proof that these capabilities can operate together in a controlled local environment.

---

# 2. One-Line Definition

> **A sovereign industrial AI workbench that turns sensitive operational documents and user goals into controlled, verifiable, traceable agentic workflows and business-ready deliverables using local AI.**

---

# 3. 30-Second Explanation

> We are building a local AI workbench for sensitive industrial environments. An engineer can upload SOPs, inspection reports, manuals, scanned documents, and engineering visuals, then give the system a real operational objective. The system understands the task, retrieves relevant evidence, routes the task to an appropriate local model, executes approved tools through a bounded agent workflow, verifies the result, and generates a professional report or spreadsheet. The design keeps the core intelligence and sensitive data inside the organization's controlled environment and records evidence of what the system did.

---

# 4. What We Are Actually Building

The project consists of these major layers:

```text
                    USER
                      │
                      ▼
              ┌───────────────┐
              │ WORKBENCH UI  │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │  FASTAPI API  │
              └───────┬───────┘
                      │
                      ▼
          ┌─────────────────────────┐
          │   AGENT ORCHESTRATOR   │
          │                         │
          │ Understand             │
          │ Plan                   │
          │ Execute                │
          │ Observe                │
          │ Reflect                │
          │ Validate               │
          └───────────┬─────────────┘
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
   MODEL ROUTER      RAG          CONTROLLED
       │           KNOWLEDGE        TOOLS
       ▼              │              ▼
 LOCAL MODELS         ▼           SANDBOX
   LLM/VISION     VECTOR STORE
       │              │              │
       └──────────────┼──────────────┘
                      ▼
                VALIDATION
                      │
                      ▼
            DETERMINISTIC OUTPUT
                      │
              ┌───────┼───────┐
              ▼       ▼       ▼
            DOCX     XLSX    PPTX
                      │
                      ▼
             AUDIT / EVIDENCE
```

This is the system we are building.

---

# 5. The Five Core Pillars

The project is organized around five technical pillars.

## Pillar 1 — Sovereign Local Operation

Sensitive information should be processed locally rather than requiring external cloud AI inference.

The architecture supports:

```text
User
 ↓
Local UI
 ↓
Local API
 ↓
Local Agent
 ↓
Local Models
 ↓
Local Knowledge
 ↓
Local Tools
 ↓
Local Output
```

The MVP will demonstrate local-only execution paths and network evidence.

**Important wording:** software-level local-only controls and runtime network evidence are not the same thing as proving a physical air gap. Deployment-level isolation is a separate concern.

---

## Pillar 2 — Dynamic Multi-Model Routing

Different tasks need different capabilities.

Instead of forcing every request through one model:

```text
Task
 ↓
Task Type
 ↓
Required Capability
 ↓
Model Role
 ↓
Model Manager
 ↓
Appropriate Local Model
```

Examples:

| Task | Capability |
|---|---|
| Classification | Lightweight reasoning |
| Summarization | Instruction model |
| Complex analysis | Reasoning model |
| Coding/tool task | Coding model |
| Image/drawing analysis | Vision model |
| Embedding | Embedding model |

The router selects the **task/capability/model role**. The Model Manager handles the actual model/provider resolution.

Model names remain configurable rather than embedded into business logic.

---

## Pillar 3 — Multi-Step Agentic Execution

The system is not merely a chatbot.

The agent follows an explicit bounded lifecycle:

```text
IDLE
 ↓
RECEIVE
 ↓
UNDERSTAND
 ↓
PLAN
 ↓
EXECUTE
 ↓
OBSERVE
 ↓
REFLECT
 ↓
VALIDATE
 ↓
FINALIZE
 ↓
DELIVER
```

A failure can lead to a controlled retry/replanning path.

Safety limits include:

- maximum execution steps,
- retry limits,
- per-step timeout,
- global task timeout,
- validation before final delivery.

This makes agent behavior observable and bounded.

---

## Pillar 4 — Multimodal Industrial Document Intelligence

Industrial knowledge is not only plain text.

The ingestion and vision layers support the processing path for:

- PDF
- DOCX
- XLSX
- CSV
- PNG/JPG/JPEG
- scanned PDFs
- tables
- engineering drawings
- visual information

The intended pipeline is:

```text
Upload
 ↓
Validate
 ↓
Hash
 ↓
Detect
 ↓
Parse
 ↓
OCR if required
 ↓
Vision if required
 ↓
Normalize
 ↓
Chunk
 ↓
Embed
 ↓
Knowledge Store
```

The MVP does not claim that every type of engineering drawing can be perfectly interpreted. Vision/P&ID capability is bounded and capability-aware.

---

## Pillar 5 — Deterministic Business Deliverables

The AI does not directly control Office-file formatting.

Preferred architecture:

```text
Local Model / Agent
        ↓
Structured JSON
        ↓
Pydantic Validation
        ↓
Engineering Validation
        ↓
Deterministic Generator
        ↓
DOCX / XLSX / PPTX
```

This gives:

- predictable output,
- validation,
- reproducibility,
- consistent formatting,
- provenance preservation,
- easier testing.

---

# 6. The Core MVP Workflow

The strongest MVP is one complete industrial workflow rather than many unrelated demos.

## North-Star Workflow

```text
Industrial Inspection / NDT Document
              ↓
       Document Ingestion
              ↓
          OCR / Vision
              ↓
        Knowledge / RAG
              ↓
          User Goal
              ↓
        Task Understanding
              ↓
             Plan
              ↓
        Model Routing
              ↓
        Local Reasoning
              ↓
      Controlled Calculation
              ↓
          Observation
              ↓
           Reflection
              ↓
          Validation
              ↓
      Structured Result
              ↓
     DOCX + XLSX Output
              ↓
      Audit / Network Proof
```

The primary demonstration scenario is a **synthetic C-101 corrosion/inspection audit**.

---

# 7. Primary Demo Scenario — C-101 Corrosion Audit

The north-star demonstration should be centered on an industrial inspection/corrosion case.

## Input

Synthetic industrial documents such as:

- inspection/NDT report,
- relevant SOP,
- equipment information,
- inspection measurements,
- supporting technical information.

## Example Objective

> Analyze the inspection findings, retrieve the relevant procedure, calculate the required engineering result, verify the findings against available evidence, and generate a professional maintenance/inspection report.

## Expected System Behavior

```text
1. User uploads documents
2. Ingestion validates and stores them
3. OCR/Vision processes required content
4. Relevant knowledge is indexed/retrieved
5. Agent understands the objective
6. Router identifies required capabilities
7. Local model is selected
8. Agent creates a bounded plan
9. RAG retrieves supporting evidence
10. Approved calculation tool executes
11. Agent observes the result
12. Validator checks the result
13. Provenance is preserved
14. DOCX report is generated
15. XLSX analysis is generated
16. Audit evidence is recorded
17. User receives the result
```

This single workflow demonstrates the five pillars together.

---

# 8. Current Implemented Architecture

The project is being built incrementally and is no longer just a conceptual architecture.

## Phase Status

```text
Phase 0  Architecture & Contracts          ✅
Phase 1  Backend Foundation                ✅ FROZEN
Phase 2  Local Model Manager               ✅ FROZEN
Phase 3  Task Router                       ✅ FROZEN
Phase 4  Document Ingestion                ✅ FROZEN
Phase 5  OCR & Vision                      ✅ FROZEN
Phase 6  Sovereign Knowledge / RAG         ✅ FROZEN
Phase 7  Agent State Machine               ✅ FROZEN
Phase 8  Sandbox / Controlled Tools        ✅ FROZEN
Phase 9  Structured Output / Validation    ✅ FROZEN
Phase 10 Office Deliverables               🔄 AUDITED / FREEZE PENDING
Phase 11 Audit & Sovereignty Evidence      ⏳
Phase 12 Workbench Frontend                ⏳
Phase 13 End-to-End MVP Integration        ⏳
Phase 14 Accuracy / Performance Evaluation ⏳
Phase 15 Linux / On-Prem Validation        ⏳
Phase 16 Demo Hardening                    ⏳
```

The phase process is intentionally strict:

```text
IMPLEMENT
   ↓
RUN TESTS
   ↓
INDEPENDENT ARCHITECTURE AUDIT
   ↓
VERIFY FROZEN PHASES
   ↓
LOCAL GIT COMMIT
   ↓
FREEZE
   ↓
NEXT PHASE
```

GitHub push is not required after every phase. Local Git commits are the primary freeze checkpoints.

---

# 9. Phase-by-Phase Technical Architecture

## Phase 1 — Backend Foundation

Purpose:

- FastAPI foundation
- configuration
- logging
- middleware
- errors
- API versioning
- core interfaces

Key principle:

> Establish stable boundaries before implementing intelligence.

---

## Phase 2 — Local Model Manager

Purpose:

- local model provider abstraction,
- Ollama adapter,
- mock provider,
- model configuration,
- lifecycle management,
- structured generation,
- health checking.

Architecture:

```text
Application
    ↓
ModelManager
    ↓
Model Role
    ↓
Provider
    ↓
Local Model Runtime
```

The application does not directly depend on Ollama everywhere.

---

## Phase 3 — Task Router

Purpose:

Determine what capability a task requires.

```text
User Task
   ↓
Rule Router
   ↓
Task Type
   ↓
Capability
   ↓
Model Role
```

The router does **not** call Ollama and does not directly choose model IDs.

This separation is important:

```text
Router
= WHAT capability is required?

Model Manager
= HOW/WHICH local model provides it?
```

---

## Phase 4 — Multimodal Document Ingestion

Pipeline:

```text
Upload
 ↓
Validation
 ↓
SHA-256
 ↓
Magic-byte detection
 ↓
Raw storage
 ↓
Parser
 ↓
NormalizedDocument
 ↓
Processed storage
```

Supported formats:

- PDF
- DOCX
- XLSX
- CSV
- images

The output is a normalized representation that later phases consume.

OCR and semantic RAG are intentionally separate phases.

---

## Phase 5 — OCR & Vision

Purpose:

- local OCR abstraction,
- deterministic image preprocessing,
- vision provider abstraction,
- engineering drawing analysis,
- instrument/equipment/line tag extraction.

Architecture:

```text
Document/Image
      ↓
Preprocessing
      ↓
OCR / Vision
      ↓
Visual Findings
      ↓
Provenance
```

If real OCR/VLM capability is unavailable, the system must fail or report capability unavailability rather than pretending that real analysis occurred.

---

## Phase 6 — Sovereign Knowledge / RAG

Purpose:

Turn normalized industrial documents into searchable local knowledge.

```text
NormalizedDocument
      ↓
Chunker
      ↓
Embedding Provider
      ↓
Local Vector Store
      ↓
Retriever
      ↓
Cited Evidence
```

Important output:

```text
Retrieved Evidence
+
Source Document
+
Page / Section
+
Chunk ID
+
Content Hash
+
Similarity
```

The RAG layer must not fabricate evidence.

The current development implementation uses a local NumPy/JSON vector store with pluggable embedding providers and deterministic mock embeddings for offline testing.

---

## Phase 7 — Agent State Machine & Orchestration

Purpose:

Provide explicit bounded agent execution.

Core components:

```text
Planner
State Machine
Orchestrator
Tools
Reflector
Validator
```

The orchestrator connects earlier capabilities but does not bypass their boundaries.

Example:

```text
UNDERSTAND
   ↓
Router
   ↓
PLAN
   ↓
RAG Tool
   ↓
Vision Tool
   ↓
EXECUTE
   ↓
OBSERVE
   ↓
REFLECT
   ↓
VALIDATE
```

---

## Phase 8 — Sandbox / Controlled Tool Execution

Purpose:

Allow the agent to perform approved deterministic computations without unrestricted operating-system access.

Current principle:

```text
Agent
 ↓
Tool Registry
 ↓
Whitelist
 ↓
Argument Validation
 ↓
Sandbox Executor
 ↓
Deterministic Tool
 ↓
Result
```

Current MVP calculation tools are deliberately narrow.

The sandbox is not described as a perfect production security boundary on Windows. Stronger Linux/container isolation is a later deployment/hardening concern.

---

## Phase 9 — Structured Output & Validation

Purpose:

Prevent raw model output from becoming an unchecked final result.

Architecture:

```text
Agent / Local Model
       ↓
JSON Parser
       ↓
Pydantic Schema
       ↓
Engineering Validator
       ↓
Validated Result
       ↓
Deliverables
```

Validation covers items such as:

- valid JSON,
- required fields,
- equipment identifiers,
- positive thickness values,
- non-negative rates,
- calculation consistency,
- remaining-life consistency,
- recommendation consistency,
- required provenance/citations.

The validator does not claim regulatory compliance unless explicitly validated against a regulation.

---

## Phase 10 — Deterministic Office Deliverables

Purpose:

Generate professional files from validated structured results.

```text
Validated Result
       ↓
Deliverable Factory
       ├── DOCX Builder
       ├── XLSX Builder
       └── PPTX Builder
```

The AI does not directly write the Office file structure.

Output locations:

```text
outputs/
├── docx/
├── xlsx/
└── pptx/
```

Provenance from the validation layer is preserved in the deliverable data.

---

# 10. Phase 11 — Audit & Sovereignty Evidence

This is the next major layer after Office generation is frozen.

Purpose:

Provide evidence of what happened.

Expected capabilities:

## Audit Events

Record locally:

- event ID,
- timestamp,
- task ID,
- action,
- model role,
- tool,
- source/provenance,
- result status,
- errors,
- duration.

## Hash-Chain Audit

Conceptually:

```text
Event 1
  ↓ hash
Event 2
  ↓ hash
Event 3
  ↓ hash
Event 4
```

Tampering with an earlier event should be detectable through chain verification.

## Network Evidence

The system should record observable runtime network behavior.

Important distinction:

```text
Network monitor
≠
Physical air-gap
```

The monitor provides software/runtime evidence, while physical or OS-level isolation belongs to deployment.

---

# 11. Phase 12 — Workbench Frontend

The frontend becomes the visible control surface.

Required MVP views:

## Dashboard

- system status,
- local model status,
- capabilities,
- sovereignty status/evidence.

## Documents

- upload,
- processing status,
- metadata,
- document list.

## Task Workspace

- user objective,
- task status,
- current agent state,
- plan,
- selected capability/model role,
- retrieval,
- tool execution,
- validation,
- final result.

## Evidence

- retrieved sources,
- page numbers,
- citations,
- provenance.

## Outputs

- generated DOCX,
- XLSX,
- PPTX,
- download/open actions.

---

# 12. Phase 13 — End-to-End MVP Integration

This phase connects the complete pipeline:

```text
UI
 ↓
API
 ↓
Ingestion
 ↓
OCR/Vision
 ↓
RAG
 ↓
Agent
 ↓
Router
 ↓
Local Model Manager
 ↓
Sandbox Tools
 ↓
Validation
 ↓
Deliverables
 ↓
Audit
 ↓
UI Result
```

This is where the project becomes a complete demonstrable workbench.

---

# 13. Phase 14 — Accuracy & Performance Evaluation

The system must be measured rather than described only through architecture.

## RAG

- retrieval relevance,
- Precision@K,
- Recall@K,
- citation correctness.

## Router

- routing accuracy,
- fallback behavior,
- latency,
- resource use.

## Agent

- task completion,
- average steps,
- retry rate,
- recovery rate.

## Models

- latency,
- VRAM,
- RAM,
- output quality.

## End-to-End

- workflow success rate,
- execution time,
- output validity.

---

# 14. Phase 15 — Linux / On-Prem Validation

Windows is the current development environment.

The target deployment direction is Linux/on-premise.

The architecture must therefore avoid:

- Windows-only APIs,
- hardcoded drive letters,
- PowerShell dependencies,
- usernames,
- machine-specific paths.

Use:

- configurable paths,
- pathlib,
- environment configuration,
- replaceable providers,
- replaceable sandbox implementations.

Target deployment can later use stronger Linux/container isolation.

---

# 15. Phase 16 — Demo Hardening

Final focus:

- reliable demo data,
- deterministic startup,
- clear UI,
- fast execution,
- polished outputs,
- network evidence,
- audit trace,
- failure handling,
- presentation-ready screenshots,
- reproducible demo.

The goal is not to add more features.

The goal is to make the existing MVP **reliable, understandable, and convincing**.

---

# 16. Core Component Responsibilities

A major architectural rule is that every layer has one clear responsibility.

| Component | Responsibility |
|---|---|
| UI | User interaction and visualization |
| API | Request/response boundary |
| Ingestion | Convert files into normalized documents |
| OCR/Vision | Extract text/visual findings |
| RAG | Retrieve organizational knowledge |
| Router | Decide required task/capability/model role |
| Model Manager | Resolve/invoke local models |
| Agent | Decide execution sequence |
| Tools | Perform approved actions |
| Sandbox | Restrict tool execution |
| Validation | Check structured/engineering results |
| Deliverables | Create deterministic Office files |
| Audit | Record execution evidence |
| Network Monitor | Observe runtime network behavior |

---

# 17. Critical Architectural Boundaries

These boundaries must not be broken.

## Router must NOT:

- call Ollama,
- load models,
- hardcode model IDs,
- perform RAG,
- execute tools.

## Agent must NOT:

- directly access vector files,
- bypass the Tool Registry,
- execute arbitrary shell commands,
- directly call external services.

## RAG must NOT:

- fabricate citations,
- access external cloud search,
- bypass provenance.

## Deliverables must NOT:

- directly ask an LLM to create Office files,
- accept invalid validation results,
- fabricate source information.

## Sandbox must NOT:

- permit arbitrary command execution,
- use `shell=True`,
- expose unrestricted environment variables,
- allow unrestricted filesystem access.

---

# 18. Data Provenance

Trust is a major part of the project.

The desired chain is:

```text
Final Result
     ↓
Validated Finding
     ↓
Agent Observation
     ↓
Retrieved Evidence
     ↓
Chunk
     ↓
Page / Section
     ↓
Original Document
     ↓
SHA-256
```

This allows the system to answer:

> Where did this result come from?

---

# 19. Local Model Strategy

The MVP is designed around practical local hardware.

Current development target:

```text
GPU: NVIDIA RTX 4060
VRAM: ~8 GB
RAM: 16 GB
```

The architecture therefore uses model roles and controlled loading.

Potential local model roles include:

```text
router / lightweight
reasoning
vision
coding
embedding
```

Exact model choices remain configurable and must be benchmarked on the actual hardware.

The system should not assume that a larger model is automatically better.

---

# 20. Model Manager vs Router

This distinction should be explained clearly in the PPT.

### Router

Answers:

> **What capability does this task need?**

Example:

```text
Image analysis
→ VISION capability
→ VISION model role
```

### Model Manager

Answers:

> **Which configured local model/provider currently implements that role?**

Example:

```text
VISION role
→ configured local VLM
→ local provider
→ inference
```

Therefore:

```text
ROUTER
  ↓
CAPABILITY / ROLE
  ↓
MODEL MANAGER
  ↓
LOCAL MODEL
```

---

# 21. Why Agent + RAG + Router Are Different

These components solve different problems.

### RAG

> What information do we know?

### Router

> What capability/model role should handle this task?

### Agent

> What steps should we perform, and in what order?

### Model Manager

> How do we invoke the selected local model?

### Tools

> What controlled action can we execute?

### Validator

> Is the result acceptable?

This separation is one of the most important architectural ideas in the project.

---

# 22. Example Full Execution Trace

```text
TASK CREATED
     │
     ▼
RECEIVE
     │
     ▼
UNDERSTAND
     │
     ├── Router
     │
     ▼
PLAN
     │
     ▼
EXECUTE
     │
     ├── RAG Retrieval
     ├── Vision
     └── Calculation Tool
     │
     ▼
OBSERVE
     │
     ▼
REFLECT
     │
     ├── Retry if required
     │
     ▼
VALIDATE
     │
     ├── Schema
     ├── Engineering checks
     └── Provenance
     │
     ▼
FINALIZE
     │
     ▼
DELIVER
     │
     ├── Answer
     ├── DOCX
     └── XLSX
     │
     ▼
AUDIT EVENT
```

---

# 23. What Makes This Different From a Normal Chatbot?

A normal chatbot:

```text
Question
 ↓
LLM
 ↓
Answer
```

A basic RAG system:

```text
Question
 ↓
Search
 ↓
Context
 ↓
LLM
 ↓
Answer
```

Our MVP:

```text
Goal
 ↓
Understand
 ↓
Plan
 ↓
Route
 ↓
Retrieve
 ↓
Reason
 ↓
Act
 ↓
Observe
 ↓
Reflect
 ↓
Validate
 ↓
Deliver
 ↓
Audit
```

The differentiator is therefore the **combination of sovereignty, routing, multimodality, bounded agency, verification, provenance, and deterministic deliverables**.

---

# 24. What We Are NOT Claiming

Technical credibility is important.

We should NOT claim:

- perfect AI accuracy,
- perfect OCR,
- perfect P&ID understanding,
- regulatory compliance unless separately validated,
- unrestricted autonomous industrial control,
- physical air-gap proof from application code alone,
- production-grade container isolation from the Windows sandbox,
- that mock embeddings prove semantic RAG accuracy,
- that a confidence score equals routing accuracy,
- that the MVP is a complete refinery enterprise platform.

Instead, say:

> The MVP demonstrates a controlled architecture and provides measurable evidence for its major capabilities.

---

# 25. MVP Security Model

The system follows defense-in-depth principles.

```text
                 SECURITY
                    │
     ┌──────────────┼───────────────┐
     ▼              ▼               ▼
Data Locality   Tool Control    Network Control
     │              │               │
     ▼              ▼               ▼
Local Storage   Whitelist       Local Provider
     │           + Schema        Restrictions
     │              │               │
     └──────────────┼───────────────┘
                    ▼
                 Audit
                    │
                    ▼
              Evidence / Trace
```

---

# 26. Storage Architecture

The MVP uses local storage boundaries.

```text
data/
├── raw/
├── processed/
├── knowledge/
└── samples/

outputs/
├── docx/
├── xlsx/
└── pptx/

logs/
```

The system should preserve:

- original documents,
- normalized documents,
- knowledge indexes,
- generated outputs,
- audit records.

---

# 27. Technology Direction

## Backend

- Python
- FastAPI
- Pydantic

## Frontend

- React/Next.js-based workbench

## Local AI

- Ollama/local inference
- configurable local models

## Document Processing

- PDF parsing
- DOCX parsing
- XLSX parsing
- CSV parsing
- Pillow
- OCR/Vision abstractions

## Knowledge

- local embeddings
- local vector storage
- RAG

## Tools

- controlled sandbox execution
- deterministic calculations

## Deliverables

- DOCX
- XLSX
- PPTX

## Infrastructure

- Windows development
- Linux/on-prem deployment target
- Docker/containerization where appropriate

---

# 28. Why We Chose a Focused MVP

A complete industrial enterprise platform would require:

- enterprise IAM,
- large-scale databases,
- ERP/CMMS/MES integration,
- SCADA/IoT integration,
- distributed model serving,
- high availability,
- multi-site deployment,
- extensive governance.

That is not the current objective.

Our MVP asks a much more valuable question:

> **Can we prove that a sovereign local AI system can take a real industrial objective, understand sensitive documents, retrieve evidence, route work to suitable local capabilities, execute bounded actions, verify the result, and produce a professional deliverable?**

If yes, the architecture has a strong foundation for future expansion.

---

# 29. MVP Completion Criteria

The MVP should be considered functionally complete when one complete workflow can reliably execute:

```text
UPLOAD
  ↓
INGEST
  ↓
UNDERSTAND
  ↓
RETRIEVE
  ↓
ROUTE
  ↓
PLAN
  ↓
EXECUTE
  ↓
OBSERVE
  ↓
REFLECT
  ↓
VALIDATE
  ↓
GENERATE
  ↓
AUDIT
  ↓
DISPLAY
```

And the system can demonstrate:

### Technical

- local inference,
- multimodal ingestion,
- RAG,
- model routing,
- agent state machine,
- controlled tools,
- structured validation,
- deterministic documents.

### Security

- local provider restrictions,
- no mandatory external AI APIs,
- sandbox controls,
- provenance,
- audit evidence,
- runtime network evidence.

### User Experience

- upload document,
- enter objective,
- watch execution,
- inspect evidence,
- receive final answer,
- receive professional files.

---

# 30. PPT-Ready Storyline

The presentation should tell one simple story.

## Slide 1 — Title

**SIH26117: Sovereign Agentic Industrial Intelligence Workbench**

Subtitle:

> Local AI for controlled, verifiable industrial intelligence

## Slide 2 — Problem

Industrial knowledge is:

- fragmented,
- sensitive,
- multimodal,
- difficult to operationalize.

## Slide 3 — Why Existing AI Is Not Enough

```text
Cloud AI
→ Data leaves environment

Single LLM
→ One model for everything

Basic RAG
→ Retrieve + answer

Chatbot
→ No controlled execution
```

## Slide 4 — Our Solution

```text
Goal
→ Know
→ Route
→ Plan
→ Act
→ Verify
→ Deliver
```

## Slide 5 — Five Pillars

1. Sovereign local operation
2. Dynamic model routing
3. Agentic execution
4. Multimodal intelligence
5. Deterministic deliverables

## Slide 6 — Architecture

Show the complete system architecture.

## Slide 7 — Agent

Show:

```text
Understand → Plan → Execute → Observe → Reflect → Validate → Deliver
```

## Slide 8 — Dynamic Model Routing

Show:

```text
Task → Capability → Model Role → Local Model
```

## Slide 9 — Document Intelligence + RAG

Show:

```text
Documents → OCR/Vision → Chunking → Embeddings → Retrieval → Citations
```

## Slide 10 — Controlled Tools

Show:

```text
Agent → Registry → Validation → Sandbox → Tool → Result
```

## Slide 11 — Structured Validation

Show:

```text
Model JSON
→ Pydantic
→ Engineering Validator
→ Valid Result
```

## Slide 12 — Deterministic Output

Show:

```text
Validated Result
→ DOCX
→ XLSX
→ PPTX
```

## Slide 13 — Sovereignty

Show:

```text
Local UI
 ↓
Local API
 ↓
Local Models
 ↓
Local Data
 ↓
Local Tools
```

Then show runtime network evidence.

## Slide 14 — North-Star Demo

C-101 corrosion/inspection audit.

## Slide 15 — End-to-End Demo Flow

```text
Document
→ RAG
→ Agent
→ Router
→ Local Model
→ Tool
→ Validation
→ Report
```

## Slide 16 — Current Progress

Show the completed phases and remaining phases.

## Slide 17 — Evaluation

Show:

- routing accuracy,
- retrieval quality,
- task completion,
- latency,
- resource usage,
- output validity.

## Slide 18 — Differentiators

```text
Sovereign
+
Agentic
+
Multimodal
+
Multi-Model
+
Verifiable
+
Deterministic
```

## Slide 19 — Future Scope

Only after MVP:

- enterprise integrations,
- larger model infrastructure,
- advanced access control,
- additional industrial workflows,
- deeper on-prem deployment.

## Slide 20 — Conclusion

> **From sensitive industrial knowledge to controlled, verifiable action — entirely within a sovereign local intelligence layer.**

---

# 31. Team Explanation

Every team member should be able to explain the project in this sequence:

```text
PROBLEM
↓
Sensitive industrial knowledge is fragmented and difficult to use safely.

SOLUTION
↓
Build a sovereign local AI workbench.

INPUT
↓
Industrial documents + user objective.

INTELLIGENCE
↓
OCR/Vision + RAG + local models.

DECISION
↓
Router selects required capability.

AGENCY
↓
Agent plans and executes bounded steps.

ACTION
↓
Approved tools execute calculations/tasks.

SAFETY
↓
Sandbox + validation + provenance.

OUTPUT
↓
Professional DOCX/XLSX/PPTX.

EVIDENCE
↓
Audit + network/runtime evidence.
```

---

# 32. Final Mental Model

Remember the entire project as:

```text
             KNOW
              │
              ▼
            ROUTE
              │
              ▼
             PLAN
              │
              ▼
             ACT
              │
              ▼
           OBSERVE
              │
              ▼
           REFLECT
              │
              ▼
           VALIDATE
              │
              ▼
           DELIVER
              │
              ▼
            AUDIT
```

Or in one line:

> **GOAL → KNOW → ROUTE → PLAN → ACT → VERIFY → DELIVER → AUDIT**

---

# 33. Final Project Definition

We are building a **focused MVP of a sovereign, local-first, agentic industrial intelligence workbench for MRPL**.

It is designed to allow an engineer to provide sensitive industrial documents and a real operational objective. The system processes the information locally, retrieves relevant evidence, determines the required capability, selects an appropriate local model, creates a bounded execution plan, uses approved tools, observes and reflects on the results, validates the final output, preserves provenance, generates deterministic business documents, and records evidence of execution and network behavior.

The project is **not a chatbot, not simply a RAG system, and not a full enterprise refinery platform**.

Its core value is the combination of:

```text
SOVEREIGN LOCAL AI
        +
MULTIMODAL INDUSTRIAL KNOWLEDGE
        +
DYNAMIC MODEL ROUTING
        +
CONTROLLED AGENTIC EXECUTION
        +
VERIFICATION
        +
DETERMINISTIC BUSINESS OUTPUT
        +
AUDITABILITY
```

That combination is the MVP we are building.