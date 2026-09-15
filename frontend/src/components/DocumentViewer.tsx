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
  ChevronRight,
  Eye,
  Table,
} from 'lucide-react';
import { CopyableMono } from './CopyableMono';

interface DocumentViewerProps {
  documents: DocumentIngestionResult[];
  onUploadSuccess?: (doc: DocumentIngestionResult) => void;
  selectedDoc?: DocumentIngestionResult | null;
  onSelectDoc?: (doc: DocumentIngestionResult) => void;
  compact?: boolean;
}

interface ThicknessSurveyRow {
  cml_tag: string;
  location_desc: string;
  nominal_mm: number;
  actual_mm: number;
  loss_mm: number;
  date_measured: string;
}

const SAMPLE_SURVEY_DATA: ThicknessSurveyRow[] = [
  { cml_tag: 'CML-1', location_desc: 'Column Shell Ring 1 (Top Head Nozzle)', nominal_mm: 12.0, actual_mm: 11.45, loss_mm: 0.55, date_measured: '2026-03-12' },
  { cml_tag: 'CML-2', location_desc: 'Column Shell Ring 3 (Reflux Inlet)', nominal_mm: 12.0, actual_mm: 10.90, loss_mm: 1.10, date_measured: '2026-03-12' },
  { cml_tag: 'CML-3', location_desc: 'Column Shell Ring 5 (Tray 12 Vapor Zone)', nominal_mm: 12.0, actual_mm: 10.40, loss_mm: 1.60, date_measured: '2026-03-12' },
  { cml_tag: 'CML-4', location_desc: 'Overhead Condenser Vapor Line Elbow E-02', nominal_mm: 12.0, actual_mm: 10.10, loss_mm: 1.90, date_measured: '2026-03-12' },
];

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
  const [activeTab, setActiveTab] = useState<'survey' | 'params' | 'archive'>('survey');

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

  const activeDoc = selectedDoc || activePreviewDoc || documents[0];

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

        {/* Ingested Document Metadata Pill */}
        {activeDoc && (
          <div className="active-doc-banner">
            <div className="active-doc-top">
              <span className="active-doc-filename">{activeDoc.filename}</span>
              <span className="badge-pill badge-success">PARSED &amp; BOUND</span>
            </div>
            <div className="active-doc-hash-row">
              <span className="hash-label">SHA-256:</span>
              <CopyableMono value={activeDoc.sha256} truncateLength={28} label="Document Digest" />
            </div>
            <div className="active-doc-meta-row">
              <span>Pages: {activeDoc.page_count}</span>
              <span>•</span>
              <span>Tables: {activeDoc.table_count}</span>
              <span>•</span>
              <span>Size: {(activeDoc.size_bytes / 1024).toFixed(1)} KB</span>
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
        {activeTab === 'survey' && (
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
                  {SAMPLE_SURVEY_DATA.map((row) => {
                    const isMaxLoss = row.cml_tag === 'CML-4';
                    return (
                      <tr key={row.cml_tag} className={isMaxLoss ? 'row-critical-highlight' : ''}>
                        <td>
                          <code className="cml-tag-badge">{row.cml_tag}</code>
                        </td>
                        <td className="location-desc-cell">{row.location_desc}</td>
                        <td className="num-col mono-num">{row.nominal_mm.toFixed(2)} mm</td>
                        <td className="num-col mono-num highlight-actual">{row.actual_mm.toFixed(2)} mm</td>
                        <td className="num-col mono-num text-warning">{row.loss_mm.toFixed(2)} mm</td>
                        <td className="mono-date">{row.date_measured}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="table-footnote">
              <span className="footnote-alert">CRITICAL CML:</span>
              <span>CML-4 represents minimum wall thickness location (10.10 mm) governed by API 570 §7.1.</span>
            </div>
          </div>
        )}

        {/* Sub-View: Extracted Engineering Parameters Card */}
        {activeTab === 'params' && (
          <div className="evidence-card params-card">
            <div className="params-grid">
              <div className="param-item">
                <span className="param-label">EQUIPMENT TAG</span>
                <code className="param-val">C-101</code>
              </div>
              <div className="param-item">
                <span className="param-label">COMPONENT</span>
                <span className="param-val-text">Atmospheric Column Overhead Piping</span>
              </div>
              <div className="param-item">
                <span className="param-label">MATERIAL SPECIFICATION</span>
                <code className="param-val">ASTM A106 Gr. B (Class 150)</code>
              </div>
              <div className="param-item">
                <span className="param-label">GOVERNING STANDARD</span>
                <code className="param-val">API 570 / SOP-MRPL-PIP-001</code>
              </div>
              <div className="param-item">
                <span className="param-label">NOMINAL THICKNESS (t_initial)</span>
                <code className="param-val highlight-val">12.00 mm</code>
              </div>
              <div className="param-item">
                <span className="param-label">CURRENT MINIMUM (t_actual)</span>
                <code className="param-val highlight-val">10.10 mm (CML-4)</code>
              </div>
              <div className="param-item">
                <span className="param-label">RETIREMENT THICKNESS (t_min)</span>
                <code className="param-val text-warning">8.00 mm</code>
              </div>
              <div className="param-item">
                <span className="param-label">ELAPSED SERVICE TIME (T)</span>
                <code className="param-val">5.00 Years (2021-2026)</code>
              </div>
            </div>
          </div>
        )}

        {/* Sub-View: Document Repository List */}
        {activeTab === 'archive' && (
          <div className="evidence-card doc-archive-card">
            <div className="archive-list">
              {documents.map((doc) => {
                const isSelected = activeDoc?.sha256 === doc.sha256;
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
                      <CopyableMono value={doc.sha256} truncateLength={24} label="SHA-256" />
                    </div>
                    <div className="archive-summary">{doc.extraction_summary}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
