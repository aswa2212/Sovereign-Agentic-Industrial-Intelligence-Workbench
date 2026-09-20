import React, { useState, useRef, useEffect } from 'react';
import { DocumentIngestionResult } from '../types/documents';
import { documentService } from '../services/documents';
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Layers,
  ChevronRight,
  Eye,
  Table,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { CopyableMono } from './CopyableMono';

interface DocumentViewerProps {
  documents: DocumentIngestionResult[];
  onUploadSuccess?: (doc: DocumentIngestionResult, file?: File) => void;
  selectedDoc?: DocumentIngestionResult | null;
  onSelectDoc?: (doc: DocumentIngestionResult) => void;
  compact?: boolean;
  isFocused?: boolean;
  onToggleFocus?: () => void;
  selectedEquipmentId?: string;
}

interface ThicknessSurveyRow {
  cml_tag: string;
  location_desc: string;
  nominal_mm: number;
  actual_mm: number;
  loss_mm: number;
  date_measured: string;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documents,
  onUploadSuccess,
  selectedDoc,
  onSelectDoc,
  compact = false,
  isFocused = false,
  onToggleFocus,
  selectedEquipmentId,
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [activePreviewDoc, setActivePreviewDoc] = useState<DocumentIngestionResult | null>(
    selectedDoc || null
  );
  const [activeTab, setActiveTab] = useState<'survey' | 'params' | 'archive'>('survey');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync active preview and file input state with selectedDoc (handles Workbench dedicated reset)
  useEffect(() => {
    setActivePreviewDoc(selectedDoc || null);
    if (!selectedDoc && fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    if (!selectedDoc) {
      setActiveTab('survey');
    }
  }, [selectedDoc]);

  const handleFileChange = async (file: File) => {
    setIsUploading(true);
    setUploadError(null);
    try {
      const result = await documentService.uploadDocument(file);
      if (onUploadSuccess) {
        onUploadSuccess(result, file);
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

  const activeDoc = selectedDoc || activePreviewDoc || null;

  return (
    <div className="workbench-panel document-viewer-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-header-title-group">
          <FileText size={16} className="panel-header-icon" />
          <div>
            <h2 className="panel-title">Source Evidence &amp; NDT Gauging</h2>
            <span className="panel-subtitle">Inspection Reports • Ultrasonic Wall Surveys • P&amp;ID Schematics</span>
          </div>
        </div>

        <div className="panel-header-badges">
          <span className="badge-pill badge-neutral">
            {documents.length} File{documents.length === 1 ? '' : 's'}
          </span>
          {onToggleFocus && (
            <button
              type="button"
              className={`panel-header-btn ${isFocused ? 'is-active' : ''}`}
              onClick={onToggleFocus}
              title={isFocused ? 'Restore 3-Column Cockpit (Esc)' : 'Focus Document Viewer (Full Width)'}
              aria-label={isFocused ? 'Restore 3-Column Cockpit' : 'Focus Document Viewer'}
            >
              {isFocused ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
            </button>
          )}
        </div>
      </div>

      <div className="panel-body-scroll">
        {/* Upload Dropzone */}
        <div
          className={`upload-dropzone ${dragOver ? 'is-drag-over' : ''} ${isUploading ? 'is-uploading' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label="Upload inspection document for ingestion"
        >
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={(e) => e.target.files?.[0] && handleFileChange(e.target.files[0])}
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.xlsx"
          />

          <Upload size={18} className="upload-icon" />

          <div className="upload-text-group">
            <span className="upload-title">
              {isUploading ? 'Ingesting & SHA-256 Digesting...' : 'Drag & Drop Inspection Document or Click to Browse'}
            </span>
            <span className="upload-hint">
              Supports PDF, PNG/JPG P&amp;IDs, XLSX survey logs • Air-gap local hashing
            </span>
          </div>

          {uploadError && (
            <div className="upload-error-pill">
              <AlertCircle size={13} />
              <span>{uploadError}</span>
            </div>
          )}
        </div>

        {/* Ingested Document Metadata Pill or Clean Empty State */}
        {activeDoc ? (
          <div className="active-doc-banner">
            <div className="active-doc-top">
              <span className="active-doc-filename">{activeDoc.filename}</span>
              <span className="badge-pill badge-success">PARSED &amp; BOUND</span>
            </div>
            <div className="active-doc-hash-row">
              <span className="hash-label">SHA-256:</span>
              <CopyableMono value={activeDoc.sha256} truncateLength={16} label="Document Digest" />
            </div>
            <div className="active-doc-meta-row">
              <span>Pages: {activeDoc.page_count}</span>
              <span>•</span>
              <span>Tables: {activeDoc.table_count}</span>
              <span>•</span>
              <span>Size: {(activeDoc.size_bytes / 1024).toFixed(1)} KB</span>
            </div>
          </div>
        ) : (
          <div className="active-doc-banner doc-empty-banner">
            <div className="active-doc-top">
              <span className="active-doc-filename" style={{ color: 'var(--text-muted)', fontWeight: 500 }}>
                No document loaded
              </span>
              <span className="badge-pill badge-neutral">UNBOUND</span>
            </div>
            <div className="active-doc-meta-row" style={{ marginTop: '0.2rem' }}>
              <span>Drop an inspection report or P&amp;ID schematic to begin.</span>
            </div>
          </div>
        )}

        {/* View Switcher Sub-Tabs */}
        <div className="sub-tab-strip">
          <button
            type="button"
            className={`sub-tab-btn ${activeTab === 'survey' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('survey')}
          >
            <Table size={13} />
            <span>Ultrasonic Survey</span>
          </button>
          <button
            type="button"
            className={`sub-tab-btn ${activeTab === 'params' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('params')}
          >
            <Layers size={13} />
            <span>Parameters</span>
          </button>
          <button
            type="button"
            className={`sub-tab-btn ${activeTab === 'archive' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('archive')}
          >
            <FileText size={13} />
            <span>Docs ({documents.length})</span>
          </button>
        </div>

        {/* Sub-View: Ultrasonic Survey Data Table */}
        {activeTab === 'survey' && (() => {
          if (!activeDoc) {
            return (
              <div className="evidence-card survey-table-card" style={{ padding: '1.5rem', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>
                  No inspection document loaded. Upload an ultrasonic thickness survey or engineering drawing to view gauging measurements.
                </p>
              </div>
            );
          }

          if (activeDoc.status === 'failed') {
            return (
              <div className="evidence-card survey-table-card" style={{ padding: '2rem', textAlign: 'center' }}>
                <h3 style={{ color: 'var(--color-alert)', fontSize: '0.95rem', fontWeight: 600, margin: '0 0 0.5rem 0' }}>
                  EXTRACTION UNAVAILABLE
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>
                  The document ingestion pipeline failed to parse valid tabular gauging data from this file.
                </p>
              </div>
            );
          }

          const isDrawing = (activeDoc as any).is_drawing || activeDoc.filename.toLowerCase().includes('pid') || activeDoc.filename.toLowerCase().includes('p&id');
          if (isDrawing) {
            return (
              <div className="evidence-card survey-table-card" style={{ padding: '2rem', textAlign: 'center' }}>
                <h3 style={{ color: 'var(--color-brand)', fontSize: '0.95rem', fontWeight: 600, margin: '0 0 0.5rem 0' }}>
                  P&amp;ID SCHEMATIC DETECTED
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>
                  Engineering schematic detected without ultrasonic thickness tables. Visual findings and tag extractions are handled via the OCR / VLM engine.
                </p>
              </div>
            );
          }

          const rawMeasurements: any[] = (activeDoc as any).evidence?.measurements || [];

          if (rawMeasurements.length === 0) {
            return (
              <div className="evidence-card survey-table-card" style={{ padding: '2rem', textAlign: 'center' }}>
                <h3 style={{ color: 'var(--text-muted)', fontSize: '0.95rem', fontWeight: 600, margin: '0 0 0.5rem 0' }}>
                  NO TABULAR GAUGING DATA DETECTED
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>
                  No ultrasonic thickness gauging rows were identified in this document.
                </p>
              </div>
            );
          }

          const displayRows: ThicknessSurveyRow[] = rawMeasurements.map((m: any) => ({
            cml_tag: m.cml_tag || 'CML',
            location_desc: m.location_desc || 'Inspection Point',
            nominal_mm: m.nominal_thickness_mm ?? (activeDoc as any).evidence?.nominal_thickness_mm ?? 0,
            actual_mm: m.measured_thickness_mm,
            loss_mm: m.loss_mm ?? (m.nominal_thickness_mm ? Math.round((m.nominal_thickness_mm - m.measured_thickness_mm) * 100) / 100 : 0),
            date_measured: m.measurement_date || '—',
          }));

          const minActual = displayRows.length > 0 ? Math.min(...displayRows.map(r => r.actual_mm)) : 0;

          return (
            <div className="evidence-card survey-table-card">
              <div className="table-responsive">
                <table className="deck-table">
                  <thead>
                    <tr>
                      <th>CML</th>
                      <th>Inspection Location</th>
                      <th className="num-col">Nominal</th>
                      <th className="num-col">Actual</th>
                      <th className="num-col">Δt Loss</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayRows.map((row, idx) => {
                      const isCritical = row.actual_mm === minActual;
                      return (
                        <tr key={`${row.cml_tag}-${idx}`} className={isCritical ? 'row-critical-highlight' : ''}>
                          <td>
                            <code className="cml-tag-badge">{row.cml_tag}</code>
                          </td>
                          <td className="location-desc-cell">{row.location_desc}</td>
                          <td className="num-col mono-num">{row.nominal_mm > 0 ? `${row.nominal_mm.toFixed(2)} mm` : '—'}</td>
                          <td className="num-col mono-num highlight-actual">{row.actual_mm.toFixed(2)} mm</td>
                          <td className="num-col mono-num text-warning">{row.loss_mm > 0 ? `${row.loss_mm.toFixed(2)} mm` : '—'}</td>
                          <td className="mono-date">{row.date_measured}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {(() => {
                const governingRow = displayRows.find(r => r.actual_mm === minActual);
                const minReqThreshold = (activeDoc as any)?.evidence?.minimum_required_thickness_mm ?? 9.0;
                const isPassing = minActual >= minReqThreshold;
                return (
                  <div className="table-footnote">
                    <div className="footnote-left">
                      <span className="footnote-tag">GOVERNING CML:</span>
                      <span className="footnote-cml-info">
                        {governingRow ? `${governingRow.cml_tag} / ${governingRow.location_desc}` : 'Governing Point'} — {minActual.toFixed(2)} mm
                      </span>
                    </div>
                    <span className={`footnote-assessment ${isPassing ? 'assessment-pass' : 'assessment-alert'}`}>
                      {isPassing ? 'PASS / CONTINUE SERVICE' : 'RETIRE FROM SERVICE'}
                    </span>
                  </div>
                );
              })()}
            </div>
          );
        })()}

        {/* Sub-View: Extracted Engineering Parameters Card */}
        {activeTab === 'params' && (() => {
          if (!activeDoc) {
            return (
              <div className="evidence-card params-card" style={{ padding: '1.5rem', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>
                  No equipment parameters extracted. Parameters will populate automatically upon document ingestion.
                </p>
              </div>
            );
          }

          const ev = (activeDoc as any).evidence;

          const eqTag = ev?.equipment_id || 'UNAVAILABLE';
          const nomThick = ev?.nominal_thickness_mm != null ? `${ev.nominal_thickness_mm.toFixed(2)} mm` : 'UNAVAILABLE';
          const curThick = ev?.current_thickness_mm != null ? `${ev.current_thickness_mm.toFixed(2)} mm` : 'UNAVAILABLE';
          const minThick = ev?.minimum_required_thickness_mm != null ? `${ev.minimum_required_thickness_mm.toFixed(2)} mm` : 'UNAVAILABLE';
          const elapsed = ev?.elapsed_time_years != null ? `${ev.elapsed_time_years} Years` : 'UNAVAILABLE';

          return (
            <div className="evidence-card params-card">
              <div className="params-grid">
                <div className="param-item">
                  <span className="param-label">EQUIPMENT TAG</span>
                  <code className="param-val">{eqTag}</code>
                </div>
                <div className="param-item">
                  <span className="param-label">SOURCE DIGEST</span>
                  <CopyableMono value={activeDoc.sha256} truncateLength={16} label="SHA-256" />
                </div>
                <div className="param-item">
                  <span className="param-label">NOMINAL THICKNESS (t_initial)</span>
                  <code className="param-val highlight-val">{nomThick}</code>
                </div>
                <div className="param-item">
                  <span className="param-label">CURRENT MINIMUM (t_actual)</span>
                  <code className="param-val highlight-val">{curThick}</code>
                </div>
                <div className="param-item">
                  <span className="param-label">RETIREMENT THICKNESS (t_min)</span>
                  <code className="param-val text-warning">{minThick}</code>
                </div>
                <div className="param-item">
                  <span className="param-label">ELAPSED TIME (T)</span>
                  <code className="param-val">{elapsed}</code>
                </div>
              </div>
            </div>
          );
        })()}

        {/* Sub-View: Document Repository List */}
        {activeTab === 'archive' && (
          <div className="evidence-card doc-archive-card">
            {documents.length === 0 ? (
              <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                No documents in session repository. Upload a file above.
              </div>
            ) : (
              <div className="archive-list">
                {documents.map((doc) => {
                  const isSelected = activeDoc?.sha256 === doc.sha256;
                  const summaryText = typeof doc.extraction_summary === 'string'
                    ? doc.extraction_summary
                    : JSON.stringify(doc.extraction_summary, null, 2);
                  return (
                    <div
                      key={doc.sha256}
                      className={`archive-item ${isSelected ? 'is-active-doc' : ''}`}
                      onClick={() => {
                        setActivePreviewDoc(doc);
                        if (onSelectDoc) onSelectDoc(doc);
                      }}
                      role="button"
                      tabIndex={0}
                    >
                      <div className="archive-item-top">
                        <span className="archive-filename">{doc.filename}</span>
                        <span className="archive-size">{(doc.size_bytes / 1024).toFixed(1)} KB</span>
                      </div>
                      <div className="archive-hash">
                        <CopyableMono value={doc.sha256} truncateLength={16} label="SHA-256" />
                      </div>
                      <div className="archive-summary">{summaryText}</div>
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
