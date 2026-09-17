import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, CheckCircle, AlertTriangle, Trash2, Clock, Eye, ShieldCheck, ChevronDown, ChevronUp, Calendar } from 'lucide-react';

export default function ChatView({
  messages,
  onSendMessage,
  isLoading,
  activeUser,
  simulatedDate,
  onSimulatedDateChange,
  onSelectMemory
}) {
  const [input, setInput] = useState('');
  const [expandedTrace, setExpandedTrace] = useState({});
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const toggleTrace = (msgIndex) => {
    setExpandedTrace(prev => ({
      ...prev,
      [msgIndex]: !prev[msgIndex]
    }));
  };

  const quickPrompts = [
    { label: "📍 Where do I live?", text: "Where do I live?" },
    { label: "☕ My favorite drink?", text: "What is my favorite beverage?" },
    { label: "🗄️ Database decision?", text: "What database did we choose for our project?" },
    { label: "⚡ State update: Moved to Tokyo", text: "I moved to Tokyo last weekend and currently reside there." },
    { label: "🍵 Preference pivot: Switched to Matcha", text: "I quit coffee completely; now I only drink matcha green tea." },
    { label: "🗑️ GDPR Purge: Forget phone", text: "Forget my phone number." }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
      {/* Date Simulation Bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 16px', background: 'rgba(16, 21, 34, 0.7)',
        borderBottom: '1px solid var(--border-subtle)', fontSize: '0.78rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)' }}>
          <Calendar size={14} color="#06b6d4" />
          <span>Simulated Timestamp:</span>
          <select
            value={simulatedDate || ''}
            onChange={(e) => onSimulatedDateChange(e.target.value || null)}
            style={{
              background: 'var(--bg-input)', color: '#f8fafc',
              border: '1px solid var(--border-subtle)', borderRadius: '4px',
              padding: '2px 8px', fontSize: '0.75rem'
            }}
          >
            <option value="">Live Real-Time (Current)</option>
            <option value="2026-09-01T10:00:00Z">Day 1 (2026-09-01) - Initial Setup</option>
            <option value="2026-09-02T10:00:00Z">Day 2 (2026-09-02) - Intermediate Changes</option>
            <option value="2026-09-03T10:00:00Z">Day 3 (2026-09-03) - Major Relocation & Reversals</option>
            <option value="2026-09-05T10:00:00Z">Day 5 (2026-09-05) - Future Consolidation</option>
          </select>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#34d399', fontSize: '0.72rem' }}>
          <ShieldCheck size={14} />
          <span>Tenant Isolated: <strong>{activeUser.toUpperCase()}</strong></span>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {messages.length === 0 && (
          <div style={{
            margin: 'auto', textAlign: 'center', maxWidth: '460px',
            padding: '30px', borderRadius: '16px', background: 'rgba(22, 29, 46, 0.4)',
            border: '1px dashed var(--border-subtle)'
          }}>
            <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(99, 102, 241, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px' }}>
              <Sparkles size={26} color="#06b6d4" />
            </div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '8px' }}>
              Continuous Cognitive Memory Active
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.6 }}>
              ChronosMemory tracks your identity, evolving decisions, and habits across sessions. Ask what it knows, update a fact, or explore how it resolves contradictions!
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', justifyContent: 'center' }}>
              {quickPrompts.slice(0, 3).map((qp, i) => (
                <button
                  key={i}
                  onClick={() => onSendMessage(qp.text)}
                  className="btn-secondary"
                  style={{ fontSize: '0.75rem', padding: '5px 10px' }}
                >
                  {qp.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          const isExpanded = expandedTrace[idx];
          const hasAttribution = msg.used_memories?.length > 0 || msg.superseded_memories?.length > 0 || msg.conflict_notes?.length > 0;

          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignSelf: isUser ? 'flex-end' : 'flex-start',
                maxWidth: isUser ? '75%' : '85%',
                gap: '4px'
              }}
            >
              {/* Message Bubble */}
              <div
                style={{
                  padding: '12px 16px',
                  borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  background: isUser
                    ? 'linear-gradient(135deg, #4f46e5 0%, #3730a3 100%)'
                    : 'rgba(22, 29, 46, 0.85)',
                  border: isUser ? 'none' : '1px solid var(--border-subtle)',
                  color: '#f8fafc',
                  fontSize: '0.9rem',
                  lineHeight: 1.55,
                  boxShadow: isUser ? '0 4px 14px rgba(79, 70, 229, 0.3)' : '0 4px 20px rgba(0, 0, 0, 0.2)'
                }}
              >
                {/* Text */}
                <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>

                {/* Timestamp & Sim Badge */}
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  marginTop: '8px', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.08)',
                  fontSize: '0.68rem', color: isUser ? 'rgba(255,255,255,0.7)' : 'var(--text-muted)'
                }}>
                  <span>{isUser ? activeUser.toUpperCase() : 'MEMORY OS'}</span>
                  <span>{msg.simulated_date ? `Sim: ${msg.simulated_date.slice(0, 10)}` : new Date(msg.created_at || Date.now()).toLocaleTimeString()}</span>
                </div>
              </div>

              {/* Attribution & Conflict Resolution Accordion (for Assistant responses) */}
              {!isUser && hasAttribution && (
                <div
                  className="glass-panel-subtle"
                  style={{
                    marginTop: '4px',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '0.75rem',
                    border: '1px solid rgba(99, 102, 241, 0.25)',
                    background: 'rgba(14, 19, 32, 0.8)'
                  }}
                >
                  <div
                    onClick={() => toggleTrace(idx)}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      cursor: 'pointer', userSelect: 'none'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Eye size={13} color="#06b6d4" />
                      <span style={{ fontWeight: 600, color: '#38bdf8' }}>
                        Memory Attribution & Reasoning Trace
                      </span>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                        ({msg.used_memories?.length || 0} active used, {msg.superseded_memories?.length || 0} superseded filtered)
                      </span>
                    </div>
                    {isExpanded ? <ChevronUp size={14} color="#94a3b8" /> : <ChevronDown size={14} color="#94a3b8" />}
                  </div>

                  {isExpanded && (
                    <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {/* Conflict Resolution Notes */}
                      {msg.conflict_notes?.length > 0 && (
                        <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '6px 10px', borderRadius: '6px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#fbbf24', fontWeight: 600, marginBottom: '2px' }}>
                            <AlertTriangle size={13} />
                            <span>Contradiction Mutation Handled</span>
                          </div>
                          {msg.conflict_notes.map((note, nIdx) => (
                            <div key={nIdx} style={{ color: '#fef3c7', fontSize: '0.72rem' }}>• {note}</div>
                          ))}
                        </div>
                      )}

                      {/* Active Memories Consulted */}
                      {msg.used_memories?.length > 0 && (
                        <div>
                          <span style={{ color: '#34d399', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
                            <CheckCircle size={12} /> Active Memories Consulted:
                          </span>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {msg.used_memories.map((m, mIdx) => (
                              <div
                                key={mIdx}
                                onClick={() => onSelectMemory && onSelectMemory(m.memory_id)}
                                style={{
                                  padding: '5px 8px', borderRadius: '4px',
                                  background: 'rgba(16, 185, 129, 0.1)',
                                  border: '1px solid rgba(16, 185, 129, 0.25)',
                                  cursor: 'pointer'
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#e2e8f0' }}>
                                  <span>{m.content}</span>
                                  <span style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>Sim: {m.similarity_score}</span>
                                </div>
                                <div style={{ display: 'flex', gap: '8px', marginTop: '2px', color: 'var(--text-muted)', fontSize: '0.66rem' }}>
                                  <span>ID: #{m.memory_id?.slice(0, 6)}</span>
                                  <span>Type: {m.memory_type}</span>
                                  <span>{m.valid_interval}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Superseded / Filtered Memories */}
                      {msg.superseded_memories?.length > 0 && (
                        <div>
                          <span style={{ color: '#fbbf24', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
                            <Clock size={12} /> Filtered Outdated/Superseded Memories:
                          </span>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {msg.superseded_memories.map((m, mIdx) => (
                              <div
                                key={mIdx}
                                style={{
                                  padding: '5px 8px', borderRadius: '4px',
                                  background: 'rgba(245, 158, 11, 0.08)',
                                  border: '1px solid rgba(245, 158, 11, 0.25)',
                                  color: '#cbd5e1'
                                }}
                              >
                                <div style={{ textDecoration: 'line-through', opacity: 0.8 }}>{m.content}</div>
                                <div style={{ color: '#fbbf24', fontSize: '0.68rem', marginTop: '2px' }}>
                                  Reason: {m.filter_reason}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {isLoading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '0.8rem', padding: '8px' }}>
            <div className="animate-pulse-glow" style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#06b6d4' }}></div>
            <span>Evaluating cognitive state, resolving contradictions & querying memory index...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Fast Prompts */}
      <div style={{ padding: '6px 16px', background: 'var(--bg-secondary)', borderTop: '1px solid var(--border-subtle)', display: 'flex', gap: '6px', overflowX: 'auto' }}>
        {quickPrompts.map((qp, i) => (
          <button
            key={i}
            onClick={() => onSendMessage(qp.text)}
            className="btn-secondary"
            style={{ fontSize: '0.72rem', padding: '4px 8px', whiteSpace: 'nowrap', borderRadius: '12px' }}
          >
            {qp.label}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <form onSubmit={handleSubmit} style={{ padding: '12px 16px', background: 'var(--bg-secondary)', display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Speak with MemoryOS as ${activeUser.toUpperCase()} (declare a fact, change a preference, or ask a question)...`}
          style={{ flex: 1, fontSize: '0.88rem' }}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="btn-primary"
          disabled={isLoading || !input.trim()}
          style={{ opacity: isLoading || !input.trim() ? 0.6 : 1 }}
        >
          <Send size={16} />
          Send
        </button>
      </form>
    </div>
  );
}
