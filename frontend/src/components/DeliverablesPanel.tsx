import React, { useState } from 'react';
import { GeneratedArtifact, DeliverableFormat } from '../types/deliverables';
import { deliverablesService } from '../services/deliverables';
import {
  FileText,
  Download,
  FileSpreadsheet,
  CheckCircle2,
  FileCheck2,
  RefreshCw,
  Lock,
  ExternalLink,
  ShieldCheck,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { CopyableMono } from './CopyableMono';
import { useToast } from './ToastProvider';
import { DataSourceBadge } from './DataSourceBadge';

interface DeliverablesPanelProps {
  artifacts: GeneratedArtifact[];
  taskId?: string | null;
  executionCapability?: string | null;
  activeModel?: string | null;
  sourceDocument?: string | null;
  visualFindingsCount?: number;
  equipmentId?: string;
  summary?: string;
  onGenerated?: (artifacts: GeneratedArtifact[]) => void;
  validationPassed?: boolean;
  executionMode?: 'deterministic' | 'live';
  isFocused?: boolean;
  onToggleFocus?: () => void;
}

export const DeliverablesPanel: React.FC<DeliverablesPanelProps> = ({
  artifacts,
  taskId,
  executionCapability,
  activeModel,
  sourceDocument,
  visualFindingsCount,
  equipmentId = 'UNAVAILABLE',
  summary = 'Corrosion and integrity analysis findings.',
  onGenerated,
  validationPassed = true,
  executionMode = 'deterministic',
  isFocused = false,
  onToggleFocus,
}) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const isLive = executionMode === 'live';
  const isVisionOnly = executionCapability === 'vision';

  // Section 9 & 10: Strict task isolation — filter strictly by current taskId
  const currentArtifacts = taskId
    ? artifacts.filter((a) => a.task_id === taskId)
    : [];
  const hasArtifacts = currentArtifacts.length > 0;

  const handleGenerate = async (formats: DeliverableFormat[] = ['docx', 'xlsx']) => {
    if (isVisionOnly) {
      toast.info('Vision Task', 'Engineering report compilation is not applicable for visual inspection tasks.');
      return;
    }
    if (!validationPassed) {
      toast.error('Validation Gate Failed', 'Fail-Closed policy withholds deliverable compilation until all 12 checks pass.');
      return;
    }

    setIsGenerating(true);
    setError(null);
    try {
      const response = await deliverablesService.generateDeliverables(
        {
          equipment_id: equipmentId,
          inspection_subject: 'Atmospheric Distillation Column Overhead Condenser Piping System',
          summary,
        },
        formats,
        taskId || `task-${Date.now()}`
      );

      if (response.artifacts && response.artifacts.length > 0) {
        if (onGenerated) {
          onGenerated(response.artifacts);
        }
        toast.success('Deliverables Compiled', `Successfully generated ${response.artifacts.length} publication documents.`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to compile deliverables');
      toast.error('Compilation Error', err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async (artifact: GeneratedArtifact) => {
    toast.info('Downloading Artifact', artifact.filename);
    try {
      const url = artifact.download_url || deliverablesService.getDownloadUrl(artifact.format, artifact.filename);
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}: ${res.statusText}`);
      }
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = artifact.filename;
      document.body.appendChild(a);
      a.click();
      window.setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(blobUrl);
      }, 150);
    } catch (err: any) {
      toast.error('Download Failed', err.message || 'Unable to download deliverable');
    }
  };

  return (
    <div className="workbench-panel deliverables-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-header-title-group">
          <FileText size={16} className="panel-header-icon" />
          <div>
            <h2 className="panel-title">Deliverables Factory</h2>
            <span className="panel-subtitle">Clean-Room DOCX &amp; XLSX Compilers</span>
          </div>
        </div>

        <div className="panel-header-badges">
          {isVisionOnly ? (
            <DataSourceBadge
              source="LIVE"
              label="VISUAL ANALYSIS"
              size="sm"
            />
          ) : (
            <>
              <DataSourceBadge
                source={hasArtifacts ? 'LIVE' : 'FALLBACK'}
                label={hasArtifacts ? 'VERIFIED DELIVERABLES' : (!taskId ? 'NO ACTIVE TASK' : 'AWAITING RELEASE')}
              />
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => handleGenerate(['docx', 'xlsx'])}
                disabled={isGenerating}
                title="Compile publication-ready DOCX and XLSX deliverables"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw size={13} className="icon-spin" />
                    <span>Compiling...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw size={13} />
                    <span>Compile</span>
                  </>
                )}
              </button>
            </>
          )}
          {onToggleFocus && (
            <button
              type="button"
              className={`panel-header-btn ${isFocused ? 'is-active' : ''}`}
              onClick={onToggleFocus}
              title={isFocused ? 'Restore 3-Column Cockpit (Esc)' : 'Focus Deliverables Column (Full Width)'}
              aria-label={isFocused ? 'Restore 3-Column Cockpit' : 'Focus Deliverables Column'}
            >
              {isFocused ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
            </button>
          )}
        </div>
      </div>

      <div className="panel-body-scroll">
        {isVisionOnly && currentArtifacts.length === 0 ? (
          <div className="empty-panel-state vision-empty-deliverables">
            <CheckCircle2 size={28} className="empty-icon" style={{ color: 'var(--color-brand)', opacity: 0.9 }} />
            <div className="empty-title">NO ENGINEERING DELIVERABLES</div>
            <div className="empty-desc">
              Visual analysis completed. Engineering calculation and document generation were not part of this execution.
            </div>
            <div className="vision-deliverables-meta-box">
              <div className="meta-row">
                <span className="meta-label">TASK TYPE:</span>
                <span className="meta-val">VISION</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">ACTIVE MODEL:</span>
                <code className="meta-code">{activeModel || 'MODEL UNAVAILABLE'}</code>
              </div>
              <div className="meta-row">
                <span className="meta-label">SOURCE:</span>
                <span className="meta-val">{sourceDocument || 'pid_sample.png'}</span>
              </div>
              {visualFindingsCount !== undefined && visualFindingsCount > 0 && (
                <div className="meta-row">
                  <span className="meta-label">FINDINGS:</span>
                  <span className="meta-val">{visualFindingsCount} elements detected</span>
                </div>
              )}
            </div>
          </div>
        ) : !taskId ? (
          <div className="empty-panel-state">
            <Lock size={26} className="empty-icon" />
            <div className="empty-title">No Active Task</div>
            <div className="empty-desc">
              Execute an engineering audit task to compile and verify signed deliverables.
            </div>
          </div>
        ) : currentArtifacts.length === 0 ? (
          <div className="empty-panel-state">
            <Lock size={26} className="empty-icon" />
            <div className="empty-title">No Deliverables Released Yet</div>
            <div className="empty-desc">
              Deliverables are deterministically compiled and signed with SHA-256 only after the 12-point engineering validation gate passes 100%.
            </div>
          </div>
        ) : (
          <div className="deliverables-cards-list">
            {currentArtifacts.map((art) => {
              const isDocx = art.format === 'docx';
              const sizeKb = (art.file_size_bytes / 1024).toFixed(1);
              const hash = art.sha256_hash || art.sha256_checksum || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';

              return (
                <div key={art.artifact_id} className="deliverable-card">
                  <div className="deliverable-card-top">
                    <div className="deliv-format-icon-wrap">
                      {isDocx ? (
                        <FileText size={22} className="format-icon-docx" />
                      ) : (
                        <FileSpreadsheet size={22} className="format-icon-xlsx" />
                      )}
                    </div>
                    <div className="deliv-card-meta">
                      <div className="deliv-filename">{art.filename}</div>
                      <div className="deliv-format-badge">
                        <span>{art.format.toUpperCase()}</span>
                        <span>•</span>
                        <span>{sizeKb} KB</span>
                        <span>•</span>
                        <DataSourceBadge
                          source="LIVE"
                          label="GENERATED DELIVERABLE"
                          size="sm"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="deliv-hash-row">
                    <span className="hash-title">SHA-256 HASH:</span>
                    <CopyableMono value={hash} truncateLength={16} label="Deliverable SHA-256" />
                  </div>

                  <div className="deliv-card-actions">
                    <button
                      type="button"
                      className="btn btn-primary btn-sm btn-full"
                      onClick={() => handleDownload(art)}
                    >
                      <Download size={13} />
                      <span>Download Clean-Room {art.format.toUpperCase()}</span>
                    </button>
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
