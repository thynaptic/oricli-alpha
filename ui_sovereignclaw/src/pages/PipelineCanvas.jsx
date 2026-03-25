import { useState, useCallback, useEffect, useRef } from 'react';
import {
  ReactFlow, ReactFlowProvider, Background, Controls, MiniMap,
  addEdge, useNodesState, useEdgesState, useReactFlow,
  MarkerType, Panel, Handle, Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  GitMerge, Play, Square, Plus, Trash2, Save, ChevronLeft,
  Loader2, CheckCircle2, AlertCircle, Clock, Workflow, X,
  GripVertical, ChevronDown, ChevronRight, ArrowUp, ArrowDown,
} from 'lucide-react';
import { useSCStore } from '../store';

// ── Step type config ──────────────────────────────────────────────────────────
const STEP_TYPES = [
  { value: 'prompt',       label: 'Prompt',       color: '#7c9ef8' },
  { value: 'template',     label: 'Template',     color: '#a89cf7' },
  { value: 'summarize',    label: 'Summarize',    color: '#5ec4a8' },
  { value: 'condition',    label: 'Condition',    color: '#f0a070' },
  { value: 'web',          label: 'Web Search',   color: '#f0c070' },
  { value: 'fetch_url',    label: 'Fetch URL',    color: '#f0c070' },
  { value: 'code',         label: 'Code',         color: '#e07070' },
  { value: 'sub_workflow', label: 'Sub-workflow', color: '#a89cf7' },
];
const STEP_TYPE_COLOR = Object.fromEntries(STEP_TYPES.map(s => [s.value, s.color]));

// ── WorkflowDrawer ────────────────────────────────────────────────────────────
function WorkflowDrawer({ wfId, onClose, onSaved }) {
  const [wf, setWf]           = useState(null);
  const [name, setName]       = useState('');
  const [steps, setSteps]     = useState([]);
  const [expanded, setExpanded] = useState(null); // step index
  const [saving, setSaving]   = useState(false);
  const [dirty, setDirty]     = useState(false);

  useEffect(() => {
    if (!wfId) return;
    fetch('/workflows').then(r => r.json()).then(d => {
      const found = (d.workflows || []).find(w => w.id === wfId);
      if (found) {
        setWf(found);
        setName(found.name || '');
        setSteps((found.steps || []).map((s, i) => ({ ...s, _id: i })));
        setDirty(false);
      }
    });
  }, [wfId]);

  function mark() { setDirty(true); }

  function updateStep(idx, patch) {
    setSteps(prev => prev.map((s, i) => i === idx ? { ...s, ...patch } : s));
    mark();
  }

  function addStep() {
    setSteps(prev => {
      const ns = [...prev, { _id: Date.now(), type: 'prompt', name: '', value: '' }];
      setExpanded(ns.length - 1);
      return ns;
    });
    mark();
  }

  function removeStep(idx) {
    setSteps(prev => prev.filter((_, i) => i !== idx));
    if (expanded === idx) setExpanded(null);
    mark();
  }

  function moveStep(idx, dir) {
    const next = idx + dir;
    if (next < 0 || next >= steps.length) return;
    setSteps(prev => {
      const a = [...prev];
      [a[idx], a[next]] = [a[next], a[idx]];
      return a;
    });
    setExpanded(next);
    mark();
  }

  async function save() {
    if (!wf || !dirty) return;
    setSaving(true);
    const cleaned = steps.map(({ _id, ...rest }) => rest);
    await fetch(`/workflows/${wf.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, steps: cleaned }),
    });
    setSaving(false);
    setDirty(false);
    onSaved?.({ ...wf, name, steps: cleaned });
  }

  if (!wf) return (
    <div style={DRAWER_STYLE}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', borderBottom: '1px solid var(--color-sc-border)' }}>
        <span style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 800, fontSize: 13, color: 'var(--color-sc-text)' }}>Loading…</span>
        <button onClick={onClose} style={ICON_BTN}><X size={14} /></button>
      </div>
    </div>
  );

  return (
    <div style={DRAWER_STYLE}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 14px', borderBottom: '1px solid var(--color-sc-border)', flexShrink: 0 }}>
        <Workflow size={13} style={{ color: 'var(--color-sc-gold)', flexShrink: 0 }} />
        <input
          value={name}
          onChange={e => { setName(e.target.value); mark(); }}
          style={{
            flex: 1, background: 'transparent', border: 'none', outline: 'none',
            fontFamily: 'var(--font-grotesk)', fontWeight: 800, fontSize: 13,
            color: 'var(--color-sc-text)',
          }}
        />
        <button onClick={onClose} style={ICON_BTN}><X size={13} /></button>
      </div>

      {/* Steps list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
        {steps.length === 0 && (
          <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--color-sc-text-dim)', fontSize: 12 }}>
            No steps yet.<br />Hit + to add one.
          </div>
        )}
        {steps.map((step, idx) => {
          const isOpen = expanded === idx;
          const typeColor = STEP_TYPE_COLOR[step.type] ?? 'var(--color-sc-border)';
          return (
            <div key={step._id} style={{ margin: '2px 8px', borderRadius: 8, border: `1px solid ${isOpen ? typeColor + '88' : 'var(--color-sc-border)'}`, overflow: 'hidden', transition: 'border-color 0.15s' }}>
              {/* Row header */}
              <div
                onClick={() => setExpanded(isOpen ? null : idx)}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 10px', cursor: 'pointer', background: isOpen ? 'var(--color-sc-surface2)' : 'transparent' }}
              >
                <span style={{ fontSize: 9, fontWeight: 800, fontFamily: 'var(--font-grotesk)', color: 'var(--color-sc-text-dim)', minWidth: 14, textAlign: 'right' }}>{idx + 1}</span>
                <span style={{ fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 4, background: typeColor + '22', color: typeColor, fontFamily: 'var(--font-grotesk)', flexShrink: 0 }}>
                  {STEP_TYPES.find(t => t.value === step.type)?.label ?? step.type}
                </span>
                <span style={{ flex: 1, fontSize: 11, color: 'var(--color-sc-text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {step.name || step.value?.slice(0, 60) || '—'}
                </span>
                {isOpen ? <ChevronDown size={11} style={{ color: 'var(--color-sc-text-dim)', flexShrink: 0 }} /> : <ChevronRight size={11} style={{ color: 'var(--color-sc-text-dim)', flexShrink: 0 }} />}
              </div>

              {/* Expanded editor */}
              {isOpen && (
                <div style={{ padding: '10px 12px', borderTop: `1px solid ${typeColor}44`, background: 'var(--color-sc-bg)', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {/* Type + Name row */}
                  <div style={{ display: 'flex', gap: 6 }}>
                    <select
                      value={step.type}
                      onChange={e => updateStep(idx, { type: e.target.value })}
                      style={{ fontSize: 11, background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 5, color: 'var(--color-sc-text)', padding: '3px 6px', flex: '0 0 auto', fontFamily: 'var(--font-grotesk)' }}
                    >
                      {STEP_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                    <input
                      value={step.name || ''}
                      onChange={e => updateStep(idx, { name: e.target.value })}
                      placeholder="Step label (optional)"
                      style={{ flex: 1, fontSize: 11, background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 5, color: 'var(--color-sc-text)', padding: '3px 7px', outline: 'none', fontFamily: 'var(--font-grotesk)' }}
                    />
                  </div>

                  {/* Value textarea */}
                  <textarea
                    value={step.value || ''}
                    onChange={e => updateStep(idx, { value: e.target.value })}
                    placeholder={step.type === 'prompt' ? 'Enter prompt… use {{output}} for prior step' : step.type === 'condition' ? 'Condition expression…' : 'Value…'}
                    rows={4}
                    style={{
                      width: '100%', boxSizing: 'border-box', resize: 'vertical',
                      fontSize: 11, lineHeight: 1.5, fontFamily: 'var(--font-mono)',
                      background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)',
                      borderRadius: 6, color: 'var(--color-sc-text)', padding: '6px 8px', outline: 'none',
                    }}
                  />

                  {/* Actions */}
                  <div style={{ display: 'flex', gap: 4, justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button onClick={() => moveStep(idx, -1)} disabled={idx === 0} style={MINI_BTN} title="Move up"><ArrowUp size={11} /></button>
                      <button onClick={() => moveStep(idx, 1)} disabled={idx === steps.length - 1} style={MINI_BTN} title="Move down"><ArrowDown size={11} /></button>
                    </div>
                    <button onClick={() => removeStep(idx)} style={{ ...MINI_BTN, color: 'var(--color-sc-danger)' }} title="Delete step"><Trash2 size={11} /></button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{ padding: '10px 14px', borderTop: '1px solid var(--color-sc-border)', display: 'flex', gap: 8, flexShrink: 0 }}>
        <button onClick={addStep} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5, padding: '6px 0', borderRadius: 7, border: '1px dashed var(--color-sc-border)', background: 'transparent', cursor: 'pointer', color: 'var(--color-sc-text-dim)', fontSize: 11, fontFamily: 'var(--font-grotesk)', fontWeight: 600 }}>
          <Plus size={11} /> Add step
        </button>
        <button onClick={save} disabled={!dirty || saving} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '6px 14px', borderRadius: 7, border: 'none', cursor: dirty ? 'pointer' : 'default', background: dirty ? 'var(--color-sc-gold)' : 'var(--color-sc-surface2)', color: dirty ? '#fff' : 'var(--color-sc-text-dim)', fontFamily: 'var(--font-grotesk)', fontWeight: 800, fontSize: 11, transition: 'all 0.15s' }}>
          {saving ? <Loader2 size={11} style={{ animation: 'ori-spin 1s linear infinite' }} /> : <Save size={11} />} Save
        </button>
      </div>
    </div>
  );
}

const DRAWER_STYLE = {
  width: 290, flexShrink: 0, display: 'flex', flexDirection: 'column',
  background: 'var(--color-sc-surface)', borderLeft: '1px solid var(--color-sc-border)',
  overflow: 'hidden',
};
const ICON_BTN = { background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: 3, display: 'flex', borderRadius: 5 };
const MINI_BTN = { background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 5, cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: '3px 6px', display: 'flex', alignItems: 'center' };

// ── Status colours ────────────────────────────────────────────────────────────
const STATUS_COLOR = {
  pending:  'var(--color-sc-border)',
  running:  'var(--color-sc-gold)',
  done:     'var(--color-sc-success)',
  error:    'var(--color-sc-danger)',
  skipped:  'var(--color-sc-text-dim)',
};
const STATUS_ICON = {
  pending: Clock,
  running: Loader2,
  done:    CheckCircle2,
  error:   AlertCircle,
  skipped: Clock,
};

// ── WorkflowNode (custom node) ────────────────────────────────────────────────
function WorkflowNode({ data }) {
  const { label, stepCount, status = 'pending', output } = data;
  const Icon = STATUS_ICON[status] ?? Clock;
  const color = STATUS_COLOR[status] ?? 'var(--color-sc-border)';
  const spinning = status === 'running';
  const [showOut, setShowOut] = useState(false);

  const handleStyle = {
    width: 10, height: 10,
    background: 'var(--color-sc-surface)',
    border: `2px solid ${color}`,
    borderRadius: '50%',
    transition: 'background 0.15s, transform 0.15s',
  };

  return (
    <div
      onClick={() => output && setShowOut(v => !v)}
      style={{
        minWidth: 180, maxWidth: 240,
        background: 'var(--color-sc-surface)',
        border: `1.5px solid ${color}`,
        borderRadius: 12,
        padding: '10px 14px',
        cursor: output ? 'pointer' : 'default',
        boxShadow: status === 'running'
          ? `0 0 16px ${color}55, 0 2px 8px rgba(0,0,0,0.4)`
          : '0 2px 8px rgba(0,0,0,0.3)',
        transition: 'border-color 0.3s, box-shadow 0.3s',
        position: 'relative',
      }}
    >
      {/* Target handle — left side (receives connections) */}
      <Handle
        type="target"
        position={Position.Left}
        style={handleStyle}
      />

      {/* Source handle — right side (drag from here to connect) */}
      <Handle
        type="source"
        position={Position.Right}
        style={handleStyle}
      />

      {/* Status ring pulse */}
      {status === 'running' && (
        <div style={{
          position: 'absolute', inset: -4, borderRadius: 15,
          border: `1.5px solid ${color}`,
          animation: 'pipelinePulse 1.5s ease-in-out infinite',
          pointerEvents: 'none',
        }} />
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Icon
          size={14}
          style={{
            color,
            flexShrink: 0,
            animation: spinning ? 'ori-spin 1s linear infinite' : 'none',
          }}
        />
        <span style={{
          fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 13,
          color: 'var(--color-sc-text)', flex: 1, overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {label}
        </span>
      </div>

      <div style={{ marginTop: 4, fontSize: 10, color: 'var(--color-sc-text-dim)' }}>
        {stepCount} step{stepCount !== 1 ? 's' : ''}
        {status !== 'pending' && (
          <span style={{ marginLeft: 8, color, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {status}
          </span>
        )}
      </div>

      {showOut && output && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, zIndex: 100,
          marginTop: 8, background: 'var(--color-sc-surface2)',
          border: '1px solid var(--color-sc-border)',
          borderRadius: 10, padding: '10px 12px',
          maxWidth: 360, maxHeight: 220, overflow: 'auto',
          fontSize: 11, color: 'var(--color-sc-text)',
          fontFamily: 'var(--font-mono)',
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          whiteSpace: 'pre-wrap', lineHeight: 1.5,
        }}>
          {output.slice(0, 600)}{output.length > 600 ? '\n…' : ''}
        </div>
      )}
    </div>
  );
}

const NODE_TYPES = { workflowNode: WorkflowNode };

// ── Default edge style ────────────────────────────────────────────────────────
const EDGE_DEFAULTS = {
  style: { stroke: 'var(--color-sc-border)', strokeWidth: 2 },
  markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-sc-gold)' },
  animated: false,
};

// ── PipelineCanvas page ───────────────────────────────────────────────────────
function PipelineCanvasInner() {
  const [pipelines, setPipelines]   = useState([]);
  const [activePipe, setActivePipe] = useState(null); // full pipeline obj
  const [workflows, setWorkflows]   = useState([]);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [runId, setRunId]           = useState(null);
  const [nodeStatuses, setNodeStatuses] = useState({});
  const [running, setRunning]       = useState(false);
  const [dirty, setDirty]           = useState(false);
  const [namingNew, setNamingNew]   = useState(false);
  const [newName, setNewName]       = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [drawerWfId, setDrawerWfId] = useState(null); // open workflow drawer
  const pollRef = useRef(null);
  const dragWfRef = useRef(null);
  const { screenToFlowPosition, fitView } = useReactFlow();

  // Load pipelines + workflows on mount
  useEffect(() => {
    fetch('/pipelines').then(r => r.json()).then(d => setPipelines(d.pipelines || []));
    fetch('/workflows').then(r => r.json()).then(d => setWorkflows(d.workflows || []));
  }, []);

  // Open a pipeline
  function openPipeline(pipe) {
    setActivePipe(pipe);
    setNodeStatuses({});
    setRunId(null);
    setRunning(false);
    // Hydrate nodes from saved data
    const hydrated = (pipe.nodes || []).map(n => ({
      id:       n.id,
      type:     'workflowNode',
      position: n.position || { x: 100, y: 100 },
      data: {
        label:     n.data?.label || 'Workflow',
        wfId:      n.data?.wfId,
        stepCount: n.data?.stepCount ?? 0,
        status:    'pending',
        output:    '',
      },
    }));
    setNodes(hydrated);
    setEdges(pipe.edges || []);
    setDirty(false);
    // Fit view to existing nodes after a tick (only for saved pipelines with nodes)
    if (hydrated.length > 0) {
      setTimeout(() => fitView({ padding: 0.15, duration: 300 }), 50);
    }
  }

  // Save current canvas state to backend
  async function savePipeline() {
    if (!activePipe) return;
    const payload = {
      ...activePipe,
      nodes: nodes.map(n => ({ id: n.id, position: n.position, data: n.data })),
      edges,
    };
    const res = await fetch(`/pipelines/${activePipe.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const updated = await res.json();
    setActivePipe(updated);
    setPipelines(prev => prev.map(p => p.id === updated.id ? updated : p));
    setDirty(false);
  }

  // Create new pipeline
  async function createPipeline() {
    const name = newName.trim() || 'New Pipeline';
    const res = await fetch('/pipelines', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    const pipe = await res.json();
    setPipelines(prev => [...prev, pipe]);
    setNamingNew(false);
    setNewName('');
    openPipeline(pipe);
  }

  async function deletePipeline(id) {
    await fetch(`/pipelines/${id}`, { method: 'DELETE' });
    setPipelines(prev => prev.filter(p => p.id !== id));
    if (activePipe?.id === id) { setActivePipe(null); setNodes([]); setEdges([]); }
  }

  // Drag a workflow from sidebar → drop onto canvas
  function onDragOver(e) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }
  function onDrop(e) {
    e.preventDefault();
    const wf = dragWfRef.current;
    if (!wf) return;
    // Convert screen coordinates to React Flow canvas coordinates (respects zoom/pan)
    const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
    const newNode = {
      id:   `node_${Date.now()}`,
      type: 'workflowNode',
      position,
      data: { label: wf.name, wfId: wf.id, stepCount: wf.steps?.length ?? 0, status: 'pending', output: '' },
    };
    setNodes(prev => [...prev, newNode]);
    setDirty(true);
    dragWfRef.current = null;
  }

  const onConnect = useCallback((params) => {
    setEdges(prev => addEdge({
      ...params,
      ...EDGE_DEFAULTS,
    }, prev));
    setDirty(true);
  }, []);

  function onNodeClick(_e, node) {
    setDrawerWfId(node.data?.wfId ?? null);
  }

  function onNodesChangeDirty(changes) {
    onNodesChange(changes);
    if (changes.some(c => c.type === 'position' || c.type === 'remove')) setDirty(true);
  }
  function onEdgesChangeDirty(changes) {
    onEdgesChange(changes);
    if (changes.some(c => c.type === 'remove')) setDirty(true);
  }

  // When drawer saves, refresh node step counts + workflow list
  function onDrawerSaved(updated) {
    setWorkflows(prev => prev.map(w => w.id === updated.id ? updated : w));
    setNodes(prev => prev.map(n =>
      n.data?.wfId === updated.id
        ? { ...n, data: { ...n.data, stepCount: updated.steps?.length ?? 0, label: updated.name } }
        : n
    ));
  }

  // Run pipeline
  async function runPipeline() {
    if (!activePipe || running) return;
    // Auto-save first
    await savePipeline();
    setRunning(true);
    setNodeStatuses({});
    // Reset node statuses visually
    setNodes(prev => prev.map(n => ({ ...n, data: { ...n.data, status: 'pending', output: '' } })));

    const res = await fetch(`/pipelines/${activePipe.id}/run`, { method: 'POST' });
    const { run_id } = await res.json();
    setRunId(run_id);

    // Poll for status
    pollRef.current = setInterval(async () => {
      try {
        const sr = await fetch(`/pipelines/runs/${run_id}`);
        const data = await sr.json();
        const statuses = data.node_statuses || {};
        setNodeStatuses(statuses);
        // Sync into React Flow node data
        setNodes(prev => prev.map(n => {
          const ns = statuses[n.id];
          if (!ns) return n;
          return { ...n, data: { ...n.data, status: ns.status, output: ns.output || '' } };
        }));
        if (data.status === 'done' || data.status === 'error' || data.status === 'cancelled') {
          clearInterval(pollRef.current);
          setRunning(false);
        }
      } catch (_) {}
    }, 1200);
  }

  function stopRun() {
    clearInterval(pollRef.current);
    setRunning(false);
  }

  useEffect(() => () => clearInterval(pollRef.current), []);

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flex: 1, height: '100%', width: '100%', background: 'var(--color-sc-bg)', overflow: 'hidden' }}>

      {/* ── Left sidebar: pipeline list + workflow palette ── */}
      {sidebarOpen && (
        <div style={{
          width: 220, flexShrink: 0, display: 'flex', flexDirection: 'column',
          background: 'var(--color-sc-surface)', borderRight: '1px solid var(--color-sc-border)',
          overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{
            padding: '12px 14px 8px', borderBottom: '1px solid var(--color-sc-border)',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <GitMerge size={14} style={{ color: 'var(--color-sc-gold)' }} />
            <span style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 800, fontSize: 13, color: 'var(--color-sc-text)' }}>
              Pipelines
            </span>
            <button
              onClick={() => setNamingNew(true)}
              title="New pipeline"
              style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-gold)', padding: 2, display: 'flex' }}
            ><Plus size={14} /></button>
          </div>

          {/* New pipeline name input */}
          {namingNew && (
            <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--color-sc-border)', display: 'flex', gap: 6 }}>
              <input
                autoFocus
                value={newName}
                onChange={e => setNewName(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') createPipeline(); if (e.key === 'Escape') { setNamingNew(false); setNewName(''); } }}
                placeholder="Pipeline name…"
                style={{
                  flex: 1, background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)',
                  borderRadius: 6, padding: '4px 8px', color: 'var(--color-sc-text)', fontSize: 12,
                  outline: 'none',
                }}
              />
              <button onClick={createPipeline} style={{ background: 'var(--color-sc-gold)', border: 'none', borderRadius: 6, padding: '4px 8px', color: '#fff', cursor: 'pointer', fontSize: 11, fontWeight: 700 }}>
                OK
              </button>
            </div>
          )}

          {/* Pipeline list */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '6px 0' }}>
            {pipelines.length === 0 && (
              <div style={{ padding: '20px 14px', textAlign: 'center', color: 'var(--color-sc-text-dim)', fontSize: 12 }}>
                No pipelines yet.<br />Click + to create one.
              </div>
            )}
            {pipelines.map(p => (
              <div key={p.id}
                onClick={() => openPipeline(p)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px',
                  cursor: 'pointer', borderRadius: 7, margin: '0 4px',
                  background: activePipe?.id === p.id ? 'rgba(196,164,74,0.1)' : 'transparent',
                  borderLeft: activePipe?.id === p.id ? '2px solid var(--color-sc-gold)' : '2px solid transparent',
                }}
                onMouseEnter={e => { if (activePipe?.id !== p.id) e.currentTarget.style.background = 'rgba(128,128,128,0.08)'; }}
                onMouseLeave={e => { if (activePipe?.id !== p.id) e.currentTarget.style.background = 'transparent'; }}
              >
                <Workflow size={12} style={{ color: 'var(--color-sc-gold)', flexShrink: 0 }} />
                <span style={{ flex: 1, fontSize: 12, color: 'var(--color-sc-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {p.name}
                </span>
                <button
                  onClick={e => { e.stopPropagation(); deletePipeline(p.id); }}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: 2, display: 'flex', flexShrink: 0, opacity: 0.5 }}
                  onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                  onMouseLeave={e => e.currentTarget.style.opacity = '0.5'}
                ><Trash2 size={11} /></button>
              </div>
            ))}
          </div>

          {/* Divider */}
          {activePipe && (
            <>
              <div style={{ borderTop: '1px solid var(--color-sc-border)', padding: '8px 14px 4px' }}>
                <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-sc-text-dim)' }}>
                  Workflows — drag to canvas
                </span>
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '4px 4px 8px' }}>
                {workflows.map(wf => (
                  <div
                    key={wf.id}
                    draggable
                    onDragStart={() => { dragWfRef.current = wf; }}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '6px 10px', margin: '2px 0', borderRadius: 7,
                      border: '1px solid var(--color-sc-border)',
                      background: 'var(--color-sc-bg)',
                      cursor: 'grab', userSelect: 'none',
                    }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-sc-gold)'}
                    onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--color-sc-border)'}
                  >
                    <GitMerge size={11} style={{ color: 'var(--color-sc-text-dim)', flexShrink: 0 }} />
                    <span style={{ fontSize: 11, color: 'var(--color-sc-text)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {wf.name}
                    </span>
                    <span style={{ fontSize: 9, color: 'var(--color-sc-text-dim)' }}>{wf.steps?.length ?? 0}s</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Canvas area ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Toolbar */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px',
          borderBottom: '1px solid var(--color-sc-border)',
          background: 'var(--color-sc-surface)', flexShrink: 0,
        }}>
          <button
            onClick={() => setSidebarOpen(v => !v)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: 4, display: 'flex', borderRadius: 6 }}
            title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
          >
            <ChevronLeft size={14} style={{ transform: sidebarOpen ? 'none' : 'rotate(180deg)', transition: 'transform 0.2s' }} />
          </button>

          {activePipe ? (
            <>
              <span style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 800, fontSize: 14, color: 'var(--color-sc-text)' }}>
                {activePipe.name}
              </span>
              {dirty && (
                <span style={{ fontSize: 10, color: 'var(--color-sc-text-dim)', fontStyle: 'italic' }}>unsaved</span>
              )}

              <div style={{ flex: 1 }} />

              {/* Save */}
              <button onClick={savePipeline} disabled={!dirty}
                style={{
                  display: 'flex', alignItems: 'center', gap: 5, padding: '5px 12px',
                  borderRadius: 8, border: 'none', cursor: dirty ? 'pointer' : 'default',
                  background: dirty ? 'rgba(196,164,74,0.12)' : 'transparent',
                  color: dirty ? 'var(--color-sc-gold)' : 'var(--color-sc-text-dim)',
                  fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 12,
                  transition: 'all 0.15s',
                }}>
                <Save size={12} /> Save
              </button>

              {/* Run / Stop */}
              {!running ? (
                <button onClick={runPipeline}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '6px 16px',
                    borderRadius: 8, border: 'none', cursor: 'pointer',
                    background: 'var(--color-sc-gold)', color: '#fff',
                    fontFamily: 'var(--font-grotesk)', fontWeight: 800, fontSize: 12,
                    boxShadow: '0 2px 8px rgba(196,164,74,0.35)',
                  }}>
                  <Play size={12} fill="currentColor" /> Run
                </button>
              ) : (
                <button onClick={stopRun}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px',
                    borderRadius: 8, border: 'none', cursor: 'pointer',
                    background: 'var(--color-sc-danger)', color: '#fff',
                    fontFamily: 'var(--font-grotesk)', fontWeight: 800, fontSize: 12,
                  }}>
                  <Square size={12} fill="currentColor" /> Stop
                </button>
              )}
            </>
          ) : (
            <>
              <span style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 13, color: 'var(--color-sc-text-dim)' }}>
                Select or create a pipeline
              </span>
              <div style={{ flex: 1 }} />
            </>
          )}
        </div>

        {/* React Flow canvas + workflow drawer */}
        {activePipe ? (
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
            <div style={{ flex: 1, overflow: 'hidden' }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={NODE_TYPES}
              onNodesChange={onNodesChangeDirty}
              onEdgesChange={onEdgesChangeDirty}
              onConnect={onConnect}
              onNodeClick={onNodeClick}
              defaultEdgeOptions={EDGE_DEFAULTS}
              onDrop={onDrop}
              onDragOver={onDragOver}
              defaultViewport={{ x: 80, y: 80, zoom: 1 }}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="var(--color-sc-border)" gap={20} size={1} />
              <Controls style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)' }} />
              <MiniMap
                nodeColor={n => STATUS_COLOR[n.data?.status] ?? 'var(--color-sc-border)'}
                style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)' }}
              />
              <Panel position="top-right" style={{ margin: 12 }}>
                {running && (
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px',
                    background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-gold)',
                    borderRadius: 8, fontSize: 12, color: 'var(--color-sc-gold)',
                    fontFamily: 'var(--font-grotesk)', fontWeight: 700,
                    boxShadow: '0 0 12px rgba(196,164,74,0.2)',
                  }}>
                    <Loader2 size={12} style={{ animation: 'ori-spin 1s linear infinite' }} />
                    Running…
                  </div>
                )}
              </Panel>
            </ReactFlow>
            </div>
            {/* Workflow editor drawer */}
            {drawerWfId && (
              <WorkflowDrawer
                wfId={drawerWfId}
                onClose={() => setDrawerWfId(null)}
                onSaved={onDrawerSaved}
              />
            )}
          </div>
        ) : (
          <div style={{
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', color: 'var(--color-sc-text-dim)', gap: 12,
          }}>
            <GitMerge size={40} style={{ opacity: 0.2 }} />
            <span style={{ fontSize: 14, fontFamily: 'var(--font-grotesk)', fontWeight: 600, opacity: 0.5 }}>
              Select a pipeline from the sidebar to start building
            </span>
            <button onClick={() => setNamingNew(true)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '8px 18px',
                borderRadius: 8, border: '1px solid var(--color-sc-border)', cursor: 'pointer',
                background: 'transparent', color: 'var(--color-sc-text-muted)',
                fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 13,
              }}>
              <Plus size={13} /> New Pipeline
            </button>
          </div>
        )}
      </div>

      {/* ── CSS keyframes injected once ── */}
      <style>{`
        @keyframes pipelinePulse {
          0%, 100% { opacity: 0.4; transform: scale(1); }
          50% { opacity: 0.9; transform: scale(1.02); }
        }
        /* Handle hover — glow + scale */
        .react-flow__handle:hover {
          background: var(--color-sc-gold) !important;
          border-color: var(--color-sc-gold) !important;
          transform: scale(1.5);
          box-shadow: 0 0 6px var(--color-sc-gold);
        }
        /* Live connection line while dragging */
        .react-flow__connection-line {
          stroke: var(--color-sc-gold);
          stroke-width: 2;
          stroke-dasharray: 6 3;
        }
        /* React Flow edge path color */
        .react-flow__edge-path {
          stroke: var(--color-sc-border);
          stroke-width: 2;
        }
        .react-flow__edge.selected .react-flow__edge-path,
        .react-flow__edge:hover .react-flow__edge-path {
          stroke: var(--color-sc-gold);
        }
        /* Arrow marker */
        .react-flow__arrowhead polyline {
          stroke: var(--color-sc-gold);
          fill: var(--color-sc-gold);
        }
      `}</style>
    </div>
  );
}

// Wrap with ReactFlowProvider so useReactFlow() works inside PipelineCanvasInner
// The provider must forward flex sizing so the inner layout fills the viewport
export default function PipelineCanvas() {
  return (
    <ReactFlowProvider>
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', height: '100%', width: '100%' }}>
        <PipelineCanvasInner />
      </div>
    </ReactFlowProvider>
  );
}
