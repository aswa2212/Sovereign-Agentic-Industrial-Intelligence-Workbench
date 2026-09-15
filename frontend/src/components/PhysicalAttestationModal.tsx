import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckSquare,
  Square,
  X,
  AlertTriangle,
  Info,
  Server,
  Lock,
} from 'lucide-react';
import { auditService } from '../services/audit';
import { PhysicalIsolationAttestation, PhysicalIsolationAttestationChecklist } from '../types/audit';
import { useToast } from './ToastProvider';

interface PhysicalAttestationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAttested?: (attestation: PhysicalIsolationAttestation) => void;
  currentNetworkStatus?: string;
  foreignSocketsCount?: number;
}

export const PhysicalAttestationModal: React.FC<PhysicalAttestationModalProps> = ({
  isOpen,
  onClose,
  onAttested,
  currentNetworkStatus = 'PASS',
  foreignSocketsCount = 0,
}) => {
  const toast = useToast();
  const [checklist, setChecklist] = useState<PhysicalIsolationAttestationChecklist>({
    ethernet_disconnected: false,
    wifi_disabled: false,
    adapter_disabled: false,
    external_route_checked: false,
    radios_checked: false,
    operator_confirmed: false,
  });

  const [operatorNotes, setOperatorNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const allChecked =
    checklist.ethernet_disconnected &&
    checklist.wifi_disabled &&
    checklist.adapter_disabled &&
    checklist.external_route_checked &&
    checklist.radios_checked &&
    checklist.operator_confirmed;

  const toggleCheck = (key: keyof PhysicalIsolationAttestationChecklist) => {
    setChecklist((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleConfirm = async () => {
    if (!allChecked) {
      setError('Please verify and check all 6 physical isolation invariants before attestation.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const response = await auditService.attestPhysicalIsolation(checklist, operatorNotes.trim() || undefined);
      toast.success(
        'Physical Isolation Attested',
        `Recorded immutable audit event #${response.event_id.slice(0, 8)} (${response.status})`
      );
      if (onAttested) {
        onAttested(response);
      }
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to record operator attestation event.');
      toast.error('Attestation Failed', err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="attest-modal-title">
      <div className="modal-card physical-attestation-modal">
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-header-title-group">
            <ShieldAlert size={20} className="modal-header-icon" />
            <div>
              <h2 id="attest-modal-title" className="modal-title">
                Physical Air-Gap Operator Attestation
              </h2>
              <span className="modal-subtitle">
                Explicit On-Premise Isolation Protocol • Immutable Local Audit Ledger Event
              </span>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close attestation dialog"
          >
            <X size={16} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {/* Truthfulness Notice Callout */}
          <div className="attestation-notice-callout">
            <Info size={16} className="notice-icon" />
            <div className="notice-text">
              <strong>Technical Integrity &amp; Truthfulness Notice:</strong> Software inspection verifies local
              socket bindings and absence of active external connections. However, physical air-gap isolation
              (unplugged cables, powered-off radios) requires physical operator verification. This form records an
              auditable operator assertion in the local SHA-256 hash-chained audit ledger.
            </div>
          </div>

          {/* Current Software & Network Observation Snapshot */}
          <div className="attestation-current-obs">
            <div className="obs-item">
              <span className="obs-label">SOFTWARE SOVEREIGNTY:</span>
              <span className="obs-val text-success">LOCAL ONLY (127.0.0.1)</span>
            </div>
            <div className="obs-item">
              <span className="obs-label">NETWORK OBSERVATION:</span>
              <span className={`obs-val ${foreignSocketsCount === 0 ? 'text-success' : 'text-warning'}`}>
                {foreignSocketsCount === 0 ? '0 FOREIGN SOCKETS (PASS)' : `${foreignSocketsCount} NON-LOOPBACK DETECTED`}
              </span>
            </div>
            <div className="obs-item">
              <span className="obs-label">AUDIT LEDGER:</span>
              <span className="obs-val text-success">SHA-256 HASH CHAIN ACTIVE</span>
            </div>
          </div>

          {/* 6-Point Physical Verification Checklist */}
          <div className="attestation-checklist-group">
            <div className="checklist-heading">
              <span>PHYSICAL OPERATOR VERIFICATION CHECKLIST (ALL REQUIRED)</span>
              <span className="checklist-count">
                {Object.values(checklist).filter(Boolean).length} / 6 VERIFIED
              </span>
            </div>

            <div className="checklist-items">
              <label className={`checklist-row ${checklist.ethernet_disconnected ? 'is-checked' : ''}`}>
                <input
                  type="checkbox"
                  checked={checklist.ethernet_disconnected}
                  onChange={() => toggleCheck('ethernet_disconnected')}
                />
                <span className="checkbox-icon">
                  {checklist.ethernet_disconnected ? <CheckSquare size={16} /> : <Square size={16} />}
                </span>
                <span className="checklist-text">
                  <strong>Ethernet Cable Disconnected:</strong> Physical RJ45 Ethernet patch cable is physically detached from all network interface cards.
                </span>
              </label>

              <label className={`checklist-row ${checklist.wifi_disabled ? 'is-checked' : ''}`}>
                <input
                  type="checkbox"
                  checked={checklist.wifi_disabled}
                  onChange={() => toggleCheck('wifi_disabled')}
                />
                <span className="checkbox-icon">
                  {checklist.wifi_disabled ? <CheckSquare size={16} /> : <Square size={16} />}
                </span>
                <span className="checklist-text">
                  <strong>Wi-Fi Disabled:</strong> Wireless adapter is disabled in OS network settings or hardware switch toggled off.
                </span>
              </label>

              <label className={`checklist-row ${checklist.adapter_disabled ? 'is-checked' : ''}`}>
                <input
                  type="checkbox"
                  checked={checklist.adapter_disabled}
                  onChange={() => toggleCheck('adapter_disabled')}
                />
                <span className="checkbox-icon">
                  {checklist.adapter_disabled ? <CheckSquare size={16} /> : <Square size={16} />}
                </span>
                <span className="checklist-text">
                  <strong>Internet-Capable Adapters Isolated:</strong> Cellular modems, USB tethering, VPNs, and secondary interfaces are disabled.
                </span>
              </label>

              <label className={`checklist-row ${checklist.external_route_checked ? 'is-checked' : ''}`}>
                <input
                  type="checkbox"
                  checked={checklist.external_route_checked}
                  onChange={() => toggleCheck('external_route_checked')}
                />
                <span className="checkbox-icon">
                  {checklist.external_route_checked ? <CheckSquare size={16} /> : <Square size={16} />}
                </span>
                <span className="checklist-text">
                  <strong>No External Route Available:</strong> Host routing table contains no active default gateway route to the public Internet.
                </span>
              </label>

              <label className={`checklist-row ${checklist.radios_checked ? 'is-checked' : ''}`}>
                <input
                  type="checkbox"
                  checked={checklist.radios_checked}
                  onChange={() => toggleCheck('radios_checked')}
                />
                <span className="checkbox-icon">
                  {checklist.radios_checked ? <CheckSquare size={16} /> : <Square size={16} />}
                </span>
                <span className="checklist-text">
                  <strong>Unnecessary Radios Disabled:</strong> Bluetooth, NFC, and wireless peripheral transmitters not strictly needed are disabled.
                </span>
              </label>

              <label className={`checklist-row ${checklist.operator_confirmed ? 'is-checked' : ''}`}>
                <input
                  type="checkbox"
                  checked={checklist.operator_confirmed}
                  onChange={() => toggleCheck('operator_confirmed')}
                />
                <span className="checkbox-icon">
                  {checklist.operator_confirmed ? <CheckSquare size={16} /> : <Square size={16} />}
                </span>
                <span className="checklist-text">
                  <strong>Operator Continuity Confirmation:</strong> Operator confirms system continues using local services only (FastAPI, Ollama, RAG on <code>127.0.0.1</code>).
                </span>
              </label>
            </div>
          </div>

          {/* Optional Operator Notes */}
          <div className="attestation-notes-group">
            <label htmlFor="operator-notes" className="notes-label">
              OPERATOR IDENTIFIER / DEMO NOTES (OPTIONAL):
            </label>
            <input
              id="operator-notes"
              type="text"
              placeholder="e.g., SIH Evaluation Station 1 — Physical Isolation Confirmed by Operator"
              value={operatorNotes}
              onChange={(e) => setOperatorNotes(e.target.value)}
              className="notes-input"
            />
          </div>

          {error && (
            <div className="attestation-error-callout">
              <AlertTriangle size={15} />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-accent btn-sm"
            onClick={handleConfirm}
            disabled={!allChecked || submitting}
          >
            <ShieldCheck size={14} />
            <span>{submitting ? 'Recording Ledger Event...' : 'Confirm Physical Isolation'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
