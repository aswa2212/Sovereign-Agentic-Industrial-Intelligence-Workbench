import React from 'react';
import { AgentState, StateTransition } from '../types/agent';
import { CheckCircle2, Clock, AlertCircle, ArrowRight, Activity } from 'lucide-react';

interface AgentGraphTraceProps {
  currentState: AgentState;
  isRunning: boolean;
  trace: StateTransition[];
  taskId?: string | null;
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
}) => {
  // Determine state progress
  const visitedStates = new Set<AgentState>(trace.map((t) => t.to_state));
  if (currentState !== 'IDLE' && currentState !== 'FAILED') {
    visitedStates.add(currentState);
  }

  // Find index of current state in pipeline
  const currentIndex = ORDERED_STATES.indexOf(currentState);
  const isFailed = currentState === 'FAILED';

  const getStateStatus = (state: AgentState) => {
    if (isFailed && state === currentState) return 'failed';
    if (state === currentState && isRunning) return 'active';
    if (visitedStates.has(state)) return 'completed';
    const stateIdx = ORDERED_STATES.indexOf(state);
    if (currentIndex > -1 && stateIdx < currentIndex) return 'completed';
    return 'pending';
  };

  return (
    <div className="card" style={{ marginBottom: '1.25rem' }}>
      <div className="card-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Activity size={16} className={isRunning ? 'icon-spin' : ''} style={{ color: 'var(--accent-primary)' }} />
          <div>
            <div className="card-title">Agent State Machine Lifecycle Trace</div>
            <div className="card-subtitle">
              Deterministic 11-State Execution Graph • MRPL Refined Orchestrator
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {taskId && (
            <span className="code-badge" title="Task Identifier">
              ID: {taskId.slice(0, 8)}
            </span>
          )}
          {isFailed ? (
            <span className="badge badge-danger">
              <AlertCircle size={12} style={{ marginRight: '4px' }} />
              FAILED
            </span>
          ) : isRunning ? (
            <span className="badge badge-info">
              <Clock size={12} style={{ marginRight: '4px' }} className="icon-spin" />
              RUNNING ({currentState})
            </span>
          ) : currentState === 'DELIVER' || visitedStates.has('DELIVER') ? (
            <span className="badge badge-success">
              <CheckCircle2 size={12} style={{ marginRight: '4px' }} />
              COMPLETED
            </span>
          ) : (
            <span className="badge badge-neutral">IDLE</span>
          )}
        </div>
      </div>

      {/* Sequential Pipeline Visualization */}
      <div style={{ padding: '1rem', background: 'var(--bg-surface-muted)', borderBottom: '1px solid var(--border-subtle)', overflowX: 'auto' }}>
        <div className="state-pipeline">
          {ORDERED_STATES.map((state, idx) => {
            const status = getStateStatus(state);
            return (
              <React.Fragment key={state}>
                <div
                  className={`state-step state-step-${status}`}
                  title={`State: ${state} (${status})`}
                >
                  <div className="state-step-dot">
                    {status === 'completed' && <CheckCircle2 size={14} />}
                    {status === 'active' && <Clock size={14} className="icon-spin" />}
                    {status === 'failed' && <AlertCircle size={14} />}
                    {status === 'pending' && <span>{idx + 1}</span>}
                  </div>
                  <div className="state-step-label">{state}</div>
                </div>

                {idx < ORDERED_STATES.length - 1 && (
                  <div className={`state-connector ${status === 'completed' ? 'active' : ''}`}>
                    <ArrowRight size={12} />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Detailed Chronological Transition Log */}
      <div style={{ padding: '1rem', maxHeight: '240px', overflowY: 'auto' }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
          Sequential Transition Ledger ({trace.length} recorded events)
        </div>

        {trace.length === 0 ? (
          <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
            No task active. Define an objective and initiate workflow to observe state machine execution.
          </div>
        ) : (
          <div className="trace-list">
            {trace.map((tr, index) => {
              const timeStr = tr.timestamp ? new Date(tr.timestamp).toLocaleTimeString() : '--:--:--';
              return (
                <div key={index} className="trace-row">
                  <div className="trace-meta">
                    <span className="trace-time">{timeStr}</span>
                    <span className="trace-step-badge">STEP {index + 1}</span>
                  </div>

                  <div className="trace-content">
                    <div className="trace-transition">
                      <span className="trace-state">{tr.from_state}</span>
                      <ArrowRight size={11} style={{ margin: '0 4px', color: 'var(--text-muted)' }} />
                      <span className="trace-state trace-state-target">{tr.to_state}</span>
                    </div>
                    {tr.message && <div className="trace-message">{tr.message}</div>}
                    {tr.metadata && Object.keys(tr.metadata).length > 0 && (
                      <div className="trace-tags">
                        {Object.entries(tr.metadata).map(([k, v]) => (
                          <span key={k} className="trace-tag">
                            {k}: {String(v)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
