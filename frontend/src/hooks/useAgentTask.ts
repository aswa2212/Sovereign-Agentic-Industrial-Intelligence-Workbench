import { useState, useCallback } from 'react';
import { agentService } from '../services/agent';
import { AgentRunResponse, AgentState, StateTransition, CitationSource } from '../types/agent';
import { RouteResponse } from '../types/api';

export interface TaskExecutionState {
  isRunning: boolean;
  taskId: string | null;
  currentState: AgentState;
  routePreview: RouteResponse | null;
  trace: StateTransition[];
  result: AgentRunResponse['result'] | null;
  citations: CitationSource[];
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
      if (mode === 'live') {
        const wfRes = await agentService.runWorkflow(taskText, 'live', componentId);
        const transitions: StateTransition[] = (wfRes.stages || []).map((st: any, idx: number) => ({
          from_state: (idx === 0 ? 'IDLE' : 'EXECUTE') as AgentState,
          to_state: (st.status === 'SUCCESS' ? (idx === (wfRes.stages.length - 1) ? 'DELIVER' : 'EXECUTE') : 'FAILED') as AgentState,
          timestamp: st.completed_at || new Date().toISOString(),
          message: `[${st.stage_name}]: ${st.status} (${st.duration_ms}ms)`,
          metadata: st.details,
        }));

        setState((prev) => ({
          ...prev,
          isRunning: false,
          taskId: wfRes.task_id || wfRes.workflow_id,
          currentState: wfRes.status === 'COMPLETED' ? 'DELIVER' : 'FAILED',
          trace: transitions.length > 0 ? transitions : prev.trace,
          result: {
            task: taskText,
            status: wfRes.status,
            summary: wfRes.ocr_vision_summary?.summary || 'Completed live workflow execution.',
            citations_count: (wfRes.rag_citations || []).length,
            citations: (wfRes.rag_citations || []).map((c: any) => ({
              source_document: c.source_document || 'Reference Document',
              page_number: c.page_number || 1,
              chunk_id: c.chunk_id || '',
              text: c.excerpt || '',
            })),
            calculation: wfRes.calculation_result,
            structured_validation: wfRes.validation_result,
          },
          citations: (wfRes.rag_citations || []).map((c: any) => ({
            source_document: c.source_document || 'Reference Document',
            page_number: c.page_number || 1,
            chunk_id: c.chunk_id || '',
            text: c.excerpt || '',
          })),
          errors: wfRes.errors || [],
          errorMessage: wfRes.status !== 'COMPLETED' ? (wfRes.errors?.[0] || 'Live workflow failed') : null,
        }));

        return wfRes;
      }

      // Execute deterministic task via backend orchestrator
      const response = await agentService.runTask(taskText, maxSteps);

      setState((prev) => ({
        ...prev,
        isRunning: false,
        taskId: response.task_id,
        currentState: response.final_state,
        trace: response.execution_trace.length > 0 ? response.execution_trace : prev.trace,
        result: response.result || null,
        citations: response.citations || [],
        errors: response.errors || [],
        errorMessage: response.status === 'failed'
          ? (response.errors[0] || 'Task execution terminated with status FAILED.')
          : null,
      }));

      return response;
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
