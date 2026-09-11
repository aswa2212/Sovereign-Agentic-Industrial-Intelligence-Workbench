import React from 'react';
import { AuditLedger } from '../components/AuditLedger';
import { History, ShieldCheck, Lock, Database } from 'lucide-react';

export const AuditPage: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Banner */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <History size={18} style={{ color: 'var(--accent-primary)' }} />
            <div>
              <div className="card-title">Operational Audit Ledger & Integrity Verification</div>
              <div className="card-subtitle">
                Cryptographic SHA-256 Hash Chain • Zero External Logging • Tamper Evidence
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span className="badge badge-success">
              <Lock size={12} style={{ marginRight: '4px' }} />
              On-Prem Storage
            </span>
          </div>
        </div>

        <div
          style={{
            padding: '0.875rem 1rem',
            background: 'var(--bg-surface-muted)',
            fontSize: '0.8125rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
          }}
        >
          <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '2px' }}>
            CRYPTOGRAPHIC CHAIN INTEGRITY SPECIFICATION:
          </div>
          Every agent state transition, tool execution, model routing decision, and deliverable creation
          is hashed into an append-only ledger using SHA-256 with back-pointers to the preceding event hash:
          <code
            style={{
              display: 'block',
              margin: '6px 0',
              padding: '6px 10px',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: 'var(--accent-primary)',
            }}
          >
            H_i = SHA256( H_{'{i-1}'} || timestamp || event_type || action || metadata_sanitized )
          </code>
          Any modification, deletion, or out-of-order insertion immediately breaks subsequent hashes,
          providing mathematical proof of operational authenticity without external third parties.
        </div>
      </div>

      {/* Main Audit Ledger Component */}
      <AuditLedger autoRefresh={true} />
    </div>
  );
};
