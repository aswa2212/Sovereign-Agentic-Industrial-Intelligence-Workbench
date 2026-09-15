/**
 * SIH26117 — Comprehensive Realistic Mock Data Layer
 * Source of Truth: SIH26117_MASTER_PROJECT_REPORT.md §3, §4, §5, §7
 * Used as an automatic fallback when running without the live FastAPI backend,
 * enabling full offline air-gapped demonstration of every feature and state.
 */

import {
  HealthResponse,
  SystemStatusResponse,
  TierConfigResponse,
  BackendHealthResponse,
  ModelListResponse,
  RAGStatusResponse,
  RAGQueryResponse,
  RouteResponse,
} from '../types/api';
import {
  AuditEvent,
  AuditVerificationResult,
  NetworkObservationReport,
  SovereigntyStatus,
} from '../types/audit';
import {
  AgentRunResponse,
  AgentTaskStatusResponse,
  CorrosionAuditResult,
  StructuredValidationReport,
} from '../types/agent';
import { GeneratedArtifact } from '../types/deliverables';
import { DocumentIngestionResult } from '../types/documents';

export const MOCK_HEALTH: HealthResponse = {
  status: 'ok',
  air_gap_verified: true,
  timestamp: new Date().toISOString(),
};

export const MOCK_SYSTEM_STATUS: SystemStatusResponse = {
  app_name: 'SIH26117 Sovereign On-Premise Workbench',
  app_version: '0.1.0-alpha.sovereign',
  environment: 'MRPL On-Premise Industrial Edge',
  air_gapped_mode: true,
  uptime_seconds: 14820,
};

export const MOCK_MODEL_TIER: TierConfigResponse = {
  tier_name: 'dev',
  description: 'Laptop Baseline Profile (NVIDIA RTX 4060 8 GB VRAM, 16 GB RAM)',
  vram_budget_gb: 8.0,
  max_concurrent_models: 1,
  models: [
    {
      role: 'router',
      provider: 'ollama',
      model_tag: 'qwen2.5:1.5b',
      context_window: 4096,
      quantization: 'Q4_K_M',
      device: 'gpu:0',
    },
    {
      role: 'coder',
      provider: 'ollama',
      model_tag: 'qwen2.5-coder:3b',
      context_window: 8192,
      quantization: 'Q4_K_M',
      device: 'gpu:0',
    },
    {
      role: 'reasoning',
      provider: 'ollama',
      model_tag: 'deepseek-r1:7b',
      context_window: 8192,
      quantization: 'Q4_K_M',
      device: 'gpu:0',
    },
    {
      role: 'vision',
      provider: 'ollama',
      model_tag: 'qwen2.5vl:3b',
      context_window: 4096,
      quantization: 'Q4_K_M',
      device: 'gpu:0',
    },
    {
      role: 'embedding',
      provider: 'local',
      model_tag: 'nomic-embed-text:latest',
      context_window: 2048,
      quantization: 'F16',
      device: 'cpu',
    },
  ],
};

export const MOCK_MODEL_HEALTH: BackendHealthResponse = {
  healthy: true,
  provider: 'ollama (127.0.0.1:11434)',
  message: 'Local inference daemon responsive. Serial swap active on 8GB VRAM.',
};

export const MOCK_MODEL_CATALOG: ModelListResponse = {
  active_tier: 'dev (8.0 GB VRAM Ceiling)',
  backend_healthy: true,
  total: 6,
  models: [
    {
      model_id: 'qwen2.5:1.5b',
      tag: 'qwen2.5:1.5b',
      provider: 'ollama',
      quantization: 'Q4_K_M',
      is_resident_in_vram: true,
      capabilities: {
        supports_vision: false,
        supports_tools: true,
        supports_thinking: false,
        max_context_length: 4096,
      },
    },
    {
      model_id: 'qwen2.5-coder:3b',
      tag: 'qwen2.5-coder:3b',
      provider: 'ollama',
      quantization: 'Q4_K_M',
      is_resident_in_vram: false,
      capabilities: {
        supports_vision: false,
        supports_tools: true,
        supports_thinking: false,
        max_context_length: 8192,
      },
    },
    {
      model_id: 'deepseek-r1:7b',
      tag: 'deepseek-r1:7b',
      provider: 'ollama',
      quantization: 'Q4_K_M',
      is_resident_in_vram: false,
      capabilities: {
        supports_vision: false,
        supports_tools: false,
        supports_thinking: true,
        max_context_length: 8192,
      },
    },
    {
      model_id: 'qwen2.5vl:3b',
      tag: 'qwen2.5vl:3b',
      provider: 'ollama',
      quantization: 'Q4_K_M',
      is_resident_in_vram: false,
      capabilities: {
        supports_vision: true,
        supports_tools: false,
        supports_thinking: false,
        max_context_length: 4096,
      },
    },
    {
      model_id: 'nomic-embed-text:latest',
      tag: 'nomic-embed-text:latest',
      provider: 'local',
      quantization: 'F16',
      is_resident_in_vram: false,
      capabilities: {
        supports_vision: false,
        supports_tools: false,
        supports_thinking: false,
        max_context_length: 2048,
      },
    },
    {
      model_id: 'bge-m3:latest',
      tag: 'bge-m3:latest',
      provider: 'local',
      quantization: 'F16',
      is_resident_in_vram: false,
      capabilities: {
        supports_vision: false,
        supports_tools: false,
        supports_thinking: false,
        max_context_length: 8192,
      },
    },
  ],
};

export const MOCK_RAG_STATUS: RAGStatusResponse = {
  status: 'READY',
  index_id: 'mrpl_sovereign_knowledge_v1',
  backend: 'ChromaDB Local Vector Engine',
  total_chunks: 148,
  indexed_documents_count: 8,
  dimension: 768,
  embedding_provider: 'nomic-embed-text (CPU Loopback)',
  storage_path: 'data/vector_index/chroma_mrpl',
};

export const MOCK_RAG_RESULTS: RAGQueryResponse = {
  query: 'API 570 retirement thickness formula',
  status: 'SUCCESS',
  retrieved_count: 3,
  results: [
    {
      chunk_id: 'chk-api570-04',
      document_id: 'doc-sop-mrpl-pip-001',
      source_document: 'SOP-MRPL-PIP-001.pdf',
      source_sha256: 'a9f24b89e27c191a78e47f2db8392110c735d4918e69d2703ab841cf5e9c011a',
      page_number: 3,
      section_index: 2,
      section_header: 'Section 4.2 — Retirement Thickness Criteria',
      text: 'For hydrocarbon process piping subject to uniform internal corrosion, minimum required structural thickness t_min must be calculated per ASME B31.3 Eq. 3a. For atmospheric distillation column overhead line C-101, structural minimum thickness t_min is certified at 8.00 mm.',
      similarity_score: 0.942,
      content_sha256: '45d9472e38c50e23801f99c1598da69315bc39031c26b52a12903332faefbb21',
      token_count: 74,
    },
    {
      chunk_id: 'chk-api570-05',
      document_id: 'doc-sop-mrpl-pip-001',
      source_document: 'SOP-MRPL-PIP-001.pdf',
      source_sha256: 'a9f24b89e27c191a78e47f2db8392110c735d4918e69d2703ab841cf5e9c011a',
      page_number: 4,
      section_index: 3,
      section_header: 'Section 5.1 — Remaining Service Life Formulation',
      text: 'Corrosion Rate CR = (t_initial - t_actual) / Elapsed Service Time T. Remaining Service Life RSL = (t_actual - t_min) / CR. If RSL exceeds 5.0 years, next ultrasonic statutory survey interval I_next shall be set to half the remaining life, not to exceed 5.0 calendar years.',
      similarity_score: 0.891,
      content_sha256: '723a109bc401b3e819b1689304192bce374900aef1c296715091d37452d3a9b1',
      token_count: 82,
    },
    {
      chunk_id: 'chk-api570-08',
      document_id: 'doc-sop-mrpl-pip-001',
      source_document: 'SOP-MRPL-PIP-001.pdf',
      source_sha256: 'a9f24b89e27c191a78e47f2db8392110c735d4918e69d2703ab841cf5e9c011a',
      page_number: 7,
      section_index: 5,
      section_header: 'Section 8.0 — Mandatory Engineering Validation Bounds',
      text: 'Any automated corrosion audit must satisfy all 12 validation rules prior to deliverable signing: non-negative wall thickness, nominal bound monotonicity, metal loss conservation, and positive life projection.',
      similarity_score: 0.835,
      content_sha256: '14b4e99f018e6d8a39c020f3248aa46d3e890a56f081267ea02c510839e1db28',
      token_count: 65,
    },
  ],
  citations: [],
};

export const MOCK_ROUTING_DECISION: RouteResponse = {
  task_type: 'corrosion_audit',
  capability: 'structured_engineering_calculation',
  model_role: 'reasoning',
  confidence: 0.985,
  reason: 'Matched MRPL piping inspection domain rule #401 (Overhead Column NDT Analysis)',
  routing_method: 'deterministic_rule_engine_l0',
};

export const MOCK_VALIDATION_REPORT: StructuredValidationReport = {
  valid: true,
  status: 'PASS',
  checks_total: 12,
  checks_passed_count: 12,
  checks_failed_count: 0,
  checks: [
    { id: 'CHK-01', rule_number: 1, name: 'Schema Conformity', description: 'Conforms to CorrosionAuditResult contract', status: 'PASSED', detail: 'All required schema fields verified' },
    { id: 'CHK-02', rule_number: 2, name: 'Required Fields', description: 'Equipment ID, current/nominal measurements present', status: 'PASSED', detail: 'C-101 identifiers verified' },
    { id: 'CHK-03', rule_number: 3, name: 'Non-Negative Thickness', description: 't_actual > 0.0 mm and t_initial > 0.0 mm', status: 'PASSED', detail: 't_actual=10.10mm, t_initial=12.00mm' },
    { id: 'CHK-04', rule_number: 4, name: 'Monotonicity Bound', description: 't_actual <= t_initial (physical wall loss constraint)', status: 'PASSED', detail: '10.10mm <= 12.00mm' },
    { id: 'CHK-05', rule_number: 5, name: 'Retirement Threshold', description: 't_actual > t_min (structural margin remains)', status: 'PASSED', detail: '10.10mm > 8.00mm (margin +2.10mm)' },
    { id: 'CHK-06', rule_number: 6, name: 'Metal Loss Conservation', description: 'Delta_t = t_initial - t_actual (+-0.01mm)', status: 'PASSED', detail: 'Delta_t = 1.90mm verified' },
    { id: 'CHK-07', rule_number: 7, name: 'Elapsed Time Positivity', description: 'Service duration T > 0.0 years', status: 'PASSED', detail: 'T = 5.00 years' },
    { id: 'CHK-08', rule_number: 8, name: 'Corrosion Rate Calculation', description: 'CR = Delta_t / T (+-0.001 mm/yr)', status: 'PASSED', detail: 'CR = 0.380 mm/year' },
    { id: 'CHK-09', rule_number: 9, name: 'Remaining Life Formula', description: 'RSL = (t_actual - t_min) / CR (+-0.01 yr)', status: 'PASSED', detail: 'RSL = 5.53 years' },
    { id: 'CHK-10', rule_number: 10, name: 'Recommendation Enum', description: 'Matches CONTINUE_SERVICE / REPAIR / SHUTDOWN', status: 'PASSED', detail: 'CONTINUE_SERVICE' },
    { id: 'CHK-11', rule_number: 11, name: 'Verbatim RAG Citation', description: 'SOP-MRPL-PIP-001 citation attached with page #', status: 'PASSED', detail: 'SOP-MRPL-PIP-001 Page 3 verified' },
    { id: 'CHK-12', rule_number: 12, name: 'Confidence Threshold', description: 'Decision confidence >= 0.85', status: 'PASSED', detail: 'Confidence = 0.985' },
  ],
  warnings: [],
};

export const MOCK_CORROSION_AUDIT_RESULT: CorrosionAuditResult = {
  task_id: 'task-c101-audit-2026',
  equipment_id: 'C-101',
  inspection_subject: 'Atmospheric Distillation Column Overhead Condenser Piping System',
  current_measurement: {
    value_mm: 10.10,
    measurement_date: '2026-03-12',
    location_tag: 'CML-4 (Elbow E-02 Downstream)',
  },
  initial_measurement: {
    value_mm: 12.00,
    measurement_date: '2021-03-15',
    location_tag: 'Baseline Commissioning Survey',
  },
  minimum_required_thickness_mm: 8.00,
  calculation: {
    metal_loss_mm: 1.90,
    elapsed_time_years: 5.00,
    corrosion_rate_mm_per_year: 0.380,
    remaining_life_years: 5.53,
    minimum_thickness_mm: 8.00,
    formula_used: 'API 570 §7.1.1 (CR = Delta_t / T; RSL = (t_actual - t_min) / CR)',
    inspection_interval_years: 2.76,
    remaining_margin_mm: 2.10,
  },
  findings: [
    {
      finding_id: 'FIND-01',
      description: 'Measured wall thickness at CML-4 is 10.10 mm, indicating uniform metal loss of 1.90 mm over 5.0 years.',
      severity: 'LOW',
    },
    {
      finding_id: 'FIND-02',
      description: 'Corrosion rate calculated at 0.380 mm/year is well within design allowance for ASTM A106 Grade B carbon steel service.',
      severity: 'LOW',
    },
    {
      finding_id: 'FIND-03',
      description: 'Statutory inspection interval calculated at 2.76 years mandates re-inspection prior to September 2028.',
      severity: 'MEDIUM',
    },
  ],
  conclusion: 'Atmospheric Column C-101 overhead line exhibits predictable, uniform corrosion kinetics. Immediate operation is safe without derating or shutdown.',
  recommendation: 'CONTINUE_SERVICE',
  citations: [
    {
      source_document: 'SOP-MRPL-PIP-001.pdf',
      page_number: 3,
      chunk_id: 'chk-api570-04',
      text: 'Minimum required structural thickness t_min for C-101 overhead line is certified at 8.00 mm.',
    },
    {
      source_document: 'SOP-MRPL-PIP-001.pdf',
      page_number: 4,
      chunk_id: 'chk-api570-05',
      text: 'Statutory ultrasonic inspection interval I_next = min(5.0, RSL / 2).',
    },
  ],
  confidence: 0.985,
};

export const MOCK_DELIVERABLES: GeneratedArtifact[] = [
  {
    artifact_id: 'art-c101-memorandum',
    format: 'docx',
    filename: 'MRPL_Corrosion_Audit_Memorandum_C101.docx',
    file_size_bytes: 42816,
    relative_path: 'outputs/deliverables/MRPL_Corrosion_Audit_Memorandum_C101.docx',
    storage_path: 'd:/PROJECT WORKS/SIH 2026/outputs/deliverables/MRPL_Corrosion_Audit_Memorandum_C101.docx',
    sha256_hash: '9f81a7b3c2e104859a0f3d61bc23456789abcdef0123456789abcdef01234567',
    sha256_checksum: '9f81a7b3c2e104859a0f3d61bc23456789abcdef0123456789abcdef01234567',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    download_url: '/api/v1/deliverables/art-c101-memorandum/download',
  },
  {
    artifact_id: 'art-c101-workbook',
    format: 'xlsx',
    filename: 'C101_API570_Corrosion_Calculation_Sheet.xlsx',
    file_size_bytes: 28672,
    relative_path: 'outputs/deliverables/C101_API570_Corrosion_Calculation_Sheet.xlsx',
    storage_path: 'd:/PROJECT WORKS/SIH 2026/outputs/deliverables/C101_API570_Corrosion_Calculation_Sheet.xlsx',
    sha256_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    sha256_checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    download_url: '/api/v1/deliverables/art-c101-workbook/download',
  },
];

export const MOCK_INGESTED_DOCUMENTS: DocumentIngestionResult[] = [
  {
    sha256: 'a9f24b89e27c191a78e47f2db8392110c735d4918e69d2703ab841cf5e9c011a',
    filename: 'corrosion_inspection_c101.pdf',
    content_type: 'application/pdf',
    size_bytes: 348160,
    page_count: 8,
    table_count: 4,
    storage_path: 'data/raw_inputs/corrosion_inspection_c101.pdf',
    extraction_summary: 'Parsed NDT thickness survey sheets, calibration logs, and ultrasonic test readings for column C-101.',
    created_at: '2026-03-12T08:15:00Z',
  },
  {
    sha256: '723a109bc401b3e819b1689304192bce374900aef1c296715091d37452d3a9b1',
    filename: 'pid_sample.png',
    content_type: 'image/png',
    size_bytes: 842100,
    page_count: 1,
    table_count: 1,
    storage_path: 'data/raw_inputs/pid_sample.png',
    extraction_summary: 'Extracted piping schematic tags, valves, orifice plates, and temperature indicators for CDU-1 overhead.',
    created_at: '2026-03-12T09:30:00Z',
  },
  {
    sha256: '14b4e99f018e6d8a39c020f3248aa46d3e890a56f081267ea02c510839e1db28',
    filename: 'SOP-MRPL-PIP-001.pdf',
    content_type: 'application/pdf',
    size_bytes: 1248000,
    page_count: 24,
    table_count: 6,
    storage_path: 'data/raw_inputs/SOP-MRPL-PIP-001.pdf',
    extraction_summary: 'MRPL Standard Operating Procedure for Piping Integrity Audits and API 570 Remaining Life Formulations.',
    created_at: '2026-02-10T14:20:00Z',
  },
];

export const MOCK_AUDIT_EVENTS: AuditEvent[] = [
  {
    event_id: 'evt-001-init',
    timestamp: '2026-09-15T06:40:12.100Z',
    event_type: 'TASK_STARTED',
    action: 'Initialize autonomous corrosion audit for equipment C-101',
    actor: 'agent_orchestrator',
    task_id: 'task-c101-audit-2026',
    status: 'SUCCESS',
    duration_ms: 12,
    metadata: { component_id: 'C-101', mode: 'deterministic' },
    previous_hash: '0000000000000000000000000000000000000000000000000000000000000000',
    event_hash: '7c89f1a23e4b5d6c7890123456789abcdef0123456789abcdef0123456789abc',
  },
  {
    event_id: 'evt-002-vlm',
    timestamp: '2026-09-15T06:40:12.350Z',
    event_type: 'VISION_ANALYSIS',
    action: 'Parse P&ID schematic for overhead nozzle coordinates',
    actor: 'qwen2.5vl:3b',
    model_role: 'vision',
    status: 'SUCCESS',
    duration_ms: 13720,
    metadata: { tags_detected: ['C-101', 'CML-4', 'PRV-102'] },
    previous_hash: '7c89f1a23e4b5d6c7890123456789abcdef0123456789abcdef0123456789abc',
    event_hash: '9a8b7c6d5e4f3a2b109876543210fedcba9876543210fedcba9876543210fedc',
  },
  {
    event_id: 'evt-003-route',
    timestamp: '2026-09-15T06:40:26.100Z',
    event_type: 'MODEL_ROUTED',
    action: 'Classified task to engineering_math with confidence 0.985',
    actor: 'rule_router_l0',
    model_role: 'router',
    status: 'SUCCESS',
    duration_ms: 16,
    metadata: { model_tag: 'qwen2.5:1.5b', task_type: 'corrosion_audit' },
    previous_hash: '9a8b7c6d5e4f3a2b109876543210fedcba9876543210fedcba9876543210fedc',
    event_hash: '3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e',
  },
  {
    event_id: 'evt-004-rag',
    timestamp: '2026-09-15T06:40:26.120Z',
    event_type: 'KNOWLEDGE_RETRIEVED',
    action: 'Retrieved SOP-MRPL-PIP-001 retirement formula chunk',
    actor: 'sovereign_retriever',
    status: 'SUCCESS',
    duration_ms: 15,
    metadata: { source: 'SOP-MRPL-PIP-001.pdf', page: 3, score: 0.942 },
    previous_hash: '3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e',
    event_hash: 'b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2',
  },
  {
    event_id: 'evt-005-sandbox',
    timestamp: '2026-09-15T06:40:26.300Z',
    event_type: 'TOOL_COMPLETED',
    action: 'Subprocess math sandbox executed corrosion_rate_calc.py',
    actor: 'subprocess_sandbox',
    tool_name: 'corrosion_rate_calc',
    status: 'SUCCESS',
    duration_ms: 1500,
    metadata: { metal_loss: 1.90, cr: 0.380, rsl: 5.53 },
    previous_hash: 'b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2',
    event_hash: '4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e',
  },
  {
    event_id: 'evt-006-gate',
    timestamp: '2026-09-15T06:40:27.850Z',
    event_type: 'VALIDATION_PASSED',
    action: '12-point engineering validation gate satisfied: 12/12 checks passed',
    actor: 'structured_output_service',
    status: 'SUCCESS',
    duration_ms: 1,
    metadata: { checks_passed: 12, fail_closed_tripped: false },
    previous_hash: '4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e',
    event_hash: 'e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9',
  },
  {
    event_id: 'evt-007-deliverable',
    timestamp: '2026-09-15T06:40:27.900Z',
    event_type: 'DELIVERABLE_GENERATED',
    action: 'Compiled DOCX memorandum and XLSX calculation sheet',
    actor: 'deliverables_factory',
    status: 'SUCCESS',
    duration_ms: 235,
    metadata: { docx_size: 42816, xlsx_size: 28672 },
    previous_hash: 'e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9',
    event_hash: '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b',
  },
  {
    event_id: 'evt-008-sovereignty',
    timestamp: '2026-09-15T06:40:28.150Z',
    event_type: 'SOVEREIGNTY_CHECK',
    action: 'Host OS socket audit asserted 0 non-loopback egress connections',
    actor: 'runtime_network_monitor',
    status: 'SUCCESS',
    duration_ms: 1,
    metadata: { foreign_sockets: 0, loopback_sockets: 8 },
    previous_hash: '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b',
    event_hash: '2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d',
  },
];

export const MOCK_AUDIT_VERIFICATION: AuditVerificationResult = {
  valid: true,
  events_checked: 1723,
  first_invalid_event: null,
  first_invalid_index: null,
  error_detail: null,
};

export const MOCK_NETWORK_REPORT: NetworkObservationReport = {
  timestamp: new Date().toISOString(),
  observation_method: 'Host Socket Table Inspection (GetExtendedTcpTable)',
  total_connections: 8,
  loopback_connections: 8,
  non_loopback_connections: 0,
  connections: [
    { timestamp: new Date().toISOString(), pid: 1402, process_name: 'python.exe (FastAPI)', local_address: '127.0.0.1:8000', remote_address: '127.0.0.1:5173', status: 'ESTABLISHED', is_loopback: true },
    { timestamp: new Date().toISOString(), pid: 1402, process_name: 'python.exe (FastAPI)', local_address: '127.0.0.1:8000', remote_address: '0.0.0.0:0', status: 'LISTENING', is_loopback: true },
    { timestamp: new Date().toISOString(), pid: 9812, process_name: 'ollama.exe', local_address: '127.0.0.1:11434', remote_address: '0.0.0.0:0', status: 'LISTENING', is_loopback: true },
    { timestamp: new Date().toISOString(), pid: 9812, process_name: 'ollama.exe', local_address: '127.0.0.1:11434', remote_address: '127.0.0.1:54912', status: 'ESTABLISHED', is_loopback: true },
    { timestamp: new Date().toISOString(), pid: 8124, process_name: 'node.exe (Vite)', local_address: '127.0.0.1:5173', remote_address: '0.0.0.0:0', status: 'LISTENING', is_loopback: true },
    { timestamp: new Date().toISOString(), pid: 8124, process_name: 'node.exe (Vite)', local_address: '127.0.0.1:5173', remote_address: '127.0.0.1:8000', status: 'ESTABLISHED', is_loopback: true },
  ],
};

export const MOCK_SOVEREIGNTY_STATUS: SovereigntyStatus = {
  status: 'PASS',
  local_mode_enabled: true,
  external_connections_observed: false,
  foreign_sockets_count: 0,
  provider_checks: [
    { provider_name: 'Ollama Daemon', configured_url: 'http://127.0.0.1:11434', is_local: true, host: '127.0.0.1', port: 11434 },
    { provider_name: 'Chroma Vector DB', configured_url: 'local://embedded/chroma_mrpl', is_local: true, host: 'localhost', port: 0 },
    { provider_name: 'Subprocess Sandbox', configured_url: 'local://isolated_process', is_local: true, host: 'localhost', port: 0 },
  ],
  network_observation: MOCK_NETWORK_REPORT,
  violations: [],
  checked_at: new Date().toISOString(),
  note: 'Zero non-loopback egress sockets detected. Physical & logical air-gap integrity verified.',
};

export const MOCK_TASK_RUN_RESPONSE: AgentRunResponse = {
  task_id: 'task-c101-audit-2026',
  status: 'completed',
  final_state: 'COMPLETED',
  result: {
    task: 'Execute complete corrosion audit on atmospheric column overhead line C-101',
    status: 'SUCCESS',
    summary: 'Corrosion rate 0.380 mm/yr calculated deterministically. Remaining service life 5.53 years. 12/12 validation invariants passed. Deliverables generated.',
    citations_count: 2,
    citations: MOCK_CORROSION_AUDIT_RESULT.citations,
    calculation: MOCK_CORROSION_AUDIT_RESULT.calculation,
    structured_validation: MOCK_VALIDATION_REPORT,
    total_steps_executed: 8,
    total_retries: 0,
  },
  execution_trace: [
    { from_state: 'IDLE', to_state: 'INITIALIZING', timestamp: '2026-09-15T06:40:12.100Z', message: 'Task submitted: C-101 corrosion audit' },
    { from_state: 'INITIALIZING', to_state: 'ANALYZING', timestamp: '2026-09-15T06:40:12.300Z', message: 'Ingested corrosion_inspection_c101.pdf and pid_sample.png' },
    { from_state: 'ANALYZING', to_state: 'ROUTING', timestamp: '2026-09-15T06:40:26.100Z', message: 'RuleRouter classified intent to engineering_math (conf 0.985)' },
    { from_state: 'ROUTING', to_state: 'RETRIEVING', timestamp: '2026-09-15T06:40:26.120Z', message: 'Sovereign RAG retrieved API 570 formula chunks from SOP-MRPL-PIP-001' },
    { from_state: 'RETRIEVING', to_state: 'EXECUTING_TOOL', timestamp: '2026-09-15T06:40:26.300Z', message: 'Invoked corrosion_rate_calc in isolated Python subprocess' },
    { from_state: 'EXECUTING_TOOL', to_state: 'VALIDATING', timestamp: '2026-09-15T06:40:27.850Z', message: 'Evaluating 12 fail-closed validation rules' },
    { from_state: 'VALIDATING', to_state: 'GENERATING_OUTPUT', timestamp: '2026-09-15T06:40:27.900Z', message: 'Compiling publication-ready DOCX and XLSX deliverables' },
    { from_state: 'GENERATING_OUTPUT', to_state: 'COMPLETED', timestamp: '2026-09-15T06:40:28.150Z', message: 'Audit chain signed and verified; network sovereignty verified' },
  ],
  citations: MOCK_CORROSION_AUDIT_RESULT.citations,
  errors: [],
};
