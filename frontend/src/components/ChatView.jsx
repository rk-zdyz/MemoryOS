import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  CheckCircle,
  AlertTriangle,
  Clock,
  Eye,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Calendar,
  Terminal,
  Zap,
  Cpu,
  CornerDownRight
} from 'lucide-react';

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
  }, [messages, isLoading]);

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
    { label: "> 📍 WHERE DO I LIVE?", text: "Where do I live right now?" },
    { label: "> 🕰️ WHERE DID I LIVE BEFORE?", text: "Where did I live before Tokyo?" },
    { label: "> 🍵 FAVORITE DRINK?", text: "What is my favorite beverage?" },
    { label: "> 🗄️ DATABASE CHOICE?", text: "What database did we choose for our project?" },
    { label: "> ⚡ UPDATE: MOVED TO TOKYO", text: "I moved to Tokyo last weekend and currently reside there." },
    { label: "> 🍵 PIVOT: SWITCHED TO MATCHA", text: "I quit coffee completely; now I only drink matcha green tea." },
    { label: "> 🗑️ GDPR PURGE: PHONE", text: "Forget my phone number." }
  ];

  const renderFormattedText = (text) => {
    if (!text) return null;
    const lines = text.split('\n');
    return lines.map((line, lIdx) => {
      const parts = line.split(/(\*\*.*?\*\*|`.*?`|\*.*?\*)/g);
      return (
        <div key={lIdx} style={{ minHeight: line ? 'auto' : '8px', marginBottom: '3px' }}>
          {parts.map((part, pIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return (
                <strong
                  key={pIdx}
                  style={{
                    color: 'var(--neon-green)',
                    fontWeight: 700,
                    textShadow: '0 0 6px var(--neon-green-glow)'
                  }}
                >
                  {part.slice(2, -2)}
                </strong>
              );
            } else if (part.startsWith('`') && part.endsWith('`')) {
              return (
                <span
                  key={pIdx}
                  style={{
                    background: 'var(--cyber-black)',
                    border: '1px solid var(--neon-green)',
                    color: 'var(--neon-green)',
                    padding: '1px 6px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.85em'
                  }}
                >
                  {part.slice(1, -1)}
                </span>
              );
            } else if (part.startsWith('*') && part.endsWith('*')) {
              return <em key={pIdx} style={{ color: 'var(--hot-magenta)' }}>{part.slice(1, -1)}</em>;
            }
            return part;
          })}
        </div>
      );
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
      {/* Date Simulation & Tenant Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 16px',
          background: 'rgba(18, 18, 26, 0.95)',
          borderBottom: '1px solid var(--cyber-border)',
          fontSize: '0.75rem',
          fontFamily: 'var(--font-mono)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)' }}>
          <Calendar size={13} color="var(--neon-green)" />
          <span className="tech-label" style={{ color: 'var(--neon-green)', fontWeight: 700 }}>
            &gt; SIMULATED_TIMELINE:
          </span>
          <select
            value={simulatedDate || ''}
            onChange={(e) => onSimulatedDateChange(e.target.value || null)}
            className="cyber-select"
            style={{ fontSize: '0.72rem', padding: '2px 8px' }}
          >
            <option value="">[LIVE / PRESENT REAL-TIME]</option>
            <option value="2026-09-01T10:00:00Z">DAY 01 (2026-09-01) - INITIAL SETUP</option>
            <option value="2026-09-02T10:00:00Z">DAY 02 (2026-09-02) - INTERMEDIATE MUTATIONS</option>
            <option value="2026-09-03T10:00:00Z">DAY 03 (2026-09-03) - RELOCATIONS & REVERSALS</option>
            <option value="2026-09-05T10:00:00Z">DAY 05 (2026-09-05) - CONSOLIDATION</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge-cyber badge-cyber-green">
            <ShieldCheck size={11} />
            NODE: {activeUser.toUpperCase()} [ISOLATED]
          </span>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '18px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}
      >
        {messages.length === 0 && (
          <div
            className="cyber-chamfer"
            style={{
              margin: 'auto',
              textAlign: 'center',
              maxWidth: '520px',
              padding: '36px 24px',
              background: 'rgba(18, 18, 26, 0.9)',
              border: '1px solid var(--neon-green)',
              boxShadow: '0 0 25px var(--neon-green-glow)',
              position: 'relative'
            }}
          >
            <div
              className="cyber-chamfer-sm"
              style={{
                width: '46px',
                height: '46px',
                border: '1px solid var(--neon-green)',
                background: 'rgba(0, 255, 136, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
                boxShadow: '0 0 15px var(--neon-green-glow)'
              }}
            >
              <Sparkles size={22} color="var(--neon-green)" />
            </div>
            <h2
              className="font-heading"
              style={{
                fontSize: '1.2rem',
                fontWeight: 800,
                marginBottom: '10px',
                letterSpacing: '0.1em',
                color: 'var(--text-primary)'
              }}
            >
              COGNITIVE BELIEF ARCHITECTURE
            </h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '20px', lineHeight: 1.6, fontFamily: 'var(--font-mono)' }}>
              MemoryOS tracks real-time temporal truth, belief mutations, and contradictory state updates across sessions. Enter assertions, query past history, or trigger GDPR purges!
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center' }}>
              {quickPrompts.slice(0, 4).map((qp, i) => (
                <button
                  key={i}
                  onClick={() => !isLoading && onSendMessage(qp.text)}
                  disabled={isLoading}
                  className="btn-cyber btn-cyber-outline"
                  style={{ fontSize: '0.72rem', padding: '6px 12px' }}
                >
                  <span>{qp.label}</span>
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
                maxWidth: isUser ? '75%' : '88%',
                gap: '6px'
              }}
            >
              {/* Message Bubble */}
              <div
                className="cyber-chamfer-sm"
                style={{
                  padding: '14px 18px',
                  background: isUser ? 'rgba(255, 0, 255, 0.08)' : 'rgba(18, 18, 26, 0.95)',
                  border: isUser ? '1px solid var(--hot-magenta)' : '1px solid var(--cyber-border)',
                  borderLeft: isUser ? '3px solid var(--hot-magenta)' : '3px solid var(--neon-green)',
                  boxShadow: isUser ? '0 0 15px rgba(255, 0, 255, 0.2)' : '0 0 15px rgba(0, 255, 136, 0.1)',
                  color: 'var(--text-primary)',
                  fontSize: '0.88rem',
                  lineHeight: 1.6,
                  fontFamily: 'var(--font-mono)'
                }}
              >
                {/* Header Tag */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '8px',
                    paddingBottom: '6px',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                    fontSize: '0.7rem',
                    fontFamily: 'var(--font-tech)',
                    fontWeight: 700,
                    letterSpacing: '0.1em'
                  }}
                >
                  <span style={{ color: isUser ? 'var(--hot-magenta)' : 'var(--neon-green)' }}>
                    {isUser ? `> <OPERATOR::${activeUser.toUpperCase()}>` : '> [MEMORY_CORE.SYS]'}
                  </span>
                  <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem' }}>
                    {msg.simulated_date ? `SIM: ${msg.simulated_date.slice(0, 10)}` : new Date(msg.created_at || Date.now()).toLocaleTimeString()}
                  </span>
                </div>

                <div>{renderFormattedText(msg.content)}</div>
              </div>

              {/* Cognitive Attribution Trace */}
              {!isUser && hasAttribution && (
                <div
                  className="cyber-chamfer-sm"
                  style={{
                    marginTop: '2px',
                    padding: '10px 14px',
                    border: '1px solid var(--electric-cyan)',
                    borderLeft: '3px solid var(--electric-cyan)',
                    background: 'rgba(10, 10, 15, 0.98)',
                    boxShadow: '0 0 15px rgba(0, 212, 255, 0.15)',
                    fontSize: '0.74rem',
                    fontFamily: 'var(--font-mono)'
                  }}
                >
                  <div
                    onClick={() => toggleTrace(idx)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      userSelect: 'none'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Terminal size={13} color="var(--electric-cyan)" />
                      <span className="font-heading" style={{ fontWeight: 700, color: 'var(--electric-cyan)', letterSpacing: '0.08em', fontSize: '0.75rem' }}>
                        COGNITIVE ATTRIBUTION & REASONING TRACE
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                        [{msg.used_memories?.length || 0} ACTIVE // {msg.superseded_memories?.length || 0} SUPERSEDED]
                      </span>
                    </div>
                    {isExpanded ? <ChevronUp size={13} color="var(--electric-cyan)" /> : <ChevronDown size={13} color="var(--electric-cyan)" />}
                  </div>

                  {isExpanded && (
                    <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {/* Conflict Resolution Notes */}
                      {msg.conflict_notes?.length > 0 && (
                        <div
                          style={{
                            background: 'rgba(255, 170, 0, 0.08)',
                            border: '1px solid var(--alert-amber)',
                            padding: '8px 12px'
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--alert-amber)', fontWeight: 700, marginBottom: '4px' }}>
                            <AlertTriangle size={13} />
                            <span>&gt; CONTRADICTION MUTATION RESOLVED:</span>
                          </div>
                          {msg.conflict_notes.map((note, nIdx) => (
                            <div key={nIdx} style={{ color: '#FFE0B2', fontSize: '0.72rem' }}>• {note}</div>
                          ))}
                        </div>
                      )}

                      {/* Active Memories Consulted */}
                      {msg.used_memories?.length > 0 && (
                        <div>
                          <span style={{ color: 'var(--neon-green)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                            <CheckCircle size={12} /> &gt; ACTIVE TRUTH BELIEFS CONSULTED:
                          </span>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {msg.used_memories.map((m, mIdx) => (
                              <div
                                key={mIdx}
                                onClick={() => onSelectMemory && onSelectMemory(m.memory_id)}
                                className="cyber-chamfer-sm"
                                style={{
                                  padding: '8px 12px',
                                  background: 'rgba(0, 255, 136, 0.06)',
                                  border: '1px solid var(--neon-green)',
                                  cursor: 'pointer',
                                  boxShadow: '0 0 8px rgba(0, 255, 136, 0.1)'
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#FFFFFF', fontWeight: 600 }}>
                                  <span>{m.content}</span>
                                  <span style={{ color: 'var(--neon-green)' }}>SIM: {m.similarity_score}</span>
                                </div>
                                <div style={{ display: 'flex', gap: '12px', marginTop: '4px', color: 'var(--text-muted)', fontSize: '0.66rem' }}>
                                  <span>ID: #{m.memory_id?.slice(0, 6)}</span>
                                  <span>TYPE: {m.memory_type}</span>
                                  <span>INTERVAL: {m.valid_interval}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Superseded Historical State */}
                      {msg.superseded_memories?.length > 0 && (
                        <div>
                          <span style={{ color: 'var(--alert-amber)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                            <Clock size={12} /> &gt; OUTDATED / SUPERSEDED LINEAGE:
                          </span>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {msg.superseded_memories.map((m, mIdx) => (
                              <div
                                key={mIdx}
                                className="cyber-chamfer-sm"
                                style={{
                                  padding: '8px 12px',
                                  background: 'rgba(255, 170, 0, 0.06)',
                                  border: '1px solid var(--alert-amber)',
                                  color: '#cbd5e1'
                                }}
                              >
                                <div style={{ textDecoration: 'line-through', opacity: 0.75 }}>{m.content}</div>
                                <div style={{ color: 'var(--alert-amber)', fontSize: '0.68rem', marginTop: '3px' }}>
                                  REASON: {m.filter_reason}
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--neon-green)', fontSize: '0.8rem', padding: '10px', fontFamily: 'var(--font-mono)' }}>
            <div className="animate-pulse-glow" style={{ width: '8px', height: '8px', background: 'var(--neon-green)', boxShadow: '0 0 10px var(--neon-green)' }} />
            <span>&gt; RECONCILING COGNITIVE STATE, RESOLVING CONTRADICTIONS...</span>
            <span className="cursor-blink">█</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Fast Prompts */}
      <div
        style={{
          padding: '8px 16px',
          background: 'rgba(18, 18, 26, 0.95)',
          borderTop: '1px solid var(--cyber-border)',
          display: 'flex',
          gap: '8px',
          overflowX: 'auto'
        }}
      >
        {quickPrompts.map((qp, i) => (
          <button
            key={i}
            onClick={() => !isLoading && onSendMessage(qp.text)}
            disabled={isLoading}
            className="btn-cyber btn-cyber-outline"
            style={{ fontSize: '0.7rem', padding: '4px 10px', whiteSpace: 'nowrap' }}
          >
            <span>{qp.label}</span>
          </button>
        ))}
      </div>

      {/* Chat Input */}
      <form
        onSubmit={handleSubmit}
        style={{
          padding: '14px 18px',
          background: 'var(--cyber-black)',
          borderTop: '2px solid var(--neon-green)',
          display: 'flex',
          gap: '12px'
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`> COMMAND MEMORY_OS AS ${activeUser.toUpperCase()} (DECLARE FACT, UPDATE STATE, OR QUERY)...`}
          className="cyber-input"
          style={{ flex: 1 }}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="btn-cyber btn-cyber-primary"
          disabled={isLoading || !input.trim()}
        >
          <Send size={14} />
          <span>EXECUTE</span>
        </button>
      </form>
    </div>
  );
}
