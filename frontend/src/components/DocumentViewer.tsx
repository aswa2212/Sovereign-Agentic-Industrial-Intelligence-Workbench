import React, { useState, useRef } from 'react';
import { DocumentIngestionResult } from '../types/documents';
import { documentService } from '../services/documents';
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Layers,
  Hash,
  Clock,
  ChevronRight,
  Eye,
} from 'lucide-react';

interface DocumentViewerProps {
  documents: DocumentIngestionResult[];
  onUploadSuccess?: (doc: DocumentIngestionResult) => void;
  selectedDoc?: DocumentIngestionResult | null;
  onSelectDoc?: (doc: DocumentIngestionResult) => void;
  compact?: boolean;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documents,
  onUploadSuccess,
  selectedDoc,
  onSelectDoc,
  compact = false,
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [activePreviewDoc, setActivePreviewDoc] = useState<DocumentIngestionResult | null>(
    selectedDoc || (documents.length > 0 ? documents[0] : null)
  );

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (file: File) => {
    setIsUploading(true);
    setUploadError(null);
    try {
      const result = await documentService.uploadDocument(file);
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
      setActivePreviewDoc(result);
    } catch (err: any) {
      setUploadError(err.message || 'Document ingestion failed');
    } finally {
      setIsUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <FileText size={16} style={{ color: 'var(--accent-primary)' }} />
          <div>
            <div className="card-title">Document Management & OCR Ingestion</div>
            <div className="card-subtitle">
              Sovereign Ingestion • SHA-256 Content-Addressed Storage
            </div>
          </div>
        </div>

        <span className="badge badge-neutral">
          {documents.length} Document{documents.length === 1 ? '' : 's'}
        </span>
      </div>

      {/* Upload Dropzone */}
      <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-subtle)' }}>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? 'var(--accent-primary)' : 'var(--border-medium)'}`,
            borderRadius: 'var(--radius-md)',
            padding: compact ? '0.75rem' : '1.25rem',
            textAlign: 'center',
            cursor: 'pointer',
            background: dragOver ? 'var(--status-info-bg)' : 'var(--bg-surface-muted)',
            transition: 'border-color 0.15s ease',
          }}
          role="button"
          tabIndex={0}
          aria-label="Upload document for ingestion"
        >
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={(e) => e.target.files?.[0] && handleFileChange(e.target.files[0])}
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.txt"
          />

          <Upload
            size={compact ? 18 : 22}
            style={{ margin: '0 auto 0.375rem', color: 'var(--accent-primary)' }}
          />

          <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            {isUploading ? 'Ingesting and Extracting...' : 'Click or Drag Document to Ingest'}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Supports PDF (scanned/text), PNG, JPG, TIFF • Offline OCR & Table Extraction
          </div>
        </div>

        {uploadError && (
          <div
            style={{
              marginTop: '0.5rem',
              padding: '0.5rem',
              background: 'var(--status-error-bg)',
              border: '1px solid var(--status-error-border)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.75rem',
              color: 'var(--status-error-text)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
            }}
          >
            <AlertCircle size={13} />
            <span>{uploadError}</span>
          </div>
        )}
      </div>

      {/* Ingested Documents List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem 1rem' }}>
        <div
          style={{
            fontSize: '0.75rem',
            fontWeight: 600,
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '0.5rem',
          }}
        >
          Ingested Technical Documents
        </div>

        {documents.length === 0 ? (
          <div
            style={{
              padding: '2rem 1rem',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.8125rem',
            }}
          >
            No documents ingested yet. Upload an inspection report or P&ID to inspect.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {documents.map((doc) => {
              const isSelected = (selectedDoc?.sha256 === doc.sha256) || (activePreviewDoc?.sha256 === doc.sha256);
              const sizeKb = (doc.size_bytes / 1024).toFixed(1);

              return (
                <div
                  key={doc.sha256}
                  onClick={() => {
                    setActivePreviewDoc(doc);
                    if (onSelectDoc) onSelectDoc(doc);
                  }}
                  style={{
                    border: `1px solid ${isSelected ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.625rem 0.75rem',
                    cursor: 'pointer',
                    background: isSelected ? 'var(--status-info-bg)' : 'var(--bg-surface)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.375rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
                      <FileText size={14} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
                      <span
                        style={{
                          fontSize: '0.8125rem',
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                        title={doc.filename}
                      >
                        {doc.filename}
                      </span>
                    </div>

                    <span className="badge badge-success" style={{ fontSize: '0.6875rem' }}>
                      <CheckCircle2 size={11} style={{ marginRight: '3px' }} />
                      Processed
                    </span>
                  </div>

                  {/* Technical Information Row */}
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      alignItems: 'center',
                      gap: '0.5rem',
                      fontSize: '0.7rem',
                      color: 'var(--text-muted)',
                    }}
                  >
                    <span className="code-badge">{doc.content_type.split('/')[1]?.toUpperCase() || 'PDF'}</span>
                    <span className="code-badge">{sizeKb} KB</span>
                    <span>
                      <Layers size={11} style={{ verticalAlign: '-1px', marginRight: '2px' }} />
                      {doc.page_count} Pages
                    </span>
                    <span>
                      <FileSpreadsheet size={11} style={{ verticalAlign: '-1px', marginRight: '2px' }} />
                      {doc.table_count} Tables
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)' }} title={`SHA-256: ${doc.sha256}`}>
                      SHA: {doc.sha256.slice(0, 10)}...
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Selected Document Metadata Inspection */}
      {activePreviewDoc && (
        <div
          style={{
            borderTop: '1px solid var(--border-subtle)',
            padding: '0.75rem 1rem',
            background: 'var(--bg-surface-muted)',
            fontSize: '0.75rem',
          }}
        >
          <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.375rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Eye size={13} /> Active Selection Inspection: {activePreviewDoc.filename}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.25rem', color: 'var(--text-secondary)' }}>
            <div>
              <span style={{ fontWeight: 600 }}>Pages:</span> {activePreviewDoc.page_count}
            </div>
            <div>
              <span style={{ fontWeight: 600 }}>Tables Extracted:</span> {activePreviewDoc.table_count}
            </div>
            <div style={{ gridColumn: '1 / -1', fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              SHA-256: {activePreviewDoc.sha256}
            </div>
            {activePreviewDoc.extraction_summary && (
              <div style={{ gridColumn: '1 / -1', marginTop: '2px', color: 'var(--text-muted)' }}>
                {activePreviewDoc.extraction_summary}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
