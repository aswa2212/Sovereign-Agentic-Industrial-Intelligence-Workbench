import React, { useEffect, useState } from 'react';
import { systemService } from '../services/system';
import { TierConfigResponse, BackendHealthResponse, ModelListResponse } from '../types/api';
import { Cpu, Server, Activity, Database, RefreshCw, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

export const ModelsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tierConfig, setTierConfig] = useState<TierConfigResponse | null>(null);
  const [health, setHealth] = useState<BackendHealthResponse | null>(null);
  const [modelList, setModelList] = useState<ModelListResponse | null>(null);

  const fetchModelData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [tierRes, healthRes, listRes] = await Promise.allSettled([
        systemService.getModelTier(),
        systemService.getModelHealth(),
        systemService.getModelList(),
      ]);

      if (tierRes.status === 'fulfilled') setTierConfig(tierRes.value);
      if (healthRes.status === 'fulfilled') setHealth(healthRes.value);
      if (listRes.status === 'fulfilled') setModelList(listRes.value);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve runtime model telemetry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModelData();
  }, []);

  const isBackendHealthy = health?.healthy ?? false;
  const discoveredTags = new Set(modelList?.models?.map((m) => m.tag.toLowerCase()) || []);

  const getRoleIcon = (role: string) => {
    switch (role.toLowerCase()) {
      case 'reasoning':
        return <Activity size={18} style={{ color: 'var(--accent-primary)' }} />;
      case 'vision':
        return <Cpu size={18} style={{ color: 'var(--status-warning-dot)' }} />;
      case 'fast':
        return <Server size={18} style={{ color: 'var(--accent-secondary)' }} />;
      default:
        return <Database size={18} style={{ color: 'var(--text-secondary)' }} />;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <Cpu size={18} style={{ color: 'var(--accent-primary)' }} />
            <div>
              <div className="card-title">Local Model Registry & Tier Architecture</div>
              <div className="card-subtitle">
                Hardware Tier Configuration • Live Runtime Health • On-Prem Local Inference
              </div>
            </div>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={fetchModelData}
            disabled={loading}
            title="Query model manager and liveness probe"
          >
            <RefreshCw size={13} className={loading ? 'icon-spin' : ''} />
            Refresh Telemetry
          </button>
        </div>

        {/* Live Runtime Health Banner */}
        <div
          style={{
            padding: '0.75rem 1rem',
            background: isBackendHealthy ? 'var(--status-success-bg)' : 'var(--status-warning-bg)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.8125rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {isBackendHealthy ? (
              <CheckCircle2 size={16} style={{ color: 'var(--status-success-dot)' }} />
            ) : (
              <AlertTriangle size={16} style={{ color: 'var(--status-warning-dot)' }} />
            )}
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              LOCAL INFERENCE RUNTIME (OLLAMA):
            </span>
            <span style={{ color: isBackendHealthy ? 'var(--status-success-text)' : 'var(--status-warning-text)' }}>
              {health?.message || (isBackendHealthy ? 'Backend responsive on loopback.' : 'Backend unreachable or offline.')}
            </span>
          </div>

          <span className={`badge ${isBackendHealthy ? 'badge-success' : 'badge-warning'}`}>
            {isBackendHealthy ? 'ONLINE (LOOPBACK)' : 'STANDBY / OFFLINE'}
          </span>
        </div>

        {/* Hardware Tier Specifications */}
        <div
          style={{
            padding: '0.75rem 1rem',
            background: 'var(--bg-surface-muted)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1rem',
            fontSize: '0.8125rem',
          }}
        >
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>ACTIVE HARDWARE TIER</div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {tierConfig?.tier_name || 'Development (RTX 4060)'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>VRAM ALLOCATION BUDGET</div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--accent-primary)' }}>
              {tierConfig?.vram_budget_gb ? `${tierConfig.vram_budget_gb} GB VRAM` : '7.5 GB VRAM'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>CONCURRENCY POLICY</div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {tierConfig?.max_concurrent_models ?? 1} Model Resident (Serial Swap)
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>DISCOVERED LOCAL MODELS</div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {modelList?.total ?? 0} Models
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: '0.75rem 1rem',
            background: 'var(--status-error-bg)',
            border: '1px solid var(--status-error-border)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.8125rem',
            color: 'var(--status-error-text)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <ShieldAlert size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Configured Role Mappings (Static Configuration vs Runtime Presence) */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">Configured Tier Role Mappings</div>
          <div className="card-subtitle">
            Declared capability assignments mapped to on-premise local model tags
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="tech-table">
            <thead>
              <tr>
                <th>ROLE</th>
                <th>CONFIGURED MODEL TAG</th>
                <th>PROVIDER</th>
                <th>CONTEXT WINDOW</th>
                <th>QUANTIZATION</th>
                <th>TARGET DEVICE</th>
                <th>RUNTIME STATUS</th>
              </tr>
            </thead>
            <tbody>
              {tierConfig?.models && tierConfig.models.length > 0 ? (
                tierConfig.models.map((entry) => {
                  const isDiscovered = discoveredTags.has(entry.model_tag.toLowerCase());
                  const isAvailable = isBackendHealthy && isDiscovered;

                  return (
                    <tr key={entry.role}>
                      <td style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {getRoleIcon(entry.role)}
                        <span>{entry.role.toUpperCase()}</span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                        {entry.model_tag}
                      </td>
                      <td>
                        <span className="code-badge">{entry.provider}</span>
                      </td>
                      <td style={{ fontSize: '0.75rem' }}>
                        {entry.context_window.toLocaleString()} tokens
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                        {entry.quantization || 'Q4_K_M'}
                      </td>
                      <td style={{ fontSize: '0.75rem' }}>
                        {entry.device || 'cuda:0'}
                      </td>
                      <td>
                        {isAvailable ? (
                          <span className="badge badge-success">READY (LOCAL)</span>
                        ) : isBackendHealthy ? (
                          <span className="badge badge-neutral" title="Model tag not currently in local cache">
                            STANDBY (NOT RESIDENT)
                          </span>
                        ) : (
                          <span className="badge badge-warning" title="Inference backend offline">
                            BACKEND OFFLINE
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                    {loading ? 'Querying hardware tier configuration...' : 'No role mappings returned by backend.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Discovered Models Table from Local Ollama Instance */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">Locally Discovered Models Cache</div>
          <span className="code-badge">{modelList?.total ?? 0} Models Found</span>
        </div>

        <div style={{ overflowX: 'auto', maxHeight: '280px' }}>
          <table className="tech-table">
            <thead>
              <tr>
                <th>MODEL ID</th>
                <th>TAG</th>
                <th>PROVIDER</th>
                <th>QUANTIZATION</th>
                <th>MAX CONTEXT</th>
                <th>VRAM RESIDENCY</th>
              </tr>
            </thead>
            <tbody>
              {modelList?.models && modelList.models.length > 0 ? (
                modelList.models.map((m) => (
                  <tr key={m.model_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>{m.model_id}</td>
                    <td style={{ fontWeight: 600 }}>{m.tag}</td>
                    <td><span className="code-badge">{m.provider}</span></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>{m.quantization || '—'}</td>
                    <td style={{ fontSize: '0.75rem' }}>{m.capabilities?.max_context_length?.toLocaleString() || '4,096'}</td>
                    <td>
                      {m.is_resident_in_vram ? (
                        <span className="badge badge-success">ACTIVE IN VRAM</span>
                      ) : (
                        <span className="badge badge-neutral">UNLOADED</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                    {isBackendHealthy
                      ? 'No cached models discovered in local provider.'
                      : 'Cannot inspect model cache while inference backend is offline.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
