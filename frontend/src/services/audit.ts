/**
 * Audit Ledger & Sovereignty service methods (Phase 11).
 */

import { request } from './api';
import {
  AuditEvent,
  AuditVerificationResult,
  NetworkObservationReport,
  PhysicalIsolationAttestation,
  PhysicalIsolationAttestationChecklist,
  SovereigntyStatus,
} from '../types/audit';

export interface AuditEventListResponse {
  items: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
}

export const auditService = {
  /**
   * Query recorded audit ledger events.
   */
  async getEvents(
    taskId?: string,
    eventType?: string,
    limit = 50,
    offset = 0
  ): Promise<AuditEventListResponse> {
    const params = new URLSearchParams();
    if (taskId) params.set('task_id', taskId);
    if (eventType) params.set('event_type', eventType);
    params.set('limit', String(limit));
    params.set('offset', String(offset));

    return request<AuditEventListResponse>(`/audit/events?${params.toString()}`);
  },

  /**
   * Get single audit event by ID.
   */
  async getEventById(eventId: string): Promise<{ event: AuditEvent }> {
    return request<{ event: AuditEvent }>(`/audit/events/${eventId}`);
  },

  /**
   * Perform cryptographic hash-chain integrity verification on the local ledger.
   */
  async verifyIntegrity(): Promise<{ verification: AuditVerificationResult }> {
    return request<{ verification: AuditVerificationResult }>('/audit/integrity');
  },

  /**
   * Retrieve active runtime network socket observations.
   */
  async observeNetwork(): Promise<{ report: NetworkObservationReport }> {
    return request<{ report: NetworkObservationReport }>('/audit/network');
  },

  /**
   * Evaluate local-only provider configuration and runtime socket sovereignty.
   */
  async checkSovereignty(airGappedMode?: boolean): Promise<{ sovereignty: SovereigntyStatus }> {
    const query = airGappedMode !== undefined ? `?air_gapped_mode=${airGappedMode}` : '';
    return request<{ sovereignty: SovereigntyStatus }>(`/audit/sovereignty${query}`);
  },

  /**
   * Record an explicit, auditable physical air-gap operator verification.
   */
  async attestPhysicalIsolation(
    checklist: PhysicalIsolationAttestationChecklist,
    operatorNotes?: string
  ): Promise<PhysicalIsolationAttestation> {
    return request<PhysicalIsolationAttestation>('/audit/attest-physical-isolation', {
      method: 'POST',
      body: JSON.stringify({ checklist, operator_notes: operatorNotes }),
    });
  },

  /**
   * Fetch the latest physical isolation attestation status from the local ledger.
   */
  async getLatestPhysicalAttestation(): Promise<PhysicalIsolationAttestation> {
    return request<PhysicalIsolationAttestation>('/audit/attest-physical-isolation/latest');
  },
};

