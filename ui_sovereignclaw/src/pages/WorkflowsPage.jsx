import { useState, useEffect, useCallback, useRef } from 'react';
import { useSCStore } from '../store';
import {
  Plus, Play, Trash2, ArrowDown, Zap, Globe, Code2, Brain, Search,
  FileText, X, Clock, Calendar, RotateCcw, CheckCircle, AlertCircle,
  Loader, Bot, ChevronDown, ListTodo, ChevronRight, ChevronUp,
  Database, Bell, Filter, Edit3, Save, History, Sparkles,
  Layers, ChevronsDown, ChevronsUp, StopCircle, GitBranch, Link2, GitMerge, Plus as PlusSmall,
  Folder, FolderOpen, LayoutGrid, PlayCircle, Pencil, Check
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
  { id: 'fetch_connection', label: 'Use Connection', Icon: Link2, desc: 'Pull live data from a connected service', placeholder: '' },
  { id: 'template',     label: 'Template',       Icon: FileText,   desc: 'Fill a text template with prior outputs', placeholder: 'Report:\n\nSummary: {{step_0_output}}\n\nDetails: {{output}}' },
  { id: 'ingest_doc',   label: 'Read Document', Icon: FileText,   desc: 'Load a PDF, TXT, or CSV into the workflow', placeholder: '' },
  { id: 'sub_workflow', label: 'Run Workflow',   Icon: GitBranch,  desc: 'Trigger another workflow and chain its output', placeholder: '' },
  { id: 'if_else',      label: 'If / Else',      Icon: GitMerge,   desc: 'Branch based on a condition', placeholder: '' },
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
  background: 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 30%, transparent)',
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
          <button type="button" onClick={() => { onChange(null); setOpen(false); }} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', background: !value ? 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'transparent', color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 13 }}>
            <span>✨</span> Default (Oricli)
          </button>
          {agents.map(ag => (
            <button key={ag.id} type="button" onClick={() => { onChange(ag); setOpen(false); }} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', background: value?.id === ag.id ? 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'transparent', color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 13 }}>
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
            <button key={wf.id} type="button" onClick={() => { onChange(wf.id); setOpen(false); }} style={{ width: '100%', display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', background: value === wf.id ? 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'transparent', color: 'var(--color-sc-text)', textAlign: 'left' }}>
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

// ─── RagSourcePicker (for rag_query step type) ───────────────────────────────
const RAG_SOURCE_ICONS = { arxiv: '📄', telegram: '✈️', google_workspace: '🗂️', notion: '📝', slack: '💬', discord: '🎮', github: '🐙', jira: '🎯', confluence: '📚', linear: '🔷', airtable: '📊', hubspot: '🧡', salesforce: '☁️', zendesk: '🎫', dropbox: '📦', box: '📦', onedrive: '💾', pubmed: '🔬', default: '🗄️' };
function RagSourcePicker({ value, onChange }) {
  const [connections, setConnections] = useState([]);
  const [indexStatus, setIndexStatus] = useState({});
  const [open, setOpen] = useState(false);
  useEffect(() => {
    fetch('/connections').then(r => r.json()).then(d => setConnections(Object.values(d.connections || {}))).catch(() => {});
    fetch('/connections/index/status').then(r => r.json()).then(setIndexStatus).catch(() => {});
  }, []);

  const indexable = connections.filter(c => c.enabled !== false && (
    (indexStatus[c.id]?.docs > 0) || (indexStatus[c.id]?.local_docs > 0)
  ));

  const selected = value === '__all__' ? null : indexable.find(c => c.id === value);
  const displayLabel = value === '__all__' || !value ? 'All indexed sources' : (selected?.name || value);
  const displayIcon = value === '__all__' || !value ? '🗄️' : (RAG_SOURCE_ICONS[value] || RAG_SOURCE_ICONS.default);

  return (
    <div style={{ position: 'relative', marginBottom: 8 }}>
      <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', marginBottom: 4 }}>Search source</div>
      <button type="button" onClick={() => setOpen(o => !o)} style={{ ...inputStyle, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', padding: '8px 12px', width: '100%' }}>
        <span style={{ fontSize: 13 }}>{displayIcon}</span>
        <span style={{ flex: 1, textAlign: 'left', color: 'var(--color-sc-text)', fontSize: 13 }}>{displayLabel}</span>
        <ChevronDown size={12} style={{ opacity: 0.5, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
      </button>
      {open && (
        <div style={{ position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 50, background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.4)', padding: 4, maxHeight: 220, overflowY: 'auto' }}>
          <button type="button" onClick={() => { onChange('__all__'); setOpen(false); }} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', background: (!value || value === '__all__') ? 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'transparent', color: 'var(--color-sc-text)', textAlign: 'left' }}>
            <span style={{ fontSize: 14 }}>🗄️</span>
            <div>
              <div style={{ fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 600 }}>All indexed sources</div>
              <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)' }}>Search across every connection</div>
            </div>
          </button>
          {indexable.length === 0 && (
            <div style={{ padding: '8px 12px', fontSize: 11, color: 'var(--color-sc-text-dim)' }}>No indexed connections yet — index some in Connections first</div>
          )}
          {indexable.map(c => {
            const docs = indexStatus[c.id]?.local_docs || indexStatus[c.id]?.docs || 0;
            return (
              <button key={c.id} type="button" onClick={() => { onChange(c.id); setOpen(false); }} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', background: value === c.id ? 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'transparent', color: 'var(--color-sc-text)', textAlign: 'left' }}>
                <span style={{ fontSize: 14 }}>{RAG_SOURCE_ICONS[c.id] || RAG_SOURCE_ICONS.default}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 600 }}>{c.name || c.id}</div>
                  <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)' }}>{docs} doc{docs !== 1 ? 's' : ''} indexed</div>
                </div>
                {value === c.id && <CheckCircle size={12} style={{ color: 'var(--color-sc-gold)' }} />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}


// ─── ConnectionPicker ─────────────────────────────────────────────────────────
const FETCHABLE_CONN_TYPES = new Set([
  'discord','telegram','slack','notion','todoist','trello','airtable','linear',
  'asana','jira','salesforce','hubspot','supabase','arxiv','pubmed',
  'semantic_scholar','newsapi','reddit','wikipedia','youtube','github_api',
  'gitlab','google_workspace',
]);

function ConnectionPicker({ value, query, onChangeConn, onChangeQuery }) {
  const [connections, setConnections] = useState([]);
  useEffect(() => {
    fetch('/connections').then(r => r.json()).then(d => {
      const fetchable = Object.values(d.connections || {}).filter(c =>
        c.enabled !== false && FETCHABLE_CONN_TYPES.has(c.id)
      );
      setConnections(fetchable);
    }).catch(() => {});
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 8 }}>
      <select
        value={value || ''}
        onChange={e => onChangeConn(e.target.value)}
        style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'var(--color-sc-bg)', color: 'var(--color-sc-text)', fontSize: 13, fontFamily: 'var(--font-inter)' }}
      >
        <option value="">— pick a connection —</option>
        {connections.map(c => (
          <option key={c.id} value={c.id}>{c.label || c.id}</option>
        ))}
        {connections.length === 0 && <option disabled>No connections configured</option>}
      </select>
      <input
        value={query || ''}
        onChange={e => onChangeQuery(e.target.value)}
        placeholder="Optional: filter / search query (e.g. 'unread emails today')"
        style={{ width: '100%', boxSizing: 'border-box', padding: '7px 10px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'var(--color-sc-bg)', color: 'var(--color-sc-text)', fontSize: 12, fontFamily: 'var(--font-inter)' }}
      />
    </div>
  );
}


// ─── DocUploadModal ───────────────────────────────────────────────────────────
// ─── Template presets ────────────────────────────────────────────────────────
const TEMPLATE_PRESETS = [
  {
    label: 'Research Report',
    body: `## Research Report — {{date}}

### Summary
{{step_0_output}}

### Key Findings
{{output}}

### Sources
- 

### Conclusion
`,
  },
  {
    label: 'Executive Brief',
    body: `**TL;DR:** {{output}}

**Key Points:**
- 
- 
- 

**Recommended Action:**
`,
  },
  {
    label: 'Meeting Notes',
    body: `# Meeting Notes — {{date}}

**Attendees:** 

**Agenda:**
{{step_0_output}}

**Discussion & Decisions:**
{{output}}

**Action Items:**
- [ ] 
- [ ] 

**Next Meeting:**
`,
  },
  {
    label: 'Content Draft',
    body: `# {{workflow_name}}

## Introduction
{{step_0_output}}

## {{output}}

---
*Call to action:*
`,
  },
  {
    label: 'Comparison Table',
    body: `## Comparison — {{date}}

| Feature | Option A | Option B |
|---------|----------|----------|
|         |          |          |
|         |          |          |

**Summary:**
{{output}}
`,
  },
  {
    label: 'Email',
    body: `**Subject:** 

Hi [Name],

{{output}}

Let me know if you have any questions.

Best,
[Your name]
`,
  },
  {
    label: 'Bug Report',
    body: `## Bug Report — {{date}}

**Summary:** {{step_0_output}}

**Steps to Reproduce:**
1. 
2. 
3. 

**Expected Behaviour:**

**Actual Behaviour:**
{{output}}

**Severity:** [ ] Critical  [ ] High  [ ] Medium  [ ] Low

**Environment:**
`,
  },
  {
    label: 'Social Post',
    body: `{{output}}

#️⃣ 
`,
  },
];

function TemplatePresets({ onSelect }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ position: 'relative', marginBottom: 6 }}>
      <button type="button" onClick={() => setOpen(o => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '3px 10px', borderRadius: 6, border: '1px solid rgba(124,106,247,0.25)', background: 'rgba(124,106,247,0.07)', color: '#a89cf7', cursor: 'pointer', fontSize: 11, fontFamily: 'var(--font-grotesk)', fontWeight: 600 }}>
        <FileText size={11} /> Presets <ChevronDown size={10} style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
      </button>
      {open && (
        <div style={{ position: 'absolute', top: 'calc(100% + 4px)', left: 0, zIndex: 60, background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.5)', padding: 4, minWidth: 180 }}>
          {TEMPLATE_PRESETS.map(p => (
            <button key={p.label} type="button"
              onClick={() => { onSelect(p.body); setOpen(false); }}
              style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', background: 'transparent', color: 'var(--color-sc-text)', textAlign: 'left', fontSize: 12, fontFamily: 'var(--font-grotesk)', fontWeight: 500 }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(124,106,247,0.1)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <FileText size={12} style={{ color: '#a89cf7', flexShrink: 0 }} />
              {p.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Template variable reference ─────────────────────────────────────────────
const BUILTIN_VARS = [
  { key: 'output',         desc: 'Output of the previous step' },
  { key: 'input',          desc: 'Alias for {{output}}' },
  { key: 'date',           desc: 'Today\'s date (e.g. March 23, 2026)' },
  { key: 'time',           desc: 'Current time (e.g. 11:21 PM)' },
  { key: 'datetime',       desc: 'Full timestamp (2026-03-23 23:21)' },
  { key: 'workflow_name',  desc: 'Name of this workflow' },
  { key: 'step_N_output',  desc: 'Output of step N (e.g. step_1_output)' },
  { key: 'doc_text',       desc: 'Full text of uploaded document' },
  { key: 'doc_filename',   desc: 'Filename of uploaded document' },
];

function VarsHint() {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button type="button" onClick={() => setOpen(o => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '3px 8px', borderRadius: 6, border: '1px solid color-mix(in srgb, var(--color-sc-gold) 20%, transparent)', background: 'color-mix(in srgb, var(--color-sc-gold) 6%, transparent)', color: 'var(--color-sc-gold)', cursor: 'pointer', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
        {'{{…}}'} variables
      </button>
      {open && (
        <div style={{ position: 'absolute', top: 'calc(100% + 6px)', left: 0, zIndex: 60, background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.5)', padding: '8px 4px', minWidth: 280 }}>
          <div style={{ padding: '2px 10px 6px', fontSize: 10, fontWeight: 700, color: 'var(--color-sc-text-dim)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>Built-in variables</div>
          {BUILTIN_VARS.map(v => (
            <div key={v.key} style={{ display: 'flex', alignItems: 'baseline', gap: 8, padding: '4px 10px', borderRadius: 6, cursor: 'pointer' }}
              onClick={() => { navigator.clipboard?.writeText(`{{${v.key}}}`); setOpen(false); }}>
              <code style={{ fontSize: 11, color: 'var(--color-sc-gold)', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>{`{{${v.key}}}`}</code>
              <span style={{ fontSize: 11, color: 'var(--color-sc-text-muted)' }}>{v.desc}</span>
            </div>
          ))}
          <div style={{ padding: '6px 10px 2px', fontSize: 10, color: 'var(--color-sc-text-dim)', borderTop: '1px solid var(--color-sc-border)', marginTop: 4 }}>
            Any other <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-sc-text-muted)' }}>{'{{custom}}'}</code> variable will prompt you to fill it in at run time.
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Run-time variable fill-in modal ─────────────────────────────────────────
function RunVarsModal({ vars, onConfirm, onCancel }) {
  const [values, setValues] = useState(() => Object.fromEntries(vars.map(v => [v, ''])));
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: 'var(--color-sc-surface)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 25%, transparent)', borderRadius: 16, padding: '28px 28px 24px', width: 420, maxWidth: '90vw' }}>
        <h3 style={{ margin: '0 0 6px', fontFamily: 'var(--font-grotesk)', fontSize: 15, fontWeight: 700, color: 'var(--color-sc-text)' }}>Fill in variables</h3>
        <p style={{ margin: '0 0 20px', fontSize: 12, color: 'var(--color-sc-text-dim)' }}>This workflow uses custom variables. Enter a value for each before running.</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 22 }}>
          {vars.map(v => (
            <div key={v}>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: 'var(--color-sc-text-muted)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>{`{{${v}}}`}</label>
              <input
                autoFocus={vars[0] === v}
                value={values[v]}
                onChange={e => setValues(prev => ({ ...prev, [v]: e.target.value }))}
                onKeyDown={e => { if (e.key === 'Enter' && vars.indexOf(v) === vars.length - 1) onConfirm(values); }}
                placeholder={`Value for ${v}…`}
                style={{ width: '100%', background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)', borderRadius: 8, padding: '8px 12px', color: 'var(--color-sc-text)', fontSize: 13, fontFamily: 'var(--font-inter)', boxSizing: 'border-box' }}
              />
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={{ padding: '8px 18px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'transparent', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 13 }}>Cancel</button>
          <button onClick={() => onConfirm(values)} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'var(--color-sc-gold)', color: '#0D0D0D', cursor: 'pointer', fontFamily: 'var(--font-grotesk)', fontSize: 13, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Play size={12} /> Run workflow
          </button>
        </div>
      </div>
    </div>
  );
}


function DocUploadModal({ onConfirm, onCancel }) {
  const [dragging, setDragging]     = useState(false);
  const [file, setFile]             = useState(null);
  const [uploading, setUploading]   = useState(false);
  const [extracted, setExtracted]   = useState(null);
  const [saveToMemory, setSave]     = useState(false);
  const [error, setError]           = useState('');
  const inputRef = useRef(null);

  async function handleFile(f) {
    setFile(f); setError(''); setExtracted(null); setUploading(true);
    const fd = new FormData(); fd.append('file', f);
    try {
      const res = await fetch('/workflows/ingest-doc', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) { setError(data.error || 'Extraction failed'); setUploading(false); return; }
      setExtracted(data);
    } catch (e) { setError('Upload failed'); }
    setUploading(false);
  }

  function onDrop(e) {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200 }}>
      <div style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 16, padding: 28, width: 440, maxWidth: '90vw' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 16 }}>Upload Document</div>
          <button onClick={onCancel} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)' }}><X size={16} /></button>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          style={{ border: `2px dashed ${dragging ? 'var(--color-sc-gold)' : 'var(--color-sc-border)'}`, borderRadius: 12, padding: '28px 20px', textAlign: 'center', cursor: 'pointer', transition: 'border-color 0.15s', background: dragging ? 'color-mix(in srgb, var(--color-sc-gold) 5%, transparent)' : 'transparent', marginBottom: 16 }}
        >
          <input ref={inputRef} type="file" accept=".pdf,.txt,.csv,.md,.json" style={{ display: 'none' }} onChange={e => e.target.files[0] && handleFile(e.target.files[0])} />
          {uploading ? (
            <div style={{ color: 'var(--color-sc-text-dim)', fontSize: 13 }}><Loader size={18} style={{ animation: 'spin 1s linear infinite', display: 'inline', marginRight: 8 }} />Reading document…</div>
          ) : extracted ? (
            <div style={{ color: 'var(--color-sc-gold)', fontSize: 13 }}>
              <CheckCircle size={18} style={{ display: 'inline', marginRight: 6 }} />
              <strong>{extracted.filename}</strong> — {extracted.chars.toLocaleString()} characters
            </div>
          ) : (
            <>
              <FileText size={28} style={{ color: 'var(--color-sc-text-dim)', marginBottom: 8 }} />
              <div style={{ fontFamily: 'var(--font-grotesk)', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Drop a file or click to browse</div>
              <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>PDF · TXT · CSV · Markdown · JSON</div>
            </>
          )}
        </div>

        {error && <div style={{ color: '#ef4444', fontSize: 12, marginBottom: 12 }}>{error}</div>}

        {/* Preview */}
        {extracted && (
          <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: 8, padding: '10px 12px', fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-sc-text-muted)', marginBottom: 16, maxHeight: 80, overflowY: 'auto', lineHeight: 1.6 }}>
            {extracted.preview}{extracted.chars > 300 ? '…' : ''}
          </div>
        )}

        {/* Memory toggle */}
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', padding: '10px 12px', borderRadius: 8, border: '1px solid var(--color-sc-border)', marginBottom: 20, background: saveToMemory ? 'color-mix(in srgb, var(--color-sc-gold) 6%, transparent)' : 'transparent' }}>
          <input type="checkbox" checked={saveToMemory} onChange={e => setSave(e.target.checked)} style={{ accentColor: 'var(--color-sc-gold)', width: 14, height: 14 }} />
          <div>
            <div style={{ fontFamily: 'var(--font-grotesk)', fontSize: 13, fontWeight: 600, color: saveToMemory ? 'var(--color-sc-gold)' : 'var(--color-sc-text)' }}>Commit to long-term memory</div>
            <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>Oricli will retain this document across future sessions</div>
          </div>
        </label>

        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={onCancel} style={{ flex: 1, padding: '10px 0', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'transparent', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontFamily: 'var(--font-grotesk)', fontSize: 13 }}>Cancel</button>
          <button
            disabled={!extracted}
            onClick={() => extracted && onConfirm({ text: extracted.text, filename: extracted.filename, saveToMemory })}
            style={{ flex: 2, padding: '10px 0', borderRadius: 8, border: 'none', background: extracted ? 'var(--color-sc-gold)' : 'color-mix(in srgb, var(--color-sc-gold) 20%, transparent)', color: extracted ? '#0a0a0a' : 'var(--color-sc-text-dim)', cursor: extracted ? 'pointer' : 'not-allowed', fontFamily: 'var(--font-grotesk)', fontSize: 13, fontWeight: 700 }}
          >
            Run Workflow
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── BranchStepList ───────────────────────────────────────────────────────────
// Compact step list used inside if_else branches (avoids circular dep by
// rendering StepEditor inline after its own declaration via a ref approach).
// We keep it simple: just the step editors, no outer chrome.
function BranchStepList({ steps, onChange }) {
  const add = () => onChange([...steps, { id: `bs_${Date.now()}`, type: 'prompt', value: '' }]);
  const remove = (i) => onChange(steps.filter((_, idx) => idx !== i));
  const update = (i, s) => onChange(steps.map((x, idx) => idx === i ? s : x));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {steps.map((s, i) => (
        <StepEditor
          key={s.id || i}
          step={s}
          index={i}
          total={steps.length}
          onChange={ns => update(i, ns)}
          onRemove={() => remove(i)}
          parentWfId={null}
          compact
        />
      ))}
      <button
        type="button"
        onClick={add}
        style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px', borderRadius: 7, border: '1px dashed color-mix(in srgb, var(--color-sc-gold) 30%, transparent)', background: 'transparent', color: 'var(--color-sc-text-dim)', fontSize: 11, cursor: 'pointer', fontFamily: 'var(--font-grotesk)' }}
      >
        <Plus size={10} /> Add step
      </button>
    </div>
  );
}


function StepEditor({ step, index, total, onChange, onRemove, parentWfId, compact }) {
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
          <div style={{ width: 22, height: 22, borderRadius: '50%', background: 'color-mix(in srgb, var(--color-sc-gold) 15%, transparent)', color: 'var(--color-sc-gold)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, fontFamily: 'var(--font-grotesk)', flexShrink: 0 }}>
            {index + 1}
          </div>
          <div style={{ position: 'relative', flexShrink: 0 }}>
            <button type="button" onClick={() => setShowTypePicker(p => !p)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px', borderRadius: 7, border: '1px solid color-mix(in srgb, var(--color-sc-gold) 30%, transparent)', background: 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)', color: 'var(--color-sc-gold)', cursor: 'pointer', fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 600 }}>
              <Icon size={12} /> {def.label} <ChevronDown size={10} style={{ transform: showTypePicker ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
            </button>
            {showTypePicker && (
              <div style={{ position: 'absolute', top: 'calc(100% + 6px)', left: 0, zIndex: 50, background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.5)', padding: 4, minWidth: 200, maxHeight: 280, overflowY: 'auto' }}>
                {STEP_TYPES.map(st => (
                  <button key={st.id} type="button" onClick={() => { onChange({ ...step, type: st.id }); setShowTypePicker(false); }} style={{ width: '100%', display: 'flex', alignItems: 'flex-start', gap: 10, padding: '8px 10px', borderRadius: 7, border: 'none', cursor: 'pointer', background: step.type === st.id ? 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'transparent', color: 'var(--color-sc-text)', textAlign: 'left' }}>
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
          <VarsHint />
          <button onClick={onRemove} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: 4, display: 'flex', flexShrink: 0 }}>
            <X size={14} />
          </button>
        </div>
        {/* Step value */}
        {step.type === 'ingest_doc' ? (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'rgba(0,0,0,0.2)', marginBottom: 10 }}>
              <FileText size={14} style={{ color: 'var(--color-sc-gold)', flexShrink: 0 }} />
              <span style={{ fontSize: 12, color: 'var(--color-sc-text-muted)' }}>You'll be prompted to upload a <strong>PDF, TXT, or CSV</strong> when this workflow runs. Its contents become <code style={{ background: 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)', color: 'var(--color-sc-gold)', padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>{'{{output}}'}</code> for the next step.</span>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', padding: '9px 12px', borderRadius: 8, border: `1px solid ${step.saveToMemory ? 'color-mix(in srgb, var(--color-sc-gold) 40%, transparent)' : 'var(--color-sc-border)'}`, background: step.saveToMemory ? 'color-mix(in srgb, var(--color-sc-gold) 6%, transparent)' : 'transparent', transition: 'all 0.15s' }}>
              <input type="checkbox" checked={!!step.saveToMemory} onChange={e => onChange({ ...step, saveToMemory: e.target.checked })} style={{ accentColor: 'var(--color-sc-gold)', width: 13, height: 13 }} />
              <div>
                <div style={{ fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 600, color: step.saveToMemory ? 'var(--color-sc-gold)' : 'var(--color-sc-text)' }}>Commit to long-term memory</div>
                <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>Oricli retains this document across future sessions</div>
              </div>
            </label>
          </div>
        ) : step.type === 'sub_workflow' ? (
          <div>
            <WorkflowPicker
              value={step.workflowId || step.value || ''}
              onChange={wfId => onChange({ ...step, workflowId: wfId, value: wfId })}
              excludeId={parentWfId}
            />
            <div style={{ marginTop: 6, fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
              The selected workflow will run with the current <code style={{ background: 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)', color: 'var(--color-sc-gold)', padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>{'{{output}}'}</code> as its starting context.
              Its final output becomes <code style={{ background: 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)', color: 'var(--color-sc-gold)', padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>{'{{output}}'}</code> for your next step.
            </div>
          </div>
        ) : step.type === 'if_else' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {/* Condition */}
            <div>
              <div style={{ fontSize: 11, fontFamily: 'var(--font-grotesk)', fontWeight: 600, color: 'var(--color-sc-text-muted)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Condition</div>
              <textarea
                value={step.condition || ''}
                onChange={e => onChange({ ...step, condition: e.target.value })}
                placeholder="Does the output mention a risk or warning?"
                rows={2}
                style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.55, fontFamily: 'var(--font-inter)', fontSize: 13 }}
              />
              <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', marginTop: 3 }}>Oricli evaluates this as a yes/no question against the previous output.</div>
            </div>
            {/* Then branch */}
            <div style={{ borderLeft: '2px solid rgba(74,196,74,0.35)', paddingLeft: 12 }}>
              <div style={{ fontSize: 11, fontFamily: 'var(--font-grotesk)', fontWeight: 700, color: '#4ac44a', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>✓ If true</div>
              <BranchStepList
                steps={step.thenSteps || []}
                onChange={ts => onChange({ ...step, thenSteps: ts })}
              />
            </div>
            {/* Else branch */}
            <div style={{ borderLeft: '2px solid rgba(196,74,74,0.35)', paddingLeft: 12 }}>
              <div style={{ fontSize: 11, fontFamily: 'var(--font-grotesk)', fontWeight: 700, color: '#c44a4a', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>✗ If false <span style={{ fontWeight: 400, opacity: 0.7 }}>(optional)</span></div>
              <BranchStepList
                steps={step.elseSteps || []}
                onChange={es => onChange({ ...step, elseSteps: es })}
              />
            </div>
          </div>
        ) : step.type === 'rag_query' ? (
          <div>
            <RagSourcePicker
              value={step.ragSource || '__all__'}
              onChange={src => onChange({ ...step, ragSource: src })}
            />
            <textarea
              value={step.value || ''}
              onChange={e => onChange({ ...step, value: e.target.value })}
              placeholder="What do we know about {{output}}?"
              rows={2}
              style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.55, fontFamily: 'var(--font-inter)', fontSize: 13 }}
            />
          </div>
        ) : step.type === 'fetch_connection' ? (
          <div>
            <ConnectionPicker
              value={step.connectionId || ''}
              query={step.query || ''}
              onChangeConn={id => onChange({ ...step, connectionId: id, value: id })}
              onChangeQuery={q => onChange({ ...step, query: q })}
            />
            <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', marginTop: 2 }}>
              Fetches live data from the selected connection. Its content becomes{' '}
              <code style={{ background: 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)', color: 'var(--color-sc-gold)', padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>{'{{output}}'}</code>{' '}
              for the next step.
            </div>
          </div>
        ) : (
          <>
            {step.type === 'template' && (
              <TemplatePresets onSelect={tpl => onChange({ ...step, value: tpl })} />
            )}
            <textarea
              value={step.value || ''}
              onChange={e => onChange({ ...step, value: e.target.value })}
              placeholder={def.placeholder}
              rows={step.type === 'code' || step.type === 'template' ? 5 : 2}
              style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.55, fontFamily: step.type === 'code' ? 'var(--font-mono)' : 'var(--font-inter)', fontSize: step.type === 'code' ? 12 : 13 }}
            />
          </>
        )}
        {index > 0 && step.type !== 'sub_workflow' && (
          <div style={{ marginTop: 6, fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
            Use <code style={{ background: 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)', color: 'var(--color-sc-gold)', padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>{'{{output}}'}</code> for previous step output,{' '}
            <code style={{ background: 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)', color: 'var(--color-sc-gold)', padding: '1px 5px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>{'{{step_0_output}}'}</code> etc. for specific steps.
          </div>
        )}
      </div>
    </div>
  );
}

// ─── WorkflowCreator ─────────────────────────────────────────────────────────
function WorkflowCreator({ onSave, onCancel, initial, defaultProjectId, pendingDescription }) {
  const [name, setName]               = useState(initial?.name || '');
  const [desc, setDesc]               = useState(pendingDescription || initial?.description || '');
  const [agent, setAgent]             = useState(initial ? { id: initial.agentId, name: initial.agentName, emoji: initial.agentEmoji } : null);
  const [steps, setSteps]             = useState(initial?.steps?.length ? initial.steps : [{ id: crypto.randomUUID(), type: 'prompt', label: '', value: '' }]);
  const [sendToCanvas, setSendToCanvas] = useState(!!initial?.sendToCanvas);
  const [projectId, setProjectId]     = useState(initial?.project_id || defaultProjectId || null);
  const [saving, setSaving]           = useState(false);
  const projects                      = useSCStore(s => s.projects);

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
        steps, sendToCanvas, project_id: projectId || null,
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
    <div style={{ background: 'var(--color-sc-surface)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 25%, transparent)', borderRadius: 14, padding: '22px 24px', marginBottom: 20 }}>
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

      {projects.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <label style={labelStyle}>Project (optional)</label>
          <select value={projectId || ''} onChange={e => setProjectId(e.target.value || null)}
            style={{ ...inputStyle, appearance: 'none' }}>
            <option value=''>— Ungrouped —</option>
            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
      )}

      <label style={{ ...labelStyle, marginBottom: 12 }}>Steps</label>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0, marginBottom: 14 }}>
        {steps.map((step, idx) => (
          <StepEditor key={step.id} step={step} index={idx} total={steps.length}
            onChange={s => updateStep(idx, s)} onRemove={() => removeStep(idx)}
            parentWfId={initial?.id} />
        ))}
      </div>

      <button type="button" onClick={addStep} style={{ ...goldBtn, padding: '7px 14px', fontSize: 12, marginBottom: 20, background: 'transparent', border: '1px dashed color-mix(in srgb, var(--color-sc-gold) 30%, transparent)' }}>
        <Plus size={12} /> Add step
      </button>

      {/* Canvas output toggle */}
      <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', padding: '10px 14px', borderRadius: 9, border: `1px solid ${sendToCanvas ? 'color-mix(in srgb, var(--color-sc-gold) 40%, transparent)' : 'var(--color-sc-border)'}`, background: sendToCanvas ? 'color-mix(in srgb, var(--color-sc-gold) 6%, transparent)' : 'transparent', marginBottom: 16, transition: 'all 0.15s' }}>
        <input type="checkbox" checked={sendToCanvas} onChange={e => setSendToCanvas(e.target.checked)} style={{ accentColor: 'var(--color-sc-gold)', width: 13, height: 13, flexShrink: 0 }} />
        <div>
          <div style={{ fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 600, color: sendToCanvas ? 'var(--color-sc-gold)' : 'var(--color-sc-text)' }}>Send output to Canvas</div>
          <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>When the workflow finishes, the final output opens as a Canvas document</div>
        </div>
      </label>

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
const STATUS_COLOR = { queued: 'var(--color-sc-text-dim)', running: 'var(--color-sc-gold)', pausing: 'var(--color-sc-gold)', paused: '#c49a4a', resuming: 'var(--color-sc-gold)', cancelling: 'var(--color-sc-danger)', cancelled: 'var(--color-sc-text-dim)', done: 'var(--color-sc-success)', error: 'var(--color-sc-danger)' };

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
function ActiveRunsTray({ bgRuns, workflows, onDismiss, onDismissAll, onRerun, onCancel, onPause, onResume }) {
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
          <span style={{ padding: '2px 8px', borderRadius: 20, background: 'color-mix(in srgb, var(--color-sc-gold) 15%, transparent)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 30%, transparent)', color: 'var(--color-sc-gold)', fontSize: 11, fontWeight: 700, fontFamily: 'var(--font-grotesk)', display: 'flex', alignItems: 'center', gap: 5 }}>
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
                  {(status === 'done' || status === 'error' || status === 'cancelled') && (
                    <button onClick={() => onRerun(wfId, runId)} title="Re-run"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '2px 4px', display: 'flex', flexShrink: 0, transition: 'color 0.12s' }}
                      onMouseEnter={e => e.currentTarget.style.color = 'var(--color-sc-gold)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--color-sc-text-dim)'}>
                      <RotateCcw size={11} />
                    </button>
                  )}

                  {/* Pause / Resume */}
                  {status === 'running' && (
                    <button onClick={() => onPause(runId)} title="Pause"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '2px 4px', display: 'flex', flexShrink: 0, transition: 'color 0.12s' }}
                      onMouseEnter={e => e.currentTarget.style.color = 'var(--color-sc-gold)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--color-sc-text-dim)'}>
                      <StopCircle size={11} />
                    </button>
                  )}
                  {(status === 'paused' || status === 'pausing') && (
                    <button onClick={() => onResume(runId)} title="Resume"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-gold)', padding: '2px 4px', display: 'flex', flexShrink: 0 }}>
                      <Play size={11} />
                    </button>
                  )}

                  {/* Stop */}
                  {(status === 'running' || status === 'paused' || status === 'pausing') && (
                    <button onClick={() => onCancel(runId)} title="Stop"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '2px 4px', display: 'flex', flexShrink: 0, transition: 'color 0.12s' }}
                      onMouseEnter={e => e.currentTarget.style.color = 'var(--color-sc-danger)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--color-sc-text-dim)'}>
                      <X size={12} />
                    </button>
                  )}

                  {/* Dismiss */}
                  {(status === 'done' || status === 'error' || status === 'cancelled') && (
                    <button onClick={() => onDismiss(runId)} title="Dismiss"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '2px 4px', display: 'flex', flexShrink: 0, transition: 'color 0.12s' }}
                      onMouseEnter={e => e.currentTarget.style.color = 'var(--color-sc-danger)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--color-sc-text-dim)'}>
                      <Trash2 size={11} />
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
      style={{ background: 'var(--color-sc-surface)', border: `1px solid ${isRunning ? 'color-mix(in srgb, var(--color-sc-gold) 35%, transparent)' : hovered ? 'color-mix(in srgb, var(--color-sc-gold) 20%, transparent)' : 'var(--color-sc-border)'}`, borderRadius: 12, padding: '16px 18px', transition: 'border-color 0.15s', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ width: 38, height: 38, borderRadius: 10, background: isRunning ? 'color-mix(in srgb, var(--color-sc-gold) 18%, transparent)' : 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)', color: 'var(--color-sc-gold)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
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

// ─── Project Sidebar ─────────────────────────────────────────────────────────
const PROJECT_COLORS = ['#7c6af7','#f76a6a','#6af7c4','#f7c46a','#6aaaf7','#f76ab8','#a8f76a'];

function ProjectSidebar({ workflows, activeProjectId, onSelect, onCreateWorkflow }) {
  const projects       = useSCStore(s => s.projects);
  const fetchProjects  = useSCStore(s => s.fetchProjects);
  const createProject  = useSCStore(s => s.createProject);
  const updateProject  = useSCStore(s => s.updateProject);
  const deleteProject  = useSCStore(s => s.deleteProject);
  const [creating, setCreating]   = useState(false);
  const [newName, setNewName]     = useState('');
  const [newColor, setNewColor]   = useState(PROJECT_COLORS[0]);
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName]   = useState('');

  useEffect(() => { fetchProjects(); }, []);

  const countByProject = {};
  workflows.forEach(w => { if (w.project_id) countByProject[w.project_id] = (countByProject[w.project_id] || 0) + 1; });
  const ungroupedCount = workflows.filter(w => !w.project_id).length;

  async function handleCreate() {
    if (!newName.trim()) return;
    const proj = await createProject(newName.trim(), newColor);
    setCreating(false); setNewName(''); setNewColor(PROJECT_COLORS[0]);
    onSelect(proj.id);
  }

  async function handleRename(id) {
    if (!editName.trim()) return;
    await updateProject(id, { name: editName.trim() });
    setEditingId(null);
  }

  const sidebarItem = (isActive) => ({
    display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px',
    borderRadius: 8, cursor: 'pointer', marginBottom: 2,
    background: isActive ? 'rgba(124,106,247,0.12)' : 'transparent',
    border: `1px solid ${isActive ? 'rgba(124,106,247,0.3)' : 'transparent'}`,
    transition: 'all 0.12s',
  });

  return (
    <div style={{ width: 210, flexShrink: 0, borderRight: '1px solid var(--color-sc-border)', padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: 2, overflowY: 'auto' }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--color-sc-text-dim)', textTransform: 'uppercase', marginBottom: 8, paddingLeft: 4 }}>Projects</div>

      {/* All workflows */}
      <div onClick={() => onSelect(null)} style={sidebarItem(activeProjectId === null)}>
        <LayoutGrid size={13} style={{ color: activeProjectId === null ? '#7c6af7' : 'var(--color-sc-text-dim)', flexShrink: 0 }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: activeProjectId === null ? 'var(--color-sc-text)' : 'var(--color-sc-text-muted)', flex: 1 }}>All workflows</span>
        <span style={{ fontSize: 10, color: 'var(--color-sc-text-dim)' }}>{workflows.length}</span>
      </div>

      {/* Project folders */}
      {projects.map(p => (
        <div key={p.id} style={{ ...sidebarItem(activeProjectId === p.id), flexDirection: 'column', alignItems: 'stretch', gap: 0, padding: 0 }}>
          {editingId === p.id ? (
            <div style={{ display: 'flex', gap: 4, padding: '5px 8px' }}>
              <input autoFocus value={editName} onChange={e => setEditName(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleRename(p.id); if (e.key === 'Escape') setEditingId(null); }}
                style={{ flex: 1, background: 'var(--color-sc-bg)', border: '1px solid rgba(124,106,247,0.4)', borderRadius: 5, padding: '3px 6px', color: 'var(--color-sc-text)', fontSize: 12 }} />
              <button onClick={() => handleRename(p.id)} style={{ background: 'none', border: 'none', color: '#7c6af7', cursor: 'pointer', padding: '2px 4px' }}><Check size={12} /></button>
              <button onClick={() => setEditingId(null)} style={{ background: 'none', border: 'none', color: 'var(--color-sc-text-dim)', cursor: 'pointer', padding: '2px 4px' }}><X size={12} /></button>
            </div>
          ) : (
            <div onClick={() => onSelect(p.id)} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', cursor: 'pointer', background: activeProjectId === p.id ? 'rgba(124,106,247,0.12)' : 'transparent', borderRadius: 8, border: `1px solid ${activeProjectId === p.id ? 'rgba(124,106,247,0.3)' : 'transparent'}` }}>
              {activeProjectId === p.id
                ? <FolderOpen size={13} style={{ color: p.color || '#7c6af7', flexShrink: 0 }} />
                : <Folder size={13} style={{ color: p.color || '#7c6af7', flexShrink: 0 }} />}
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-sc-text)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</span>
              <span style={{ fontSize: 10, color: 'var(--color-sc-text-dim)', flexShrink: 0 }}>{countByProject[p.id] || 0}</span>
              <button onClick={e => { e.stopPropagation(); setEditingId(p.id); setEditName(p.name); }} style={{ background: 'none', border: 'none', color: 'var(--color-sc-text-dim)', cursor: 'pointer', padding: '1px 3px', opacity: 0.5 }}><Pencil size={10} /></button>
              <button onClick={e => { e.stopPropagation(); if (window.confirm(`Delete project "${p.name}"?`)) deleteProject(p.id).then(() => { if (activeProjectId === p.id) onSelect(null); }); }} style={{ background: 'none', border: 'none', color: 'var(--color-sc-danger)', cursor: 'pointer', padding: '1px 3px', opacity: 0.5 }}><Trash2 size={10} /></button>
            </div>
          )}
        </div>
      ))}

      {/* Ungrouped */}
      {ungroupedCount > 0 && (
        <div onClick={() => onSelect('__ungrouped__')} style={sidebarItem(activeProjectId === '__ungrouped__')}>
          <Folder size={13} style={{ color: 'var(--color-sc-text-dim)', flexShrink: 0 }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: activeProjectId === '__ungrouped__' ? 'var(--color-sc-text)' : 'var(--color-sc-text-muted)', flex: 1 }}>Ungrouped</span>
          <span style={{ fontSize: 10, color: 'var(--color-sc-text-dim)' }}>{ungroupedCount}</span>
        </div>
      )}

      <div style={{ borderTop: '1px solid var(--color-sc-border)', marginTop: 10, paddingTop: 10 }}>
        {creating ? (
          <div>
            <input autoFocus value={newName} onChange={e => setNewName(e.target.value)} placeholder="Project name"
              onKeyDown={e => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setCreating(false); }}
              style={{ width: '100%', background: 'var(--color-sc-bg)', border: '1px solid rgba(124,106,247,0.4)', borderRadius: 6, padding: '5px 8px', color: 'var(--color-sc-text)', fontSize: 12, boxSizing: 'border-box', marginBottom: 6 }} />
            <div style={{ display: 'flex', gap: 4, marginBottom: 6, flexWrap: 'wrap' }}>
              {PROJECT_COLORS.map(c => (
                <div key={c} onClick={() => setNewColor(c)}
                  style={{ width: 16, height: 16, borderRadius: '50%', background: c, cursor: 'pointer', border: newColor === c ? '2px solid white' : '2px solid transparent', boxSizing: 'border-box' }} />
              ))}
            </div>
            <div style={{ display: 'flex', gap: 5 }}>
              <button onClick={handleCreate} style={{ flex: 1, padding: '5px', borderRadius: 6, border: 'none', background: '#7c6af7', color: '#fff', cursor: 'pointer', fontSize: 11, fontWeight: 700 }}>Create</button>
              <button onClick={() => setCreating(false)} style={{ padding: '5px 8px', borderRadius: 6, border: '1px solid var(--color-sc-border)', background: 'none', color: 'var(--color-sc-text-dim)', cursor: 'pointer', fontSize: 11 }}>Cancel</button>
            </div>
          </div>
        ) : (
          <button onClick={() => setCreating(true)} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 6, padding: '6px 8px', borderRadius: 7, border: '1px dashed rgba(124,106,247,0.3)', background: 'none', color: 'var(--color-sc-text-dim)', cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
            <Plus size={11} /> New project
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Project Chain Graph ──────────────────────────────────────────────────────
function ProjectChainGraph({ workflows, projectId, onRunProject, onOpenWorkflow }) {
  const projWfs = workflows.filter(w => w.project_id === projectId);
  if (projWfs.length === 0) return null;

  // Build directed graph from sub_workflow steps
  const edges = new Map(); // wfId → Set<targetId>
  const inDegree = {};
  projWfs.forEach(w => { edges.set(w.id, new Set()); inDegree[w.id] = 0; });

  projWfs.forEach(wf => {
    (wf.steps || []).forEach(step => {
      if (step.type === 'sub_workflow') {
        const tid = (step.params?.wf_id) || step.wf_id;
        if (tid && edges.has(tid)) {
          edges.get(wf.id).add(tid);
          inDegree[tid] = (inDegree[tid] || 0) + 1;
        }
      }
    });
  });

  // Topological BFS to build columns
  const cols = [];
  let queue = projWfs.filter(w => (inDegree[w.id] || 0) === 0).map(w => w.id);
  const placed = new Set();
  const tempDeg = { ...inDegree };

  while (queue.length > 0) {
    cols.push([...queue]);
    queue.forEach(id => placed.add(id));
    const next = [];
    queue.forEach(id => {
      edges.get(id)?.forEach(tid => {
        tempDeg[tid]--;
        if (tempDeg[tid] === 0 && !placed.has(tid)) next.push(tid);
      });
    });
    queue = next;
  }
  // Catch any cycles
  projWfs.forEach(w => { if (!placed.has(w.id)) cols.push([w.id]); });

  const wfMap = Object.fromEntries(projWfs.map(w => [w.id, w]));

  return (
    <div style={{ padding: '16px 20px 0', borderBottom: '1px solid var(--color-sc-border)', marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--color-sc-text-dim)' }}>Execution chain</span>
        <button onClick={onRunProject} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 7, border: 'none', background: '#7c6af7', color: '#fff', cursor: 'pointer', fontSize: 11, fontWeight: 700 }}>
          <PlayCircle size={12} /> Run project
        </button>
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 0, overflowX: 'auto', paddingBottom: 16 }}>
        {cols.map((col, ci) => (
          <div key={ci} style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {col.map(wfId => {
                const wf = wfMap[wfId];
                if (!wf) return null;
                return (
                  <div key={wfId} onClick={() => onOpenWorkflow(wf)}
                    style={{ padding: '8px 12px', borderRadius: 9, background: 'var(--color-sc-surface)', border: '1px solid rgba(124,106,247,0.25)', cursor: 'pointer', minWidth: 130, maxWidth: 160, transition: 'border-color 0.15s' }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(124,106,247,0.6)'}
                    onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(124,106,247,0.25)'}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-sc-text)', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{wf.agentEmoji || '✨'} {wf.name}</div>
                    <div style={{ fontSize: 10, color: 'var(--color-sc-text-dim)' }}>{(wf.steps || []).length} step{wf.steps?.length !== 1 ? 's' : ''}</div>
                  </div>
                );
              })}
            </div>
            {ci < cols.length - 1 && (
              <div style={{ display: 'flex', alignItems: 'center', padding: '0 8px', color: 'rgba(124,106,247,0.5)', fontSize: 18, flexShrink: 0 }}>→</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── WorkflowsTab ────────────────────────────────────────────────────────────
function WorkflowsTab({ creating, setCreating }) {
  const [workflows, setWorkflows] = useState([]);
  const [historyWf, setHistoryWf] = useState(null);
  const [editingWf, setEditingWf] = useState(null);
  const [pendingDocRun, setPendingDocRun] = useState(null);
  const [pendingVarsRun, setPendingVarsRun] = useState(null); // { wf, vars[] }
  const [wfPrompt, setWfPrompt]     = useState(null);
  const [wfIntentId, setWfIntentId] = useState(null);

  // bgRuns lives in global store — survives page navigation
  const bgRuns               = useSCStore(s => s.bgRuns);
  const startBgRun           = useSCStore(s => s.startBgRun);
  const dismissBgRun         = useSCStore(s => s.dismissBgRun);
  const dismissAllDoneBgRuns = useSCStore(s => s.dismissAllDoneBgRuns);
  const cancelRun            = useSCStore(s => s.cancelRun);
  const pauseRun             = useSCStore(s => s.pauseRun);
  const resumeRun            = useSCStore(s => s.resumeRun);
  const activeProjectId      = useSCStore(s => s.activeProjectId);
  const setActiveProject     = useSCStore(s => s.setActiveProject);
  const fetchProjects        = useSCStore(s => s.fetchProjects);

  const pendingWorkflowPrompt      = useSCStore(s => s.pendingWorkflowPrompt);
  const clearPendingWorkflowPrompt = useSCStore(s => s.clearPendingWorkflowPrompt);
  const pendingWorkflowIntentId      = useSCStore(s => s.pendingWorkflowIntentId);
  const clearPendingWorkflowIntentId = useSCStore(s => s.clearPendingWorkflowIntentId);
  const updateCreationIntent         = useSCStore(s => s.updateCreationIntent);
  const logCreationIntent            = useSCStore(s => s.logCreationIntent);

  // Auto-open creator when navigated from chat with a pending prompt
  useEffect(() => {
    if (pendingWorkflowPrompt) {
      setWfPrompt(pendingWorkflowPrompt);
      setWfIntentId(pendingWorkflowIntentId);
      setCreating(true);
      clearPendingWorkflowPrompt();
      clearPendingWorkflowIntentId();
    }
  }, [pendingWorkflowPrompt, pendingWorkflowIntentId, clearPendingWorkflowPrompt, clearPendingWorkflowIntentId, setCreating]);

  async function refresh() {
    try {
      const r = await fetch('/workflows');
      const d = await r.json();
      setWorkflows(d.workflows || []);
    } catch {}
  }
  useEffect(() => { refresh(); fetchProjects(); }, []);

  async function handleRun(wf, userVars = null) {
    if (wf.steps?.some(s => s.type === 'ingest_doc')) {
      setPendingDocRun(wf);
      return;
    }
    // Check for user-defined template vars (skip if already provided)
    if (!userVars) {
      try {
        const vr = await fetch(`/workflows/${wf.id}/vars`).then(r => r.json());
        if (vr.vars?.length > 0) {
          setPendingVarsRun({ wf, vars: vr.vars });
          return;
        }
      } catch {}
    }
    try {
      const res  = await fetch(`/workflows/${wf.id}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_vars: userVars || {} }),
      });
      const data = await res.json();
      startBgRun(data.run_id, wf.id, { sendToCanvas: !!wf.sendToCanvas, wfName: wf.name });
    } catch (e) { console.error('Failed to start workflow:', e); }
  }

  async function handleRunProject(projectId) {
    try {
      const res  = await fetch(`/projects/${projectId}/run`, { method: 'POST' });
      const data = await res.json();
      (data.run_ids || []).forEach((runId, i) => {
        const wfId = data.entry_workflows?.[i];
        const wf = workflows.find(w => w.id === wfId);
        startBgRun(runId, wfId, { sendToCanvas: !!wf?.sendToCanvas, wfName: wf?.name });
      });
    } catch (e) { console.error('Failed to run project:', e); }
  }

  async function handleDocRunConfirm({ text, filename, saveToMemory }) {
    const wf = pendingDocRun;
    setPendingDocRun(null);
    try {
      const res = await fetch(`/workflows/${wf.id}/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_text: text, doc_filename: filename, save_to_memory: saveToMemory }),
      });
      const data = await res.json();
      startBgRun(data.run_id, wf.id, { sendToCanvas: !!wf.sendToCanvas, wfName: wf.name });
    } catch (e) { console.error('Failed to start workflow with doc:', e); }
  }

  async function handleRerun(wfId, oldRunId) {
    try {
      dismissBgRun(oldRunId);
      const wf = workflows.find(w => w.id === wfId);
      const res  = await fetch(`/workflows/${wfId}/run`, { method: 'POST' });
      const data = await res.json();
      startBgRun(data.run_id, wfId, { sendToCanvas: !!wf?.sendToCanvas, wfName: wf?.name });
    } catch {}
  }

  async function handleDelete(id) {
    await fetch(`/workflows/${id}`, { method: 'DELETE' });
    setWorkflows(prev => prev.filter(w => w.id !== id));
  }

  function handleSave(wf) {
    if (wfIntentId && wf?.name) {
      updateCreationIntent(wfIntentId, { action: 'created', resolution_quality: 'completed', resultName: wf.name, resultId: wf.id });
      setWfIntentId(null);
    }
    setWfPrompt(null);
    setCreating(false);
    setEditingWf(null);
    refresh();
  }

  // Map wfId → most recent bgRun for card status indicators
  const activeByWf = {};
  Object.values(bgRuns).forEach(r => {
    if (!activeByWf[r.wfId] || r.startedAt > activeByWf[r.wfId].startedAt)
      activeByWf[r.wfId] = r;
  });

  // Filter workflows based on selected project
  const visibleWfs = (() => {
    if (!activeProjectId || activeProjectId === null) return workflows;
    if (activeProjectId === '__ungrouped__') return workflows.filter(w => !w.project_id);
    return workflows.filter(w => w.project_id === activeProjectId);
  })();

  const isRealProject = activeProjectId && activeProjectId !== '__ungrouped__';

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Project sidebar */}
        <ProjectSidebar
          workflows={workflows}
          activeProjectId={activeProjectId}
          onSelect={id => { setActiveProject(id); setCreating(false); setEditingWf(null); }}
          onCreateWorkflow={() => {
            const id = logCreationIntent({ type: 'workflow', subject: '(direct)', origin_surface: 'workflows' });
            setWfIntentId(id);
            setCreating(true);
          }}
        />

        {/* Main content */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Chain graph — only shown when a real project is selected */}
          {isRealProject && (
            <ProjectChainGraph
              workflows={workflows}
              projectId={activeProjectId}
              onRunProject={() => handleRunProject(activeProjectId)}
              onOpenWorkflow={wf => { setCreating(false); setEditingWf(wf); }}
            />
          )}

          <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
            {creating && (
              <WorkflowCreator
                onSave={handleSave}
                onCancel={() => {
                  if (wfIntentId) {
                    updateCreationIntent(wfIntentId, { resolution_quality: 'abandoned' });
                    setWfIntentId(null);
                  }
                  setCreating(false); setWfPrompt(null);
                }}
                defaultProjectId={isRealProject ? activeProjectId : null}
                pendingDescription={wfPrompt}
              />
            )}
            {editingWf && (
              <WorkflowCreator
                initial={editingWf}
                onSave={handleSave}
                onCancel={() => setEditingWf(null)}
              />
            )}
            {pendingDocRun && <DocUploadModal onConfirm={handleDocRunConfirm} onCancel={() => setPendingDocRun(null)} />}
            {pendingVarsRun && (
              <RunVarsModal
                vars={pendingVarsRun.vars}
                onConfirm={vals => { const wf = pendingVarsRun.wf; setPendingVarsRun(null); handleRun(wf, vals); }}
                onCancel={() => setPendingVarsRun(null)}
              />
            )}

            {visibleWfs.length === 0 && !creating && (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--color-sc-text-dim)' }}>
                <Zap size={36} style={{ opacity: 0.2, marginBottom: 12 }} />
                <div style={{ fontSize: 14, marginBottom: 8, color: 'var(--color-sc-text-muted)' }}>
                  {activeProjectId ? 'No workflows in this project yet' : 'No workflows yet'}
                </div>
                <div style={{ fontSize: 13 }}>Chain steps together into automated, repeatable pipelines.</div>
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {visibleWfs.filter(w => !editingWf || w.id !== editingWf.id).map(wf => (
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
        </div>
      </div>

      <ActiveRunsTray
        bgRuns={bgRuns}
        workflows={workflows}
        onDismiss={dismissBgRun}
        onDismissAll={dismissAllDoneBgRuns}
        onRerun={handleRerun}
        onCancel={cancelRun}
        onPause={pauseRun}
        onResume={resumeRun}
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
    <div style={{ background: 'var(--color-sc-surface)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 25%, transparent)', borderRadius: 14, padding: '22px 24px', marginBottom: 20 }}>
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
            <button key={st.id} type="button" onClick={() => { setSchedType(st.id); setSchedValue(''); }} style={{ flex: 1, padding: '8px 10px', borderRadius: 8, border: `1px solid ${schedType === st.id ? 'color-mix(in srgb, var(--color-sc-gold) 50%, transparent)' : 'var(--color-sc-border)'}`, background: schedType === st.id ? 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)' : 'var(--color-sc-bg)', color: schedType === st.id ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', cursor: 'pointer', fontFamily: 'var(--font-inter)', fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
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
            {CRON_PRESETS.map(p => (<button key={p.value} type="button" onClick={() => setSchedValue(p.value)} style={{ padding: '4px 10px', borderRadius: 20, fontSize: 11, cursor: 'pointer', border: `1px solid ${schedValue === p.value ? 'color-mix(in srgb, var(--color-sc-gold) 50%, transparent)' : 'var(--color-sc-border)'}`, background: schedValue === p.value ? 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)' : 'var(--color-sc-bg)', color: schedValue === p.value ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', fontFamily: 'var(--font-inter)' }}>{p.label}</button>))}
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
          }} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, border: 'none', background: 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 30%, transparent)', color: 'var(--color-sc-gold)', cursor: running ? 'default' : 'pointer', fontFamily: 'var(--font-grotesk)', fontSize: 12, fontWeight: 700 }} disabled={running}>
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
    <button key={id} onClick={() => { setTab(id); setCreating(false); }} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, border: `1px solid ${tab === id ? 'color-mix(in srgb, var(--color-sc-gold) 40%, transparent)' : 'transparent'}`, background: tab === id ? 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)' : 'transparent', color: tab === id ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 13, fontWeight: 600, fontFamily: 'var(--font-grotesk)', transition: 'all 0.15s' }}>
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
            onMouseEnter={e => e.currentTarget.style.background = 'color-mix(in srgb, var(--color-sc-gold) 22%, transparent)'}
            onMouseLeave={e => e.currentTarget.style.background = 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)'}>
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
