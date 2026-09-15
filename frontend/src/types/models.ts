/**
 * SIH26117 — Model Manager & Hardware Tier Contracts
 * Source of Truth: SIH26117_MASTER_PROJECT_REPORT.md §3, §5.2.B
 */

export type ModelRole = 'router' | 'reasoning' | 'coder' | 'vision' | 'embedding';

export interface ModelTierItem {
  role: ModelRole;
  provider: 'ollama' | 'local';
  model_tag: string;
  context_window?: number;
  device?: string;
  vram_allocated_gb?: number;
  status?: 'loaded' | 'standby' | 'swapping';
}

export interface TierConfigResponse {
  tier_name: string;
  description: string;
  vram_budget_gb: number;
  vram_used_gb?: number;
  max_concurrent_models: number;
  swap_keep_alive: string;
  models: ModelTierItem[];
}

export interface ModelInfoSchema {
  tag: string;
  provider: string;
  size_on_disk_gb?: number;
  size_human?: string;
  quantization?: string;
  parameter_count?: string;
  context_window?: number;
  capabilities: {
    vision?: boolean;
    tools?: boolean;
    thinking?: boolean;
    embedding?: boolean;
  };
}

export interface ModelListResponse {
  models: ModelInfoSchema[];
  total_count: number;
  active_tier: string;
}
