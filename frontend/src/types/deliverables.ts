/**
 * SIH26117 — Deterministic Deliverables Types
 * Source of Truth: SIH26117_MASTER_PROJECT_REPORT.md §6.2.B
 */

export type DeliverableFormat = 'docx' | 'xlsx' | 'pptx';

export interface GeneratedArtifact {
  artifact_id: string;
  task_id?: string;
  format: DeliverableFormat;
  filename: string;
  file_size_bytes: number;
  relative_path?: string;
  storage_path?: string;
  sha256_hash: string;
  sha256_checksum?: string;
  created_at: string;
  download_url?: string;
  validation_status?: string;
}

export interface DeliverableGenerateResponse {
  success: boolean;
  task_id: string;
  equipment_id: string;
  inspection_subject: string;
  artifacts: GeneratedArtifact[];
  formats_requested: DeliverableFormat[];
  summary: string;
  validation_status: string;
}
