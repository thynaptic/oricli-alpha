import React, { useState, useEffect, useCallback } from 'react';
import { Target, Zap, CheckCircle2, XCircle, Clock, RefreshCw, Plus, Trash2, ChevronRight, Activity, MoreHorizontal, Network, ChevronDown } from 'lucide-react';

const API = '/api/v1';
const GOLD = 'var(--color-sc-gold)';
const goldBg = (pct) => `color-mix(in srgb, var(--color-sc-gold) ${pct}%, transparent)`;

// ── Status config ──────────────────────────────────────────────────────────────
const STATUS = {
  pending:   { label: 'Pending',   color: 'rgba(120,120,160,0.9)', bg: 'rgba(120,120,160,0.1)', Icon: Clock },
  active:    { label: 'Active',    color: 'color-mix(in srgb, var(--color-sc-gold) 95%, transparent)', bg: 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)', Icon: Zap },
  completed: { label: 'Completed', color: 'rgba(80,200,120,0.9)',  bg: 'rgba(80,200,120,0.1)',  Icon: CheckCircle2 },
  failed:    { label: 'Failed',    color: 'rgba(220,80,80,0.9)',   bg: 'rgba(220,80,80,0.1)',   Icon: XCircle },
};

const DAEMON_COLOR = { active: GOLD, idle: 'rgba(120,120,160,0.8)', running: 'rgba(80,200,120,0.85)' };

// ── Daemon health row ──────────────────────────────────────────────────────────
function DaemonRow({ daemon }) {
  const color = DAEMON_COLOR[daemon.status] ?? DAEMON_COLOR.idle;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, padding: '8px 14px',
      borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
    }}>
      <div style={{
        width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0,
        boxShadow: daemon.status === 'active' ? `0 0 6px ${color}` : 'none',
        animation: daemon.status === 'active' ? 'eri-pulse 1.5s ease-in-out infinite' : 'none',
      }} />
      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-sc-text)', minWidth: 130 }}>
        {daemon.name}
      </span>
      <span style={{
        fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--color-sc-text-dim)',
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }}>
        {daemon.detail}
      </span>
      <span style={{
        marginLeft: 'auto', fontSize: 10, fontWeight: 600, letterSpacing: '0.05em',
        color, textTransform: 'uppercase', flexShrink: 0,
      }}>
        {daemon.status}
      </span>
    </div>
  );
}

// ── Objective card ─────────────────────────────────────────────────────────────
const STATUS_TRANSITIONS = {
  pending:   ['active', 'completed', 'failed'],
  active:    ['completed', 'failed', 'pending'],
  completed: ['pending'],
  failed:    ['pending'],
};

function ObjectiveCard({ obj, all, onDelete, onStatusChange }) {
  const cfg = STATUS[obj.status] ?? STATUS.pending;
  const { Icon } = cfg;
  const [menuOpen, setMenuOpen] = useState(false);

  const deps = (obj.depends_on ?? []).map(depId => {
    const dep = all.find(o => o.id === depId);
    return dep ? dep.goal : depId;
  });

  return (
    <div style={{
      borderRadius: 12, padding: '14px 16px',
      background: 'rgba(255,255,255,0.025)',
      border: `1px solid ${obj.status === 'active' ? goldBg(30) : 'rgba(255,255,255,0.07)'}`,
      transition: 'border-color 0.2s',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 8 }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          padding: '3px 8px', borderRadius: 6, flexShrink: 0,
          background: cfg.bg, color: cfg.color, fontSize: 10, fontWeight: 700, letterSpacing: '0.05em',
        }}>
          <Icon size={10} />
          {cfg.label.toUpperCase()}
        </div>

        {obj.priority > 0 && (
          <span style={{
            fontSize: 10, color: goldBg(70), fontFamily: 'var(--font-mono)',
            background: goldBg(8), padding: '3px 7px', borderRadius: 5,
          }}>
            P{obj.priority}
          </span>
        )}

        {obj.retry_count > 0 && (
          <span style={{ fontSize: 10, color: 'rgba(220,160,80,0.7)', fontFamily: 'var(--font-mono)', marginLeft: 2 }}>
            ↺{obj.retry_count}
          </span>
        )}

        <button
          onClick={() => onDelete(obj.id)}
          title="Delete objective"
          style={{
            marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--color-sc-text-muted)', padding: 2, borderRadius: 4,
            opacity: 0.5, transition: 'opacity 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.opacity = 1}
          onMouseLeave={e => e.currentTarget.style.opacity = 0.5}
        >
          <Trash2 size={13} />
        </button>

        {/* Status transition menu */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setMenuOpen(v => !v)}
            title="Change status"
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--color-sc-text-muted)', padding: 2, borderRadius: 4,
              opacity: 0.5, transition: 'opacity 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.opacity = 1}
            onMouseLeave={e => e.currentTarget.style.opacity = 0.5}
          >
            <MoreHorizontal size={13} />
          </button>
          {menuOpen && (
            <div
              style={{
                position: 'absolute', right: 0, top: '100%', zIndex: 100,
                background: 'var(--color-sc-surface)', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 8, padding: '4px 0', minWidth: 130, boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
              }}
              onMouseLeave={() => setMenuOpen(false)}
            >
              {(STATUS_TRANSITIONS[obj.status] ?? []).map(s => {
                const c = STATUS[s];
                const SI = c?.Icon;
                return (
                  <button
                    key={s}
                    onClick={() => { setMenuOpen(false); onStatusChange(obj.id, s); }}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      width: '100%', padding: '7px 14px', background: 'none', border: 'none',
                      cursor: 'pointer', fontSize: 12, color: c?.color ?? 'var(--color-sc-text)',
                      textAlign: 'left', transition: 'background 0.1s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'none'}
                  >
                    {SI && <SI size={11} />}
                    Mark {s}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Goal text */}
      <p style={{ fontSize: 13, color: 'var(--color-sc-text)', lineHeight: 1.6, margin: '0 0 8px' }}>
        {obj.goal}
      </p>

      {/* Progress bar */}
      {obj.status === 'active' && (
        <div style={{ height: 2, background: 'rgba(255,255,255,0.08)', borderRadius: 2, margin: '8px 0' }}>
          <div style={{
            height: '100%', borderRadius: 2,
            background: goldBg(70),
            width: `${Math.round((obj.progress ?? 0) * 100)}%`,
            transition: 'width 0.5s ease',
          }} />
        </div>
      )}

      {/* Dependencies */}
      {deps.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
          <span style={{ fontSize: 10, color: 'var(--color-sc-text-muted)' }}>Waits for:</span>
          {deps.map((d, i) => (
            <span key={i} style={{
              fontSize: 10, color: 'var(--color-sc-text-dim)',
              background: 'rgba(255,255,255,0.04)', padding: '2px 7px', borderRadius: 4,
              border: '1px solid rgba(255,255,255,0.08)',
            }}>
              <ChevronRight size={8} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 2 }} />
              {d.length > 40 ? d.slice(0, 40) + '…' : d}
            </span>
          ))}
        </div>
      )}

      {/* Timestamps */}
      <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
        {obj.created_at && (
          <span style={{ fontSize: 10, color: 'var(--color-sc-text-muted)', fontFamily: 'var(--font-mono)' }}>
            Created {new Date(obj.created_at).toLocaleString()}
          </span>
        )}
        {obj.updated_at && obj.updated_at !== obj.created_at && (
          <span style={{ fontSize: 10, color: 'var(--color-sc-text-muted)', fontFamily: 'var(--font-mono)' }}>
            · Updated {new Date(obj.updated_at).toLocaleString()}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Add Goal modal ─────────────────────────────────────────────────────────────
function AddGoalModal({ onClose, onAdd }) {
  const [goal, setGoal] = useState('');
  const [priority, setPriority] = useState(5);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!goal.trim()) return;
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/goals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: goal.trim(), priority }),
      });
      if (r.ok) { onAdd(); onClose(); }
    } finally { setSubmitting(false); }
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 500,
      background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div style={{
        background: 'var(--color-sc-surface)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 25%, transparent)',
        borderRadius: 16, padding: 28, width: 480, maxWidth: '90vw',
      }} onClick={e => e.stopPropagation()}>
        <h3 style={{ margin: '0 0 20px', color: 'var(--color-sc-text)', fontSize: 16, fontWeight: 700 }}>
          New Sovereign Objective
        </h3>

        <textarea
          autoFocus
          value={goal}
          onChange={e => setGoal(e.target.value)}
          placeholder="Describe the objective Oricli should work toward autonomously…"
          style={{
            width: '100%', minHeight: 100, background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '10px 12px',
            color: 'var(--color-sc-text)', fontSize: 13, lineHeight: 1.6, resize: 'vertical',
            fontFamily: 'var(--font-inter)', outline: 'none', boxSizing: 'border-box',
          }}
          onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit(); }}
        />

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 14 }}>
          <label style={{ fontSize: 12, color: 'var(--color-sc-text-muted)', flexShrink: 0 }}>Priority</label>
          <input
            type="range" min={1} max={10} value={priority}
            onChange={e => setPriority(Number(e.target.value))}
            style={{ flex: 1 }}
          />
          <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', color: GOLD, minWidth: 20 }}>
            {priority}
          </span>
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 20, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{
            padding: '8px 18px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)',
            background: 'transparent', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 13,
          }}>
            Cancel
          </button>
          <button onClick={submit} disabled={submitting || !goal.trim()} style={{
            padding: '8px 18px', borderRadius: 8, border: 'none',
            background: goldBg(15), color: GOLD, cursor: 'pointer', fontSize: 13, fontWeight: 600,
            opacity: submitting || !goal.trim() ? 0.5 : 1,
          }}>
            {submitting ? 'Adding…' : 'Add Objective'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Sovereign Goal (DAG) components ───────────────────────────────────────────

const SG_STATUS = {
  pending:   { color: 'rgba(120,120,160,0.9)', bg: 'rgba(120,120,160,0.08)', Icon: Clock, label: 'Pending' },
  running:   { color: 'color-mix(in srgb, var(--color-sc-gold) 95%, transparent)', bg: goldBg(8), Icon: Zap, label: 'Running' },
  completed: { color: 'rgba(80,200,120,0.9)',  bg: 'rgba(80,200,120,0.08)',  Icon: CheckCircle2, label: 'Done' },
  failed:    { color: 'rgba(220,80,80,0.9)',   bg: 'rgba(220,80,80,0.08)',   Icon: XCircle, label: 'Failed' },
  cancelled: { color: 'rgba(160,120,120,0.9)', bg: 'rgba(160,120,120,0.08)', Icon: XCircle, label: 'Cancelled' },
};

function SovereignGoalCard({ dag, onCancel }) {
  const [open, setOpen] = useState(false);
  const sg = SG_STATUS[dag.status] ?? SG_STATUS.pending;
  const SgIcon = sg.Icon;
  const done = dag.nodes?.filter(n => n.status === 'completed').length ?? 0;
  const total = dag.nodes?.length ?? 0;

  return (
    <div style={{
      background: 'var(--color-sc-surface)', border: `1px solid ${open ? goldBg(20) : 'var(--color-sc-border)'}`,
      borderRadius: 10, overflow: 'hidden', transition: 'border-color 0.15s',
    }}>
      {/* Header */}
      <div onClick={() => setOpen(o => !o)} style={{
        padding: '12px 16px', cursor: 'pointer', display: 'flex', alignItems: 'flex-start', gap: 12,
      }}>
        <SgIcon size={16} style={{ color: sg.color, flexShrink: 0, marginTop: 2 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-sc-text)', marginBottom: 4, lineHeight: 1.4 }}>
            {dag.objective}
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 10.5, padding: '2px 7px', borderRadius: 8, background: sg.bg, color: sg.color, fontWeight: 600 }}>
              {sg.label}
            </span>
            {total > 0 && (
              <span style={{ fontSize: 10.5, color: 'var(--color-sc-text-muted)' }}>
                {done}/{total} steps
              </span>
            )}
            {dag.tick_count > 0 && (
              <span style={{ fontSize: 10.5, color: 'var(--color-sc-text-dim)' }}>
                {dag.tick_count} ticks
              </span>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
          {dag.status === 'running' || dag.status === 'pending' ? (
            <button onClick={e => { e.stopPropagation(); onCancel(dag.id); }} title="Cancel plan"
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '3px 6px', borderRadius: 5, color: 'var(--color-sc-text-muted)', fontSize: 11 }}
              onMouseEnter={e => e.currentTarget.style.color = 'var(--color-sc-danger)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--color-sc-text-muted)'}
            >
              <XCircle size={13} />
            </button>
          ) : null}
          <ChevronDown size={14} style={{ color: 'var(--color-sc-text-muted)', transform: open ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.15s' }} />
        </div>
      </div>

      {/* Execution timeline */}
      {open && dag.nodes?.length > 0 && (
        <div style={{ borderTop: '1px solid var(--color-sc-border)', padding: '12px 16px 16px', display: 'flex', flexDirection: 'column', gap: 0 }}>
          {dag.nodes.map((node, i) => {
            const ns = SG_STATUS[node.status] ?? SG_STATUS.pending;
            const NIcon = ns.Icon;
            const isLast = i === dag.nodes.length - 1;
            return (
              <div key={node.id} style={{ display: 'flex', gap: 12 }}>
                {/* Connector line */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 16, flexShrink: 0 }}>
                  <div style={{
                    width: 16, height: 16, borderRadius: '50%', background: ns.bg,
                    border: `1.5px solid ${ns.color}`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0, marginTop: 2,
                  }}>
                    <NIcon size={8} style={{ color: ns.color }} />
                  </div>
                  {!isLast && <div style={{ width: 1.5, flex: 1, background: 'var(--color-sc-border)', minHeight: 12 }} />}
                </div>
                {/* Node content */}
                <div style={{ flex: 1, paddingBottom: isLast ? 0 : 10 }}>
                  <div style={{ fontSize: 12.5, color: 'var(--color-sc-text)', lineHeight: 1.45 }}>
                    {node.description}
                  </div>
                  {node.result && (
                    <div style={{ fontSize: 11.5, color: 'var(--color-sc-text-muted)', marginTop: 4, background: 'var(--color-sc-bg)', padding: '4px 8px', borderRadius: 5, fontFamily: 'var(--font-mono)' }}>
                      {node.result.length > 120 ? node.result.slice(0, 120) + '…' : node.result}
                    </div>
                  )}
                  {node.depends_on?.length > 0 && (
                    <div style={{ fontSize: 10.5, color: 'var(--color-sc-text-dim)', marginTop: 3 }}>
                      depends on: {node.depends_on.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {dag.final_answer && (
            <div style={{ marginTop: 12, padding: '10px 12px', background: goldBg(6), border: `1px solid ${goldBg(20)}`, borderRadius: 8 }}>
              <div style={{ fontSize: 10, color: GOLD, fontWeight: 600, marginBottom: 4, letterSpacing: '0.06em' }}>FINAL ANSWER</div>
              <div style={{ fontSize: 13, color: 'var(--color-sc-text)', lineHeight: 1.5 }}>{dag.final_answer}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AddSovereignGoalModal({ onClose, onAdd }) {
  const [objective, setObjective] = useState('');
  const [context, setContext] = useState('');
  const [maxNodes, setMaxNodes] = useState(6);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    if (!objective.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch(`${API}/sovereign/goals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ objective: objective.trim(), context: context.trim(), max_nodes: maxNodes }),
      });
      if (!r.ok) { const d = await r.json(); throw new Error(d.error || 'Failed'); }
      const dag = await r.json();
      onAdd(dag);
      onClose();
    } catch (e) { setError(e.message); } finally { setSubmitting(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 14, padding: '28px', width: 480, maxWidth: '90vw', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-sc-text)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Network size={16} style={{ color: GOLD }} /> New Sovereign Plan
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <label style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Objective</label>
          <textarea value={objective} onChange={e => setObjective(e.target.value)}
            placeholder="What should ORI accomplish?"
            rows={3}
            style={{ background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)', borderRadius: 8, padding: '10px 12px', fontSize: 13, color: 'var(--color-sc-text)', resize: 'none', outline: 'none', fontFamily: 'var(--font-inter)' }}
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <label style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Context (optional)</label>
          <input value={context} onChange={e => setContext(e.target.value)}
            placeholder="Additional context or constraints…"
            style={{ background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)', borderRadius: 8, padding: '10px 12px', fontSize: 13, color: 'var(--color-sc-text)', outline: 'none', fontFamily: 'var(--font-inter)' }}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <label style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Max Steps</label>
          <input type="number" min={2} max={12} value={maxNodes} onChange={e => setMaxNodes(+e.target.value)}
            style={{ width: 60, background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)', borderRadius: 6, padding: '6px 10px', fontSize: 13, color: 'var(--color-sc-text)', outline: 'none', textAlign: 'center' }}
          />
        </div>
        {error && <div style={{ fontSize: 12, color: 'var(--color-sc-danger)' }}>{error}</div>}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{ padding: '8px 16px', borderRadius: 7, border: '1px solid var(--color-sc-border)', background: 'transparent', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 13 }}>
            Cancel
          </button>
          <button onClick={submit} disabled={submitting || !objective.trim()} style={{
            padding: '8px 18px', borderRadius: 7, border: 'none', background: GOLD, color: '#fff',
            cursor: submitting ? 'default' : 'pointer', fontSize: 13, fontWeight: 600, opacity: submitting ? 0.7 : 1,
          }}>
            {submitting ? 'Planning…' : 'Create Plan'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
const TABS = ['all', 'active', 'pending', 'completed', 'failed', 'plans'];

export function GoalsPage() {
  const [goals, setGoals]             = useState([]);
  const [sovereignGoals, setSovGoals] = useState([]);
  const [daemons, setDaemons]         = useState([]);
  const [tab, setTab]                 = useState('all');
  const [loading, setLoading]         = useState(true);
  const [showAdd, setShowAdd]         = useState(false);
  const [showAddSov, setShowAddSov]   = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchGoals = useCallback(async () => {
    try {
      const r = await fetch(`${API}/goals`);
      if (r.ok) { const d = await r.json(); setGoals(d.goals ?? []); }
    } catch { /* silent */ }
  }, []);

  const fetchSovGoals = useCallback(async () => {
    try {
      const r = await fetch(`${API}/sovereign/goals`);
      if (r.ok) { const d = await r.json(); setSovGoals(d.goals ?? []); }
    } catch { /* silent */ }
  }, []);

  const fetchDaemons = useCallback(async () => {
    try {
      const r = await fetch(`${API}/daemons`);
      if (r.ok) { const d = await r.json(); setDaemons(d.daemons ?? []); }
    } catch { /* silent */ }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchGoals(), fetchDaemons(), fetchSovGoals()]);
    setLoading(false);
    setLastRefresh(new Date());
  }, [fetchGoals, fetchDaemons, fetchSovGoals]);

  useEffect(() => { refresh(); }, [refresh]);

  // Auto-refresh every 30s
  useEffect(() => {
    const id = setInterval(refresh, 30_000);
    return () => clearInterval(id);
  }, [refresh]);

  const handleDelete = async (id) => {
    await fetch(`${API}/goals/${id}`, { method: 'DELETE' });
    await fetchGoals();
  };

  const handleCancelSov = async (id) => {
    await fetch(`${API}/sovereign/goals/${id}`, { method: 'DELETE' });
    await fetchSovGoals();
  };

  const handleStatusChange = async (id, status) => {
    // Optimistic update
    setGoals(prev => prev.map(g => g.id === id ? { ...g, status } : g));
    try {
      await fetch(`${API}/goals/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
    } catch { /* revert on error */ await fetchGoals(); }
  };

  const filtered = tab === 'all' ? goals : tab === 'plans' ? [] : goals.filter(g => g.status === tab);
  const counts = TABS.reduce((acc, t) => {
    if (t === 'plans') { acc[t] = sovereignGoals.length; return acc; }
    acc[t] = t === 'all' ? goals.length : goals.filter(g => g.status === t).length;
    return acc;
  }, {});
  const activeCount = counts.active ?? 0;

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '28px 32px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10, flexShrink: 0,
          background: goldBg(10), border: `1px solid ${goldBg(20)}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Target size={18} color={GOLD} />
        </div>
        <div>
          <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--color-sc-text)' }}>
            Mission Control
          </h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--color-sc-text-muted)' }}>
            Sovereign goal queue · autonomous DAG execution
          </p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          {lastRefresh && (
            <span style={{ fontSize: 10, color: 'var(--color-sc-text-muted)', fontFamily: 'var(--font-mono)' }}>
              {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <button onClick={refresh} title="Refresh" style={{
            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 8, padding: '7px 10px', cursor: 'pointer', color: 'var(--color-sc-text-muted)',
            display: 'flex', alignItems: 'center', gap: 5, fontSize: 12,
          }}>
            <RefreshCw size={13} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
          <button onClick={() => setShowAdd(true)} style={{
            background: goldBg(12), border: `1px solid ${goldBg(25)}`,
            borderRadius: 8, padding: '7px 14px', cursor: 'pointer', color: GOLD,
            display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600,
          }}>
            <Plus size={13} />
            New Objective
          </button>
          <button onClick={() => setShowAddSov(true)} style={{
            background: 'color-mix(in srgb, var(--color-sc-blue) 12%, transparent)',
            border: '1px solid color-mix(in srgb, var(--color-sc-blue) 30%, transparent)',
            borderRadius: 8, padding: '7px 14px', cursor: 'pointer',
            color: 'var(--color-sc-blue)',
            display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600,
          }}>
            <Network size={13} />
            New Plan
          </button>
        </div>
      </div>

      {/* Daemon health panel */}
      {daemons.length > 0 && (
        <div style={{
          borderRadius: 14, border: '1px solid rgba(255,255,255,0.07)',
          background: 'rgba(255,255,255,0.015)', padding: '14px 16px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <Activity size={13} color={goldBg(70)} />
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-sc-text-muted)', letterSpacing: '0.06em' }}>
              DAEMON HEALTH
            </span>
            {activeCount > 0 && (
              <span style={{
                fontSize: 10, background: goldBg(15), color: GOLD,
                padding: '2px 8px', borderRadius: 5, fontWeight: 700,
              }}>
                {activeCount} ACTIVE
              </span>
            )}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 8 }}>
            {daemons.map(d => <DaemonRow key={d.name} daemon={d} />)}
          </div>
        </div>
      )}

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid rgba(255,255,255,0.07)', paddingBottom: 0 }}>
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer', padding: '8px 14px',
              fontSize: 12, fontWeight: tab === t ? 700 : 400, letterSpacing: '0.02em',
              color: tab === t ? GOLD : 'var(--color-sc-text-muted)',
              borderBottom: tab === t ? `2px solid ${goldBg(80)}` : '2px solid transparent',
              marginBottom: -1, textTransform: 'capitalize', transition: 'color 0.15s',
            }}
          >
            {t} {counts[t] > 0 && <span style={{ fontSize: 10, opacity: 0.7 }}>({counts[t]})</span>}
          </button>
        ))}
      </div>

      {/* Goal cards */}
      {tab !== 'plans' && (
        loading && goals.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--color-sc-text-muted)', padding: '40px 0', fontSize: 13 }}>
            Loading objectives…
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Target size={32} color="rgba(255,255,255,0.1)" style={{ marginBottom: 12 }} />
            <p style={{ color: 'var(--color-sc-text-muted)', fontSize: 13, margin: 0 }}>
              {tab === 'all' ? 'No objectives yet. Add one to start autonomous execution.' : `No ${tab} objectives.`}
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {filtered.map(obj => (
              <ObjectiveCard key={obj.id} obj={obj} all={goals} onDelete={handleDelete} onStatusChange={handleStatusChange} />
            ))}
          </div>
        )
      )}

      {/* Sovereign Plans (DAG timeline) */}
      {tab === 'plans' && (
        sovereignGoals.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Network size={32} color="rgba(255,255,255,0.1)" style={{ marginBottom: 12 }} />
            <p style={{ color: 'var(--color-sc-text-muted)', fontSize: 13, margin: 0 }}>
              No sovereign plans yet. Click <strong style={{ color: GOLD }}>New Plan</strong> to create a multi-step execution DAG.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {sovereignGoals.map(dag => (
              <SovereignGoalCard key={dag.id} dag={dag} onCancel={handleCancelSov} />
            ))}
          </div>
        )
      )}

      {showAdd && <AddGoalModal onClose={() => setShowAdd(false)} onAdd={fetchGoals} />}
      {showAddSov && <AddSovereignGoalModal onClose={() => setShowAddSov(false)} onAdd={dag => { setSovGoals(prev => [dag, ...prev]); setTab('plans'); }} />}
    </div>
  );
}
