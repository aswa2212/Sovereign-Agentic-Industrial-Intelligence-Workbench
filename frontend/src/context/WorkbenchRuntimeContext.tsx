import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { RouteResponse } from '../types/api';

export interface ModelAllocation {
  assigned_role?: string;
  tier_role?: string;
  assigned_model_tag?: string | null;
  vision_model_tag?: string | null;
  resolved_model_tag?: string | null;
  provider?: string;
  available_models_count?: number;
  is_mock?: boolean;
}

export interface WorkbenchRuntimeState {
  activeModel: string | null;
  routedModel: string | null;
  routingDecision: RouteResponse | null;
  modelAllocation: ModelAllocation | null;
  executionCapability: string | null;
  taskId: string | null;
  sourceDocument: string | null;
}

export interface WorkbenchRuntimeContextValue {
  runtimeState: WorkbenchRuntimeState;
  activeModel: string;
  setRuntimeExecution: (response: {
    active_model?: string | null;
    routing_decision?: RouteResponse | null;
    model_allocation?: ModelAllocation | null;
    execution_capability?: string | null;
    task_id?: string | null;
    document_summary?: { filename?: string } | null;
  }) => void;
  setPredictedRoute: (decision: RouteResponse | null, allocatedModel?: string | null) => void;
  resetRuntimeState: () => void;
}

const initialRuntimeState: WorkbenchRuntimeState = {
  activeModel: null,
  routedModel: null,
  routingDecision: null,
  modelAllocation: null,
  executionCapability: null,
  taskId: null,
  sourceDocument: null,
};

const WorkbenchRuntimeContext = createContext<WorkbenchRuntimeContextValue | null>(null);

export const WorkbenchRuntimeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [runtimeState, setRuntimeState] = useState<WorkbenchRuntimeState>(initialRuntimeState);

  const setRuntimeExecution = useCallback(
    (response: {
      active_model?: string | null;
      routing_decision?: RouteResponse | null;
      model_allocation?: ModelAllocation | null;
      execution_capability?: string | null;
      task_id?: string | null;
      document_summary?: { filename?: string } | null;
    }) => {
      // Rule 3: activeModel represents the model actually invoked/allocated by backend
      const resolvedActiveModel =
        response.active_model ??
        response.model_allocation?.resolved_model_tag ??
        response.model_allocation?.assigned_model_tag ??
        null;

      setRuntimeState({
        activeModel: resolvedActiveModel,
        routedModel: resolvedActiveModel,
        routingDecision: response.routing_decision ?? null,
        modelAllocation: response.model_allocation ?? null,
        executionCapability: response.execution_capability ?? null,
        taskId: response.task_id ?? null,
        sourceDocument: response.document_summary?.filename ?? null,
      });
    },
    []
  );

  const setPredictedRoute = useCallback(
    (decision: RouteResponse | null, allocatedModel?: string | null) => {
      setRuntimeState((prev) => ({
        ...prev,
        routingDecision: decision,
        routedModel: allocatedModel ?? prev.routedModel,
      }));
    },
    []
  );

  const resetRuntimeState = useCallback(() => {
    setRuntimeState(initialRuntimeState);
  }, []);

  const activeModel = runtimeState.activeModel || runtimeState.routedModel || 'MODEL UNAVAILABLE';

  return (
    <WorkbenchRuntimeContext.Provider
      value={{
        runtimeState,
        activeModel,
        setRuntimeExecution,
        setPredictedRoute,
        resetRuntimeState,
      }}
    >
      {children}
    </WorkbenchRuntimeContext.Provider>
  );
};

export const useWorkbenchRuntime = (): WorkbenchRuntimeContextValue => {
  const context = useContext(WorkbenchRuntimeContext);
  if (!context) {
    throw new Error('useWorkbenchRuntime must be used within a WorkbenchRuntimeProvider');
  }
  return context;
};
