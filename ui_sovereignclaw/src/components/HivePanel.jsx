import { useMemo, useRef, useEffect, useState } from 'react';
import { useSCStore } from '../store';

const NODE_COUNT = 269;
const W = 280, H = 400;

// Stable random positions seeded by index
function nodePositions() {
  const positions = [];
  // deterministic pseudo-random using golden ratio spiral
  const phi = (1 + Math.sqrt(5)) / 2;
  for (let i = 0; i < NODE_COUNT; i++) {
    const t = i / phi;
    const r = (Math.sqrt(i + 1) / Math.sqrt(NODE_COUNT)) * 0.45;
    const x = 0.5 + r * Math.cos(2 * Math.PI * t);
    const y = 0.5 + r * Math.sin(2 * Math.PI * t);
    positions.push({ x: x * W, y: y * H });
  }
  return positions;
}

const POSITIONS = nodePositions();

function useAnimatedSet(activeSet, allModules) {
  const [glowing, setGlowing] = useState(new Set());
  const prev = useRef(new Set());

  useEffect(() => {
    const next = new Set();
    allModules.forEach((m, i) => {
      if (activeSet.has(m.name ?? m.id ?? `module_${i}`)) next.add(i);
    });
    setGlowing(next);
    prev.current = next;
  }, [activeSet, allModules]);

  return glowing;
}

export function HivePanel() {
  const modules = useSCStore(s => s.modules);
  const hiveActive = useSCStore(s => s.hiveActive);
  const hiveEdges = useSCStore(s => s.hiveEdges);
  const consensusScore = useSCStore(s => s.consensusScore);
  const wsStatus = useSCStore(s => s.wsStatus);
  const hivePanelOpen = useSCStore(s => s.hivePanelOpen);
  const toggleHivePanel = useSCStore(s => s.toggleHivePanel);

  // Fallback: use indices if no modules loaded yet
  const nodeLabels = useMemo(() => {
    if (modules.length > 0) return modules.map(m => m.name ?? m.id);
    return Array.from({ length: NODE_COUNT }, (_, i) => `module_${i}`);
  }, [modules]);

  const glowing = useAnimatedSet(hiveActive, modules.length > 0 ? modules : nodeLabels.map(n => ({ name: n })));

  // Idle shimmer: randomly activate a few nodes when ws is disconnected
  const [idleActive, setIdleActive] = useState(new Set());
  useEffect(() => {
    if (wsStatus === 'connected') { setIdleActive(new Set()); return; }
    const interval = setInterval(() => {
      const next = new Set();
      for (let k = 0; k < 8; k++) next.add(Math.floor(Math.random() * NODE_COUNT));
      setIdleActive(next);
    }, 800);
    return () => clearInterval(interval);
  }, [wsStatus]);

  const activeIndices = wsStatus === 'connected' ? glowing : idleActive;
  const [hovered, setHovered] = useState(null);

  // Build edge index map
  const edgeLines = useMemo(() => {
    if (!hiveEdges?.length) return [];
    return hiveEdges.slice(0, 20).map(e => {
      const fi = nodeLabels.indexOf(e.from);
      const ti = nodeLabels.indexOf(e.to);
      if (fi < 0 || ti < 0) return null;
      return { x1: POSITIONS[fi].x, y1: POSITIONS[fi].y, x2: POSITIONS[ti].x, y2: POSITIONS[ti].y };
    }).filter(Boolean);
  }, [hiveEdges, nodeLabels]);

  if (!hivePanelOpen) {
    return (
      <div
        onClick={toggleHivePanel}
        style={{
          width: 28, background: 'var(--color-sc-surface)', borderLeft: '1px solid var(--color-sc-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
          writingMode: 'vertical-rl', fontSize: 11, color: 'var(--color-sc-gold)', letterSpacing: '0.1em',
          fontFamily: 'var(--font-grotesk)', userSelect: 'none',
        }}
        title="Show Hive"
      >
        HIVE
      </div>
    );
  }

  return (
    <div style={{
      width: 300, flexShrink: 0, background: 'var(--color-sc-surface)',
      borderLeft: '1px solid var(--color-sc-border)', display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid var(--color-sc-border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, fontFamily: 'var(--font-grotesk)', fontWeight: 600, letterSpacing: '0.08em', color: 'var(--color-sc-gold)' }}>
            THE HIVE
          </span>
          <span style={{
            fontSize: 10, padding: '1px 6px', borderRadius: 10,
            background: 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)', color: 'var(--color-sc-gold)',
            fontFamily: 'var(--font-mono)',
          }}>
            {NODE_COUNT} modules
          </span>
        </div>
        <button
          onClick={toggleHivePanel}
          style={{ background: 'none', border: 'none', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 16, lineHeight: 1, padding: '0 2px' }}
          title="Collapse"
        >×</button>
      </div>

      {/* Status */}
      <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--color-sc-border)', display: 'flex', gap: 16, fontSize: 11 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ color: 'var(--color-sc-text-muted)' }}>ACTIVE</span>
          <span style={{ color: 'var(--color-sc-gold-glow)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
            {wsStatus === 'connected' ? hiveActive.size : '~'} nodes
          </span>
        </div>
        {consensusScore != null && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ color: 'var(--color-sc-text-muted)' }}>CONSENSUS</span>
            <span style={{ color: 'var(--color-sc-success)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
              {Math.round(consensusScore * 100)}%
            </span>
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ color: 'var(--color-sc-text-muted)' }}>STREAM</span>
          <span style={{
            color: wsStatus === 'connected' ? 'var(--color-sc-success)' : wsStatus === 'reconnecting' ? 'var(--color-sc-gold-glow)' : 'var(--color-sc-danger)',
            fontFamily: 'var(--font-mono)', fontWeight: 600, textTransform: 'uppercase',
          }}>{wsStatus}</span>
        </div>
      </div>

      {/* SVG Visualization */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          style={{ width: '100%', height: '100%' }}
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Active edges */}
          {edgeLines.map((e, i) => (
            <line key={i} x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2}
              stroke="var(--color-sc-gold)" strokeWidth="0.8" strokeDasharray="4 4" opacity="0.4"
              style={{ animation: 'edge-flow 1.5s linear infinite' }}
            />
          ))}

          {/* Nodes */}
          {POSITIONS.map((pos, i) => {
            const isActive = activeIndices.has(i);
            return (
              <g key={i}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'default' }}
              >
                {isActive && (
                  <circle cx={pos.x} cy={pos.y} r={8} fill="var(--color-sc-gold)" opacity={0.12} />
                )}
                <circle
                  cx={pos.x} cy={pos.y}
                  r={isActive ? 3.5 : 2}
                  fill={isActive ? 'var(--color-sc-gold-glow)' : '#2A2A44'}
                  style={isActive ? { animation: 'node-pulse 1s ease-in-out infinite', transformOrigin: `${pos.x}px ${pos.y}px` } : undefined}
                />
                {hovered === i && nodeLabels[i] && (
                  <text x={pos.x + 6} y={pos.y + 4} fontSize="7" fill="var(--color-sc-text)" fontFamily="var(--font-mono)" opacity={0.8}>
                    {nodeLabels[i].replace('module_', 'm')}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Active module list */}
      {wsStatus === 'connected' && hiveActive.size > 0 && (
        <div style={{
          borderTop: '1px solid var(--color-sc-border)', padding: '8px 12px',
          maxHeight: 100, overflowY: 'auto',
        }}>
          <div style={{ fontSize: 10, color: 'var(--color-sc-text-muted)', marginBottom: 4, fontFamily: 'var(--font-grotesk)', letterSpacing: '0.06em' }}>
            BIDDING NOW
          </div>
          {Array.from(hiveActive).slice(0, 8).map(name => (
            <div key={name} style={{
              fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-sc-gold)',
              padding: '2px 0', display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--color-sc-gold-glow)', display: 'inline-block' }} />
              {name}
            </div>
          ))}
          {hiveActive.size > 8 && (
            <div style={{ fontSize: 10, color: 'var(--color-sc-text-muted)', marginTop: 2 }}>+{hiveActive.size - 8} more</div>
          )}
        </div>
      )}
    </div>
  );
}
