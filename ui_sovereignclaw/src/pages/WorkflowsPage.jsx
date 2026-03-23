import { useState, useEffect, useCallback, useRef } from 'react';
import { useSCStore } from '../store';
import {
  Plus, Play, Trash2, ArrowDown, Zap, Globe, Code2, Brain, Search,
  FileText, X, Clock, Calendar, RotateCcw, CheckCircle, AlertCircle,
  Loader, Bot, ChevronDown, ListTodo, ChevronRight, ChevronUp,
  Database, Bell, Filter, Edit3, Save, History, Sparkles,
  Layers, ChevronsDown, ChevronsUp, StopCircle, GitBranch
} from 'lucide-react';

// ─── Step type catalog ───────────────────────────────────────────────────────
const STEP_TYPES = [
  { id: 'prompt',       label: 'AI Prompt',      Icon: Brain,      desc: 'Send a message to the agent', placeholder: 'Write a summary of {{output}}' },
  { id: 'summarize',    label: 'Summarize',      Icon: Sparkles,   desc: 'Condense the previous output', placeholder: 'Focus on key insights and action items' },
  { id: 'transform',    label: 'Transform',      Icon: Edit3,      desc: 'Reshape previous output with an instruction', placeholder: 'Convert to bullet-point format' },
  { id: 'extract',      label: 'Extract',        Icon: Filter,     desc: 'Pull structured data from previous output', placeholder: 'Extract names, dates, and URLs as JSON' },
  { id: 'web',          label: 'Web Search',     Icon: Globe,      desc: 'Search the web for information', placeholder: 'Latest news about {{output}}' },
  { id: 'fetch_url',    label: 'Fetch URL',      Icon: Search,     desc: 'Retrieve content from a URL', placeholder: 'https://example.com/page' },
  { id: 'rag_query',    label: 'Knowledge',      Icon: Database,   desc: 'Query the agent knowledge base', placeholder: 'What do we know about {{output}}?' },
  { id: 'code',         label: 'Run Code',       Icon: Code2,      desc: 'Execute Python (input_text = previous output)', placeholder: 'result = input_text.upper()' },
  { id: 'condition',    label: 'Condition',      Icon: Filter,     desc: 'Evaluate a condition on previous output', placeholder: 'Does the output mention pricing?' },
  { id: 'notify',       label: 'Notify',         Icon: Bell,       desc: 'Send notification via a connection', placeholder: 'discord: {{output}}' },
  { id: 'template',     label: 'Template',       Icon: FileText,   desc: 'Fill a text template with prior outputs', placeholder: 'Report:\n\nSummary: {{step_0_output}}\n\nDetails: {{output}}' },
  { id: 'sub_workflow', label: 'Run Workflow',   Icon: GitBranch,  desc: 'Trigger another workflow and chain its output', placeholder: '' },
];

const STEP_BY_ID = Object.fromEntries(STEP_TYPES.map(s => [s.id, s]));

// ─── Schedule constants (reused for Tasks) ──────────────────────────────────
const SCHEDULE_TYPES = [
  { id: 'manual', label: 'Manual',   Icon: Play },
  { id: 'once',   label: 'Once',     Icon: Calendar },
  { id: 'cron',   label: 'Cron',     Icon: Clock },
];
const CRON_PRESETS = [
  { label: 'Every hour',        value: '0 * * * *' },
  { label: 'Every day at 9am',  value: '0 9 * * *' },
  { label: 'Every Monday 9am',  value: '0 9 * * 1' },
  { label: 'Every day midnight',value: '0 0 * * *' },
];
const TASK_STATUS = {
  idle:    { label: 'Idle',    color: 'var(--color-sc-text-dim)',  Icon: Clock },
  running: { label: 'Running', color: 'var(--color-sc-gold)',       Icon: Loader },
  done:    { label: 'Done',    color: 'var(--color-sc-success)',    Icon: CheckCircle },
  error:   { label: 'Error',   color: 'var(--color-sc-danger)',     Icon: AlertCircle },
};

// ─── Shared styles ──────────────────────────────────────────────────────────
const inputStyle = {
  width: '100%', background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)',
  borderRadius: 8, padding: '9px 12px', color: 'var(--color-sc-text)',
  fontFamily: 'var(--font-inter)', fontSize: 13, outline: 'none', boxSizing: 'border-box',
};
const labelStyle = {
  fontSize: 12, fontWeight: 600, color: 'var(--color-sc-text-muted)',
  fontFamily: 'var(--font-grotesk)', marginBottom: 6, display: 'block',
};
const goldBtn = {
  display: 'flex', alignItems: 'center', gap: 7, padding: '8px 16px', borderRadius: 9,
  background: 'rgba(196,164,74,0.12)', border: '1px solid rgba(196,164,74,0.3)',
  color: 'var(--color-sc-gold)', cursor: 'pointer', fontSize: 13, fontWeight: 600,
  fontFamily: 'var(--font-grotesk)', transition: 'background 0.15s',
};

// ─── AgentPicker ─────────────────────────────────────────────────────────────
function AgentPicker({ value, onChange }) {
  const [agents, setAgents] = useState([]);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    fetch('/agents/list').then(r => r.json()).then(d => setAgents(d.agents || [])).catch(() => {});
  }, []);
  return (
    <div style={{ position: 'relative' }}>
      <button type="button" onClick={() => setOpen(o => !o)} style={{ ...inputStyle, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', padding: '9px 12px' }}>
        <span>{value?.emoji ?? '✨'}</span>
        <span style={{ flex: 1, textAlign: 'left' }}>{value?.name ?? 'Default (Oricli)'}</span>
        <ChevronDown size={12} style={{ opacity: 0.5, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
      </button>
      {open && (
        <div style={{ position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, zIndex: 50, background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.4)', padding: 4, maxHeight: 240, overflowY: 'auto' }}>
          <button type="button" onClick={() => { onChange(null); setOpen(false); }} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', background: !value ? 'rgba(196,164,74,0.08)' : 'transparent', color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 13 }}>
            <span>✨</span> Default (Oricli)
          </button>
          {agents.map(ag => (
            <button key={ag.id} type="button" onClick={() => { onChange(ag); setOpen(false); }} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', background: value?.id === ag.id ? 'rgba(196,164,74,0.08)' : 'transparent', color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 13 }}>
              <span>{ag.emoji}</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 12 }}>{ag.name}</div>
                {ag.description && <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 200 }}>{ag.description}</div>}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── WorkflowPicker (for sub_workflow step type) ─────────────────────────────
function WorkflowPicker({ value, onChange, excludeId }) {
  const [workflows, setWorkflows] = useState([]);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    fetch('/workflows').then(r => r.json()).then(d => setWorkflows(d.workflows || [])).catch(() => {});
  }, []);
  const available = workflows.filter(w => w.id !== excludeId);
  const selected = available.find(w => w.id === value);
  return (
    <div style={{ position: 'relative' }}>
      <button type="button" onClick={() => setOpen(o => !o)} style={{ ...inputStyle, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', padding: '9px 12px' }}>
        <GitBranch size={13} style={{ color: 'var(--color-sc-gold)', flexShrink: 0 }} />
        <span style={{ flex: 1, textAlign: 'left', color: selected ? 'var(--color-sc-text)' : 'var(--color-sc-text-dim)' }}>
          {selected ? selected.name : 'Select a workflow…'}
        </span>
        <ChevronDown size={12} style={{ opacity: 0.5, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
      </button>
      {open && (
        <div style={{ position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, zIndex: 50, background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.4)', padding: 4, maxHeight: 240, overflowY: 'auto' }}>
          {available.length === 0 && (
            <div style={{ padding: '10px 12px', fontSize: 12, color: 'var(--color-sc-text-dim)' }}>No other workflows yet</div>
          )}
          {available.map(wf => (
            <button key={wf.id} type="button" onClick={() => { onChange(wf.id); setOpen(false); }} style={{ width: '100%', display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', background: value === wf.id ? 'rgba(196,164,74,0.08)' : 'transparent', color: 'var(--color-sc-text)', textAlign: 'left' }}>
              <GitBranch size={12} style={{ color: 'var(--color-sc-gold)', marginTop: 2, flexShrink: 0 }} />
              <div>
                <div style={{ fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 600 }}>{wf.name}</div>
                {wf.description && <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)' }}>{wf.description}</div>}
                <div style={{ fontSize: 10, color: 'var(--color-sc-text-dim)', marginTop: 2 }}>{wf.steps?.length ?? 0} steps</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── StepEditor ─────────────────────────────────────────────────────────────
function StepEditor({ step, index, total, onChange, onRemove, parentWfId }) {
  const [showTypePicker, setShowTypePicker] = useState(false);
  const def = STEP_BY_ID[step.type] ?? STEP_TYPES[0];
  const { Icon } = def;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {index > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '2px 0' }}>
          <div style={{ width: 1, height: 12, background: 'var(--color-sc-border)' }} />
          <ArrowDown size={11} style={{ color: 'var(--color-sc-text-dim)', margin: '1px 0' }} />
          <div style={{ width: 1, height: 8, background: 'var(--color-sc-border)' }} />
          <div style={{ fontSize: 10, color: 'var(--color-sc-text-dim)', fontFamily: 'var(--font-mono)', padding: '1px 6px', borderRadius: 4, border: '1px solid var(--color-sc-border)', background: 'var(--color-sc-bg)' }}>
            {'{{output}}'}
          </div>
          <div style={{ width: 1, height: 8, background: 'var(--color-sc-border)' }} />
        </div>
      )}
      <div style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 12, padding: '14px 16px', position: 'relative' }}>
        {/* Step header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <div style={{ width: 22, height: 22, borderRadius: '50%', background: 'rgba(196,164,74,0.15)', color: 'var(--color-sc-gold)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, fontFamily: 'var(--font-grotesk)', flexShrink: 0 }}>
            {index + 1}
          </div>
          <div style={{ position: 'relative', flexShrink: 0 }}>
            <button type="button" onClick={() => setShowTypePicker(p => !p)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px', borderRadius: 7, border: '1px solid rgba(196,164,74,0.3)', background: 'rgba(196,164,74,0.08)', color: 'var(--color-sc-gold)', cursor: 'pointer', fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 600 }}>
              <Icon size={12} /> {def.label} <ChevronDown size={10} style={{ transform: showTypePicker ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
            </button>
            {showTypePicker && (
              <div style={{ position: 'absolute', top: 'calc(100% + 6px)', left: 0, zIndex: 50, background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.5)', padding: 4, minWidth: 200, maxHeight: 280, overflowY: 'auto' }}>
                {STEP_TYPES.map(st => (
                  <button key={st.id} type="button" onClick={() => { onChange({ ...step, type: st.id }); setShowTypePicker(false); }} style={{ width: '100%', display: 'flex', alignItems: 'flex-start', gap: 10, padding: '8px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', background: step.type === st.id ? 'rgba(196,164,74,0.08)' : 'transparent', color: 'var(--color-sc-text)', textAlign: 'left' }}>
                    <st.Icon size={13} style={{ color: 'var(--color-sc-gold)', marginTop: 1, flexShrink: 0 }} />
                    <div>
                      <div style={{ fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 600 }}>{st.label}</div>
                      <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)' }}>{st.desc}</div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
          <input
            value={step.label || ''}
            onChange={e => onChange({ ...step, label: e.target.value })}
            placeholder={`Step ${index + 1} label (optional)`}
            style={{ ...inputStyle, flex: 1, padding: '5px 10px', fontSize: 12 }}
          />
          <button onClick={onRemove} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: 4, display: 'flex', flexShrink: 0 }}>
            <X size={14} />
          </button>
        </div>
        {/* Step value */}
        {step.type === 'sub_workflow' ? (
          <div>
            <WorkflowPicker
              value={step.workflowId || step.value || ''}
              onChange={wfId => onChange({ ...step, workflowId: wfId, value: wfId })}
              excludeId={parentWfId}
            />
            <div style={{ marginTop: 6, fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
              The selected workflow will run with the current <code style={{ background: 'rgba(196,164,74,0.1)', color: 'var(--color-sc-gold)', padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>{'{{output}}'}</code> as its starting context.
              Its final output becomes <code style={{ background: 'rgba(196,164,74,0.1)', color: 'var(--color-sc-gold)', padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>{'{{output}}'}</code> for your next step.
            </div>
          </div>
        ) : (
          <textarea
            value={step.value || ''}
            onChange={e => onChange({ ...step, value: e.target.value })}
            placeholder={def.placeholder}
            rows={step.type === 'code' || step.type === 'template' ? 5 : 2}
            style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.55, fontFamily: step.type === 'code' ? 'var(--font-mono)' : 'var(--font-inter)', fontSize: step.type === 'code' ? 12 : 13 }}
          />
        )}
        {index > 0 && step.type !== 'sub_workflow' && (
          <div style={{ marginTop: 6, fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
            Use <code style={{ background: 'rgba(196,164,74,0.1)', color: 'var(--color-sc-gold)', padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>{'{{output}}'}</code> for previous step output,{' '}
            <code style={{ background: 'rgba(196,164,74,0.1)', color: 'var(--color-sc-gold)', padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>{'{{step_0_output}}'}</code> etc. for specific steps.
          </div>
        )}
      </div>
    </div>
  );
}

// ─── WorkflowCreator ─────────────────────────────────────────────────────────
function WorkflowCreator({ onSave, onCancel, initial }) {
  const [name, setName]         = useState(initial?.name || '');
  const [desc, setDesc]         = useState(initial?.description || '');
  const [agent, setAgent]       = useState(initial ? { id: initial.agentId, name: initial.agentName, emoji: initial.agentEmoji } : null);
  const [steps, setSteps]       = useState(initial?.steps?.length ? initial.steps : [{ id: crypto.randomUUID(), type: 'prompt', label: '', value: '' }]);
  const [saving, setSaving]     = useState(false);

  function addStep() {
    setSteps(s => [...s, { id: crypto.randomUUID(), type: 'prompt', label: '', value: '' }]);
  }
  function updateStep(idx, s) { setSteps(prev => prev.map((x, i) => i === idx ? s : x)); }
  function removeStep(idx)    { setSteps(prev => prev.filter((_, i) => i !== idx)); }

  async function handleSave() {
    if (!name.trim() || steps.length === 0) return;
    setSaving(true);
    try {
      const payload = {
        name: name.trim(), description: desc.trim(),
        agentId: agent?.id || null, agentName: agent?.name || 'Default', agentEmoji: agent?.emoji || '✨',
        steps,
      };
      const method = initial?.id ? 'PUT' : 'POST';
      const url = initial?.id ? `/workflows/${initial.id}` : '/workflows';
      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const data = await res.json();
      onSave(data.workflow || payload);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ background: 'var(--color-sc-surface)', border: '1px solid rgba(196,164,74,0.25)', borderRadius: 14, padding: '22px 24px', marginBottom: 20 }}>
      <h3 style={{ margin: '0 0 18px', fontFamily: 'var(--font-grotesk)', fontSize: 15, fontWeight: 700, color: 'var(--color-sc-text)' }}>
        {initial?.id ? 'Edit Workflow' : 'New Workflow'}
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
        <div>
          <label style={labelStyle}>Workflow name</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Daily market brief" style={inputStyle} />
        </div>
        <div>
          <label style={labelStyle}>Agent</label>
          <AgentPicker value={agent} onChange={setAgent} />
        </div>
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={labelStyle}>Description (optional)</label>
        <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="What does this workflow do?" style={inputStyle} />
      </div>

      <label style={{ ...labelStyle, marginBottom: 12 }}>Steps</label>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0, marginBottom: 14 }}>
        {steps.map((step, idx) => (
          <StepEditor key={step.id} step={step} index={idx} total={steps.length}
            onChange={s => updateStep(idx, s)} onRemove={() => removeStep(idx)}
            parentWfId={initial?.id} />
        ))}
      </div>

      <button type="button" onClick={addStep} style={{ ...goldBtn, padding: '7px 14px', fontSize: 12, marginBottom: 20, background: 'transparent', border: '1px dashed rgba(196,164,74,0.3)' }}>
        <Plus size={12} /> Add step
      </button>

      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
        <button onClick={onCancel} style={{ padding: '8px 18px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'transparent', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontFamily: 'var(--font-inter)', fontSize: 13 }}>Cancel</button>
        <button onClick={handleSave} disabled={!name.trim() || steps.length === 0 || saving}
          style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: name.trim() ? 'var(--color-sc-gold)' : 'rgba(255,255,255,0.06)', color: name.trim() ? '#0D0D0D' : 'var(--color-sc-text-dim)', cursor: name.trim() ? 'pointer' : 'default', fontFamily: 'var(--font-grotesk)', fontSize: 13, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
          {saving ? <><Loader size={12} style={{ animation: 'spin 1s linear infinite' }} /> Saving…</> : <><Save size={12} /> Save workflow</>}
        </button>
      </div>
    </div>
  );
}

// ─── Shared helpers ──────────────────────────────────────────────────────────
const STATUS_COLOR = { queued: 'var(--color-sc-text-dim)', running: 'var(--color-sc-gold)', done: 'var(--color-sc-success)', error: 'var(--color-sc-danger)' };

function StepStatusIcon({ s }) {
  if (s === 'running') return <Loader size={12} style={{ animation: 'spin 1s linear infinite', color: 'var(--color-sc-gold)' }} />;
  if (s === 'done')    return <CheckCircle size={12} style={{ color: 'var(--color-sc-success)' }} />;
  if (s === 'error')   return <AlertCircle size={12} style={{ color: 'var(--color-sc-danger)' }} />;
  return <div style={{ width: 12, height: 12, borderRadius: '50%', border: '1px solid var(--color-sc-border)', flexShrink: 0 }} />;
}

// ─── RunHistoryDrawer ────────────────────────────────────────────────────────
function RunHistoryDrawer({ wf, onClose }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(null);

  useEffect(() => {
    fetch(`/workflows/${wf.id}/runs`)
      .then(r => r.json())
      .then(d => { setRuns(d.runs || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [wf.id]);

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 200, background: 'rgba(8,8,16,0.75)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 16, width: '100%', maxWidth: 700, maxHeight: '80vh', display: 'flex', flexDirection: 'column', boxShadow: '0 24px 80px rgba(0,0,0,0.6)' }}>
        <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--color-sc-border)', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          <History size={15} style={{ color: 'var(--color-sc-gold)' }} />
          <div style={{ flex: 1, fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 14, color: 'var(--color-sc-text)' }}>Run History — {wf.name}</div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-muted)', padding: 4 }}><X size={16} /></button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 22px' }}>
          {loading && <div style={{ color: 'var(--color-sc-text-dim)', fontSize: 13 }}>Loading…</div>}
          {!loading && runs.length === 0 && <div style={{ color: 'var(--color-sc-text-dim)', fontSize: 13 }}>No runs yet.</div>}
          {runs.map(r => (
            <div key={r.id} style={{ marginBottom: 10, border: '1px solid var(--color-sc-border)', borderRadius: 10, overflow: 'hidden' }}>
              <button type="button" onClick={() => setActive(active === r.id ? null : r.id)}
                style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', background: 'none', border: 'none', cursor: 'pointer' }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLOR[r.status] ?? 'var(--color-sc-border)', flexShrink: 0 }} />
                <span style={{ flex: 1, fontFamily: 'var(--font-grotesk)', fontSize: 13, fontWeight: 600, color: 'var(--color-sc-text)', textAlign: 'left' }}>{r.status.toUpperCase()}</span>
                <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', fontFamily: 'var(--font-mono)' }}>{new Date(r.created).toLocaleString()}</span>
                {active === r.id ? <ChevronUp size={12} style={{ color: 'var(--color-sc-text-dim)' }} /> : <ChevronRight size={12} style={{ color: 'var(--color-sc-text-dim)' }} />}
              </button>
              {active === r.id && r.final_output && (
                <div style={{ padding: '0 14px 12px', borderTop: '1px solid var(--color-sc-border)' }}>
                  <pre style={{ margin: '10px 0 0', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--color-sc-text)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.65, background: 'rgba(0,0,0,0.2)', borderRadius: 8, padding: '10px 12px', maxHeight: 240, overflowY: 'auto' }}>
                    {r.final_output}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── ActiveRunsTray ──────────────────────────────────────────────────────────
// Bottom panel showing all in-flight and recently completed workflow runs.
// Each run is independently polled. Multiple can execute in parallel.
function ActiveRunsTray({ bgRuns, workflows, onDismiss, onDismissAll, onRerun }) {
  const [collapsed, setCollapsed] = useState(false);
  const [expandedRun, setExpandedRun] = useState({});
  const [expandedStep, setExpandedStep] = useState({});

  const runList = Object.values(bgRuns).sort((a, b) => (b.startedAt ?? 0) - (a.startedAt ?? 0));
  if (runList.length === 0) return null;

  const activeCount = runList.filter(r => r.run?.status === 'running' || r.run?.status === 'queued' || !r.run).length;

  return (
    <div style={{
      position: 'sticky', bottom: 0, left: 0, right: 0, zIndex: 100,
      background: 'var(--color-sc-surface)', borderTop: '1px solid var(--color-sc-border)',
      boxShadow: '0 -8px 32px rgba(0,0,0,0.35)', flexShrink: 0,
    }}>
      {/* Tray header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 20px', cursor: 'pointer', userSelect: 'none' }} onClick={() => setCollapsed(c => !c)}>
        <Layers size={14} style={{ color: 'var(--color-sc-gold)' }} />
        <span style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 13, color: 'var(--color-sc-text)' }}>
          Background Runs
        </span>
        {activeCount > 0 && (
          <span style={{ padding: '2px 8px', borderRadius: 20, background: 'rgba(196,164,74,0.15)', border: '1px solid rgba(196,164,74,0.3)', color: 'var(--color-sc-gold)', fontSize: 11, fontWeight: 700, fontFamily: 'var(--font-grotesk)', display: 'flex', alignItems: 'center', gap: 5 }}>
            <Loader size={9} style={{ animation: 'spin 1s linear infinite' }} />
            {activeCount} running
          </span>
        )}
        <span style={{ padding: '2px 8px', borderRadius: 20, background: 'rgba(255,255,255,0.05)', border: '1px solid var(--color-sc-border)', color: 'var(--color-sc-text-dim)', fontSize: 11, fontFamily: 'var(--font-grotesk)' }}>
          {runList.length} total
        </span>
        <div style={{ flex: 1 }} />
        <button onClick={e => { e.stopPropagation(); onDismissAll(); }}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', fontSize: 11, fontFamily: 'var(--font-inter)', padding: '2px 8px' }}
          title="Dismiss all completed">
          Clear done
        </button>
        {collapsed ? <ChevronsUp size={14} style={{ color: 'var(--color-sc-text-dim)' }} /> : <ChevronsDown size={14} style={{ color: 'var(--color-sc-text-dim)' }} />}
      </div>

      {/* Run list */}
      {!collapsed && (
        <div style={{ maxHeight: 320, overflowY: 'auto', padding: '0 16px 12px' }}>
          {runList.map(({ runId, wfId, run, error }) => {
            const wf = workflows.find(w => w.id === wfId);
            const isExpanded = expandedRun[runId];
            const status = run?.status ?? (error ? 'error' : 'queued');
            const donePct = run?.steps
              ? Math.round((run.steps.filter(s => s.status === 'done').length / run.steps.length) * 100)
              : 0;

            return (
              <div key={runId} style={{ marginBottom: 8, border: `1px solid ${status === 'error' ? 'rgba(255,77,109,0.2)' : status === 'done' ? 'rgba(6,214,160,0.15)' : 'var(--color-sc-border)'}`, borderRadius: 10, overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
                {/* Run row header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px' }}>
                  <StepStatusIcon s={status} />
                  <span style={{ flex: 1, fontFamily: 'var(--font-grotesk)', fontSize: 13, fontWeight: 600, color: 'var(--color-sc-text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {wf?.name ?? wfId}
                  </span>

                  {/* Step progress pills */}
                  {run?.steps && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 3, flexShrink: 0 }}>
                      {run.steps.map((s, i) => (
                        <div key={i} style={{ width: 10, height: 10, borderRadius: 3, background: s.status === 'done' ? 'var(--color-sc-success)' : s.status === 'running' ? 'var(--color-sc-gold)' : s.status === 'error' ? 'var(--color-sc-danger)' : 'var(--color-sc-border)' }} title={`Step ${i+1}: ${s.status}`} />
                      ))}
                    </div>
                  )}

                  {/* Progress percent */}
                  {status === 'running' && run?.steps && (
                    <span style={{ fontSize: 11, color: 'var(--color-sc-gold)', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>{donePct}%</span>
                  )}

                  {/* Status badge */}
                  <span style={{ fontSize: 10, fontWeight: 700, fontFamily: 'var(--font-grotesk)', color: STATUS_COLOR[status] ?? 'var(--color-sc-text-dim)', textTransform: 'uppercase', letterSpacing: '0.07em', flexShrink: 0 }}>
                    {status}
                  </span>

                  {/* Expand toggle */}
                  <button type="button" onClick={() => setExpandedRun(p => ({ ...p, [runId]: !p[runId] }))}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '2px 4px', display: 'flex', flexShrink: 0 }}>
                    {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  </button>

                  {/* Re-run */}
                  {(status === 'done' || status === 'error') && (
                    <button onClick={() => onRerun(wfId, runId)} title="Re-run"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '2px 4px', display: 'flex', flexShrink: 0, transition: 'color 0.12s' }}
                      onMouseEnter={e => e.currentTarget.style.color = 'var(--color-sc-gold)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--color-sc-text-dim)'}>
                      <RotateCcw size={11} />
                    </button>
                  )}

                  {/* Dismiss */}
                  {(status === 'done' || status === 'error') && (
                    <button onClick={() => onDismiss(runId)} title="Dismiss"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '2px 4px', display: 'flex', flexShrink: 0, transition: 'color 0.12s' }}
                      onMouseEnter={e => e.currentTarget.style.color = 'var(--color-sc-danger)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--color-sc-text-dim)'}>
                      <X size={11} />
                    </button>
                  )}
                </div>

                {/* Progress bar */}
                {status === 'running' && run?.steps && (
                  <div style={{ height: 2, background: 'var(--color-sc-border)', margin: '0 12px 8px' }}>
                    <div style={{ height: '100%', background: 'var(--color-sc-gold)', width: `${donePct}%`, transition: 'width 0.4s ease', borderRadius: 2 }} />
                  </div>
                )}

                {/* Expanded step details */}
                {isExpanded && run?.steps && (
                  <div style={{ padding: '0 12px 10px', borderTop: '1px solid var(--color-sc-border)' }}>
                    {run.steps.map((s, idx) => {
                      const def = STEP_BY_ID[wf?.steps?.[idx]?.type] ?? STEP_TYPES[0];
                      const stepKey = `${runId}-${idx}`;
                      const isStepExp = expandedStep[stepKey];
                      return (
                        <div key={idx} style={{ marginTop: 8 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0' }}>
                            <StepStatusIcon s={s.status} />
                            <def.Icon size={11} style={{ color: 'var(--color-sc-text-dim)', flexShrink: 0 }} />
                            <span style={{ flex: 1, fontSize: 12, color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)' }}>
                              {wf?.steps?.[idx]?.label || def.label}
                            </span>
                            {s.output && (
                              <button type="button" onClick={() => setExpandedStep(p => ({ ...p, [stepKey]: !p[stepKey] }))}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '1px 3px', display: 'flex' }}>
                                {isStepExp ? <ChevronUp size={11} /> : <ChevronRight size={11} />}
                              </button>
                            )}
                          </div>
                          {isStepExp && s.output && (
                            <pre style={{ margin: '4px 0 0 20px', fontFamily: 'var(--font-mono)', fontSize: 11, color: s.status === 'error' ? 'var(--color-sc-danger)' : 'var(--color-sc-text)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.6, background: 'rgba(0,0,0,0.25)', borderRadius: 6, padding: '8px 10px', maxHeight: 160, overflowY: 'auto' }}>
                              {s.output}
                            </pre>
                          )}
                        </div>
                      );
                    })}
                    {run.status === 'done' && run.final_output && (
                      <div style={{ marginTop: 10, padding: '10px 12px', background: 'rgba(6,214,160,0.05)', border: '1px solid rgba(6,214,160,0.18)', borderRadius: 8 }}>
                        <div style={{ fontFamily: 'var(--font-grotesk)', fontSize: 11, fontWeight: 700, color: 'var(--color-sc-success)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 5 }}>
                          <CheckCircle size={11} /> Final Output
                        </div>
                        <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--color-sc-text)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.6, maxHeight: 180, overflowY: 'auto' }}>
                          {run.final_output}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── WorkflowCard ────────────────────────────────────────────────────────────
function WorkflowCard({ wf, onDelete, onRun, onEdit, onHistory, activeRun }) {
  const [hovered, setHovered] = useState(false);
  const isRunning = activeRun?.run?.status === 'running' || activeRun?.run?.status === 'queued' || (activeRun && !activeRun.run);
  const donePct = activeRun?.run?.steps
    ? Math.round((activeRun.run.steps.filter(s => s.status === 'done').length / activeRun.run.steps.length) * 100)
    : 0;

  return (
    <div onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      style={{ background: 'var(--color-sc-surface)', border: `1px solid ${isRunning ? 'rgba(196,164,74,0.35)' : hovered ? 'rgba(196,164,74,0.2)' : 'var(--color-sc-border)'}`, borderRadius: 12, padding: '16px 18px', transition: 'border-color 0.15s', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ width: 38, height: 38, borderRadius: 10, background: isRunning ? 'rgba(196,164,74,0.18)' : 'rgba(196,164,74,0.1)', color: 'var(--color-sc-gold)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          {isRunning ? <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Zap size={16} />}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 14, color: 'var(--color-sc-text)', marginBottom: 2 }}>{wf.name}</div>
          {wf.description && <div style={{ fontSize: 12, color: 'var(--color-sc-text-muted)', marginBottom: 6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{wf.description}</div>}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', fontFamily: 'var(--font-grotesk)' }}>
              {wf.steps?.length ?? 0} step{wf.steps?.length !== 1 ? 's' : ''}
            </span>
            {wf.steps?.map((s, i) => {
              const def = STEP_BY_ID[s.type] ?? STEP_TYPES[0];
              return <def.Icon key={i} size={11} style={{ color: 'var(--color-sc-text-dim)' }} />;
            })}
            {wf.agentName && wf.agentName !== 'Default' && (
              <span style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                <span>{wf.agentEmoji}</span>{wf.agentName}
              </span>
            )}
            {isRunning && activeRun.run?.steps && (
              <span style={{ fontSize: 11, color: 'var(--color-sc-gold)', fontFamily: 'var(--font-grotesk)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                <Loader size={9} style={{ animation: 'spin 1s linear infinite' }} />
                {donePct}% — step {activeRun.run.steps.filter(s => s.status === 'done').length + 1}/{activeRun.run.steps.length}
              </span>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
          <button onClick={() => onHistory(wf)} title="Run history" style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '5px 7px', borderRadius: 6, display: 'flex', alignItems: 'center', transition: 'color 0.12s' }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--color-sc-text)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--color-sc-text-dim)'}>
            <History size={13} />
          </button>
          <button onClick={() => onEdit(wf)} title="Edit" style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '5px 7px', borderRadius: 6, display: 'flex', alignItems: 'center', transition: 'color 0.12s' }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--color-sc-gold)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--color-sc-text-dim)'}>
            <Edit3 size={13} />
          </button>
          <button onClick={() => onDelete(wf.id)} title="Delete" style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '5px 7px', borderRadius: 6, display: 'flex', alignItems: 'center', transition: 'color 0.12s' }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--color-sc-danger)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--color-sc-text-dim)'}>
            <Trash2 size={13} />
          </button>
          <button onClick={() => onRun(wf)}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, border: 'none', background: 'var(--color-sc-gold)', color: '#0D0D0D', cursor: 'pointer', fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 700, transition: 'opacity 0.15s' }}
            onMouseEnter={e => e.currentTarget.style.opacity = '0.85'} onMouseLeave={e => e.currentTarget.style.opacity = '1'}>
            <Play size={11} /> Run
          </button>
        </div>
      </div>
      {/* Running progress bar on card bottom */}
      {isRunning && activeRun.run?.steps && (
        <div style={{ marginTop: 12, height: 3, background: 'var(--color-sc-border)', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ height: '100%', background: 'var(--color-sc-gold)', width: `${donePct}%`, transition: 'width 0.5s ease', borderRadius: 2 }} />
        </div>
      )}
    </div>
  );
}

// ─── WorkflowsTab ────────────────────────────────────────────────────────────
function WorkflowsTab({ creating, setCreating }) {
  const [workflows, setWorkflows] = useState([]);
  const [historyWf, setHistoryWf] = useState(null);
  const [editingWf, setEditingWf] = useState(null);

  // bgRuns lives in global store — survives page navigation
  const bgRuns             = useSCStore(s => s.bgRuns);
  const startBgRun         = useSCStore(s => s.startBgRun);
  const dismissBgRun       = useSCStore(s => s.dismissBgRun);
  const dismissAllDoneBgRuns = useSCStore(s => s.dismissAllDoneBgRuns);

  async function refresh() {
    try {
      const r = await fetch('/workflows');
      const d = await r.json();
      setWorkflows(d.workflows || []);
    } catch {}
  }
  useEffect(() => { refresh(); }, []);

  async function handleRun(wf) {
    try {
      const res  = await fetch(`/workflows/${wf.id}/run`, { method: 'POST' });
      const data = await res.json();
      startBgRun(data.run_id, wf.id);
    } catch (e) {
      console.error('Failed to start workflow:', e);
    }
  }

  async function handleRerun(wfId, oldRunId) {
    try {
      dismissBgRun(oldRunId);
      const res  = await fetch(`/workflows/${wfId}/run`, { method: 'POST' });
      const data = await res.json();
      startBgRun(data.run_id, wfId);
    } catch {}
  }

  async function handleDelete(id) {
    await fetch(`/workflows/${id}`, { method: 'DELETE' });
    setWorkflows(prev => prev.filter(w => w.id !== id));
  }

  function handleSave() {
    setCreating(false);
    setEditingWf(null);
    refresh();
  }

  // Map wfId → most recent bgRun for card status indicators
  const activeByWf = {};
  Object.values(bgRuns).forEach(r => {
    if (!activeByWf[r.wfId] || r.startedAt > activeByWf[r.wfId].startedAt) {
      activeByWf[r.wfId] = r;
    }
  });

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 32px' }}>
        {creating && <WorkflowCreator onSave={handleSave} onCancel={() => setCreating(false)} />}
        {editingWf && <WorkflowCreator initial={editingWf} onSave={handleSave} onCancel={() => setEditingWf(null)} />}

        {workflows.length === 0 && !creating && (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--color-sc-text-dim)' }}>
            <Zap size={36} style={{ opacity: 0.2, marginBottom: 12 }} />
            <div style={{ fontSize: 14, marginBottom: 8, color: 'var(--color-sc-text-muted)' }}>No workflows yet</div>
            <div style={{ fontSize: 13 }}>Chain steps together into automated, repeatable pipelines.</div>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {workflows.filter(w => !editingWf || w.id !== editingWf.id).map(wf => (
            <WorkflowCard key={wf.id} wf={wf}
              activeRun={activeByWf[wf.id] ?? null}
              onDelete={handleDelete}
              onRun={handleRun}
              onEdit={w => { setCreating(false); setEditingWf(w); }}
              onHistory={w => setHistoryWf(w)}
            />
          ))}
        </div>
      </div>

      {/* Persistent background runs tray — reads from global store */}
      <ActiveRunsTray
        bgRuns={bgRuns}
        workflows={workflows}
        onDismiss={dismissBgRun}
        onDismissAll={dismissAllDoneBgRuns}
        onRerun={handleRerun}
      />

      {historyWf && <RunHistoryDrawer wf={historyWf} onClose={() => setHistoryWf(null)} />}
    </div>
  );
}

// ─── TasksTab (unchanged) ────────────────────────────────────────────────────
function TaskCreator({ onSave, onCancel }) {
  const [name, setName]             = useState('');
  const [goal, setGoal]             = useState('');
  const [agent, setAgent]           = useState(null);
  const [schedType, setSchedType]   = useState('manual');
  const [schedValue, setSchedValue] = useState('');
  const [saving, setSaving]         = useState(false);

  async function handleSave() {
    if (!goal.trim()) return;
    setSaving(true);
    try {
      const res = await fetch('/tasks', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() || goal.trim().slice(0, 60), goal: goal.trim(), agentId: agent?.id || null, agentName: agent?.name || 'Default', agentEmoji: agent?.emoji || '✨', scheduleType: schedType, scheduleValue: schedValue.trim() }),
      });
      const data = await res.json();
      onSave(data.task);
    } finally { setSaving(false); }
  }

  return (
    <div style={{ background: 'var(--color-sc-surface)', border: '1px solid rgba(196,164,74,0.25)', borderRadius: 14, padding: '22px 24px', marginBottom: 20 }}>
      <h3 style={{ margin: '0 0 20px', fontFamily: 'var(--font-grotesk)', fontSize: 15, fontWeight: 700, color: 'var(--color-sc-text)' }}>New Task</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
        <div><label style={labelStyle}>Task name (optional)</label><input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Daily market summary" style={inputStyle} /></div>
        <div><label style={labelStyle}>Agent</label><AgentPicker value={agent} onChange={setAgent} /></div>
      </div>
      <div style={{ marginBottom: 14 }}>
        <label style={labelStyle}>Goal / instructions</label>
        <textarea value={goal} onChange={e => setGoal(e.target.value)} placeholder="Describe exactly what the agent should do…" rows={3} style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.55 }} />
      </div>
      <div style={{ marginBottom: schedType !== 'manual' ? 14 : 20 }}>
        <label style={labelStyle}>Schedule</label>
        <div style={{ display: 'flex', gap: 8 }}>
          {SCHEDULE_TYPES.map(st => (
            <button key={st.id} type="button" onClick={() => { setSchedType(st.id); setSchedValue(''); }} style={{ flex: 1, padding: '8px 10px', borderRadius: 8, border: `1px solid ${schedType === st.id ? 'rgba(196,164,74,0.5)' : 'var(--color-sc-border)'}`, background: schedType === st.id ? 'rgba(196,164,74,0.1)' : 'var(--color-sc-bg)', color: schedType === st.id ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', cursor: 'pointer', fontFamily: 'var(--font-inter)', fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              <st.Icon size={12} /> {st.label}
            </button>
          ))}
        </div>
      </div>
      {schedType === 'once' && (
        <div style={{ marginBottom: 20 }}><label style={labelStyle}>Run at (UTC)</label><input type="datetime-local" value={schedValue} onChange={e => setSchedValue(e.target.value)} style={inputStyle} /></div>
      )}
      {schedType === 'cron' && (
        <div style={{ marginBottom: 20 }}>
          <label style={labelStyle}>Cron expression (UTC)</label>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
            {CRON_PRESETS.map(p => (<button key={p.value} type="button" onClick={() => setSchedValue(p.value)} style={{ padding: '4px 10px', borderRadius: 20, fontSize: 11, cursor: 'pointer', border: `1px solid ${schedValue === p.value ? 'rgba(196,164,74,0.5)' : 'var(--color-sc-border)'}`, background: schedValue === p.value ? 'rgba(196,164,74,0.1)' : 'var(--color-sc-bg)', color: schedValue === p.value ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', fontFamily: 'var(--font-inter)' }}>{p.label}</button>))}
          </div>
          <input value={schedValue} onChange={e => setSchedValue(e.target.value)} placeholder="0 9 * * *" style={inputStyle} />
          <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', marginTop: 5 }}>Format: minute hour day month weekday — <a href="https://crontab.guru" target="_blank" rel="noopener" style={{ color: 'var(--color-sc-gold)' }}>crontab.guru</a></div>
        </div>
      )}
      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
        <button onClick={onCancel} style={{ padding: '8px 18px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'transparent', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontFamily: 'var(--font-inter)', fontSize: 13 }}>Cancel</button>
        <button onClick={handleSave} disabled={!goal.trim() || saving} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: goal.trim() ? 'var(--color-sc-gold)' : 'rgba(255,255,255,0.06)', color: goal.trim() ? '#0D0D0D' : 'var(--color-sc-text-dim)', cursor: goal.trim() ? 'pointer' : 'default', fontFamily: 'var(--font-grotesk)', fontSize: 13, fontWeight: 700 }}>
          {saving ? 'Saving…' : 'Save task'}
        </button>
      </div>
    </div>
  );
}

function TaskCard({ task, onDelete, onRun, onRefresh }) {
  const [running, setRunning] = useState(false);
  const st = TASK_STATUS[task.status] ?? TASK_STATUS.idle;
  return (
    <div style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 12, padding: '14px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ width: 34, height: 34, borderRadius: 9, background: `${TASK_STATUS[running ? 'running' : task.status]?.color ?? 'var(--color-sc-text-dim)'}22`, color: TASK_STATUS[running ? 'running' : task.status]?.color ?? 'var(--color-sc-text-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <st.Icon size={15} style={running || task.status === 'running' ? { animation: 'spin 1s linear infinite' } : {}} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 14, color: 'var(--color-sc-text)', marginBottom: 2 }}>{task.name}</div>
          <div style={{ fontSize: 12, color: 'var(--color-sc-text-muted)', marginBottom: 6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{task.goal}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {task.agentEmoji && <span style={{ fontSize: 12 }}>{task.agentEmoji} {task.agentName}</span>}
            {task.scheduleType !== 'manual' && <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', display: 'flex', alignItems: 'center', gap: 4 }}><Clock size={10} /> {task.scheduleValue || task.scheduleType}</span>}
            {task.lastRun && <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>Last: {new Date(task.lastRun).toLocaleString()}</span>}
          </div>
          {task.lastOutput && (
            <div style={{ marginTop: 8, fontSize: 12, color: 'var(--color-sc-text-muted)', background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '6px 10px', fontFamily: 'var(--font-mono)', lineHeight: 1.55, maxHeight: 80, overflow: 'hidden', position: 'relative' }}>
              {task.lastOutput.slice(0, 280)}{task.lastOutput.length > 280 ? '…' : ''}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
          <button onClick={() => onDelete(task.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '5px 7px', borderRadius: 6, display: 'flex', alignItems: 'center' }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--color-sc-danger)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--color-sc-text-dim)'}>
            <Trash2 size={13} />
          </button>
          <button onClick={async () => {
            setRunning(true);
            try {
              await fetch(`/tasks/${task.id}/run`, { method: 'POST' });
              await new Promise(r => setTimeout(r, 2000));
              onRefresh();
            } finally { setRunning(false); }
          }} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, border: 'none', background: 'rgba(196,164,74,0.12)', border: '1px solid rgba(196,164,74,0.3)', color: 'var(--color-sc-gold)', cursor: running ? 'default' : 'pointer', fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 700 }} disabled={running}>
            {running ? <Loader size={11} style={{ animation: 'spin 1s linear infinite' }} /> : <Play size={11} />} {running ? 'Running…' : 'Run now'}
          </button>
        </div>
      </div>
    </div>
  );
}

function TasksTab({ creating, setCreating }) {
  const [tasks, setTasks] = useState([]);
  async function refresh() {
    try {
      const r = await fetch('/tasks');
      const d = await r.json();
      setTasks(d.tasks || []);
    } catch {}
  }
  useEffect(() => { refresh(); const iv = setInterval(refresh, 8000); return () => clearInterval(iv); }, []);

  async function handleDelete(id) {
    await fetch(`/tasks/${id}`, { method: 'DELETE' });
    setTasks(prev => prev.filter(t => t.id !== id));
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '28px 32px' }}>
      {creating && <TaskCreator onSave={t => { setTasks(prev => [t, ...prev]); setCreating(false); }} onCancel={() => setCreating(false)} />}
      {tasks.length === 0 && !creating && (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--color-sc-text-dim)' }}>
          <ListTodo size={36} style={{ opacity: 0.2, marginBottom: 12 }} />
          <div style={{ fontSize: 14, marginBottom: 8, color: 'var(--color-sc-text-muted)' }}>No tasks yet</div>
          <div style={{ fontSize: 13 }}>Assign agents goals and run them on a schedule.</div>
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {tasks.map(t => (<TaskCard key={t.id} task={t} onDelete={handleDelete} onRun={() => {}} onRefresh={refresh} />))}
      </div>
    </div>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────
export function WorkflowsPage() {
  const [creating, setCreating] = useState(false);
  const [tab, setTab] = useState('workflows');

  const TAB_BTN = (id, label, Icon) => (
    <button key={id} onClick={() => { setTab(id); setCreating(false); }} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, border: `1px solid ${tab === id ? 'rgba(196,164,74,0.4)' : 'transparent'}`, background: tab === id ? 'rgba(196,164,74,0.1)' : 'transparent', color: tab === id ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 13, fontWeight: 600, fontFamily: 'var(--font-grotesk)', transition: 'all 0.15s' }}>
      <Icon size={13} /> {label}
    </button>
  );

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
      <div style={{ padding: '20px 32px 0', borderBottom: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 14 }}>
          <div>
            <h1 style={{ margin: '0 0 4px', fontFamily: 'var(--font-grotesk)', fontSize: 20, fontWeight: 700, color: 'var(--color-sc-text)' }}>
              {tab === 'tasks' ? 'Tasks' : 'Workflows'}
            </h1>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--color-sc-text-muted)' }}>
              {tab === 'tasks' ? 'Assign agents goals and run them on a schedule.' : 'Chain agent steps into repeatable, runnable pipelines.'}
            </p>
          </div>
          <button onClick={() => setCreating(true)} style={goldBtn}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(196,164,74,0.22)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(196,164,74,0.12)'}>
            <Plus size={14} /> {tab === 'tasks' ? 'New task' : 'New workflow'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 4, paddingBottom: 1 }}>
          {TAB_BTN('workflows', 'Workflows', Zap)}
          {TAB_BTN('tasks', 'Tasks', ListTodo)}
        </div>
      </div>

      {tab === 'tasks'
        ? <TasksTab creating={creating} setCreating={setCreating} />
        : <WorkflowsTab creating={creating} setCreating={setCreating} />
      }
    </div>
  );
}
