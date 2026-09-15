import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface CopyableMonoProps {
  value: string;
  displayValue?: string;
  truncateLength?: number;
  className?: string;
  label?: string;
}

export const CopyableMono: React.FC<CopyableMonoProps> = ({
  value,
  displayValue,
  truncateLength,
  className = '',
  label,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Fallback
      const el = document.createElement('textarea');
      el.value = value;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    }
  };

  const formattedDisplay = () => {
    if (displayValue) return displayValue;
    if (truncateLength && value.length > truncateLength) {
      const half = Math.floor(truncateLength / 2);
      return `${value.substring(0, half)}...${value.substring(value.length - half)}`;
    }
    return value;
  };

  return (
    <span
      className={`copyable-mono-wrapper ${className}`}
      title={label ? `${label}: ${value}` : value}
    >
      <code className="copyable-mono-text">{formattedDisplay()}</code>
      <button
        type="button"
        className={`copyable-mono-btn ${copied ? 'is-copied' : ''}`}
        onClick={handleCopy}
        aria-label={`Copy ${label || 'value'} to clipboard`}
      >
        {copied ? <Check size={12} className="copy-icon-success" /> : <Copy size={12} />}
        {copied && <span className="copy-micro-tooltip">COPIED</span>}
      </button>
    </span>
  );
};
