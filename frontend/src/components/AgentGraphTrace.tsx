import React from 'react';
import { AgentState, StateTransition } from '../types/agent';
import { CheckCircle2, Clock, AlertCircle, Activity, ChevronDown, ChevronUp, Maximize2, Minimize2 } from 'lucide-react';
import { DataSourceBadge } from './DataSourceBadge';

interface AgentGraphTraceProps {
  currentState: AgentState;
  isRunning: boolean;
  trace: StateTransition[];
  taskId?: string | null;
  executionMode?: 'deterministic' | 'live';
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  isFocused?: boolean;
  onToggleFocus?: () => void;
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
  isCollapsed = false,
  onToggleCollapse,
  isFocused = false,
  onToggleFocus,
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
    <div className={`workbench-panel agent-trace-panel ${isCollapsed ? 'is-collapsed' : ''}`}>
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-header-title-group">
          <Activity size={16} className={`panel-header-icon ${isRunning ? 'icon-spin' : ''}`} />
          <div>
            <h2 className="panel-title">Agent Execution Graph</h2>
            <span className="panel-subtitle">
              {isCollapsed
                ? (currentState === 'DELIVER' || visitedStates.has('DELIVER')
                    ? `${visitedStates.size}/11 States Completed • Verified`
                    : isFailed
                    ? 'Sequence Halted (Failed)'
                    : '11-Stage Sequence (Collapsed)')
                : '11-Stage State Machine'}
            </span>
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
          {onToggleCollapse && (
            <button
              type="button"
              className="panel-header-btn"
              onClick={onToggleCollapse}
              title={isCollapsed ? 'Expand Agent Trace (View event sequence)' : 'Collapse Agent Trace (Recover Deliverables space)'}
              aria-label={isCollapsed ? 'Expand Agent Trace' : 'Collapse Agent Trace'}
            >
              {isCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
            </button>
          )}
          {onToggleFocus && (
            <button
              type="button"
              className={`panel-header-btn ${isFocused ? 'is-active' : ''}`}
              onClick={onToggleFocus}
              title={isFocused ? 'Restore 3-Column Cockpit (Esc)' : 'Focus Lifecycle Column (Full Width)'}
              aria-label={isFocused ? 'Restore 3-Column Cockpit' : 'Focus Lifecycle Column'}
            >
              {isFocused ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
            </button>
          )}
        </div>
      </div>

      {!isCollapsed && (
      <div className="trace-body">
        {/* Pipeline Nodes Strip */}
        <div className="state-pipeline-strip" role="list" aria-label="11-Stage Agent Execution Pipeline">
          {ORDERED_STATES.map((state, idx) => {
            const status = getStateStatus(state);
            return (
              <React.Fragment key={state}>
                <div
                  className={`pipeline-node node-${status}`}
                  title={`Stage ${idx + 1}/9: ${state} (${status})`}
                  role="listitem"
                >
                  <div className="pipeline-dot" />
                  <span className="pipeline-label">{state}</span>
                </div>
                {idx < ORDERED_STATES.length - 1 && (
                  <span
                    className={`pipeline-arrow ${status === 'completed' ? 'is-active' : ''}`}
                    aria-hidden="true"
                  >
                    &rarr;
                  </span>
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
      )}
    </div>
  );
};
