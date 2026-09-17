import React, { useState } from 'react';
import { Sliders, X, Key, Shield, Sparkles, Check, Database } from 'lucide-react';

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
        position: 'fixed', inset: 0, zIndex: 100,
        background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(8px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px'
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%', maxWidth: '500px', padding: '24px',
          borderRadius: '16px', border: '1px solid var(--border-active)'
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={18} color="#06b6d4" />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Engine & Provider Settings</h3>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Provider Selection */}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc', marginBottom: '6px' }}>
              Inference & Synthesis Provider
            </label>
            <select
              value={provider}
              onChange={(e) => onProviderChange(e.target.value)}
              style={{ width: '100%', fontSize: '0.85rem' }}
            >
              <option value="local">Built-in Cognitive Engine (100% Offline & Deterministic)</option>
              <option value="gemini">Google Gemini API (gemini-1.5-flash)</option>
              <option value="openai">OpenAI API (gpt-4o-mini)</option>
            </select>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              The built-in engine performs state tracking, contradiction detection, and attribution locally without requiring any external keys.
            </p>
          </div>

          {/* API Key (if external) */}
          {provider !== 'local' && (
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc', marginBottom: '6px' }}>
                {provider.toUpperCase()} API Key
              </label>
              <div style={{ position: 'relative' }}>
                <Key size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '12px' }} />
                <input
                  type="password"
                  placeholder={`Enter your ${provider} API key...`}
                  value={apiKey}
                  onChange={(e) => onApiKeyChange(e.target.value)}
                  style={{ width: '100%', paddingLeft: '32px', fontSize: '0.85rem' }}
                />
              </div>
            </div>
          )}

          {/* Persistence & Database Reset */}
          <div style={{ paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc', marginBottom: '6px' }}>
              Database & Benchmark State
            </label>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
              Resetting will clear custom changes and restore default multi-user scenarios for Riku, Vansh, and Sid.
            </p>
            <button
              onClick={() => {
                onResetDatabase();
                onClose();
              }}
              className="btn-danger"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem' }}
            >
              <Database size={13} />
              Re-seed Database
            </button>
          </div>
        </div>

        {/* Footer */}
        <div style={{ marginTop: '22px', display: 'flex', justifyContent: 'flex-end' }}>
          <button onClick={onClose} className="btn-primary" style={{ fontSize: '0.82rem' }}>
            <Check size={14} />
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
