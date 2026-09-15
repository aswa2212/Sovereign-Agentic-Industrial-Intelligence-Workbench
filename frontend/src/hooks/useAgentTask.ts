import { useState, useCallback } from 'react';
import { agentService } from '../services/agent';
import { AgentRunResponse, AgentState, StateTransition, CitationSource } from '../types/agent';
import { RouteResponse } from '../types/api';
import { GeneratedArtifact } from '../types/deliverables';

export interface TaskExecutionState {
  isRunning: boolean;
  taskId: string | null;
  currentState: AgentState;
  routePreview: RouteResponse | null;
  trace: StateTransition[];
  result: AgentRunResponse['result'] | null;
  citations: CitationSource[];
  deliverables: GeneratedArtifact[];
  executionMode: 'deterministic' | 'live';
  errors: string[];
  errorMessage: string | null;
}

export function useAgentTask() {
  const [state, setState] = useState<TaskExecutionState>({
    isRunning: false,
    taskId: null,
    currentState: 'IDLE',
    routePreview: null,
    trace: [],
    result: null,
    citations: [],
    deliverables: [],
    executionMode: 'deterministic',
    errors: [],
    errorMessage: null,
  });

  const previewRoute = useCallback(async (taskText: string) => {
    if (!taskText.trim()) return null;
    try {
      const decision = await agentService.routeTask(taskText);
      setState((prev) => ({ ...prev, routePreview: decision }));
      return decision;
    } catch {
      return null;
    }
  }, []);

  const executeTask = useCallback(async (
    taskText: string,
    maxSteps = 8,
    mode: 'deterministic' | 'live' = 'deterministic',
    componentId = 'C-101',
  ) => {
    setState((prev) => ({
      ...prev,
      isRunning: true,
      currentState: 'RECEIVE',
      executionMode: mode,
      errorMessage: null,
      errors: [],
      trace: [
        {
          from_state: 'IDLE',
          to_state: 'RECEIVE',
          timestamp: new Date().toISOString(),
          message: `Initiated task in ${mode.toUpperCase()} mode: ${taskText.slice(0, 60)}...`,
        },
      ],
    }));

    try {
      // Execute the 11-stage integration workflow for both deterministic & live modes
      const wfRes = await agentService.runWorkflow(taskText, mode, componentId);

      const transitions: StateTransition[] = (wfRes.stages || []).map((st: any, idx: number) => ({
        from_state: (idx === 0 ? 'IDLE' : 'EXECUTE') as AgentState,
        to_state: (st.status === 'SUCCESS' ? (idx === (wfRes.stages.length - 1) ? 'DELIVER' : 'EXECUTE') : 'FAILED') as AgentState,
        timestamp: st.completed_at || new Date().toISOString(),
        message: `[${st.stage_name}]: ${st.status} (${st.duration_ms?.toFixed(1) || 0}ms)`,
        metadata: st.details,
      }));

      const mappedDeliverables: GeneratedArtifact[] = (wfRes.deliverables || []).map((d: any) => ({
        artifact_id: d.artifact_id,
        task_id: wfRes.task_id || wfRes.workflow_id,
        format: d.format,
        filename: d.filename,
        file_size_bytes: d.file_size_bytes,
        sha256_hash: d.sha256,
        download_url: d.download_url,
        created_at: wfRes.completed_at || new Date().toISOString(),
        validation_status: 'PASSED',
      }));

      const mappedCitations: CitationSource[] = (wfRes.rag_citations || []).map((c: any) => ({
        source_document: c.source_document || 'Reference Document',
        page_number: c.page_number || 1,
        chunk_id: c.chunk_id || '',
        text: c.excerpt || '',
        similarity_score: c.similarity_score,
      }));

      setState((prev) => ({
        ...prev,
        isRunning: false,
        taskId: wfRes.task_id || wfRes.workflow_id,
        currentState: wfRes.status === 'COMPLETED' ? 'DELIVER' : 'FAILED',
        trace: transitions.length > 0 ? transitions : prev.trace,
        deliverables: mappedDeliverables,
        result: {
          task: taskText,
          status: wfRes.status,
          summary: wfRes.ocr_vision_summary?.summary || 'Completed autonomous engineering workflow execution.',
          citations_count: mappedCitations.length,
          citations: mappedCitations,
          calculation: wfRes.calculation_result,
          structured_validation: wfRes.validation_result,
        },
        citations: mappedCitations,
        errors: wfRes.errors || [],
        errorMessage: wfRes.status !== 'COMPLETED' ? (wfRes.errors?.[0] || 'Workflow execution failed') : null,
      }));

      return wfRes;
    } catch (err: any) {
      setState((prev) => ({
        ...prev,
        isRunning: false,
        currentState: 'FAILED',
        errorMessage: err.message || 'Unexpected failure executing agent task',
        errors: [err.message || 'Workflow execution error'],
      }));
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    setState({
      isRunning: false,
      taskId: null,
      currentState: 'IDLE',
      routePreview: null,
      trace: [],
      result: null,
      citations: [],
      deliverables: [],
      executionMode: 'deterministic',
      errors: [],
      errorMessage: null,
    });
  }, []);

  return {
    ...state,
    previewRoute,
    executeTask,
    reset,
  };
}
