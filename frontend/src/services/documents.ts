/**
 * Document Ingestion service methods (Phase 4).
 */

import { request } from './api';
import { DocumentIngestionResult } from '../types/documents';

export const documentService = {
  /**
   * Upload an industrial document (PDF, DOCX, XLSX, PNG, JPG) to raw storage
   * and extract normalized structure.
   */
  async uploadDocument(file: File): Promise<DocumentIngestionResult> {
    const formData = new FormData();
    formData.append('file', file, file.name);

    return request<DocumentIngestionResult>('/files/upload', {
      method: 'POST',
      body: formData,
    }, 45000); // 45s timeout for document processing
  },

  /**
   * Retrieve normalized document status and metadata by SHA-256 identifier.
   */
  async getDocumentStatus(sha256: string): Promise<Record<string, any>> {
    return request<Record<string, any>>(`/files/${sha256}/status`, {
      method: 'GET',
    });
  },
};
