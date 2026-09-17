import React, { useState } from 'react';
import { Clock, ArrowRight, CheckCircle, AlertTriangle, ShieldCheck, Play } from 'lucide-react';

export default function TimelineSlider({ timelineEvents, activeUser }) {
  const [selectedEvent, setSelectedEvent] = useState(null);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '16px 20px', overflowY: 'auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <Clock size={18} color="#06b6d4" />
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Temporal Lineage & Truth Evolution</h3>
        </div>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          Trace every state transition, mutation, and contradiction for <strong>{activeUser.toUpperCase()}</strong> in chronological order.
        </p>
      </div>

      {/* Timeline Stream */}
      <div style={{ position: 'relative', paddingLeft: '28px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Vertical Axis Line */}
        <div style={{
          position: 'absolute', left: '10px', top: '10px', bottom: '10px', width: '2px',
          background: 'linear-gradient(to bottom, #06b6d4, #6366f1, #10b981)'
        }} />

        {timelineEvents.length === 0 && (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem', padding: '20px 0' }}>
            No timeline events recorded for this user.
          </div>
        )}

        {timelineEvents.map((evt, idx) => {
          const isActive = evt.status === 'ACTIVE';
          const isSuperseded = evt.status === 'SUPERSEDED';
          const isForgotten = evt.status === 'FORGOTTEN';

          const dotColor = isActive ? '#10b981' : (isSuperseded ? '#f59e0b' : '#f43f5e');

          return (
            <div key={evt.id || idx} style={{ position: 'relative' }}>
              {/* Pulsing Node Marker */}
              <div
                style={{
                  position: 'absolute', left: '-23px', top: '14px', width: '12px', height: '12px',
                  borderRadius: '50%', background: dotColor,
                  border: '2px solid var(--bg-primary)',
                  boxShadow: `0 0 10px ${dotColor}`
                }}
              />

              {/* Event Card */}
              <div
                className="glass-panel"
                style={{
                  padding: '12px 16px',
                  borderRadius: '10px',
                  border: isActive ? '1px solid rgba(16, 185, 129, 0.4)' : (isSuperseded ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid var(--border-subtle)'),
                  background: isActive ? 'rgba(16, 185, 129, 0.05)' : 'rgba(22, 29, 46, 0.65)'
                }}
              >
                {/* Date & Status */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
                    {evt.valid_from ? evt.valid_from.slice(0, 19).replace('T', ' ') : 'Session Initial'}
                  </span>
                  <span
                    className={isActive ? 'badge-active' : (isSuperseded ? 'badge-superseded' : 'badge-forgotten')}
                    style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.68rem', fontWeight: 700 }}
                  >
                    {evt.status}
                  </span>
                </div>

                {/* Content */}
                <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#f8fafc', marginBottom: '6px' }}>
                  {evt.content}
                </div>

                {/* Triple representation */}
                {evt.triple && (
                  <div style={{
                    fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: '#38bdf8',
                    background: 'rgba(0, 0, 0, 0.35)', padding: '4px 8px', borderRadius: '4px',
                    display: 'inline-block', marginBottom: '6px'
                  }}>
                    {evt.triple.subject} ➔ {evt.triple.predicate} ➔ {evt.triple.object}
                  </div>
                )}

                {/* Supersede / Mutation explanation */}
                {isSuperseded && evt.supersede_reason && (
                  <div style={{
                    marginTop: '6px', padding: '6px 10px', borderRadius: '6px',
                    background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.3)',
                    color: '#fbbf24', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '6px'
                  }}>
                    <AlertTriangle size={14} />
                    <span><strong>Superseded:</strong> {evt.supersede_reason}</span>
                  </div>
                )}

                {/* Validity interval */}
                <div style={{ marginTop: '8px', fontSize: '0.68rem', color: 'var(--text-muted)', display: 'flex', gap: '14px' }}>
                  <span>Valid Interval: {evt.valid_from ? evt.valid_from.slice(0, 10) : 'Start'} ➔ {evt.valid_to ? evt.valid_to.slice(0, 10) : 'Present'}</span>
                  <span>Type: {evt.memory_type}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
