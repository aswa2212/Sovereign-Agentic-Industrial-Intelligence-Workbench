import React, { useState } from 'react';
import { AgentState, StateTransition } from '../types/agent';
import { CheckCircle2, Clock, AlertCircle, ChevronDown, ChevronUp, Maximize2, Minimize2, GitCommit, ListFilter } from 'lucide-react';

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

const STAGE_METADATA: Record<string, { indexStr: string; desc: string }> = {
  IDLE: { indexStr: '00', desc: 'Standby state' },
  RECEIVE: { indexStr: '01', desc: 'Ingest document & verify payload' },
  UNDERSTAND: { indexStr: '02', desc: 'Schema bind & entity extraction' },
  PLAN: { indexStr: '03', desc: 'Formulate ASME / API compliance strategy' },
  EXECUTE: { indexStr: '04', desc: 'Deterministic engineering computation' },
  OBSERVE: { indexStr: '05', desc: 'Capture numerical gauging & bounding' },
  REFLECT: { indexStr: '06', desc: 'Cross-check invariant constraints' },
  VALIDATE: { indexStr: '07', desc: 'Evaluate 12 fail-closed invariants' },
  FINALIZE: { indexStr: '08', desc: 'Generate cryptographic audit record' },
  DELIVER: { indexStr: '09', desc: 'Compile verified DOCX & XLSX artifacts' },
  FAILED: { indexStr: 'XX', desc: 'Execution halted upon error' },
};

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
  const [activeView, setActiveView] = useState<'pipeline' | 'events'>('pipeline');

  const visitedStates = new Set<AgentState>(trace.map((t) => t.to_state));
  if (currentState !== 'IDLE' && currentState !== 'FAILED') {
    visitedStates.add(currentState);
  }

  const currentIndex = ORDERED_STATES.indexOf(currentState);
  const isFailed = currentState === 'FAILED';
  const hasStarted = trace.length > 0 || (currentState !== 'IDLE' && currentIndex >= 0);

  const getStateStatus = (state: AgentState): 'completed' | 'active' | 'failed' | 'pending' => {
    if (isFailed && state === currentState) return 'failed';
    if (state === currentState && isRunning) return 'active';
    if (visitedStates.has(state)) return 'completed';
    const stateIdx = ORDERED_STATES.indexOf(state);
    if (currentIndex > -1 && stateIdx < currentIndex) return 'completed';
    return 'pending';
  };

  return (
    <div className={`workbench-panel agent-trace-panel ${isCollapsed ? 'is-collapsed' : ''}`}>
      {/* Section 9: Agent Graph Header - Improved Hierarchy & Balanced Controls */}
      <div className="panel-header agent-graph-header">
        <div className="panel-header-title-group">
          <h2 className="panel-title">AGENT EXECUTION GRAPH</h2>
          <span className="panel-subtitle">11-STAGE STATE MACHINE</span>
        </div>

        <div className="panel-header-badges">
          {isFailed ? (
            <span className="fuse-status-pill status-failed">
              <AlertCircle size={12} />
              <span>FAILED</span>
            </span>
          ) : isRunning ? (
            <span className="fuse-status-pill status-evaluating">
              <Clock size={12} className="icon-spin" />
              <span>RUNNING ({currentState})</span>
            </span>
          ) : currentState === 'DELIVER' || visitedStates.has('DELIVER') ? (
            <span className="fuse-status-pill status-passed">
              <CheckCircle2 size={12} />
              <span>COMPLETED</span>
            </span>
          ) : (
            <span className="fuse-status-pill status-standby">IDLE</span>
          )}

          {onToggleCollapse && (
            <button
              type="button"
              className="panel-header-btn"
              onClick={onToggleCollapse}
              title={isCollapsed ? 'Expand Agent Execution Graph' : 'Collapse Agent Execution Graph'}
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
          {/* Section 10: Deliberate Idle State when no task is active */}
          {!hasStarted ? (
            <div className="agent-graph-idle-container">
              <div className="agent-idle-badge">
                <span className="agent-idle-dot" />
                <span className="agent-idle-status">IDLE</span>
              </div>
              <h3 className="agent-idle-headline">No active engineering task.</h3>
              <p className="agent-idle-subtext">
                Upload a document and execute an analysis to begin.
              </p>

              {/* Standby Pipeline Schematic */}
              <div className="idle-pipeline-standby" aria-label="Standby Engineering Pipeline Preview">
                <div className="standby-header-label">STANDBY PIPELINE SEQUENCE:</div>
                <div className="standby-nodes-row">
                  {ORDERED_STATES.map((st, i) => (
                    <React.Fragment key={st}>
                      <span className="standby-node" title={STAGE_METADATA[st].desc}>
                        {st}
                      </span>
                      {i < ORDERED_STATES.length - 1 && <span className="standby-arrow">&rarr;</span>}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Secondary View Switcher for Active / Historical Pipeline */}
              <div className="agent-view-switch-bar">
                <button
                  type="button"
                  className={`view-switch-btn ${activeView === 'pipeline' ? 'is-active' : ''}`}
                  onClick={() => setActiveView('pipeline')}
                >
                  <GitCommit size={12} />
                  <span>Pipeline Sequence</span>
                </button>
                <button
                  type="button"
                  className={`view-switch-btn ${activeView === 'events' ? 'is-active' : ''}`}
                  onClick={() => setActiveView('events')}
                >
                  <ListFilter size={12} />
                  <span>Transitions ({trace.length})</span>
                </button>
              </div>

              {activeView === 'pipeline' ? (
                /* Sections 7, 8, 11: Industrial Engineering Control Sequence Pipeline */
                <div className="industrial-pipeline-ladder" role="list" aria-label="Connected Industrial Pipeline">
                  {ORDERED_STATES.map((state, idx) => {
                    const status = getStateStatus(state);
                    const meta = STAGE_METADATA[state];
                    const isLast = idx === ORDERED_STATES.length - 1;

                    // Connector state depends on the progression
                    const nextState = !isLast ? ORDERED_STATES[idx + 1] : null;
                    const nextStatus = nextState ? getStateStatus(nextState) : null;
                    const connectorStatus =
                      status === 'completed' && (nextStatus === 'completed' || nextStatus === 'active')
                        ? 'connector-completed'
                        : status === 'active'
                        ? 'connector-active'
                        : 'connector-pending';

                    return (
                      <div key={state} className="pipeline-ladder-step" role="listitem">
                        <div className={`pipeline-ladder-node node-status-${status}`}>
                          <div className="node-indicator">
                            <span className="node-index">{meta.indexStr}</span>
                            <span className="node-dot" />
                          </div>

                          <div className="node-content">
                            <div className="node-label-row">
                              <span className="node-label">{state}</span>
                              <span className={`node-status-badge badge-${status}`}>
                                {status === 'completed'
                                  ? 'COMPLETED'
                                  : status === 'active'
                                  ? 'EXECUTING'
                                  : status === 'failed'
                                  ? 'FAILED'
                                  : 'PENDING'}
                              </span>
                            </div>
                            <span className="node-desc">{meta.desc}</span>
                          </div>
                        </div>

                        {!isLast && (
                          <div className={`pipeline-ladder-connector ${connectorStatus}`}>
                            <div className="connector-line" />
                            <span className="connector-arrow">&darr;</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                /* Step-by-Step Transition Event Log */
                <div className="trace-events-list">
                  {trace.length === 0 ? (
                    <div className="empty-trace-state">
                      <span>No transition events recorded yet.</span>
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
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};
