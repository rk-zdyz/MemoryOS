import React, { useState } from 'react';
import { Database, Search, ShieldAlert, Trash2, CheckCircle2, History, AlertCircle, Cpu, Clock, Layers } from 'lucide-react';

export default function MemoryInspector({
  memories,
  activeUser,
  onForgetMemory,
  onRefresh,
  highlightedMemoryId
}) {
  const [filter, setFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredMemories = memories.filter(m => {
    if (filter === 'ACTIVE' && m.status !== 'ACTIVE') return false;
    if (filter === 'SUPERSEDED' && m.status !== 'SUPERSEDED') return false;
    if (filter === 'DECAYED' && m.status !== 'DECAYED') return false;
    if (filter === 'FORGOTTEN' && m.status !== 'FORGOTTEN') return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const contentMatch = m.content.toLowerCase().includes(q);
      const tagMatch = m.tags?.some(t => t.toLowerCase().includes(q));
      const tripleMatch = m.triple && (m.triple.predicate.toLowerCase().includes(q) || m.triple.object.toLowerCase().includes(q));
      return contentMatch || tagMatch || tripleMatch;
    }
    return true;
  });

  const getStatusBadge = (status) => {
    switch (status) {
      case 'ACTIVE':
        return <span className="badge-active" style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 600 }}>ACTIVE</span>;
      case 'SUPERSEDED':
        return <span className="badge-superseded" style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 600 }}>SUPERSEDED</span>;
      case 'DECAYED':
        return <span className="badge-decayed" style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 600 }}>DECAYED</span>;
      case 'FORGOTTEN':
        return <span className="badge-forgotten" style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 600 }}>FORGOTTEN</span>;
      default:
        return <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem' }}>{status}</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-card)', borderLeft: '1px solid var(--border-subtle)' }}>
      {/* Header */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={17} color="#06b6d4" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Cognitive Memory Bank</h3>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {memories.length} total entries
          </span>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', marginBottom: '10px' }}>
          <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '10px' }} />
          <input
            type="text"
            placeholder="Search memory contents, triples, tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: '100%', paddingLeft: '32px', fontSize: '0.78rem', height: '34px' }}
          />
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', paddingBottom: '2px' }}>
          {['ALL', 'ACTIVE', 'SUPERSEDED', 'DECAYED', 'FORGOTTEN'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                background: filter === f ? 'rgba(99, 102, 241, 0.25)' : 'rgba(255, 255, 255, 0.04)',
                color: filter === f ? '#818cf8' : 'var(--text-secondary)',
                border: filter === f ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid var(--border-subtle)',
                padding: '3px 8px', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer'
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Memory List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filteredMemories.length === 0 && (
          <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
            No memories matching filter '{filter}'
          </div>
        )}

        {filteredMemories.map(mem => {
          const isHighlighted = highlightedMemoryId === mem.id;
          return (
            <div
              key={mem.id}
              className="glass-panel-subtle"
              style={{
                padding: '10px 12px',
                borderRadius: '8px',
                border: isHighlighted ? '2px solid #06b6d4' : (mem.status === 'ACTIVE' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-subtle)'),
                background: isHighlighted ? 'rgba(6, 182, 212, 0.1)' : (mem.status === 'ACTIVE' ? 'rgba(16, 185, 129, 0.04)' : 'rgba(15, 20, 32, 0.6)'),
                transition: 'all 0.2s ease'
              }}
            >
              {/* Header row */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {getStatusBadge(mem.status)}
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    #{mem.id.slice(0, 6)}
                  </span>
                </div>
                
                {mem.status !== 'FORGOTTEN' && (
                  <button
                    onClick={() => onForgetMemory(mem.id)}
                    title="Purge / Forget this memory (GDPR deletion)"
                    style={{
                      background: 'transparent', border: 'none', color: 'var(--text-muted)',
                      cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.color = '#f43f5e'}
                    onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>

              {/* Memory content */}
              <div style={{ fontSize: '0.82rem', color: '#f8fafc', fontWeight: 500, marginBottom: '6px', lineHeight: 1.4 }}>
                {mem.content}
              </div>

              {/* Triple representation */}
              {mem.triple && (
                <div style={{
                  background: 'rgba(0, 0, 0, 0.3)', padding: '4px 8px', borderRadius: '4px',
                  fontSize: '0.7rem', color: '#38bdf8', fontFamily: 'var(--font-mono)',
                  marginBottom: '6px', border: '1px solid rgba(56, 189, 248, 0.15)'
                }}>
                  {mem.triple.subject} ➔ {mem.triple.predicate} ➔ <strong>{mem.triple.object}</strong>
                </div>
              )}

              {/* Supersede / Invalidation reason */}
              {mem.supersede_reason && (
                <div style={{
                  background: 'rgba(245, 158, 11, 0.1)', padding: '4px 8px', borderRadius: '4px',
                  fontSize: '0.7rem', color: '#fbbf24', marginBottom: '6px', border: '1px solid rgba(245, 158, 11, 0.2)'
                }}>
                  ⚠️ {mem.supersede_reason}
                </div>
              )}

              {/* Footer metadata */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.66rem', color: 'var(--text-muted)' }}>
                <span>Type: <strong>{mem.memory_type}</strong></span>
                <span>Interval: {mem.valid_from ? mem.valid_from.slice(0, 10) : 'Start'} ➔ {mem.valid_to ? mem.valid_to.slice(0, 10) : 'Now'}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
