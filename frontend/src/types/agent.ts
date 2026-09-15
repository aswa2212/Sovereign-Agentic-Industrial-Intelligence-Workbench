/**
 * SIH26117 — Agent & Workflow Type Contracts
 * Source of Truth: SIH26117_MASTER_PROJECT_REPORT.md §6.2.A
 */

export type AgentState =
  | 'IDLE'
  | 'INITIALIZING'
  | 'ANALYZING'
  | 'ROUTING'
  | 'RETRIEVING'
  | 'REASONING'
  | 'EXECUTING_TOOL'
  | 'OBSERVING'
  | 'EVALUATING'
  | 'VALIDATING'
  | 'GENERATING_OUTPUT'
  | 'COMPLETED'
  | 'FAILED'
  | 'PAUSED'
  | 'RECEIVE'
  | 'UNDERSTAND'
  | 'PLAN'
  | 'EXECUTE'
  | 'OBSERVE'
  | 'REFLECT'
  | 'VALIDATE'
  | 'FINALIZE'
  | 'DELIVER';

export interface AgentStepTrace {
  step_number: number;
  state: AgentState;
  thought: string;
  action?: string;
  action_input?: Record<string, any>;
  observation?: string;
  timestamp: string;
  duration_ms: number;
}

export interface StateTransition {
  from_state: AgentState;
  to_state: AgentState;
  timestamp: string;
  message?: string;
  metadata?: Record<string, any>;
}

export interface WallThicknessMeasurement {
  value_mm: number;
  measurement_date: string;
  location_tag: string;
}

export interface CorrosionCalculation {
  metal_loss_mm: number;
  elapsed_time_years: number;
  corrosion_rate_mm_per_year: number;
  remaining_life_years: number;
  minimum_thickness_mm: number;
  formula_used: string;
  inspection_interval_years?: number;
  remaining_margin_mm?: number;
}

export interface CitationSource {
  source_document: string;
  page_number: number;
  chunk_id?: string;
  text: string;
  similarity_score?: number;
}

export interface ValidationCheckItem {
  id: string;
  rule_number: number;
  name: string;
  description: string;
  status: 'PASSED' | 'FAILED' | 'SKIPPED';
  detail: string;
}

export interface StructuredValidationReport {
  valid: boolean;
  status: 'PASS' | 'FAIL';
  checks_total: number;
  checks_passed_count: number;
  checks_failed_count: number;
  checks: ValidationCheckItem[];
  warnings?: string[];
}

export interface CorrosionAuditResult {
  task_id: string;
  equipment_id: string;
  inspection_subject: string;
  current_measurement: WallThicknessMeasurement;
  initial_measurement: WallThicknessMeasurement;
  minimum_required_thickness_mm: number;
  calculation: CorrosionCalculation;
  findings: Array<{
    finding_id: string;
    description: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    supporting_citation?: any;
  }>;
  conclusion: string;
  recommendation: 'CONTINUE_SERVICE' | 'REPAIR_REQUIRED' | 'IMMEDIATE_SHUTDOWN';
  citations: CitationSource[];
  confidence: number;
}

export interface AgentRunRequest {
  task: string;
  max_steps?: number;
  mode?: 'deterministic' | 'live';
  component_id?: string;
}

export interface AgentRunResponse {
  task_id: string;
  status: 'completed' | 'failed';
  final_state: AgentState;
  result?: {
    task: string;
    status: string;
    summary: string;
    citations_count: number;
    citations: CitationSource[];
    calculation?: CorrosionCalculation;
    structured_validation?: StructuredValidationReport;
    total_steps_executed?: number;
    total_retries?: number;
  };
  execution_trace: StateTransition[];
  citations: CitationSource[];
  errors: string[];
}

export interface AgentTaskStatusResponse {
  task_id: string;
  current_state: AgentState;
  step_count: number;
  started_at: string;
  updated_at: string;
  execution_trace: StateTransition[];
  errors: string[];
}
