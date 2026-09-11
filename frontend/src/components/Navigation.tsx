import React from 'react';
import {
  LayoutDashboard,
  FileText,
  BookOpen,
  History,
  ShieldCheck,
  Cpu,
} from 'lucide-react';

export type NavigationTab =
  | 'workbench'
  | 'documents'
  | 'knowledge'
  | 'audit'
  | 'sovereignty'
  | 'models';

interface NavigationProps {
  activeTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
}

export const Navigation: React.FC<NavigationProps> = ({ activeTab, onSelectTab }) => {
  return (
    <nav className="nav-sidebar" aria-label="Main Navigation">
      <div className="nav-section">
        <div className="nav-section-title">WORKSPACE</div>
        <button
          className={`nav-item ${activeTab === 'workbench' ? 'active' : ''}`}
          onClick={() => onSelectTab('workbench')}
          aria-current={activeTab === 'workbench' ? 'page' : undefined}
        >
          <LayoutDashboard size={15} />
          <span>Workbench</span>
        </button>
        <button
          className={`nav-item ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => onSelectTab('documents')}
          aria-current={activeTab === 'documents' ? 'page' : undefined}
        >
          <FileText size={15} />
          <span>Documents</span>
        </button>
      </div>

      <div className="nav-section">
        <div className="nav-section-title">EVIDENCE & ASSURANCE</div>
        <button
          className={`nav-item ${activeTab === 'knowledge' ? 'active' : ''}`}
          onClick={() => onSelectTab('knowledge')}
          aria-current={activeTab === 'knowledge' ? 'page' : undefined}
        >
          <BookOpen size={15} />
          <span>Knowledge Base</span>
        </button>
        <button
          className={`nav-item ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => onSelectTab('audit')}
          aria-current={activeTab === 'audit' ? 'page' : undefined}
        >
          <History size={15} />
          <span>Audit Ledger</span>
        </button>
      </div>

      <div className="nav-section">
        <div className="nav-section-title">SYSTEM & SECURITY</div>
        <button
          className={`nav-item ${activeTab === 'sovereignty' ? 'active' : ''}`}
          onClick={() => onSelectTab('sovereignty')}
          aria-current={activeTab === 'sovereignty' ? 'page' : undefined}
        >
          <ShieldCheck size={15} />
          <span>Sovereignty</span>
        </button>
        <button
          className={`nav-item ${activeTab === 'models' ? 'active' : ''}`}
          onClick={() => onSelectTab('models')}
          aria-current={activeTab === 'models' ? 'page' : undefined}
        >
          <Cpu size={15} />
          <span>Model Registry</span>
        </button>
      </div>

      <div className="nav-footer">
        <div className="nav-footer-meta">
          <div>NODE: MRPL-ONPREM-01</div>
          <div>ISOLATION: ENFORCED</div>
          <div>VERSION: 1.0.0 (PHASE 12)</div>
        </div>
      </div>
    </nav>
  );
};
