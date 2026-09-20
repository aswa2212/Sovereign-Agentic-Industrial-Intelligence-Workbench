import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { useAgentTask } from '../hooks/useAgentTask';
import { AgentRunResponse, AgentState, StateTransition, CitationSource } from '../types/agent';
import { RouteResponse } from '../types/api';
import { DocumentIngestionResult } from '../types/documents';
import { GeneratedArtifact } from '../types/deliverables';

export interface WorkbenchSessionContextValue {
  // Agent task execution state & operations
  isRunning: boolean;
  taskId: string | null;
  currentState: AgentState;
  routePreview: RouteResponse | null;
  trace: StateTransition[];
  result: AgentRunResponse['result'] | null;
  citations: CitationSource[];
  deliverables: GeneratedArtifact[];
  errors: string[];
  errorMessage: string | null;
  previewRoute: (taskText: string) => Promise<RouteResponse | null>;
  executeTask: (
    taskText: string,
    maxSteps?: number,
    mode?: 'deterministic' | 'live',
    componentId?: string | null,
    file?: File | null
  ) => Promise<AgentRunResponse | null>;
  resetTask: () => void;

  // Active workflow document & evidence state
  documents: DocumentIngestionResult[];
  setDocuments: React.Dispatch<React.SetStateAction<DocumentIngestionResult[]>>;
  selectedDoc: DocumentIngestionResult | null;
  setSelectedDoc: React.Dispatch<React.SetStateAction<DocumentIngestionResult | null>>;
  selectedFile: File | null;
  setSelectedFile: React.Dispatch<React.SetStateAction<File | null>>;
  artifacts: GeneratedArtifact[];
  setArtifacts: React.Dispatch<React.SetStateAction<GeneratedArtifact[]>>;
  taskInput: string;
  setTaskInput: React.Dispatch<React.SetStateAction<string>>;
  selectedEquipmentId: string;
  setSelectedEquipmentId: React.Dispatch<React.SetStateAction<string>>;
  maxSteps: number;
  setMaxSteps: React.Dispatch<React.SetStateAction<number>>;
  executionMode: 'deterministic' | 'live';
  setExecutionMode: React.Dispatch<React.SetStateAction<'deterministic' | 'live'>>;
  focusedColumn: 'documents' | 'evidence' | 'lifecycle' | null;
  setFocusedColumn: React.Dispatch<React.SetStateAction<'documents' | 'evidence' | 'lifecycle' | null>>;
  isTraceCollapsed: boolean;
  setIsTraceCollapsed: React.Dispatch<React.SetStateAction<boolean>>;
  isPromptExpanded: boolean;
  setIsPromptExpanded: React.Dispatch<React.SetStateAction<boolean>>;

  // Dedicated Workbench Refresh / Reset handler
  handleResetAll: () => void;
}

const WorkbenchSessionContext = createContext<WorkbenchSessionContextValue | null>(null);

export const WorkbenchSessionProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
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
    reset: resetTask,
  } = useAgentTask();

  const [documents, setDocuments] = useState<DocumentIngestionResult[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentIngestionResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [artifacts, setArtifacts] = useState<GeneratedArtifact[]>([]);
  const [taskInput, setTaskInput] = useState('');
  const [selectedEquipmentId, setSelectedEquipmentId] = useState('');
  const [maxSteps, setMaxSteps] = useState(8);
  const [executionMode, setExecutionMode] = useState<'deterministic' | 'live'>('deterministic');
  const [focusedColumn, setFocusedColumn] = useState<'documents' | 'evidence' | 'lifecycle' | null>(null);
  const [isTraceCollapsed, setIsTraceCollapsed] = useState(false);
  const [isPromptExpanded, setIsPromptExpanded] = useState(false);

  const handleResetAll = useCallback(() => {
    resetTask();
    setArtifacts([]);
    setSelectedFile(null);
    setSelectedDoc(null);
    setDocuments([]);
    setSelectedEquipmentId('');
    setTaskInput('');
  }, [resetTask]);

  const value: WorkbenchSessionContextValue = {
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
    resetTask,

    documents,
    setDocuments,
    selectedDoc,
    setSelectedDoc,
    selectedFile,
    setSelectedFile,
    artifacts,
    setArtifacts,
    taskInput,
    setTaskInput,
    selectedEquipmentId,
    setSelectedEquipmentId,
    maxSteps,
    setMaxSteps,
    executionMode,
    setExecutionMode,
    focusedColumn,
    setFocusedColumn,
    isTraceCollapsed,
    setIsTraceCollapsed,
    isPromptExpanded,
    setIsPromptExpanded,

    handleResetAll,
  };

  return (
    <WorkbenchSessionContext.Provider value={value}>
      {children}
    </WorkbenchSessionContext.Provider>
  );
};

export const useWorkbenchSession = (): WorkbenchSessionContextValue => {
  const context = useContext(WorkbenchSessionContext);
  if (!context) {
    throw new Error('useWorkbenchSession must be used within a WorkbenchSessionProvider');
  }
  return context;
};
