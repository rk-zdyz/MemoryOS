import React from 'react';
import { Brain, User, RefreshCw, Sliders, Shield, Clock, Sparkles, FileText, Terminal, Activity, Zap } from 'lucide-react';

export default function Navbar({
  activeUser,
  onSelectUser,
  usersList,
  onReset,
  onOpenSettings,
  onOpenAuditLogs,
  activeTab,
  onSelectTab,
  simulatedDate,
  onSimulatedDateChange
}) {
  return (
    <header
      className="cyber-card cyber-chamfer-sm"
      style={{
        margin: '12px 16px 0 16px',
        padding: '0',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 50,
        position: 'relative'
      }}
    >
      {/* Top HUD Terminal Chrome Bar */}
      <div className="terminal-chrome">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="traffic-dots">
            <div className="traffic-dot traffic-dot-red" />
            <div className="traffic-dot traffic-dot-amber" />
            <div className="traffic-dot traffic-dot-green" />
          </div>
          <span className="tech-label" style={{ fontSize: '0.68rem', color: 'var(--neon-green)', letterSpacing: '0.12em' }}>
            MEMORY_OS // KERNEL.SYS [v3.0.4-CYBERPUNK]
          </span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.65rem', color: 'var(--neon-green)', fontFamily: 'var(--font-mono)' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--neon-green)', boxShadow: '0 0 8px var(--neon-green)' }} />
            NEURAL_BUS: ACTIVE
          </span>
          <span style={{ fontSize: '0.65rem', color: 'var(--electric-cyan)', fontFamily: 'var(--font-mono)' }}>
            LATENCY: 1.4ms
          </span>
        </div>
      </div>

      {/* Main Navbar HUD Controls */}
      <div
        style={{
          padding: '10px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(10, 10, 15, 0.95)',
          gap: '16px',
          borderBottom: '1px solid var(--cyber-border)'
        }}
      >
        {/* Brand & Identity */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            className="cyber-chamfer-sm glitch-hover"
            style={{
              width: '38px',
              height: '38px',
              background: 'rgba(0, 255, 136, 0.08)',
              border: '1px solid var(--neon-green)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px var(--neon-green-glow)'
            }}
          >
            <Brain size={20} color="var(--neon-green)" />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1
                className="font-heading glitch-text"
                data-text="MEMORY_OS"
                style={{
                  fontSize: '1.35rem',
                  fontWeight: 900,
                  letterSpacing: '0.1em',
                  color: 'var(--text-primary)',
                  margin: 0
                }}
              >
                MEMORY<span style={{ color: 'var(--neon-green)', textShadow: '0 0 10px var(--neon-green)' }}>_OS</span>
              </h1>
              <span className="badge-cyber badge-cyber-green" style={{ fontSize: '0.62rem' }}>
                CONTRADICTION-AWARE
              </span>
            </div>
            <p className="tech-label" style={{ fontSize: '0.7rem', color: 'var(--text-muted)', margin: 0, marginTop: '2px' }}>
              &gt; THE PERSISTENT COGNITIVE BELIEF ENGINE // MATRIX_v3
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav
          className="cyber-chamfer-sm"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: 'var(--cyber-black)',
            padding: '4px',
            border: '1px solid var(--cyber-border)'
          }}
        >
          {[
            { id: 'chat', label: 'NEURAL CHAT', icon: Sparkles },
            { id: 'graph', label: 'BELIEF GRAPH', icon: Brain },
            { id: 'timeline', label: 'TIMELINE', icon: Clock },
            { id: 'benchmarks', label: 'JUDGE BENCHMARKS', icon: Shield }
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onSelectTab(tab.id)}
                className={`nav-tab-cyber ${isActive ? 'active' : ''}`}
              >
                <Icon size={13} color={isActive ? 'var(--neon-green)' : 'currentColor'} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Right Controls: Tenant Switcher, Audit Logs, Reset, Settings */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Tenant Switcher */}
          <div
            className="cyber-chamfer-sm"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'var(--cyber-black)',
              padding: '6px 12px',
              border: '1px solid var(--cyber-border)',
              boxShadow: 'inset 0 0 8px rgba(0,0,0,0.8)'
            }}
          >
            <Terminal size={13} color="var(--neon-green)" />
            <span className="tech-label" style={{ fontSize: '0.72rem', color: 'var(--neon-green)', fontWeight: 700 }}>
              &gt; USER:
            </span>
            <select
              value={activeUser}
              onChange={(e) => onSelectUser(e.target.value)}
              className="cyber-select"
              style={{
                border: 'none',
                boxShadow: 'none',
                padding: '0 4px',
                fontSize: '0.75rem',
                fontWeight: 700,
                color: 'var(--electric-cyan)',
                background: 'transparent'
              }}
            >
              <option value="riku">RIKU // SEC_LVL_4</option>
              <option value="vansh">VANSH // ATHLETE_NODE</option>
              <option value="sid">SID // RESEARCHER_NODE</option>
            </select>
          </div>

          {/* Audit Logs Button */}
          <button
            onClick={onOpenAuditLogs}
            title="Inspect Immutable GDPR Erasure & State Mutation Audit Trail"
            className="btn-cyber btn-cyber-outline"
            style={{ padding: '6px 12px', fontSize: '0.72rem' }}
          >
            <FileText size={12} />
            <span>AUDIT TRAIL</span>
          </button>

          {/* Re-seed Button */}
          <button
            onClick={onReset}
            title="Reset Database & Restore Benchmark Scenarios"
            className="btn-cyber btn-cyber-ghost"
            style={{ padding: '6px 12px', fontSize: '0.72rem' }}
          >
            <RefreshCw size={12} />
            <span>RESET</span>
          </button>

          {/* Settings Button */}
          <button
            onClick={onOpenSettings}
            title="Cognitive Engine & Model Settings"
            className="btn-cyber btn-cyber-ghost"
            style={{ padding: '6px 10px' }}
          >
            <Sliders size={13} />
          </button>
        </div>
      </div>
    </header>
  );
}
