import React, { useState } from 'react';
import { CitationSource, StructuredValidationReport } from '../types/agent';
import { RouteResponse } from '../types/api';
import { BookOpen, FileText, ChevronDown, ChevronUp, ShieldCheck, Search, Cpu, CheckCircle2 } from 'lucide-react';
import { ValidationGateFuseBox } from './ValidationGateFuseBox';
import { DataSourceBadge } from './DataSourceBadge';

interface EvidencePanelProps {
  citations: CitationSource[];
  summary?: string | null;
  routePreview?: RouteResponse | null;
  validationReport?: StructuredValidationReport | null;
  isRunning?: boolean;
  executionMode?: 'deterministic' | 'live';
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  citations,
  summary,
  routePreview,
  validationReport,
  isRunning = false,
  executionMode = 'deterministic',
}) => {
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

  return (
    <div className="workbench-panel evidence-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-header-title-group">
          <BookOpen size={16} className="panel-header-icon" />
          <div>
            <h2 className="panel-title">Evidence &amp; Invariants</h2>
            <span className="panel-subtitle">Gatekeeper &amp; RAG Citations</span>
          </div>
        </div>

        <div className="panel-header-badges">
          <DataSourceBadge
            source={hasCitations ? (isLive ? 'LIVE' : 'DEMO') : 'FALLBACK'}
            label={hasCitations ? (isLive ? 'LIVE LOCAL CORPUS' : 'DEMO — SYNTHETIC CORPUS') : 'NO EVIDENCE LOADED'}
          />
        </div>
      </div>

      <div className="panel-body-scroll">
        {/* Real-time Intent Routing Card */}
        {routePreview && (
          <div className="evidence-card route-evidence-card">
            <div className="evidence-card-header">
              <div className="card-header-left">
                <Cpu size={14} className="accent-icon" />
                <span className="card-heading">TASK INTENT ROUTER (LEVEL 0)</span>
              </div>
              <span className="badge-pill badge-neutral">
                {Math.round((routePreview.confidence ?? 0.98) * 100)}% CONFIDENCE
              </span>
            </div>

            <div className="route-attributes-grid">
              <div className="route-attr">
                <span className="attr-label">TASK TYPE:</span>
                <code className="attr-value">{routePreview.task_type || 'corrosion_audit'}</code>
              </div>
              <div className="route-attr">
                <span className="attr-label">TARGET CAPABILITY:</span>
                <code className="attr-value">{routePreview.capability || 'engineering_math'}</code>
              </div>
              <div className="route-attr">
                <span className="attr-label">ALLOCATED ROLE:</span>
                <code className="attr-value">{routePreview.model_role || 'reasoning'}</code>
              </div>
            </div>

            {routePreview.reason && (
              <div className="route-reason-row">
                <span className="reason-label">MATCHED RULE:</span>
                <span className="reason-text">{routePreview.reason}</span>
              </div>
            )}
          </div>
        )}

        {/* 12-Cell Status Grid (Fuse Box) */}
        <ValidationGateFuseBox report={validationReport} isRunning={isRunning} />

        {/* Sovereign RAG Citations Section */}
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
                          <span className="badge-pill badge-success">
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
      </div>
    </div>
  );
};
