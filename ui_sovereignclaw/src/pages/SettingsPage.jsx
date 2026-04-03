import { useState, useEffect } from 'react';
import { useSCStore, PB_URL } from '../store';
import { ProfilesPage } from './ProfilesPage';
import { User, Monitor, Sliders, Sun, Moon, Check, Loader, Eye, EyeOff, Cpu, Zap, Target, Mail, Trash2, Plus, Bell } from 'lucide-react';

const SKILLS = [
  'api_designer','benchmark_analyst','data_scientist','devops_sre',
  'digital_guardian','go_engineer','hive_orchestrator','jarvis_ops',
  'knowledge_curator','ml_trainer','offensive_security','prompt_engineer',
  'senior_python_dev','sovereign_planner','system_architect','technical_writer',
];

const TABS = [
  { id: 'account',   label: 'Account',   Icon: User },
  { id: 'workspace', label: 'Workspace', Icon: Monitor },
  { id: 'profiles',  label: 'Profiles',  Icon: Cpu },
  { id: 'email',     label: 'Email',     Icon: Mail },
  { id: 'advanced',  label: 'Advanced',  Icon: Sliders },
];

// ─── Shared styles ────────────────────────────────────────────────────────────
const S = {
  label: {
    fontSize: 11, fontWeight: 700, color: 'var(--color-sc-text-muted)',
    fontFamily: 'var(--font-grotesk)', marginBottom: 6, display: 'block',
    textTransform: 'uppercase', letterSpacing: '0.06em',
  },
  input: {
    width: '100%', background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)',
    borderRadius: 8, padding: '9px 12px', color: 'var(--color-sc-text)',
    fontFamily: 'var(--font-inter)', fontSize: 13, outline: 'none', boxSizing: 'border-box',
  },
  select: {
    width: '100%', background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)',
    borderRadius: 8, padding: '9px 12px', color: 'var(--color-sc-text)',
    fontFamily: 'var(--font-inter)', fontSize: 13, outline: 'none', cursor: 'pointer',
  },
  row: { marginBottom: 22 },
  hint: { fontSize: 11, color: 'var(--color-sc-text-dim)', marginTop: 5, lineHeight: 1.5 },
  section: {
    fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 11,
    color: 'var(--color-sc-text-muted)', textTransform: 'uppercase',
    letterSpacing: '0.07em', marginBottom: 14, marginTop: 28,
  },
  saveBtn: (saving, saved) => ({
    display: 'inline-flex', alignItems: 'center', gap: 7, padding: '9px 20px',
    borderRadius: 9, border: 'none', cursor: saving ? 'default' : 'pointer',
    fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 13,
    background: saved
      ? 'color-mix(in srgb, var(--color-sc-success) 15%, transparent)'
      : 'color-mix(in srgb, var(--color-sc-gold) 15%, transparent)',
    color: saved ? 'var(--color-sc-success)' : 'var(--color-sc-gold)',
    border: `1px solid ${saved ? 'color-mix(in srgb, var(--color-sc-success) 30%, transparent)' : 'color-mix(in srgb, var(--color-sc-gold) 30%, transparent)'}`,
    transition: 'all 0.2s',
  }),
};

// ─── AccountTab ───────────────────────────────────────────────────────────────
function AccountTab() {
  const user  = useSCStore(s => s.user);
  const token = useSCStore(s => s.token);
  const refreshUser = useSCStore(s => s.refreshUser);

  const [name, setName]         = useState(user?.name ?? '');
  const [email, setEmail]       = useState(user?.email ?? '');
  const [saving, setSaving]     = useState(false);
  const [saved, setSaved]       = useState(false);
  const [error, setError]       = useState('');

  const [curPw, setCurPw]       = useState('');
  const [newPw, setNewPw]       = useState('');
  const [confirmPw, setConfirm] = useState('');
  const [showPw, setShowPw]     = useState(false);
  const [pwSaving, setPwSaving] = useState(false);
  const [pwSaved, setPwSaved]   = useState(false);
  const [pwError, setPwError]   = useState('');

  // Avatar initials
  const initials = (user?.name ?? '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();

  async function saveProfile() {
    if (!user?.id) return;
    setSaving(true); setError('');
    try {
      const res = await fetch(`${PB_URL}/api/collections/users/records/${user.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: token },
        body: JSON.stringify({ name, email }),
      });
      if (!res.ok) throw new Error((await res.json()).message || 'Save failed');
      await refreshUser();
      setSaved(true); setTimeout(() => setSaved(false), 2000);
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  }

  async function changePassword() {
    if (newPw !== confirmPw) { setPwError('Passwords do not match'); return; }
    if (newPw.length < 8)    { setPwError('Minimum 8 characters'); return; }
    if (!user?.id) return;
    setPwSaving(true); setPwError('');
    try {
      const res = await fetch(`${PB_URL}/api/collections/users/records/${user.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: token },
        body: JSON.stringify({ oldPassword: curPw, password: newPw, passwordConfirm: confirmPw }),
      });
      if (!res.ok) throw new Error((await res.json()).message || 'Password change failed');
      setPwSaved(true); setCurPw(''); setNewPw(''); setConfirm('');
      setTimeout(() => setPwSaved(false), 2500);
    } catch (e) { setPwError(e.message); }
    finally { setPwSaving(false); }
  }

  return (
    <div style={{ maxWidth: 500 }}>
      {/* Avatar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginBottom: 28 }}>
        <div style={{
          width: 56, height: 56, borderRadius: '50%',
          background: 'color-mix(in srgb, var(--color-sc-gold) 18%, transparent)',
          border: '2px solid color-mix(in srgb, var(--color-sc-gold) 35%, transparent)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-grotesk)', fontWeight: 800, fontSize: 18,
          color: 'var(--color-sc-gold)',
        }}>{initials}</div>
        <div>
          <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 15, color: 'var(--color-sc-text)' }}>{user?.name ?? '—'}</div>
          <div style={{ fontSize: 12, color: 'var(--color-sc-text-muted)', marginTop: 3 }}>{user?.email ?? '—'}</div>
          <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', marginTop: 2, textTransform: 'capitalize' }}>Role: {user?.role ?? '—'}</div>
        </div>
      </div>

      {/* Profile fields */}
      <div style={S.row}>
        <label style={S.label}>Name</label>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="Your name" style={S.input} />
      </div>
      <div style={S.row}>
        <label style={S.label}>Email</label>
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="email@domain.com" style={S.input} />
      </div>
      {error && <p style={{ color: 'var(--color-sc-danger)', fontSize: 12, marginBottom: 12 }}>{error}</p>}
      <button onClick={saveProfile} disabled={saving} style={S.saveBtn(saving, saved)}>
        {saving ? <Loader size={13} /> : saved ? <Check size={13} /> : null}
        {saved ? 'Saved' : 'Save Profile'}
      </button>

      {/* Password */}
      <div style={S.section}>Change Password</div>
      <div style={S.row}>
        <label style={S.label}>Current Password</label>
        <div style={{ position: 'relative' }}>
          <input type={showPw ? 'text' : 'password'} value={curPw} onChange={e => setCurPw(e.target.value)} placeholder="Current password" style={{ ...S.input, paddingRight: 36 }} />
          <button onClick={() => setShowPw(v => !v)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-muted)', display: 'flex' }}>
            {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 22 }}>
        <div>
          <label style={S.label}>New Password</label>
          <input type={showPw ? 'text' : 'password'} value={newPw} onChange={e => setNewPw(e.target.value)} placeholder="New password" style={S.input} />
        </div>
        <div>
          <label style={S.label}>Confirm</label>
          <input type={showPw ? 'text' : 'password'} value={confirmPw} onChange={e => setConfirm(e.target.value)} placeholder="Confirm password" style={S.input} />
        </div>
      </div>
      {pwError && <p style={{ color: 'var(--color-sc-danger)', fontSize: 12, marginBottom: 12 }}>{pwError}</p>}
      <button onClick={changePassword} disabled={pwSaving} style={S.saveBtn(pwSaving, pwSaved)}>
        {pwSaving ? <Loader size={13} /> : pwSaved ? <Check size={13} /> : null}
        {pwSaved ? 'Password Updated' : 'Update Password'}
      </button>
    </div>
  );
}

// Model display map — friendly labels over raw IDs
const MODEL_CARDS = [
  {
    id:    'fast',
    label: 'Fast',
    Icon:  Zap,
    desc:  'Snappy responses for everyday tasks — summaries, quick answers, short drafts.',
    match: m => /ministral|3b|small|mini|flash/i.test(m),
  },
  {
    id:    'precise',
    label: 'Precise',
    Icon:  Target,
    desc:  'Deeper reasoning for code, analysis, research, and complex workflows.',
    match: m => /coder|7b|14b|large|pro|plus|qwen|deepseek/i.test(m),
  },
];

function friendlyToModelId(friendlyId, models) {
  const card = MODEL_CARDS.find(c => c.id === friendlyId);
  if (!card) return models[0]?.id ?? null;
  return models.find(m => card.match(m.id))?.id ?? models[0]?.id ?? null;
}

function modelIdToFriendly(modelId, models) {
  if (!modelId) return 'fast';
  for (const card of MODEL_CARDS) {
    if (card.match(modelId)) return card.id;
  }
  return 'fast';
}

// ─── WorkspaceTab ─────────────────────────────────────────────────────────────
function WorkspaceTab() {
  const theme        = useSCStore(s => s.theme);
  const toggleTheme  = useSCStore(s => s.toggleTheme);
  const models       = useSCStore(s => s.models);
  const activeModel  = useSCStore(s => s.activeModel);
  const setActiveModel = useSCStore(s => s.setActiveModel);

  const friendly = modelIdToFriendly(activeModel, models);

  function pickFriendly(cardId) {
    const modelId = friendlyToModelId(cardId, models);
    if (modelId) setActiveModel(modelId);
  }

  return (
    <div style={{ maxWidth: 500 }}>
      {/* Intelligence Mode */}
      {models.length > 0 && (
        <>
          <div style={{ ...S.section, marginTop: 0 }}>Intelligence Mode</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 28 }}>
            {MODEL_CARDS.map(card => {
              const active = friendly === card.id;
              return (
                <button
                  key={card.id}
                  onClick={() => pickFriendly(card.id)}
                  style={{
                    textAlign: 'left', padding: '16px 18px', borderRadius: 12, cursor: 'pointer',
                    background: active
                      ? 'color-mix(in srgb, var(--color-sc-gold) 10%, var(--color-sc-surface))'
                      : 'var(--color-sc-surface)',
                    border: `1.5px solid ${active ? 'color-mix(in srgb, var(--color-sc-gold) 55%, transparent)' : 'var(--color-sc-border)'}`,
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{ marginBottom: 8 }}><card.Icon size={20} style={{ color: active ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)' }} /></div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 14, color: active ? 'var(--color-sc-gold)' : 'var(--color-sc-text)' }}>
                      {card.label}
                    </span>
                    {active && (
                      <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--color-sc-gold)', background: 'color-mix(in srgb, var(--color-sc-gold) 15%, transparent)', padding: '2px 7px', borderRadius: 20, fontFamily: 'var(--font-grotesk)' }}>
                        Active
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--color-sc-text-muted)', lineHeight: 1.5 }}>{card.desc}</div>
                </button>
              );
            })}
          </div>
        </>
      )}

      <div style={S.section}>Appearance</div>

      {/* Theme toggle */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, marginBottom: 12 }}>
        <div>
          <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 600, fontSize: 13, color: 'var(--color-sc-text)' }}>Theme</div>
          <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', marginTop: 2 }}>Toggle between dark and light mode</div>
        </div>
        <button
          onClick={toggleTheme}
          style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px',
            borderRadius: 8, border: '1px solid var(--color-sc-border)',
            background: 'var(--color-sc-bg)', cursor: 'pointer',
            color: 'var(--color-sc-text)', fontSize: 13, fontFamily: 'var(--font-grotesk)', fontWeight: 600,
          }}
        >
          {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
      </div>

      <div style={{ marginTop: 28 }}>
        <div style={S.section}>About ORI Studio</div>
        <div style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, overflow: 'hidden' }}>
          {[
            { label: 'Product',            value: 'ORI Studio' },
            { label: 'Intelligence Engine',value: 'Oricli-Alpha' },
            { label: 'Data Residency',     value: 'Your infrastructure only' },
            { label: 'Model Providers',    value: 'None — fully sovereign' },
            { label: 'Built by',           value: 'Thynaptic' },
          ].map((r, i, arr) => (
            <div key={r.label} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '11px 16px', fontSize: 13,
              borderBottom: i < arr.length - 1 ? '1px solid var(--color-sc-border)' : 'none',
            }}>
              <span style={{ color: 'var(--color-sc-text-muted)' }}>{r.label}</span>
              <span style={{ color: 'var(--color-sc-text)', fontWeight: 500 }}>{r.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── AdvancedTab ──────────────────────────────────────────────────────────────
function AdvancedTab() {
  const models         = useSCStore(s => s.models);
  const activeModel    = useSCStore(s => s.activeModel);
  const setActiveModel = useSCStore(s => s.setActiveModel);
  const activeSkill    = useSCStore(s => s.activeSkill);
  const setActiveSkill = useSCStore(s => s.setActiveSkill);
  const health         = useSCStore(s => s.health);
  const wsStatus       = useSCStore(s => s.wsStatus);

  return (
    <div style={{ maxWidth: 500 }}>
      {models.length > 0 && (
        <div style={S.row}>
          <label style={S.label}>Model</label>
          <select value={activeModel ?? ''} onChange={e => setActiveModel(e.target.value)} style={S.select}>
            {models.map(m => <option key={m.id} value={m.id}>{m.id}</option>)}
          </select>
        </div>
      )}

      <div style={S.row}>
        <label style={S.label}>Expertise Mode</label>
        <select value={activeSkill ?? ''} onChange={e => setActiveSkill(e.target.value || null)} style={S.select}>
          <option value="">Auto — no specific mode</option>
          {SKILLS.map(sk => <option key={sk} value={sk}>{sk.replace(/_/g, ' ')}</option>)}
        </select>
        <p style={S.hint}>Activates a specialised skill profile for the current session.</p>
      </div>

      <div style={S.section}>System Status</div>
      <div style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, overflow: 'hidden' }}>
        {[
          { label: 'API',                value: health?.ok ? 'Connected' : 'Disconnected', ok: health?.ok },
          { label: 'Intelligence stream', value: wsStatus, ok: wsStatus === 'connected' },
          { label: 'API base',            value: health?.api_base ?? '—', mono: true },
        ].map((r, i, arr) => (
          <div key={r.label} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '11px 16px', fontSize: 13,
            borderBottom: i < arr.length - 1 ? '1px solid var(--color-sc-border)' : 'none',
          }}>
            <span style={{ color: 'var(--color-sc-text-muted)' }}>{r.label}</span>
            <span style={{
              color: r.ok === true ? 'var(--color-sc-success)' : r.ok === false ? 'var(--color-sc-danger)' : 'var(--color-sc-text)',
              fontFamily: r.mono ? 'var(--font-mono)' : 'var(--font-inter)',
              fontSize: r.mono ? 11 : 13,
            }}>{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── EmailTab ─────────────────────────────────────────────────────────────────
function EmailTab() {
  const token = useSCStore(s => s.token);
  const [clients, setClients]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [adding, setAdding]     = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName]   = useState('');
  const [newTime, setNewTime]   = useState('08:00');
  const [newBriefing, setNewBriefing] = useState(true);
  const [err, setErr]           = useState('');
  const [saving, setSaving]     = useState(null);

  const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };

  useEffect(() => { fetchClients(); }, []);

  async function fetchClients() {
    setLoading(true);
    try {
      const r = await fetch('/v1/email/clients', { headers });
      const d = await r.json();
      setClients(d.clients || []);
    } catch { setClients([]); }
    setLoading(false);
  }

  async function addClient() {
    if (!newEmail.includes('@')) { setErr('Enter a valid email.'); return; }
    setErr('');
    setSaving('add');
    try {
      const r = await fetch('/v1/email/clients', {
        method: 'POST', headers,
        body: JSON.stringify({ email: newEmail, name: newName || newEmail.split('@')[0], briefing: newBriefing, briefing_time: newTime }),
      });
      if (!r.ok) { const d = await r.json(); setErr(d.error || 'Failed'); }
      else { setAdding(false); setNewEmail(''); setNewName(''); setNewBriefing(true); setNewTime('08:00'); fetchClients(); }
    } catch { setErr('Network error'); }
    setSaving(null);
  }

  async function toggleBriefing(email, current, time) {
    setSaving(email);
    await fetch(`/v1/email/clients/${encodeURIComponent(email)}`, {
      method: 'PATCH', headers,
      body: JSON.stringify({ briefing: !current, briefing_time: time }),
    });
    setSaving(null);
    fetchClients();
  }

  async function removeClient(email) {
    if (!confirm(`Remove ${email}?`)) return;
    setSaving(email + '_del');
    await fetch(`/v1/email/clients/${encodeURIComponent(email)}`, { method: 'DELETE', headers });
    setSaving(null);
    fetchClients();
  }

  async function sendBriefingNow(email) {
    setSaving(email + '_brief');
    await fetch(`/v1/email/briefing/${encodeURIComponent(email)}`, { method: 'POST', headers });
    setSaving(null);
  }

  return (
    <div>
      <div style={S.section}>Email Command Interface</div>
      <p style={{ fontSize: 13, color: 'var(--color-sc-text-muted)', marginBottom: 24, lineHeight: 1.6 }}>
        Authorized clients can email ORI to run workflows, check status, and receive daily briefings.
        Commands: <code style={{ background: 'var(--color-sc-border)', padding: '1px 6px', borderRadius: 4, fontSize: 12 }}>LIST</code>{' '}
        <code style={{ background: 'var(--color-sc-border)', padding: '1px 6px', borderRadius: 4, fontSize: 12 }}>RUN &lt;name&gt;</code>{' '}
        <code style={{ background: 'var(--color-sc-border)', padding: '1px 6px', borderRadius: 4, fontSize: 12 }}>STATUS</code>{' '}
        <code style={{ background: 'var(--color-sc-border)', padding: '1px 6px', borderRadius: 4, fontSize: 12 }}>STOP &lt;id&gt;</code>
      </p>

      {/* Client list */}
      {loading ? (
        <div style={{ color: 'var(--color-sc-text-muted)', fontSize: 13 }}>Loading…</div>
      ) : clients.length === 0 ? (
        <div style={{ color: 'var(--color-sc-text-muted)', fontSize: 13, padding: '16px 0' }}>No authorized clients yet.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
          {clients.map(c => (
            <div key={c.email} style={{
              display: 'flex', alignItems: 'center', gap: 14,
              background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)',
              borderRadius: 10, padding: '12px 16px',
            }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--color-sc-text)', marginBottom: 2 }}>{c.name || c.email}</div>
                <div style={{ fontSize: 12, color: 'var(--color-sc-text-muted)' }}>{c.email}</div>
              </div>

              {/* Briefing toggle */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                <Bell size={13} color={c.briefing ? 'var(--color-sc-gold)' : 'var(--color-sc-text-dim)'} />
                <span style={{ fontSize: 12, color: 'var(--color-sc-text-muted)' }}>
                  {c.briefing ? `Daily ${c.briefing_time || '08:00'}` : 'No briefing'}
                </span>
                <button
                  onClick={() => toggleBriefing(c.email, c.briefing, c.briefing_time)}
                  disabled={saving === c.email}
                  style={{
                    fontSize: 11, padding: '4px 10px', borderRadius: 6, border: 'none', cursor: 'pointer',
                    fontFamily: 'var(--font-grotesk)', fontWeight: 600,
                    background: c.briefing
                      ? 'color-mix(in srgb, var(--color-sc-gold) 15%, transparent)'
                      : 'var(--color-sc-border)',
                    color: c.briefing ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
                  }}
                >
                  {saving === c.email ? '…' : c.briefing ? 'On' : 'Off'}
                </button>
              </div>

              {/* Send briefing now */}
              <button
                onClick={() => sendBriefingNow(c.email)}
                disabled={saving === c.email + '_brief'}
                title="Send briefing now"
                style={{
                  fontSize: 11, padding: '4px 10px', borderRadius: 6, border: '1px solid var(--color-sc-border)',
                  cursor: 'pointer', background: 'transparent', color: 'var(--color-sc-text-muted)',
                  fontFamily: 'var(--font-grotesk)', fontWeight: 600,
                }}
              >
                {saving === c.email + '_brief' ? '…' : 'Brief now'}
              </button>

              {/* Remove */}
              <button
                onClick={() => removeClient(c.email)}
                disabled={saving === c.email + '_del'}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 4, color: 'var(--color-sc-text-dim)', display: 'flex' }}
              >
                {saving === c.email + '_del' ? <Loader size={14} /> : <Trash2 size={14} />}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add client */}
      {adding ? (
        <div style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, padding: 20, marginBottom: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
            <div>
              <label style={S.label}>Email *</label>
              <input style={S.input} value={newEmail} onChange={e => setNewEmail(e.target.value)} placeholder="client@example.com" />
            </div>
            <div>
              <label style={S.label}>Name</label>
              <input style={S.input} value={newName} onChange={e => setNewName(e.target.value)} placeholder="Optional display name" />
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13, color: 'var(--color-sc-text)' }}>
              <input type="checkbox" checked={newBriefing} onChange={e => setNewBriefing(e.target.checked)} />
              Daily briefing
            </label>
            {newBriefing && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <label style={{ ...S.label, marginBottom: 0 }}>Time</label>
                <input type="time" style={{ ...S.input, width: 120 }} value={newTime} onChange={e => setNewTime(e.target.value)} />
              </div>
            )}
          </div>
          {err && <div style={{ fontSize: 12, color: 'var(--color-sc-error)', marginBottom: 10 }}>{err}</div>}
          <div style={{ display: 'flex', gap: 10 }}>
            <button onClick={addClient} disabled={saving === 'add'} style={S.saveBtn(saving === 'add', false)}>
              {saving === 'add' ? <Loader size={13} /> : <Check size={13} />}
              {saving === 'add' ? 'Adding…' : 'Add Client'}
            </button>
            <button onClick={() => { setAdding(false); setErr(''); }} style={{ ...S.saveBtn(false, false), background: 'transparent', color: 'var(--color-sc-text-muted)', border: '1px solid var(--color-sc-border)' }}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setAdding(true)}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 7, padding: '9px 18px',
            borderRadius: 9, border: '1px dashed var(--color-sc-border)', cursor: 'pointer',
            background: 'transparent', color: 'var(--color-sc-text-muted)',
            fontFamily: 'var(--font-grotesk)', fontWeight: 600, fontSize: 13,
          }}
        >
          <Plus size={14} /> Add Authorized Client
        </button>
      )}

      <div style={{ ...S.section, marginTop: 36 }}>Inbound Address</div>
      <div style={{ fontSize: 13, color: 'var(--color-sc-text-muted)', lineHeight: 1.7 }}>
        Clients send commands to{' '}
        <code style={{ background: 'var(--color-sc-border)', padding: '2px 8px', borderRadius: 4, color: 'var(--color-sc-text)', fontSize: 12 }}>
          ori@inbound.thynaptic.com
        </code>
        {' '}— ORI replies from{' '}
        <code style={{ background: 'var(--color-sc-border)', padding: '2px 8px', borderRadius: 4, color: 'var(--color-sc-text)', fontSize: 12 }}>
          ori@thynaptic.com
        </code>
      </div>
    </div>
  );
}

// ─── SettingsPage ─────────────────────────────────────────────────────────────
export function SettingsPage() {
  const [activeTab, setActiveTab] = useState('account');

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--color-sc-bg)', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '28px 32px 0', borderBottom: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)', flexShrink: 0 }}>
        <h1 style={{ margin: '0 0 20px', fontFamily: 'var(--font-grotesk)', fontWeight: 800, fontSize: 22, color: 'var(--color-sc-text)' }}>Settings</h1>
        <div style={{ display: 'flex', gap: 2 }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 7, padding: '9px 16px',
                border: 'none', borderRadius: '8px 8px 0 0', cursor: 'pointer',
                fontFamily: 'var(--font-grotesk)', fontWeight: 600, fontSize: 13,
                background: activeTab === tab.id ? 'var(--color-sc-bg)' : 'transparent',
                color: activeTab === tab.id ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
                borderBottom: activeTab === tab.id ? '2px solid var(--color-sc-gold)' : '2px solid transparent',
                transition: 'all 0.15s',
              }}
            >
              <tab.Icon size={14} />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {activeTab === 'account'   && <div style={{ padding: '28px 32px' }}><AccountTab /></div>}
        {activeTab === 'workspace' && <div style={{ padding: '28px 32px' }}><WorkspaceTab /></div>}
        {activeTab === 'profiles'  && <ProfilesPage />}
        {activeTab === 'email'     && <div style={{ padding: '28px 32px' }}><EmailTab /></div>}
        {activeTab === 'advanced'  && <div style={{ padding: '28px 32px' }}><AdvancedTab /></div>}
      </div>
    </div>
  );
}

