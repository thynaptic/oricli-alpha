import { useEffect, useState } from 'react';
import { useSCStore, fetchHealth, fetchModels, fetchModules, connectHiveWS } from './store';
import { NavRail } from './components/NavRail';
import { ChatSidebar } from './components/ChatSidebar';
import { ChatArea } from './components/ChatArea';
import { AgentsPage } from './pages/AgentsPage';
import { ProfilesPage } from './pages/ProfilesPage';
import { WorkflowsPage } from './pages/WorkflowsPage';
import { ArtifactsCanvas } from './pages/ArtifactsCanvas';
import { ResearchPage } from './pages/ResearchPage';
import { MCPPage } from './pages/MCPPage';
import { ConnectionsPage } from './pages/ConnectionsPage';
import { LogsPage } from './pages/LogsPage';
import { MemoryBrowser } from './pages/MemoryBrowser';
import { SettingsPanel } from './components/SettingsPanel';

// ── ERI state → accent color mapping (mirrors Go sensory.go KosmicColor palette) ──
export const ERI_STATES = [
  { min: 0.7,        name: 'Symphonic',  accent: '#994CFF', glow: '#C490FF', label: 'E Major ✦' },
  { min: 0.45,       name: 'Stable',     accent: '#C4A44A', glow: '#FFD166', label: 'C Major ◈' },
  { min: 0.25,       name: 'Dissonant',  accent: '#00CCCC', glow: '#66FFFF', label: 'G Minor ◇' },
  { min: 0.0,        name: 'Discordant', accent: '#FF9900', glow: '#FFBB44', label: 'D Minor △' },
  { min: -Infinity,  name: 'Cacophonic', accent: '#FF4D6D', glow: '#FF8898', label: 'B Locrian ⚠' },
];

export function resolveEriTheme(eri) {
  return ERI_STATES.find(s => eri >= s.min) ?? ERI_STATES[ERI_STATES.length - 1];
}

export default function App() {
  const setHealth  = useSCStore(s => s.setHealth);
  const setModels  = useSCStore(s => s.setModels);
  const setModules = useSCStore(s => s.setModules);
  const activePage = useSCStore(s => s.activePage);
  const eriState   = useSCStore(s => s.eriState);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Apply ERI accent to CSS custom properties whenever ERI changes
  useEffect(() => {
    const theme = resolveEriTheme(eriState.eri ?? 0.5);
    const root = document.documentElement;
    root.style.setProperty('--color-sc-gold', theme.accent);
    root.style.setProperty('--color-sc-gold-glow', theme.glow);
  }, [eriState]);

  useEffect(() => {
    fetchHealth().then(h => setHealth(h));
    fetchModels().then(ms => setModels(ms));
    fetchModules().then(ms => setModules(ms));
    const poll = setInterval(() => fetchHealth().then(h => setHealth(h)), 30_000);
    connectHiveWS();
    return () => clearInterval(poll);
  }, []);

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

      {activePage === 'research'  && <ResearchPage />}
      {activePage === 'agents'    && <AgentsPage />}
      {activePage === 'profiles'  && <ProfilesPage />}
      {activePage === 'workflows' && <WorkflowsPage />}
      {activePage === 'mcp'         && <MCPPage />}
      {activePage === 'connections'  && <ConnectionsPage />}
      {activePage === 'logs'         && <LogsPage />}
      {activePage === 'memory'       && <MemoryBrowser />}

      {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}
