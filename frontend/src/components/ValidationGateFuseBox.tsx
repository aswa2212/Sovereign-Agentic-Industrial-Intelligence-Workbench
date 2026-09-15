import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, Check, AlertCircle, Info, Lock } from 'lucide-react';
import { StructuredValidationReport, ValidationCheckItem } from '../types/agent';
import { MOCK_VALIDATION_REPORT } from '../services/mockData';

interface ValidationGateFuseBoxProps {
  report?: StructuredValidationReport | null;
  isRunning?: boolean;
}

import { DataSourceBadge } from './DataSourceBadge';

interface ValidationGateFuseBoxProps {
  report?: StructuredValidationReport | null;
  isRunning?: boolean;
}

const STANDBY_RULES: ValidationCheckItem[] = MOCK_VALIDATION_REPORT.checks.map((c) => ({
  ...c,
  status: 'FAILED' as const, // will be treated as standby when !hasReport
  detail: 'Awaiting pipeline execution to evaluate invariant against telemetry.',
}));

export const ValidationGateFuseBox: React.FC<ValidationGateFuseBoxProps> = ({
  report,
  isRunning = false,
}) => {
  const [selectedCheck, setSelectedCheck] = useState<ValidationCheckItem | null>(null);

  const hasReport = !!(report && report.checks && report.checks.length > 0);
  const checks = hasReport ? report.checks : STANDBY_RULES;
  const passedCount = hasReport ? report.checks_passed_count : 0;
  const failedCount = hasReport ? report.checks_failed_count : 0;
  const isAllPassed = hasReport && passedCount === 12 && failedCount === 0;

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
                  <span>12/12 PASSED</span>
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

      {/* The 12-Cell Fuse Box Status Grid */}
      <div className="fuse-grid" role="group" aria-label="12-Check Engineering Validation Gate">
        {checks.map((chk, index) => {
          const isPassed = !isRunning && hasReport && chk.status === 'PASSED';
          const isFailed = !isRunning && hasReport && chk.status === 'FAILED';
          const isStandby = !isRunning && !hasReport;
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
                  ) : isStandby ? (
                    <span className="fuse-standby-dash">•</span>
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

      {/* Interactive Detail Drawer for Inspected Check */}
      {selectedCheck && (
        <div className="fuse-detail-card" role="region" aria-label="Rule Inspection Details">
          <div className="fuse-detail-header">
            <div className="detail-rule-tag">
              <Info size={13} />
              <span>RULE #{selectedCheck.rule_number}: {selectedCheck.name}</span>
            </div>
            <span
              className={`badge-pill ${
                !hasReport
                  ? 'badge-neutral'
                  : selectedCheck.status === 'PASSED'
                  ? 'badge-success'
                  : 'badge-error'
              }`}
            >
              {!hasReport ? 'STANDBY' : selectedCheck.status}
            </span>
          </div>
          <div className="fuse-detail-desc">{selectedCheck.description}</div>
          <div className="fuse-detail-evidence">
            <span className="evidence-label">VERIFIED NUMERICAL EVIDENCE:</span>
            <code className="evidence-code">
              {!hasReport ? 'Awaiting pipeline execution to evaluate invariant.' : selectedCheck.detail}
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
