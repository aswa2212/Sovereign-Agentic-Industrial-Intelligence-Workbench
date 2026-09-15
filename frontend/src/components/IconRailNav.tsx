import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Cpu,
  FileText,
  Database,
  Layers,
  ShieldCheck,
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  Terminal,
  LucideIcon,
} from 'lucide-react';

interface IconRailNavProps {
  onOpenCommandPalette: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

interface NavItemDef {
  to: string;
  label: string;
  badge?: string;
  icon: LucideIcon;
}

export const IconRailNav: React.FC<IconRailNavProps> = ({
  onOpenCommandPalette,
  isCollapsed,
  onToggleCollapse,
}) => {
  const navItems: NavItemDef[] = [
    { to: '/overview', label: 'Overview', badge: 'NEW', icon: LayoutDashboard },
    { to: '/workbench', label: 'Workbench', icon: Cpu },
    { to: '/documents', label: 'Documents', icon: FileText },
    { to: '/knowledge', label: 'Knowledge (RAG)', icon: Database },
    { to: '/models', label: 'Models', icon: Layers },
    { to: '/audit', label: 'Audit Ledger', icon: ShieldCheck },
    { to: '/sovereignty', label: 'Sovereignty', icon: ShieldAlert },
  ];

  return (
    <aside
      className={`icon-rail-sidebar ${isCollapsed ? 'is-collapsed' : 'is-expanded'}`}
      aria-label="Application Navigation"
    >
      {/* Rail Nav Items */}
      <nav className="rail-nav-list" role="navigation">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rail-nav-item ${isActive ? 'is-active' : ''}`
              }
              title={isCollapsed ? item.label : undefined}
            >
              <div className="rail-item-icon-wrap">
                <Icon size={19} className="rail-icon" />
              </div>
              <span className="rail-item-label">{item.label}</span>
              {item.badge && !isCollapsed && (
                <span className="rail-item-badge">{item.badge}</span>
              )}
              {isCollapsed && (
                <div className="rail-flyout-tooltip" role="tooltip">
                  {item.label}
                  {item.badge && <span className="tooltip-badge">{item.badge}</span>}
                </div>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Rail Bottom Actions */}
      <div className="rail-bottom-actions">
        {/* Command Palette Launcher */}
        <button
          type="button"
          className="rail-cmd-launcher"
          onClick={onOpenCommandPalette}
          title={isCollapsed ? 'Command Palette (Cmd/Ctrl + K)' : undefined}
          aria-label="Open Command Palette"
        >
          <div className="rail-item-icon-wrap">
            <Terminal size={17} className="rail-icon" />
          </div>
          <span className="rail-item-label">Command Palette</span>
          <kbd className="rail-cmd-kbd">⌘K</kbd>
          {isCollapsed && (
            <div className="rail-flyout-tooltip" role="tooltip">
              Command Palette (⌘K)
            </div>
          )}
        </button>

        {/* Pin / Collapse Toggle */}
        <button
          type="button"
          className="rail-toggle-btn"
          onClick={onToggleCollapse}
          title={isCollapsed ? 'Expand Navigation Sidebar' : 'Collapse Sidebar to 64px Rail'}
          aria-label={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          {!isCollapsed && <span className="rail-toggle-label">Collapse Deck</span>}
        </button>
      </div>
    </aside>
  );
};
