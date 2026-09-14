"""
SIH26117 — Phase 14: Labeled Synthetic Benchmark Datasets

Provides reproducible, domain-representative datasets for:
1. Router classification: 64 labeled tasks across all 8 TaskTypes (8 per class).
2. RAG Retrieval: 12 labeled industrial SOP questions mapped to ground-truth chunks in SOP-MRPL-PIP-001.pdf.
3. P&ID / Drawing Extraction: Synthetic ground truth for equipment tags, instrument bubbles, lines, and bounding boxes.
"""

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# 1. Router Classification Dataset (64 items: 8 classes x 8 samples)
# ---------------------------------------------------------------------------
ROUTER_BENCHMARK_DATASET: List[Dict[str, str]] = [
    # --- VISION (Priority 1) ---
    {
        "task_id": "vis_01",
        "task": "Inspect P&ID diagram for Atmospheric Distillation Column C-101 and locate pressure transmitter PT-101",
        "expected_task_type": "vision",
        "expected_capability": "vision",
        "expected_model_role": "vision",
    },
    {
        "task_id": "vis_02",
        "task": "Extract instrument tags and piping diagram connections from unit schematic scan",
        "expected_task_type": "vision",
        "expected_capability": "vision",
        "expected_model_role": "vision",
    },
    {
        "task_id": "vis_03",
        "task": "Read the gauge dial reading from the uploaded inspection photograph",
        "expected_task_type": "vision",
        "expected_capability": "vision",
        "expected_model_role": "vision",
    },
    {
        "task_id": "vis_04",
        "task": "Analyze the process flow diagram drawing for the vacuum distillation overhead system",
        "expected_task_type": "vision",
        "expected_capability": "vision",
        "expected_model_role": "vision",
    },
    {
        "task_id": "vis_05",
        "task": "Identify the tag number on the heat exchanger nameplate in this picture",
        "expected_task_type": "vision",
        "expected_capability": "vision",
        "expected_model_role": "vision",
    },
    {
        "task_id": "vis_06",
        "task": "Review visual plate figure showing localized pitting corrosion on flange face",
        "expected_task_type": "vision",
        "expected_capability": "vision",
        "expected_model_role": "vision",
    },
    {
        "task_id": "vis_07",
        "task": "Perform visual understanding on flowsheet showing CDU preheat train layout",
        "expected_task_type": "vision",
        "expected_capability": "vision",
        "expected_model_role": "vision",
    },
    {
        "task_id": "vis_08",
        "task": "Check piping and instrumentation diagram for relief valve RV-204 discharge routing",
        "expected_task_type": "vision",
        "expected_capability": "vision",
        "expected_model_role": "vision",
    },

    # --- CODING (Priority 2) ---
    {
        "task_id": "cod_01",
        "task": "Write a python script to parse csv thickness gauging readings into a structured dataframe",
        "expected_task_type": "coding",
        "expected_capability": "coding",
        "expected_model_role": "coder",
    },
    {
        "task_id": "cod_02",
        "task": "Implement an algorithm in python to detect anomaly spikes in sensor telemetry streams",
        "expected_task_type": "coding",
        "expected_capability": "coding",
        "expected_model_role": "coder",
    },
    {
        "task_id": "cod_03",
        "task": "Fix the code error in the json parser module handling temperature logs",
        "expected_task_type": "coding",
        "expected_capability": "coding",
        "expected_model_role": "coder",
    },
    {
        "task_id": "cod_04",
        "task": "Generate code for a unit test suite using pytest to validate corrosion formula calculations",
        "expected_task_type": "coding",
        "expected_capability": "coding",
        "expected_model_role": "coder",
    },
    {
        "task_id": "cod_05",
        "task": "Write an automation script in bash to archive daily refinery unit log directories",
        "expected_task_type": "coding",
        "expected_capability": "coding",
        "expected_model_role": "coder",
    },
    {
        "task_id": "cod_06",
        "task": "Implement a function to execute sql query against the plant maintenance database",
        "expected_task_type": "coding",
        "expected_capability": "coding",
        "expected_model_role": "coder",
    },
    {
        "task_id": "cod_07",
        "task": "Debug the syntax error in the python class managing serial port communication",
        "expected_task_type": "coding",
        "expected_capability": "coding",
        "expected_model_role": "coder",
    },
    {
        "task_id": "cod_08",
        "task": "Write a python program to parse xml instrumentation exchange files",
        "expected_task_type": "coding",
        "expected_capability": "coding",
        "expected_model_role": "coder",
    },

    # --- CALCULATION (Priority 3) ---
    {
        "task_id": "calc_01",
        "task": "Calculate the corrosion rate in mm/year for crude transfer line between 2021 and 2026",
        "expected_task_type": "calculation",
        "expected_capability": "calculation",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "calc_02",
        "task": "Compute remaining life and retirement date using API 570 formula for nozzle N-1",
        "expected_task_type": "calculation",
        "expected_capability": "calculation",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "calc_03",
        "task": "Calculate wall thickness tmin requirement based on ASME B31.3 internal design pressure",
        "expected_task_type": "calculation",
        "expected_capability": "calculation",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "calc_04",
        "task": "Determine pressure drop across orifice plate given fluid density and volumetric flow rate",
        "expected_task_type": "calculation",
        "expected_capability": "calculation",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "calc_05",
        "task": "Solve for heat transfer coefficient and thermal efficiency in shell and tube reboiler E-102",
        "expected_task_type": "calculation",
        "expected_capability": "calculation",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "calc_06",
        "task": "Compute mass balance percentage yield of naphtha cut from crude assay distillation curve",
        "expected_task_type": "calculation",
        "expected_capability": "calculation",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "calc_07",
        "task": "Evaluate fitness for service API 579 remaining life based on ultrasonic thickness measurement",
        "expected_task_type": "calculation",
        "expected_capability": "calculation",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "calc_08",
        "task": "Calculate allowable stress and pressure rating for ASTM A106 Grade B pipe at 350 deg C",
        "expected_task_type": "calculation",
        "expected_capability": "calculation",
        "expected_model_role": "reasoning",
    },

    # --- EXTRACTION (Priority 4) ---
    {
        "task_id": "ext_01",
        "task": "Extract all equipment tags and design parameters from the vendor datasheet",
        "expected_task_type": "extraction",
        "expected_capability": "extraction",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "ext_02",
        "task": "List the calibration dates and serial numbers for all transmitters in the unit log",
        "expected_task_type": "extraction",
        "expected_capability": "extraction",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "ext_03",
        "task": "Tabulate all ultrasonic thickness measurement values from the inspection report",
        "expected_task_type": "extraction",
        "expected_capability": "extraction",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "ext_04",
        "task": "Pull out the pump impeller specifications and motor ratings from equipment manual",
        "expected_task_type": "extraction",
        "expected_capability": "extraction",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "ext_05",
        "task": "Enumerate the operating temperature limits from section 3 of the process specification",
        "expected_task_type": "extraction",
        "expected_capability": "extraction",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "ext_06",
        "task": "Find the values of test pressure and holding duration from the hydrostatic test certificate",
        "expected_task_type": "extraction",
        "expected_capability": "extraction",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "ext_07",
        "task": "Identify all relief valve set points and orifice sizes from the safety valve register",
        "expected_task_type": "extraction",
        "expected_capability": "extraction",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "ext_08",
        "task": "Extract table of corrosion monitoring locations CML coordinates from the inspection annexure",
        "expected_task_type": "extraction",
        "expected_capability": "extraction",
        "expected_model_role": "reasoning",
    },

    # --- SUMMARIZATION (Priority 5) ---
    {
        "task_id": "sum_01",
        "task": "Summarize the key findings from the annual turnaround maintenance review",
        "expected_task_type": "summarization",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "sum_02",
        "task": "Provide an executive summary of the safety incident investigation report",
        "expected_task_type": "summarization",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "sum_03",
        "task": "Give a brief tl;dr overview of the quarterly steam system energy audit",
        "expected_task_type": "summarization",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "sum_04",
        "task": "Condense the twenty page sulfur recovery unit performance audit into bullet points",
        "expected_task_type": "summarization",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "sum_05",
        "task": "Recap the main conclusions from the crude distillation unit energy efficiency study",
        "expected_task_type": "summarization",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "sum_06",
        "task": "Create a summary highlight of the mechanical integrity findings for storage tank TK-501",
        "expected_task_type": "summarization",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "sum_07",
        "task": "Shorten the environmental discharge compliance memo for the shift supervisor briefing",
        "expected_task_type": "summarization",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "sum_08",
        "task": "Provide an abstract and overview of the hydrocracker catalyst deactivation report",
        "expected_task_type": "summarization",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },

    # --- DOCUMENT ANALYSIS (Priority 6) ---
    {
        "task_id": "doc_01",
        "task": "Analyze this ndt report to verify compliance with MRPL standard operating procedure",
        "expected_task_type": "document_analysis",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "doc_02",
        "task": "Review this engineering specification against statutory OISD-118 requirements",
        "expected_task_type": "document_analysis",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "doc_03",
        "task": "What does the refinery maintenance manual prescribe for centrifugal compressor seal replacement",
        "expected_task_type": "document_analysis",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "doc_04",
        "task": "Interpret the ultrasonic inspection report to identify pit depth exceeding structural tolerance",
        "expected_task_type": "document_analysis",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "doc_05",
        "task": "Analyze this technical datasheet to confirm material spec compatibility with sour crude service",
        "expected_task_type": "document_analysis",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "doc_06",
        "task": "Review this vendor bid proposal for crude preheat heat exchanger retubing",
        "expected_task_type": "document_analysis",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "doc_07",
        "task": "Verify according to SOP-MRPL-PIP-001 whether wall thinning requires isolation tagging",
        "expected_task_type": "document_analysis",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "doc_08",
        "task": "Based on the engineering report determine if shutdown overhaul interval can be extended",
        "expected_task_type": "document_analysis",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },

    # --- REASONING (Priority 7) ---
    {
        "task_id": "rea_01",
        "task": "Compare the advantages and disadvantages of 316L stainless steel vs duplex alloy in cooling water service",
        "expected_task_type": "reasoning",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "rea_02",
        "task": "Evaluate the operational tradeoff between higher reflux ratio and reboiler steam consumption",
        "expected_task_type": "reasoning",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "rea_03",
        "task": "Recommend an optimal replacement strategy for heat exchanger bundles nearing retirement",
        "expected_task_type": "reasoning",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "rea_04",
        "task": "Explain why high naphthenic acid crude causes severe corrosion between 220 and 280 deg C",
        "expected_task_type": "reasoning",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "rea_05",
        "task": "Think through step by step how to isolate overhead condenser E-101 without tripping column C-101",
        "expected_task_type": "reasoning",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "rea_06",
        "task": "Justify the decision to downgrade design pressure rating of vacuum furnace transfer line",
        "expected_task_type": "reasoning",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "rea_07",
        "task": "Assess risk of stress corrosion cracking under thermal insulation on austenitic piping",
        "expected_task_type": "reasoning",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "rea_08",
        "task": "Determine the pros and cons of using polysulfide injection to control cyanide corrosion",
        "expected_task_type": "reasoning",
        "expected_capability": "reasoning",
        "expected_model_role": "reasoning",
    },

    # --- GENERAL (Priority 8 / Fallback) ---
    {
        "task_id": "gen_01",
        "task": "Hello assistant how are you today",
        "expected_task_type": "general",
        "expected_capability": "general",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "gen_02",
        "task": "What is the capital of Karnataka state",
        "expected_task_type": "general",
        "expected_capability": "general",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "gen_03",
        "task": "Give me some general productivity advice for industrial shift workers",
        "expected_task_type": "general",
        "expected_capability": "general",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "gen_04",
        "task": "Good morning please introduce your capabilities",
        "expected_task_type": "general",
        "expected_capability": "general",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "gen_05",
        "task": "Tell me an interesting historical fact about petroleum refining",
        "expected_task_type": "general",
        "expected_capability": "general",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "gen_06",
        "task": "What are common unit conversion constants used in mechanical engineering",
        "expected_task_type": "general",
        "expected_capability": "general",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "gen_07",
        "task": "Can you assist me with refinery operations today",
        "expected_task_type": "general",
        "expected_capability": "general",
        "expected_model_role": "reasoning",
    },
    {
        "task_id": "gen_08",
        "task": "Thank you for the helpful response have a great day",
        "expected_task_type": "general",
        "expected_capability": "general",
        "expected_model_role": "reasoning",
    },
]


# ---------------------------------------------------------------------------
# 2. Labeled RAG Retrieval Benchmark Dataset (Mapped to SOP-MRPL-PIP-001.pdf)
# ---------------------------------------------------------------------------
RAG_BENCHMARK_DATASET: List[Dict[str, Any]] = [
    {
        "query_id": "rag_01",
        "query": "What is the minimum allowable retirement wall thickness for Class 150 carbon steel piping?",
        "ground_truth_chunk_ids": ["a1b2c3d4e5f6_p3_c0002", "a1b2c3d4e5f6_p3_c0003"],
        "expected_source_doc": "SOP-MRPL-PIP-001.pdf",
        "expected_page": 3,
        "keywords": ["3.2 mm", "Class 150", "ASTM A106 Grade B"],
    },
    {
        "query_id": "rag_02",
        "query": "What actions are mandated if ultrasonic thickness reading falls below 3.2 mm?",
        "ground_truth_chunk_ids": ["a1b2c3d4e5f6_p3_c0002"],
        "expected_source_doc": "SOP-MRPL-PIP-001.pdf",
        "expected_page": 3,
        "keywords": ["non-conformance reporting", "isolation tagging", "Head of Asset Integrity"],
    },
    {
        "query_id": "rag_03",
        "query": "What standards must ultrasonic thickness measurements comply with according to Lead Engineer responsibilities?",
        "ground_truth_chunk_ids": ["a1b2c3d4e5f6_p2_c0001"],
        "expected_source_doc": "SOP-MRPL-PIP-001.pdf",
        "expected_page": 2,
        "keywords": ["API 570", "ASME B31.3"],
    },
    {
        "query_id": "rag_04",
        "query": "Where must Corrosion Monitoring Locations CML be permanently marked?",
        "ground_truth_chunk_ids": ["a1b2c3d4e5f6_p2_c0001"],
        "expected_source_doc": "SOP-MRPL-PIP-001.pdf",
        "expected_page": 2,
        "keywords": ["piping spools", "permanently marked"],
    },
    {
        "query_id": "rag_05",
        "query": "What units are covered under the piping integrity inspection standard operating procedure scope?",
        "ground_truth_chunk_ids": ["a1b2c3d4e5f6_p1_c0000"],
        "expected_source_doc": "SOP-MRPL-PIP-001.pdf",
        "expected_page": 1,
        "keywords": ["MRPL Phase I and Phase II units", "crude distillation", "secondary processing"],
    },
    {
        "query_id": "rag_06",
        "query": "What is the document code and revision number of the piping integrity inspection standard operating procedure?",
        "ground_truth_chunk_ids": ["a1b2c3d4e5f6_p1_c0000"],
        "expected_source_doc": "SOP-MRPL-PIP-001.pdf",
        "expected_page": 1,
        "keywords": ["SOP-MRPL-PIP-001", "Revision: 04"],
    },
    {
        "query_id": "rag_07",
        "query": "According to the table specifications what is the nominal wall thickness for a 6 inch Class 150 pipe?",
        "ground_truth_chunk_ids": ["a1b2c3d4e5f6_p3_c0003"],
        "expected_source_doc": "SOP-MRPL-PIP-001.pdf",
        "expected_page": 3,
        "keywords": ["7.11", "6 inch", "Class 150"],
    },
    {
        "query_id": "rag_08",
        "query": "What is the nominal wall thickness for a 10 inch Class 150 ASTM A106 pipe?",
        "ground_truth_chunk_ids": ["a1b2c3d4e5f6_p3_c0003"],
        "expected_source_doc": "SOP-MRPL-PIP-001.pdf",
        "expected_page": 3,
        "keywords": ["9.27", "10 inch", "3.20"],
    },
    {
        "query_id": "rag_09",
        "query": "What is the minimum retirement wall thickness specified in the table for 2 inch Class 150 pipes?",
        "ground_truth_chunk_ids": ["a1b2c3d4e5f6_p3_c0003"],
        "expected_source_doc": "SOP-MRPL-PIP-001.pdf",
        "expected_page": 3,
        "keywords": ["3.20", "2 inch", "3.91"],
    },
    {
        "query_id": "rag_10",
        "query": "Who is the authority that must be notified when ultrasonic thickness gauging reading falls below 3.2 mm?",
        "ground_truth_chunk_ids": ["a1b2c3d4e5f6_p3_c0002"],
        "expected_source_doc": "SOP-MRPL-PIP-001.pdf",
        "expected_page": 3,
        "keywords": ["Head of Asset Integrity"],
    },
    # Negative queries (should evaluate empty retrieval or below threshold)
    {
        "query_id": "rag_neg_01",
        "query": "What is the recipe for baking chocolate chip cookies in an electric oven?",
        "ground_truth_chunk_ids": [],  # Expected empty
        "expected_source_doc": None,
        "expected_page": None,
        "keywords": [],
    },
    {
        "query_id": "rag_neg_02",
        "query": "Who won the ICC cricket world cup in 2011?",
        "ground_truth_chunk_ids": [],  # Expected empty
        "expected_source_doc": None,
        "expected_page": None,
        "keywords": [],
    },
]


# ---------------------------------------------------------------------------
# 3. P&ID and Engineering Drawing Synthetic Ground Truth
# ---------------------------------------------------------------------------
PID_GROUND_TRUTH: Dict[str, Any] = {
    "drawing_id": "DWG-MRPL-CDU-0101-P&ID",
    "sheet_title": "Atmospheric Crude Distillation Column C-101 Overhead Circuit",
    "expected_tags": [
        {"tag": "C-101", "type": "equipment_tag", "bbox": [0.20, 0.15, 0.45, 0.75]},
        {"tag": "PT-101", "type": "instrument_tag", "bbox": [0.48, 0.30, 0.55, 0.38]},
        {"tag": "FT-202", "type": "instrument_tag", "bbox": [0.10, 0.50, 0.18, 0.58]},
        {"tag": "TT-101", "type": "instrument_tag", "bbox": [0.35, 0.70, 0.42, 0.78]},
        {"tag": "10-CDU-0101-CS150", "type": "line_id", "bbox": [0.25, 0.80, 0.60, 0.85]},
    ],
}
