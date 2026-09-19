import { useState, useCallback } from 'react';
import { agentService } from '../services/agent';
import { AgentRunResponse, AgentState, StateTransition, CitationSource } from '../types/agent';
import { RouteResponse } from '../types/api';
import { GeneratedArtifact } from '../types/deliverables';
import { useWorkbenchRuntime } from '../context/WorkbenchRuntimeContext';

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
  const { setRuntimeExecution, setPredictedRoute, resetRuntimeState } = useWorkbenchRuntime();

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
      setPredictedRoute(decision, null);
      return decision;
    } catch {
      return null;
    }
  }, [setPredictedRoute]);

  const executeTask = useCallback(async (
    taskText: string,
    maxSteps = 8,
    mode: 'deterministic' | 'live' = 'deterministic',
    componentId?: string | null,
    file?: File | null,
  ) => {
    // Rule 8: Clear ALL previous execution state before sending the request
    resetRuntimeState();
    setState({
      isRunning: true,
      taskId: null,
      currentState: 'RECEIVE',
      routePreview: state.routePreview,
      executionMode: mode,
      errorMessage: null,
      errors: [],
      deliverables: [],
      result: null,
      citations: [],
      trace: [
        {
          from_state: 'IDLE',
          to_state: 'RECEIVE',
          timestamp: new Date().toISOString(),
          message: `Initiated task in ${mode.toUpperCase()} mode: ${taskText.slice(0, 60)}...`,
        },
      ],
    });

    try {
      // Execute the 11-stage integration workflow for both deterministic & live modes
      const wfRes = await agentService.runWorkflow(taskText, mode, componentId, file);

      const transitions: StateTransition[] = (wfRes.stages || []).map((st: any, idx: number) => ({
        from_state: (idx === 0 ? 'IDLE' : 'EXECUTE') as AgentState,
        to_state: (st.status === 'SUCCESS' ? (idx === (wfRes.stages.length - 1) ? 'DELIVER' : 'EXECUTE') : (st.status === 'SKIPPED' ? 'EXECUTE' : 'FAILED')) as AgentState,
        timestamp: st.completed_at || new Date().toISOString(),
        message: `[${st.stage_name}]: ${st.status} (${st.duration_ms?.toFixed(1) || 0}ms)`,
        metadata: st.details,
      }));

      const currentTaskId = wfRes.task_id || wfRes.workflow_id;

      const mappedDeliverables: GeneratedArtifact[] = (wfRes.deliverables || []).map((d: any) => ({
        artifact_id: d.artifact_id,
        task_id: currentTaskId,
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

      // Synchronize runtime context strictly from the backend response facts
      setRuntimeExecution({
        active_model: wfRes.active_model,
        routing_decision: wfRes.routing_decision,
        model_allocation: wfRes.model_allocation,
        execution_capability: wfRes.execution_capability,
        task_id: currentTaskId,
        document_summary: wfRes.document_summary,
      });

      // Extract governing CML if present from evidence summary or calculation
      const governingCml =
        wfRes.calculation_result?.governing_cml ||
        wfRes.evidence_summary?.selected_measurement?.cml_tag ||
        wfRes.evidence_summary?.selected_measurement?.location_desc ||
        wfRes.calculation_result?.component_id;

      const calcWithCml = wfRes.calculation_result
        ? {
            ...wfRes.calculation_result,
            governing_cml: governingCml,
          }
        : undefined;

      const summaryText =
        wfRes.summary ||
        wfRes.ocr_vision_summary?.summary ||
        (wfRes.status === 'COMPLETED' ? 'Completed autonomous engineering workflow execution.' : '');

      // Entirely replace state with the new response (do NOT merge with previous run)
      setState({
        isRunning: false,
        taskId: currentTaskId,
        currentState: wfRes.status === 'COMPLETED' ? 'DELIVER' : 'FAILED',
        routePreview: wfRes.routing_decision || state.routePreview,
        trace: transitions.length > 0 ? transitions : [],
        deliverables: mappedDeliverables,
        result: {
          task: taskText,
          status: wfRes.status,
          summary: summaryText,
          citations_count: mappedCitations.length,
          citations: mappedCitations,
          calculation: calcWithCml,
          structured_validation: wfRes.validation_result,
          ocr_vision_summary: wfRes.ocr_vision_summary,
          governing_cml: governingCml,
        },
        citations: mappedCitations,
        executionMode: mode,
        errors: wfRes.errors || [],
        errorMessage: wfRes.status !== 'COMPLETED' ? (wfRes.errors?.[0] || 'Workflow execution failed') : null,
      });

      return wfRes;
    } catch (err: any) {
      setState({
        isRunning: false,
        taskId: null,
        currentState: 'FAILED',
        routePreview: state.routePreview,
        trace: state.trace,
        deliverables: [],
        result: null,
        citations: [],
        executionMode: mode,
        errorMessage: err.message || 'Unexpected failure executing agent task',
        errors: [err.message || 'Workflow execution error'],
      });
      return null;
    }
  }, [resetRuntimeState, setRuntimeExecution, state.routePreview, state.trace]);

  const reset = useCallback(() => {
    resetRuntimeState();
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
  }, [resetRuntimeState]);

  return {
    ...state,
    previewRoute,
    executeTask,
    reset,
  };
}

