import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useSCStore } from '../store';
import { Home, Zap, BookOpen, Pin, Plug, Settings, Sun, Moon, LogOut } from 'lucide-react';
import { resolveEriTheme, IS_DEMO } from '../App';

const NAV_ITEMS = [
  { id: 'home',        Icon: Home,     label: 'Home'        },
  { id: 'automations', Icon: Zap,      label: 'Automations' },
  { id: 'notebook',    Icon: BookOpen, label: 'Notebook'    },
  { id: 'board',       Icon: Pin,      label: 'Board'       },
  { id: 'connections', Icon: Plug,     label: 'Connections' },
];

function ERIOrb() {
  const eriState  = useSCStore(s => s.eriState);
  const wsStatus  = useSCStore(s => s.wsStatus);
  const eri       = eriState?.eri ?? 0.5;
  const theme     = resolveEriTheme(eri);
  const bpm       = eriState?.bpm ?? 120;
  const beatMs    = Math.round(60000 / Math.max(40, Math.min(180, bpm)));
  const animDur   = `${(beatMs / 1000).toFixed(2)}s`;
  const isConnected = wsStatus === 'connected';
  const [hover, setHover] = React.useState(false);

  return (
    <div
      style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, marginBottom: 4 }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <div style={{
        width: 8, height: 8, borderRadius: '50%',
        background: isConnected ? theme.accent : '#44445A',
        animation: isConnected ? `eri-pulse ${animDur} ease-in-out infinite` : 'none',
        transition: 'background 1.2s ease',
      }} />
      {hover && isConnected && (
        <div style={{
          position: 'absolute', left: 52, bottom: 0, zIndex: 400,
          background: 'var(--color-sc-surface)', border: `1px solid ${theme.accent}40`,
          borderRadius: 10, padding: '10px 14px', width: 160,
          boxShadow: `0 4px 20px ${theme.accent}20`, pointerEvents: 'none',
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: theme.accent, marginBottom: 6 }}>{theme.name}</div>
          <div style={{ fontSize: 10, color: 'var(--color-sc-text-dim)' }}>
            ERI {Math.round(eri * 100)}% · {Math.round(bpm)} BPM
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
  const theme         = useSCStore(s => s.theme);
  const toggleTheme   = useSCStore(s => s.toggleTheme);
  const logout        = useSCStore(s => s.logout);
  const user          = useSCStore(s => s.user);
  const navigate      = useNavigate();
  const location      = useLocation();

  const currentPage = location.pathname.replace(/^\//, '') || activePage;

  const activeRunCount = Object.values(bgRuns).filter(r =>
    r.run?.status === 'running' || r.run?.status === 'queued' || !r.run
  ).length;

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <nav style={{
      width: 60, flexShrink: 0,
      background: 'var(--color-sc-surface)',
      borderRight: '1px solid var(--color-sc-border)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '12px 0', gap: 2,
    }}>
      {/* Logo */}
      <div
        onClick={() => { navigate('/home'); setActivePage('home'); }}
        title="Home"
        style={{ marginBottom: 16, padding: '4px 0', cursor: 'pointer', opacity: 0.9, transition: 'opacity 0.15s' }}
        onMouseEnter={e => e.currentTarget.style.opacity = '1'}
        onMouseLeave={e => e.currentTarget.style.opacity = '0.9'}
      >
        <img src="/ori-mark.png" alt="ORI" className="logo-light-src"
          style={{ width: 32, height: 32, objectFit: 'contain', display: 'block' }} />
      </div>

      {/* Nav items */}
      {NAV_ITEMS.map(({ id, Icon, label }) => {
        const active = currentPage === id;
        const showBadge = id === 'automations' && activeRunCount > 0;
        return (
          <button
            key={id}
            onClick={() => { navigate(`/${id}`); setActivePage(id); }}
            title={label}
            style={{
              width: 44, height: 44, borderRadius: 10, border: 'none', cursor: 'pointer',
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3,
              background: active ? 'color-mix(in srgb, var(--color-sc-gold) 15%, transparent)' : 'transparent',
              color: active ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
              transition: 'background 0.15s, color 0.15s', position: 'relative',
            }}
            onMouseEnter={e => { if (!active) { e.currentTarget.style.background = 'rgba(128,128,128,0.1)'; e.currentTarget.style.color = 'var(--color-sc-text)'; }}}
            onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-sc-text-muted)'; }}}
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
            {showBadge && (
              <span style={{
                position: 'absolute', top: 4, right: 4, width: 8, height: 8, borderRadius: '50%',
                background: 'var(--color-sc-gold)',
                boxShadow: '0 0 6px color-mix(in srgb, var(--color-sc-gold) 70%, transparent)',
                animation: 'pulse 1.5s ease-in-out infinite',
              }} />
            )}
          </button>
        );
      })}

      <div style={{ flex: 1 }} />

      <ERIOrb />

      {/* Theme toggle */}
      <NavBtn onClick={toggleTheme} title={theme === 'dark' ? 'Light mode' : 'Dark mode'} label={theme === 'dark' ? 'Light' : 'Dark'}>
        {theme === 'dark' ? <Sun size={15} strokeWidth={1.7} /> : <Moon size={15} strokeWidth={1.7} />}
      </NavBtn>

      {/* Settings */}
      <NavBtn onClick={() => navigate('/settings')} title="Settings" label="Settings">
        <Settings size={17} strokeWidth={1.7} />
      </NavBtn>

      {/* Avatar + logout */}
      {user && (
        <NavBtn onClick={handleLogout} title={`Sign out (${user.name})`} label="Sign out">
          <LogOut size={15} strokeWidth={1.7} />
        </NavBtn>
      )}
    </nav>
  );
}

function NavBtn({ onClick, title, label, children }) {
  return (
    <button onClick={onClick} title={title} style={{
      width: 44, height: 44, borderRadius: 10, border: 'none', cursor: 'pointer',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3,
      background: 'transparent', color: 'var(--color-sc-text-muted)', transition: 'background 0.15s, color 0.15s',
    }}
      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(128,128,128,0.1)'; e.currentTarget.style.color = 'var(--color-sc-text)'; }}
      onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-sc-text-muted)'; }}
    >
      {children}
      <span style={{ fontSize: 9, fontFamily: 'var(--font-inter)' }}>{label}</span>
    </button>
  );
}
