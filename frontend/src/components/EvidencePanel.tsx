import React, { useState } from 'react';
import {
  CitationSource,
  StructuredValidationReport,
  CorrosionCalculation,
  OcrVisionSummary,
} from '../types/agent';
import { RouteResponse } from '../types/api';
import {
  BookOpen,
  FileText,
  ChevronDown,
  ChevronUp,
  Search,
  Cpu,
  CheckCircle2,
  Calculator,
  Eye,
  AlertTriangle,
  AlertCircle,
  ShieldCheck,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { ValidationGateFuseBox, evaluateValidationGate } from './ValidationGateFuseBox';
import { DataSourceBadge } from './DataSourceBadge';

interface EvidencePanelProps {
  citations: CitationSource[];
  summary?: string | null;
  calculation?: CorrosionCalculation | null;
  ocrVisionSummary?: OcrVisionSummary | null;
  routePreview?: RouteResponse | null;
  validationReport?: StructuredValidationReport | null;
  isRunning?: boolean;
  executionMode?: 'deterministic' | 'live';
  isFocused?: boolean;
  onToggleFocus?: () => void;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  citations,
  summary,
  calculation,
  ocrVisionSummary,
  routePreview,
  validationReport,
  isRunning = false,
  executionMode = 'deterministic',
  isFocused = false,
  onToggleFocus,
}) => {
  const [activeTab, setActiveTab] = useState<'validation' | 'calculations' | 'ocr' | 'citations'>('validation');
  const [expandedChunk, setExpandedChunk] = useState<string | null>(
    citations.length > 0 ? (citations[0].chunk_id || 'chk-0') : null
  );
  const [filterText, setFilterText] = useState('');

  const isLive = executionMode === 'live';
  const hasCitations = citations.length > 0;

  const filtered = citations.filter(
    (c) =>
      c.source_document.toLowerCase().includes(filterText.toLowerCase()) ||
      c.text.toLowerCase().includes(filterText.toLowerCase()) ||
      (c.chunk_id && c.chunk_id.toLowerCase().includes(filterText.toLowerCase()))
  );

  const hasVisualFindings = !!(
    ocrVisionSummary &&
    (
      (ocrVisionSummary.findings_count !== undefined && ocrVisionSummary.findings_count > 0) ||
      (ocrVisionSummary.equipment_tags && ocrVisionSummary.equipment_tags.length > 0) ||
      (ocrVisionSummary.instrument_tags && ocrVisionSummary.instrument_tags.length > 0) ||
      (ocrVisionSummary.findings && ocrVisionSummary.findings.length > 0)
    )
  );

  // Derive assessment status dynamically
  const isSafe = calculation?.margin_check?.is_acceptable ?? (calculation?.margin_check?.status === 'PASS');
  const isRetire = calculation?.margin_check?.status === 'RETIRE' || calculation?.margin_check?.is_acceptable === false;
  const isMonitor = calculation?.margin_check?.status === 'MONITOR';
  // Evaluate validation gate through single authoritative source
  const valGate = evaluateValidationGate(validationReport);

  return (
    <div className="workbench-panel evidence-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-header-title-group">
          <BookOpen size={16} className="panel-header-icon" />
          <div>
            <h2 className="panel-title">Evidence &amp; Assessment</h2>
            <span className="panel-subtitle">Calculations, Invariants &amp; Synthesis</span>
          </div>
        </div>

        <div className="panel-header-badges">
          <DataSourceBadge
            source={hasCitations ? (isLive ? 'LIVE' : 'FALLBACK') : 'FALLBACK'}
            label={hasCitations ? (isLive ? 'LIVE LOCAL CORPUS' : 'LOCAL CORPUS') : 'NO EVIDENCE LOADED'}
          />
          {onToggleFocus && (
            <button
              type="button"
              className={`panel-header-btn ${isFocused ? 'is-active' : ''}`}
              onClick={onToggleFocus}
              title={isFocused ? 'Restore 3-Column Cockpit (Esc)' : 'Focus Evidence & Assessment (Full Width)'}
              aria-label={isFocused ? 'Restore 3-Column Cockpit' : 'Focus Evidence & Assessment'}
            >
              {isFocused ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
            </button>
          )}
        </div>
      </div>

      {/* Real-time Intent Routing Mini-Banner (if available) */}
      {routePreview && (
        <div className="route-evidence-mini-strip" title={routePreview.reason || 'Task Intent Routing Decision'}>
          <div className="route-mini-left">
            <Cpu size={12} className="accent-icon" />
            <span className="route-mini-label">ROUTED:</span>
            <code className="route-mini-code">{routePreview.task_type || 'corrosion_audit'}</code>
            <span className="route-mini-sep">•</span>
            <span className="route-mini-text">{routePreview.capability || 'engineering_math'}</span>
            <span className="route-mini-sep">•</span>
            <span className="route-mini-role">{routePreview.model_role || 'reasoning'}</span>
          </div>
          <span className="badge-pill badge-neutral">
            {Math.round((routePreview.confidence ?? 0.98) * 100)}% CONF
          </span>
        </div>
      )}

      {/* CONDITION 1: Persistent Executive Summary (Visible without tab click) */}
      <div className="persistent-summary-card" id="executive-summary-card">
        <div className="persistent-summary-header">
          <div className="summary-header-left">
            <FileText size={13} className="accent-icon" />
            <span className="summary-header-title">EXECUTIVE ASSESSMENT SUMMARY</span>
          </div>
          <span className="summary-badge">AUTONOMOUS SYNTHESIS</span>
        </div>
        <div className="persistent-summary-content">
          {summary && summary.trim() ? (
            <p className="summary-paragraph">{summary}</p>
          ) : (
            <p className="summary-placeholder">Awaiting pipeline execution for autonomous engineering synthesis.</p>
          )}
        </div>
      </div>

      {/* Evidence Subsystem Tabs Navigation */}
      <div className="evidence-tabs-deck" role="tablist" aria-label="Evidence Subsystems">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'validation'}
          className={`evidence-deck-tab ${activeTab === 'validation' ? 'is-active-tab' : ''}`}
          onClick={() => setActiveTab('validation')}
        >
          <ShieldCheck size={13} />
          <span>Validation Gate</span>
          <span className={`tab-pill-badge ${valGate.hasReport ? (valGate.isAllPassed ? 'badge-safe' : 'badge-alert') : ''}`}>
            {valGate.passedCount}/{valGate.totalCount}
          </span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'calculations'}
          className={`evidence-deck-tab ${activeTab === 'calculations' ? 'is-active-tab' : ''}`}
          onClick={() => setActiveTab('calculations')}
        >
          <Calculator size={13} />
          <span>Calculations</span>
          <span className={`tab-pill-badge ${calculation ? (isSafe ? 'badge-safe' : 'badge-alert') : ''}`}>
            {calculation
              ? (calculation.corrosion_rate_mm_per_year !== undefined
                  ? `${calculation.corrosion_rate_mm_per_year} mm/y`
                  : 'API 570')
              : 'API 570'}
          </span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'ocr'}
          className={`evidence-deck-tab ${activeTab === 'ocr' ? 'is-active-tab' : ''}`}
          onClick={() => setActiveTab('ocr')}
          disabled={!hasVisualFindings}
          title={!hasVisualFindings ? 'No visual OCR findings for this task' : 'Inspect OCR/VLM visual findings'}
        >
          <Eye size={13} />
          <span>Visual OCR</span>
          <span className="tab-pill-badge">{ocrVisionSummary?.findings_count || 0}</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'citations'}
          className={`evidence-deck-tab ${activeTab === 'citations' ? 'is-active-tab' : ''}`}
          onClick={() => setActiveTab('citations')}
        >
          <BookOpen size={13} />
          <span>Citations</span>
          <span className="tab-pill-badge">{citations.length}</span>
        </button>
      </div>

      {/* Active Tab Viewport */}
      <div className="panel-body-scroll evidence-tab-viewport">
        {/* TAB 1: Validation Gate (Fuse Box) */}
        {activeTab === 'validation' && (
          <div className="tab-pane-validation">
            <ValidationGateFuseBox report={validationReport} isRunning={isRunning} />
          </div>
        )}

        {/* TAB 2: Calculations & Engineering Assessment */}
        {activeTab === 'calculations' && (() => {
          if (!calculation) {
            const hasVisualFindings = Boolean(
              ocrVisionSummary &&
              ((ocrVisionSummary.findings_count && ocrVisionSummary.findings_count > 0) ||
               (ocrVisionSummary.findings && ocrVisionSummary.findings.length > 0) ||
               (ocrVisionSummary.equipment_tags && ocrVisionSummary.equipment_tags.length > 0))
            );

            return (
              <div className="evidence-card calculation-assessment-card" id="calculation-assessment-card">
                <div className="evidence-card-header">
                  <div className="card-header-left">
                    <Calculator size={14} className="accent-icon" />
                    <span className="card-heading">ENGINEERING CALCULATION &amp; ASSESSMENT</span>
                  </div>
                  <span className={`badge-pill ${hasVisualFindings ? 'badge-warning' : 'badge-neutral'}`}>
                    {isRunning ? 'CALCULATING...' : (hasVisualFindings ? 'UNAVAILABLE' : 'AWAITING INPUT')}
                  </span>
                </div>

                {hasVisualFindings ? (
                  <div style={{ padding: '1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-alert)', marginBottom: '0.5rem' }}>
                      <AlertTriangle size={15} />
                      <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>CORROSION RATE UNAVAILABLE</span>
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0 0 0.75rem 0', lineHeight: 1.5 }}>
                      Visual and document analysis completed successfully, but authoritative corrosion calculations cannot be evaluated because required thickness gauging data was not present in the document.
                    </p>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-hairline)' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                        Missing evidence required for API 570 / ASME B31.3 calculation:
                      </span>
                      <ul style={{ margin: 0, paddingLeft: '1.2rem', lineHeight: '1.6' }}>
                        <li>Current measured thickness (t_actual)</li>
                        <li>Nominal / initial baseline thickness (t_initial)</li>
                        <li>Elapsed operating / inspection interval (Δt)</li>
                        <li>Minimum required retirement thickness (t_min)</li>
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: '2rem', textAlign: 'center' }}>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>
                      Awaiting document upload and pipeline execution to perform engineering calculations.
                    </p>
                  </div>
                )}
              </div>
            );
          }

          return (
            <div className="evidence-card calculation-assessment-card" id="calculation-assessment-card">
              <div className="evidence-card-header">
                <div className="card-header-left">
                  <Calculator size={14} className="accent-icon" />
                  <span className="card-heading">ENGINEERING CALCULATION &amp; ASSESSMENT</span>
                </div>
                <span
                  className={`badge-pill ${
                    isSafe
                      ? 'badge-success'
                      : isRetire
                      ? 'badge-error'
                      : isMonitor
                      ? 'badge-warning'
                      : 'badge-neutral'
                  }`}
                >
                  {isSafe
                    ? 'CONTINUE SERVICE'
                    : isRetire
                    ? 'RETIRE / CRITICAL'
                    : isMonitor
                    ? 'MONITOR SERVICE'
                    : calculation.margin_check?.status || calculation.remaining_life_status || 'ASSESSED'}
                </span>
              </div>

              <div className="calc-metrics-grid">
                {/* Corrosion Rate */}
                <div className="calc-metric-cell cell-highlight">
                  <span className="calc-metric-label">CORROSION RATE</span>
                  <span className={`calc-metric-value ${calculation?.corrosion_rate_mm_per_year !== undefined && calculation?.corrosion_rate_mm_per_year !== null ? 'val-highlight' : 'val-muted'}`}>
                    {calculation?.corrosion_rate_mm_per_year !== undefined && calculation?.corrosion_rate_mm_per_year !== null
                      ? `${calculation.corrosion_rate_mm_per_year} mm/yr`
                      : '—'}
                  </span>
                  <span className="calc-metric-sub">API 570 Short-Term</span>
                </div>

                {/* Remaining Service Life */}
                <div className={`calc-metric-cell ${calculation?.remaining_life_years !== undefined && calculation?.remaining_life_years !== null ? (calculation.remaining_life_years > 2 ? 'cell-safe' : 'cell-warning') : ''}`}>
                  <span className="calc-metric-label">REMAINING SERVICE LIFE</span>
                  <span className={`calc-metric-value ${calculation?.remaining_life_years !== undefined && calculation?.remaining_life_years !== null ? (calculation.remaining_life_years > 2 ? 'val-success' : 'val-warning') : 'val-muted'}`}>
                    {calculation?.remaining_life_years !== undefined && calculation?.remaining_life_years !== null
                      ? `${calculation.remaining_life_years} yrs`
                      : (calculation ? 'UNAVAILABLE' : '—')}
                  </span>
                  <span className="calc-metric-sub">To t_min limit</span>
                </div>

                {/* Total Metal Loss */}
                <div className="calc-metric-cell">
                  <span className="calc-metric-label">TOTAL METAL LOSS</span>
                  <span className={`calc-metric-value ${calculation?.metal_loss_mm !== undefined && calculation?.metal_loss_mm !== null ? '' : 'val-muted'}`}>
                    {calculation?.metal_loss_mm !== undefined && calculation?.metal_loss_mm !== null
                      ? `${calculation.metal_loss_mm} mm`
                      : '—'}
                  </span>
                  <span className="calc-metric-sub">t_nominal - t_actual</span>
                </div>

                {/* Structural Margin */}
                <div className={`calc-metric-cell ${calculation?.margin_check?.margin_mm !== undefined ? (calculation.margin_check.margin_mm >= 0 ? 'cell-safe' : 'cell-critical') : ''}`}>
                  <span className="calc-metric-label">STRUCTURAL MARGIN</span>
                  <span className={`calc-metric-value ${calculation?.margin_check?.margin_mm !== undefined ? (calculation.margin_check.margin_mm >= 0 ? 'val-success' : 'val-critical') : 'val-muted'}`}>
                    {calculation?.margin_check?.margin_mm !== undefined && calculation?.margin_check?.margin_mm !== null
                      ? `${calculation.margin_check.margin_mm >= 0 ? '+' : ''}${calculation.margin_check.margin_mm} mm`
                      : (calculation?.remaining_margin_mm !== undefined ? `${calculation.remaining_margin_mm} mm` : (calculation ? 'UNAVAILABLE' : '—'))}
                  </span>
                  <span className="calc-metric-sub">t_actual - t_required</span>
                </div>

                {/* Governing CML */}
                <div className="calc-metric-cell">
                  <span className="calc-metric-label">GOVERNING CML</span>
                  <span className={`calc-metric-value ${calculation?.governing_cml || calculation?.component_id ? '' : 'val-muted'}`}>
                    {calculation?.governing_cml || calculation?.component_id || (calculation ? 'UNAVAILABLE' : '—')}
                  </span>
                  <span className="calc-metric-sub">Critical inspection point</span>
                </div>

                {/* Assessment Status */}
                <div className="calc-metric-cell">
                  <span className="calc-metric-label">ASSESSMENT STATUS</span>
                  <span className={`calc-metric-value ${
                    isSafe
                      ? 'val-success'
                      : isRetire
                      ? 'val-critical'
                      : isMonitor
                      ? 'val-warning'
                      : 'val-muted'
                  }`}>
                    {calculation?.margin_check?.status || calculation?.remaining_life_status || (calculation ? 'UNAVAILABLE' : '—')}
                  </span>
                  <span className="calc-metric-sub">Integrity disposition</span>
                </div>
              </div>

              {calculation && (
                <div className="calc-details-footer">
                  <span>Formula: <code>{calculation.formula_used || 'API 570: Cr = (t_initial - t_actual) / Δt'}</code></span>
                  {calculation.previous_thickness_mm !== undefined && calculation.current_thickness_mm !== undefined && (
                    <span>Baseline: <code>{calculation.previous_thickness_mm} mm → {calculation.current_thickness_mm} mm</code> ({calculation.elapsed_time_years ?? '—'} yrs)</span>
                  )}
                </div>
              )}
            </div>
          );
        })()}

        {/* TAB 3: Visual OCR / VLM Findings */}
        {activeTab === 'ocr' && (
          <div className="evidence-card visual-findings-card" id="visual-findings-card">
            <div className="evidence-card-header">
              <div className="card-header-left">
                <Eye size={14} className="accent-icon" />
                <span className="card-heading">VISUAL FINDINGS (OCR/VLM)</span>
              </div>
              <span className="badge-pill badge-neutral">
                {ocrVisionSummary?.findings_count || 0} EXTRACTED
              </span>
            </div>

            {ocrVisionSummary?.equipment_tags && ocrVisionSummary.equipment_tags.length > 0 && (
              <div className="visual-tags-section">
                <span className="visual-tags-label">EQUIPMENT TAGS:</span>
                <div className="visual-tags-group">
                  {ocrVisionSummary.equipment_tags.map((tag, idx) => (
                    <code key={idx} className="cml-tag-badge">{tag}</code>
                  ))}
                </div>
              </div>
            )}

            {ocrVisionSummary?.instrument_tags && ocrVisionSummary.instrument_tags.length > 0 && (
              <div className="visual-tags-section">
                <span className="visual-tags-label">INSTRUMENT TAGS:</span>
                <div className="visual-tags-group">
                  {ocrVisionSummary.instrument_tags.map((tag, idx) => (
                    <code key={idx} className="cml-tag-badge">{tag}</code>
                  ))}
                </div>
              </div>
            )}

            {ocrVisionSummary?.findings && ocrVisionSummary.findings.length > 0 && (
              <div className="visual-findings-list">
                {ocrVisionSummary.findings.map((f, idx) => (
                  <div key={idx} className="visual-finding-item">
                    <div className="visual-finding-header">
                      <span className="visual-finding-label">{f.label || f.finding_type || `Finding #${idx + 1}`}</span>
                      {f.confidence !== undefined && (
                        <span className="citation-match-tag">{Math.round(f.confidence * 100)}% CONF</span>
                      )}
                    </div>
                    <div className="visual-finding-desc">{f.description}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 4: Sovereign RAG Citations */}
        {activeTab === 'citations' && (
          <div className="evidence-card rag-citations-card">
            <div className="evidence-card-header">
              <div className="card-header-left">
                <FileText size={14} className="accent-icon" />
                <span className="card-heading">SOVEREIGN RAG CITATIONS ({citations.length})</span>
              </div>
              <span className="subtle-note">Dense Vector Match (Nomic 768-d)</span>
            </div>

            {citations.length > 2 && (
              <div className="citations-search-wrap">
                <Search size={13} className="search-icon-pos" />
                <input
                  type="text"
                  placeholder="Filter retrieved citations by keyword or section..."
                  value={filterText}
                  onChange={(e) => setFilterText(e.target.value)}
                  className="citations-search-input"
                />
              </div>
            )}

            {citations.length === 0 ? (
              <div className="empty-panel-state">
                <BookOpen size={24} className="empty-icon" />
                <div className="empty-title">No Citations Loaded Yet</div>
                <div className="empty-desc">
                  Submit a task to trigger dense semantic retrieval over local MRPL standard operating procedures.
                </div>
              </div>
            ) : (
              <div className="citations-list">
                {filtered.map((citation, index) => {
                  const chunkKey = citation.chunk_id || `chk-${index}`;
                  const isExpanded = expandedChunk === chunkKey;
                  const matchPct = citation.similarity_score
                    ? Math.round(citation.similarity_score * 100)
                    : null;

                  return (
                    <div key={chunkKey} className={`citation-card ${isExpanded ? 'is-expanded' : ''}`}>
                      <div
                        className="citation-card-summary"
                        onClick={() => setExpandedChunk(isExpanded ? null : chunkKey)}
                        role="button"
                        tabIndex={0}
                      >
                        <div className="citation-summary-left">
                          <span className="citation-provenance-ribbon">
                            P.{citation.page_number}
                          </span>
                          <span className="citation-source-doc">{citation.source_document}</span>
                        </div>

                        <div className="citation-summary-right">
                          {matchPct !== null && (
                            <span className="citation-match-tag">{matchPct}% MATCH</span>
                          )}
                          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="citation-card-detail">
                          <div className="citation-meta-tags">
                            <span><strong>Document:</strong> {citation.source_document}</span>
                            <span><strong>Page:</strong> {citation.page_number}</span>
                            {citation.chunk_id && (
                              <span><strong>Chunk ID:</strong> <code>{citation.chunk_id}</code></span>
                            )}
                            {citation.similarity_score !== undefined && citation.similarity_score !== null && (
                              <span><strong>Cosine Score:</strong> <code>{typeof citation.similarity_score === 'number' ? citation.similarity_score.toFixed(4) : citation.similarity_score}</code></span>
                            )}
                            <span className="badge-pill badge-neutral">
                              <CheckCircle2 size={10} />
                              <span>PROVENANCE: LOCAL ON-PREM CORPUS</span>
                            </span>
                          </div>
                          <div className="citation-quote-box">
                            &ldquo;{citation.text}&rdquo;
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
