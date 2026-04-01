import { useState } from 'react';

const ACTION_ICONS = {
  research:  '🔍',
  fetch:     '🌐',
  summarize: '📝',
  compare:   '⚖️',
  generate:  '✨',
  save:      '💾',
};

const STATUS_ICONS = {
  pending:  { icon: '○',  cls: 'text-zinc-500' },
  running:  { icon: '⟳',  cls: 'text-blue-400 animate-spin' },
  done:     { icon: '✓',  cls: 'text-emerald-400' },
  failed:   { icon: '✗',  cls: 'text-red-400' },
};

export default function TaskPlanCard({ tasks }) {
  const [collapsed, setCollapsed] = useState(false);

  if (!tasks || tasks.length === 0) return null;

  const done  = tasks.filter(t => t.status === 'done').length;
  const total = tasks.length;
  const allDone = done === total;
  const hasFailed = tasks.some(t => t.status === 'failed');

  const progressPct = Math.round((done / total) * 100);

  return (
    <div style={{
      margin: '8px 0', borderRadius: 12, overflow: 'hidden', fontSize: 13,
      border: '1px solid var(--color-sc-border2)',
      background: 'var(--color-sc-surface2)',
    }}>
      {/* Header */}
      <button
        onClick={() => setCollapsed(c => !c)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 16px', background: 'transparent', border: 'none',
          cursor: 'pointer', color: 'var(--color-sc-text)', transition: 'background 0.12s',
        }}
        onMouseEnter={e => e.currentTarget.style.background = 'color-mix(in srgb, var(--color-sc-gold) 6%, transparent)'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
      >
        <span style={{ fontSize: 15 }}>📋</span>
        <span style={{ fontWeight: 600, flex: 1, textAlign: 'left', color: 'var(--color-sc-text)' }}>
          {allDone
            ? 'Plan complete'
            : hasFailed
            ? 'Plan — some steps failed'
            : `Planning… ${done}/${total}`}
        </span>
        {!allDone && (
          <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>{progressPct}%</span>
        )}
        <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', marginLeft: 4 }}>{collapsed ? '▸' : '▾'}</span>
      </button>

      {/* Progress bar */}
      {!allDone && (
        <div style={{ height: 2, background: 'var(--color-sc-border)' }}>
          <div
            style={{ height: '100%', background: 'var(--color-sc-blue)', width: `${progressPct}%`, transition: 'width 0.3s' }}
          />
        </div>
      )}

      {/* Task list */}
      {!collapsed && (
        <ul style={{ listStyle: 'none', margin: 0, padding: '8px 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {tasks.map((task) => {
            const si = STATUS_ICONS[task.status] ?? STATUS_ICONS.pending;
            const actionIcon = ACTION_ICONS[task.action] ?? '▸';
            const statusColor = task.status === 'done' ? 'var(--color-sc-success)'
              : task.status === 'failed' ? 'var(--color-sc-danger)'
              : task.status === 'running' ? 'var(--color-sc-blue)'
              : 'var(--color-sc-text-dim)';
            return (
              <li key={task.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <span style={{ fontFamily: 'monospace', fontSize: 11, width: 12, flexShrink: 0, marginTop: 1, color: statusColor }}>
                  {si.icon}
                </span>
                <span style={{ flexShrink: 0, fontSize: 11 }}>{actionIcon}</span>
                <span style={{ flex: 1, lineHeight: 1.5, color: task.status === 'done' ? 'var(--color-sc-text-muted)' : 'var(--color-sc-text)' }}>
                  {task.title}
                </span>
                {task.snippet && task.status === 'done' && (
                  <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {task.snippet}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
