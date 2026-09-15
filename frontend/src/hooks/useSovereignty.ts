import { useState, useEffect, useCallback } from 'react';
import { auditService } from '../services/audit';
import { systemService } from '../services/system';
import { SovereigntyStatus, NetworkObservationReport, AuditVerificationResult, PhysicalIsolationAttestation } from '../types/audit';
import { HealthResponse, TierConfigResponse } from '../types/api';

export interface SovereigntyState {
  health: HealthResponse | null;
  sovereignty: SovereigntyStatus | null;
  network: NetworkObservationReport | null;
  integrity: AuditVerificationResult | null;
  tierConfig: TierConfigResponse | null;
  physicalAttestation: PhysicalIsolationAttestation | null;
  activeModel: string;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  isPolling: boolean;
}

export function useSovereignty(pollIntervalMs = 10000) {
  const [state, setState] = useState<SovereigntyState>({
    health: null,
    sovereignty: null,
    network: null,
    integrity: null,
    tierConfig: null,
    physicalAttestation: null,
    activeModel: 'Locating Model...',
    loading: true,
    error: null,
    lastUpdated: null,
    isPolling: true,
  });

  const refresh = useCallback(async () => {
    try {
      const [healthRes, sovRes, netRes, intRes, tierRes, attestRes] = await Promise.allSettled([
        systemService.getHealth(),
        auditService.checkSovereignty(),
        auditService.observeNetwork(),
        auditService.verifyIntegrity(),
        systemService.getModelTier(),
        auditService.getLatestPhysicalAttestation(),
      ]);

      let activeModelTag = 'Local Model';
      if (tierRes.status === 'fulfilled' && tierRes.value?.models) {
        // Priority for active model display: reasoning or vision or first active model tag
        const primary = tierRes.value.models.find(m => m.role === 'vision' || m.role === 'reasoning') || tierRes.value.models[0];
        if (primary) {
          activeModelTag = primary.model_tag;
        }
      }

      setState((prev) => ({
        ...prev,
        health: healthRes.status === 'fulfilled' ? healthRes.value : prev.health,
        sovereignty: sovRes.status === 'fulfilled' ? sovRes.value.sovereignty : prev.sovereignty,
        network: netRes.status === 'fulfilled' ? netRes.value.report : prev.network,
        integrity: intRes.status === 'fulfilled' ? intRes.value.verification : prev.integrity,
        tierConfig: tierRes.status === 'fulfilled' ? tierRes.value : prev.tierConfig,
        physicalAttestation: attestRes.status === 'fulfilled' ? attestRes.value : prev.physicalAttestation,
        activeModel: activeModelTag,
        loading: false,
        error: null,
        lastUpdated: new Date(),
        isPolling: true,
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
