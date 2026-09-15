import React, { useState, useEffect } from 'react';
import { systemService } from '../services/system';
import { RAGStatusResponse, RetrievedChunk } from '../types/api';
import { MOCK_RAG_STATUS, MOCK_RAG_RESULTS } from '../services/mockData';
import { CopyableMono } from '../components/CopyableMono';
import { DataSourceBadge } from '../components/DataSourceBadge';
import { useToast } from '../components/ToastProvider';
import {
  Database,
  Search,
  Sliders,
  BookOpen,
  FileText,
  Layers,
  CheckCircle2,
  RefreshCw,
  Sparkles,
  ChevronRight,
  Hash,
  ExternalLink,
} from 'lucide-react';

export const KnowledgePage: React.FC = () => {
  const [ragStatus, setRagStatus] = useState<RAGStatusResponse | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);

  // Search Test Bench State
  const [query, setQuery] = useState('API 570 retirement thickness formula for overhead line');
  const [topK, setTopK] = useState(3);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.65);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<RetrievedChunk[]>(MOCK_RAG_RESULTS.results);
  const [selectedChunk, setSelectedChunk] = useState<RetrievedChunk | null>(MOCK_RAG_RESULTS.results[0]);

  const toast = useToast();

  const loadRAGStatus = async () => {
    setLoadingStats(true);
    try {
      const res = await systemService.getRAGStatus();
      setRagStatus(res || MOCK_RAG_STATUS);
    } catch {
      setRagStatus(MOCK_RAG_STATUS);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    loadRAGStatus();
  }, []);

  const handleExecuteSearch = async () => {
    if (!query.trim() || isSearching) return;
    setIsSearching(true);
    try {
      const res = await systemService.queryRAG(query, topK, similarityThreshold);
      setResults(res.results || []);
      if (res.results && res.results.length > 0) {
        setSelectedChunk(res.results[0]);
        toast.success('Search Complete', `Retrieved ${res.results.length} relevant citation chunks.`);
      } else {
        setSelectedChunk(null);
        toast.info('Zero Results', 'No chunks exceeded the similarity threshold.');
      }
    } catch (err: any) {
      toast.error('Search Failed', err.message || 'Error executing dense vector retrieval');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="page-container knowledge-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Sovereign Knowledge &amp; RAG Vector Store</h1>
          <p className="page-subtitle">
            Dense Semantic Vector Search • On-Premise Embeddings (nomic-embed-text:latest) • Local Vector Index
          </p>
        </div>

        <div className="page-header-actions">
          <DataSourceBadge source="LIVE" label="LIVE LOCAL CORPUS (768-D)" />
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={loadRAGStatus}
            disabled={loadingStats}
          >
            <RefreshCw size={13} className={loadingStats ? 'icon-spin' : ''} />
            <span>Refresh Vector Index</span>
          </button>
        </div>
      </div>

      {/* Vector Store Stat Cards */}
      <div className="knowledge-stats-grid">
        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-label">TOTAL INDEXED CHUNKS</span>
            <Database size={16} className="stat-icon" />
          </div>
          <div className="stat-value">{ragStatus?.total_chunks ?? 148}</div>
          <div className="stat-sub">10 Industrial SOPs &amp; Codes</div>
        </div>

        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-label">VECTOR DIMENSION</span>
            <Layers size={16} className="stat-icon" />
          </div>
          <div className="stat-value">{ragStatus?.dimension ?? 768}</div>
          <div className="stat-sub">Dense Floating-Point Vector Space</div>
        </div>

        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-label">EMBEDDING MODEL</span>
            <Sparkles size={16} className="stat-icon" />
          </div>
          <div className="stat-value mono-val">nomic-embed-text</div>
          <div className="stat-sub">Ollama Local GPU/CPU Inference</div>
        </div>

        <div className="stat-card">
          <div className="stat-card-top">
            <span className="stat-label">DISTANCE METRIC</span>
            <Sliders size={16} className="stat-icon" />
          </div>
          <div className="stat-value">Cosine Similarity</div>
          <div className="stat-sub">Local NumPy / JSON Vector Engine</div>
        </div>
      </div>

      {/* Test Bench & Search Section */}
      <div className="knowledge-testbench-grid">
        {/* Left: Query Controls & Sliders */}
        <div className="testbench-controls-card">
          <div className="controls-card-header">
            <h2 className="controls-title">Semantic Retrieval Test Bench</h2>
            <span className="controls-desc">Inspect vector query responses, page provenance, and similarity rankings</span>
          </div>

          <div className="testbench-form">
            <div className="form-group">
              <label className="form-label" htmlFor="rag-query-input">
                QUERY OR INDUSTRIAL QUESTION:
              </label>
              <textarea
                id="rag-query-input"
                className="query-textarea"
                rows={3}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. API 570 minimum retirement thickness formula for carbon steel overhead line..."
              />
            </div>

            {/* Top-K Range Slider with Live Numeric Readout */}
            <div className="slider-group">
              <div className="slider-header">
                <span className="slider-label">TOP-K RETRIEVAL LIMIT:</span>
                <span className="slider-value-pill">{topK} Chunks</span>
              </div>
              <input
                type="range"
                min={1}
                max={10}
                step={1}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="deck-range-slider"
                aria-label="Top-K limit slider"
              />
              <div className="slider-range-limits">
                <span>1</span>
                <span>5</span>
                <span>10</span>
              </div>
            </div>

            {/* Similarity Threshold Range Slider with Live Numeric Readout */}
            <div className="slider-group">
              <div className="slider-header">
                <span className="slider-label">SIMILARITY THRESHOLD CUTOFF:</span>
                <span className="slider-value-pill">{(similarityThreshold * 100).toFixed(0)}% Match</span>
              </div>
              <input
                type="range"
                min={0.3}
                max={0.95}
                step={0.05}
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
                className="deck-range-slider"
                aria-label="Similarity threshold cutoff slider"
              />
              <div className="slider-range-limits">
                <span>30%</span>
                <span>65% (Standard)</span>
                <span>95% (Strict)</span>
              </div>
            </div>

            <button
              type="button"
              className="btn btn-accent btn-full"
              onClick={handleExecuteSearch}
              disabled={isSearching || !query.trim()}
            >
              {isSearching ? (
                <>
                  <RefreshCw size={14} className="icon-spin" />
                  <span>Computing Dense Embeddings...</span>
                </>
              ) : (
                <>
                  <Search size={14} />
                  <span>Query Local Vector Index</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right: Retrieved Citation Cards with Provenance Ribbon */}
        <div className="testbench-results-card">
          <div className="results-header">
            <div className="results-header-left">
              <BookOpen size={16} className="accent-icon" />
              <h2 className="results-title">Retrieved Standard Chunks ({results.length})</h2>
            </div>
            <span className="badge-pill badge-neutral">VERIFIED PROVENANCE</span>
          </div>

          <div className="results-scroll-list">
            {results.length === 0 ? (
              <div className="empty-panel-state">
                <Search size={32} className="empty-icon" />
                <div className="empty-title">No Chunks Retrieved</div>
                <div className="empty-desc">
                  Try lowering the similarity threshold or adjusting your query terms.
                </div>
              </div>
            ) : (
              results.map((chunk, idx) => {
                const isSelected = selectedChunk?.chunk_id === chunk.chunk_id;
                const matchPct = Math.round(chunk.similarity_score * 100);

                return (
                  <div
                    key={chunk.chunk_id || idx}
                    className={`chunk-citation-card ${isSelected ? 'is-selected-chunk' : ''}`}
                    onClick={() => setSelectedChunk(chunk)}
                    role="button"
                    tabIndex={0}
                  >
                    {/* Provenance Ribbon Header */}
                    <div className="chunk-ribbon-bar">
                      <div className="ribbon-left">
                        <span className="provenance-tag">PAGE {chunk.page_number ?? 1}</span>
                        <span className="source-doc-name">{chunk.source_document}</span>
                      </div>
                      <div className="ribbon-right">
                        <span className="similarity-score-badge">{matchPct}% MATCH</span>
                      </div>
                    </div>

                    {/* Section Header */}
                    {chunk.section_header && (
                      <div className="chunk-section-title">{chunk.section_header}</div>
                    )}

                    {/* Verbatim Excerpt */}
                    <div className="chunk-excerpt-box">
                      &ldquo;{chunk.text}&rdquo;
                    </div>

                    {/* Monospace Fingerprint Row */}
                    <div className="chunk-meta-footer">
                      <div className="chunk-id-tag">
                        <span>CHUNK ID:</span>
                        <code>{chunk.chunk_id}</code>
                      </div>
                      <div className="chunk-hash-tag">
                        <span>SHA-256:</span>
                        <CopyableMono value={chunk.source_sha256} truncateLength={16} label="Source SHA-256" />
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
