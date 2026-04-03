import { useEffect, useState, useRef } from 'react';
import { Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom';
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
import { DemoPreviewPage } from './pages/DemoPreviewPage';
import { LandingPage } from './pages/LandingPage';
import FAQPage, { AskOricliWidget, FAQ_SECTIONS } from './pages/FAQPage';
import { NotionBuilderPage } from './pages/NotionBuilderPage';
import { LoginPage } from './pages/LoginPage';
import { HomePage } from './pages/HomePage';
import { NotebookPage } from './pages/NotebookPage';
import { BoardPage } from './pages/BoardPage';
import { AutomationsPage } from './pages/AutomationsPage';
import { SettingsPage } from './pages/SettingsPage';

// ── AuthGuard — redirects to /login if no token ───────────────────────────────
function AuthGuard({ children }) {
  const token = useSCStore(s => s.token);
  const refreshUser = useSCStore(s => s.refreshUser);

  useEffect(() => { if (token) refreshUser(); }, []); // eslint-disable-line

  if (!token) return <Navigate to="/login" replace />;
  return children;
}

// ── Demo mode banner (shown on demo.thynaptic.com) ───────────────────────────
export const IS_DEMO = window.location.hostname === 'demo.thynaptic.com';

function DemoFAQButton() {
  const [open, setOpen] = useState(false);
  if (!IS_DEMO) return null;
  return (
    <>
      {/* Floating ? button */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 8000,
          width: 44, height: 44, borderRadius: '50%',
          background: open ? '#8875FF' : 'rgba(136,117,255,0.15)',
          border: '1px solid rgba(136,117,255,0.35)',
          color: open ? '#FFF' : '#8875FF',
          fontSize: 18, fontWeight: 700, cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'background 0.2s, color 0.2s',
          boxShadow: open ? '0 0 20px rgba(136,117,255,0.35)' : 'none',
        }}
        title="Help & FAQ"
      >?</button>

      {/* Slide-out panel */}
      {open && (
        <div style={{
          position: 'fixed', bottom: 80, right: 24, zIndex: 7999,
          width: 360, height: 520,
          background: '#13131A',
          border: '1px solid rgba(136,117,255,0.22)',
          borderRadius: 16, overflow: 'hidden',
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
          animation: 'faqPanelIn 0.2s ease forwards',
        }}>
          <style>{`
            @keyframes faqPanelIn { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
            @keyframes faqDot { 0%,80%,100% { transform:scale(0.6); opacity:0.4; } 40% { transform:scale(1); opacity:1; } }
          `}</style>

          {/* Header */}
          <div style={{
            padding: '14px 16px', borderBottom: '1px solid rgba(136,117,255,0.12)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div>
              <div style={{ fontFamily: 'system-ui,-apple-system,sans-serif', fontSize: 14, fontWeight: 700, color: '#F0ECF0' }}>Ask Oricli</div>
              <div style={{ fontFamily: "'SF Mono','Fira Code',monospace", fontSize: 8.5, color: 'rgba(136,117,255,0.6)', letterSpacing: '0.12em' }}>POWERED BY ORI STUDIO</div>
            </div>
            <button onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(240,236,240,0.35)', fontSize: 16 }}>✕</button>
          </div>

          {/* Quick FAQ links */}
          <div style={{ padding: '10px 14px', borderBottom: '1px solid rgba(136,117,255,0.08)', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {FAQ_SECTIONS.flatMap(s => s.items).slice(0, 4).map((item, i) => (
              <div key={i} style={{
                fontFamily: 'system-ui,-apple-system,sans-serif',
                fontSize: 11, color: 'rgba(136,117,255,0.8)',
                background: 'rgba(136,117,255,0.08)',
                border: '1px solid rgba(136,117,255,0.15)',
                borderRadius: 20, padding: '4px 10px', cursor: 'default',
                lineHeight: 1.3,
              }}>{item.q.split('?')[0].slice(0, 30)}…</div>
            ))}
          </div>

          {/* Chat widget */}
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <AskOricliWidget compact />
          </div>
        </div>
      )}
    </>
  );
}

function DemoBanner() {
  if (!IS_DEMO) return null;
  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 9999,
      height: 28,
      background: 'rgba(136,117,255,0.12)',
      borderBottom: '1px solid rgba(136,117,255,0.25)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
      backdropFilter: 'blur(8px)',
    }}>
      <span style={{
        fontFamily: "'SF Mono','Fira Code',monospace",
        fontSize: 9.5, letterSpacing: '0.18em', fontWeight: 600,
        color: 'rgba(169,155,255,0.85)',
      }}>✦ DEMO ENVIRONMENT — DATA RESETS HOURLY · NOT FOR PRODUCTION USE ✦</span>
    </div>
  );
}

// ── ERI state → accent color mapping ──
// ERI -1.0…1.0: swarm coherence composite from Go ResonanceService
export const ERI_STATES = [
  { min: 0.7,       name: 'Symphonic',  accent: '#A99BFF', glow: '#C4B9FF', label: 'E Major ✦' },
  { min: 0.3,       name: 'Stable',     accent: '#8875FF', glow: '#A99BFF', label: 'C Major ◈' },
  { min: -0.3,      name: 'Dissonant',  accent: '#6B5FE0', glow: '#8875FF', label: 'G Minor ◇' },
  { min: -Infinity, name: 'Cacophonic', accent: '#4F45B8', glow: '#6B5FE0', label: 'B Locrian ⚠' },
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
          0%, 100% { filter: drop-shadow(0 0 16px rgba(136,117,255,0.50)); }
          50%       { filter: drop-shadow(0 0 36px rgba(136,117,255,0.85)); }
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
        background: 'radial-gradient(ellipse 55% 45% at 50% 48%, rgba(67,56,202,0.11) 0%, rgba(49,46,129,0.04) 55%, transparent 75%)',
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
        background: 'linear-gradient(to right, transparent 0%, rgba(136,117,255,0.6) 30%, rgba(136,117,255,0.8) 50%, rgba(136,117,255,0.6) 70%, transparent 100%)',
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
            src="/ori-mark.png"
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
          fontSize: 9.5, color: 'rgba(136,117,255,0.65)', letterSpacing: '0.26em',
          fontWeight: 500,
          opacity: 0,
          animation: phase >= 1 ? 'oriFadeSlideIn 0.5s ease 0.12s forwards' : 'none',
          marginBottom: 30,
        }}>SOVEREIGN INTELLIGENCE OS</div>

        {/* Hairline divider */}
        <div style={{
          width: 60, height: 1, marginBottom: 22,
          background: 'linear-gradient(to right, transparent, rgba(136,117,255,0.45), transparent)',
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
                color: line.hero ? '#8875FF' : 'rgba(255,255,255,0.48)',
                borderTop: line.hero ? '1px solid rgba(136,117,255,0.18)' : 'none',
                paddingTop: line.hero ? 11 : 0,
                marginTop: line.hero ? 5 : 0,
                animation: line.hero
                  ? 'oriHeroIn 0.5s ease forwards'
                  : 'oriLineIn 0.32s ease forwards',
              }}>
                <span>{line.text}</span>
                <span style={{
                  color: line.hero ? '#8875FF' : 'rgba(136,117,255,0.75)',
                  marginLeft: 20, flexShrink: 0,
                  textShadow: line.hero ? '0 0 12px rgba(136,117,255,0.6)' : 'none',
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
            background: 'rgba(136,117,255,0.8)',
            animation: 'oriCursor 0.75s step-end infinite',
            borderRadius: 1,
          }} />
        )}
      </div>

      {/* Bottom scan bar */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: 1,
        background: 'rgba(136,117,255,0.08)',
      }}>
        <div style={{
          height: '100%',
          background: 'linear-gradient(to right, transparent, #8875FF 20%, #8875FF 80%, transparent)',
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

// ── App shell — rendered for all /:page routes ────────────────────────────────
function AppShell() {
  const { page } = useParams();
  const navigate = useNavigate();

  const setHealth      = useSCStore(s => s.setHealth);
  const setModels      = useSCStore(s => s.setModels);
  const setModules     = useSCStore(s => s.setModules);
  const activePage     = useSCStore(s => s.activePage);
  const setActivePage  = useSCStore(s => s.setActivePage);
  const eriState       = useSCStore(s => s.eriState);
  const theme          = useSCStore(s => s.theme);
  const hasLaunched    = useSCStore(s => s.hasLaunched);
  const setHasLaunched = useSCStore(s => s.setHasLaunched);
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Skip boot splash on demo OR if hasLaunched is in localStorage (sync read avoids Zustand hydration gap)
  const [booting, setBooting] = useState(() => {
    if (IS_DEMO) return false;
    try {
      const stored = localStorage.getItem('sc-store-v1');
      if (stored && JSON.parse(stored).state?.hasLaunched) return false;
    } catch (_) {}
    return !hasLaunched;
  });
  const syncingUrl = useRef(false);

  // URL → Zustand: keep activePage in sync when URL changes
  useEffect(() => {
    if (page && page !== activePage) {
      syncingUrl.current = true;
      setActivePage(page);
      // allow one render cycle before re-enabling Zustand→URL sync
      requestAnimationFrame(() => { syncingUrl.current = false; });
    }
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  // Zustand → URL: programmatic setActivePage (e.g. canvas redirect from service) syncs URL
  useEffect(() => {
    if (!syncingUrl.current && activePage && activePage !== page) {
      navigate(`/${activePage}`, { replace: true });
    }
  }, [activePage]); // eslint-disable-line react-hooks/exhaustive-deps

  // Apply theme CSS vars
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme ?? 'dark');
    if (theme === 'light') {
      const vars = {
        '--color-sc-bg':         '#F7F7FA',
        '--color-sc-surface':    '#FFFFFF',
        '--color-sc-surface2':   '#F0F0F5',
        '--color-sc-border':     '#E2E2EC',
        '--color-sc-border2':    '#D0D0DE',
        '--color-sc-gold':       '#6254D6',
        '--color-sc-gold-glow':  '#7B6EE8',
        '--color-sc-text':       '#111118',
        '--color-sc-text-muted': '#4A4A60',
        '--color-sc-text-dim':   '#8888A0',
        '--color-sc-success':    '#059669',
        '--color-sc-danger':     '#DC2626',
        '--color-sc-blue':       '#2563EB',
      };
      Object.entries(vars).forEach(([k, v]) => root.style.setProperty(k, v));
    } else {
      const DARK_VARS = {
        '--color-sc-bg':         '#0C0C11',
        '--color-sc-surface':    '#13131A',
        '--color-sc-surface2':   '#1A1A23',
        '--color-sc-border':     '#22222E',
        '--color-sc-border2':    '#2C2C3A',
        '--color-sc-gold':       '#8875FF',
        '--color-sc-gold-glow':  '#A99BFF',
        '--color-sc-text':       '#EEEDF2',
        '--color-sc-text-muted': '#8A8898',
        '--color-sc-text-dim':   '#47465A',
        '--color-sc-success':    '#22D3A0',
        '--color-sc-danger':     '#F06060',
        '--color-sc-blue':       '#60AAFF',
      };
      Object.entries(DARK_VARS).forEach(([k, v]) => root.style.setProperty(k, v));
    }
    requestAnimationFrame(() => root.classList.remove('sc-no-transition'));
  }, [theme]);

  // ERI → live CSS accent shifts
  useERI(eriState?.eri ?? null);

  // Bootstrap API on mount
  useEffect(() => {
    fetchHealth().then(h => setHealth(h));
    fetchModels().then(ms => setModels(ms));
    fetchModules().then(ms => setModules(ms));
    connectHiveWS();
    if (!hasLaunched) {
      setTimeout(() => { setBooting(false); setHasLaunched(true); }, 3400);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Health poll
  useEffect(() => {
    const poll = setInterval(() => fetchHealth().then(h => setHealth(h)), 30_000);
    return () => clearInterval(poll);
  }, [setHealth]);

  if (booting) return <BootSplash />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
      <DemoBanner />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', marginTop: IS_DEMO ? 28 : 0 }}>
      <NavRail />

      {IS_DEMO && ['agents', 'workflows', 'memory', 'canvas'].includes(activePage)
        ? <DemoPreviewPage page={activePage} />
        : (<>
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

      {activePage === 'home'        && <HomePage />}
      {activePage === 'notebook'    && <NotebookPage />}
      {activePage === 'board'       && <BoardPage />}
      {activePage === 'automations' && <AutomationsPage />}
      {activePage === 'research'    && <ResearchPage />}
      {activePage === 'agents'      && <AgentsPage />}
      {activePage === 'settings'    && <SettingsPage />}
      {activePage === 'profiles'    && <SettingsPage />}
      {activePage === 'workflows'   && <WorkflowsPage />}
      {activePage === 'mcp'         && <MCPPage />}
      {activePage === 'connections' && <ConnectionsPage />}
      {activePage === 'logs'        && <LogsPage />}
      {activePage === 'memory'      && <MemoryBrowser />}
      {activePage === 'goals'       && <GoalsPage />}
      {activePage === 'ori-studio'  && <OriStudioPage />}
      {activePage === 'notion-builder' && <NotionBuilderPage />}
      </>)
      }

      {/* settings panel removed — Settings is now a full page */}
      </div>
      <DemoFAQButton />
    </div>
  );
}

// ── Root router ───────────────────────────────────────────────────────────────
export default function App() {
  const navigate = useNavigate();
  const hasLaunched = useSCStore(s => s.hasLaunched);

  const handleLaunch = () => {
    fetchHealth();
    fetchModels();
    fetchModules();
    navigate('/chat');
  };

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/faq"   element={<FAQPage />} />
      <Route path="/" element={
        <AuthGuard><LandingPage onLaunch={handleLaunch} /></AuthGuard>
      } />
      <Route path="/:page" element={
        <AuthGuard><AppShell /></AuthGuard>
      } />
      <Route path="*" element={<Navigate to="/home" replace />} />
    </Routes>
  );
}
