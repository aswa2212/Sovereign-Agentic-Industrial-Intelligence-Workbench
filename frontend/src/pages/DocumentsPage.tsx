import React, { useState } from 'react';
import { DocumentViewer } from '../components/DocumentViewer';
import { DocumentIngestionResult } from '../types/documents';
import { FileText, ShieldCheck, Database, Layers } from 'lucide-react';

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentIngestionResult[]>([
    {
      sha256: 'a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0',
      filename: 'SOP-MRPL-PIP-001.pdf',
      content_type: 'application/pdf',
      size_bytes: 412984,
      page_count: 14,
      table_count: 6,
      storage_path: 'knowledge/default/SOP-MRPL-PIP-001.pdf',
      extraction_summary:
        'Standard Operating Procedure for Ultrasonic Thickness Gauging and corrosion retirement criteria for MRPL Phase I/II units.',
    },
    {
      sha256: '8f4a21b392bd01754890cdef1234567890abcdef1234567890abcdef12345678',
      filename: 'C101_UTG_Inspection_Report.pdf',
      content_type: 'application/pdf',
      size_bytes: 285400,
      page_count: 8,
      table_count: 4,
      storage_path: 'uploads/C101_UTG_Inspection_Report.pdf',
      extraction_summary:
        'Non-destructive testing inspection report for C-101 atmospheric distillation tower shell rings and nozzles.',
    },
  ]);

  const [selectedDoc, setSelectedDoc] = useState<DocumentIngestionResult | null>(documents[0]);

  const totalPages = documents.reduce((acc, d) => acc + d.page_count, 0);
  const totalTables = documents.reduce((acc, d) => acc + d.table_count, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header Banner */}
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <FileText size={18} style={{ color: 'var(--accent-primary)' }} />
            <div>
              <div className="card-title">Technical Document Repository & Ingestion</div>
              <div className="card-subtitle">
                Air-Gapped Content Extraction • Deterministic SHA-256 Storage • PDF/Table OCR
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className="badge badge-success">
              <ShieldCheck size={12} style={{ marginRight: '4px' }} />
              Local Storage Enforced
            </span>
          </div>
        </div>

        {/* Repository Stats */}
        <div
          style={{
            padding: '0.75rem 1rem',
            background: 'var(--bg-surface-muted)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: '1rem',
            fontSize: '0.8125rem',
          }}
        >
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              DOCUMENTS STORED
            </div>
            <div style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {documents.length}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              TOTAL PAGES INDEXED
            </div>
            <div style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {totalPages}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              TABLES EXTRACTED
            </div>
            <div style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {totalTables}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              INGESTION ENGINE
            </div>
            <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--accent-secondary)' }}>
              PyMuPDF + Tesseract OCR
            </div>
          </div>
        </div>
      </div>

      {/* Main Document Viewer Component */}
      <div style={{ minHeight: '520px' }}>
        <DocumentViewer
          documents={documents}
          selectedDoc={selectedDoc}
          onSelectDoc={setSelectedDoc}
          onUploadSuccess={(newDoc) => {
            setDocuments((prev) => [newDoc, ...prev]);
            setSelectedDoc(newDoc);
          }}
        />
      </div>
    </div>
  );
};
