import React, { useState, useEffect, useCallback } from 'react';
import { useAgentTask } from '../hooks/useAgentTask';
import { AgentGraphTrace } from '../components/AgentGraphTrace';
import { EvidencePanel } from '../components/EvidencePanel';
import { DeliverablesPanel } from '../components/DeliverablesPanel';
import { DocumentViewer } from '../components/DocumentViewer';
import { DocumentIngestionResult } from '../types/documents';
import { GeneratedArtifact } from '../types/deliverables';
import { systemService } from '../services/system';
import { MOCK_INGESTED_DOCUMENTS } from '../services/mockData';
import { DataSourceBadge } from '../components/DataSourceBadge';
import { useToast } from '../components/ToastProvider';
import {
  Play,
  RotateCcw,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  Sliders,
  ShieldCheck,
  Terminal,
} from 'lucide-react';

const PRESET_TASKS = [
  {
    title: 'C-101 Column Corrosion & Remaining Life Audit (API 570)',
    query:
      'Execute autonomous corrosion audit on Atmospheric Distillation Column C-101 overhead line. Ingest ultrasonic thickness survey, compute deterministic metal loss and remaining service life per API 570, evaluate 12 fail-closed validation rules, and compile branded DOCX/XLSX deliverables.',
    equipmentId: 'C-101',
  },
  {
    title: 'API 570 Minimum Retirement Thickness Check',
    query:
      'Evaluate piping spool thickness inspection readings against retirement thickness thresholds defined in SOP-MRPL-PIP-001 Section 4.2.',
    equipmentId: 'C-101',
  },
  {
    title: 'Ultrasonic Survey (CML-4) Grid Ingestion',
    query:
      'Ingest ultrasonic thickness survey and extract CML-1 through CML-4 gauging grid for CDU-1 overhead condenser piping.',
    equipmentId: 'CML-4',
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
    deliverables,
    errors,
    errorMessage,
    previewRoute,
    executeTask,
    reset,
  } = useAgentTask();

  const toast = useToast();
  const [taskInput, setTaskInput] = useState(PRESET_TASKS[0].query);
  const [selectedEquipmentId, setSelectedEquipmentId] = useState(PRESET_TASKS[0].equipmentId);
  const [maxSteps, setMaxSteps] = useState(8);
  const [executionMode, setExecutionMode] = useState<'deterministic' | 'live'>('deterministic');
  const [configuredVisionModel, setConfiguredVisionModel] = useState<string>('qwen2.5vl:3b');
  const [configuredProvider, setConfiguredProvider] = useState<string>('Ollama');
  const [artifacts, setArtifacts] = useState<GeneratedArtifact[]>([]);

  const activeArtifacts = deliverables.length > 0 ? deliverables : artifacts;

  // Ingested documents state
  const [documents, setDocuments] = useState<DocumentIngestionResult[]>(MOCK_INGESTED_DOCUMENTS);
  const [selectedDoc, setSelectedDoc] = useState<DocumentIngestionResult>(documents[0]);

  // Dynamically load active configured model from backend / tier discovery (Never hardcode!)
  useEffect(() => {
    systemService
      .getModelTier()
      .then((tier) => {
        const vModel = tier?.models?.find((m) => m.role === 'vision' || m.role === 'reasoning');
        if (vModel) {
          setConfiguredVisionModel(vModel.model_tag);
          if (vModel.provider) {
            setConfiguredProvider(vModel.provider === 'ollama' ? 'Ollama' : vModel.provider);
          }
        }
      })
      .catch(() => {
        // Fallback already set to default
      });
  }, []);

  // Trigger route preview when query changes
  useEffect(() => {
    const timer = setTimeout(() => {
      if (taskInput.trim()) {
        previewRoute(taskInput);
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [taskInput, previewRoute]);

  // Handle running task
  const handleStartTask = useCallback(async () => {
    if (!taskInput.trim() || isRunning) return;

    toast.info('Starting Task', `Executing in ${executionMode.toUpperCase()} mode...`);
    const res = await executeTask(taskInput, maxSteps, executionMode, selectedEquipmentId);

    if (res) {
      toast.success(
        'Task Completed',
        '12/12 engineering invariants satisfied. Deliverables verified.'
      );
    } else {
      toast.error('Task Encountered Failure', 'Check execution trace for details.');
    }
  }, [taskInput, isRunning, executionMode, selectedEquipmentId, executeTask, toast]);

  // Keyboard shortcuts inside the Workbench (Enter to run, Esc to cancel/reset)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is in an input or textarea unless Ctrl/Cmd+Enter is pressed, or if not focused in textarea
      const isTextarea = (e.target as HTMLElement)?.tagName === 'TEXTAREA';

      if (e.key === 'Enter' && (!isTextarea || e.ctrlKey || e.metaKey)) {
        if (!isRunning && taskInput.trim()) {
          e.preventDefault();
          handleStartTask();
        }
      } else if (e.key === 'Escape') {
        if (isRunning) {
          e.preventDefault();
          reset();
          toast.warning('Task Cancelled', 'Agent execution was stopped by user.');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleStartTask, isRunning, taskInput, reset, toast]);

  const handleSelectPreset = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const idx = Number(e.target.value);
    const preset = PRESET_TASKS[idx];
    if (preset) {
      setTaskInput(preset.query);
      setSelectedEquipmentId(preset.equipmentId);
    }
  };

  const handleArtifactsGenerated = (newArtifacts: GeneratedArtifact[]) => {
    setArtifacts((prev) => {
      const existingIds = new Set(prev.map((a) => a.artifact_id));
      const filtered = newArtifacts.filter((a) => !existingIds.has(a.artifact_id));
      return [...prev, ...filtered];
    });
  };

  return (
    <div className="page-container workbench-page">
      {/* Top Engineering Control Bar */}
      <section className="workbench-control-bar" aria-label="Workbench Task Controls">
        <div className="control-bar-top-row">
          <div className="preset-selector-group">
            <span className="control-label">TASK PRESET:</span>
            <select
              className="form-select preset-select"
              onChange={handleSelectPreset}
              disabled={isRunning}
              defaultValue="0"
            >
              {PRESET_TASKS.map((preset, index) => (
                <option key={index} value={index}>
                  {preset.title}
                </option>
              ))}
            </select>
          </div>

          <div className="control-bar-settings-group">
            <div className="mode-toggle-pill">
              <span className="control-label">MODE:</span>
              <button
                type="button"
                className={`mode-btn ${executionMode === 'deterministic' ? 'is-active' : ''}`}
                onClick={() => setExecutionMode('deterministic')}
                disabled={isRunning}
                title="Source: Deterministic demonstration pipeline (clean-room calculation & compilers)"
              >
                Demo Pipeline
              </button>
              <button
                type="button"
                className={`mode-btn ${executionMode === 'live' ? 'is-active' : ''}`}
                onClick={() => setExecutionMode('live')}
                disabled={isRunning}
                title="Source: FastAPI + local Ollama (qwen2.5vl:3b)"
              >
                Live Local Model
              </button>
              <DataSourceBadge
                source={executionMode === 'live' ? 'LIVE' : 'DEMO'}
                label={executionMode === 'live' ? 'LIVE — LOCAL OLLAMA' : 'DEMO — DETERMINISTIC'}
                size="sm"
              />
            </div>

            <div className="steps-selector-group">
              <span className="control-label">STEPS:</span>
              <select
                className="form-select steps-select"
                value={maxSteps}
                onChange={(e) => setMaxSteps(Number(e.target.value))}
                disabled={isRunning}
              >
                <option value={4}>4</option>
                <option value={8}>8</option>
                <option value={12}>12</option>
              </select>
            </div>

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={reset}
              disabled={isRunning}
              title="Reset workbench state"
            >
              <RotateCcw size={13} />
              <span>Reset</span>
            </button>

            <button
              type="button"
              className="btn btn-accent btn-sm run-task-btn"
              onClick={handleStartTask}
              disabled={isRunning || !taskInput.trim()}
            >
              {isRunning ? (
                <>
                  <Clock size={14} className="icon-spin" />
                  <span>Executing Pipeline...</span>
                </>
              ) : (
                <>
                  <Play size={14} fill="currentColor" />
                  <span>Execute Analysis</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Task Objective Text Input Area */}
        <div className="task-input-wrapper">
          <textarea
            className="task-objective-textarea"
            rows={2}
            value={taskInput}
            onChange={(e) => setTaskInput(e.target.value)}
            disabled={isRunning}
            placeholder="Enter refinery operational goal or inspection question..."
          />
        </div>

        {/* Surfaced Keyboard Shortcut Hints Row */}
        <div className="workbench-shortcuts-hint-row">
          <span className="shortcut-hint">
            <kbd className="cmd-kbd">↵ Enter</kbd> (or <kbd className="cmd-kbd">Ctrl+Enter</kbd>) to Execute
          </span>
          <span className="hint-sep">•</span>
          <span className="shortcut-hint">
            <kbd className="cmd-kbd">Esc</kbd> to Cancel / Reset
          </span>
          <span className="hint-sep">•</span>
          <span className="shortcut-hint">
            <kbd className="cmd-kbd">⌘K</kbd> Command Palette
          </span>
        </div>

        {/* Live Local Model Accent-Glow Banner */}
        {executionMode === 'live' && (
          <div className="live-local-banner-glow">
            <div className="banner-left">
              <span className="live-glow-dot" />
              <strong className="live-banner-title">LIVE LOCAL MODEL ACTIVE</strong>
              <span className="banner-sep">|</span>
              <span>Provider: <code>{configuredProvider}</code></span>
              <span className="banner-sep">|</span>
              <span>Model Tag: <code>{configuredVisionModel}</code></span>
            </div>
            <div className="banner-right">
              <code>127.0.0.1 (On-Prem Loopback Sovereign)</code>
            </div>
          </div>
        )}

        {errorMessage && (
          <div className="workbench-error-banner">
            <AlertTriangle size={14} />
            <span>{errorMessage}</span>
          </div>
        )}
      </section>

      {/* NON-NEGOTIABLE 3-COLUMN ENGINEERING LAYOUT */}
      <div className="workbench-three-columns-grid">
        {/* Column 1: Source Document Viewer & NDT Table */}
        <div className="workbench-column col-documents">
          <DocumentViewer
            documents={documents}
            selectedDoc={selectedDoc}
            onSelectDoc={setSelectedDoc}
            onUploadSuccess={(doc) => {
              setDocuments((prev) => [doc, ...prev]);
              setSelectedDoc(doc);
              toast.success('Document Uploaded', `Ingested ${doc.filename} (${doc.sha256.substring(0, 12)}...)`);
            }}
          />
        </div>

        {/* Column 2: Evidence Panel & 12-Cell Fuse Box */}
        <div className="workbench-column col-evidence">
          <EvidencePanel
            citations={citations.length > 0 ? citations : (result?.citations || [])}
            summary={result?.summary}
            routePreview={routePreview}
            validationReport={result?.structured_validation}
            isRunning={isRunning}
            executionMode={executionMode}
          />
        </div>

        {/* Column 3: Agent Lifecycle Timeline & Deliverables Factory */}
        <div className="workbench-column col-lifecycle-deliverables">
          <AgentGraphTrace
            currentState={currentState}
            isRunning={isRunning}
            trace={trace}
            taskId={taskId}
            executionMode={executionMode}
          />
          <DeliverablesPanel
            artifacts={activeArtifacts}
            taskId={taskId}
            equipmentId={selectedEquipmentId}
            summary={result?.summary || taskInput}
            onGenerated={handleArtifactsGenerated}
            validationPassed={!!result?.structured_validation?.valid}
            executionMode={executionMode}
          />
        </div>
      </div>
    </div>
  );
};
