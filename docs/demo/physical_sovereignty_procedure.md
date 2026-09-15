# SIH26117 — Physical Air-Gap Sovereignty Demonstration Procedure

**Project:** Sovereign On-Premise Agentic AI Workbench for MRPL  
**Scope:** Controlled Demonstration of Air-Gapped Operation, Operator Attestation, and E2E Workflow Execution  
**Document Revision:** 1.0 (Post-Phase-16 Sovereignty Hardening)  

---

## 1. Technical Premise & Truthfulness Invariant

> [!IMPORTANT]
> **Critical Truthfulness Rule:** Software running inside an operating system **cannot independently prove a physical air gap** (e.g., that an RJ45 Ethernet patch cable is physically disconnected from the machine or that no external path exists outside the host socket table).
> 
> The system strictly distinguishes:
> 1. **Software Locality:** Measured runtime bindings of application processes to `127.0.0.1` loopback (FastAPI, Ollama, Vector Store, Sandbox).
> 2. **Network Observation:** Host TCP socket table observations via the Windows IP Helper API (`RuntimeNetworkMonitor`), confirming 0 foreign/non-loopback egress sockets.
> 3. **Physical Isolation:** An explicit, auditable **operator-verified condition** recorded into the immutable SHA-256 hash-chained local audit ledger.

---

## 2. Pre-Requisites & System Inventory

Ensure all required local dependencies, assets, and weights are present before initiating isolation:

- **Local Model Weights (Ollama on `127.0.0.1:11434`):**
  - Vision/Reasoning: `qwen2.5vl:3b`
  - Embedding Engine: `nomic-embed-text:latest` (768 dimensions)
- **Local Knowledge Corpus (`data/knowledge/default/`):**
  - 10 Controlled Demonstration Industrial Engineering SOPs and NDT inspection documents
  - Pre-computed 768-d vector embeddings in `index.npy` and `metadata.json`
- **Frontend Assets:**
  - Fully local bundle (`dist/`) containing bundled WOFF2 typography (Manrope, Space Grotesk, JetBrains Mono)
  - Zero CDN, zero external fonts, zero external scripts, zero analytics

---

## 3. Step-by-Step Operator Demonstration Protocol

### Step 1: Pre-Flight Verification (While Online if Initial Setup Required)
1. Launch local Ollama runtime:
   ```powershell
   ollama serve
   ```
2. Launch FastAPI backend on loopback interface:
   ```powershell
   $env:PYTHONPATH = "d:\PROJECT WORKS\SIH 2026;d:\PROJECT WORKS\SIH 2026\backend"
   .\backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
   ```
3. Launch React + Vite frontend:
   ```powershell
   npx vite --host 127.0.0.1 --port 5173
   ```
4. Verify backend health endpoint responds:
   ```powershell
   curl http://127.0.0.1:8000/api/v1/system/health
   ```

---

### Step 2: Physical Network Isolation
To establish physical air-gap conditions for evaluation:

1. **Disconnect Ethernet:** Physically pull the RJ45 network cable from the workstation.
2. **Disable Wi-Fi:**
   - In Windows: Settings &rarr; Network &amp; Internet &rarr; Wi-Fi &rarr; **Toggle OFF**.
   - Or run in administrator PowerShell:
     ```powershell
     netsh interface set interface name="Wi-Fi" admin=DISABLED
     ```
3. **Disable Secondary Adapters:** Disconnect cellular dongles, USB tethering, and Bluetooth network adapters.
4. **Verify Route Isolation:**
   Run in PowerShell:
   ```powershell
   route print 0.0.0.0
   ```
   *Expected Output:* No active default gateway or route to public IP ranges.
5. **Verify No Internet Egress:**
   ```powershell
   ping 8.8.8.8 -n 1
   ```
   *Expected Result:* `Destination host unreachable` or `General failure`.

---

### Step 3: Sovereign Control Deck Inspection
1. Open the browser to `http://127.0.0.1:5173/sovereignty`.
2. Observe the **Sovereignty Status Matrix**:
   - `SOFTWARE LOCALITY`: **PASS** (FastAPI + Ollama on 127.0.0.1)
   - `LOCAL MODEL RUNTIME`: **PASS** (`qwen2.5vl:3b`)
   - `LOCAL KNOWLEDGE`: **PASS** (Nomic 768-d Vector Index)
   - `EXTERNAL CONNECTIONS`: **0 OBSERVED**
   - `NETWORK OBSERVATION`: **PASS** (Loopback Interface Only)
   - `PHYSICAL AIR-GAP`: **OPERATOR CHECK REQUIRED** *(truthful initial state)*
3. Click **"Audit Host Sockets"**:
   - Observe live socket query via Windows IP Helper API (`GetExtendedTcpTable`).
   - Confirm all active bindings are restricted to `127.0.0.1` and `0.0.0.0:LISTENING`.

---

### Step 4: Record Physical Isolation Attestation
1. Click the **[ Verify Physical Isolation ]** button (or use `Cmd/Ctrl + K` &rarr; "Verify Physical Isolation").
2. The **Physical Air-Gap Operator Attestation Modal** appears.
3. Review and check the 6 physical invariants:
   - [x] **Ethernet Cable Disconnected**
   - [x] **Wi-Fi Disabled**
   - [x] **Internet-Capable Adapters Isolated**
   - [x] **No External Route Available**
   - [x] **Unnecessary Radios Disabled**
   - [x] **Operator Continuity Confirmation**
4. Enter optional operator identifier/notes (e.g., `SIH Evaluation Station 1 — Physical Isolation Confirmed`).
5. Click **[ Confirm Physical Isolation ]**.
6. Observe:
   - Status badge transitions to `PHYSICAL ISOLATION: OPERATOR VERIFIED`.
   - Attestation certificate card renders with timestamp, event ID, hostname, and SHA-256 event hash.
   - An immutable audit event of type `PHYSICAL_ISOLATION_ATTESTED` is permanently appended to `data/audit/events.jsonl`.

---

### Step 5: Execute Autonomous C-101 Workflow in Isolated State
1. Navigate to `http://127.0.0.1:5173/workbench`.
2. Verify execution controls:
   - Select Preset: **C-101 Column Corrosion & Remaining Life Audit (API 570)**.
   - Select Mode: **Live Local Model** (or **Demo Pipeline**).
   - Confirm **Data Source Badges** indicate `LIVE — LOCAL OLLAMA` or `DEMO — DETERMINISTIC`.
3. Click **[ Execute Analysis ]** (or press `Enter`):
   - **Stage 1 (Vision):** Local multimodal VLM (`qwen2.5vl:3b`) ingests UT survey grid without cloud APIs.
   - **Stage 2 (Router):** Intent classifier assigns Level 0 execution plan.
   - **Stage 3 (Sovereign RAG):** Dense vector retriever queries the 768-d Nomic vector index in `data/knowledge/default/`, retrieving exact citations from `SOP-MRPL-PIP-001`.
   - **Stage 4 (Deterministic Math):** Computes metal loss (`0.38 mm/year`) and remaining life (`5.53 years`) per API 570 formula inside isolated local sandbox.
   - **Stage 5 (Validation Gate):** 12-cell Fuse Box transitions from **STANDBY** to **12/12 PASSED** with green invariants.
   - **Stage 6 (Clean-Room Compilers):** Python compilers assemble stamped `.docx` and `.xlsx` deliverables, signed with SHA-256.
   - **Stage 7 (Audit Hash Chain):** Task completion and stage hashes recorded to local JSONL ledger.

---

### Step 6: Verify Cryptographic Ledger & Deliverables
1. Navigate to `http://127.0.0.1:5173/audit`.
2. Click **[ Verify Full Hash Chain ]**:
   - Backend scans sequential event digests from genesis to current event.
   - Confirm `Zero tampering detected` across unbroken SHA-256 links.
   - Confirm the `PHYSICAL_ISOLATION_ATTESTED` event is present in the ledger.
3. In the Workbench Deliverables Factory:
   - Click **Download Clean-Room DOCX** and **Download Clean-Room XLSX**.
   - Inspect files locally in Microsoft Word/Excel or LibreOffice to verify professional executive branding and numerical consistency.

---

## 4. Technical Defense & Judge Q&A Guide

| Question / Challenge | Defensible Architectural Answer |
| :--- | :--- |
| **"How do you prove this didn't make a cloud API call?"** | 1. Host socket inspection (`RuntimeNetworkMonitor`) queries the OS TCP table via `GetExtendedTcpTable` continuously, logging 0 foreign sockets.<br>2. Wi-Fi and Ethernet are physically disconnected during the live demo.<br>3. Fail-closed network monitor terminates execution and withholds deliverables if non-loopback egress is detected. |
| **"Does the software prove the cable is unplugged?"** | **No.** We honestly acknowledge that software cannot detect physical air gaps alone. Software proves local runtime sockets; physical isolation is established by the operator and attested via an immutable audit certificate. |
| **"Where are the embeddings stored?"** | Stored entirely on local NVMe disk in `data/knowledge/default/index.npy` and `metadata.json` (768 dimensions from `nomic-embed-text`). No external vector database or cloud vector service is used. |
| **"Can this run in a SCADA bunker?"** | Yes. The entire stack (FastAPI, Ollama, React bundle, Python math sandbox, docx/xlsx compilers) requires only a local edge workstation (e.g., RTX 4060) with zero Internet connectivity. |
