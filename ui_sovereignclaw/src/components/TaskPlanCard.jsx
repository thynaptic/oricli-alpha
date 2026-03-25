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
    <div className="my-2 rounded-xl border border-zinc-700/60 bg-zinc-900/70 backdrop-blur-sm overflow-hidden text-sm">
      {/* Header */}
      <button
        onClick={() => setCollapsed(c => !c)}
        className="w-full flex items-center gap-2 px-4 py-2.5 hover:bg-zinc-800/50 transition-colors"
      >
        <span className="text-base">📋</span>
        <span className="font-semibold text-zinc-200 flex-1 text-left">
          {allDone
            ? 'Plan complete'
            : hasFailed
            ? 'Plan — some steps failed'
            : `Planning… ${done}/${total}`}
        </span>
        {!allDone && (
          <span className="text-xs text-zinc-500">{progressPct}%</span>
        )}
        <span className="text-zinc-500 text-xs ml-1">{collapsed ? '▸' : '▾'}</span>
      </button>

      {/* Progress bar */}
      {!allDone && (
        <div className="h-0.5 bg-zinc-800">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      )}

      {/* Task list */}
      {!collapsed && (
        <ul className="px-4 py-2 space-y-1.5">
          {tasks.map((task) => {
            const si = STATUS_ICONS[task.status] ?? STATUS_ICONS.pending;
            const actionIcon = ACTION_ICONS[task.action] ?? '▸';
            return (
              <li key={task.id} className="flex items-start gap-2.5">
                {/* Status icon */}
                <span className={`mt-0.5 font-mono text-xs w-3 shrink-0 ${si.cls} ${task.status === 'running' ? 'inline-block' : ''}`}>
                  {si.icon}
                </span>
                {/* Action badge */}
                <span className="shrink-0 text-xs">{actionIcon}</span>
                {/* Title */}
                <span className={`flex-1 leading-snug ${task.status === 'done' ? 'text-zinc-400' : 'text-zinc-200'}`}>
                  {task.title}
                </span>
                {/* Snippet on done */}
                {task.snippet && task.status === 'done' && (
                  <span className="text-zinc-600 text-xs max-w-[180px] truncate hidden sm:block">
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
