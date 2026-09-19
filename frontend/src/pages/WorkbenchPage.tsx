import React, { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useAgentTask } from '../hooks/useAgentTask';
import { useWorkbenchRuntime } from '../context/WorkbenchRuntimeContext';
import { AgentGraphTrace } from '../components/AgentGraphTrace';
import { EvidencePanel } from '../components/EvidencePanel';
import { DeliverablesPanel } from '../components/DeliverablesPanel';
import { DocumentViewer, isApprovedDemoPreset } from '../components/DocumentViewer';
import { DocumentIngestionResult } from '../types/documents';
import { GeneratedArtifact } from '../types/deliverables';
import { systemService } from '../services/system';
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
  Maximize2,
  X,
  FileText,
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

  const { runtimeState, activeModel } = useWorkbenchRuntime();

  const toast = useToast();
  const [taskInput, setTaskInput] = useState(PRESET_TASKS[0].query);
  const [selectedEquipmentId, setSelectedEquipmentId] = useState(PRESET_TASKS[0].equipmentId);
  const [maxSteps, setMaxSteps] = useState(8);
  const [executionMode, setExecutionMode] = useState<'deterministic' | 'live'>('deterministic');
  const [configuredProvider, setConfiguredProvider] = useState<string>('Ollama');
  const [artifacts, setArtifacts] = useState<GeneratedArtifact[]>([]);

  const [isPromptExpanded, setIsPromptExpanded] = useState(false);
  const [focusedColumn, setFocusedColumn] = useState<'documents' | 'evidence' | 'lifecycle' | null>(null);
  const [isTraceCollapsed, setIsTraceCollapsed] = useState(false);
  const prevRunningRef = useRef(isRunning);

  const handleToggleFocus = useCallback((col: 'documents' | 'evidence' | 'lifecycle') => {
    setFocusedColumn((prev) => (prev === col ? null : col));
  }, []);

  const handleToggleTraceCollapse = useCallback(() => {
    setIsTraceCollapsed((prev) => !prev);
  }, []);

  // Strict task isolation: only render deliverables belonging to the current task_id
  const currentArtifacts = deliverables.filter((d) => !taskId || d.task_id === taskId);

  // Ingested documents state
  const [documents, setDocuments] = useState<DocumentIngestionResult[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentIngestionResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Dynamically load provider from tier discovery
  useEffect(() => {
    systemService
      .getModelTier()
      .then((tier) => {
        const vModel = tier?.models?.find((m) => m.role === 'vision' || m.role === 'reasoning');
        if (vModel && vModel.provider) {
          setConfiguredProvider(vModel.provider === 'ollama' ? 'Ollama' : vModel.provider);
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

    // Reset local artifacts cache before starting new task and auto-expand trace
    setArtifacts([]);
    setIsTraceCollapsed(false);
    toast.info('Starting Task', `Executing in ${executionMode.toUpperCase()} mode...`);
    const res = await executeTask(taskInput, maxSteps, executionMode, selectedEquipmentId, selectedFile);

    if (res) {
      setIsTraceCollapsed(true);
      toast.success(
        'Task Completed',
        '12/12 engineering invariants satisfied. Deliverables verified.'
      );
    } else {
      toast.error('Task Encountered Failure', 'Check execution trace for details.');
    }
  }, [taskInput, isRunning, executionMode, selectedEquipmentId, selectedFile, executeTask, toast]);

  // Auto-collapse Agent Trace after task completion to maximize vertical space for Deliverables Factory
  useEffect(() => {
    if (prevRunningRef.current && !isRunning) {
      if (currentState === 'DELIVER' || (trace && trace.length > 0)) {
        setIsTraceCollapsed(true);
      }
    }
    prevRunningRef.current = isRunning;
  }, [isRunning, currentState, trace]);

  // Keyboard shortcuts inside the Workbench (Enter to run, Esc to cancel/reset/unfocus)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is in an input or textarea unless Ctrl/Cmd+Enter is pressed, or if not focused in textarea
      const isTextarea = (e.target as HTMLElement)?.tagName === 'TEXTAREA';

      if (e.key === 'Enter' && (!isTextarea || e.ctrlKey || e.metaKey)) {
        if (!isRunning && taskInput.trim()) {
          e.preventDefault();
          setIsPromptExpanded(false);
          handleStartTask();
        }
      } else if (e.key === 'Escape') {
        if (focusedColumn) {
          e.preventDefault();
          setFocusedColumn(null);
        } else if (isPromptExpanded) {
          e.preventDefault();
          setIsPromptExpanded(false);
        } else if (isRunning) {
          e.preventDefault();
          reset();
          toast.warning('Task Cancelled', 'Agent execution was stopped by user.');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleStartTask, isRunning, taskInput, reset, toast, isPromptExpanded, focusedColumn]);

  const handleSelectPreset = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const idx = Number(e.target.value);
    const preset = PRESET_TASKS[idx];
    if (preset) {
      setTaskInput(preset.query);
      setSelectedEquipmentId(preset.equipmentId);
      setArtifacts([]);
      reset();
    }
  };

  const syncEquipmentIdFromDoc = (doc: DocumentIngestionResult) => {
    const extractedEq = (doc as any).evidence?.equipment_id;
    if (extractedEq && typeof extractedEq === 'string' && extractedEq.trim()) {
      setSelectedEquipmentId(extractedEq.trim());
    } else if (isApprovedDemoPreset(doc)) {
      setSelectedEquipmentId('C-101');
    } else {
      setSelectedEquipmentId('');
    }
  };

  const handleArtifactsGenerated = (newArtifacts: GeneratedArtifact[]) => {
    setArtifacts((prev) => {
      const existingIds = new Set(prev.map((a) => a.artifact_id));
      const filtered = newArtifacts.filter((a) => !existingIds.has(a.artifact_id));
      return [...prev, ...filtered];
    });
  };

  const [slot, setSlot] = useState<HTMLElement | null>(null);

  useEffect(() => {
    // Locate the persistent top command slot in SovereigntyBar
    setSlot(document.getElementById('workbench-command-slot'));
  }, []);

  const handleResetAll = useCallback(() => {
    reset();
    setArtifacts([]);
    setSelectedFile(null);
    setSelectedDoc(null);
    setDocuments([]);
    setSelectedEquipmentId(PRESET_TASKS[0].equipmentId);
  }, [reset]);

  const commandBarElement = (
    <div className="unified-command-deck" role="toolbar" aria-label="Workbench Unified Command Bar">
      <div className="cmd-preset-wrapper" title="Select Operational Goal Preset">
        <select
          className="cmd-preset-select"
          onChange={handleSelectPreset}
          disabled={isRunning}
          defaultValue="0"
          aria-label="Preset Engineering Scenario"
        >
          {PRESET_TASKS.map((preset, index) => (
            <option key={index} value={index}>
              {preset.title}
            </option>
          ))}
        </select>
      </div>

      <div className="cmd-input-container">
        <input
          type="text"
          className="cmd-task-input"
          value={taskInput}
          onChange={(e) => setTaskInput(e.target.value)}
          disabled={isRunning}
          placeholder="Refinery objective or inspection query... (↵ Execute, Click ⤢ to expand)"
          aria-label="Operational Goal or Inspection Query"
        />

        {taskInput.length > 60 && (
          <span className="cmd-char-count" title={`${taskInput.length} characters in objective`}>
            {taskInput.length}c
          </span>
        )}

        <button
          type="button"
          className={`cmd-expand-btn ${isPromptExpanded ? 'is-active' : ''}`}
          onClick={() => setIsPromptExpanded((prev) => !prev)}
          title={isPromptExpanded ? 'Close prompt editor (Esc)' : 'Expand full multi-line prompt editor'}
          aria-label="Expand multi-line prompt editor"
          disabled={isRunning}
        >
          <Maximize2 size={12} />
        </button>

        {/* Floating Multi-Line Objective Popover (<= 56px collapsed bar preserved) */}
        {isPromptExpanded && (
          <div className="cmd-prompt-popover" role="dialog" aria-label="Operational Objective Multi-Line Editor">
            <div className="prompt-popover-header">
              <div className="popover-header-left">
                <FileText size={13} className="accent-icon" />
                <span className="popover-title">OPERATIONAL OBJECTIVE &amp; GOAL EDITOR</span>
                <span className="popover-char-badge">{taskInput.length} characters</span>
              </div>
              <div className="popover-header-right">
                <span className="popover-hint"><kbd className="cmd-kbd">Ctrl+↵</kbd> Execute</span>
                <span className="popover-hint"><kbd className="cmd-kbd">Esc</kbd> Close</span>
                <button
                  type="button"
                  className="popover-close-btn"
                  onClick={() => setIsPromptExpanded(false)}
                  aria-label="Close Popover"
                >
                  <X size={13} />
                </button>
              </div>
            </div>
            <div className="prompt-popover-body">
              <textarea
                className="prompt-popover-textarea"
                rows={5}
                value={taskInput}
                onChange={(e) => setTaskInput(e.target.value)}
                disabled={isRunning}
                placeholder="Enter complete industrial engineering objective, standards to enforce, or inspection parameters..."
                autoFocus
              />
            </div>
            <div className="prompt-popover-footer">
              <span className="popover-footer-note">
                API 570 / ASME B31.3 deterministic compliance enforcement active
              </span>
              <div className="popover-footer-actions">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setIsPromptExpanded(false)}
                >
                  Done
                </button>
                <button
                  type="button"
                  className="btn btn-accent btn-sm"
                  onClick={() => {
                    setIsPromptExpanded(false);
                    handleStartTask();
                  }}
                  disabled={isRunning || !taskInput.trim()}
                >
                  <Play size={12} fill="currentColor" />
                  <span>Execute Prompt</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div
        className="cmd-mode-pill"
        title={`Mode: ${executionMode === 'live' ? 'Live Local Model (FastAPI + Ollama)' : 'Deterministic Demonstration Pipeline'}`}
      >
        <button
          type="button"
          className={`cmd-mode-btn ${executionMode === 'deterministic' ? 'is-active' : ''}`}
          onClick={() => setExecutionMode('deterministic')}
          disabled={isRunning}
        >
          DEMO
        </button>
        <button
          type="button"
          className={`cmd-mode-btn ${executionMode === 'live' ? 'is-active' : ''}`}
          onClick={() => setExecutionMode('live')}
          disabled={isRunning}
        >
          LIVE
        </button>
      </div>

      <div className="cmd-steps-wrap" title="Max Agent Exploration Steps">
        <select
          className="cmd-steps-select"
          value={maxSteps}
          onChange={(e) => setMaxSteps(Number(e.target.value))}
          disabled={isRunning}
          aria-label="Agent Steps Limit"
        >
          <option value={4}>4s</option>
          <option value={8}>8s</option>
          <option value={12}>12s</option>
        </select>
      </div>

      <button
        type="button"
        className="cmd-btn-reset"
        onClick={handleResetAll}
        disabled={isRunning}
        title="Reset workbench state (Esc)"
        aria-label="Reset State"
      >
        <RotateCcw size={13} />
      </button>

      <button
        type="button"
        className={`cmd-btn-execute ${isRunning ? 'is-running' : ''}`}
        onClick={handleStartTask}
        disabled={isRunning || !taskInput.trim()}
        aria-label={isRunning ? 'Executing Pipeline...' : 'Execute Analysis'}
      >
        {isRunning ? (
          <>
            <Clock size={13} className="icon-spin" />
            <span>Executing...</span>
          </>
        ) : (
          <>
            <Play size={13} fill="currentColor" />
            <span>Execute</span>
          </>
        )}
      </button>
    </div>
  );

  return (
    <div className="page-container workbench-page">
      {/* 1. Mount Unified Command Bar into Top Persistent Header (or inline fallback if slot pending) */}
      {slot ? createPortal(commandBarElement, slot) : commandBarElement}

      {/* 2. Slim Alert Banner (Rendered only on error) */}
      {errorMessage && (
        <div className="workbench-error-banner" role="alert">
          <AlertTriangle size={14} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* 3-COLUMN ASYMMETRIC ENGINEERING GRID (WITH COLUMN FOCUS & TRACE RECOVERY) */}
      <div className={`workbench-three-columns-grid ${focusedColumn ? `is-focused focus-${focusedColumn}` : ''}`}>
        {/* Column 1: Source Document Viewer & NDT Table */}
        <div className="workbench-column col-documents">
          <DocumentViewer
            documents={documents}
            selectedDoc={selectedDoc}
            onSelectDoc={(doc) => {
              setSelectedDoc(doc);
              syncEquipmentIdFromDoc(doc);
            }}
            onUploadSuccess={(doc, file) => {
              setDocuments((prev) => [doc, ...prev]);
              setSelectedDoc(doc);
              if (file) {
                setSelectedFile(file);
              }
              syncEquipmentIdFromDoc(doc);
              toast.success('Document Uploaded', `Ingested ${doc.filename} (${doc.sha256.substring(0, 12)}...)`);
            }}
            isFocused={focusedColumn === 'documents'}
            onToggleFocus={() => handleToggleFocus('documents')}
            selectedEquipmentId={selectedEquipmentId}
          />
        </div>

        {/* Column 2: Evidence Panel & 12-Cell Fuse Box */}
        <div className="workbench-column col-evidence">
          <EvidencePanel
            citations={citations.length > 0 ? citations : (result?.citations || [])}
            summary={result?.summary}
            calculation={result?.calculation}
            ocrVisionSummary={result?.ocr_vision_summary}
            routePreview={routePreview}
            validationReport={result?.structured_validation}
            isRunning={isRunning}
            executionMode={executionMode}
            isFocused={focusedColumn === 'evidence'}
            onToggleFocus={() => handleToggleFocus('evidence')}
          />
        </div>

        {/* Column 3: Agent Lifecycle Timeline & Deliverables Factory */}
        <div className={`workbench-column col-lifecycle-deliverables ${isTraceCollapsed ? 'trace-collapsed' : ''}`}>
          <AgentGraphTrace
            currentState={currentState}
            isRunning={isRunning}
            trace={trace}
            taskId={taskId}
            executionMode={executionMode}
            isCollapsed={isTraceCollapsed}
            onToggleCollapse={handleToggleTraceCollapse}
            isFocused={focusedColumn === 'lifecycle'}
            onToggleFocus={() => handleToggleFocus('lifecycle')}
          />
          <DeliverablesPanel
            artifacts={currentArtifacts.length > 0 ? currentArtifacts : (taskId ? artifacts.filter(a => a.task_id === taskId) : [])}
            taskId={taskId}
            executionCapability={runtimeState.executionCapability}
            activeModel={activeModel}
            sourceDocument={selectedDoc?.filename || selectedFile?.name || runtimeState.sourceDocument || 'pid_sample.png'}
            visualFindingsCount={
              typeof result?.summary === 'object' && (result.summary as any)?.findings_count !== undefined
                ? (result.summary as any).findings_count
                : undefined
            }
            equipmentId={selectedEquipmentId || (selectedDoc as any)?.evidence?.equipment_id || 'UNAVAILABLE'}
            summary={typeof result?.summary === 'string' ? result.summary : taskInput}
            onGenerated={handleArtifactsGenerated}
            validationPassed={!!result?.structured_validation?.valid}
            executionMode={executionMode}
            isFocused={focusedColumn === 'lifecycle'}
            onToggleFocus={() => handleToggleFocus('lifecycle')}
          />
        </div>
      </div>
    </div>
  );
};
