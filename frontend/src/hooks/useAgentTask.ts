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

  const executeTask = useCallback(async (taskText: string, maxSteps = 8) => {
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
          message: `Initiated task: ${taskText.slice(0, 60)}...`,
        },
      ],
    }));

    try {
      // Execute via backend orchestrator
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
