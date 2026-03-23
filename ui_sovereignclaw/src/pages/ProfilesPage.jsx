import { useState, useEffect, useCallback } from 'react';
import { useSCStore } from '../store';
import { Plus, Trash2, Edit3, X, User, Cpu, ChevronDown, ChevronUp, Save, RefreshCw } from 'lucide-react';

const API = (path) => `${import.meta.env.VITE_API_BASE ?? 'http://localhost:8089'}/v1${path}`;
const authHeaders = () => {
  const k = localStorage.getItem('sc_api_key');
  return k ? { 'Content-Type': 'application/json', Authorization: `Bearer ${k}` } : { 'Content-Type': 'application/json' };
};

const ARCHETYPES = ['friend', 'mentor', 'professional', 'creative', 'cheerleader'];
const ENERGIES   = ['low', 'moderate', 'high'];

function SovereignIdentityEditor() {
  const [profile, setProfile]   = useState(null);
  const [saving, setSaving]     = useState(false);
  const [saved, setSaved]       = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [instrText, setInstrText] = useState('');
  const [rulesText, setRulesText] = useState('');

  const load = useCallback(async () => {
    try {
      const res = await fetch(API('/sovereign/identity'), { headers: authHeaders() });
      const data = await res.json();
      setProfile(data);
      setInstrText((data.instructions ?? []).join('\n'));
      setRulesText((data.rules ?? []).join('\n'));
    } catch (e) { console.error('[SovereignIdentity] load failed', e); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function save() {
    if (!profile) return;
    setSaving(true);
    try {
      const payload = {
        ...profile,
        instructions: instrText.split('\n').map(l => l.replace(/^-\s*/, '').trim()).filter(Boolean),
        rules:        rulesText.split('\n').map(l => l.replace(/^-\s*/, '').trim()).filter(Boolean),
      };
      await fetch(API('/sovereign/identity'), {
        method: 'PUT', headers: authHeaders(), body: JSON.stringify(payload),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally { setSaving(false); }
  }

  const set = (k, v) => setProfile(p => ({ ...p, [k]: v }));

  const inp = {
    background: 'var(--color-sc-surface2)', border: '1px solid var(--color-sc-border2)',
    color: 'var(--color-sc-text)', borderRadius: 8, padding: '8px 12px',
    fontSize: 13, fontFamily: 'var(--font-inter)', outline: 'none', width: '100%', boxSizing: 'border-box',
  };
  const lbl = { fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6, display: 'block' };

  return (
    <div style={{
      background: 'var(--color-sc-surface)', border: '1px solid rgba(196,164,74,0.25)',
      borderRadius: 12, marginBottom: 28, overflow: 'hidden',
      boxShadow: '0 0 24px rgba(196,164,74,0.05)',
    }}>
      {/* Header */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: '100%', padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 10,
          background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left',
          borderBottom: expanded ? '1px solid var(--color-sc-border)' : 'none',
        }}
      >
        <Cpu size={15} color="var(--color-sc-gold)" />
        <span style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 14, color: 'var(--color-sc-text)', flex: 1 }}>
          Sovereign Identity
        </span>
        <span style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', marginRight: 8 }}>
          {profile?.name ?? '—'}
        </span>
        {expanded ? <ChevronUp size={14} color="var(--color-sc-text-muted)" /> : <ChevronDown size={14} color="var(--color-sc-text-muted)" />}
      </button>

      {expanded && profile && (
        <div style={{ padding: '20px 20px 16px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Description */}
          <div>
            <label style={lbl}>Description</label>
            <input value={profile.description ?? ''} onChange={e => set('description', e.target.value)} style={inp} placeholder="Who is she, in one line?" />
          </div>

          {/* Archetype + Energy row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            <div>
              <label style={lbl}>Archetype</label>
              <select value={profile.archetype ?? 'friend'} onChange={e => set('archetype', e.target.value)} style={{ ...inp, cursor: 'pointer' }}>
                {ARCHETYPES.map(a => <option key={a}>{a}</option>)}
              </select>
            </div>
            <div>
              <label style={lbl}>Energy</label>
              <select value={profile.energy ?? 'moderate'} onChange={e => set('energy', e.target.value)} style={{ ...inp, cursor: 'pointer' }}>
                {ENERGIES.map(e => <option key={e}>{e}</option>)}
              </select>
            </div>
            <div>
              <label style={lbl}>Sass factor — {(profile.sass_factor ?? 0.65).toFixed(2)}</label>
              <input
                type="range" min={0} max={1} step={0.05}
                value={profile.sass_factor ?? 0.65}
                onChange={e => set('sass_factor', parseFloat(e.target.value))}
                style={{ width: '100%', marginTop: 10, accentColor: 'var(--color-sc-gold)' }}
              />
            </div>
          </div>

          {/* Instructions */}
          <div>
            <label style={lbl}>Instructions (one per line)</label>
            <textarea
              value={instrText}
              onChange={e => setInstrText(e.target.value)}
              rows={5}
              style={{ ...inp, resize: 'vertical', lineHeight: 1.7 }}
              placeholder="You have opinions. Share them when relevant..."
            />
          </div>

          {/* Rules */}
          <div>
            <label style={lbl}>Rules (one per line)</label>
            <textarea
              value={rulesText}
              onChange={e => setRulesText(e.target.value)}
              rows={4}
              style={{ ...inp, resize: 'vertical', lineHeight: 1.7 }}
              placeholder="Never start a response with a personality phrase verbatim..."
            />
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', paddingTop: 4 }}>
            <button onClick={load} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 8,
              background: 'none', border: '1px solid var(--color-sc-border)',
              color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 12,
            }}>
              <RefreshCw size={12} /> Reload
            </button>
            <button onClick={save} disabled={saving} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '7px 18px', borderRadius: 8,
              background: saved ? 'rgba(6,214,160,0.15)' : 'rgba(196,164,74,0.14)',
              border: `1px solid ${saved ? 'rgba(6,214,160,0.4)' : 'rgba(196,164,74,0.35)'}`,
              color: saved ? '#06D6A0' : 'var(--color-sc-gold)',
              cursor: saving ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600,
              fontFamily: 'var(--font-grotesk)', transition: 'all 0.2s',
            }}>
              <Save size={12} /> {saved ? 'Saved!' : saving ? 'Saving…' : 'Save & apply'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const AVATAR_COLORS = ['#C4A44A','#4D9EFF','#06D6A0','#FF4D6D','#A78BFA','#F97316','#EC4899','#14B8A6'];

const SKILLS = [
  'api_designer','benchmark_analyst','data_scientist','devops_sre','digital_guardian',
  'go_engineer','hive_orchestrator','jarvis_ops','knowledge_curator','ml_trainer',
  'offensive_security','prompt_engineer','senior_python_dev','sovereign_planner',
  'system_architect','technical_writer',
];

const EMPTY_FORM = { name: '', color: AVATAR_COLORS[0], systemPrompt: '', skills: [], tone: 'balanced' };

function Avatar({ name, color, size = 40 }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', flexShrink: 0,
      background: color + '22', border: `2px solid ${color}55`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.38, fontWeight: 700, color, fontFamily: 'var(--font-grotesk)',
      userSelect: 'none',
    }}>
      {name ? name[0].toUpperCase() : <User size={size * 0.4} />}
    </div>
  );
}

function ProfileCard({ profile, onDelete, onEdit }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? 'rgba(255,255,255,0.03)' : 'var(--color-sc-surface)',
        border: '1px solid var(--color-sc-border)', borderRadius: 12,
        padding: '18px 18px 14px', display: 'flex', flexDirection: 'column', gap: 12,
        transition: 'border-color 0.15s, background 0.15s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <Avatar name={profile.name} color={profile.color} size={44} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 14, color: 'var(--color-sc-text)' }}>{profile.name}</div>
          <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', marginTop: 2 }}>
            {profile.skills.length > 0 ? profile.skills.map(s => s.replace(/_/g, ' ')).join(', ') : 'No skills assigned'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 4, opacity: hovered ? 1 : 0, transition: 'opacity 0.15s' }}>
          <button onClick={() => onEdit(profile)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-muted)', padding: 4, display: 'flex', borderRadius: 5 }}>
            <Edit3 size={13} />
          </button>
          <button onClick={() => onDelete(profile.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-danger)', padding: 4, display: 'flex', borderRadius: 5 }}>
            <Trash2 size={13} />
          </button>
        </div>
      </div>
      {profile.systemPrompt && (
        <p style={{ margin: 0, fontSize: 12.5, color: 'var(--color-sc-text-muted)', lineHeight: 1.55, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
          {profile.systemPrompt}
        </p>
      )}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {[{ label: profile.tone, color: 'var(--color-sc-gold)' }].map(badge => (
          <span key={badge.label} style={{
            fontSize: 10, padding: '2px 8px', borderRadius: 10,
            background: 'rgba(196,164,74,0.1)', color: badge.color,
            fontFamily: 'var(--font-grotesk)', letterSpacing: '0.04em', textTransform: 'capitalize',
          }}>{badge.label}</span>
        ))}
      </div>
    </div>
  );
}

function ProfileForm({ initial, onSave, onCancel }) {
  const [form, setForm] = useState(initial ?? EMPTY_FORM);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  function toggleSkill(sk) {
    set('skills', form.skills.includes(sk) ? form.skills.filter(s => s !== sk) : [...form.skills, sk]);
  }

  const field = { display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 18 };
  const lbl = { fontSize: 12, fontWeight: 500, color: 'var(--color-sc-text-muted)' };
  const inp = {
    background: 'var(--color-sc-surface2)', border: '1px solid var(--color-sc-border2)',
    color: 'var(--color-sc-text)', borderRadius: 8, padding: '8px 12px',
    fontSize: 13, fontFamily: 'var(--font-inter)', outline: 'none', width: '100%',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      <div style={field}>
        <label style={lbl}>Name</label>
        <input value={form.name} onChange={e => set('name', e.target.value)} placeholder="Profile name" style={inp} />
      </div>

      <div style={field}>
        <label style={lbl}>Avatar colour</label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {AVATAR_COLORS.map(c => (
            <button key={c} onClick={() => set('color', c)} style={{
              width: 26, height: 26, borderRadius: '50%', background: c, border: `2px solid ${form.color === c ? 'white' : 'transparent'}`,
              cursor: 'pointer', transition: 'border-color 0.15s',
            }} />
          ))}
        </div>
      </div>

      <div style={field}>
        <label style={lbl}>Tone</label>
        <select value={form.tone} onChange={e => set('tone', e.target.value)} style={{ ...inp, cursor: 'pointer' }}>
          {['balanced','technical','concise','creative','formal'].map(t => <option key={t}>{t}</option>)}
        </select>
      </div>

      <div style={field}>
        <label style={lbl}>System prompt (optional)</label>
        <textarea
          value={form.systemPrompt}
          onChange={e => set('systemPrompt', e.target.value)}
          placeholder="You are a..."
          rows={3}
          style={{ ...inp, resize: 'vertical', lineHeight: 1.6 }}
        />
      </div>

      <div style={field}>
        <label style={lbl}>Assign skills</label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {SKILLS.map(sk => {
            const on = form.skills.includes(sk);
            return (
              <button key={sk} onClick={() => toggleSkill(sk)} style={{
                padding: '4px 10px', borderRadius: 8, border: `1px solid ${on ? 'var(--color-sc-gold)' : 'var(--color-sc-border)'}`,
                background: on ? 'rgba(196,164,74,0.12)' : 'transparent',
                color: on ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
                fontSize: 11, cursor: 'pointer', fontFamily: 'var(--font-inter)',
                transition: 'all 0.12s',
              }}>{sk.replace(/_/g, ' ')}</button>
            );
          })}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
        <button onClick={onCancel} style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'none', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 13 }}>Cancel</button>
        <button
          onClick={() => form.name.trim() && onSave(form)}
          disabled={!form.name.trim()}
          style={{
            padding: '8px 20px', borderRadius: 8, border: 'none', cursor: form.name.trim() ? 'pointer' : 'not-allowed',
            background: form.name.trim() ? 'var(--color-sc-gold)' : 'rgba(255,255,255,0.06)',
            color: form.name.trim() ? '#0D0D0D' : 'var(--color-sc-text-dim)',
            fontSize: 13, fontWeight: 600, fontFamily: 'var(--font-grotesk)',
          }}
        >Save profile</button>
      </div>
    </div>
  );
}

export function ProfilesPage() {
  const profiles = useSCStore(s => s.profiles);
  const addProfile = useSCStore(s => s.addProfile);
  const updateProfile = useSCStore(s => s.updateProfile);
  const deleteProfile = useSCStore(s => s.deleteProfile);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
      {/* Header */}
      <div style={{ padding: '24px 32px 20px', borderBottom: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)', flexShrink: 0, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ margin: '0 0 4px', fontFamily: 'var(--font-grotesk)', fontSize: 20, fontWeight: 700, color: 'var(--color-sc-text)' }}>Profiles</h1>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--color-sc-text-muted)' }}>Create agent personas with custom behaviour, tone, and assigned skills.</p>
        </div>
        <button
          onClick={() => { setCreating(true); setEditing(null); }}
          style={{
            display: 'flex', alignItems: 'center', gap: 7, padding: '8px 16px', borderRadius: 9,
            background: 'rgba(196,164,74,0.12)', border: '1px solid rgba(196,164,74,0.3)',
            color: 'var(--color-sc-gold)', cursor: 'pointer', fontSize: 13, fontWeight: 600,
            fontFamily: 'var(--font-grotesk)', transition: 'background 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(196,164,74,0.22)'}
          onMouseLeave={e => e.currentTarget.style.background = 'rgba(196,164,74,0.12)'}
        >
          <Plus size={14} /> New profile
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 32px' }}>
        {/* Sovereign Identity — active .ori profile editor */}
        <SovereignIdentityEditor />

        {/* Agent persona section label */}
        <div style={{ fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 16 }}>
          Agent Personas
        </div>

        {/* Creator / editor */}
        {(creating || editing) && (
          <div style={{
            background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-gold)',
            borderRadius: 12, padding: '20px 22px', marginBottom: 24,
            boxShadow: '0 0 20px rgba(196,164,74,0.08)',
          }}>
            <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 600, fontSize: 14, color: 'var(--color-sc-text)', marginBottom: 18 }}>
              {editing ? 'Edit profile' : 'Create profile'}
            </div>
            <ProfileForm
              initial={editing}
              onSave={data => {
                if (editing) updateProfile(editing.id, data);
                else addProfile(data);
                setCreating(false); setEditing(null);
              }}
              onCancel={() => { setCreating(false); setEditing(null); }}
            />
          </div>
        )}

        {profiles.length === 0 && !creating && (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--color-sc-text-dim)' }}>
            <User size={36} style={{ opacity: 0.2, marginBottom: 12 }} />
            <div style={{ fontSize: 14, marginBottom: 8, color: 'var(--color-sc-text-muted)' }}>No profiles yet</div>
            <div style={{ fontSize: 13 }}>Create a profile to save a custom agent persona.</div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
          {profiles.map(p => (
            <ProfileCard key={p.id} profile={p}
              onDelete={deleteProfile}
              onEdit={p => { setEditing(p); setCreating(false); }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
