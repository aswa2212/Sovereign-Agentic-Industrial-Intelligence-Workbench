import React, { useState } from 'react';
import './styles/workbench.css';
import { SovereigntyBar } from './components/SovereigntyBar';
import { Navigation, NavigationTab } from './components/Navigation';
import { WorkbenchPage } from './pages/WorkbenchPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { AuditPage } from './pages/AuditPage';
import { SovereigntyPage } from './pages/SovereigntyPage';
import { ModelsPage } from './pages/ModelsPage';

export default function App() {
  const [activeTab, setActiveTab] = useState<NavigationTab>('workbench');

  const renderActivePage = () => {
    switch (activeTab) {
      case 'workbench':
        return <WorkbenchPage />;
      case 'documents':
        return <DocumentsPage />;
      case 'knowledge':
        return <KnowledgePage />;
      case 'audit':
        return <AuditPage />;
      case 'sovereignty':
        return <SovereigntyPage />;
      case 'models':
        return <ModelsPage />;
      default:
        return <WorkbenchPage />;
    }
  };

  return (
    <div className="workbench-layout">
      {/* Persistent Sovereignty Header */}
      <SovereigntyBar onNavigateToSovereignty={() => setActiveTab('sovereignty')} />

      {/* Main Workspace with Restrained Sidebar and Canvas */}
      <div className="workbench-body">
        <Navigation activeTab={activeTab} onSelectTab={setActiveTab} />
        <main className="workbench-main" role="main">
          {renderActivePage()}
        </main>
      </div>
    </div>
  );
}
