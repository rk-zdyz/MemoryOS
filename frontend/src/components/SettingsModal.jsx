import React from 'react';
import { Sliders, X, Cpu, Key, RefreshCw, Sparkles, Terminal } from 'lucide-react';

export default function SettingsModal({
  isOpen,
  onClose,
  provider,
  onProviderChange,
  apiKey,
  onApiKeyChange,
  onResetDatabase
}) {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        background: 'rgba(5, 5, 10, 0.85)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100
      }}
    >
      <div
        className="cyber-card cyber-chamfer"
        style={{
          width: '560px',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 0 50px var(--neon-green-glow)',
          border: '1px solid var(--neon-green)',
          fontFamily: 'var(--font-mono)'
        }}
      >
        {/* Terminal Chrome Bar */}
        <div className="terminal-chrome">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="traffic-dots">
              <div className="traffic-dot traffic-dot-red" />
              <div className="traffic-dot traffic-dot-amber" />
              <div className="traffic-dot traffic-dot-green" />
            </div>
            <span className="tech-label" style={{ fontSize: '0.74rem', fontWeight: 800, color: 'var(--neon-green)', letterSpacing: '0.1em' }}>
              SYSTEM CONFIGURATION // INFERENCE & STORAGE
            </span>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <X size={14} />
          </button>
        </div>

        {/* Form Body */}
        <div style={{ padding: '22px', display: 'flex', flexDirection: 'column', gap: '18px', overflowY: 'auto' }}>
          {/* Inference Provider */}
          <div>
            <label className="tech-label" style={{ display: 'block', fontSize: '0.74rem', color: 'var(--neon-green)', marginBottom: '8px', fontWeight: 700 }}>
              &gt; COGNITIVE INFERENCE ENGINE PROVIDER:
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
              {[
                { id: 'local', label: 'LOCAL COGNITIVE', desc: '100% Offline / Zero-Dep' },
                { id: 'gemini', label: 'GOOGLE GEMINI', desc: 'Gemini 1.5 Flash' },
                { id: 'openai', label: 'OPENAI GPT-4O', desc: 'GPT-4o Mini' }
              ].map(p => (
                <div
                  key={p.id}
                  onClick={() => onProviderChange(p.id)}
                  className="cyber-chamfer-sm"
                  style={{
                    padding: '10px 12px',
                    background: provider === p.id ? 'rgba(0, 255, 136, 0.12)' : 'var(--cyber-black)',
                    border: provider === p.id ? '1px solid var(--neon-green)' : '1px solid var(--cyber-border)',
                    boxShadow: provider === p.id ? '0 0 15px var(--neon-green-glow)' : 'none',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <div style={{ color: provider === p.id ? 'var(--neon-green)' : 'var(--text-primary)', fontWeight: 700, fontSize: '0.76rem' }}>
                    {p.label}
                  </div>
                  <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {p.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* API Key Input */}
          {provider !== 'local' && (
            <div>
              <label className="tech-label" style={{ display: 'block', fontSize: '0.74rem', color: 'var(--hot-magenta)', marginBottom: '6px', fontWeight: 700 }}>
                &gt; {provider.toUpperCase()} API ACCESS KEY:
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => onApiKeyChange(e.target.value)}
                placeholder={`Enter your ${provider === 'gemini' ? 'Gemini' : 'OpenAI'} API key...`}
                className="cyber-input"
                style={{ width: '100%' }}
              />
            </div>
          )}

          {/* Database Reset */}
          <div style={{ marginTop: '10px', paddingTop: '16px', borderTop: '1px solid var(--cyber-border)' }}>
            <label className="tech-label" style={{ display: 'block', fontSize: '0.74rem', color: 'var(--alert-amber)', marginBottom: '6px', fontWeight: 700 }}>
              &gt; MEMORY STORE RE-INITIALIZATION:
            </label>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              Purges temporary changes and re-seeds default benchmark scenarios for Riku, Vansh, and Sid.
            </p>
            <button
              onClick={() => {
                onResetDatabase();
                onClose();
              }}
              className="btn-cyber btn-cyber-outline"
              style={{ borderColor: 'var(--alert-amber)', color: 'var(--alert-amber)' }}
            >
              <RefreshCw size={12} />
              <span>RESTORE DEFAULT SEED DATA</span>
            </button>
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: '14px 22px', background: 'var(--cyber-black)', borderTop: '1px solid var(--cyber-border)', display: 'flex', justifyContent: 'flex-end' }}>
          <button onClick={onClose} className="btn-cyber btn-cyber-primary">
            <span>SAVE & CLOSE</span>
          </button>
        </div>
      </div>
    </div>
  );
}
