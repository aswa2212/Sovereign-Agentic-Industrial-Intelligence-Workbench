import React, { useState, useEffect } from 'react';
import { useAgentTask } from '../hooks/useAgentTask';
import { AgentGraphTrace } from '../components/AgentGraphTrace';
import { EvidencePanel } from '../components/EvidencePanel';
import { DeliverablesPanel } from '../components/DeliverablesPanel';
import { DocumentViewer } from '../components/DocumentViewer';
import { DocumentIngestionResult } from '../types/documents';
import { GeneratedArtifact } from '../types/deliverables';
import {
  Play,
  RotateCcw,
  Layers,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Clock,
  Sliders,
} from 'lucide-react';

const PRESET_TASKS = [
  {
    title: 'C-101 Column Corrosion & Thickness',
    query:
      'Analyze ultrasonic thickness inspection findings for C-101 atmospheric distillation column shell and evaluate minimum thickness compliance under API 510.',
    equipmentId: 'C-101',
  },
  {
    title: 'SOP-MRPL-PIP-001 Piping Compliance',
    query:
      'Evaluate piping spool thickness inspection readings against retirement thickness thresholds defined in SOP-MRPL-PIP-001.',
    equipmentId: 'PIP-001',
  },
  {
    title: 'Atmospheric Tower Nozzle Inspection',
    query:
      'Review nozzle N1 and N2 ultrasonic gauging results and flag any localized pitting corrosion exceeding safety margins.',
    equipmentId: 'TOWER-N1',
  },
];

export const WorkbenchPage: React.FC = () => {
  const {
    isRunning,
    taskId,
    currentState,
    routePreview,
    trace,
    result,
    citations,
    errors,
    errorMessage,
    previewRoute,
    executeTask,
    reset,
  } = useAgentTask();

  const [taskInput, setTaskInput] = useState(PRESET_TASKS[0].query);
  const [selectedEquipmentId, setSelectedEquipmentId] = useState(PRESET_TASKS[0].equipmentId);
  const [maxSteps, setMaxSteps] = useState(8);
  const [artifacts, setArtifacts] = useState<GeneratedArtifact[]>([]);
  const [showDocSelector, setShowDocSelector] = useState(false);

  // Ingested documents state
  const [documents, setDocuments] = useState<DocumentIngestionResult[]>([
    {
      sha256: 'a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0',
      filename: 'SOP-MRPL-PIP-001.pdf',
      content_type: 'application/pdf',
      size_bytes: 412984,
      page_count: 14,
      table_count: 6,
      storage_path: 'knowledge/default/SOP-MRPL-PIP-001.pdf',
      extraction_summary: 'Ultrasonic thickness gauging procedure and retirement criteria for MRPL piping.',
    },
    {
      sha256: '8f4a21b392bd01754890cdef1234567890abcdef1234567890abcdef12345678',
      filename: 'C101_UTG_Inspection_Report.pdf',
      content_type: 'application/pdf',
      size_bytes: 285400,
      page_count: 8,
      table_count: 4,
      storage_path: 'uploads/C101_UTG_Inspection_Report.pdf',
      extraction_summary: 'Ultrasonic thickness survey measurements across C-101 column shell rings 1 through 8.',
    },
  ]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentIngestionResult>(documents[0]);

  // Trigger route preview when query changes
  useEffect(() => {
    const timer = setTimeout(() => {
      if (taskInput.trim()) {
        previewRoute(taskInput);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [taskInput, previewRoute]);

  const handleSelectPreset = (preset: (typeof PRESET_TASKS)[0]) => {
    setTaskInput(preset.query);
    setSelectedEquipmentId(preset.equipmentId);
    previewRoute(preset.query);
  };

  const handleStartTask = async () => {
    if (!taskInput.trim() || isRunning) return;
    setArtifacts([]);
    const res = await executeTask(taskInput, maxSteps);
    // If response succeeded, we can pre-populate default deliverables or let user generate them
  };

  const handleArtifactsGenerated = (newArtifacts: GeneratedArtifact[]) => {
    setArtifacts((prev) => [...prev, ...newArtifacts]);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* SECTION 1: Objective & Task Submission */}
      <section className="card" aria-labelledby="task-submission-title">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <Layers size={16} style={{ color: 'var(--accent-primary)' }} />
            <div>
              <div id="task-submission-title" className="card-title">
                Operator Task & Objective Definition
              </div>
              <div className="card-subtitle">
                Industrial Reasoning • Local Semantic Retrieval • Autonomous Execution
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setShowDocSelector(!showDocSelector)}
              title="Select or inspect active reference document"
            >
              <FileText size={13} />
              Ref: {selectedDoc.filename}
            </button>
          </div>
        </div>

        {/* Document Ingestion Drawer if open */}
        {showDocSelector && (
          <div
            style={{
              padding: '1rem',
              borderBottom: '1px solid var(--border-subtle)',
              background: 'var(--bg-surface-muted)',
            }}
          >
            <DocumentViewer
              documents={documents}
              selectedDoc={selectedDoc}
              onSelectDoc={(doc) => {
                setSelectedDoc(doc);
                setShowDocSelector(false);
              }}
              onUploadSuccess={(newDoc) => {
                setDocuments((prev) => [newDoc, ...prev]);
                setSelectedDoc(newDoc);
              }}
              compact
            />
          </div>
        )}

        <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
          {/* Quick Presets */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              ENGINEERING PRESETS:
            </span>
            {PRESET_TASKS.map((preset, i) => (
              <button
                key={i}
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => handleSelectPreset(preset)}
                style={{ fontSize: '0.75rem', padding: '3px 8px' }}
              >
                {preset.title}
              </button>
            ))}
          </div>

          {/* Objective Textarea */}
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" htmlFor="objective-input">
              OPERATIONAL OBJECTIVE / REASONING DIRECTIVE
            </label>
            <textarea
              id="objective-input"
              className="form-textarea"
              rows={3}
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              placeholder="Enter engineering inspection task, equipment ID, or regulatory compliance query..."
              disabled={isRunning}
            />
          </div>

          {/* Model Router Preview Ribbon */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1rem',
              padding: '0.625rem 0.875rem',
              background: 'var(--bg-surface-muted)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.8125rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                <Cpu size={14} style={{ color: 'var(--accent-secondary)' }} />
                <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>ROUTED CAPABILITY:</span>
                <span className="code-badge">
                  {routePreview?.capability ? routePreview.capability.toUpperCase() : 'REASONING'}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>MODEL ROLE:</span>
                <span className="badge badge-neutral">
                  {routePreview?.model_role || 'Reasoning Model'}
                </span>
              </div>

              {routePreview?.confidence !== undefined && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>CONFIDENCE:</span>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>
                    {Math.round(routePreview.confidence * 100)}%
                  </span>
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>TARGET:</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Router → Local Model Manager → On-Prem Ollama
                </span>
              </div>
            </div>

            {/* Execution Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', marginRight: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Max Steps:</span>
                <select
                  value={maxSteps}
                  onChange={(e) => setMaxSteps(Number(e.target.value))}
                  disabled={isRunning}
                  style={{
                    fontSize: '0.75rem',
                    padding: '2px 4px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-medium)',
                  }}
                >
                  <option value={4}>4 Steps</option>
                  <option value={8}>8 Steps</option>
                  <option value={12}>12 Steps</option>
                </select>
              </div>

              <button
                className="btn btn-secondary btn-sm"
                onClick={reset}
                disabled={isRunning}
                title="Reset workbench state"
              >
                <RotateCcw size={13} />
                Reset
              </button>

              <button
                className="btn btn-primary"
                onClick={handleStartTask}
                disabled={isRunning || !taskInput.trim()}
                style={{ minWidth: '130px' }}
              >
                {isRunning ? (
                  <>
                    <Clock size={14} className="icon-spin" />
                    Executing...
                  </>
                ) : (
                  <>
                    <Play size={14} fill="currentColor" />
                    Start Analysis
                  </>
                )}
              </button>
            </div>
          </div>

          {errorMessage && (
            <div
              style={{
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
              <AlertTriangle size={14} />
              <span>{errorMessage}</span>
            </div>
          )}
        </div>
      </section>

      {/* SECTION 2: Agent State Machine Lifecycle Trace */}
      <AgentGraphTrace
        currentState={currentState}
        isRunning={isRunning}
        trace={trace}
        taskId={taskId}
      />

      {/* SECTION 3: Structured Validation Status (if task has finished) */}
      {result?.structured_validation && (
        <section className="card" style={{ marginBottom: '1.25rem' }}>
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
              <CheckCircle2 size={16} style={{ color: 'var(--status-success-dot)' }} />
              <div>
                <div className="card-title">Deterministic Engineering Validation Engine</div>
                <div className="card-subtitle">
                  Rule Verification • API 510/570 Boundary Checks • Zero Hallucination Guarantee
                </div>
              </div>
            </div>

            <span
              className={`badge ${
                result.structured_validation.valid ? 'badge-success' : 'badge-danger'
              }`}
            >
              {result.structured_validation.status.toUpperCase()}
            </span>
          </div>

          <div style={{ padding: '0.875rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {result.structured_validation.checks_passed?.length > 0 && (
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--status-success-text)', marginBottom: '4px' }}>
                  CHECKS PASSED:
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                  {result.structured_validation.checks_passed.map((chk, i) => (
                    <li key={i}>{chk}</li>
                  ))}
                </ul>
              </div>
            )}

            {result.structured_validation.checks_failed?.length > 0 && (
              <div style={{ marginTop: '0.375rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--status-error-text)', marginBottom: '4px' }}>
                  CHECKS FAILED:
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8125rem', color: 'var(--status-error-text)' }}>
                  {result.structured_validation.checks_failed.map((chk, i) => (
                    <li key={i}>{chk}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}

      {/* SECTION 4: Dual Evidence & Deliverables Panels */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
          gap: '1.25rem',
        }}
      >
        {/* Left: Retrieved Knowledge Evidence Panel */}
        <EvidencePanel citations={citations} summary={result?.summary} />

        {/* Right: Deterministic Office Deliverables Panel */}
        <DeliverablesPanel
          artifacts={artifacts}
          taskId={taskId}
          equipmentId={selectedEquipmentId}
          summary={result?.summary || taskInput}
          onGenerated={handleArtifactsGenerated}
        />
      </div>
    </div>
  );
};
