/**
 * Deterministic Office Deliverables service methods (Phase 10).
 */

import { request } from './api';
import { DeliverableFormat, DeliverableGenerateResponse, GeneratedArtifact } from '../types/deliverables';

export const deliverablesService = {
  /**
   * List all generated deliverables.
   */
  async listDeliverables(): Promise<GeneratedArtifact[]> {
    return request<GeneratedArtifact[]>('/deliverables');
  },

  /**
   * Request compilation of verified engineering results into Office deliverables.
   */
  async generateDeliverables(
    data: Record<string, any>,
    formats: DeliverableFormat[] = ['docx', 'xlsx', 'pptx'],
    taskId?: string,
    metadata?: Record<string, any>
  ): Promise<DeliverableGenerateResponse> {
    return request<DeliverableGenerateResponse>('/deliverables/generate', {
      method: 'POST',
      body: JSON.stringify({
        data,
        formats,
        task_id: taskId,
        metadata,
      }),
    });
  },

  /**
   * Construct absolute API download URL for a generated artifact.
   */
  getDownloadUrl(format: DeliverableFormat, filename: string): string {
    return `/api/v1/deliverables/download/${format}/${encodeURIComponent(filename)}`;
  },
};
