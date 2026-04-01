import React, { useState, useEffect, useCallback } from 'react';
import { Target, Zap, CheckCircle2, XCircle, Clock, RefreshCw, Plus, Trash2, ChevronRight, Activity, MoreHorizontal } from 'lucide-react';

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

// ── Main page ──────────────────────────────────────────────────────────────────
const TABS = ['all', 'active', 'pending', 'completed', 'failed'];

export function GoalsPage() {
  const [goals, setGoals]       = useState([]);
  const [daemons, setDaemons]   = useState([]);
  const [tab, setTab]           = useState('all');
  const [loading, setLoading]   = useState(true);
  const [showAdd, setShowAdd]   = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchGoals = useCallback(async () => {
    try {
      const r = await fetch(`${API}/goals`);
      if (r.ok) { const d = await r.json(); setGoals(d.goals ?? []); }
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
    await Promise.all([fetchGoals(), fetchDaemons()]);
    setLoading(false);
    setLastRefresh(new Date());
  }, [fetchGoals, fetchDaemons]);

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

  const filtered = tab === 'all' ? goals : goals.filter(g => g.status === tab);
  const counts = TABS.reduce((acc, t) => {
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
      {loading && goals.length === 0 ? (
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
      )}

      {showAdd && <AddGoalModal onClose={() => setShowAdd(false)} onAdd={fetchGoals} />}
    </div>
  );
}
