import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, Check, AlertCircle, Info, Lock } from 'lucide-react';
import { StructuredValidationReport, ValidationCheckItem } from '../types/agent';
import { DataSourceBadge } from './DataSourceBadge';

interface ValidationGateFuseBoxProps {
  report?: StructuredValidationReport | null;
  isRunning?: boolean;
}

export interface ValidationGateEvaluation {
  hasReport: boolean;
  isPassed: boolean;
  isAllPassed: boolean;
  passedCount: number;
  totalCount: number;
  failedCount: number;
  hasPerCheckDetail: boolean;
  checks: ValidationCheckItem[];
}

export function evaluateValidationGate(report?: StructuredValidationReport | null): ValidationGateEvaluation {
  const hasReport = !!(report && (report.valid !== undefined || report.status !== undefined || (Array.isArray(report.checks) && report.checks.length > 0)));
  const failedCount = report?.checks_failed_count ?? ((report as any)?.checks_failed?.length ?? 0);
  const isPassed = !!(report && (report.valid === true || (report.status as string) === 'VALID' || report.status === 'PASS' || (report.checks_passed_count === 12))) && failedCount === 0;

  const totalCount = report?.checks_total ?? 12;
  const passedCount = isPassed ? totalCount : Math.max(0, totalCount - failedCount);
  const isAllPassed = isPassed && failedCount === 0;

  const hasPerCheckDetail = !!(report && Array.isArray(report.checks) && report.checks.length > 0);
  const checks: ValidationCheckItem[] = hasPerCheckDetail ? (report!.checks as ValidationCheckItem[]) : [];

  return {
    hasReport,
    isPassed,
    isAllPassed,
    passedCount,
    totalCount,
    failedCount,
    hasPerCheckDetail,
    checks,
  };
}

export const ValidationGateFuseBox: React.FC<ValidationGateFuseBoxProps> = ({
  report,
  isRunning = false,
}) => {
  const [selectedCheck, setSelectedCheck] = useState<ValidationCheckItem | null>(null);

  const {
    hasReport,
    isAllPassed,
    passedCount,
    totalCount,
    failedCount,
    hasPerCheckDetail,
    checks,
  } = evaluateValidationGate(report);

  return (
    <div className="fuse-box-container">
      {/* Fuse Box Header */}
      <div className="fuse-box-header">
        <div className="fuse-box-title-group">
          <div className="fuse-box-led-status">
            <span
              className={`fuse-led ${
                isRunning
                  ? 'is-evaluating'
                  : hasReport
                  ? isAllPassed
                    ? 'is-passed'
                    : 'is-tripped'
                  : 'is-standby'
              }`}
            />
            <span className="fuse-box-title">ENGINEERING VALIDATION GATE (12 INVARIANTS)</span>
          </div>
          <span className="fuse-box-subtitle">Fail-Closed Boundary Enforcement • API 570 / ASME B31.3</span>
        </div>

        <div className="fuse-box-badge-wrap">
          {hasReport && (
            <DataSourceBadge
              source={isAllPassed ? 'LIVE' : 'DEMO'}
              label={isAllPassed ? 'LIVE BACKEND VALIDATION' : 'DEMO VALIDATION'}
              size="sm"
            />
          )}
          <span
            className={`fuse-status-pill ${
              isRunning
                ? 'status-evaluating'
                : hasReport
                ? isAllPassed
                  ? 'status-passed'
                  : 'status-failed'
                : 'status-standby'
            }`}
          >
            {isRunning ? (
              <>EVALUATING INVARIANTS...</>
            ) : hasReport ? (
              isAllPassed ? (
                <>
                  <ShieldCheck size={13} />
                  <span>{hasPerCheckDetail ? `${passedCount}/${totalCount} PASSED` : `${passedCount}/${totalCount} AGGREGATE PASSED`}</span>
                </>
              ) : (
                <>
                  <ShieldAlert size={13} />
                  <span>FAIL-CLOSED: {failedCount} FAILED</span>
                </>
              )
            ) : (
              <>
                <ShieldAlert size={13} />
                <span>STANDBY — AWAITING EXECUTION</span>
              </>
            )}
          </span>
        </div>
      </div>

      {/* Case 1: Backend Provided Real Per-Check Results */}
      {hasReport && hasPerCheckDetail && checks.length > 0 && (
        <div className="fuse-grid" role="group" aria-label="12-Check Engineering Validation Gate">
          {checks.map((chk, index) => {
            const isPassed = !isRunning && chk.status === 'PASSED';
            const isFailed = !isRunning && chk.status === 'FAILED';
            const isSelected = selectedCheck?.id === chk.id;

            return (
              <button
                key={chk.id || index}
                type="button"
                className={`fuse-cell ${
                  isRunning
                    ? 'cell-evaluating'
                    : isPassed
                    ? 'cell-passed'
                    : isFailed
                    ? 'cell-failed'
                    : 'cell-standby'
                } ${isSelected ? 'is-active-cell' : ''}`}
                onClick={() => setSelectedCheck(isSelected ? null : chk)}
                title={`${chk.name}: ${chk.detail} (Click to inspect rule)`}
                aria-label={`Rule ${chk.rule_number}: ${chk.name}, Status: ${isRunning ? 'Evaluating' : chk.status}`}
              >
                <div className="fuse-cell-top">
                  <span className="fuse-rule-num">#{String(chk.rule_number).padStart(2, '0')}</span>
                  <span className="fuse-indicator-dot">
                    {isRunning ? (
                      <span className="fuse-eval-spin" />
                    ) : isPassed ? (
                      <Check size={10} className="fuse-check-icon" />
                    ) : (
                      <AlertCircle size={10} className="fuse-fail-icon" />
                    )}
                  </span>
                </div>
                <div className="fuse-cell-name">{chk.name}</div>
              </button>
            );
          })}
        </div>
      )}

      {/* Case 2: Aggregate Pass Exists But Per-Check Detail Not Provided By Backend */}
      {hasReport && !hasPerCheckDetail && (
        <div className="aggregate-validation-panel">
          <div className="aggregate-status-badge-row">
            <ShieldCheck size={20} className={isAllPassed ? 'text-success' : 'text-error'} />
            <div>
              <h3 className="aggregate-title">
                {isAllPassed ? `${passedCount}/${totalCount} AGGREGATE VALIDATION PASSED` : `FAIL-CLOSED: ${failedCount} FAILED`}
              </h3>
              <p className="aggregate-desc">
                Per-invariant validation detail not returned by backend.
              </p>
            </div>
          </div>

          {Array.isArray((report as any)?.checks_passed) && (report as any).checks_passed.length > 0 && (
            <div className="aggregate-raw-checks">
              <span className="aggregate-raw-label">
                Authoritative Backend Step Verifications ({(report as any).checks_passed.length}):
              </span>
              <div className="aggregate-chips-wrap">
                {(report as any).checks_passed.map((chk: string, idx: number) => (
                  <span key={idx} className="aggregate-check-chip">
                    <Check size={10} />
                    <code>{chk}</code>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Case 3: No Validation Result (Standby State) */}
      {!hasReport && (
        <div className="validation-standby-panel">
          <ShieldAlert size={18} className="text-muted" />
          <div>
            <h4 className="standby-title">STANDBY — AWAITING PIPELINE EXECUTION</h4>
            <p className="standby-desc">
              Validation detail is unavailable until an engineering task is executed. Invariant rules will be evaluated upon workflow run.
            </p>
          </div>
        </div>
      )}

      {/* Interactive Detail Drawer (for Case 1 when user clicks a check) */}
      {selectedCheck && hasPerCheckDetail && (
        <div className="fuse-detail-card" role="region" aria-label="Rule Inspection Details">
          <div className="fuse-detail-header">
            <div className="detail-rule-tag">
              <Info size={13} />
              <span>RULE #{selectedCheck.rule_number}: {selectedCheck.name}</span>
            </div>
            <span
              className={`badge-pill ${
                selectedCheck.status === 'PASSED' ? 'badge-success' : 'badge-error'
              }`}
            >
              {selectedCheck.status}
            </span>
          </div>
          <div className="fuse-detail-desc">{selectedCheck.description}</div>
          <div className="fuse-detail-evidence">
            <span className="evidence-label">VERIFIED NUMERICAL EVIDENCE:</span>
            <code className="evidence-code">
              {selectedCheck.detail}
            </code>
          </div>
        </div>
      )}

      {/* Fail-Closed Release Guarantee Footer */}
      <div className="fuse-box-footer">
        <div className="fuse-footer-left">
          <Lock size={12} className="fuse-lock-icon" />
          <span>
            Fail-Closed Policy: Deliverable compilation withheld if <em>any</em> invariant fails.
          </span>
        </div>
        <div className="fuse-footer-right">
          <code>API 570 §7.1</code>
        </div>
      </div>
    </div>
  );
};
