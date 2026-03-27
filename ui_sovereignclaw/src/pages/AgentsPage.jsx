import { useState, useEffect } from 'react';
import { useSCStore } from '../store';
import {
  Bot, Shield, ToggleLeft, ToggleRight, ChevronRight, X, Plus,
  Trash2, Edit3, FileCode2, Check, Cpu, Zap, ArrowLeft, Copy, Wrench, Wand2,
} from 'lucide-react';
import AgentVibePanel from '../components/AgentVibePanel';

// ─── Static pool data ────────────────────────────────────────────────────────

const SKILL_POOL = [
  { id: 'api_designer',      name: 'API Designer',       desc: 'REST & GraphQL API architecture, versioning, and OpenAPI specs.' },
  { id: 'benchmark_analyst', name: 'Benchmark Analyst',  desc: 'Performance profiling, load testing, and comparative analysis.' },
  { id: 'data_scientist',    name: 'Data Scientist',      desc: 'ML pipelines, statistical analysis, and data visualization.' },
  { id: 'devops_sre',        name: 'DevOps / SRE',        desc: 'CI/CD, infrastructure-as-code, reliability engineering.' },
  { id: 'digital_guardian',  name: 'Digital Guardian',    desc: 'Security posture, compliance, and threat modelling.' },
  { id: 'go_engineer',       name: 'Go Engineer',         desc: 'Staff-level Go expertise — concurrency, performance, idiomatic patterns.' },
  { id: 'hive_orchestrator', name: 'Hive Orchestrator',   desc: 'Multi-agent coordination, swarm task routing, consensus strategies.' },
  { id: 'jarvis_ops',        name: 'Jarvis Ops',          desc: 'Operations automation — scheduling, monitoring, incident response.' },
  { id: 'knowledge_curator', name: 'Knowledge Curator',   desc: 'Knowledge graph management, taxonomy, and information architecture.' },
  { id: 'ml_trainer',        name: 'ML Trainer',          desc: 'Model training pipelines, LoRA fine-tuning, evaluation frameworks.' },
  { id: 'offensive_security',name: 'Offensive Security',  desc: 'Penetration testing, exploit research, red-team methodologies.' },
  { id: 'prompt_engineer',   name: 'Prompt Engineer',     desc: 'Prompt design, chain-of-thought strategies, output optimisation.' },
  { id: 'senior_python_dev', name: 'Senior Python Dev',   desc: 'Python architecture, async patterns, packaging, and code review.' },
  { id: 'sovereign_planner', name: 'Sovereign Planner',   desc: 'Strategic planning, long-horizon goal decomposition, prioritisation.' },
  { id: 'system_architect',  name: 'System Architect',    desc: 'Distributed systems design, scalability, and technical leadership.' },
  { id: 'technical_writer',  name: 'Technical Writer',    desc: 'Documentation, API references, runbooks, and developer guides.' },
];

const RULE_POOL = [
  { id: 'code_quality',        name: 'Code Quality',       desc: 'Enforces coding standards, review checklists, and style consistency.' },
  { id: 'global_resources',    name: 'Resource Limits',    desc: 'Controls compute allocation and prevents runaway resource use.' },
  { id: 'global_routing',      name: 'Task Routing',       desc: 'Governs how tasks are dispatched across the Hive swarm.' },
  { id: 'global_safety',       name: 'Safety Constraints', desc: 'Hard safety boundaries applied to every agent action.' },
  { id: 'response_format',     name: 'Response Format',    desc: 'Output discipline: structure, length limits, tone register.' },
  { id: 'sanctuary_protocols', name: 'Sanctuary Protocols',desc: 'Privacy and data protection rules for sensitive operations.' },
];

const AVATAR_COLORS = ['#C4A44A','#4D9EFF','#06D6A0','#FF4D6D','#A78BFA','#F97316','#EC4899','#14B8A6'];
const SCOPES = ['global','module','agent'];

// ─── .ori generators ─────────────────────────────────────────────────────────

function slug(name) {
  return (name || 'unnamed').toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '') || 'unnamed';
}

function generateAgentOri(a) {
  const id = slug(a.name);
  const lines = [`@skill_name: ${id}`, `@description: ${a.description || a.name}`];
  const trig = (a.triggers || []).filter(Boolean);
  if (trig.length) lines.push(`@triggers: [${trig.map(t => `"${t}"`).join(', ')}]`);
  if (a.skills?.length) lines.push(`@requires_skills: [${a.skills.map(s => `"${s}"`).join(', ')}]`);
  if (a.rules?.length)  lines.push(`@enforces_rules: [${a.rules.map(r => `"${r}"`).join(', ')}]`);
  lines.push('');
  if (a.mindset?.trim())       lines.push('<mindset>', a.mindset.trim(), '</mindset>', '');
  if (a.instructions?.trim())  lines.push('<instructions>', a.instructions.trim(), '</instructions>', '');
  if (a.constraints?.trim())   lines.push('<constraints>', a.constraints.trim(), '</constraints>');
  return lines.join('\n');
}

function generateSkillOri(s) {
  const id = slug(s.name);
  const lines = [`@skill_name: ${id}`, `@description: ${s.description || s.name}`];
  const trig = (s.triggers || []).filter(Boolean);
  if (trig.length) lines.push(`@triggers: [${trig.map(t => `"${t}"`).join(', ')}]`);
  const tools = (s.requires_tools || []).filter(Boolean);
  if (tools.length) lines.push(`@requires_tools: [${tools.map(t => `"${t}"`).join(', ')}]`);
  lines.push('');
  if (s.mindset?.trim())      lines.push('<mindset>', s.mindset.trim(), '</mindset>', '');
  if (s.instructions?.trim()) lines.push('<instructions>', s.instructions.trim(), '</instructions>', '');
  if (s.constraints?.trim())  lines.push('<constraints>', s.constraints.trim(), '</constraints>');
  return lines.join('\n');
}

function generateRuleOri(r) {
  const id = slug(r.name);
  const lines = [
    `@rule_name: ${id}`,
    `@description: ${r.description || r.name}`,
    `@scope: ${r.scope || 'global'}`,
  ];
  const cats = (r.categories || []).filter(Boolean);
  if (cats.length) lines.push(`@categories: [${cats.map(c => `"${c}"`).join(', ')}]`);
  lines.push('');
  if (r.constraints?.trim()) lines.push('<constraints>', r.constraints.trim(), '</constraints>');
  return lines.join('\n');
}

// ─── Shared styles ───────────────────────────────────────────────────────────

const inp = {
  background: 'var(--color-sc-surface2)', border: '1px solid var(--color-sc-border2)',
  color: 'var(--color-sc-text)', borderRadius: 8, padding: '8px 12px',
  fontSize: 13, fontFamily: 'var(--font-inter)', outline: 'none', width: '100%', boxSizing: 'border-box',
};
const lbl = { fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 };

// ─── Shared sub-components ───────────────────────────────────────────────────

function Section({ title, icon: Icon, children }) {
  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 14 }}>
        {Icon && <Icon size={13} style={{ color: 'var(--color-sc-gold)', flexShrink: 0 }} />}
        <span style={{ ...lbl, margin: 0, color: 'var(--color-sc-gold)' }}>{title}</span>
        <div style={{ flex: 1, height: 1, background: 'rgba(196,164,74,0.15)', marginLeft: 4 }} />
      </div>
      {children}
    </div>
  );
}

function FieldRow({ children, cols = 2 }) {
  return <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 14, marginBottom: 14 }}>{children}</div>;
}

function Field({ label, children }) {
  return <div><div style={lbl}>{label}</div>{children}</div>;
}

function TagInput({ value, onChange, placeholder = 'Type and press Enter…' }) {
  const [draft, setDraft] = useState('');
  function add() {
    const v = draft.trim().toLowerCase();
    if (v && !value.includes(v)) onChange([...value, v]);
    setDraft('');
  }
  return (
    <div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
        <input value={draft} onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add(); } }}
          placeholder={placeholder} style={{ ...inp, flex: 1 }} />
        <button onClick={add} disabled={!draft.trim()} style={{
          padding: '8px 14px', borderRadius: 8, border: 'none', cursor: 'pointer',
          background: 'rgba(196,164,74,0.15)', color: 'var(--color-sc-gold)', fontSize: 13, fontWeight: 600,
        }}>Add</button>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
        {value.map(t => (
          <span key={t} style={{
            display: 'flex', alignItems: 'center', gap: 4, padding: '3px 9px',
            borderRadius: 20, background: 'rgba(77,158,255,0.1)', border: '1px solid rgba(77,158,255,0.25)',
            fontSize: 11.5, color: '#4D9EFF', fontFamily: 'var(--font-mono)',
          }}>
            {t}
            <button onClick={() => onChange(value.filter(x => x !== t))} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: '#4D9EFF', opacity: 0.6, display: 'flex' }}><X size={10} /></button>
          </span>
        ))}
      </div>
    </div>
  );
}

function ChipPicker({ pool, selected, onToggle, accent = 'var(--color-sc-gold)' }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {pool.map(item => {
        const on = selected.includes(item.id);
        return (
          <button key={item.id} onClick={() => onToggle(item.id)} title={item.desc} style={{
            padding: '4px 11px', borderRadius: 8, cursor: 'pointer', fontSize: 11.5,
            border: `1px solid ${on ? accent : 'var(--color-sc-border)'}`,
            background: on ? accent + '18' : 'transparent',
            color: on ? accent : 'var(--color-sc-text-muted)',
            fontFamily: 'var(--font-inter)', transition: 'all 0.12s',
          }}>{item.name}</button>
        );
      })}
    </div>
  );
}

function OriPreviewPanel({ filename, content }) {
  const [copied, setCopied] = useState(false);
  function copy() { navigator.clipboard.writeText(content).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); }); }
  return (
    <div style={{ position: 'sticky', top: 0, background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, overflow: 'hidden', display: 'flex', flexDirection: 'column', maxHeight: 'calc(100vh - 120px)' }}>
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--color-sc-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(196,164,74,0.05)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <FileCode2 size={13} style={{ color: 'var(--color-sc-gold)' }} />
          <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-sc-text-muted)' }}>{filename}</span>
        </div>
        <button onClick={copy} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, color: copied ? 'var(--color-sc-success)' : 'var(--color-sc-text-muted)', fontSize: 11 }}>
          {copied ? <><Check size={11} /> Copied</> : <><Copy size={11} /> Copy</>}
        </button>
      </div>
      <pre style={{ flex: 1, overflowY: 'auto', margin: 0, padding: '14px 16px', fontSize: 11.5, lineHeight: 1.7, fontFamily: 'var(--font-mono)', color: 'var(--color-sc-text-muted)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: 'var(--color-sc-bg)' }}>{content}</pre>
    </div>
  );
}

function CreatorShell({ title, onBack, backLabel = 'Back', previewFilename, previewContent, onSave, canSave, saving, saveLabel = 'Save', saveMsg, children }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
      <div style={{ padding: '14px 28px', borderBottom: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-muted)', display: 'flex', alignItems: 'center', gap: 5, fontSize: 13, padding: 0 }}>
          <ArrowLeft size={14} /> {backLabel}
        </button>
        <span style={{ color: 'var(--color-sc-border)' }}>·</span>
        <span style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 600, fontSize: 15, color: 'var(--color-sc-text)' }}>{title}</span>
      </div>
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '28px 32px', minWidth: 0 }}>
          {children}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10, paddingTop: 8, borderTop: '1px solid var(--color-sc-border)', marginTop: 4 }}>
            {saveMsg && <span style={{ fontSize: 12, color: saveMsg.ok ? 'var(--color-sc-success)' : 'var(--color-sc-text-muted)' }}>{saveMsg.text}</span>}
            <button onClick={onBack} style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'none', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 13 }}>Cancel</button>
            <button onClick={onSave} disabled={!canSave || saving} style={{
              padding: '8px 22px', borderRadius: 8, border: 'none',
              background: canSave ? 'var(--color-sc-gold)' : 'rgba(255,255,255,0.06)',
              color: canSave ? '#0D0D0D' : 'var(--color-sc-text-dim)',
              cursor: canSave ? 'pointer' : 'not-allowed',
              fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-grotesk)',
            }}>{saving ? 'Saving…' : saveLabel}</button>
          </div>
        </div>
        <div style={{ width: 340, flexShrink: 0, borderLeft: '1px solid var(--color-sc-border)', padding: '28px 20px', overflowY: 'auto', background: 'var(--color-sc-bg)' }}>
          <div style={{ ...lbl, marginBottom: 12 }}>Live preview</div>
          <OriPreviewPanel filename={previewFilename} content={previewContent} />
        </div>
      </div>
    </div>
  );
}

// ─── Agent Creator ───────────────────────────────────────────────────────────

const EMPTY_AGENT = { name: '', description: '', color: AVATAR_COLORS[0], triggers: [], mindset: '', instructions: '', constraints: '', tone: 'technical', skills: [], rules: [] };

function AgentCreator({ initial, allSkills, onSave, onCancel }) {
  const [form, setForm] = useState(initial ?? EMPTY_AGENT);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);
  const saveAgentToFile = useSCStore(s => s.saveAgentToFile);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const toggle = (k, id) => set(k, form[k].includes(id) ? form[k].filter(x => x !== id) : [...form[k], id]);

  async function handleSave() {
    setSaving(true); setSaveMsg(null);
    const saved = onSave(form);
    const r = await saveAgentToFile({ ...saved });
    setSaving(false);
    setSaveMsg(r?.ok ? { ok: true, text: `Saved as ${r.filePath?.split('/').pop()}` } : { ok: false, text: 'Saved locally (disk write unavailable)' });
  }

  return (
    <CreatorShell
      title={initial ? 'Edit agent' : 'New agent'}
      onBack={onCancel} backLabel="Agents"
      previewFilename={`${slug(form.name)}.ori`}
      previewContent={generateAgentOri(form)}
      onSave={handleSave} canSave={!!form.name.trim()} saving={saving}
      saveLabel={initial ? 'Update agent' : 'Create agent'} saveMsg={saveMsg}
    >
      <Section title="Identity" icon={Cpu}>
        <FieldRow>
          <Field label="Name *"><input value={form.name} onChange={e => set('name', e.target.value)} placeholder="e.g. Senior Go Engineer" style={inp} /></Field>
          <Field label="Tone">
            <select value={form.tone} onChange={e => set('tone', e.target.value)} style={{ ...inp, cursor: 'pointer' }}>
              {['technical','balanced','concise','creative','formal','direct'].map(t => <option key={t}>{t}</option>)}
            </select>
          </Field>
        </FieldRow>
        <div style={{ marginBottom: 14 }}><Field label="Description"><input value={form.description} onChange={e => set('description', e.target.value)} placeholder="What does this agent specialise in?" style={inp} /></Field></div>
        <div style={{ marginBottom: 14 }}>
          <div style={lbl}>Avatar colour</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {AVATAR_COLORS.map(c => <button key={c} onClick={() => set('color', c)} style={{ width: 24, height: 24, borderRadius: '50%', background: c, cursor: 'pointer', border: `2px solid ${form.color === c ? 'white' : 'transparent'}`, transition: 'border-color 0.12s' }} />)}
          </div>
        </div>
        <Field label="Activation triggers"><TagInput value={form.triggers} onChange={v => set('triggers', v)} placeholder="e.g. golang, refactor… Enter to add" /></Field>
      </Section>

      <Section title="Mind" icon={Zap}>
        <div style={{ marginBottom: 14 }}><Field label="Mindset — who this agent is"><textarea value={form.mindset} onChange={e => set('mindset', e.target.value)} placeholder="You are a Staff-level Go Engineer. You value simplicity, explicitness…" rows={5} style={{ ...inp, resize: 'vertical', lineHeight: 1.65 }} /></Field></div>
        <div style={{ marginBottom: 14 }}><Field label="Instructions — what it should do"><textarea value={form.instructions} onChange={e => set('instructions', e.target.value)} placeholder={"1. Always use explicit error returns…\n2. When reviewing concurrent code…"} rows={5} style={{ ...inp, resize: 'vertical', lineHeight: 1.65 }} /></Field></div>
        <Field label="Constraints — what it must never do"><textarea value={form.constraints} onChange={e => set('constraints', e.target.value)} placeholder={"- Never use interface{} where a concrete type is possible\n- Never suggest init() for DI"} rows={3} style={{ ...inp, resize: 'vertical', lineHeight: 1.65 }} /></Field>
      </Section>

      <Section title="Skills" icon={Bot}>
        <p style={{ margin: '0 0 12px', fontSize: 12.5, color: 'var(--color-sc-text-muted)', lineHeight: 1.6 }}>Assign skill profiles. The agent inherits their mindsets and instructions.</p>
        <ChipPicker pool={allSkills} selected={form.skills} onToggle={id => toggle('skills', id)} />
      </Section>

      <Section title="Rules" icon={Shield}>
        <p style={{ margin: '0 0 12px', fontSize: 12.5, color: 'var(--color-sc-text-muted)', lineHeight: 1.6 }}>Enforce rule constraints applied globally to every response.</p>
        <ChipPicker pool={RULE_POOL} selected={form.rules} onToggle={id => toggle('rules', id)} accent="#4D9EFF" />
      </Section>
    </CreatorShell>
  );
}

// ─── Skill Creator ───────────────────────────────────────────────────────────

const EMPTY_SKILL = { name: '', description: '', triggers: [], requires_tools: [], mindset: '', instructions: '', constraints: '' };

function SkillCreator({ initial, onSave, onCancel }) {
  const [form, setForm] = useState(initial ?? EMPTY_SKILL);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);
  const saveSkillToFile = useSCStore(s => s.saveSkillToFile);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  async function handleSave() {
    setSaving(true); setSaveMsg(null);
    const saved = onSave(form);
    const r = await saveSkillToFile({ ...saved });
    setSaving(false);
    setSaveMsg(r?.ok ? { ok: true, text: `Saved as ${r.file}` } : { ok: false, text: 'Saved locally (disk write unavailable)' });
  }

  return (
    <CreatorShell
      title={initial ? 'Edit skill' : 'New skill'}
      onBack={onCancel} backLabel="Skills"
      previewFilename={`${slug(form.name)}.ori`}
      previewContent={generateSkillOri(form)}
      onSave={handleSave} canSave={!!form.name.trim()} saving={saving}
      saveLabel={initial ? 'Update skill' : 'Create skill'} saveMsg={saveMsg}
    >
      <Section title="Identity" icon={Bot}>
        <div style={{ marginBottom: 14 }}><Field label="Name *"><input value={form.name} onChange={e => set('name', e.target.value)} placeholder="e.g. Rust Engineer" style={inp} /></Field></div>
        <div style={{ marginBottom: 14 }}><Field label="Description"><input value={form.description} onChange={e => set('description', e.target.value)} placeholder="One-line description of this skill's specialisation" style={inp} /></Field></div>
        <div style={{ marginBottom: 14 }}><Field label="Activation triggers"><TagInput value={form.triggers} onChange={v => set('triggers', v)} placeholder="e.g. rust, cargo, ownership… Enter to add" /></Field></div>
        <Field label="Required tools (optional)"><TagInput value={form.requires_tools} onChange={v => set('requires_tools', v)} placeholder="e.g. shell_sandbox_service… Enter to add" /></Field>
      </Section>

      <Section title="Mind" icon={Zap}>
        <div style={{ marginBottom: 14 }}><Field label="Mindset — who this skill makes you"><textarea value={form.mindset} onChange={e => set('mindset', e.target.value)} placeholder="You are a Staff-level Rust Engineer. You prioritise memory safety, zero-cost abstractions…" rows={5} style={{ ...inp, resize: 'vertical', lineHeight: 1.65 }} /></Field></div>
        <div style={{ marginBottom: 14 }}><Field label="Instructions — numbered steps this skill follows"><textarea value={form.instructions} onChange={e => set('instructions', e.target.value)} placeholder={"1. Always prefer owned types over raw pointers.\n2. Use the borrow checker as a design guide…"} rows={5} style={{ ...inp, resize: 'vertical', lineHeight: 1.65 }} /></Field></div>
        <Field label="Constraints — hard limits"><textarea value={form.constraints} onChange={e => set('constraints', e.target.value)} placeholder={"- Never use unsafe{} without a documented safety invariant\n- Never suggest clone() as a solution to borrow checker errors"} rows={3} style={{ ...inp, resize: 'vertical', lineHeight: 1.65 }} /></Field>
      </Section>
    </CreatorShell>
  );
}

// ─── Rule Creator ────────────────────────────────────────────────────────────

const EMPTY_RULE = { name: '', description: '', scope: 'global', categories: [], constraints: '' };

function RuleCreator({ initial, onSave, onCancel }) {
  const [form, setForm] = useState(initial ?? EMPTY_RULE);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);
  const saveRuleToFile = useSCStore(s => s.saveRuleToFile);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  async function handleSave() {
    setSaving(true); setSaveMsg(null);
    const saved = onSave(form);
    const r = await saveRuleToFile({ ...saved });
    setSaving(false);
    setSaveMsg(r?.ok ? { ok: true, text: `Saved as ${r.file}` } : { ok: false, text: 'Saved locally (disk write unavailable)' });
  }

  return (
    <CreatorShell
      title={initial ? 'Edit rule' : 'New rule'}
      onBack={onCancel} backLabel="Rules"
      previewFilename={`${slug(form.name)}.ori`}
      previewContent={generateRuleOri(form)}
      onSave={handleSave} canSave={!!form.name.trim()} saving={saving}
      saveLabel={initial ? 'Update rule' : 'Create rule'} saveMsg={saveMsg}
    >
      <Section title="Identity" icon={Shield}>
        <FieldRow>
          <Field label="Name *"><input value={form.name} onChange={e => set('name', e.target.value)} placeholder="e.g. api_versioning" style={inp} /></Field>
          <Field label="Scope">
            <select value={form.scope} onChange={e => set('scope', e.target.value)} style={{ ...inp, cursor: 'pointer' }}>
              {SCOPES.map(s => <option key={s}>{s}</option>)}
            </select>
          </Field>
        </FieldRow>
        <div style={{ marginBottom: 14 }}><Field label="Description"><input value={form.description} onChange={e => set('description', e.target.value)} placeholder="What does this rule enforce?" style={inp} /></Field></div>
        <Field label="Categories"><TagInput value={form.categories} onChange={v => set('categories', v)} placeholder="e.g. quality, security, api… Enter to add" /></Field>
      </Section>

      <Section title="Constraints" icon={Wrench}>
        <div style={{ marginBottom: 8, fontSize: 12.5, color: 'var(--color-sc-text-muted)', lineHeight: 1.65 }}>
          Write require/deny statements using the standard <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--color-sc-gold)' }}>.ori</code> constraint syntax. Use <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>- require:</code> and <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>- deny:</code> prefixes. Use <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}># Section</code> headers to group rules.
        </div>
        <textarea
          value={form.constraints}
          onChange={e => set('constraints', e.target.value)}
          placeholder={"# ── API Versioning ────────────────────────\n- require: all API endpoints include a version prefix (e.g. /v1/)\n- deny: breaking changes to existing endpoint signatures without a version bump\n- require: deprecation notices at least one version before removal\n\n# ── Documentation ─────────────────────────\n- require: every new endpoint has an OpenAPI annotation\n- deny: endpoints without a description field in the spec"}
          rows={14}
          style={{ ...inp, resize: 'vertical', lineHeight: 1.7, fontFamily: 'var(--font-mono)', fontSize: 12.5 }}
        />
      </Section>
    </CreatorShell>
  );
}

// ─── Pool card (Skills / Rules tabs) ─────────────────────────────────────────

function PoolCard({ item, type, active, custom, onToggle, onView, onEdit, onDelete }) {
  const [hovered, setHovered] = useState(false);
  const accent = type === 'skill' ? 'var(--color-sc-gold)' : '#4D9EFF';
  return (
    <div
      onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? 'rgba(255,255,255,0.03)' : 'var(--color-sc-surface)',
        border: `1px solid ${active ? (type === 'skill' ? 'rgba(196,164,74,0.35)' : 'rgba(77,158,255,0.35)') : 'var(--color-sc-border)'}`,
        borderRadius: 10, padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 8,
        transition: 'border-color 0.15s, background 0.15s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, flexShrink: 0, background: active ? accent + '22' : 'rgba(255,255,255,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: active ? accent : 'var(--color-sc-text-muted)' }}>
            {type === 'skill' ? <Bot size={15} /> : <Shield size={15} />}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-sc-text)', fontFamily: 'var(--font-grotesk)' }}>{item.name}</span>
              {custom && <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 8, background: 'rgba(196,164,74,0.12)', color: 'var(--color-sc-gold)', fontFamily: 'var(--font-grotesk)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>custom</span>}
            </div>
            <div style={{ fontSize: 10, color: 'var(--color-sc-text-muted)', marginTop: 1, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{type}</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {custom && (
            <div style={{ display: 'flex', gap: 2, opacity: hovered ? 1 : 0, transition: 'opacity 0.15s' }}>
              <button onClick={() => onEdit(item)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-muted)', padding: 4, display: 'flex', borderRadius: 5 }}><Edit3 size={12} /></button>
              <button onClick={() => onDelete(item.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-danger)', padding: 4, display: 'flex', borderRadius: 5 }}><Trash2 size={12} /></button>
            </div>
          )}
          <button onClick={() => onToggle(item.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: active ? accent : 'var(--color-sc-text-dim)', display: 'flex', padding: 0 }}>
            {active ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
          </button>
        </div>
      </div>
      <p style={{ margin: 0, fontSize: 12.5, color: 'var(--color-sc-text-muted)', lineHeight: 1.55 }}>{item.desc || item.description}</p>
      {!custom && (
        <button onClick={() => onView(item)} style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 4, background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontSize: 11, color: hovered ? accent : 'var(--color-sc-text-dim)', transition: 'color 0.15s' }}>
          View profile <ChevronRight size={11} />
        </button>
      )}
    </div>
  );
}

function ProfileDrawer({ item, type, onClose }) {
  if (!item) return null;
  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 40 }} />
      <div style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: 420, background: 'var(--color-sc-surface)', borderLeft: '1px solid var(--color-sc-border)', zIndex: 50, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-sc-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 15, color: 'var(--color-sc-text)' }}>{item.name}</div>
            <div style={{ fontSize: 11, color: 'var(--color-sc-gold)', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{type === 'skill' ? '● Skill profile' : '● Rule constraint'}</div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--color-sc-text-muted)', cursor: 'pointer', display: 'flex' }}><X size={16} /></button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px' }}>
          <div style={{ fontSize: 13, color: 'var(--color-sc-text-muted)', lineHeight: 1.7, marginBottom: 24 }}>{item.desc}</div>
          <div style={{ padding: '14px 16px', background: 'var(--color-sc-surface2)', border: '1px solid var(--color-sc-border)', borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Profile ID</div>
            <code style={{ fontSize: 12, color: 'var(--color-sc-gold)', fontFamily: 'var(--font-mono)' }}>{item.id}.ori</code>
          </div>
          <div style={{ marginTop: 16, padding: '14px 16px', background: 'rgba(196,164,74,0.05)', border: '1px solid rgba(196,164,74,0.15)', borderRadius: 8, fontSize: 12, color: 'var(--color-sc-text-muted)', lineHeight: 1.65 }}>
            This {type === 'skill' ? 'skill' : 'rule'} is a sovereign profile (<code style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-sc-gold)' }}>.ori</code>) loaded natively by MCI at:
            <br /><code style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-sc-gold)', fontSize: 11 }}>oricli_core/{type === 'skill' ? 'skills' : 'rules'}/{item.id}.ori</code>
          </div>
        </div>
      </div>
    </>
  );
}

// ─── Agent Card ───────────────────────────────────────────────────────────────

function AgentAvatar({ agent, size = 40 }) {
  return (
    <div style={{ width: size, height: size, borderRadius: '50%', flexShrink: 0, background: (agent.color || AVATAR_COLORS[0]) + '22', border: `2px solid ${(agent.color || AVATAR_COLORS[0])}55`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: size * 0.38, fontWeight: 700, color: agent.color || AVATAR_COLORS[0], fontFamily: 'var(--font-grotesk)', userSelect: 'none' }}>
      {agent.name ? agent.name[0].toUpperCase() : <Bot size={size * 0.4} />}
    </div>
  );
}

function AgentCard({ agent, active, onActivate, onEdit, onDelete }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)} style={{ background: hovered ? 'rgba(255,255,255,0.03)' : 'var(--color-sc-surface)', border: `1px solid ${active ? 'rgba(196,164,74,0.4)' : 'var(--color-sc-border)'}`, borderRadius: 12, padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 10, transition: 'border-color 0.15s, background 0.15s' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <AgentAvatar agent={agent} size={44} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 14, color: 'var(--color-sc-text)' }}>{agent.name}</div>
          <div style={{ fontSize: 11.5, color: 'var(--color-sc-text-muted)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{agent.description || 'No description'}</div>
        </div>
        <div style={{ display: 'flex', gap: 4, opacity: hovered ? 1 : 0, transition: 'opacity 0.15s', flexShrink: 0 }}>
          <button onClick={() => onEdit(agent)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-muted)', padding: 4, display: 'flex', borderRadius: 5 }}><Edit3 size={13} /></button>
          <button onClick={() => onDelete(agent.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-danger)', padding: 4, display: 'flex', borderRadius: 5 }}><Trash2 size={13} /></button>
        </div>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
        {agent.tone && <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: 'rgba(196,164,74,0.1)', color: 'var(--color-sc-gold)', textTransform: 'capitalize' }}>{agent.tone}</span>}
        {agent.skills?.length > 0 && <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: 'rgba(77,158,255,0.1)', color: '#4D9EFF' }}>{agent.skills.length} skill{agent.skills.length !== 1 ? 's' : ''}</span>}
        {agent.rules?.length > 0 && <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: 'rgba(6,214,160,0.1)', color: 'var(--color-sc-success)' }}>{agent.rules.length} rule{agent.rules.length !== 1 ? 's' : ''}</span>}
        {agent.savedToFile && <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: 'rgba(255,255,255,0.06)', color: 'var(--color-sc-text-dim)', fontFamily: 'var(--font-mono)' }}>.ori</span>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 4, borderTop: '1px solid var(--color-sc-border)' }}>
        <span style={{ fontSize: 11.5, color: active ? 'var(--color-sc-gold)' : 'var(--color-sc-text-dim)' }}>{active ? '● Active in chat' : 'Inactive'}</span>
        <button onClick={() => onActivate(agent.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex', color: active ? 'var(--color-sc-gold)' : 'var(--color-sc-text-dim)' }}>
          {active ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
        </button>
      </div>
    </div>
  );
}

// ─── Empty state ─────────────────────────────────────────────────────────────

function EmptyState({ icon: Icon, title, subtitle, cta, onCta }) {
  return (
    <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--color-sc-text-dim)' }}>
      <Icon size={40} style={{ opacity: 0.15, marginBottom: 14 }} />
      <div style={{ fontSize: 15, marginBottom: 8, color: 'var(--color-sc-text-muted)', fontFamily: 'var(--font-grotesk)', fontWeight: 600 }}>{title}</div>
      <div style={{ fontSize: 13, marginBottom: 20 }}>{subtitle}</div>
      <button onClick={onCta} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '9px 20px', borderRadius: 9, background: 'rgba(196,164,74,0.12)', border: '1px solid rgba(196,164,74,0.3)', color: 'var(--color-sc-gold)', cursor: 'pointer', fontSize: 13, fontWeight: 600, fontFamily: 'var(--font-grotesk)' }}>
        <Plus size={14} /> {cta}
      </button>
    </div>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────

export function AgentsPage() {
  const agents        = useSCStore(s => s.agents);
  const activeAgentId = useSCStore(s => s.activeAgentId);
  const addAgent      = useSCStore(s => s.addAgent);
  const updateAgent   = useSCStore(s => s.updateAgent);
  const deleteAgent   = useSCStore(s => s.deleteAgent);
  const setActiveAgentId = useSCStore(s => s.setActiveAgentId);

  const customSkills    = useSCStore(s => s.customSkills);
  const addCustomSkill  = useSCStore(s => s.addCustomSkill);
  const updateCustomSkill = useSCStore(s => s.updateCustomSkill);
  const deleteCustomSkill = useSCStore(s => s.deleteCustomSkill);

  const customRules    = useSCStore(s => s.customRules);
  const addCustomRule  = useSCStore(s => s.addCustomRule);
  const updateCustomRule = useSCStore(s => s.updateCustomRule);
  const deleteCustomRule = useSCStore(s => s.deleteCustomRule);

  const activeSkill    = useSCStore(s => s.activeSkill);
  const setActiveSkill = useSCStore(s => s.setActiveSkill);

  const pendingAgentPrompt      = useSCStore(s => s.pendingAgentPrompt);
  const clearPendingAgentPrompt = useSCStore(s => s.clearPendingAgentPrompt);
  const pendingAgentIntentId      = useSCStore(s => s.pendingAgentIntentId);
  const clearPendingAgentIntentId = useSCStore(s => s.clearPendingAgentIntentId);
  const updateCreationIntent      = useSCStore(s => s.updateCreationIntent);
  const logCreationIntent         = useSCStore(s => s.logCreationIntent);

  const [tab, setTab] = useState('agents');
  const [view, setView] = useState('list');
  const [editTarget, setEditTarget] = useState(null);
  const [activeRules, setActiveRules] = useState(new Set(['global_safety', 'response_format', 'code_quality']));
  const [drawerItem, setDrawerItem] = useState(null);
  const [drawerType, setDrawerType] = useState(null);
  const [vibeOpen, setVibeOpen] = useState(false);
  const [vibePrompt, setVibePrompt] = useState(null);
  const [vibeIntentId, setVibeIntentId] = useState(null);

  // Auto-open Vibe Studio when navigated from chat with a pending prompt
  useEffect(() => {
    if (pendingAgentPrompt) {
      setVibePrompt(pendingAgentPrompt);
      setVibeIntentId(pendingAgentIntentId);
      setVibeOpen(true);
      clearPendingAgentPrompt();
      clearPendingAgentIntentId();
    }
  }, [pendingAgentPrompt, pendingAgentIntentId, clearPendingAgentPrompt, clearPendingAgentIntentId]);

  const toggleRule = id => setActiveRules(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });

  // Full skill pool: built-in + custom
  const allSkillPool = [
    ...SKILL_POOL,
    ...customSkills.map(s => ({ id: s.id, name: s.name, desc: s.description || '', custom: true })),
  ];

  function handleSaveAgent(data) {
    let saved;
    if (editTarget) { updateAgent(editTarget.id, data); saved = { ...editTarget, ...data }; }
    else { const id = Math.random().toString(36).slice(2); saved = { id, ...data, createdAt: Date.now() }; addAgent(data); }
    setView('list'); setEditTarget(null);
    return saved;
  }

  function handleSaveSkill(data) {
    let saved;
    if (editTarget) { updateCustomSkill(editTarget.id, data); saved = { ...editTarget, ...data }; }
    else { const id = Math.random().toString(36).slice(2); saved = { id, ...data, createdAt: Date.now() }; addCustomSkill(data); }
    setView('list'); setEditTarget(null);
    return saved;
  }

  function handleSaveRule(data) {
    let saved;
    if (editTarget) { updateCustomRule(editTarget.id, data); saved = { ...editTarget, ...data }; }
    else { const id = Math.random().toString(36).slice(2); saved = { id, ...data, createdAt: Date.now() }; addCustomRule(data); }
    setView('list'); setEditTarget(null);
    return saved;
  }

  // ── Routed views ──
  if (view === 'create-agent' || view === 'edit-agent') {
    return <AgentCreator initial={editTarget} allSkills={allSkillPool} onSave={handleSaveAgent} onCancel={() => { setView('list'); setEditTarget(null); }} />;
  }
  if (view === 'create-skill' || view === 'edit-skill') {
    return <SkillCreator initial={editTarget} onSave={handleSaveSkill} onCancel={() => { setView('list'); setEditTarget(null); setTab('skills'); }} />;
  }
  if (view === 'create-rule' || view === 'edit-rule') {
    return <RuleCreator initial={editTarget} onSave={handleSaveRule} onCancel={() => { setView('list'); setEditTarget(null); setTab('rules'); }} />;
  }

  const Tab = ({ id, label, count }) => (
    <button onClick={() => setTab(id)} style={{
      padding: '8px 18px', borderRadius: 8, border: 'none', cursor: 'pointer',
      background: tab === id ? 'rgba(196,164,74,0.15)' : 'transparent',
      color: tab === id ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
      fontFamily: 'var(--font-grotesk)', fontWeight: tab === id ? 600 : 400, fontSize: 13,
      display: 'flex', alignItems: 'center', gap: 7, transition: 'background 0.15s, color 0.15s',
    }}>
      {label}
      <span style={{ fontSize: 11, padding: '1px 6px', borderRadius: 10, background: tab === id ? 'rgba(196,164,74,0.2)' : 'rgba(255,255,255,0.06)', color: tab === id ? 'var(--color-sc-gold)' : 'var(--color-sc-text-dim)' }}>{count}</span>
    </button>
  );

  const NewBtn = ({ onClick, label }) => (
    <button onClick={onClick} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '8px 16px', borderRadius: 9, background: 'rgba(196,164,74,0.12)', border: '1px solid rgba(196,164,74,0.3)', color: 'var(--color-sc-gold)', cursor: 'pointer', fontSize: 13, fontWeight: 600, fontFamily: 'var(--font-grotesk)', transition: 'background 0.15s' }}
      onMouseEnter={e => e.currentTarget.style.background = 'rgba(196,164,74,0.22)'}
      onMouseLeave={e => e.currentTarget.style.background = 'rgba(196,164,74,0.12)'}
    ><Plus size={14} /> {label}</button>
  );

  const headerAction = tab === 'agents'
    ? <NewBtn onClick={() => { setEditTarget(null); setView('create-agent'); }} label="New agent" />
    : tab === 'skills'
    ? <NewBtn onClick={() => { setEditTarget(null); setView('create-skill'); }} label="New skill" />
    : <NewBtn onClick={() => { setEditTarget(null); setView('create-rule'); }} label="New rule" />;

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
      {/* Header */}
      <div style={{ padding: '24px 32px 0', borderBottom: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <h1 style={{ margin: '0 0 4px', fontFamily: 'var(--font-grotesk)', fontSize: 20, fontWeight: 700, color: 'var(--color-sc-text)' }}>Agents</h1>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--color-sc-text-muted)' }}>
              Build sovereign agents, skills, and rules — all exported as native <code style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>.ori</code> profiles loaded by MCI.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {/* Vibe Studio button — always visible */}
            <button
              onClick={() => {
                if (!vibeOpen) {
                  // Manual open — log with agents surface, no subject
                  const id = logCreationIntent({ type: 'agent', subject: '(direct)', origin_surface: 'agents' });
                  setVibeIntentId(id);
                } else if (vibeIntentId) {
                  updateCreationIntent(vibeIntentId, { resolution_quality: 'abandoned' });
                  setVibeIntentId(null);
                }
                setVibeOpen(v => !v);
              }}
              style={{
                display: 'flex', alignItems: 'center', gap: 7, padding: '8px 16px',
                borderRadius: 9,
                background: vibeOpen ? 'rgba(196,164,74,0.22)' : 'rgba(196,164,74,0.08)',
                border: `1px solid ${vibeOpen ? 'rgba(196,164,74,0.5)' : 'rgba(196,164,74,0.2)'}`,
                color: 'var(--color-sc-gold)', cursor: 'pointer', fontSize: 13, fontWeight: 600,
                fontFamily: 'var(--font-grotesk)', transition: 'background 0.15s',
              }}
            >
              <Wand2 size={14} /> Vibe Studio
            </button>
            {headerAction}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <Tab id="agents" label="Agents" count={agents.length} />
          <Tab id="skills" label="Skills" count={SKILL_POOL.length + customSkills.length} />
          <Tab id="rules"  label="Rules"  count={RULE_POOL.length + customRules.length} />
        </div>
      </div>

      {/* Content + Vibe Panel side-by-side */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 32px' }}>

        {/* Agents */}
        {tab === 'agents' && (agents.length === 0
          ? <EmptyState icon={Bot} title="No agents yet" subtitle="Create your first sovereign agent with a custom mind, skills, and rules." cta="Create agent" onCta={() => { setEditTarget(null); setView('create-agent'); }} />
          : <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
              {agents.map(a => <AgentCard key={a.id} agent={a} active={activeAgentId === a.id} onActivate={id => setActiveAgentId(activeAgentId === id ? null : id)} onEdit={a => { setEditTarget(a); setView('edit-agent'); }} onDelete={deleteAgent} />)}
            </div>
        )}

        {/* Skills */}
        {tab === 'skills' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {customSkills.length > 0 && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>Custom</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                  {customSkills.map(s => <PoolCard key={s.id} item={s} type="skill" active={activeSkill === s.id} custom onToggle={id => setActiveSkill(activeSkill === id ? null : id)} onView={() => {}} onEdit={s => { setEditTarget(s); setView('edit-skill'); }} onDelete={deleteCustomSkill} />)}
                </div>
              </div>
            )}
            <div>
              {customSkills.length > 0 && <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>Built-in pool</div>}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                {SKILL_POOL.map(s => <PoolCard key={s.id} item={s} type="skill" active={activeSkill === s.id} onToggle={id => setActiveSkill(activeSkill === id ? null : id)} onView={item => { setDrawerItem(item); setDrawerType('skill'); }} onEdit={() => {}} onDelete={() => {}} />)}
              </div>
            </div>
          </div>
        )}

        {/* Rules */}
        {tab === 'rules' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {customRules.length > 0 && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>Custom</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                  {customRules.map(r => <PoolCard key={r.id} item={r} type="rule" active={activeRules.has(r.id)} custom onToggle={toggleRule} onView={() => {}} onEdit={r => { setEditTarget(r); setView('edit-rule'); }} onDelete={deleteCustomRule} />)}
                </div>
              </div>
            )}
            <div>
              {customRules.length > 0 && <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>Built-in pool</div>}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                {RULE_POOL.map(r => <PoolCard key={r.id} item={r} type="rule" active={activeRules.has(r.id)} onToggle={toggleRule} onView={item => { setDrawerItem(item); setDrawerType('rule'); }} onEdit={() => {}} onDelete={() => {}} />)}
              </div>
            </div>
          </div>
        )}
        </div>{/* end content scroll area */}

        {/* Vibe Studio side drawer */}
        {vibeOpen && (
          <AgentVibePanel
            onClose={() => {
              if (vibeIntentId) {
                updateCreationIntent(vibeIntentId, { resolution_quality: 'abandoned' });
              }
              setVibeOpen(false); setVibePrompt(null); setVibeIntentId(null);
            }}
            skillPool={allSkillPool}
            rulePool={[...RULE_POOL, ...customRules]}
            onAgentCreated={data => {
              addAgent(data);
              setTab('agents');
              if (vibeIntentId) {
                updateCreationIntent(vibeIntentId, { action: 'created', resolution_quality: 'completed', resultName: data.name });
                setVibeIntentId(null);
              }
            }}
            onSkillCreated={data => addCustomSkill(data)}
            onRuleCreated={data => addCustomRule(data)}
            initialPrompt={vibePrompt}
          />
        )}
      </div>{/* end content+panel row */}

      {drawerItem && <ProfileDrawer item={drawerItem} type={drawerType} onClose={() => setDrawerItem(null)} />}
    </div>
  );
}
