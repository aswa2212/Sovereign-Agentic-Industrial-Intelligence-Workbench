/**
 * Deterministic Deliverables types.
 */

export type DeliverableFormat = 'docx' | 'xlsx' | 'pptx';

export interface GeneratedArtifact {
  artifact_id: string;
  format: DeliverableFormat;
  filename: string;
  file_size_bytes: number;
  storage_path: string;
  sha256_checksum?: string;
  created_at: string;
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
