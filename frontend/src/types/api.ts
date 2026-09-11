/**
 * Shared API and System types for SIH26117 Workbench.
 */

export interface HealthResponse {
  status: string;
  air_gap_verified: boolean;
  timestamp?: string;
}

export interface SystemStatusResponse {
  app_name: string;
  app_version: string;
  environment: string;
  air_gapped_mode: boolean;
  uptime_seconds?: number;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

export interface RouteResponse {
  task_type: string;
  capability: string;
  model_role: string;
  confidence: number;
  reason: string;
  routing_method: string;
}

export interface BackendHealthResponse {
  healthy: boolean;
  provider: string;
  message: string;
}

export interface TierModelEntry {
  role: string;
  provider: string;
  model_tag: string;
  context_window: number;
  quantization?: string | null;
  device?: string | null;
}

export interface TierConfigResponse {
  tier_name: string;
  description: string;
  vram_budget_gb: number;
  max_concurrent_models: number;
  models: TierModelEntry[];
}

export interface ModelInfoSchema {
  model_id: string;
  provider: string;
  tag: string;
  quantization?: string | null;
  capabilities: {
    supports_vision: boolean;
    supports_tools: boolean;
    supports_thinking: boolean;
    max_context_length: number;
  };
  is_resident_in_vram: boolean;
}

export interface ModelListResponse {
  models: ModelInfoSchema[];
  total: number;
  backend_healthy: boolean;
  active_tier: string;
}

export interface RAGStatusResponse {
  status: string;
  index_id: string;
  backend: string;
  total_chunks: number;
  indexed_documents_count: number;
  dimension: number;
  embedding_provider: string;
  storage_path: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  source_sha256: string;
  source_document: string;
  page_number?: number | null;
  section_index?: number | null;
  section_header?: string | null;
  text: string;
  similarity_score: number;
  content_sha256: string;
  token_count: number;
  metadata?: Record<string, any>;
}

export interface RAGQueryResponse {
  query: string;
  status: string;
  retrieved_count: number;
  results: RetrievedChunk[];
  citations: any[];
  message?: string | null;
}
