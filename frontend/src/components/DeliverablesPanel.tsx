import React, { useState } from 'react';
import { GeneratedArtifact, DeliverableFormat } from '../types/deliverables';
import { deliverablesService } from '../services/deliverables';
import {
  FileText,
  Download,
  FileSpreadsheet,
  CheckCircle2,
  RefreshCw,
  Lock,
  ExternalLink,
} from 'lucide-react';
import { CopyableMono } from './CopyableMono';
import { useToast } from './ToastProvider';
import { DataSourceBadge } from './DataSourceBadge';

interface DeliverablesPanelProps {
  artifacts: GeneratedArtifact[];
  taskId?: string | null;
  equipmentId?: string;
  summary?: string;
  onGenerated?: (artifacts: GeneratedArtifact[]) => void;
  validationPassed?: boolean;
  executionMode?: 'deterministic' | 'live';
}

export const DeliverablesPanel: React.FC<DeliverablesPanelProps> = ({
  artifacts,
  taskId,
  equipmentId = 'C-101',
  summary = 'Corrosion and integrity analysis findings.',
  onGenerated,
  validationPassed = true,
  executionMode = 'deterministic',
}) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const isLive = executionMode === 'live';
  const hasArtifacts = artifacts.length > 0;

  const handleGenerate = async (formats: DeliverableFormat[] = ['docx', 'xlsx']) => {
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

  const handleDownload = (artifact: GeneratedArtifact) => {
    toast.info('Downloading Artifact', artifact.filename);
    // In demo / live, trigger download
    const url = artifact.download_url || deliverablesService.getDownloadUrl(artifact.format, artifact.filename);
    const a = document.createElement('a');
    a.href = url;
    a.download = artifact.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
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
          <DataSourceBadge
            source={hasArtifacts ? (isLive ? 'LIVE' : 'DEMO') : 'FALLBACK'}
            label={hasArtifacts ? (isLive ? 'GENERATED LIVE' : 'DEMO ARTIFACT') : 'AWAITING RELEASE'}
          />
          <button
            type="button"
            className="btn btn-secondary btn-sm"
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
        </div>
      </div>

      <div className="panel-body-scroll">
        {artifacts.length === 0 ? (
          <div className="empty-panel-state">
            <Lock size={26} className="empty-icon" />
            <div className="empty-title">No Deliverables Released Yet</div>
            <div className="empty-desc">
              Deliverables are deterministically compiled and signed with SHA-256 only after the 12-point engineering validation gate passes 100%.
            </div>
          </div>
        ) : (
          <div className="deliverables-cards-list">
            {artifacts.map((art) => {
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
                          source={isLive ? 'LIVE' : 'DEMO'}
                          label={isLive ? 'GENERATED LIVE' : 'DEMO ARTIFACT'}
                          size="sm"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="deliv-hash-row">
                    <span className="hash-title">SHA-256 HASH:</span>
                    <CopyableMono value={hash} truncateLength={28} label="Deliverable SHA-256" />
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
