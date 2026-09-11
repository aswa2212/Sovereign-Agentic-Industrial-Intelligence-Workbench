/**
 * Agent State Machine and Lifecycle types.
 */

export type AgentState =
  | 'IDLE'
  | 'RECEIVE'
  | 'UNDERSTAND'
  | 'PLAN'
  | 'EXECUTE'
  | 'OBSERVE'
  | 'REFLECT'
  | 'VALIDATE'
  | 'FINALIZE'
  | 'DELIVER'
  | 'FAILED';

export interface StateTransition {
  from_state: AgentState;
  to_state: AgentState;
  timestamp: string;
  message?: string;
  metadata?: Record<string, any>;
}

export interface CitationSource {
  source_document: string;
  page_number: number;
  chunk_id: string;
  text: string;
  similarity_score?: number;
}

export interface AgentRunRequest {
  task: string;
  max_steps?: number;
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
    calculation?: Record<string, any>;
    structured_validation?: {
      valid: boolean;
      status: string;
      checks_passed: string[];
      checks_failed: string[];
      warnings?: string[];
    };
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
