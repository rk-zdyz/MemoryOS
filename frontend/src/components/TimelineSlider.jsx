import React, { useState } from 'react';
import { Clock, Calendar, ArrowRight, CheckCircle, AlertTriangle, Layers, Zap, Cpu } from 'lucide-react';

export default function TimelineSlider({ timelineEvents, activeUser }) {
  const [selectedEventId, setSelectedEventId] = useState(null);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          background: 'rgba(18, 18, 26, 0.95)',
          borderBottom: '1px solid var(--cyber-border)',
          fontFamily: 'var(--font-mono)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Clock size={15} color="var(--neon-green)" />
          <span className="font-heading" style={{ fontSize: '0.92rem', fontWeight: 800, letterSpacing: '0.08em', color: 'var(--text-primary)' }}>
            TEMPORAL MUTATION HIGHWAY // BELIEF EVOLUTION
          </span>
        </div>
        <div>
          <span className="badge-cyber badge-cyber-magenta">
            {timelineEvents?.length || 0} TOTAL STATE MUTATIONS
          </span>
        </div>
      </div>

      {/* Main Timeline Scrollable Content */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px 20px',
          position: 'relative'
        }}
      >
        {(!timelineEvents || timelineEvents.length === 0) ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '40px', fontFamily: 'var(--font-mono)' }}>
            &gt; NO TEMPORAL STATE MUTATIONS RECORDED YET FOR {activeUser.toUpperCase()}.
          </div>
        ) : (
          <div style={{ position: 'relative', maxWidth: '800px', margin: '0 auto' }}>
            {/* Central Laser Checkpoint Line */}
            <div
              style={{
                position: 'absolute',
                top: '0',
                bottom: '0',
                left: '28px',
                width: '2px',
                background: 'linear-gradient(180deg, var(--neon-green) 0%, var(--hot-magenta) 50%, var(--electric-cyan) 100%)',
                boxShadow: '0 0 10px var(--neon-green-glow)'
              }}
            />

            {/* Timeline Event Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {timelineEvents.map((evt, idx) => {
                const isActive = evt.status === 'ACTIVE';
                const isSuperseded = evt.status === 'SUPERSEDED';

                return (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '18px',
                      position: 'relative'
                    }}
                  >
                    {/* Glowing Checkpoint Node */}
                    <div
                      className="cyber-chamfer-sm"
                      style={{
                        width: '22px',
                        height: '22px',
                        background: isActive ? 'var(--neon-green)' : 'var(--alert-amber)',
                        boxShadow: isActive ? '0 0 12px var(--neon-green-glow)' : '0 0 12px rgba(255, 170, 0, 0.4)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 2,
                        marginTop: '12px'
                      }}
                    >
                      <div style={{ width: '6px', height: '6px', background: 'var(--cyber-black)' }} />
                    </div>

                    {/* Event Detail Box */}
                    <div
                      className="cyber-card cyber-chamfer-sm"
                      style={{
                        flex: 1,
                        padding: '14px 18px',
                        fontFamily: 'var(--font-mono)',
                        borderLeft: isActive ? '3px solid var(--neon-green)' : '3px solid var(--alert-amber)',
                        boxShadow: isActive ? '0 0 15px rgba(0, 255, 136, 0.1)' : '0 0 15px rgba(255, 170, 0, 0.1)'
                      }}
                    >
                      {/* Header */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className={isActive ? 'badge-cyber badge-cyber-green' : 'badge-cyber badge-cyber-amber'}>
                            {evt.status}
                          </span>
                          <span className="tech-label" style={{ fontSize: '0.7rem', color: 'var(--electric-cyan)', fontWeight: 700 }}>
                            {evt.memory_type}
                          </span>
                        </div>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                          RECORDED: {evt.created_at?.slice(0, 10) || 'UNKNOWN'}
                        </span>
                      </div>

                      {/* Content */}
                      <div style={{ fontSize: '0.88rem', color: 'var(--text-primary)', fontWeight: 600, marginBottom: '8px' }}>
                        {evt.content}
                      </div>

                      {/* Validity Window */}
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                        <div>
                          <span style={{ color: 'var(--text-muted)' }}>VALID FROM: </span>
                          <strong style={{ color: 'var(--neon-green)' }}>{evt.valid_from ? evt.valid_from.slice(0, 10) : 'PRESENT'}</strong>
                        </div>
                        {evt.valid_to && (
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>VALID TO: </span>
                            <strong style={{ color: 'var(--alert-amber)' }}>{evt.valid_to.slice(0, 10)}</strong>
                          </div>
                        )}
                        {evt.superseded_by_id && (
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>SUPERSEDED BY: </span>
                            <span style={{ color: 'var(--hot-magenta)' }}>#{evt.superseded_by_id.slice(0, 8)}</span>
                          </div>
                        )}
                      </div>

                      {/* Supersede Reason */}
                      {evt.supersede_reason && (
                        <div
                          style={{
                            marginTop: '8px',
                            padding: '6px 10px',
                            background: 'rgba(255, 170, 0, 0.08)',
                            border: '1px solid var(--alert-amber)',
                            fontSize: '0.7rem',
                            color: '#FFE0B2'
                          }}
                        >
                          &gt; CAUSAL OVERRIDE: {evt.supersede_reason}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
