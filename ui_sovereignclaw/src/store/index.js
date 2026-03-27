import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const API_BASE = import.meta.env.VITE_API_BASE || '';

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

function newSession(title = 'New Directive') {
  return { id: makeId(), title, messages: [], artifacts: [], createdAt: Date.now() };
}

// Standalone selector — avoids the getter-freezing bug in Zustand's set() spread
export const selectActiveSession = (s) => {
  const id = s.activeSessionId ?? s.sessions[0]?.id;
  return s.sessions.find(x => x.id === id) ?? s.sessions[0];
};

// ── Store ─────────────────────────────────────────────────────────────────────

export const useSCStore = create(
  persist(
    (set, get) => ({
  // ── Sessions ──────────────────────────────────────────────────────────────
  sessions: [newSession('Initial Directive')],
  activeSessionId: null,

  newSession() {
    const s = newSession();
    set(state => ({ sessions: [s, ...state.sessions], activeSessionId: s.id }));
  },

  setActiveSession(id) { set({ activeSessionId: id }); },

  renameSession(id, title) {
    set(state => ({
      sessions: state.sessions.map(s => s.id === id ? { ...s, title } : s),
    }));
  },

  deleteSession(id) {
    set(state => {
      const next = state.sessions.filter(s => s.id !== id);
      return {
        sessions: next.length ? next : [newSession()],
        activeSessionId: next[0]?.id ?? null,
      };
    });
  },

  appendMessage(sessionId, msg) {
    set(state => ({
      sessions: state.sessions.map(s =>
        s.id === sessionId ? { ...s, messages: [...s.messages, msg] } : s
      ),
    }));
  },

  updateLastAgentMessage(sessionId, patch) {
    set(state => ({
      sessions: state.sessions.map(s => {
        if (s.id !== sessionId) return s;
        const msgs = [...s.messages];
        const idx = msgs.findLastIndex(m => m.role === 'assistant');
        if (idx < 0) return s;
        msgs[idx] = { ...msgs[idx], ...patch };
        return { ...s, messages: msgs };
      }),
    }));
  },

  updateMessage(sessionId, msgId, patchOrFn) {
    set(state => ({
      sessions: state.sessions.map(s => {
        if (s.id !== sessionId) return s;
        return {
          ...s,
          messages: s.messages.map(m => {
            if (m.id !== msgId) return m;
            return typeof patchOrFn === 'function' ? patchOrFn(m) : { ...m, ...patchOrFn };
          }),
        };
      }),
    }));
  },

  // Insert a message immediately before the last message in the session.
  // Used by the task plan card to appear above the streaming assistant bubble.
  insertBeforeLastMessage(sessionId, msg) {
    set(state => ({
      sessions: state.sessions.map(s => {
        if (s.id !== sessionId) return s;
        const msgs = [...s.messages];
        if (msgs.length === 0) return { ...s, messages: [msg] };
        msgs.splice(msgs.length - 1, 0, msg);
        return { ...s, messages: msgs };
      }),
    }));
  },

  truncateAfter(sessionId, msgId) {
    set(state => ({
      sessions: state.sessions.map(s => {
        if (s.id !== sessionId) return s;
        const idx = s.messages.findIndex(m => m.id === msgId);
        if (idx < 0) return s;
        return { ...s, messages: s.messages.slice(0, idx + 1) };
      }),
    }));
  },

  addArtifact(sessionId, artifact) {
    set(state => ({
      sessions: state.sessions.map(s =>
        s.id === sessionId ? { ...s, artifacts: [...s.artifacts, artifact] } : s
      ),
    }));
  },

  // ── Goals ─────────────────────────────────────────────────────────────────
  goals: [],

  addGoal(title, description = '') {
    set(state => ({
      goals: [...state.goals, { id: makeId(), title, description, status: 'ACTIVE', createdAt: Date.now() }],
    }));
  },

  updateGoalStatus(id, status) {
    set(state => ({ goals: state.goals.map(g => g.id === id ? { ...g, status } : g) }));
  },

  removeGoal(id) {
    set(state => ({ goals: state.goals.filter(g => g.id !== id) }));
  },

  // ── Modules / Hive ────────────────────────────────────────────────────────
  modules: [],
  hiveActive: new Set(),           // set of active module names
  hiveEdges: [],                   // [{from, to}] currently active edges
  consensusScore: null,
  wsStatus: 'disconnected',        // 'connected' | 'reconnecting' | 'disconnected'

  setModules(modules) { set({ modules }); },
  setHiveActive(names) { set({ hiveActive: new Set(names) }); },
  setHiveEdges(edges) { set({ hiveEdges: edges }); },
  setConsensusScore(score) { set({ consensusScore: score }); },
  setWsStatus(s) { set({ wsStatus: s }); },

  // ── ERI / Resonance (live from backbone WS) ───────────────────────────────
  eriState: {
    eri: 0.5, ers: 0.5,
    pacing: 1.0, volatility: 0.0, coherence: 1.0,
    musicalKey: 'C Major', bpm: 120.0,
  },
  sensoryState: {
    active_tone: 'Deep Focus',
    primary_color: '#3399FF',
    secondary_color: '#994CFF',
    opacity: 0.85,
    pulse_rate: 1.0,
  },
  setEriState(s) { set({ eriState: s }); },
  setSensoryState(s) { set({ sensoryState: s }); },

  // ── Models ────────────────────────────────────────────────────────────────
  models: [],
  activeModel: null,
  setModels(models) { set({ models, activeModel: models[0]?.id ?? null }); },
  setActiveModel(id) { set({ activeModel: id }); },

  // ── Active Skill ──────────────────────────────────────────────────────────
  activeSkill: null,
  setActiveSkill(skill) { set({ activeSkill: skill }); },

  // ── Health ────────────────────────────────────────────────────────────────
  health: null,
  setHealth(h) { set({ health: h }); },

  // ── Streaming ─────────────────────────────────────────────────────────────
  isStreaming: false,
  setIsStreaming(v) { set({ isStreaming: v }); },

  // ── Page navigation ───────────────────────────────────────────────────────
  activePage: 'chat', // 'chat' | 'agents' | 'profiles' | 'workflows' | 'canvas'
  setActivePage(page) { set({ activePage: page }); },

  // ── Theme ─────────────────────────────────────────────────────────────────
  theme: 'dark', // 'dark' | 'light'
  setTheme(t) { set({ theme: t }); },
  toggleTheme() { set(s => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })); },

  // ── Background Workflow Runs (persists across page navigation) ────────────
  // { [runId]: { runId, wfId, startedAt, run: {...}|null, error: str|null, sendToCanvas: bool } }
  bgRuns: {},
  startBgRun(runId, wfId, opts = {}) {
    set(state => ({ bgRuns: { ...state.bgRuns, [runId]: { runId, wfId, startedAt: Date.now(), run: null, error: null, sendToCanvas: !!opts.sendToCanvas, wfName: opts.wfName || '' } } }));
  },
  updateBgRun(runId, run) {
    // Don't let a stale poll overwrite an intent state the user just triggered
    const INTENT = new Set(['cancelling', 'pausing', 'cancelled']);
    set(state => {
      if (!state.bgRuns[runId]) return state;
      const cur = state.bgRuns[runId].run?.status;
      if (INTENT.has(cur) && !INTENT.has(run?.status) && run?.status !== 'done' && run?.status !== 'error') return state;
      return { bgRuns: { ...state.bgRuns, [runId]: { ...state.bgRuns[runId], run } } };
    });
  },
  dismissBgRun(runId) {
    set(state => { const n = { ...state.bgRuns }; delete n[runId]; return { bgRuns: n }; });
  },
  dismissAllDoneBgRuns() {
    set(state => {
      const n = {};
      Object.values(state.bgRuns).forEach(r => { if (r.run?.status !== 'done' && r.run?.status !== 'error') n[r.runId] = r; });
      return { bgRuns: n };
    });
  },

  cancelRun(runId) {
    fetch(`/workflows/runs/${runId}/cancel`, { method: 'POST' }).catch(() => {});
    set(state => state.bgRuns[runId] ? {
      bgRuns: { ...state.bgRuns, [runId]: { ...state.bgRuns[runId], run: { ...state.bgRuns[runId].run, status: 'cancelling' } } },
    } : state);
  },
  pauseRun(runId) {
    fetch(`/workflows/runs/${runId}/pause`, { method: 'POST' }).catch(() => {});
    set(state => state.bgRuns[runId] ? {
      bgRuns: { ...state.bgRuns, [runId]: { ...state.bgRuns[runId], run: { ...state.bgRuns[runId].run, status: 'pausing' } } },
    } : state);
  },
  resumeRun(runId) {
    fetch(`/workflows/runs/${runId}/resume`, { method: 'POST' }).catch(() => {});
    set(state => state.bgRuns[runId] ? {
      bgRuns: { ...state.bgRuns, [runId]: { ...state.bgRuns[runId], run: { ...state.bgRuns[runId].run, status: 'resuming' } } },
    } : state);
  },

  // ── Profiles ──────────────────────────────────────────────────────────────
  projects: [],
  activeProjectId: null,
  fetchProjects() {
    fetch('/projects').then(r => r.json()).then(d => set({ projects: d.projects || [] })).catch(() => {});
  },
  setActiveProject(id) { set({ activeProjectId: id }); },
  async createProject(name, color = '#7c6af7') {
    const r = await fetch('/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, color }) });
    const d = await r.json();
    set(state => ({ projects: [...state.projects, d.project] }));
    return d.project;
  },
  async updateProject(id, patch) {
    const r = await fetch(`/projects/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch) });
    const d = await r.json();
    set(state => ({ projects: state.projects.map(p => p.id === id ? d.project : p) }));
  },
  async deleteProject(id) {
    await fetch(`/projects/${id}`, { method: 'DELETE' });
    set(state => ({ projects: state.projects.filter(p => p.id !== id), activeProjectId: state.activeProjectId === id ? null : state.activeProjectId }));
  },

  profiles: [],
  addProfile(profile) { set(state => ({ profiles: [...state.profiles, { id: makeId(), ...profile, createdAt: Date.now() }] })); },
  updateProfile(id, patch) { set(state => ({ profiles: state.profiles.map(p => p.id === id ? { ...p, ...patch } : p) })); },
  deleteProfile(id) { set(state => ({ profiles: state.profiles.filter(p => p.id !== id) })); },

  // ── Active Chat Agent (switcher on main chat) ─────────────────────────────
  activeChatAgent: null,          // { id, name, description, systemPrompt, emoji } | null
  setChatAgent(agent) { set({ activeChatAgent: agent }); },
  clearChatAgent() { set({ activeChatAgent: null }); },

  // ── Agents ────────────────────────────────────────────────────────────────
  agents: [],
  activeAgentId: null,
  addAgent(agent) { set(state => ({ agents: [...state.agents, { id: makeId(), ...agent, savedToFile: false, createdAt: Date.now() }] })); },
  updateAgent(id, patch) { set(state => ({ agents: state.agents.map(a => a.id === id ? { ...a, ...patch } : a) })); },
  deleteAgent(id) { set(state => ({ agents: state.agents.filter(a => a.id !== id), activeAgentId: state.activeAgentId === id ? null : state.activeAgentId })); },
  setActiveAgentId(id) { set({ activeAgentId: id }); },
  async saveAgentToFile(agent) {
    try {
      const res = await fetch('/agents/save', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agent),
      });
      if (res.ok) {
        const { path: filePath } = await res.json();
        set(state => ({ agents: state.agents.map(a => a.id === agent.id ? { ...a, savedToFile: true, filePath } : a) }));
        return { ok: true, filePath };
      }
      return { ok: false };
    } catch { return { ok: false }; }
  },

  // ── Custom Skills ─────────────────────────────────────────────────────────
  customSkills: [],
  addCustomSkill(skill) { set(state => ({ customSkills: [...state.customSkills, { id: makeId(), ...skill, savedToFile: false, createdAt: Date.now() }] })); },
  updateCustomSkill(id, patch) { set(state => ({ customSkills: state.customSkills.map(s => s.id === id ? { ...s, ...patch } : s) })); },
  deleteCustomSkill(id) { set(state => ({ customSkills: state.customSkills.filter(s => s.id !== id) })); },
  async saveSkillToFile(skill) {
    try {
      const res = await fetch('/skills/save', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(skill),
      });
      if (res.ok) {
        const { path: filePath, file } = await res.json();
        set(state => ({ customSkills: state.customSkills.map(s => s.id === skill.id ? { ...s, savedToFile: true, filePath } : s) }));
        return { ok: true, filePath, file };
      }
      return { ok: false };
    } catch { return { ok: false }; }
  },

  // ── Custom Rules ──────────────────────────────────────────────────────────
  customRules: [],
  addCustomRule(rule) { set(state => ({ customRules: [...state.customRules, { id: makeId(), ...rule, savedToFile: false, createdAt: Date.now() }] })); },
  updateCustomRule(id, patch) { set(state => ({ customRules: state.customRules.map(r => r.id === id ? { ...r, ...patch } : r) })); },
  deleteCustomRule(id) { set(state => ({ customRules: state.customRules.filter(r => r.id !== id) })); },
  async saveRuleToFile(rule) {
    try {
      const res = await fetch('/rules/save', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rule),
      });
      if (res.ok) {
        const { path: filePath, file } = await res.json();
        set(state => ({ customRules: state.customRules.map(r => r.id === rule.id ? { ...r, savedToFile: true, filePath } : r) }));
        return { ok: true, filePath, file };
      }
      return { ok: false };
    } catch { return { ok: false }; }
  },

  // ── Workflows ─────────────────────────────────────────────────────────────
  workflows: [],
  addWorkflow(wf) { set(state => ({ workflows: [...state.workflows, { id: makeId(), ...wf, status: 'idle', createdAt: Date.now() }] })); },
  deleteWorkflow(id) { set(state => ({ workflows: state.workflows.filter(w => w.id !== id) })); },
  updateWorkflowStatus(id, status) { set(state => ({ workflows: state.workflows.map(w => w.id === id ? { ...w, status } : w) })); },

  // ── Canvas Documents ──────────────────────────────────────────────────────
  canvasDocuments: [],
  activeCanvasDocId: null,
  canvasChatHistories: {}, // { [docId]: Message[] }
  addCanvasDoc(doc) {
    const id = makeId();
    const now = Date.now();
    const full = { id, name: 'Untitled', type: 'markdown', language: 'markdown', content: '', versions: [], ...doc, createdAt: now, updatedAt: now };
    if (full.content) full.versions = [{ id: makeId(), content: full.content, label: 'Initial', timestamp: now }];
    set(state => ({ canvasDocuments: [...state.canvasDocuments, full], activeCanvasDocId: id }));
    return full;
  },
  updateCanvasDoc(id, patch) {
    set(state => ({ canvasDocuments: state.canvasDocuments.map(d => d.id === id ? { ...d, ...patch, updatedAt: Date.now() } : d) }));
  },
  deleteCanvasDoc(id) {
    set(state => {
      const remaining = state.canvasDocuments.filter(d => d.id !== id);
      const nextId = state.activeCanvasDocId === id ? (remaining[0]?.id ?? null) : state.activeCanvasDocId;
      const histories = { ...state.canvasChatHistories };
      delete histories[id];
      return { canvasDocuments: remaining, activeCanvasDocId: nextId, canvasChatHistories: histories };
    });
  },
  setActiveCanvasDocId(id) { set({ activeCanvasDocId: id }); },
  pendingCanvasPrompt: null,
  setPendingCanvasPrompt(text) { set({ pendingCanvasPrompt: text }); },
  clearPendingCanvasPrompt() { set({ pendingCanvasPrompt: null }); },

  pendingAgentPrompt: null,
  setPendingAgentPrompt(text) { set({ pendingAgentPrompt: text }); },
  clearPendingAgentPrompt() { set({ pendingAgentPrompt: null }); },

  pendingWorkflowPrompt: null,
  setPendingWorkflowPrompt(text) { set({ pendingWorkflowPrompt: text }); },
  clearPendingWorkflowPrompt() { set({ pendingWorkflowPrompt: null }); },
  setCanvasChatHistory(docId, messages) {
    set(state => ({ canvasChatHistories: { ...state.canvasChatHistories, [docId]: messages } }));
  },
  addCanvasVersion(docId, content, label) {
    set(state => ({
      canvasDocuments: state.canvasDocuments.map(d => {
        if (d.id !== docId) return d;
        const versions = [...(d.versions || []), { id: makeId(), content, label: label || 'Version', timestamp: Date.now() }].slice(-20);
        return { ...d, content, versions, updatedAt: Date.now() };
      }),
    }));
  },

  // ── UI layout ─────────────────────────────────────────────────────────────
  sidebarOpen: true,
  hivePanelOpen: true,
  toggleSidebar() { set(s => ({ sidebarOpen: !s.sidebarOpen })); },
  toggleHivePanel() { set(s => ({ hivePanelOpen: !s.hivePanelOpen })); },

  activeArtifactId: null,
  setActiveArtifact(id) { set({ activeArtifactId: id }); },
    }),
    {
      name: 'sc-store-v1',
      // Only persist bgRuns (so in-flight runs survive refresh) + canvas docs + theme
      partialize: (state) => ({
        bgRuns: state.bgRuns,
        canvasDocuments: state.canvasDocuments,
        activeCanvasDocId: state.activeCanvasDocId,
        canvasChatHistories: state.canvasChatHistories,
        theme: state.theme,
      }),
    }
  )
);

// ── API helpers ───────────────────────────────────────────────────────────────

export async function fetchHealth() {
  try {
    const r = await fetch(`${API_BASE}/health`);
    return r.ok ? r.json() : null;
  } catch { return null; }
}

export async function fetchModels() {
  try {
    const r = await fetch(`${API_BASE}/models`);
    if (!r.ok) return [];
    const data = await r.json();
    return data.data ?? [];
  } catch { return []; }
}

export async function fetchModules() {
  try {
    const r = await fetch(`${API_BASE}/modules`);
    if (!r.ok) return [];
    const data = await r.json();
    return data.modules ?? [];
  } catch { return []; }
}

export async function* streamChat({ messages, model, signal, onDispatch, onTaskPlan, onTaskUpdate, ...extraBody }) {
  const apiKey = import.meta.env.VITE_API_KEY;
  const headers = { 'Content-Type': 'application/json' };
  if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers,
    signal,
    body: JSON.stringify({ messages, model, stream: true, ...extraBody }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Chat error ${res.status}: ${err}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const raw = line.slice(5).trim();
      if (raw === '[DONE]') return;
      try {
        const chunk = JSON.parse(raw);
        // Agent dispatch event — fire callback, don't yield a token
        if (chunk.type === 'agent_dispatch') {
          onDispatch?.(chunk);
          continue;
        }
        // Task plan / task update events (from TaskExecutor)
        if (chunk.event === 'task_plan') {
          onTaskPlan?.(chunk.payload);
          continue;
        }
        if (chunk.event === 'task_update') {
          onTaskUpdate?.(chunk.payload);
          continue;
        }
        const delta = chunk.choices?.[0]?.delta?.content;
        if (delta) yield delta;
      } catch { /* skip malformed */ }
    }
  }
}

// ── WebSocket manager ─────────────────────────────────────────────────────────

let ws = null;
let wsRetryTimer = null;
const WS_URL = (() => {
  const base = import.meta.env.VITE_WS_BASE;
  if (base) return `${base}/v1/ws`;
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  // Route through Caddy (same host, no port) — Caddy proxies /v1/ws to Go backbone
  return `${proto}//${location.host}/v1/ws`;
})();

let wsRetries = 0;
const WS_MAX_RETRIES = 8;
const WS_BACKOFF = [2000, 4000, 8000, 15000, 30000, 60000, 120000, 300000];

export function connectHiveWS() {
  const store = useSCStore.getState();
  if (ws && ws.readyState <= WebSocket.OPEN) return;

  // Silent give-up after max retries — backbone may not be serving WS
  if (wsRetries >= WS_MAX_RETRIES) {
    store.setWsStatus('disconnected');
    return;
  }

  store.setWsStatus(wsRetries === 0 ? 'reconnecting' : 'disconnected');

  try {
    ws = new WebSocket(WS_URL);
  } catch {
    store.setWsStatus('disconnected');
    return;
  }

  ws.onopen = () => {
    wsRetries = 0;
    useSCStore.getState().setWsStatus('connected');
    if (wsRetryTimer) { clearTimeout(wsRetryTimer); wsRetryTimer = null; }
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      const s = useSCStore.getState();
      if (msg.type === 'resonance_sync') {
        // Payload IS the ResonanceState struct — unwrap from WS envelope
        const p = msg.payload ?? msg;
        s.setEriState({
          eri:        p.ERI        ?? p.eri        ?? 0.5,
          ers:        p.ERS        ?? p.ers        ?? 0.5,
          pacing:     p.Pacing     ?? p.pacing     ?? 1.0,
          volatility: p.Volatility ?? p.volatility ?? 0.0,
          coherence:  p.Coherence  ?? p.coherence  ?? 1.0,
          musicalKey: p.MusicalKey ?? p.musical_key ?? 'C Major',
          bpm:        p.BPM        ?? p.bpm        ?? 120.0,
        });
        if (p.active_modules) s.setHiveActive(p.active_modules);
        if (p.edges) s.setHiveEdges(p.edges);
        if (p.consensus != null) s.setConsensusScore(p.consensus);
      } else if (msg.type === 'sensory_sync') {
        const p = msg.payload ?? msg;
        s.setSensoryState({
          active_tone:     p.active_tone     ?? 'Deep Focus',
          primary_color:   p.primary_color   ?? '#3399FF',
          secondary_color: p.secondary_color ?? '#994CFF',
          opacity:         p.opacity         ?? 0.85,
          pulse_rate:      p.pulse_rate      ?? 1.0,
        });
      } else if (msg.type === 'agent_action') {
        // Update dispatch card in whatever session it lives in
        const payload = msg.payload ?? msg;
        const allSessions = useSCStore.getState().sessions;
        useSCStore.setState({
          sessions: allSessions.map(sess => ({
            ...sess,
            messages: sess.messages.map(m =>
              m.role === 'dispatch' && m.jobId === payload.job_id
                ? { ...m, status: payload.status, summary: payload.summary, error: payload.error }
                : m
            ),
          })),
        });
      } else if (msg.type === 'scai_correction') {
        // SCAI Critique-Revision fired post-stream and found a constitutional violation.
        // Patch the last assistant message in the matching session with the corrected text,
        // and mark it so the UI can show a correction badge.
        const payload = msg.payload ?? msg;
        const sid = payload.session_id;
        const corrected = payload.corrected;
        if (!corrected) return;
        const allSessions = useSCStore.getState().sessions;
        useSCStore.setState({
          sessions: allSessions.map(sess => {
            // If session_id header wasn't set, fall back to patching active session
            if (sid && sess.id !== sid) return sess;
            const msgs = [...sess.messages];
            // Find the last assistant message and patch it
            for (let i = msgs.length - 1; i >= 0; i--) {
              if (msgs[i].role === 'assistant') {
                msgs[i] = { ...msgs[i], content: corrected, scaiCorrected: true };
                break;
              }
            }
            return { ...sess, messages: msgs };
          }),
        });
      }
    } catch { /* ignore */ }
  };

  ws.onclose = () => {
    useSCStore.getState().setWsStatus('disconnected');
    const delay = WS_BACKOFF[Math.min(wsRetries, WS_BACKOFF.length - 1)];
    wsRetries++;
    if (wsRetries < WS_MAX_RETRIES) {
      wsRetryTimer = setTimeout(connectHiveWS, delay);
    }
  };

  ws.onerror = () => { ws.close(); };
}

// ── Global workflow run poller ──────────────────────────────────────────────
// Runs independently of page/component lifecycle — survives navigation.
setInterval(() => {
  const { bgRuns, updateBgRun, addCanvasDoc, setActivePage } = useSCStore.getState();
  const TERMINAL = new Set(['done', 'error', 'cancelled']);
  const NO_POLL  = new Set(['done', 'error', 'cancelled', 'cancelling', 'pausing']);
  Object.values(bgRuns).forEach(({ runId, run, sendToCanvas, wfName, _canvasPushed }) => {
    if (TERMINAL.has(run?.status)) {
      // Push final output to Canvas once when run completes
      if (sendToCanvas && run?.status === 'done' && run?.final_output && !_canvasPushed) {
        useSCStore.setState(state => ({
          bgRuns: { ...state.bgRuns, [runId]: { ...state.bgRuns[runId], _canvasPushed: true } },
        }));
        addCanvasDoc({
          name: wfName ? `${wfName} — Output` : 'Workflow Output',
          type: 'markdown',
          language: 'markdown',
          content: run.final_output,
        });
        setActivePage('canvas');
      }
      return;
    }
    if (NO_POLL.has(run?.status)) return;
    fetch(`/workflows/runs/${runId}`)
      .then(r => r.json())
      .then(data => updateBgRun(runId, data))
      .catch(() => {});
  });
}, 1500);
