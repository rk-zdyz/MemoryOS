import React, { useRef, useEffect, useState } from 'react';
import { Network, RefreshCw, ZoomIn, ZoomOut, Info } from 'lucide-react';

export default function KnowledgeGraph({ graphData, onRefresh, onSelectMemory }) {
  const canvasRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [zoom, setZoom] = useState(1.0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.parentElement.clientWidth || 800;
    const height = canvas.height = canvas.parentElement.clientHeight || 550;

    const nodes = graphData?.nodes || [];
    const edges = graphData?.edges || [];

    if (nodes.length === 0) {
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = '#64748b';
      ctx.font = '14px Outfit';
      ctx.textAlign = 'center';
      ctx.fillText('No knowledge nodes found for this user.', width / 2, height / 2);
      return;
    }

    // Assign dynamic circular layout around central user node
    const userNode = nodes.find(n => n.type === 'USER') || nodes[0];
    const otherNodes = nodes.filter(n => n.id !== userNode.id);

    const centerX = width / 2;
    const centerY = height / 2;
    userNode.x = centerX;
    userNode.y = centerY;

    const radius = Math.min(width, height) * 0.35 * zoom;
    otherNodes.forEach((node, i) => {
      const angle = (i / Math.max(otherNodes.length, 1)) * 2 * Math.PI;
      node.x = centerX + radius * Math.cos(angle);
      node.y = centerY + radius * Math.sin(angle);
    });

    // Render loop
    ctx.clearRect(0, 0, width, height);

    // Draw Background Grid
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 40) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
    }
    for (let y = 0; y < height; y += 40) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
    }

    // Draw Edges
    edges.forEach(edge => {
      const src = nodes.find(n => n.id === edge.source);
      const tgt = nodes.find(n => n.id === edge.target);
      if (!src || !tgt) return;

      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);

      if (edge.status === 'EVOLUTION') {
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
      } else if (edge.status === 'SUPERSEDED') {
        ctx.strokeStyle = 'rgba(245, 158, 11, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 3]);
      } else {
        ctx.strokeStyle = 'rgba(6, 182, 212, 0.5)';
        ctx.lineWidth = 1.8;
        ctx.setLineDash([]);
      }
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw Edge Label
      if (edge.label) {
        const midX = (src.x + tgt.x) / 2;
        const midY = (src.y + tgt.y) / 2;
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px JetBrains Mono';
        ctx.textAlign = 'center';
        ctx.fillText(edge.label, midX, midY - 4);
      }
    });

    // Draw Nodes
    nodes.forEach(node => {
      const isUser = node.type === 'USER';
      const nodeRadius = isUser ? 26 : 18;

      // Outer glow
      ctx.beginPath();
      ctx.arc(node.x, node.y, nodeRadius + 6, 0, 2 * Math.PI);
      if (node.status === 'ACTIVE') {
        ctx.fillStyle = 'rgba(16, 185, 129, 0.2)';
      } else if (node.status === 'SUPERSEDED') {
        ctx.fillStyle = 'rgba(245, 158, 11, 0.15)';
      } else {
        ctx.fillStyle = 'rgba(99, 102, 241, 0.2)';
      }
      ctx.fill();

      // Node Body
      ctx.beginPath();
      ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
      ctx.fillStyle = node.color || (node.status === 'ACTIVE' ? '#10b981' : '#f59e0b');
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Node Label
      ctx.fillStyle = '#f8fafc';
      ctx.font = isUser ? 'bold 12px Outfit' : '11px Outfit';
      ctx.textAlign = 'center';
      ctx.fillText(node.label, node.x, node.y + nodeRadius + 14);

      if (node.status && !isUser) {
        ctx.fillStyle = node.status === 'ACTIVE' ? '#34d399' : '#fbbf24';
        ctx.font = '9px JetBrains Mono';
        ctx.fillText(node.status, node.x, node.y + nodeRadius + 26);
      }
    });

  }, [graphData, zoom]);

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const nodes = graphData?.nodes || [];
    for (const node of nodes) {
      if (node.x && node.y) {
        const dist = Math.hypot(node.x - x, node.y - y);
        if (dist <= 26) {
          setSelectedNode(node);
          return;
        }
      }
    }
    setSelectedNode(null);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
      {/* Controls */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 16px', background: 'rgba(16, 21, 34, 0.7)',
        borderBottom: '1px solid var(--border-subtle)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Network size={16} color="#06b6d4" />
          <h3 style={{ fontSize: '0.9rem', fontWeight: 600 }}>Active vs Superseded Belief Graph</h3>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            (Emerald = Active Truth • Amber = Superseded History • Red Dashed = Mutation Path)
          </span>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button onClick={() => setZoom(z => Math.max(0.6, z - 0.1))} className="btn-secondary" style={{ padding: '4px 8px' }}>
            <ZoomOut size={13} />
          </button>
          <button onClick={() => setZoom(z => Math.min(1.6, z + 0.1))} className="btn-secondary" style={{ padding: '4px 8px' }}>
            <ZoomIn size={13} />
          </button>
          <button onClick={onRefresh} className="btn-secondary" style={{ padding: '4px 8px' }}>
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* Canvas container */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          style={{ width: '100%', height: '100%', display: 'block', cursor: 'pointer' }}
        />

        {/* Selected Node Overlay Modal */}
        {selectedNode && (
          <div
            className="glass-panel"
            style={{
              position: 'absolute', bottom: '16px', right: '16px',
              maxWidth: '320px', padding: '14px', zIndex: 10,
              border: '1px solid var(--accent-cyan)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#38bdf8' }}>
                Node Details
              </span>
              <button
                onClick={() => setSelectedNode(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>
            <div style={{ fontSize: '0.8rem', marginBottom: '6px', color: '#f8fafc' }}>
              {selectedNode.full_content || selectedNode.label}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <div>Status: <strong style={{ color: selectedNode.status === 'ACTIVE' ? '#34d399' : '#fbbf24' }}>{selectedNode.status}</strong></div>
              <div>Type: {selectedNode.type}</div>
              {selectedNode.valid_interval && <div>Interval: {selectedNode.valid_interval}</div>}
              {selectedNode.supersede_reason && (
                <div style={{ color: '#fbbf24', marginTop: '4px' }}>
                  ⚠️ {selectedNode.supersede_reason}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
