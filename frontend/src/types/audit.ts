/**
 * SIH26117 — Cryptographic Audit & Sovereignty Types
 * Source of Truth: SIH26117_MASTER_PROJECT_REPORT.md §6.2.C
 */

export type AuditEventType =
  | 'TASK_CREATED'
  | 'TASK_STARTED'
  | 'STATE_CHANGED'
  | 'PLAN_CREATED'
  | 'MODEL_ROUTED'
  | 'MODEL_INVOKED'
  | 'KNOWLEDGE_RETRIEVED'
  | 'VISION_ANALYSIS'
  | 'TOOL_STARTED'
  | 'TOOL_COMPLETED'
  | 'TOOL_INVOKED'
  | 'TOOL_RESULT'
  | 'DOCUMENT_INGESTED'
  | 'VALIDATION_STARTED'
  | 'VALIDATION_COMPLETED'
  | 'VALIDATION_PASSED'
  | 'VALIDATION_FAILED'
  | 'DELIVERABLE_CREATED'
  | 'DELIVERABLE_GENERATED'
  | 'TASK_COMPLETED'
  | 'TASK_FAILED'
  | 'NETWORK_CHECK'
  | 'SOVEREIGNTY_CHECK'
  | 'SOVEREIGNTY_VIOLATION'
  | 'LEDGER_VERIFIED'
  | 'PHYSICAL_ISOLATION_ATTESTED';

export interface AuditEvent {
  event_id: string;
  timestamp: string;
  task_id?: string | null;
  event_type: AuditEventType;
  action: string;
  actor?: string;
  agent_state?: string | null;
  model_role?: string | null;
  capability?: string | null;
  tool_name?: string | null;
  source?: string | null;
  status: 'SUCCESS' | 'FAILED' | 'WARNING' | string;
  duration_ms?: number | null;
  message?: string | null;
  metadata: Record<string, any>;
  previous_hash: string;
  event_hash: string;
}

export interface AuditVerificationResult {
  valid: boolean;
  events_checked: number;
  first_invalid_event?: string | null;
  first_invalid_index?: number | null;
  error_detail?: string | null;
}

export interface NetworkConnectionRecord {
  timestamp: string;
  pid?: number | null;
  process_name?: string | null;
  local_address: string;
  remote_address?: string | null;
  status: string;
  is_loopback: boolean;
}

export interface NetworkObservationReport {
  timestamp: string;
  observation_method: string;
  total_connections: number;
  loopback_connections: number;
  non_loopback_connections: number;
  connections: NetworkConnectionRecord[];
  warning?: string | null;
}

export interface ProviderSovereigntyCheck {
  provider_name: string;
  configured_url?: string | null;
  is_local: boolean;
  host?: string | null;
  port?: number | null;
  error?: string | null;
}

export interface SovereigntyStatus {
  status: 'PASS' | 'FAIL';
  local_mode_enabled: boolean;
  provider_checks: ProviderSovereigntyCheck[];
  network_observation?: NetworkObservationReport | null;
  external_connections_observed: boolean;
  foreign_sockets_count?: number;
  violations: string[];
  checked_at: string;
  note?: string;
}

export interface PhysicalIsolationAttestationChecklist {
  ethernet_disconnected: boolean;
  wifi_disabled: boolean;
  adapter_disabled: boolean;
  external_route_checked: boolean;
  radios_checked: boolean;
  operator_confirmed: boolean;
  operator_notes?: string;
}

export interface PhysicalIsolationAttestation {
  status: 'OPERATOR_VERIFIED' | 'NOT_ATTESTED';
  event_id: string;
  timestamp: string;
  event_hash: string;
  hostname: string;
  operator_confirmed: boolean;
  evidence: Record<string, any>;
  network_observation: Record<string, any>;
  sovereignty_status: string;
}

