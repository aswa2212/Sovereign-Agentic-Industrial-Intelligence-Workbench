import React from 'react';

export type DataSourceType = 'LIVE' | 'DEMO' | 'MOCK' | 'FALLBACK' | 'UNAVAILABLE';

interface DataSourceBadgeProps {
  source: DataSourceType;
  label?: string;
  className?: string;
  size?: 'sm' | 'md';
}

const BADGE_CONFIG: Record<DataSourceType, { defaultLabel: string; dotClass: string; badgeClass: string }> = {
  LIVE: {
    defaultLabel: 'LIVE — BACKEND',
    dotClass: 'dot-live',
    badgeClass: 'badge-source-live',
  },
  DEMO: {
    defaultLabel: 'DEMO — SYNTHETIC CORPUS',
    dotClass: 'dot-demo',
    badgeClass: 'badge-source-demo',
  },
  MOCK: {
    defaultLabel: 'MOCK — DEVELOPMENT',
    dotClass: 'dot-mock',
    badgeClass: 'badge-source-mock',
  },
  FALLBACK: {
    defaultLabel: 'FALLBACK — NO LIVE DATA',
    dotClass: 'dot-fallback',
    badgeClass: 'badge-source-fallback',
  },
  UNAVAILABLE: {
    defaultLabel: 'UNAVAILABLE',
    dotClass: 'dot-unavailable',
    badgeClass: 'badge-source-unavailable',
  },
};

export const DataSourceBadge: React.FC<DataSourceBadgeProps> = ({
  source,
  label,
  className = '',
  size = 'sm',
}) => {
  const config = BADGE_CONFIG[source] || BADGE_CONFIG.UNAVAILABLE;
  const displayLabel = label || config.defaultLabel;

  return (
    <span
      className={`data-source-badge ${config.badgeClass} size-${size} ${className}`}
      title={`Data Source: ${displayLabel}`}
      aria-label={`Data provenance: ${displayLabel}`}
    >
      <span className={`source-dot ${config.dotClass}`} aria-hidden="true" />
      <span className="source-label">{displayLabel}</span>
    </span>
  );
};
