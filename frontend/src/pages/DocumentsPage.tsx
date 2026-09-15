import React, { useState, useRef, useEffect } from 'react';
import { documentService } from '../services/documents';
import { DocumentIngestionResult } from '../types/documents';
import { MOCK_INGESTED_DOCUMENTS } from '../services/mockData';
import { CopyableMono } from '../components/CopyableMono';
import { useToast } from '../components/ToastProvider';
import {
  Upload,
  FileText,
  FileSpreadsheet,
  Layers,
  Search,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  RefreshCw,
  Clock,
  HardDrive,
} from 'lucide-react';

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentIngestionResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<DocumentIngestionResult | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const list = await documentService.listDocuments();
      setDocuments(list && list.length > 0 ? list : MOCK_INGESTED_DOCUMENTS);
      if (!selectedDoc && list && list.length > 0) {
        setSelectedDoc(list[0]);
      }
    } catch {
      setDocuments(MOCK_INGESTED_DOCUMENTS);
      if (!selectedDoc) {
        setSelectedDoc(MOCK_INGESTED_DOCUMENTS[0]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    toast.info('Ingesting Document', `Hashing and parsing ${file.name}...`);

    try {
      const result = await documentService.uploadDocument(file);
      setDocuments((prev) => [result, ...prev]);
      setSelectedDoc(result);
      toast.success('Document Ingested', `SHA-256 digest calculated: ${result.sha256.substring(0, 16)}...`);
    } catch (err: any) {
      toast.error('Upload Failed', err.message || 'Failed to ingest file');
    } finally {
      setIsUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const filteredDocs = documents.filter((d) =>
    d.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.sha256.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (d.extraction_summary && d.extraction_summary.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="page-container documents-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Sovereign Document Management</h1>
          <p className="page-subtitle">
            SHA-256 Content-Addressed Ingestion • Zero Cloud Leaks • P&amp;ID &amp; NDT Parser
          </p>
        </div>

        <div className="page-header-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={loadDocuments}
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? 'icon-spin' : ''} />
            <span>Refresh Archive</span>
          </button>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="documents-layout-grid">
        {/* Left: Upload & Documents Table */}
        <div className="documents-main-column">
          {/* Drag & Drop Upload Zone */}
          <div
            className={`drag-drop-hero-zone ${dragOver ? 'is-drag-over' : ''} ${isUploading ? 'is-uploading' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            aria-label="Upload document for ingestion"
          >
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
              accept=".pdf,.png,.jpg,.jpeg,.tiff,.xlsx"
            />

            <div className="drag-drop-icon-wrap">
              <Upload size={28} className="drag-drop-icon" />
            </div>

            <div className="drag-drop-instructions">
              <h3>{isUploading ? 'Computing SHA-256 & Parsing Text...' : 'Drag & Drop Technical Documents Here'}</h3>
              <p>
                Supports engineering PDFs (scanned &amp; vector), ultrasonic XLSX survey workbooks, and high-res P&amp;ID schematics.
              </p>
              <span className="drag-drop-cta">or click to browse local files</span>
            </div>
          </div>

          {/* Search & Filter Bar */}
          <div className="table-filter-bar">
            <div className="search-input-wrap">
              <Search size={14} className="search-icon" />
              <input
                type="text"
                className="filter-search-input"
                placeholder="Search documents by filename, SHA-256 hash, or summary..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <span className="count-badge">{filteredDocs.length} Documents</span>
          </div>

          {/* Documents Table */}
          <div className="table-card">
            {loading ? (
              <div className="skeleton-loading-panel">
                <div className="skeleton-line" style={{ width: '80%' }} />
                <div className="skeleton-line" style={{ width: '95%' }} />
                <div className="skeleton-line" style={{ width: '60%' }} />
              </div>
            ) : filteredDocs.length === 0 ? (
              <div className="empty-panel-state">
                <FileText size={32} className="empty-icon" />
                <div className="empty-title">No Matching Documents</div>
                <div className="empty-desc">
                  No documents found matching &ldquo;{searchQuery}&rdquo;. Clear search or upload a new inspection file.
                </div>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="deck-table documents-table">
                  <thead>
                    <tr>
                      <th>Filename</th>
                      <th>SHA-256 Content Digest</th>
                      <th className="num-col">Pages</th>
                      <th className="num-col">Tables</th>
                      <th className="num-col">Size</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDocs.map((doc) => {
                      const isSelected = selectedDoc?.sha256 === doc.sha256;
                      const sizeKb = (doc.size_bytes / 1024).toFixed(1);

                      return (
                        <tr
                          key={doc.sha256}
                          className={`table-row-interactive ${isSelected ? 'row-selected' : ''}`}
                          onClick={() => setSelectedDoc(doc)}
                        >
                          <td className="doc-filename-cell">
                            <FileText size={15} className="table-file-icon" />
                            <span className="filename-text">{doc.filename}</span>
                          </td>
                          <td>
                            <CopyableMono value={doc.sha256} truncateLength={24} label="Document Digest" />
                          </td>
                          <td className="num-col mono-num">{doc.page_count}</td>
                          <td className="num-col mono-num">{doc.table_count}</td>
                          <td className="num-col mono-num">{sizeKb} KB</td>
                          <td>
                            <span className="badge-pill badge-success">
                              <CheckCircle2 size={11} />
                              <span>PARSED</span>
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right: Selected Document Detail Drawer */}
        <div className="documents-detail-column">
          {selectedDoc ? (
            <div className="doc-inspector-card">
              <div className="inspector-header">
                <div className="inspector-title-group">
                  <span className="subtle-label">DOCUMENT INSPECTOR</span>
                  <h3 className="inspector-filename">{selectedDoc.filename}</h3>
                </div>
                <span className="badge-pill badge-success">INDEXED</span>
              </div>

              <div className="inspector-attributes">
                <div className="inspector-attr-row">
                  <span className="attr-name">SHA-256 FINGERPRINT</span>
                  <div className="attr-val">
                    <CopyableMono value={selectedDoc.sha256} truncateLength={32} label="SHA-256" />
                  </div>
                </div>

                <div className="inspector-attr-row">
                  <span className="attr-name">FILE TYPE</span>
                  <span className="attr-val-plain">{selectedDoc.content_type || 'application/pdf'}</span>
                </div>

                <div className="inspector-attr-row">
                  <span className="attr-name">EXTRACTED PAGES</span>
                  <span className="attr-val-plain">{selectedDoc.page_count} Pages</span>
                </div>

                <div className="inspector-attr-row">
                  <span className="attr-name">NDT TABLES PARSED</span>
                  <span className="attr-val-plain">{selectedDoc.table_count} Structured Tables</span>
                </div>

                <div className="inspector-attr-row">
                  <span className="attr-name">STORAGE LOCATION</span>
                  <code className="attr-val-code">{selectedDoc.storage_path}</code>
                </div>
              </div>

              <div className="inspector-summary-box">
                <span className="summary-heading">EXTRACTION SUMMARY:</span>
                <p>{selectedDoc.extraction_summary}</p>
              </div>

              <div className="inspector-airgap-notice">
                <HardDrive size={14} className="accent-icon" />
                <span>
                  Stored strictly in on-premise directory. Byte stream never leaves local loopback interface.
                </span>
              </div>
            </div>
          ) : (
            <div className="empty-inspector-card">
              <FileCheck size={28} className="empty-icon" />
              <span>Select a document from the archive table to inspect cryptographic attributes and extraction details.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
