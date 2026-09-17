import React, { useState, Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { SovereigntyBar } from './components/SovereigntyBar';
import { IconRailNav } from './components/IconRailNav';
import { CommandPalette } from './components/CommandPalette';
import { PhysicalAttestationModal } from './components/PhysicalAttestationModal';
import { ToastProvider } from './components/ToastProvider';
import { WorkbenchRuntimeProvider } from './context/WorkbenchRuntimeContext';

// Lazy-loaded routes for code-splitting
const OverviewPage = lazy(() => import('./pages/OverviewPage').then(m => ({ default: m.OverviewPage })));
const WorkbenchPage = lazy(() => import('./pages/WorkbenchPage').then(m => ({ default: m.WorkbenchPage })));
const DocumentsPage = lazy(() => import('./pages/DocumentsPage').then(m => ({ default: m.DocumentsPage })));
const KnowledgePage = lazy(() => import('./pages/KnowledgePage').then(m => ({ default: m.KnowledgePage })));
const ModelsPage = lazy(() => import('./pages/ModelsPage').then(m => ({ default: m.ModelsPage })));
const AuditPage = lazy(() => import('./pages/AuditPage').then(m => ({ default: m.AuditPage })));
const SovereigntyPage = lazy(() => import('./pages/SovereigntyPage').then(m => ({ default: m.SovereigntyPage })));

const PageSkeletonFallback: React.FC = () => (
  <div className="page-skeleton-wrapper" aria-label="Loading page structure...">
    <div className="skeleton-header">
      <div className="skeleton-line" style={{ width: '280px', height: '28px', marginBottom: '8px' }} />
      <div className="skeleton-line" style={{ width: '460px', height: '16px' }} />
    </div>
    <div className="skeleton-cards-grid">
      <div className="skeleton-box" style={{ height: '220px' }} />
      <div className="skeleton-box" style={{ height: '220px' }} />
      <div className="skeleton-box" style={{ height: '220px' }} />
    </div>
  </div>
);

const AppContent: React.FC = () => {
  const [isRailCollapsed, setIsRailCollapsed] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isAttestationModalOpen, setIsAttestationModalOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <div className="workbench-layout">
      {/* 1. Permanent Sovereignty Status Strip at Top */}
      <SovereigntyBar
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        onNavigateToSovereignty={() => navigate('/sovereignty')}
        onOpenSettings={() => navigate('/models')}
        onOpenAttestation={() => setIsAttestationModalOpen(true)}
      />

      {/* 2. Workspace Body: Collapsible Icon Rail + Routed Content Canvas */}
      <div className="workbench-body">
        <IconRailNav
          isCollapsed={isRailCollapsed}
          onToggleCollapse={() => setIsRailCollapsed((prev) => !prev)}
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        />

        <main className="workbench-main" role="main">
          <Suspense fallback={<PageSkeletonFallback />}>
            <Routes>
              <Route path="/" element={<Navigate to="/overview" replace />} />
              <Route path="/overview" element={<OverviewPage />} />
              <Route path="/workbench" element={<WorkbenchPage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/knowledge" element={<KnowledgePage />} />
              <Route path="/models" element={<ModelsPage />} />
              <Route path="/audit" element={<AuditPage />} />
              <Route path="/sovereignty" element={<SovereigntyPage />} />
              <Route path="*" element={<Navigate to="/overview" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>

      {/* 3. Global Command Palette Modal (Cmd/Ctrl + K) */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onOpenAttestation={() => setIsAttestationModalOpen(true)}
      />

      {/* 4. Operator Physical Air-Gap Attestation Modal */}
      <PhysicalAttestationModal
        isOpen={isAttestationModalOpen}
        onClose={() => setIsAttestationModalOpen(false)}
      />
    </div>
  );
};

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <WorkbenchRuntimeProvider>
          <AppContent />
        </WorkbenchRuntimeProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
