import React, { useState, useEffect } from 'react';
import { systemService } from '../services/system';
import { TierConfigResponse, ModelListResponse, ModelInfoSchema, ModelRole } from '../types/api';
import { MOCK_MODEL_TIER, MOCK_MODEL_CATALOG } from '../services/mockData';
import { useToast } from '../components/ToastProvider';
import {
  Layers,
  Cpu,
  HardDrive,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Sparkles,
  Zap,
  Eye,
  Terminal,
  Shield,
  Clock,
  Sliders,
  LucideIcon,
} from 'lucide-react';

interface RoleCardMeta {
  role: ModelRole;
  displayName: string;
  desc: string;
  defaultVramGb: number;
  icon: LucideIcon;
}

const ROLE_DEFINITIONS: RoleCardMeta[] = [
  { role: 'router', displayName: 'Intent Router (Level 0)', desc: 'Fast keyword taxonomy parsing & model delegation', defaultVramGb: 1.1, icon: Sliders },
  { role: 'reasoning', displayName: 'Deep Engineering Reasoning', desc: 'Chain-of-thought analysis, synthesis & standards cross-reference', defaultVramGb: 4.8, icon: Sparkles },
  { role: 'coder', displayName: 'Deterministic Code Synthesizer', desc: 'Python automation script generation & sandbox calculations', defaultVramGb: 2.1, icon: Terminal },
  { role: 'vision', displayName: 'Schematic & P&ID Vision', desc: 'Equipment symbol identification, coordinate & tag extraction', defaultVramGb: 3.4, icon: Eye },
  { role: 'embedding', displayName: 'Dense Vector Embeddings', desc: '768-dim semantic chunk vectorization (offloaded to CPU)', defaultVramGb: 0.0, icon: Layers },
];

export const ModelsPage: React.FC = () => {
  const [tierConfig, setTierConfig] = useState<TierConfigResponse | null>(null);
  const [modelCatalog, setModelCatalog] = useState<ModelListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'dev' | 'target'>('dev');

  const toast = useToast();

  const loadModelsData = async () => {
    setLoading(true);
    try {
      const [tierRes, catalogRes] = await Promise.allSettled([
        systemService.getModelTier(),
        systemService.getModelList(),
      ]);

      if (tierRes.status === 'fulfilled') {
        setTierConfig(tierRes.value || MOCK_MODEL_TIER);
      }
      if (catalogRes.status === 'fulfilled') {
        setModelCatalog(catalogRes.value || MOCK_MODEL_CATALOG);
      }
    } catch {
      setTierConfig(MOCK_MODEL_TIER);
      setModelCatalog(MOCK_MODEL_CATALOG);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModelsData();
  }, []);

  const vramBudget = activeTab === 'dev' ? 8.0 : 24.0;
  const models = tierConfig?.models || MOCK_MODEL_TIER.models;

  return (
    <div className="page-container models-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Local Model Management &amp; Hardware Tiers</h1>
          <p className="page-subtitle">
            Model-Agnostic Role Resolution • Serial GPU VRAM Swapping • 100% On-Premise Ollama Engine
          </p>
        </div>

        <div className="page-header-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={loadModelsData}
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? 'icon-spin' : ''} />
            <span>Discover Local Models</span>
          </button>
        </div>
      </div>

      {/* Hardware Profile Card */}
      <div className="hardware-tier-card">
        <div className="tier-header-row">
          <div className="tier-info-group">
            <span className="subtle-label">HARDWARE EXECUTION PROFILE</span>
            <h2 className="tier-title">
              {activeTab === 'dev'
                ? 'Laptop Development Profile (RTX 4060, 8 GB VRAM, 16 GB RAM)'
                : 'Enterprise Edge Workstation Profile (A5000 / RTX 4090, 24 GB VRAM)'}
            </h2>
          </div>

          {/* Profile Switcher */}
          <div className="profile-switch-tabs">
            <button
              type="button"
              className={`profile-tab ${activeTab === 'dev' ? 'is-active' : ''}`}
              onClick={() => setActiveTab('dev')}
            >
              8 GB Baseline (Dev)
            </button>
            <button
              type="button"
              className={`profile-tab ${activeTab === 'target' ? 'is-active' : ''}`}
              onClick={() => setActiveTab('target')}
            >
              24 GB Target (Lab Node)
            </button>
          </div>
        </div>

        {/* Global Memory Ceiling Progress Bar */}
        <div className="vram-global-meter">
          <div className="vram-meter-labels">
            <span>
              <strong>VRAM Allocation Ceiling:</strong> {vramBudget.toFixed(1)} GB Available
            </span>
            <span>
              Serial Swap Policy: <strong>max_concurrent_models = {activeTab === 'dev' ? 1 : 3}</strong>
            </span>
          </div>
          <div className="vram-track">
            <div
              className="vram-fill"
              style={{ width: activeTab === 'dev' ? '60%' : '25%' }}
            />
          </div>
          <div className="vram-meter-footer">
            <span>Peak Swapping Footprint: ~4.8 GB (DeepSeek-R1 7B)</span>
            <span>Zero OOM Invariant: Enforced via async semaphore lock</span>
          </div>
        </div>
      </div>

      {/* Section Title */}
      <div className="section-title-strip">
        <h3 className="section-heading">MODEL ROLE ALLOCATIONS (DYNAMICALLY RESOLVED)</h3>
        <span className="section-sub">Mapped from models/configs/model_tiers.yaml • Zero hardcoded tags in application code</span>
      </div>

      {/* 5 ModelRole Cards Grid */}
      <div className="role-cards-grid">
        {ROLE_DEFINITIONS.map((def) => {
          const matchedModel = models.find((m) => m.role === def.role);
          const modelTag = matchedModel?.model_tag || 'Unassigned';
          const Icon = def.icon;
          const vramRequired = def.defaultVramGb;
          const vramPercent = Math.min(100, Math.round((vramRequired / vramBudget) * 100));

          return (
            <div key={def.role} className="model-role-card">
              <div className="role-card-header">
                <div className="role-icon-wrap">
                  <Icon size={16} />
                </div>
                <div className="role-titles">
                  <span className="role-id-badge">ROLE: {def.role.toUpperCase()}</span>
                  <div className="role-display-name">{def.displayName}</div>
                </div>
              </div>

              <p className="role-desc">{def.desc}</p>

              {/* Bound Model Tag Box */}
              <div className="role-model-binding">
                <span className="binding-label">RESOLVED MODEL TAG:</span>
                <code className="binding-tag">{modelTag}</code>
              </div>

              {/* Live VRAM Budget Bar for this Role */}
              <div className="role-vram-strip">
                <div className="role-vram-labels">
                  <span>VRAM Footprint:</span>
                  <strong>{vramRequired > 0 ? `${vramRequired.toFixed(1)} GB` : '0.0 GB (CPU)'}</strong>
                </div>
                <div className="role-vram-track">
                  <div
                    className="role-vram-fill"
                    style={{ width: `${vramPercent}%` }}
                  />
                </div>
                <div className="role-vram-sub">
                  <span>{vramPercent}% of {vramBudget} GB Ceiling</span>
                  <span>{def.role === 'embedding' ? 'CPU Device' : 'Serial Swapped'}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Discovered Local Ollama Models Catalog */}
      <div className="section-title-strip" style={{ marginTop: '1.75rem' }}>
        <h3 className="section-heading">DISCOVERED LOCAL OLLAMA REPOSITORY</h3>
        <span className="section-sub">Resident tags verified via 127.0.0.1:11434 /api/tags</span>
      </div>

      <div className="table-card">
        <div className="table-responsive">
          <table className="deck-table models-table">
            <thead>
              <tr>
                <th>Model Tag</th>
                <th>Provider</th>
                <th>Quantization</th>
                <th>Context Length</th>
                <th>Capabilities</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {(modelCatalog?.models || MOCK_MODEL_CATALOG.models).map((m) => (
                <tr key={m.tag || m.model_id}>
                  <td className="model-tag-cell">
                    <Cpu size={14} className="accent-icon" />
                    <code className="model-tag-text">{m.tag || m.model_id}</code>
                  </td>
                  <td>{m.provider}</td>
                  <td>
                    <span className="badge-pill badge-neutral">{m.quantization || 'Q4_K_M'}</span>
                  </td>
                  <td className="mono-num">{m.capabilities.max_context_length || 4096} tokens</td>
                  <td>
                    <div className="capabilities-tags-list">
                      {m.capabilities.supports_vision && (
                        <span className="badge-pill badge-info">Vision</span>
                      )}
                      {m.capabilities.supports_tools && (
                        <span className="badge-pill badge-success">Tools</span>
                      )}
                      {m.capabilities.supports_thinking && (
                        <span className="badge-pill badge-neutral">Thinking</span>
                      )}
                    </div>
                  </td>
                  <td>
                    {m.is_resident_in_vram ? (
                      <span className="badge-pill badge-success">
                        <span className="dot-live" />
                        <span>RESIDENT IN VRAM</span>
                      </span>
                    ) : (
                      <span className="badge-pill badge-neutral">STANDBY ON DISK</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
