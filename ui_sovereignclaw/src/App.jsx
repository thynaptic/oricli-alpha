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
import { GoalsPage } from './pages/GoalsPage';
import OriStudioPage from './pages/OriStudioPage';
import { SettingsPanel } from './components/SettingsPanel';
import { useERI } from './hooks/useERI';

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

export default function App() {
  const setHealth  = useSCStore(s => s.setHealth);
  const setModels  = useSCStore(s => s.setModels);
  const setModules = useSCStore(s => s.setModules);
  const activePage = useSCStore(s => s.activePage);
  const eriState   = useSCStore(s => s.eriState);
  const theme      = useSCStore(s => s.theme);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Apply theme attribute to root element — all CSS vars cascade from here
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme ?? 'dark');
  }, [theme]);

  // ERI → live CSS color shifts (poll + SSE live value)
  useERI(eriState?.eri ?? null);

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
      {activePage === 'goals'        && <GoalsPage />}
      {activePage === 'ori-studio'   && <OriStudioPage />}

      {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
    </div>
  );
}
