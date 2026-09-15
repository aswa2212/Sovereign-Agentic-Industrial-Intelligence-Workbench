import React from 'react';
import { AgentState, StateTransition } from '../types/agent';
import { CheckCircle2, Clock, AlertCircle, Activity } from 'lucide-react';
import { DataSourceBadge } from './DataSourceBadge';

interface AgentGraphTraceProps {
  currentState: AgentState;
  isRunning: boolean;
  trace: StateTransition[];
  taskId?: string | null;
  executionMode?: 'deterministic' | 'live';
}

const ORDERED_STATES: AgentState[] = [
  'RECEIVE',
  'UNDERSTAND',
  'PLAN',
  'EXECUTE',
  'OBSERVE',
  'REFLECT',
  'VALIDATE',
  'FINALIZE',
  'DELIVER',
];

export const AgentGraphTrace: React.FC<AgentGraphTraceProps> = ({
  currentState,
  isRunning,
  trace,
  taskId,
  executionMode = 'deterministic',
}) => {
  const visitedStates = new Set<AgentState>(trace.map((t) => t.to_state));
  if (currentState !== 'IDLE' && currentState !== 'FAILED') {
    visitedStates.add(currentState);
  }

  const currentIndex = ORDERED_STATES.indexOf(currentState);
  const isFailed = currentState === 'FAILED';
  const hasStarted = trace.length > 0;

  const getStateStatus = (state: AgentState) => {
    if (isFailed && state === currentState) return 'failed';
    if (state === currentState && isRunning) return 'active';
    if (visitedStates.has(state)) return 'completed';
    const stateIdx = ORDERED_STATES.indexOf(state);
    if (currentIndex > -1 && stateIdx < currentIndex) return 'completed';
    return 'pending';
  };

  return (
    <div className="workbench-panel agent-trace-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-header-title-group">
          <Activity size={16} className={`panel-header-icon ${isRunning ? 'icon-spin' : ''}`} />
          <div>
            <h2 className="panel-title">Agent Execution Graph</h2>
            <span className="panel-subtitle">11-Stage State Machine</span>
          </div>
        </div>

        <div className="panel-header-badges">
          {hasStarted && (
            <DataSourceBadge
              source={executionMode === 'live' ? 'LIVE' : 'DEMO'}
              label={executionMode === 'live' ? 'LIVE LOCAL MODEL' : 'DEMO DETERMINISTIC'}
              size="sm"
            />
          )}
          {taskId && (
            <span className="badge-pill badge-neutral">
              TASK: {taskId.slice(0, 8)}
            </span>
          )}
          {isFailed ? (
            <span className="badge-pill badge-error">
              <AlertCircle size={12} />
              <span>FAILED</span>
            </span>
          ) : isRunning ? (
            <span className="badge-pill badge-warning">
              <Clock size={12} className="icon-spin" />
              <span>RUNNING ({currentState})</span>
            </span>
          ) : currentState === 'DELIVER' || visitedStates.has('DELIVER') ? (
            <span className="badge-pill badge-success">
              <CheckCircle2 size={12} />
              <span>COMPLETED</span>
            </span>
          ) : (
            <span className="badge-pill badge-neutral">IDLE</span>
          )}
        </div>
      </div>

      <div className="trace-body">
        {/* Pipeline Nodes Strip */}
        <div className="state-pipeline-strip">
          {ORDERED_STATES.map((state, idx) => {
            const status = getStateStatus(state);
            return (
              <React.Fragment key={state}>
                <div
                  className={`pipeline-node node-${status}`}
                  title={`State: ${state} (${status})`}
                >
                  <div className="pipeline-dot" />
                  <span className="pipeline-label">{state}</span>
                </div>
                {idx < ORDERED_STATES.length - 1 && (
                  <div className={`pipeline-connector conn-${status === 'completed' ? 'active' : 'inactive'}`} />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Step-by-Step Transition Log */}
        <div className="trace-events-list">
          {trace.length === 0 ? (
            <div className="empty-trace-state">
              <span>Agent idle. Click &ldquo;Start Analysis&rdquo; to launch the 11-stage autonomous execution sequence.</span>
            </div>
          ) : (
            trace.map((tr, index) => (
              <div key={index} className="trace-event-item">
                <div className="trace-event-top">
                  <div className="trace-states-pill">
                    <code>{tr.from_state}</code>
                    <span className="arrow-sep">&rarr;</span>
                    <code>{tr.to_state}</code>
                  </div>
                  <span className="trace-timestamp">
                    {new Date(tr.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                {tr.message && <div className="trace-message">{tr.message}</div>}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
