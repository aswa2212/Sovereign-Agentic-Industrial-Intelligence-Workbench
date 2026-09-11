import React, { useState, useEffect } from 'react';
import { AuditEvent, AuditVerificationResult } from '../types/audit';
import { auditService } from '../services/audit';
import {
  ShieldCheck,
  ShieldAlert,
  History,
  RefreshCw,
  Search,
  ChevronDown,
  ChevronUp,
  Hash,
  Database,
} from 'lucide-react';

interface AuditLedgerProps {
  initialEvents?: AuditEvent[];
  autoRefresh?: boolean;
}

export const AuditLedger: React.FC<AuditLedgerProps> = ({
  initialEvents = [],
  autoRefresh = false,
}) => {
  const [events, setEvents] = useState<AuditEvent[]>(initialEvents);
  const [verification, setVerification] = useState<AuditVerificationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [filterQuery, setFilterQuery] = useState('');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const response = await auditService.getEvents(undefined, undefined, 100);
      setEvents(response.items || []);
    } catch (err) {
      console.error('Failed to load audit events', err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const res = await auditService.verifyIntegrity();
      setVerification(res.verification);
    } catch (err) {
      console.error('Integrity check failed', err);
    } finally {
      setVerifying(false);
    }
  };

  useEffect(() => {
    fetchEvents();
    handleVerify();
    if (autoRefresh) {
      const interval = setInterval(fetchEvents, 10000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const filteredEvents = events.filter((ev) => {
    const q = filterQuery.toLowerCase();
    return (
      ev.event_type.toLowerCase().includes(q) ||
      (ev.action && ev.action.toLowerCase().includes(q)) ||
      (ev.agent_state && ev.agent_state.toLowerCase().includes(q)) ||
      (ev.source && ev.source.toLowerCase().includes(q)) ||
      (ev.message && ev.message.toLowerCase().includes(q)) ||
      ev.event_id.toLowerCase().includes(q)
    );
  });

  return (
    <div className="card">
      <div className="card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <History size={16} style={{ color: 'var(--accent-primary)' }} />
          <div>
            <div className="card-title">Immutable Audit Ledger</div>
            <div className="card-subtitle">
              Local Cryptographic Hash Chain • Tamper-Evident Operational Proof
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={fetchEvents}
            disabled={loading}
            title="Reload recent audit events"
          >
            <RefreshCw size={13} className={loading ? 'icon-spin' : ''} />
            Refresh
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleVerify}
            disabled={verifying}
            title="Verify SHA-256 hash link continuity across all recorded events"
          >
            <ShieldCheck size={13} className={verifying ? 'icon-spin' : ''} />
            Verify Hash Chain
          </button>
        </div>
      </div>

      {/* Verification & Metrics Status Ribbon */}
      <div
        style={{
          padding: '0.75rem 1rem',
          background: 'var(--bg-surface-muted)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          fontSize: '0.8125rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>INTEGRITY STATUS:</span>
            {verification?.valid ? (
              <span className="badge badge-success">
                <ShieldCheck size={12} style={{ marginRight: '4px' }} />
                Chain Valid ({verification.events_checked} records verified)
              </span>
            ) : verification ? (
              <span className="badge badge-danger">
                <ShieldAlert size={12} style={{ marginRight: '4px' }} />
                Integrity Failed at event {verification.first_invalid_event}
              </span>
            ) : (
              <span className="badge badge-neutral">Unverified</span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ color: 'var(--text-muted)' }}>TOTAL RECORDS:</span>
            <span className="code-badge">{events.length}</span>
          </div>
        </div>

        {/* Filter input */}
        <div style={{ position: 'relative', width: '240px' }}>
          <Search
            size={13}
            style={{ position: 'absolute', left: '8px', top: '9px', color: 'var(--text-muted)' }}
          />
          <input
            type="text"
            placeholder="Filter audit events..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            className="form-input"
            style={{ paddingLeft: '28px', fontSize: '0.75rem', height: '30px' }}
          />
        </div>
      </div>

      {/* Technical Table */}
      <div style={{ overflowX: 'auto', maxHeight: '420px' }}>
        <table className="tech-table">
          <thead>
            <tr>
              <th style={{ width: '90px' }}>TIME</th>
              <th style={{ width: '160px' }}>EVENT</th>
              <th style={{ width: '100px' }}>STATE</th>
              <th style={{ width: '130px' }}>SOURCE</th>
              <th>ACTION / MESSAGE</th>
              <th style={{ width: '80px' }}>STATUS</th>
              <th style={{ width: '110px' }}>HASH</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  {loading ? 'Loading audit ledger...' : 'No audit records match the current filter.'}
                </td>
              </tr>
            ) : (
              filteredEvents.map((ev) => {
                const isExpanded = expandedEventId === ev.event_id;
                const timeStr = ev.timestamp
                  ? new Date(ev.timestamp).toLocaleTimeString()
                  : '--:--:--';

                const isPass = ev.status.toUpperCase() === 'PASS' || ev.status.toUpperCase() === 'SUCCESS';

                return (
                  <React.Fragment key={ev.event_id}>
                    <tr
                      onClick={() => setExpandedEventId(isExpanded ? null : ev.event_id)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {timeStr}
                      </td>
                      <td>
                        <span className="badge badge-neutral" style={{ fontSize: '0.7rem', fontWeight: 600 }}>
                          {ev.event_type}
                        </span>
                      </td>
                      <td>
                        {ev.agent_state ? (
                          <span className="code-badge">{ev.agent_state}</span>
                        ) : (
                          <span style={{ color: 'var(--text-light)' }}>—</span>
                        )}
                      </td>
                      <td style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        {ev.source || ev.tool_name || 'System'}
                      </td>
                      <td style={{ fontSize: '0.8125rem' }}>
                        <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{ev.action}</div>
                        {ev.message && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                            {ev.message}
                          </div>
                        )}
                      </td>
                      <td>
                        <span
                          className={`badge ${isPass ? 'badge-success' : 'badge-danger'}`}
                          style={{ fontSize: '0.7rem' }}
                        >
                          {ev.status.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.7rem',
                            color: 'var(--text-muted)',
                          }}
                        >
                          <Hash size={10} />
                          {ev.event_hash ? ev.event_hash.slice(0, 8) : '—'}
                          {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                        </div>
                      </td>
                    </tr>

                    {/* Detailed Event Inspection Drawer */}
                    {isExpanded && (
                      <tr style={{ background: 'var(--bg-surface-muted)' }}>
                        <td colSpan={7} style={{ padding: '0.75rem 1rem' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem', fontSize: '0.75rem', marginBottom: '0.5rem' }}>
                            <div>
                              <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>EVENT ID:</span>{' '}
                              <span style={{ fontFamily: 'var(--font-mono)' }}>{ev.event_id}</span>
                            </div>
                            <div>
                              <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>TIMESTAMP:</span>{' '}
                              <span style={{ fontFamily: 'var(--font-mono)' }}>{ev.timestamp}</span>
                            </div>
                            <div>
                              <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>PREVIOUS HASH:</span>{' '}
                              <span style={{ fontFamily: 'var(--font-mono)' }}>{ev.previous_hash}</span>
                            </div>
                            <div>
                              <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>CURRENT HASH:</span>{' '}
                              <span style={{ fontFamily: 'var(--font-mono)' }}>{ev.event_hash}</span>
                            </div>
                          </div>

                          {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                            <div>
                              <div style={{ fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.7rem', textTransform: 'uppercase', marginBottom: '4px' }}>
                                Non-Sensitive Event Metadata
                              </div>
                              <pre
                                style={{
                                  background: 'var(--bg-surface)',
                                  border: '1px solid var(--border-subtle)',
                                  borderRadius: 'var(--radius-sm)',
                                  padding: '0.5rem',
                                  fontSize: '0.75rem',
                                  fontFamily: 'var(--font-mono)',
                                  overflowX: 'auto',
                                  margin: 0,
                                }}
                              >
                                {JSON.stringify(ev.metadata, null, 2)}
                              </pre>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
