import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  LayoutDashboard,
  Cpu,
  FileText,
  Database,
  Layers,
  ShieldCheck,
  ShieldAlert,
  Play,
  RotateCcw,
  Sparkles,
  X,
  CornerDownLeft,
  LucideIcon,
} from 'lucide-react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectPreset?: (preset: string) => void;
  onOpenAttestation?: () => void;
}

interface CommandItem {
  id: string;
  title: string;
  category: 'Navigation' | 'Presets' | 'Actions';
  icon: LucideIcon;
  hint?: string;
  perform: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectPreset,
  onOpenAttestation,
}) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const commands: CommandItem[] = [
    // 8 Navigation Pages
    {
      id: 'nav-overview',
      title: 'Overview — Mission Control Deck',
      category: 'Navigation',
      icon: LayoutDashboard,
      hint: 'Go to /overview',
      perform: () => { navigate('/overview'); onClose(); },
    },
    {
      id: 'nav-workbench',
      title: 'Workbench — 3-Column Execution Deck',
      category: 'Navigation',
      icon: Cpu,
      hint: 'Go to /workbench',
      perform: () => { navigate('/workbench'); onClose(); },
    },
    {
      id: 'nav-documents',
      title: 'Documents — SHA-256 Ingestion Archive',
      category: 'Navigation',
      icon: FileText,
      hint: 'Go to /documents',
      perform: () => { navigate('/documents'); onClose(); },
    },
    {
      id: 'nav-knowledge',
      title: 'Knowledge — Sovereign RAG Vector Store',
      category: 'Navigation',
      icon: Database,
      hint: 'Go to /knowledge',
      perform: () => { navigate('/knowledge'); onClose(); },
    },
    {
      id: 'nav-models',
      title: 'Models — Local Portfolio & VRAM Budget',
      category: 'Navigation',
      icon: Layers,
      hint: 'Go to /models',
      perform: () => { navigate('/models'); onClose(); },
    },
    {
      id: 'nav-audit',
      title: 'Audit Ledger — Cryptographic Hash Chain',
      category: 'Navigation',
      icon: ShieldCheck,
      hint: 'Go to /audit',
      perform: () => { navigate('/audit'); onClose(); },
    },
    {
      id: 'nav-sovereignty',
      title: 'Sovereignty — Runtime Air-Gap & Sockets',
      category: 'Navigation',
      icon: ShieldAlert,
      hint: 'Go to /sovereignty',
      perform: () => { navigate('/sovereignty'); onClose(); },
    },

    // Workbench Presets
    {
      id: 'preset-c101',
      title: 'Preset: C-101 Column Corrosion Audit (API 570)',
      category: 'Presets',
      icon: Play,
      hint: 'North-Star Scenario',
      perform: () => {
        navigate('/workbench');
        if (onSelectPreset) onSelectPreset('C-101 Overhead Column Corrosion Audit');
        onClose();
      },
    },
    {
      id: 'preset-thickness',
      title: 'Preset: API 570 Minimum Retirement Thickness',
      category: 'Presets',
      icon: Play,
      hint: 'Formula Verification',
      perform: () => {
        navigate('/workbench');
        if (onSelectPreset) onSelectPreset('Verify API 570 Retirement Thickness Formula on Carbon Steel');
        onClose();
      },
    },
    {
      id: 'preset-ndt',
      title: 'Preset: Ingest Ultrasonic Survey Data (CML-4)',
      category: 'Presets',
      icon: Play,
      hint: 'NDT Ingestion',
      perform: () => {
        navigate('/workbench');
        if (onSelectPreset) onSelectPreset('Ingest ultrasonic thickness survey and extract CML grid');
        onClose();
      },
    },

    // Quick Actions
    {
      id: 'action-verify-ledger',
      title: 'Action: Verify Cryptographic Ledger Integrity',
      category: 'Actions',
      icon: ShieldCheck,
      hint: 'Audit Validation',
      perform: () => {
        navigate('/audit');
        onClose();
      },
    },
    {
      id: 'action-audit-sockets',
      title: 'Action: Inspect Host OS Sockets (0 Foreign Egress)',
      category: 'Actions',
      icon: ShieldAlert,
      hint: 'Runtime Socket Proof',
      perform: () => {
        navigate('/sovereignty');
        onClose();
      },
    },
    {
      id: 'action-attest-isolation',
      title: 'Action: Verify Physical Isolation (Operator Attestation)',
      category: 'Actions',
      icon: ShieldCheck,
      hint: 'Record Air-Gap Verification',
      perform: () => {
        onClose();
        if (onOpenAttestation) {
          onOpenAttestation();
        } else {
          navigate('/sovereignty');
        }
      },
    },
  ];

  const filteredCommands = commands.filter((c) => {
    const q = query.toLowerCase();
    return (
      c.title.toLowerCase().includes(q) ||
      c.category.toLowerCase().includes(q) ||
      (c.hint && c.hint.toLowerCase().includes(q))
    );
  });

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) {
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
          e.preventDefault();
          onClose(); // toggle
        }
        return;
      }

      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % (filteredCommands.length || 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + (filteredCommands.length || 1)) % (filteredCommands.length || 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].perform();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, filteredCommands, selectedIndex]);

  if (!isOpen) return null;

  return (
    <div className="cmd-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label="Command Palette">
      <div className="cmd-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="cmd-header">
          <Search size={18} className="cmd-search-icon" />
          <input
            ref={inputRef}
            type="text"
            className="cmd-input"
            placeholder="Type a command, page name, or preset... (Esc to cancel)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="button" className="cmd-close-btn" onClick={onClose} aria-label="Close Command Palette">
            <X size={16} />
          </button>
        </div>

        <div className="cmd-results" role="listbox">
          {filteredCommands.length === 0 ? (
            <div className="cmd-empty">
              No matching commands or routes found for &ldquo;{query}&rdquo;
            </div>
          ) : (
            filteredCommands.map((cmd, idx) => {
              const Icon = cmd.icon;
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={cmd.id}
                  className={`cmd-item ${isSelected ? 'is-selected' : ''}`}
                  onClick={() => cmd.perform()}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  role="option"
                  aria-selected={isSelected}
                >
                  <div className="cmd-item-left">
                    <span className="cmd-item-icon">
                      <Icon size={16} />
                    </span>
                    <span className="cmd-item-title">{cmd.title}</span>
                  </div>
                  <div className="cmd-item-right">
                    {cmd.hint && <span className="cmd-item-hint">{cmd.hint}</span>}
                    <span className="cmd-item-category">{cmd.category}</span>
                    {isSelected && <CornerDownLeft size={13} className="cmd-enter-icon" />}
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="cmd-footer">
          <span><kbd className="cmd-kbd">↑</kbd> <kbd className="cmd-kbd">↓</kbd> to navigate</span>
          <span><kbd className="cmd-kbd">↵</kbd> to select</span>
          <span><kbd className="cmd-kbd">ESC</kbd> to close</span>
        </div>
      </div>
    </div>
  );
};
