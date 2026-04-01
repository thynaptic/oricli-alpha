import { useEffect, useState, useCallback } from 'react';
import { useSCStore, fetchHealth, fetchModels, fetchModules, connectHiveWS } from './store';
import { NavRail } from './components/NavRail';
import { ChatSidebar } from './components/ChatSidebar';
import { ChatArea } from './components/ChatArea';
import { AgentsPage } from './pages/AgentsPage';
import { ProfilesPage } from './pages/ProfilesPage';
import { WorkflowsPage } from './pages/WorkflowsPage';
import PipelineCanvas from './pages/PipelineCanvas';
import { ArtifactsCanvas } from './pages/ArtifactsCanvas';
import { ResearchPage } from './pages/ResearchPage';
import { MCPPage } from './pages/MCPPage';
import { ConnectionsPage } from './pages/ConnectionsPage';
import { LogsPage } from './pages/LogsPage';
import { MemoryBrowser } from './pages/MemoryBrowser';
import { GoalsPage } from './pages/GoalsPage';
import OriStudioPage from './pages/OriStudioPage';
import { SettingsPanel } from './components/SettingsPanel';
import { useERI } from './hooks/useERI';
import { LandingPage } from './pages/LandingPage';

// ── ERI state → accent color mapping ──
// ERI -1.0…1.0: swarm coherence composite from Go ResonanceService
export const ERI_STATES = [
  { min: 0.7,       name: 'Symphonic',  accent: '#FF1A5E', glow: '#FF4D80', label: 'E Major ✦' },
  { min: 0.3,       name: 'Stable',     accent: '#E5004C', glow: '#FF0055', label: 'C Major ◈' },
  { min: -0.3,      name: 'Dissonant',  accent: '#B8003D', glow: '#D4004A', label: 'G Minor ◇' },
  { min: -Infinity, name: 'Cacophonic', accent: '#7A0028', glow: '#9E0035', label: 'B Locrian ⚠' },
];

export function resolveEriTheme(eri) {
  return ERI_STATES.find(s => eri >= s.min) ?? ERI_STATES[ERI_STATES.length - 1];
}

// ── Boot splash ───────────────────────────────────────────────────────────────
// Cinematic system-boot sequence: logo reveal → wordmark → boot lines → scan
function BootSplash() {
  const [phase, setPhase] = useState(0);
  // phase 0: logo reveals
  // phase 1 (380ms): wordmark + subtitle
  // phase 2 (780ms): line 1
  // phase 3 (1020ms): line 2
  // phase 4 (1260ms): line 3
  // phase 5 (1500ms): SOVEREIGNTY ENGAGED (hero line)
  // phase 6 (2100ms): scan + complete state
  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 380),
      setTimeout(() => setPhase(2), 780),
      setTimeout(() => setPhase(3), 1020),
      setTimeout(() => setPhase(4), 1260),
      setTimeout(() => setPhase(5), 1500),
      setTimeout(() => setPhase(6), 2100),
    ];
    return () => timers.forEach(clearTimeout);
  }, []);

  const bootLines = [
    { text: 'RING-0 KERNEL MERGE',  status: 'OK'     },
    { text: 'HIVE SWARM INTERFACE', status: 'OK'     },
    { text: 'MEMORY BRIDGE',        status: 'ACTIVE' },
    { text: 'SOVEREIGNTY ENGAGED',  status: '—',  hero: true },
  ];

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: '#040208',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      overflow: 'hidden',
    }}>
      <style>{`
        @keyframes oriBgPulse {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes oriLogoReveal {
          0%   { opacity: 0; transform: scale(0.72); filter: blur(18px); }
          60%  { opacity: 1; filter: blur(0px); }
          100% { opacity: 1; transform: scale(1); filter: blur(0px); }
        }
        @keyframes oriLogoGlow {
          0%, 100% { filter: drop-shadow(0 0 16px rgba(229,0,76,0.50)); }
          50%       { filter: drop-shadow(0 0 36px rgba(229,0,76,0.85)); }
        }
        @keyframes oriWordIn {
          0%   { opacity: 0; letter-spacing: 0.7em; filter: blur(8px); }
          100% { opacity: 1; letter-spacing: 0.22em; filter: blur(0); }
        }
        @keyframes oriFadeSlideIn {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes oriLineIn {
          from { opacity: 0; transform: translateX(-10px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        @keyframes oriHeroIn {
          0%   { opacity: 0; transform: translateX(-10px); }
          30%  { opacity: 1; }
          100% { opacity: 1; transform: translateX(0); }
        }
        @keyframes oriScanExpand {
          from { transform: scaleX(0); }
          to   { transform: scaleX(1); }
        }
        @keyframes oriCursor {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0; }
        }
        @keyframes oriStampIn {
          from { opacity: 0; }
          to   { opacity: 0.28; }
        }
        @keyframes oriVignetteIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
      `}</style>

      {/* Radial red warmth — center glow */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 55% 45% at 50% 48%, rgba(200,0,48,0.11) 0%, rgba(120,0,28,0.04) 55%, transparent 75%)',
        animation: 'oriBgPulse 1.2s ease forwards',
      }} />

      {/* Vignette */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        boxShadow: 'inset 0 0 120px rgba(0,0,0,0.75)',
        animation: 'oriVignetteIn 0.6s ease forwards',
      }} />

      {/* Horizontal scan line — top edge, appears at phase 6 */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 1,
        background: 'linear-gradient(to right, transparent 0%, rgba(229,0,76,0.6) 30%, rgba(229,0,76,0.8) 50%, rgba(229,0,76,0.6) 70%, transparent 100%)',
        transformOrigin: 'center',
        transform: phase >= 6 ? 'scaleX(1)' : 'scaleX(0)',
        transition: 'transform 0.7s ease',
      }} />

      {/* ── Main content column ── */}
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        width: 340, position: 'relative',
      }}>

        {/* Logo */}
        <div style={{
          animation: 'oriLogoReveal 0.65s cubic-bezier(0.16, 1, 0.3, 1) 0.05s both',
          marginBottom: 22,
        }}>
          <img
            src="/ori-mark-red.png"
            alt="ORI"
            style={{
              width: 92, height: 92, objectFit: 'contain', display: 'block',
              animation: 'oriLogoGlow 3.2s ease-in-out 0.7s infinite',
            }}
          />
        </div>

        {/* Wordmark */}
        <div style={{
          fontFamily: "'SF Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace",
          fontSize: 27, fontWeight: 700, color: '#FFFFFF',
          letterSpacing: '0.22em', lineHeight: 1,
          opacity: 0,
          animation: phase >= 1 ? 'oriWordIn 0.65s cubic-bezier(0.16, 1, 0.3, 1) forwards' : 'none',
          marginBottom: 7,
        }}>ORI STUDIO</div>

        {/* Subtitle */}
        <div style={{
          fontFamily: "'SF Mono', 'Fira Code', monospace",
          fontSize: 9.5, color: 'rgba(229,0,76,0.65)', letterSpacing: '0.26em',
          fontWeight: 500,
          opacity: 0,
          animation: phase >= 1 ? 'oriFadeSlideIn 0.5s ease 0.12s forwards' : 'none',
          marginBottom: 30,
        }}>SOVEREIGN INTELLIGENCE OS</div>

        {/* Hairline divider */}
        <div style={{
          width: 60, height: 1, marginBottom: 22,
          background: 'linear-gradient(to right, transparent, rgba(229,0,76,0.45), transparent)',
          opacity: 0,
          animation: phase >= 1 ? 'oriFadeSlideIn 0.5s ease 0.18s forwards' : 'none',
        }} />

        {/* Boot sequence lines */}
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 9 }}>
          {bootLines.map((line, i) => {
            const visible = phase >= i + 2;
            if (!visible) return null;
            return (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                fontFamily: "'SF Mono', 'Fira Code', monospace",
                fontSize: line.hero ? 12.5 : 11,
                fontWeight: line.hero ? 700 : 400,
                letterSpacing: line.hero ? '0.14em' : '0.06em',
                color: line.hero ? '#E5004C' : 'rgba(255,255,255,0.48)',
                borderTop: line.hero ? '1px solid rgba(229,0,76,0.18)' : 'none',
                paddingTop: line.hero ? 11 : 0,
                marginTop: line.hero ? 5 : 0,
                animation: line.hero
                  ? 'oriHeroIn 0.5s ease forwards'
                  : 'oriLineIn 0.32s ease forwards',
              }}>
                <span>{line.text}</span>
                <span style={{
                  color: line.hero ? '#E5004C' : 'rgba(229,0,76,0.75)',
                  marginLeft: 20, flexShrink: 0,
                  textShadow: line.hero ? '0 0 12px rgba(229,0,76,0.6)' : 'none',
                }}>{line.status}</span>
              </div>
            );
          })}
        </div>

        {/* Blinking cursor — active while lines are appearing */}
        {phase >= 2 && phase < 6 && (
          <div style={{
            alignSelf: 'flex-start', marginTop: 10,
            width: 7, height: 13,
            background: 'rgba(229,0,76,0.8)',
            animation: 'oriCursor 0.75s step-end infinite',
            borderRadius: 1,
          }} />
        )}
      </div>

      {/* Bottom scan bar */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: 1,
        background: 'rgba(229,0,76,0.12)',
      }}>
        <div style={{
          height: '100%',
          background: 'linear-gradient(to right, transparent, #E5004C 20%, #E5004C 80%, transparent)',
          transformOrigin: 'left center',
          transform: phase >= 6 ? 'scaleX(1)' : 'scaleX(0)',
          transition: 'transform 0.9s ease',
        }} />
      </div>

      {/* Corner stamps */}
      <div style={{
        position: 'absolute', bottom: 18, left: 22,
        fontFamily: "'SF Mono', monospace", fontSize: 9,
        color: '#FFFFFF', letterSpacing: '0.1em',
        opacity: 0,
        animation: phase >= 1 ? 'oriStampIn 0.8s ease 0.3s forwards' : 'none',
      }}>THYNAPTIC · RING-0</div>
      <div style={{
        position: 'absolute', bottom: 18, right: 22,
        fontFamily: "'SF Mono', monospace", fontSize: 9,
        color: '#FFFFFF', letterSpacing: '0.1em',
        opacity: 0,
        animation: phase >= 1 ? 'oriStampIn 0.8s ease 0.3s forwards' : 'none',
      }}>v2.1.0</div>

    </div>
  );
}

export default function App() {
  const setHealth  = useSCStore(s => s.setHealth);
  const setModels  = useSCStore(s => s.setModels);
  const setModules = useSCStore(s => s.setModules);
  const activePage = useSCStore(s => s.activePage);
  const eriState   = useSCStore(s => s.eriState);
  const theme      = useSCStore(s => s.theme);
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Phase machine: 'landing' → 'booting' → 'app'
  const [phase, setPhase] = useState('landing');

  // Apply theme: set CSS vars directly on documentElement.style (inline = highest priority)
  // Beats @layer theme in Tailwind v4 compiled CSS and all component inline styles
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme ?? 'dark');
    if (theme === 'light') {
      const vars = {
        '--color-sc-bg':         '#F5F0EC',
        '--color-sc-surface':    '#EDE8E3',
        '--color-sc-surface2':   '#E5DFD9',
        '--color-sc-border':     '#D4CDC5',
        '--color-sc-border2':    '#C5BDB4',
        '--color-sc-gold':       '#C4001E',
        '--color-sc-gold-glow':  '#E5003A',
        '--color-sc-text':       '#1A1214',
        '--color-sc-text-muted': '#6B5F68',
        '--color-sc-text-dim':   '#9E9099',
        '--color-sc-success':    '#059669',
        '--color-sc-danger':     '#DC2626',
        '--color-sc-blue':       '#1D4ED8',
      };
      Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
    } else {
      const DARK_VARS = {
        '--color-sc-bg':         '#080810',
        '--color-sc-surface':    '#0E0810',
        '--color-sc-surface2':   '#150A14',
        '--color-sc-border':     '#1E0A18',
        '--color-sc-border2':    '#2A0F22',
        '--color-sc-gold':       '#E5004C',
        '--color-sc-gold-glow':  '#FF0055',
        '--color-sc-text':       '#F0ECE8',
        '--color-sc-text-muted': '#9A8890',
        '--color-sc-text-dim':   '#4D2F42',
        '--color-sc-success':    '#06D6A0',
        '--color-sc-danger':     '#FF4D6D',
        '--color-sc-blue':       '#4D9EFF',
      };
      Object.entries(DARK_VARS).forEach(([k, v]) => root.style.setProperty(k, v));
    }
    // Remove no-transition guard now that theme is applied — re-enable smooth transitions
    requestAnimationFrame(() => root.classList.remove('sc-no-transition'));
  }, [theme]);

  // ERI → live CSS color shifts (poll + SSE live value)
  useERI(eriState?.eri ?? null);

  // handleLaunch: fires on CTA click — starts boot sequence + kicks off API fetches
  const handleLaunch = useCallback(() => {
    setPhase('booting');
    fetchHealth().then(h => setHealth(h));
    fetchModels().then(ms => setModels(ms));
    fetchModules().then(ms => setModules(ms));
    connectHiveWS();
    setTimeout(() => setPhase('app'), 3400);
  }, [setHealth, setModels, setModules]);

  // Health poll — only active once inside the app
  useEffect(() => {
    if (phase !== 'app') return;
    const poll = setInterval(() => fetchHealth().then(h => setHealth(h)), 30_000);
    return () => clearInterval(poll);
  }, [phase, setHealth]);

  if (phase === 'landing') return <LandingPage onLaunch={handleLaunch} />;
  if (phase === 'booting') return <BootSplash />;

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
      <NavRail onOpenSettings={() => setSettingsOpen(true)} />

      {activePage === 'chat' && (
        <>
          <ChatSidebar />
          <ChatArea />
        </>
      )}

      {/* Canvas stays mounted so in-flight LLM streams survive tab switches */}
      <div style={{ display: activePage === 'canvas' ? 'flex' : 'none', flex: 1, overflow: 'hidden' }}>
        <ArtifactsCanvas />
      </div>

      {/* Pipeline canvas stays mounted so runs survive tab switches */}
      <div style={{ display: activePage === 'pipelines' ? 'flex' : 'none', flex: 1, overflow: 'hidden' }}>
        <PipelineCanvas />
      </div>

      {activePage === 'research'  && <ResearchPage />}
      {activePage === 'agents'    && <AgentsPage />}
      {activePage === 'profiles'  && <ProfilesPage />}
      {activePage === 'workflows' && <WorkflowsPage />}
      {activePage === 'mcp'         && <MCPPage />}
      {activePage === 'connections'  && <ConnectionsPage />}
      {activePage === 'logs'         && <LogsPage />}
      {activePage === 'memory'       && <MemoryBrowser />}
      {activePage === 'goals'        && <GoalsPage />}
      {activePage === 'ori-studio'   && <OriStudioPage />}

      {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}
