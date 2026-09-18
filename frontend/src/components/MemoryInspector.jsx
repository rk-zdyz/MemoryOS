import React, { useState } from 'react';
import {
  Database,
  Search,
  Trash2,
  CheckCircle2,
  Plus,
  X,
  Sparkles,
  Layers,
  Clock,
  AlertCircle,
  Terminal,
  Shield,
  Cpu
} from 'lucide-react';
import { createManualMemory } from '../api';

export default function MemoryInspector({
  memories,
  activeUser,
  onForgetMemory,
  onRefresh,
  highlightedMemoryId
}) {
  const [filter, setFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  
  // Manual Memory Form State
  const [newContent, setNewContent] = useState('');
  const [newType, setNewType] = useState('PROFILE_FACT');
  const [newPredicate, setNewPredicate] = useState('');
  const [newObject, setNewObject] = useState('');
  const [newImportance, setNewImportance] = useState(0.8);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const filteredMemories = memories.filter(m => {
    if (filter === 'ACTIVE' && m.status !== 'ACTIVE') return false;
    if (filter === 'SUPERSEDED' && m.status !== 'SUPERSEDED') return false;
    if (filter === 'DECAYED' && m.status !== 'DECAYED') return false;
    if (filter === 'FORGOTTEN' && m.status !== 'FORGOTTEN') return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const contentMatch = m.content.toLowerCase().includes(q);
      const tagMatch = m.tags?.some(t => t.toLowerCase().includes(q));
      const tripleMatch = m.triple && (
        m.triple.predicate.toLowerCase().includes(q) ||
        m.triple.object.toLowerCase().includes(q)
      );
      return contentMatch || tagMatch || tripleMatch;
    }
    return true;
  });

  const handleCreateMemory = async (e) => {
    e.preventDefault();
    if (!newContent.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await createManualMemory(
        activeUser,
        newContent.trim(),
        newType,
        newPredicate.trim() || null,
        newObject.trim() || null,
        parseFloat(newImportance)
      );
      setNewContent('');
      setNewPredicate('');
      setNewObject('');
      setIsAddModalOpen(false);
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error('Failed to create manual memory:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'ACTIVE':
        return <span className="badge-cyber badge-cyber-green">ACTIVE</span>;
      case 'SUPERSEDED':
        return <span className="badge-cyber badge-cyber-amber">SUPERSEDED</span>;
      case 'DECAYED':
        return <span className="badge-cyber badge-cyber-cyan">DECAYED</span>;
      case 'FORGOTTEN':
        return <span className="badge-cyber badge-cyber-magenta">FORGOTTEN</span>;
      default:
        return <span className="badge-cyber badge-cyber-magenta">{status}</span>;
    }
  };

  return (
    <div
      className="cyber-card cyber-chamfer-sm"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'relative'
      }}
    >
      {/* Window Title Bar */}
      <div className="terminal-chrome">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Database size={13} color="var(--neon-green)" />
          <span className="tech-label" style={{ fontSize: '0.74rem', fontWeight: 800, color: 'var(--neon-green)', letterSpacing: '0.1em' }}>
            MEMORY BANK // {activeUser.toUpperCase()}
          </span>
        </div>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="btn-cyber btn-cyber-primary"
          style={{ padding: '2px 8px', fontSize: '0.68rem' }}
        >
          <Plus size={11} />
          <span>INJECT</span>
        </button>
      </div>

      {/* Search & Status Filter */}
      <div style={{ padding: '10px 12px', background: 'rgba(18, 18, 26, 0.95)', borderBottom: '1px solid var(--cyber-border)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--cyber-black)', padding: '6px 10px', border: '1px solid var(--cyber-border)' }}>
          <Search size={12} color="var(--neon-green)" />
          <input
            type="text"
            placeholder="SEARCH MEMORY RECORDS..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--neon-green)',
              fontSize: '0.72rem',
              fontFamily: 'var(--font-mono)',
              outline: 'none',
              width: '100%',
              letterSpacing: '0.06em'
            }}
          />
        </div>

        {/* Status Filter Buttons */}
        <div style={{ display: 'flex', gap: '4px', overflowX: 'auto' }}>
          {['ALL', 'ACTIVE', 'SUPERSEDED', 'DECAYED'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={filter === f ? 'btn-cyber btn-cyber-primary' : 'btn-cyber btn-cyber-ghost'}
              style={{ fontSize: '0.66rem', padding: '3px 8px', flex: 1 }}
            >
              <span>{f}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Memory Cards Scroll Area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          fontFamily: 'var(--font-mono)'
        }}
      >
        {filteredMemories.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '30px', fontSize: '0.76rem' }}>
            &gt; NO MEMORIES MATCHING FILTER.
          </div>
        ) : (
          filteredMemories.map((mem) => {
            const isHighlighted = highlightedMemoryId === mem.id;
            const isActive = mem.status === 'ACTIVE';

            return (
              <div
                key={mem.id}
                className="cyber-chamfer-sm"
                style={{
                  padding: '10px 12px',
                  background: isHighlighted ? 'rgba(0, 255, 136, 0.12)' : 'rgba(18, 18, 26, 0.95)',
                  border: isHighlighted ? '1px solid var(--neon-green)' : '1px solid var(--cyber-border)',
                  borderLeft: isActive ? '3px solid var(--neon-green)' : '3px solid var(--alert-amber)',
                  boxShadow: isHighlighted ? '0 0 15px var(--neon-green-glow)' : 'none',
                  transition: 'all 0.2s ease',
                  fontSize: '0.76rem'
                }}
              >
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {getStatusBadge(mem.status)}
                    <span style={{ fontSize: '0.66rem', color: 'var(--electric-cyan)' }}>
                      #{mem.id.slice(0, 6)}
                    </span>
                  </div>
                  <button
                    onClick={() => onForgetMemory(mem.id)}
                    title="GDPR Targeted Selective Forgetting"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '2px'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.color = 'var(--destructive-red)'}
                    onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>

                {/* Content */}
                <div style={{ color: 'var(--text-primary)', fontWeight: 600, marginBottom: '6px', lineHeight: 1.4 }}>
                  {mem.content}
                </div>

                {/* Structured Triple */}
                {mem.triple && (
                  <div style={{ color: 'var(--electric-cyan)', fontSize: '0.68rem', marginBottom: '6px' }}>
                    &gt; ({mem.triple.subject} ➔ {mem.triple.predicate} ➔ {mem.triple.object})
                  </div>
                )}

                {/* Importance Bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                  <span className="tech-label">IMPORTANCE:</span>
                  <div style={{ flex: 1, height: '4px', background: 'var(--cyber-black)', border: '1px solid var(--cyber-border)' }}>
                    <div
                      style={{
                        width: `${Math.round((mem.importance || 0.5) * 100)}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, var(--neon-green), var(--electric-cyan))'
                      }}
                    />
                  </div>
                  <span>{Math.round((mem.importance || 0.5) * 100)}%</span>
                </div>

                {/* Validity interval */}
                <div style={{ marginTop: '4px', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                  FROM: {mem.valid_from ? mem.valid_from.slice(0, 10) : 'PRESENT'} {mem.valid_to ? `➔ TO: ${mem.valid_to.slice(0, 10)}` : '➔ PRESENT'}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Manual Memory Injection Modal */}
      {isAddModalOpen && (
        <div
          className="cyber-chamfer-sm"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            background: 'rgba(10, 10, 15, 0.98)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 10,
            border: '1px solid var(--neon-green)',
            boxShadow: '0 0 30px var(--neon-green-glow)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid var(--cyber-border)', paddingBottom: '8px' }}>
            <span className="font-heading" style={{ color: 'var(--neon-green)', fontWeight: 800, letterSpacing: '0.08em', fontSize: '0.8rem' }}>
              &gt; MANUAL BELIEF INJECTION
            </span>
            <button onClick={() => setIsAddModalOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <X size={14} />
            </button>
          </div>

          <form onSubmit={handleCreateMemory} style={{ display: 'flex', flexDirection: 'column', gap: '12px', flex: 1, overflowY: 'auto' }}>
            <div>
              <label className="tech-label" style={{ display: 'block', fontSize: '0.7rem', color: 'var(--neon-green)', marginBottom: '4px' }}>
                &gt; NATURAL CONTENT STATEMENT:
              </label>
              <textarea
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                placeholder="e.g., User lives in: Tokyo, Japan"
                className="cyber-input"
                style={{ width: '100%', height: '60px', resize: 'none' }}
                required
              />
            </div>

            <div>
              <label className="tech-label" style={{ display: 'block', fontSize: '0.7rem', color: 'var(--neon-green)', marginBottom: '4px' }}>
                &gt; MEMORY TYPE:
              </label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                className="cyber-select"
                style={{ width: '100%' }}
              >
                <option value="PROFILE_FACT">PROFILE_FACT</option>
                <option value="DECISION">DECISION</option>
                <option value="PREFERENCE">PREFERENCE</option>
                <option value="EVENT_EPISODE">EVENT_EPISODE</option>
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>
                <label className="tech-label" style={{ display: 'block', fontSize: '0.7rem', color: 'var(--neon-green)', marginBottom: '4px' }}>
                  PREDICATE:
                </label>
                <input
                  type="text"
                  placeholder="lives_in"
                  value={newPredicate}
                  onChange={(e) => setNewPredicate(e.target.value)}
                  className="cyber-input"
                  style={{ width: '100%', fontSize: '0.75rem' }}
                />
              </div>
              <div>
                <label className="tech-label" style={{ display: 'block', fontSize: '0.7rem', color: 'var(--neon-green)', marginBottom: '4px' }}>
                  OBJECT:
                </label>
                <input
                  type="text"
                  placeholder="Tokyo, Japan"
                  value={newObject}
                  onChange={(e) => setNewObject(e.target.value)}
                  className="cyber-input"
                  style={{ width: '100%', fontSize: '0.75rem' }}
                />
              </div>
            </div>

            <div style={{ marginTop: 'auto', display: 'flex', gap: '10px' }}>
              <button
                type="submit"
                className="btn-cyber btn-cyber-primary"
                style={{ flex: 1 }}
                disabled={isSubmitting || !newContent.trim()}
              >
                <span>COMMIT TO MEMORY</span>
              </button>
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="btn-cyber btn-cyber-ghost"
              >
                <span>CANCEL</span>
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
