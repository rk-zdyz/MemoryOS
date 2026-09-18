import React, { useRef, useEffect, useState } from 'react';
import { Network, RefreshCw, ZoomIn, ZoomOut, Filter, Search, Info, X, Zap, Cpu } from 'lucide-react';

export default function KnowledgeGraph({ graphData, onRefresh, onSelectMemory }) {
  const canvasRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDraggingCanvas, setIsDraggingCanvas] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [draggedNode, setDraggedNode] = useState(null);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const nodesRef = useRef([]);

  // Initialize node positions and force simulation
  useEffect(() => {
    const rawNodes = graphData?.nodes || [];
    const width = 800;
    const height = 550;

    // Filter nodes based on user toggle
    const filteredNodes = rawNodes.filter(n => {
      if (statusFilter === 'ACTIVE' && n.status !== 'ACTIVE' && n.type !== 'USER') return false;
      if (statusFilter === 'SUPERSEDED' && n.status !== 'SUPERSEDED' && n.type !== 'USER') return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return n.label.toLowerCase().includes(q) || (n.full_content && n.full_content.toLowerCase().includes(q));
      }
      return true;
    });

    const userNode = filteredNodes.find(n => n.type === 'USER') || filteredNodes[0];
    const otherNodes = filteredNodes.filter(n => !userNode || n.id !== userNode.id);

    const centerX = width / 2;
    const centerY = height / 2;

    if (userNode) {
      userNode.x = centerX;
      userNode.y = centerY;
      userNode.vx = 0;
      userNode.vy = 0;
    }

    const radius = Math.min(width, height) * 0.35;
    otherNodes.forEach((node, i) => {
      const existing = nodesRef.current.find(n => n.id === node.id);
      if (existing && existing.x && existing.y) {
        node.x = existing.x;
        node.y = existing.y;
      } else {
        const angle = (i / Math.max(otherNodes.length, 1)) * 2 * Math.PI;
        node.x = centerX + radius * Math.cos(angle);
        node.y = centerY + radius * Math.sin(angle);
      }
      node.vx = 0;
      node.vy = 0;
    });

    nodesRef.current = filteredNodes;
  }, [graphData, statusFilter, searchQuery]);

  // Main Canvas Render Loop
  useEffect(() => {
    let animationFrameId;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const render = () => {
      const width = canvas.width = canvas.parentElement.clientWidth || 800;
      const height = canvas.height = canvas.parentElement.clientHeight || 550;

      const nodes = nodesRef.current;
      const edges = graphData?.edges || [];

      ctx.clearRect(0, 0, width, height);

      // Save canvas state
      ctx.save();
      ctx.translate(pan.x, pan.y);
      ctx.scale(zoom, zoom);

      // Draw Cyberpunk Matrix Grid in canvas background
      ctx.strokeStyle = 'rgba(0, 255, 136, 0.05)';
      ctx.lineWidth = 1;
      const gridSize = 40;
      for (let x = -width; x < width * 2; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, -height);
        ctx.lineTo(x, height * 2);
        ctx.stroke();
      }
      for (let y = -height; y < height * 2; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(-width, y);
        ctx.lineTo(width * 2, y);
        ctx.stroke();
      }

      // Force Simulation Step
      const centerX = width / 2;
      const centerY = height / 2;

      for (let i = 0; i < nodes.length; i++) {
        const n1 = nodes[i];
        if (n1 === draggedNode) continue;

        // Repulsion between nodes
        for (let j = i + 1; j < nodes.length; j++) {
          const n2 = nodes[j];
          const dx = n2.x - n1.x;
          const dy = n2.y - n1.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < 180) {
            const force = (180 - dist) / 180 * 0.4;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            if (n1.type !== 'USER') {
              n1.vx -= fx;
              n1.vy -= fy;
            }
            if (n2.type !== 'USER') {
              n2.vx += fx;
              n2.vy += fy;
            }
          }
        }

        // Attraction to center
        if (n1.type !== 'USER') {
          const cdx = centerX - n1.x;
          const cdy = centerY - n1.y;
          n1.vx += cdx * 0.0008;
          n1.vy += cdy * 0.0008;
        }

        // Apply velocity with damping
        n1.x += n1.vx || 0;
        n1.y += n1.vy || 0;
        n1.vx = (n1.vx || 0) * 0.85;
        n1.vy = (n1.vy || 0) * 0.85;
      }

      // Draw Edges
      edges.forEach(edge => {
        const source = nodes.find(n => n.id === edge.source);
        const target = nodes.find(n => n.id === edge.target);
        if (!source || !target) return;

        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);

        if (edge.type === 'SUPERSEDES') {
          // Cyberpunk Mutation Vector: Hot Magenta Dashed
          ctx.strokeStyle = '#ff00ff';
          ctx.lineWidth = 2.5;
          ctx.setLineDash([6, 6]);
          ctx.shadowColor = '#ff00ff';
          ctx.shadowBlur = 10;
        } else {
          // Normal belief edge: Neon Green / Electric Cyan
          ctx.strokeStyle = 'rgba(0, 255, 136, 0.45)';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([]);
          ctx.shadowColor = '#00ff88';
          ctx.shadowBlur = 6;
        }
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.shadowBlur = 0;

        // Edge Predicate Label
        if (edge.label) {
          const midX = (source.x + target.x) / 2;
          const midY = (source.y + target.y) / 2;
          ctx.fillStyle = '#0a0a0f';
          ctx.fillRect(midX - 35, midY - 9, 70, 18);
          ctx.strokeStyle = edge.type === 'SUPERSEDES' ? '#ff00ff' : 'rgba(0, 255, 136, 0.5)';
          ctx.strokeRect(midX - 35, midY - 9, 70, 18);

          ctx.fillStyle = edge.type === 'SUPERSEDES' ? '#ffaa00' : '#00ff88';
          ctx.font = '9px "Share Tech Mono", monospace';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(edge.label.toUpperCase().slice(0, 12), midX, midY);
        }
      });

      // Draw Nodes
      nodes.forEach(node => {
        const isSelected = selectedNode?.id === node.id;
        const isUser = node.type === 'USER';
        const isActive = node.status === 'ACTIVE';
        const isSuperseded = node.status === 'SUPERSEDED';

        let nodeColor = '#00ff88'; // Neon Green
        let shadowColor = 'rgba(0, 255, 136, 0.8)';
        let radius = isUser ? 24 : 16;

        if (isUser) {
          nodeColor = '#ff00ff'; // Hot Magenta
          shadowColor = '#ff00ff';
        } else if (isSuperseded) {
          nodeColor = '#ffaa00'; // Alert Amber
          shadowColor = '#ffaa00';
        }

        // Draw Outer Neon Glow Ring
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + (isSelected ? 6 : 3), 0, Math.PI * 2);
        ctx.strokeStyle = shadowColor;
        ctx.lineWidth = isSelected ? 3 : 1.5;
        ctx.shadowColor = shadowColor;
        ctx.shadowBlur = isSelected ? 20 : 12;
        ctx.stroke();

        // Draw Node Core
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = isUser ? '#ff00ff' : (isSuperseded ? '#161622' : '#0a0a0f');
        ctx.fill();
        ctx.strokeStyle = nodeColor;
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Label
        ctx.fillStyle = '#FFFFFF';
        ctx.font = isUser ? 'bold 11px "Orbitron", sans-serif' : '10px "Share Tech Mono", monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const labelText = node.label || 'Node';
        ctx.fillText(labelText.length > 14 ? labelText.slice(0, 12) + '..' : labelText, node.x, node.y + radius + 14);

        // Status Tag
        if (!isUser) {
          ctx.fillStyle = isSuperseded ? '#ffaa00' : '#00ff88';
          ctx.font = '8px "Share Tech Mono", monospace';
          ctx.fillText(node.status || '', node.x, node.y + radius + 25);
        }
      });

      ctx.restore();
      animationFrameId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationFrameId);
  }, [graphData, pan, zoom, selectedNode, draggedNode]);

  // Mouse Interaction Handlers
  const handleMouseDown = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = (e.clientX - rect.left - pan.x) / zoom;
    const mouseY = (e.clientY - rect.top - pan.y) / zoom;

    const clicked = nodesRef.current.find(n => {
      const dx = n.x - mouseX;
      const dy = n.y - mouseY;
      return Math.sqrt(dx * dx + dy * dy) < (n.type === 'USER' ? 24 : 18);
    });

    if (clicked) {
      setSelectedNode(clicked);
      setDraggedNode(clicked);
      if (onSelectMemory && clicked.id) onSelectMemory(clicked.id);
    } else {
      setIsDraggingCanvas(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e) => {
    if (draggedNode) {
      const rect = canvasRef.current.getBoundingClientRect();
      draggedNode.x = (e.clientX - rect.left - pan.x) / zoom;
      draggedNode.y = (e.clientY - rect.top - pan.y) / zoom;
    } else if (isDraggingCanvas) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  };

  const handleMouseUp = () => {
    setDraggedNode(null);
    setIsDraggingCanvas(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
      {/* Control Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 16px',
          background: 'rgba(18, 18, 26, 0.95)',
          borderBottom: '1px solid var(--cyber-border)',
          fontSize: '0.78rem',
          fontFamily: 'var(--font-mono)'
        }}
      >
        {/* Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="tech-label" style={{ color: 'var(--neon-green)', fontWeight: 700 }}>&gt; FILTER_STATUS:</span>
          {['ALL', 'ACTIVE', 'SUPERSEDED'].map(f => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={statusFilter === f ? 'btn-cyber btn-cyber-primary' : 'btn-cyber btn-cyber-ghost'}
              style={{ fontSize: '0.7rem', padding: '4px 10px' }}
            >
              <span>{f}</span>
            </button>
          ))}
        </div>

        {/* Search & Zoom */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--cyber-black)', padding: '4px 8px', border: '1px solid var(--cyber-border)' }}>
            <Search size={12} color="var(--neon-green)" />
            <input
              type="text"
              placeholder="SEARCH NODES..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--neon-green)',
                fontSize: '0.72rem',
                fontFamily: 'var(--font-mono)',
                outline: 'none',
                width: '130px'
              }}
            />
          </div>

          <button onClick={() => setZoom(z => Math.min(z + 0.15, 2.2))} className="btn-cyber btn-cyber-ghost" style={{ padding: '4px 8px' }}>
            <ZoomIn size={13} />
          </button>
          <button onClick={() => setZoom(z => Math.max(z - 0.15, 0.5))} className="btn-cyber btn-cyber-ghost" style={{ padding: '4px 8px' }}>
            <ZoomOut size={13} />
          </button>
          <button onClick={onRefresh} className="btn-cyber btn-cyber-ghost" style={{ padding: '4px 8px' }}>
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', background: 'var(--cyber-black)' }}>
        <canvas
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          style={{ width: '100%', height: '100%', cursor: isDraggingCanvas ? 'grabbing' : 'grab' }}
        />

        {/* Legend */}
        <div
          className="cyber-chamfer-sm"
          style={{
            position: 'absolute',
            bottom: '14px',
            left: '14px',
            padding: '10px 14px',
            background: 'rgba(18, 18, 26, 0.92)',
            border: '1px solid var(--cyber-border)',
            borderLeft: '3px solid var(--neon-green)',
            boxShadow: '0 0 15px rgba(0, 255, 136, 0.15)',
            fontSize: '0.7rem',
            fontFamily: 'var(--font-mono)',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--hot-magenta)', boxShadow: '0 0 6px var(--hot-magenta)' }} />
            <span>USER ROOT CORE</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--neon-green)', boxShadow: '0 0 6px var(--neon-green)' }} />
            <span>ACTIVE TRUTH BELIEF</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--alert-amber)', boxShadow: '0 0 6px var(--alert-amber)' }} />
            <span>SUPERSEDED / OUTDATED</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '14px', height: '2px', background: 'var(--hot-magenta)', borderTop: '2px dashed var(--hot-magenta)' }} />
            <span>MUTATION LINEAGE VECTOR</span>
          </div>
        </div>

        {/* Selected Node Details Drawer */}
        {selectedNode && (
          <div
            className="cyber-chamfer-sm"
            style={{
              position: 'absolute',
              top: '14px',
              right: '14px',
              width: '320px',
              background: 'rgba(18, 18, 26, 0.98)',
              border: '1px solid var(--hot-magenta)',
              borderLeft: '3px solid var(--hot-magenta)',
              boxShadow: '0 0 25px rgba(255, 0, 255, 0.25)',
              padding: '16px',
              fontSize: '0.76rem',
              fontFamily: 'var(--font-mono)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', borderBottom: '1px solid var(--cyber-border)', paddingBottom: '8px' }}>
              <span className="font-heading" style={{ color: 'var(--hot-magenta)', fontWeight: 800, letterSpacing: '0.08em', fontSize: '0.78rem' }}>
                NODE INSPECTOR
              </span>
              <button onClick={() => setSelectedNode(null)} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <X size={13} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div>
                <span className="tech-label" style={{ color: 'var(--text-muted)' }}>LABEL:</span>
                <div style={{ color: 'var(--neon-green)', fontWeight: 700, fontSize: '0.86rem' }}>{selectedNode.label}</div>
              </div>
              <div>
                <span className="tech-label" style={{ color: 'var(--text-muted)' }}>TYPE:</span>
                <div style={{ color: 'var(--text-primary)' }}>{selectedNode.type}</div>
              </div>
              <div>
                <span className="tech-label" style={{ color: 'var(--text-muted)' }}>STATUS:</span>
                <div style={{ marginTop: '2px' }}>
                  <span className={selectedNode.status === 'ACTIVE' ? 'badge-cyber badge-cyber-green' : 'badge-cyber badge-cyber-amber'}>
                    {selectedNode.status || 'UNKNOWN'}
                  </span>
                </div>
              </div>
              {selectedNode.full_content && (
                <div>
                  <span className="tech-label" style={{ color: 'var(--text-muted)' }}>CONTENT:</span>
                  <div style={{ color: 'var(--text-primary)', marginTop: '3px', background: 'var(--cyber-black)', padding: '8px', border: '1px solid var(--cyber-border)' }}>
                    {selectedNode.full_content}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
