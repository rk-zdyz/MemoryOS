import React, { useState, useEffect } from 'react';
import { Shield, X, FileText, CheckCircle2, Terminal } from 'lucide-react';
import { getAuditLogs } from '../api';

export default function AuditLogModal({ isOpen, onClose, activeUser }) {
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadAuditLogs();
    }
  }, [isOpen, activeUser]);

  const loadAuditLogs = async () => {
    setIsLoading(true);
    try {
      const res = await getAuditLogs(activeUser);
      setLogs(res.logs || []);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    } finally {
      setIsLoading(false);
    }
  };

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
          width: '640px',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 0 50px rgba(255, 0, 255, 0.3)',
          border: '1px solid var(--hot-magenta)',
          fontFamily: 'var(--font-mono)'
        }}
      >
        {/* Terminal Chrome Bar */}
        <div className="terminal-chrome" style={{ borderBottomColor: 'var(--hot-magenta)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="traffic-dots">
              <div className="traffic-dot traffic-dot-red" />
              <div className="traffic-dot traffic-dot-amber" />
              <div className="traffic-dot traffic-dot-green" />
            </div>
            <span className="tech-label" style={{ fontSize: '0.74rem', fontWeight: 800, color: 'var(--hot-magenta)', letterSpacing: '0.1em' }}>
              IMMUTABLE AUDIT LOG // GDPR ARTICLE 17 ERASURE TRAIL
            </span>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <X size={14} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '20px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            Cryptographically sealed audit receipts of targeted memory purges, selective forgetting operations, and state mutations for tenant <strong>{activeUser.toUpperCase()}</strong>.
          </div>

          {isLoading ? (
            <div style={{ textAlign: 'center', color: 'var(--neon-green)', padding: '24px' }}>
              &gt; FETCHING IMMUTABLE AUDIT TRAIL...
              <span className="cursor-blink">█</span>
            </div>
          ) : logs.length === 0 ? (
            <div className="cyber-chamfer-sm" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '30px', background: 'var(--cyber-black)', border: '1px solid var(--cyber-border)' }}>
              &gt; NO PURGE RECEIPTS FOUND IN AUDIT LOG FOR {activeUser.toUpperCase()}.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {logs.map((log) => (
                <div
                  key={log.id}
                  className="cyber-chamfer-sm"
                  style={{
                    padding: '12px 14px',
                    background: 'var(--cyber-black)',
                    border: '1px solid var(--cyber-border)',
                    borderLeft: '3px solid var(--hot-magenta)',
                    fontSize: '0.76rem'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ color: 'var(--hot-magenta)', fontWeight: 700 }}>
                      ACTION: {log.action}
                    </span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>
                      {log.created_at}
                    </span>
                  </div>

                  <div style={{ color: 'var(--text-primary)', marginBottom: '4px' }}>
                    &gt; REASON: {log.reason}
                  </div>

                  {log.target_memory_id && (
                    <div style={{ color: 'var(--electric-cyan)', fontSize: '0.7rem' }}>
                      PURGED TARGET ID: #{log.target_memory_id}
                    </div>
                  )}

                  <div style={{ color: 'var(--text-muted)', fontSize: '0.66rem', marginTop: '4px' }}>
                    RECEIPT HASH: #{log.id}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '12px 20px', background: 'var(--cyber-black)', borderTop: '1px solid var(--cyber-border)', display: 'flex', justifyContent: 'flex-end' }}>
          <button onClick={onClose} className="btn-cyber btn-cyber-primary" style={{ padding: '6px 16px' }}>
            <span>CLOSE AUDIT TRAIL</span>
          </button>
        </div>
      </div>
    </div>
  );
}
