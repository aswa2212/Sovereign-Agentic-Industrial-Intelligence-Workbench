import React, { useEffect, useState } from 'react';
import { systemService } from '../services/system';
import { RAGStatusResponse, RetrievedChunk } from '../types/api';
import { BookOpen, Search, ShieldCheck, Database, RefreshCw, Layers, CheckCircle2, AlertCircle, FileText } from 'lucide-react';

export const KnowledgePage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ragStatus, setRagStatus] = useState<RAGStatusResponse | null>(null);

  // Live Query State
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [queryResults, setQueryResults] = useState<RetrievedChunk[]>([]);
  const [hasQueried, setHasQueried] = useState(false);
  const [selectedChunk, setSelectedChunk] = useState<RetrievedChunk | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const status = await systemService.getRAGStatus();
      setRagStatus(status);
    } catch (err: any) {
      setError(err.message || 'Failed to query RAG vector store status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setError(null);
    try {
      const resp = await systemService.queryRAG(searchQuery, 4, 0.50);
      setQueryResults(resp.results || []);
      setHasQueried(true);
      if (resp.results && resp.results.length > 0) {
        setSelectedChunk(resp.results[0]);
      } else {
        setSelectedChunk(null);
      }
    } catch (err: any) {
      setError(err.message || 'Knowledge query failed');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <BookOpen size={18} style={{ color: 'var(--accent-primary)' }} />
            <div>
              <div className="card-title">Sovereign RAG Knowledge Base & Vector Store</div>
              <div className="card-subtitle">
                Local Dense Retrieval • Semantic Chunking • Immutable Index Storage
              </div>
            </div>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={fetchStatus}
            disabled={loading}
            title="Refresh RAG index telemetry"
          >
            <RefreshCw size={13} className={loading ? 'icon-spin' : ''} />
            Refresh Telemetry
          </button>
        </div>

        {/* Live Vector Index Telemetry Metrics */}
        <div
          style={{
            padding: '0.75rem 1rem',
            background: 'var(--bg-surface-muted)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1rem',
            fontSize: '0.8125rem',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>INDEX ENGINE</div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {ragStatus?.backend || 'Local NumPy JSON'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>EMBEDDING MODEL</div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--accent-primary)' }}>
              {ragStatus?.embedding_provider || 'all-MiniLM-L6-v2'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>DIMENSIONALITY</div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {ragStatus?.dimension ? `${ragStatus.dimension} Dimensions` : '384 Dimensions'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL CHUNKS INDEXED</div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--status-success-text)' }}>
              {ragStatus?.total_chunks ?? 0} Chunks
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>INDEXED STANDARDS</div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {ragStatus?.indexed_documents_count ?? 0} Documents
            </div>
          </div>
        </div>

        {/* Index Location Banner */}
        <div style={{ padding: '0.5rem 1rem', fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Database size={13} style={{ color: 'var(--text-muted)' }} />
          <span>Index ID: <strong style={{ color: 'var(--text-primary)' }}>{ragStatus?.index_id || 'default'}</strong></span>
          <span style={{ color: 'var(--border-medium)' }}>•</span>
          <span>Storage: <code style={{ fontFamily: 'var(--font-mono)' }}>{ragStatus?.storage_path || 'backend/data/knowledge/default'}</code></span>
          <span style={{ color: 'var(--border-medium)' }}>•</span>
          <span className="badge badge-success" style={{ fontSize: '0.6875rem' }}>
            <ShieldCheck size={11} style={{ marginRight: '3px' }} />
            {ragStatus?.status?.toUpperCase() || 'READY'}
          </span>
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: '0.75rem 1rem',
            background: 'var(--status-error-bg)',
            border: '1px solid var(--status-error-border)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.8125rem',
            color: 'var(--status-error-text)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Live Semantic Retrieval Probe */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">Live Sovereign Vector Retrieval Probe</div>
          <div className="card-subtitle">
            Query local dense embeddings directly against indexed refinery operating standards
          </div>
        </div>

        <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-subtle)' }}>
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem' }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <Search
                size={14}
                style={{ position: 'absolute', left: '10px', top: '11px', color: 'var(--text-muted)' }}
              />
              <input
                type="text"
                className="form-input"
                style={{ paddingLeft: '32px' }}
                placeholder="Enter query to retrieve verified chunks (e.g. 'corrosion rate calculation' or 'minimum retirement thickness')..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSearching || !searchQuery.trim()}
              style={{ minWidth: '120px' }}
            >
              {isSearching ? 'Searching...' : 'Run Query'}
            </button>
          </form>
        </div>

        {/* Query Results & Verified Text Inspector */}
        <div style={{ padding: '1rem' }}>
          {!hasQueried ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
              <Layers size={32} style={{ margin: '0 auto 0.5rem', opacity: 0.4 }} />
              <div>No search performed yet in this session.</div>
              <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>
                Type an engineering query above to query the live on-prem vector store ({ragStatus?.total_chunks ?? 0} indexed chunks available).
              </div>
            </div>
          ) : queryResults.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
              <AlertCircle size={28} style={{ margin: '0 auto 0.5rem', opacity: 0.5 }} />
              <div>No chunks matched the similarity threshold for "{searchQuery}".</div>
              <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>
                The sovereign RAG engine enforces a 0.50 cosine threshold guardrail to prevent irrelevant evidence injection.
              </div>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 1.5fr', gap: '1rem', alignItems: 'start' }}>
              {/* Candidates List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Matched Knowledge Chunks ({queryResults.length})
                </div>
                {queryResults.map((chunk) => {
                  const isSelected = selectedChunk?.chunk_id === chunk.chunk_id;
                  const scorePct = Math.round(chunk.similarity_score * 100);

                  return (
                    <div
                      key={chunk.chunk_id}
                      onClick={() => setSelectedChunk(chunk)}
                      style={{
                        padding: '0.625rem 0.75rem',
                        borderRadius: 'var(--radius-sm)',
                        border: `1px solid ${isSelected ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
                        background: isSelected ? 'var(--status-info-bg)' : 'var(--bg-surface)',
                        cursor: 'pointer',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                          {chunk.section_header || chunk.source_document}
                        </span>
                        <span className="badge badge-success" style={{ fontSize: '0.6875rem' }}>
                          {scorePct}% Match
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '3px', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        <span>P. {chunk.page_number || '—'}</span>
                        <span style={{ fontFamily: 'var(--font-mono)' }}>{chunk.chunk_id}</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Selected Chunk Content Preview */}
              {selectedChunk && (
                <div className="card" style={{ background: 'var(--bg-surface-muted)', padding: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                      <FileText size={14} style={{ color: 'var(--accent-primary)' }} />
                      <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {selectedChunk.source_document}
                      </span>
                      {selectedChunk.page_number && <span className="code-badge">Page {selectedChunk.page_number}</span>}
                    </div>
                    <span className="code-badge">{selectedChunk.chunk_id}</span>
                  </div>

                  <div
                    style={{
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '0.75rem',
                      fontSize: '0.8125rem',
                      lineHeight: 1.6,
                      color: 'var(--text-primary)',
                      whiteSpace: 'pre-wrap',
                      maxHeight: '260px',
                      overflowY: 'auto',
                      borderLeft: '3px solid var(--accent-primary)',
                    }}
                  >
                    {selectedChunk.text}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    <span>Tokens: {selectedChunk.token_count}</span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>SHA: {selectedChunk.content_sha256.slice(0, 16)}...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
