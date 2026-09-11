import React from 'react';
import { useSovereignty } from '../hooks/useSovereignty';
import { ShieldCheck, ShieldAlert, WifiOff, RefreshCw, Cpu, Database } from 'lucide-react';

interface SovereigntyBarProps {
  onNavigateToSovereignty?: () => void;
}

export const SovereigntyBar: React.FC<SovereigntyBarProps> = ({ onNavigateToSovereignty }) => {
  const { health, sovereignty, network, integrity, loading, refresh } = useSovereignty(15000);

  const isLocalOperational = sovereignty?.status === 'PASS' || health?.air_gap_verified;
  const externalConnections = network?.non_loopback_connections ?? 0;
  const isIntegrityValid = integrity?.valid ?? true;
  const eventsCount = integrity?.events_checked ?? 0;

  return (
    <header className="sov-bar" role="banner" aria-label="Sovereignty and Operational Integrity Bar">
      <div className="sov-brand">
        <div className="sov-brand-mark" aria-hidden="true">
          MRPL
        </div>
        <div>
          <div className="sov-title">SOVEREIGN AGENTIC WORKBENCH</div>
          <div className="sov-subtitle">
            Mangalore Refinery and Petrochemicals Limited • Industrial Operations
          </div>
        </div>
      </div>

      <div className="sov-metrics">
        {/* Local Provider Enforcement */}
        <div
          className="sov-metric-item"
          title="Local-only provider enforcement active. No cloud API dependencies configured."
        >
          <div className="sov-metric-label">Execution Environment</div>
          <div className="sov-metric-value">
            {isLocalOperational ? (
              <span className="badge badge-success">
                <ShieldCheck size={12} style={{ marginRight: '4px' }} />
                Local Enforced
              </span>
            ) : (
              <span className="badge badge-warning">
                <ShieldAlert size={12} style={{ marginRight: '4px' }} />
                Provider Notice
              </span>
            )}
          </div>
        </div>

        {/* Runtime Network Observation */}
        <div
          className="sov-metric-item"
          title="Observed OS socket connections. Physical air-gap isolation remains an environment/deployment control."
        >
          <div className="sov-metric-label">Network Sockets</div>
          <div className="sov-metric-value">
            {externalConnections === 0 ? (
              <span className="badge badge-local">
                <WifiOff size={12} style={{ marginRight: '4px' }} />
                0 External Sockets
              </span>
            ) : (
              <span className="badge badge-danger">
                {externalConnections} Non-Loopback
              </span>
            )}
          </div>
        </div>

        {/* Audit Hash-Chain Integrity */}
        <div
          className="sov-metric-item"
          title="SHA-256 tamper-evident hash-chain verification over local audit event records."
        >
          <div className="sov-metric-label">Audit Ledger</div>
          <div className="sov-metric-value">
            {isIntegrityValid ? (
              <span className="badge badge-success">
                <Database size={12} style={{ marginRight: '4px' }} />
                Chain Verified ({eventsCount})
              </span>
            ) : (
              <span className="badge badge-danger">
                <ShieldAlert size={12} style={{ marginRight: '4px' }} />
                Integrity Alert
              </span>
            )}
          </div>
        </div>

        {/* Active Engine */}
        <div className="sov-metric-item">
          <div className="sov-metric-label">Inference Engine</div>
          <div className="sov-metric-value">
            <span className="badge badge-neutral">
              <Cpu size={12} style={{ marginRight: '4px' }} />
              Ollama (On-Prem)
            </span>
          </div>
        </div>

        {/* Refresh button */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={refresh}
          title="Re-query sovereignty, network, and integrity status"
          aria-label="Refresh sovereignty status"
          disabled={loading}
          style={{ padding: '4px 8px', marginLeft: '4px' }}
        >
          <RefreshCw size={13} className={loading ? 'icon-spin' : ''} />
        </button>
      </div>
    </header>
  );
};
