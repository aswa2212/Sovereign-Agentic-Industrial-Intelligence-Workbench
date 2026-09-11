import React, { useState } from 'react';
import { CitationSource } from '../types/agent';
import { BookOpen, FileText, ChevronDown, ChevronUp, ShieldCheck, Search } from 'lucide-react';

interface EvidencePanelProps {
  citations: CitationSource[];
  summary?: string | null;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ citations, summary }) => {
  const [expandedChunk, setExpandedChunk] = useState<string | null>(
    citations.length > 0 ? citations[0].chunk_id : null
  );
  const [filterText, setFilterText] = useState('');

  const filtered = citations.filter(
    (c) =>
      c.source_document.toLowerCase().includes(filterText.toLowerCase()) ||
      c.text.toLowerCase().includes(filterText.toLowerCase()) ||
      c.chunk_id.toLowerCase().includes(filterText.toLowerCase())
  );

  return (
    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <BookOpen size={16} style={{ color: 'var(--accent-primary)' }} />
          <div>
            <div className="card-title">Retrieved Knowledge & Evidence Chain</div>
            <div className="card-subtitle">
              Verified Citations • Sovereign RAG Vector Store
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span className="badge badge-success">
            <ShieldCheck size={12} style={{ marginRight: '4px' }} />
            {citations.length} Grounded Source{citations.length === 1 ? '' : 's'}
          </span>
        </div>
      </div>

      {/* Industrial Trust Summary Banner */}
      {summary && (
        <div
          style={{
            padding: '0.75rem 1rem',
            background: 'var(--bg-surface-muted)',
            borderBottom: '1px solid var(--border-subtle)',
            fontSize: '0.8125rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
          }}
        >
          <span style={{ fontWeight: 600, color: 'var(--text-primary)', marginRight: '6px' }}>
            SYNTHESIS FINDING:
          </span>
          {summary}
        </div>
      )}

      {/* Search & Filter */}
      {citations.length > 3 && (
        <div style={{ padding: '0.5rem 1rem', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ position: 'relative' }}>
            <Search
              size={13}
              style={{ position: 'absolute', left: '8px', top: '9px', color: 'var(--text-muted)' }}
            />
            <input
              type="text"
              placeholder="Filter evidence snippets by keyword or source..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="form-input"
              style={{ paddingLeft: '28px', fontSize: '0.8125rem' }}
            />
          </div>
        </div>
      )}

      {/* Citations List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem 1rem' }}>
        {citations.length === 0 ? (
          <div
            style={{
              padding: '2.5rem 1rem',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.8125rem',
            }}
          >
            <BookOpen size={28} style={{ margin: '0 auto 0.5rem', opacity: 0.4 }} />
            <div>No retrieved citations for current state.</div>
            <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>
              Evidence retrieved during agent EXECUTE step will be grounded with exact source and page numbers.
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {filtered.map((citation, index) => {
              const isExpanded = expandedChunk === citation.chunk_id;
              const relevancePercent = citation.similarity_score
                ? Math.round(citation.similarity_score * 100)
                : null;

              return (
                <div
                  key={`${citation.chunk_id}-${index}`}
                  className="card"
                  style={{
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-surface)',
                    boxShadow: 'var(--shadow-sm)',
                  }}
                >
                  <div
                    onClick={() => setExpandedChunk(isExpanded ? null : citation.chunk_id)}
                    style={{
                      padding: '0.625rem 0.875rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      background: isExpanded ? 'var(--bg-surface-muted)' : 'var(--bg-surface)',
                      borderBottom: isExpanded ? '1px solid var(--border-subtle)' : 'none',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
                      <FileText size={14} style={{ color: 'var(--accent-secondary)', flexShrink: 0 }} />
                      <div style={{ minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: '0.8125rem',
                            fontWeight: 600,
                            color: 'var(--text-primary)',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {citation.source_document}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
                      <span className="code-badge">P. {citation.page_number}</span>
                      <span className="code-badge">{citation.chunk_id}</span>
                      {relevancePercent !== null && (
                        <span
                          className="badge"
                          style={{
                            background: '#eff6ff',
                            color: '#1e40af',
                            border: '1px solid #bfdbfe',
                            fontSize: '0.7rem',
                            padding: '2px 6px',
                          }}
                          title="Vector cosine similarity score against task embedding"
                        >
                          {relevancePercent}% MATCH
                        </span>
                      )}
                      {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </div>
                  </div>

                  {isExpanded && (
                    <div style={{ padding: '0.75rem 0.875rem', fontSize: '0.8125rem' }}>
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                          gap: '0.5rem',
                          marginBottom: '0.625rem',
                          fontSize: '0.75rem',
                          color: 'var(--text-muted)',
                        }}
                      >
                        <div>
                          <span style={{ fontWeight: 600 }}>SOURCE:</span> {citation.source_document}
                        </div>
                        <div>
                          <span style={{ fontWeight: 600 }}>PAGE:</span> {citation.page_number}
                        </div>
                        <div>
                          <span style={{ fontWeight: 600 }}>CHUNK:</span>{' '}
                          <span style={{ fontFamily: 'var(--font-mono)' }}>{citation.chunk_id}</span>
                        </div>
                        {citation.similarity_score && (
                          <div>
                            <span style={{ fontWeight: 600 }}>SIMILARITY:</span>{' '}
                            {citation.similarity_score.toFixed(4)}
                          </div>
                        )}
                      </div>

                      <div
                        style={{
                          background: 'var(--bg-surface-muted)',
                          padding: '0.625rem 0.75rem',
                          borderRadius: 'var(--radius-sm)',
                          borderLeft: '3px solid var(--accent-primary)',
                          fontFamily: 'inherit',
                          lineHeight: 1.5,
                          color: 'var(--text-secondary)',
                          whiteSpace: 'pre-wrap',
                          maxHeight: '180px',
                          overflowY: 'auto',
                        }}
                      >
                        {citation.text}
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
  );
};
