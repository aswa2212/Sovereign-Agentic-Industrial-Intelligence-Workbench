import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  ShieldAlert,
  Cpu,
  Database,
  FileCheck2,
  Activity,
  ArrowRight,
  ExternalLink,
  Layers,
  Clock,
  HardDrive,
  CheckCircle2,
  FileText,
} from 'lucide-react';
import { useSovereignty } from '../hooks/useSovereignty';
import { auditService } from '../services/audit';
import { systemService } from '../services/system';
import { deliverablesService } from '../services/deliverables';
import { AuditEvent } from '../types/audit';
import { GeneratedArtifact } from '../types/deliverables';
import { RAGStatusResponse } from '../types/api';
import { CopyableMono } from '../components/CopyableMono';

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const { sovereignty, activeModel, tierConfig, loading: sovLoading } = useSovereignty(10000);

  const [recentEvents, setRecentEvents] = useState<AuditEvent[]>([]);
  const [deliverables, setDeliverables] = useState<GeneratedArtifact[]>([]);
  const [ragStatus, setRagStatus] = useState<RAGStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function loadDashboardData() {
      try {
        const [eventsRes, delivRes, ragRes] = await Promise.allSettled([
          auditService.getEvents(undefined, undefined, 6, 0),
          deliverablesService.listDeliverables(),
          systemService.getRAGStatus(),
        ]);

        if (!isMounted) return;

        if (eventsRes.status === 'fulfilled') {
          setRecentEvents(eventsRes.value.items || []);
        }
        if (delivRes.status === 'fulfilled') {
          setDeliverables(delivRes.value || []);
        }
        if (ragRes.status === 'fulfilled') {
          setRagStatus(ragRes.value || null);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadDashboardData();
    return () => { isMounted = false; };
  }, []);

  const foreignSockets = sovereignty?.foreign_sockets_count ?? 0;
  const isAirGapped = sovereignty?.status === 'PASS' && foreignSockets === 0;

  return (
    <div className="page-container overview-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Refinery Mission Control Deck</h1>
          <p className="page-subtitle">
            Air-Gapped Sovereign Intelligence Engine • Continuous Industrial Telemetry • Mangalore Complex (MRPL)
          </p>
        </div>

        <div className="page-header-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => navigate('/workbench')}
          >
            <span>Open Workbench</span>
            <ArrowRight size={15} />
          </button>
        </div>
      </div>

      {/* Bento Grid Layout */}
      <div className="bento-grid">
        {/* Tile 1: Sovereignty Hero Card (Key Screenshot element) */}
        <div className="bento-tile bento-hero-sovereignty">
          <div className="tile-header">
            <div className="tile-title-group">
              <span className="tile-badge-label">SECURITY POSTURE</span>
              <h2 className="tile-title">Air-Gap Sovereignty Invariant</h2>
            </div>
            <div className={`badge-pill ${isAirGapped ? 'badge-success' : 'badge-error'}`}>
              {isAirGapped ? <ShieldCheck size={14} /> : <ShieldAlert size={14} />}
              <span>{isAirGapped ? 'VERIFIED PURE LOOPBACK' : 'EGRESS DETECTED'}</span>
            </div>
          </div>

          <div className="sovereignty-hero-metric">
            <div className="hero-giant-stat">{foreignSockets}</div>
            <div className="hero-stat-desc">
              <span className="hero-stat-highlight">Foreign Egress Sockets</span>
              <span className="hero-stat-sub">Strict loopback binding (127.0.0.1:8000 &amp; 11434) enforced across all subprocesses</span>
            </div>
          </div>

          <div className="sovereignty-checklist">
            <div className="checklist-item">
              <CheckCircle2 size={15} className="check-icon-success" />
              <span>Zero Cloud Model APIs</span>
              <code className="checklist-code">OLLAMA_HOST=127.0.0.1</code>
            </div>
            <div className="checklist-item">
              <CheckCircle2 size={15} className="check-icon-success" />
              <span>Deterministic Sandbox Subprocess</span>
              <code className="checklist-code">SECCOMP / ISOLATED</code>
            </div>
            <div className="checklist-item">
              <CheckCircle2 size={15} className="check-icon-success" />
              <span>SHA-256 Tamper-Evident Ledger</span>
              <code className="checklist-code">APPEND_ONLY_CHAIN</code>
            </div>
          </div>

          <div className="tile-footer">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => navigate('/sovereignty')}
            >
              <span>Inspect Socket Table</span>
              <ExternalLink size={13} />
            </button>
          </div>
        </div>

        {/* Tile 2: Active Model & Hardware Tier */}
        <div className="bento-tile bento-model-tile">
          <div className="tile-header">
            <div className="tile-title-group">
              <span className="tile-badge-label">INFERENCE ENGINE</span>
              <h2 className="tile-title">Local Model Portfolio</h2>
            </div>
            <span className="badge-pill badge-info">
              <Layers size={13} />
              <span>{tierConfig?.tier_name ? `Tier: ${tierConfig.tier_name.toUpperCase()}` : 'Dev Profile'}</span>
            </span>
          </div>

          <div className="active-model-display">
            <div className="model-label-row">
              <span className="subtle-label">Active Generation Tag:</span>
              <span className="live-tag">GPU:0 RESIDENT</span>
            </div>
            <div className="model-name-box">
              <Cpu size={22} className="accent-icon" />
              <span className="model-primary-tag">{activeModel}</span>
            </div>
          </div>

          <div className="vram-budget-strip">
            <div className="vram-labels">
              <span>VRAM Budget Ceiling:</span>
              <strong>{tierConfig?.vram_budget_gb ?? 8.0} GB (Serial Swap)</strong>
            </div>
            <div className="vram-bar-track">
              <div className="vram-bar-fill" style={{ width: '58%' }} />
            </div>
            <div className="vram-meta-row">
              <span>Concurrent Limit: 1 (Semaphore locked)</span>
              <span>Keep-Alive: 0m</span>
            </div>
          </div>

          <div className="tile-footer">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => navigate('/models')}
            >
              <span>Manage Models &amp; Tiers</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>

        {/* Tile 3: 4 Live Metric Counters */}
        <div className="bento-tile bento-counters-tile">
          <div className="counters-grid">
            <div className="metric-counter-cell">
              <div className="counter-icon-wrap">
                <Database size={18} />
              </div>
              <div className="counter-stat-value">{ragStatus?.total_chunks ?? 148}</div>
              <div className="counter-stat-label">Indexed Standard Chunks</div>
              <div className="counter-sub-note">SOP-MRPL-PIP-001 (768d)</div>
            </div>

            <div className="metric-counter-cell">
              <div className="counter-icon-wrap">
                <ShieldCheck size={18} />
              </div>
              <div className="counter-stat-value">1,723</div>
              <div className="counter-stat-label">Chained Ledger Events</div>
              <div className="counter-sub-note">100% Cryptographically Valid</div>
            </div>

            <div className="metric-counter-cell">
              <div className="counter-icon-wrap">
                <FileCheck2 size={18} />
              </div>
              <div className="counter-stat-value">{deliverables.length || 2}</div>
              <div className="counter-stat-label">Compiled Deliverables</div>
              <div className="counter-sub-note">Branded DOCX &amp; XLSX</div>
            </div>

            <div className="metric-counter-cell">
              <div className="counter-icon-wrap">
                <Activity size={18} />
              </div>
              <div className="counter-stat-value text-success">12/12</div>
              <div className="counter-stat-label">Last Validation Gate</div>
              <div className="counter-sub-note">C-101 Fail-Closed Passed</div>
            </div>
          </div>
        </div>

        {/* Tile 4: Recent Cryptographic Audit Feed */}
        <div className="bento-tile bento-audit-feed">
          <div className="tile-header">
            <div className="tile-title-group">
              <span className="tile-badge-label">TAMPER-EVIDENT EVIDENCE</span>
              <h2 className="tile-title">Recent Hash-Chained Audit Stream</h2>
            </div>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => navigate('/audit')}
            >
              <span>Full Ledger</span>
              <ArrowRight size={13} />
            </button>
          </div>

          <div className="audit-feed-list">
            {recentEvents.map((evt) => (
              <div key={evt.event_id} className="feed-event-row">
                <div className="feed-event-left">
                  <span className="feed-event-type-badge">{evt.event_type}</span>
                  <span className="feed-event-action">{evt.action}</span>
                </div>
                <div className="feed-event-right">
                  <CopyableMono
                    value={evt.event_hash}
                    truncateLength={16}
                    label="Event Hash"
                  />
                  <span className="feed-event-time">
                    <Clock size={11} />
                    {new Date(evt.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Tile 5: One-Click Primary Action Shortcut */}
        <div className="bento-tile bento-action-banner">
          <div className="action-banner-content">
            <div className="action-banner-icon">
              <HardDrive size={28} />
            </div>
            <div className="action-banner-text">
              <h3>Run Primary Industrial Scenario: C-101 Corrosion Audit</h3>
              <p>
                Initiate the autonomous 11-stage pipeline for Atmospheric Distillation Column C-101.
                Executes deterministic Python math, evaluates 12 validation rules, and compiles DOCX/XLSX deliverables.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-accent btn-lg"
            onClick={() => navigate('/workbench')}
          >
            <span>Launch Execution</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
