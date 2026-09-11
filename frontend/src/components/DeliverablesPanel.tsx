import React, { useState } from 'react';
import { GeneratedArtifact, DeliverableFormat } from '../types/deliverables';
import { deliverablesService } from '../services/deliverables';
import { FileText, Download, FileSpreadsheet, Presentation, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

interface DeliverablesPanelProps {
  artifacts: GeneratedArtifact[];
  taskId?: string | null;
  equipmentId?: string;
  summary?: string;
  onGenerated?: (artifacts: GeneratedArtifact[]) => void;
}

export const DeliverablesPanel: React.FC<DeliverablesPanelProps> = ({
  artifacts,
  taskId,
  equipmentId = 'C-101',
  summary = 'Corrosion and integrity analysis findings.',
  onGenerated,
}) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (formats: DeliverableFormat[] = ['docx', 'xlsx', 'pptx']) => {
    setIsGenerating(true);
    setError(null);
    try {
      const response = await deliverablesService.generateDeliverables(
        {
          equipment_id: equipmentId,
          inspection_subject: 'Atmospheric Distillation Column Shell Inspection',
          summary,
        },
        formats,
        taskId || `task-${Date.now()}`
      );

      if (response.artifacts && response.artifacts.length > 0) {
        if (onGenerated) {
          onGenerated(response.artifacts);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate deterministic deliverables');
    } finally {
      setIsGenerating(false);
    }
  };

  const getFormatIcon = (format: DeliverableFormat) => {
    switch (format.toLowerCase()) {
      case 'xlsx':
        return <FileSpreadsheet size={20} style={{ color: '#059669' }} />;
      case 'pptx':
        return <Presentation size={20} style={{ color: '#d97706' }} />;
      case 'docx':
      default:
        return <FileText size={20} style={{ color: '#1e3a8a' }} />;
    }
  };

  const getFormatName = (format: DeliverableFormat) => {
    switch (format.toLowerCase()) {
      case 'xlsx':
        return 'Microsoft Excel Worksheet';
      case 'pptx':
        return 'Microsoft PowerPoint Briefing';
      case 'docx':
      default:
        return 'Microsoft Word Inspection Memo';
    }
  };

  return (
    <div className="card" style={{ marginBottom: '1.25rem' }}>
      <div className="card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          <FileText size={16} style={{ color: 'var(--accent-primary)' }} />
          <div>
            <div className="card-title">Deterministic Office Deliverables</div>
            <div className="card-subtitle">
              Native DOCX, XLSX, PPTX Generators • Clean Room Zero-Hallucination Schemas
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => handleGenerate(['docx', 'xlsx', 'pptx'])}
            disabled={isGenerating}
            title="Compile deterministic office documents from findings"
          >
            {isGenerating ? (
              <>
                <RefreshCw size={13} className="icon-spin" />
                Compiling...
              </>
            ) : (
              <>
                <FileText size={13} />
                Generate All (DOCX/XLSX/PPTX)
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            margin: '0.75rem 1rem',
            padding: '0.625rem 0.875rem',
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
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      <div style={{ padding: '1rem' }}>
        {artifacts.length === 0 ? (
          <div
            style={{
              padding: '1.5rem 1rem',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.8125rem',
              background: 'var(--bg-surface-muted)',
              borderRadius: 'var(--radius-sm)',
              border: '1px dashed var(--border-medium)',
            }}
          >
            <div>No deliverables generated yet for this session.</div>
            <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>
              Click "Generate All" above or complete an inspection objective to produce verified office packages.
            </div>
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '0.875rem',
            }}
          >
            {artifacts.map((art) => {
              const downloadUrl = deliverablesService.getDownloadUrl(art.format, art.filename);
              const sizeKb = art.file_size_bytes ? (art.file_size_bytes / 1024).toFixed(1) : '—';
              const timeStr = art.created_at ? new Date(art.created_at).toLocaleTimeString() : '--:--';

              return (
                <div
                  key={art.artifact_id}
                  className="card"
                  style={{
                    padding: '0.875rem',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '0.75rem',
                    background: 'var(--bg-surface)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                    <div style={{ flexShrink: 0, marginTop: '2px' }}>
                      {getFormatIcon(art.format)}
                    </div>

                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div
                        style={{
                          fontSize: '0.875rem',
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                        title={art.filename}
                      >
                        {art.filename}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {getFormatName(art.format)}
                      </div>

                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          marginTop: '0.5rem',
                          fontSize: '0.7rem',
                        }}
                      >
                        <span className="code-badge">{art.format.toUpperCase()}</span>
                        <span className="code-badge">{sizeKb} KB</span>
                        <span style={{ color: 'var(--text-muted)' }}>{timeStr}</span>
                      </div>

                      {art.sha256_checksum && (
                        <div
                          style={{
                            fontSize: '0.6875rem',
                            color: 'var(--text-muted)',
                            fontFamily: 'var(--font-mono)',
                            marginTop: '0.25rem',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                          title={`SHA-256: ${art.sha256_checksum}`}
                        >
                          SHA: {art.sha256_checksum.slice(0, 16)}...
                        </div>
                      )}
                    </div>
                  </div>

                  <div
                    style={{
                      borderTop: '1px solid var(--border-subtle)',
                      paddingTop: '0.625rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '0.75rem',
                        color: 'var(--status-success-text)',
                        fontWeight: 500,
                      }}
                    >
                      <CheckCircle2 size={13} /> Ready
                    </span>

                    <div style={{ display: 'flex', gap: '0.375rem' }}>
                      <a
                        href={downloadUrl}
                        download={art.filename}
                        className="btn btn-primary btn-sm"
                        style={{ textDecoration: 'none' }}
                      >
                        <Download size={12} />
                        Download
                      </a>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
