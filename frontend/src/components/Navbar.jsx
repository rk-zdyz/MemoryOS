import React from 'react';
import { Brain, User, RefreshCw, Sliders, Shield, Clock, Sparkles } from 'lucide-react';

export default function Navbar({
  activeUser,
  onSelectUser,
  usersList,
  onReset,
  onOpenSettings,
  activeTab,
  onSelectTab,
  simulatedDay,
  onSimulatedDayChange
}) {
  return (
    <header className="glass-panel" style={{ margin: '12px 16px 0 16px', padding: '12px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', zIndex: 50 }}>
      {/* Brand & Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '38px', height: '38px', borderRadius: '10px',
          background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 16px rgba(6, 182, 212, 0.4)'
        }}>
          <Brain size={22} color="#ffffff" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.25rem', fontWeight: '800', letterSpacing: '-0.02em', background: 'linear-gradient(to right, #f8fafc, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Memory<span style={{ color: '#06b6d4' }}>OS</span>
            </span>
            <span style={{ fontSize: '0.65rem', padding: '2px 6px', borderRadius: '4px', background: 'rgba(99, 102, 241, 0.2)', color: '#818cf8', border: '1px solid rgba(99, 102, 241, 0.3)', fontWeight: 600 }}>
              v1.0 TEMPORAL
            </span>
          </div>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            The AI That Never Forgets... Or Does It? • Contradiction-Aware Memory
          </p>
        </div>
      </div>

      {/* Center Navigation Tabs */}
      <nav style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(10, 13, 20, 0.6)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
        {[
          { id: 'chat', label: 'Chat & Memory Trace', icon: Sparkles },
          { id: 'graph', label: 'Knowledge Graph', icon: Brain },
          { id: 'timeline', label: 'Temporal Lineage', icon: Clock },
          { id: 'benchmarks', label: 'Judge Benchmarks', icon: Shield }
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '6px 14px', borderRadius: '8px', border: 'none',
                fontSize: '0.82rem', fontWeight: isActive ? 600 : 500,
                cursor: 'pointer', transition: 'all 0.2s ease',
                background: isActive ? 'linear-gradient(135deg, rgba(99,102,241,0.25), rgba(6,182,212,0.25))' : 'transparent',
                color: isActive ? '#f8fafc' : 'var(--text-secondary)',
                borderBottom: isActive ? '2px solid #06b6d4' : '2px solid transparent'
              }}
            >
              <Icon size={15} color={isActive ? '#06b6d4' : 'currentColor'} />
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* Right Controls: User Switcher, Date Sim, Reset & Settings */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* User Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-input)', padding: '4px 10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
          <User size={15} color="#06b6d4" />
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Tenant:</span>
          <select
            value={activeUser}
            onChange={(e) => onSelectUser(e.target.value)}
            style={{
              background: 'transparent', border: 'none', color: '#f8fafc',
              fontSize: '0.82rem', fontWeight: 600, outline: 'none', cursor: 'pointer', padding: 0
            }}
          >
            <option value="riku" style={{ background: '#101522' }}>Riku (Software Lead)</option>
            <option value="vansh" style={{ background: '#101522' }}>Vansh (Health & Fitness)</option>
            <option value="sid" style={{ background: '#101522' }}>Sid (Student UCL)</option>
          </select>
        </div>

        {/* Re-seed Button */}
        <button
          onClick={onReset}
          title="Reset database to default benchmark state"
          className="btn-secondary"
          style={{ padding: '6px 10px', fontSize: '0.78rem' }}
        >
          <RefreshCw size={14} />
          Reset Demo
        </button>

        {/* Settings Button */}
        <button
          onClick={onOpenSettings}
          title="Engine Settings & API Keys"
          className="btn-secondary"
          style={{ padding: '6px 10px' }}
        >
          <Sliders size={15} />
        </button>
      </div>
    </header>
  );
}
