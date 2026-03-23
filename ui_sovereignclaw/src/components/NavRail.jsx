import React from 'react';
import { useSCStore } from '../store';
import { MessageSquare, Bot, User, GitBranch, Layers, Settings, Microscope, Plug, Cable, ScrollText, Brain, Target } from 'lucide-react';
import { resolveEriTheme } from '../App';

const NAV_ITEMS = [
  { id: 'chat',        Icon: MessageSquare, label: 'Chat' },
  { id: 'canvas',      Icon: Layers,        label: 'Canvas' },
  { id: 'research',    Icon: Microscope,    label: 'Research' },
  { id: 'agents',      Icon: Bot,           label: 'Agents' },
  { id: 'profiles',    Icon: User,          label: 'Profiles' },
  { id: 'workflows',   Icon: GitBranch,     label: 'Workflows' },
  { id: 'mcp',         Icon: Plug,          label: 'MCP' },
  { id: 'connections', Icon: Cable,          label: 'Connect' },
  { id: 'memory',      Icon: Brain,         label: 'Memory' },
  { id: 'goals',       Icon: Target,        label: 'Goals' },
  { id: 'logs',        Icon: ScrollText,    label: 'Logs' },
];

function ERIOrb() {
  const eriState    = useSCStore(s => s.eriState);
  const sensory     = useSCStore(s => s.sensoryState);
  const wsStatus    = useSCStore(s => s.wsStatus);
  const eri         = eriState?.eri ?? 0.5;
  const theme       = resolveEriTheme(eri);
  const pulseRate   = sensory?.pulse_rate ?? 1.0;
  const bpm         = eriState?.bpm ?? 120;
  const coherence   = Math.round((eriState?.coherence ?? 1.0) * 100);
  const isConnected = wsStatus === 'connected';

  // BPM → animation duration (60000ms / bpm = ms per beat)
  const beatMs = Math.round(60000 / Math.max(40, Math.min(180, bpm)));
  const animDur = `${(beatMs / 1000).toFixed(2)}s`;

  const [hover, setHover] = React.useState(false);

  return (
    <div
      style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, marginBottom: 4 }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {/* Orb */}
      <div style={{
        width: 10, height: 10, borderRadius: '50%',
        background: isConnected ? theme.accent : '#44445A',
        animation: isConnected ? `eri-pulse ${animDur} ease-in-out infinite` : 'none',
        transition: 'background 1.2s ease',
        cursor: 'default',
      }} />
      {/* Tiny label */}
      <span style={{
        fontSize: 7, fontFamily: 'var(--font-inter)', color: isConnected ? theme.accent : '#44445A',
        letterSpacing: '0.02em', lineHeight: 1, fontWeight: 600,
        transition: 'color 1.2s ease',
      }}>
        {isConnected ? theme.name.slice(0, 4).toUpperCase() : 'IDLE'}
      </span>

      {/* Hover tooltip */}
      {hover && isConnected && (
        <div style={{
          position: 'absolute', left: 52, bottom: 0, zIndex: 400,
          background: 'var(--color-sc-surface)', border: `1px solid ${theme.accent}40`,
          borderRadius: 10, padding: '10px 14px', width: 180,
          boxShadow: `0 4px 20px ${theme.accent}20`,
          pointerEvents: 'none',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: theme.accent, flexShrink: 0,
                          animation: `eri-pulse ${animDur} ease-in-out infinite` }} />
            <span style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 12, color: theme.accent }}>
              {theme.name}
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 10px' }}>
            {[
              ['ERI',       `${(eri * 100).toFixed(0)}%`],
              ['Coherence', `${coherence}%`],
              ['Key',       eriState?.musicalKey ?? '—'],
              ['BPM',       `${Math.round(bpm)}`],
              ['Pacing',    `${Math.round((eriState?.pacing ?? 1) * 100)}%`],
              ['Tone',      (sensory?.active_tone ?? 'Deep Focus').split(' ')[0]],
            ].map(([k, v]) => (
              <React.Fragment key={k}>
                <span style={{ fontSize: 10, color: 'var(--color-sc-text-dim)' }}>{k}</span>
                <span style={{ fontSize: 10, color: 'var(--color-sc-text-muted)', textAlign: 'right', fontFamily: k === 'Key' || k === 'Tone' ? 'var(--font-inter)' : 'var(--font-mono)' }}>{v}</span>
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function NavRail({ onOpenSettings }) {
  const activePage    = useSCStore(s => s.activePage);
  const setActivePage = useSCStore(s => s.setActivePage);
  const bgRuns        = useSCStore(s => s.bgRuns);

  const activeRunCount = Object.values(bgRuns).filter(r =>
    r.run?.status === 'running' || r.run?.status === 'queued' || !r.run
  ).length;

  return (
    <nav style={{
      width: 60, flexShrink: 0,
      background: 'var(--color-sc-surface)',
      borderRight: '1px solid var(--color-sc-border)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '12px 0', gap: 2,
    }}>
      {/* Logo */}
      <div style={{ marginBottom: 16, padding: '4px 0' }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M12 2 L14 8 L20 6 L16 11 L20 14 L14 13 L12 20 L10 13 L4 14 L8 11 L4 6 L10 8 Z" fill="#C4A44A" opacity="0.9" />
          <circle cx="12" cy="11" r="2" fill="#080810" />
        </svg>
      </div>

      {/* Nav items */}
      {NAV_ITEMS.map(({ id, Icon, label }) => {
        const active = activePage === id;
        const showBadge = id === 'workflows' && activeRunCount > 0;
        return (
          <button
            key={id}
            onClick={() => setActivePage(id)}
            title={label}
            style={{
              width: 44, height: 44, borderRadius: 10, border: 'none', cursor: 'pointer',
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3,
              background: active ? 'rgba(196,164,74,0.15)' : 'transparent',
              color: active ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
              transition: 'background 0.15s, color 0.15s',
              position: 'relative',
            }}
            onMouseEnter={e => { if (!active) { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = 'var(--color-sc-text)'; } }}
            onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-sc-text-muted)'; } }}
          >
            {active && (
              <span style={{
                position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)',
                width: 3, height: 20, background: 'var(--color-sc-gold)', borderRadius: '0 3px 3px 0',
              }} />
            )}
            <Icon size={17} strokeWidth={active ? 2 : 1.7} />
            <span style={{ fontSize: 9, fontFamily: 'var(--font-inter)', fontWeight: active ? 600 : 400, letterSpacing: '0.02em' }}>
              {label}
            </span>
            {/* Running badge — visible from any page */}
            {showBadge && (
              <span style={{
                position: 'absolute', top: 4, right: 4,
                width: 8, height: 8, borderRadius: '50%',
                background: 'var(--color-sc-gold)',
                boxShadow: '0 0 6px rgba(196,164,74,0.7)',
                animation: 'pulse 1.5s ease-in-out infinite',
              }} />
            )}
          </button>
        );
      })}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* ERI Status Orb */}
      <ERIOrb />

      {/* Settings */}
      <button
        onClick={onOpenSettings}
        title="Settings"
        style={{
          width: 44, height: 44, borderRadius: 10, border: 'none', cursor: 'pointer',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3,
          background: 'transparent', color: 'var(--color-sc-text-muted)', transition: 'background 0.15s, color 0.15s',
        }}
        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = 'var(--color-sc-text)'; }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-sc-text-muted)'; }}
      >
        <Settings size={17} strokeWidth={1.7} />
        <span style={{ fontSize: 9, fontFamily: 'var(--font-inter)' }}>Settings</span>
      </button>
    </nav>
  );
}
