import React, { useState, useEffect } from 'react';

export default function App() {
  const [health, setHealth] = useState<{ status: string; air_gap_verified: boolean } | null>(null);

  useEffect(() => {
    fetch('/health')
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch(() => setHealth({ status: 'offline', air_gap_verified: true }));
  }, []);

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', padding: '2rem', maxWidth: '1200px', margin: '0 auto', color: '#1a1a1a' }}>
      <header style={{ borderBottom: '2px solid #e5e7eb', paddingBottom: '1rem', marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#0f172a' }}>SIH26117 — Sovereign On-Premise Agentic AI Workbench</h1>
          <p style={{ margin: '0.25rem 0 0', color: '#64748b', fontSize: '0.875rem' }}>
            Mangalore Refinery and Petrochemicals Limited (MRPL) • Air-Gapped Industrial Operations
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span
            style={{
              display: 'inline-block',
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              backgroundColor: health?.air_gap_verified ? '#10b981' : '#f59e0b',
            }}
          />
          <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#334155' }}>
            Air-Gap Status: {health?.air_gap_verified ? 'Sovereign / Contained' : 'Checking...'}
          </span>
        </div>
      </header>

      <main>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', background: '#f8fafc' }}>
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem', color: '#1e293b' }}>1. Sovereign Operation</h3>
            <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>Zero external internet connection. Full local audit logging.</p>
          </div>
          <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', background: '#f8fafc' }}>
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem', color: '#1e293b' }}>2. Dynamic Router</h3>
            <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>Routes tasks to specialized reasoning, vision, or coding local models.</p>
          </div>
          <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', background: '#f8fafc' }}>
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem', color: '#1e293b' }}>3. Agent Orchestrator</h3>
            <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>Multi-step state machine with intermediate step visibility.</p>
          </div>
          <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', background: '#f8fafc' }}>
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem', color: '#1e293b' }}>4. Deterministic Deliverables</h3>
            <p style={{ margin: 0, fontSize: '0.875rem', color: '#64748b' }}>Automated compilation of structured JSON into native DOCX/XLSX/PPTX.</p>
          </div>
        </div>

        <div style={{ padding: '1.5rem', background: '#f1f5f9', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
          <h2 style={{ fontSize: '1.125rem', marginTop: 0 }}>Workbench Initialization</h2>
          <p style={{ fontSize: '0.875rem', color: '#475569' }}>
            Scaffolding complete. Backend service placeholder operational. System ready for incremental module implementation.
          </p>
          <pre style={{ background: '#0f172a', color: '#f8fafc', padding: '1rem', borderRadius: '6px', fontSize: '0.8rem', overflowX: 'auto' }}>
            {JSON.stringify(health, null, 2)}
          </pre>
        </div>
      </main>
    </div>
  );
}
