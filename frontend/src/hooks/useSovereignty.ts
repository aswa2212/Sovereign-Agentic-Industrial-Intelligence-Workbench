import { useState, useEffect, useCallback } from 'react';
import { auditService } from '../services/audit';
import { systemService } from '../services/system';
import { SovereigntyStatus, NetworkObservationReport, AuditVerificationResult } from '../types/audit';
import { HealthResponse } from '../types/api';

export interface SovereigntyState {
  health: HealthResponse | null;
  sovereignty: SovereigntyStatus | null;
  network: NetworkObservationReport | null;
  integrity: AuditVerificationResult | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

export function useSovereignty(pollIntervalMs = 15000) {
  const [state, setState] = useState<SovereigntyState>({
    health: null,
    sovereignty: null,
    network: null,
    integrity: null,
    loading: true,
    error: null,
    lastUpdated: null,
  });

  const refresh = useCallback(async () => {
    try {
      const [healthRes, sovRes, netRes, intRes] = await Promise.allSettled([
        systemService.getHealth(),
        auditService.checkSovereignty(),
        auditService.observeNetwork(),
        auditService.verifyIntegrity(),
      ]);

      setState((prev) => ({
        ...prev,
        health: healthRes.status === 'fulfilled' ? healthRes.value : prev.health,
        sovereignty: sovRes.status === 'fulfilled' ? sovRes.value.sovereignty : prev.sovereignty,
        network: netRes.status === 'fulfilled' ? netRes.value.report : prev.network,
        integrity: intRes.status === 'fulfilled' ? intRes.value.verification : prev.integrity,
        loading: false,
        error: null,
        lastUpdated: new Date(),
      }));
    } catch (err: any) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err.message || 'Failed to update sovereignty status',
      }));
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, pollIntervalMs);
    return () => clearInterval(timer);
  }, [refresh, pollIntervalMs]);

  return { ...state, refresh };
}
