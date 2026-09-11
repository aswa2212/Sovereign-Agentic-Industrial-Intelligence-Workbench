import React, { useEffect, useState } from 'react';
import { auditService } from '../services/audit';
import { systemService } from '../services/system';
import {
  SovereigntyStatus,
  NetworkObservationReport,
  AuditVerificationResult,
} from '../types/audit';
import { HealthResponse } from '../types/api';
import {
  ShieldCheck,
  ShieldAlert,
  WifiOff,
  Database,
  RefreshCw,
  Server,
  Activity,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

export const SovereigntyPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sovereignty, setSovereignty] = useState<SovereigntyStatus | null>(null);
  const [network, setNetwork] = useState<NetworkObservationReport | null>(null);
  const [integrity, setIntegrity] = useState<AuditVerificationResult | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sovRes, netRes, intRes, healthRes] = await Promise.allSettled([
        auditService.checkSovereignty(),
        auditService.observeNetwork(),
        auditService.verifyIntegrity(),
        systemService.getHealth(),
      ]);

      if (sovRes.status === 'fulfilled') setSovereignty(sovRes.value.sovereignty);
      if (netRes.status === 'fulfilled') setNetwork(netRes.value.report);
      if (intRes.status === 'fulfilled') setIntegrity(intRes.value.verification);
      if (healthRes.status === 'fulfilled') setHealth(healthRes.value);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve sovereignty telemetry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const isPass = sovereignty?.status === 'PASS';
  const nonLoopbackCount = network?.non_loopback_connections ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header Banner */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <ShieldCheck size={18} style={{ color: 'var(--accent-primary)' }} />
            <div>
              <div className="card-title">Sovereignty & Runtime Network Observation</div>
              <div className="card-subtitle">
                Local-Only Provider Enforcement • Runtime Socket Telemetry • Audit Verification
              </div>
            </div>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={fetchData}
            disabled={loading}
            title="Re-run sovereignty and network audits"
          >
            <RefreshCw size={13} className={loading ? 'icon-spin' : ''} />
            Re-Audit
          </button>
        </div>

        {/* Environmental Notice */}
        <div
          style={{
            padding: '0.75rem 1rem',
            background: 'var(--bg-surface-muted)',
            fontSize: '0.8125rem',
            color: 'var(--text-secondary)',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
            CONTROL PRINCIPLE:
          </span>{' '}
          This workbench enforces strict local-only provider configuration and runtime socket observation.
          Physical air-gap isolation remains an environment and deployment control.
        </div>

        {/* Status Scoreboard */}
        <div
          style={{
            padding: '1rem',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '1rem',
          }}
        >
          {/* Check 1: Provider Enforcement */}
          <div
            style={{
              padding: '0.875rem',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-surface)',
            }}
          >
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              PROVIDER ENFORCEMENT
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.375rem' }}>
              {isPass ? (
                <span className="badge badge-success">
                  <CheckCircle2 size={13} style={{ marginRight: '4px' }} />
                  PASS (Local Only)
                </span>
              ) : (
                <span className="badge badge-danger">
                  <AlertTriangle size={13} style={{ marginRight: '4px' }} />
                  NON-LOCAL DETECTED
                </span>
              )}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
              All model endpoints restricted to loopback (127.0.0.1 / localhost).
            </div>
          </div>

          {/* Check 2: Outbound Network Sockets */}
          <div
            style={{
              padding: '0.875rem',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-surface)',
            }}
          >
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              NETWORK OBSERVATION
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.375rem' }}>
              {nonLoopbackCount === 0 ? (
                <span className="badge badge-local">
                  <WifiOff size={13} style={{ marginRight: '4px' }} />
                  0 External Sockets
                </span>
              ) : (
                <span className="badge badge-danger">
                  <AlertTriangle size={13} style={{ marginRight: '4px' }} />
                  {nonLoopbackCount} External Observed
                </span>
              )}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
              {network?.loopback_connections ?? 0} active internal loopback connections observed.
            </div>
          </div>

          {/* Check 3: Cryptographic Ledger */}
          <div
            style={{
              padding: '0.875rem',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-surface)',
            }}
          >
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              AUDIT CHAIN INTEGRITY
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.375rem' }}>
              {integrity?.valid ? (
                <span className="badge badge-success">
                  <Database size={13} style={{ marginRight: '4px' }} />
                  INTEGRITY VERIFIED
                </span>
              ) : (
                <span className="badge badge-danger">
                  <AlertTriangle size={13} style={{ marginRight: '4px' }} />
                  CHAIN BROKEN
                </span>
              )}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
              {integrity?.events_checked ?? 0} sequential audit events cryptographically validated.
            </div>
          </div>
        </div>
      </div>

      {/* Provider Audit Inspection Table */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <Server size={16} style={{ color: 'var(--accent-primary)' }} />
            <div>
              <div className="card-title">Configured Provider Sovereignty Audit</div>
              <div className="card-subtitle">
                Inspection of LLM/Vision Runtime Endpoints and Socket Targets
              </div>
            </div>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="tech-table">
            <thead>
              <tr>
                <th>PROVIDER NAME</th>
                <th>CONFIGURED URL</th>
                <th>TARGET HOST</th>
                <th>TARGET PORT</th>
                <th>LOCAL ENFORCEMENT</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {sovereignty?.provider_checks?.map((chk) => (
                <tr key={chk.provider_name}>
                  <td style={{ fontWeight: 600 }}>{chk.provider_name}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                    {chk.configured_url || 'Default internal binding'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                    {chk.host || '127.0.0.1'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                    {chk.port || '11434'}
                  </td>
                  <td>
                    {chk.is_local ? (
                      <span className="badge badge-success">Local Loopback</span>
                    ) : (
                      <span className="badge badge-danger">Remote Target</span>
                    )}
                  </td>
                  <td>
                    <span className={`badge ${chk.is_local ? 'badge-success' : 'badge-danger'}`}>
                      {chk.is_local ? 'PASS' : 'VIOLATION'}
                    </span>
                  </td>
                </tr>
              )) || (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                    No provider telemetry records available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Runtime Network Sockets Telemetry Table */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <Activity size={16} style={{ color: 'var(--accent-primary)' }} />
            <div>
              <div className="card-title">Live Process Network Sockets Telemetry</div>
              <div className="card-subtitle">
                Observed Socket Bindings for Active Application Process (PID: {network?.connections?.[0]?.pid || 'Current'})
              </div>
            </div>
          </div>

          <span className="badge badge-neutral">
            {network?.connections?.length ?? 0} Recorded Socket{network?.connections?.length === 1 ? '' : 's'}
          </span>
        </div>

        <div style={{ overflowX: 'auto', maxHeight: '320px' }}>
          <table className="tech-table">
            <thead>
              <tr>
                <th>LOCAL ADDRESS</th>
                <th>REMOTE ADDRESS</th>
                <th>CLASSIFICATION</th>
                <th>CONNECTION STATE</th>
                <th>PROCESS PID</th>
              </tr>
            </thead>
            <tbody>
              {network?.connections && network.connections.length > 0 ? (
                network.connections.map((c, i) => (
                  <tr key={i}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                      {c.local_address}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                      {c.remote_address || '—'}
                    </td>
                    <td>
                      {c.is_loopback ? (
                        <span className="badge badge-local">Loopback (Safe)</span>
                      ) : (
                        <span className="badge badge-danger">Non-Loopback</span>
                      )}
                    </td>
                    <td>
                      <span className="code-badge">{c.status || 'ESTABLISHED'}</span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                      {c.pid || '—'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                    No active sockets captured during observation window.
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
