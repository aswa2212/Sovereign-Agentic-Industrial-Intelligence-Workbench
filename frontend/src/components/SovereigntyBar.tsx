import React from 'react';
import { ShieldCheck, ShieldAlert, RefreshCw, Sliders, Terminal, Cpu } from 'lucide-react';
import { useSovereignty } from '../hooks/useSovereignty';

interface SovereigntyBarProps {
  onOpenCommandPalette: () => void;
  onOpenSettings?: () => void;
  onNavigateToSovereignty?: () => void;
  onOpenAttestation?: () => void;
}

export const SovereigntyBar: React.FC<SovereigntyBarProps> = ({
  onOpenCommandPalette,
  onOpenSettings,
  onNavigateToSovereignty,
  onOpenAttestation,
}) => {
  const { sovereignty, physicalAttestation, activeModel, loading, refresh, isPolling } = useSovereignty(10000);

  const isSoftwareSovereign = sovereignty?.status === 'PASS' && !sovereignty.external_connections_observed;
  const foreignSockets = sovereignty?.foreign_sockets_count ?? 0;
  const isPhysicallyAttested = physicalAttestation?.status === 'OPERATOR_VERIFIED';

  return (
    <header className="sovereign-status-strip" role="banner">
      {/* Brand & Organization */}
      <div className="status-strip-left">
        <div className="status-brand-pill">
          <span className="status-brand-sponsor">MRPL</span>
          <span className="status-brand-divider">/</span>
          <span className="status-brand-id">SIH26117</span>
        </div>
        <div className="status-strip-title">
          <span className="title-bold">Sovereign Agentic AI Workbench</span>
          <span className="title-subtitle">Refinery Control Deck</span>
        </div>
      </div>

      {/* Center / Command Palette Hint */}
      <div className="status-strip-center">
        <button
          type="button"
          className="status-cmd-shortcut"
          onClick={onOpenCommandPalette}
          title="Open Command Palette (Cmd/Ctrl + K)"
          aria-label="Open Command Palette"
        >
          <Terminal size={13} className="shortcut-icon" />
          <span className="shortcut-text">Quick Launch &amp; Jump</span>
          <kbd className="cmd-kbd">⌘K</kbd>
        </button>
      </div>

      {/* Right Controls & Sovereignty Proofs */}
      <div className="status-strip-right">
        {/* Dynamic Model Badge (Sourced live from GET /models/tier) */}
        <div
          className="status-model-badge"
          title={`Active Hardware Tier: ${sovereignty?.local_mode_enabled ? 'Local Edge Server / RTX 4060' : 'Disconnected'}`}
        >
          <Cpu size={14} className="model-badge-icon" />
          <span className="model-badge-label">Model:</span>
          <code className="model-badge-tag">{activeModel}</code>
        </div>

        {/* 1. Software Locality & Network Observation Badge */}
        <button
          type="button"
          className={`airgap-proof-badge ${isSoftwareSovereign ? 'is-verified' : 'is-warning'}`}
          onClick={onNavigateToSovereignty}
          title={
            isSoftwareSovereign
              ? 'Software Sovereignty: 0 external egress sockets on 127.0.0.1 loopback'
              : `Warning: ${foreignSockets} non-loopback socket(s) detected`
          }
          aria-live="polite"
        >
          {isSoftwareSovereign ? (
            <>
              <ShieldCheck size={14} className="airgap-icon" />
              <span className="airgap-label">SOVEREIGN: LOCAL (0 EXTERNAL)</span>
              <span className="airgap-live-indicator" title="Live Host Sockets Polling Active">
                <span className="airgap-pulse-dot" />
              </span>
            </>
          ) : (
            <>
              <ShieldAlert size={14} className="airgap-icon" />
              <span className="airgap-label">SOCKET WARNING ({foreignSockets})</span>
            </>
          )}
        </button>

        {/* 2. Physical Air-Gap Attestation Badge (Truthful: Operator Verified vs Check Required) */}
        <button
          type="button"
          className={`airgap-proof-badge ${isPhysicallyAttested ? 'is-attested' : 'is-attest-pending'}`}
          onClick={onOpenAttestation || onNavigateToSovereignty}
          title={
            isPhysicallyAttested
              ? `Physical Air-Gap: Operator Verified (Event #${physicalAttestation?.event_id?.slice(0, 8)})`
              : 'Physical Air-Gap: Operator Verification Required (Click to attest)'
          }
          aria-label="Physical Air-Gap Status"
        >
          {isPhysicallyAttested ? (
            <>
              <ShieldCheck size={14} className="airgap-icon" />
              <span className="airgap-label">PHYSICAL: OPERATOR VERIFIED</span>
            </>
          ) : (
            <>
              <ShieldAlert size={14} className="airgap-icon" />
              <span className="airgap-label">PHYSICAL: CHECK REQUIRED</span>
            </>
          )}
        </button>

        {/* Live Refresh Action */}
        <button
          type="button"
          className={`status-action-btn ${loading ? 'is-spinning' : ''}`}
          onClick={refresh}
          title="Refresh Sovereignty & Telemetry"
          aria-label="Refresh Telemetry"
        >
          <RefreshCw size={14} />
        </button>

        {/* Settings Action */}
        <button
          type="button"
          className="status-action-btn"
          onClick={onOpenSettings || onOpenCommandPalette}
          title="System Settings & Hardware Profile"
          aria-label="System Settings"
        >
          <Sliders size={14} />
        </button>
      </div>
    </header>
  );
};
