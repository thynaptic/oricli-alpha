import { useState } from 'react';
import { useSCStore, selectActiveSession } from '../store';
import { Plus, MessageSquare, FolderOpen, Settings, Trash2, ChevronDown, ChevronRight } from 'lucide-react';

export function LeftSidebar({ onOpenSettings }) {
  const sessions = useSCStore(s => s.sessions);
  const activeSession = useSCStore(selectActiveSession);
  const newSession = useSCStore(s => s.newSession);
  const setActiveSession = useSCStore(s => s.setActiveSession);
  const renameSession = useSCStore(s => s.renameSession);
  const deleteSession = useSCStore(s => s.deleteSession);
  const goals = useSCStore(s => s.goals);
  const addGoal = useSCStore(s => s.addGoal);
  const removeGoal = useSCStore(s => s.removeGoal);
  const sidebarOpen = useSCStore(s => s.sidebarOpen);

  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [projectsOpen, setProjectsOpen] = useState(false);
  const [addingProject, setAddingProject] = useState(false);
  const [newProjectText, setNewProjectText] = useState('');
  const [hoveredId, setHoveredId] = useState(null);

  if (!sidebarOpen) return null;

  return (
    <aside style={{
      width: 240, flexShrink: 0,
      display: 'flex', flexDirection: 'column',
      background: 'var(--color-sc-surface)',
      borderRight: '1px solid var(--color-sc-border)',
      overflow: 'hidden',
    }}>
      {/* Brand */}
      <div style={{ padding: '16px 14px 10px', display: 'flex', alignItems: 'center', gap: 9 }}>
        <Logo size={24} />
        <span style={{
          fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 15,
          color: 'var(--color-sc-gold)', letterSpacing: '0.02em',
        }}>ORI Studio</span>
      </div>

      {/* New Chat */}
      <div style={{ padding: '4px 10px 10px' }}>
        <button
          onClick={newSession}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8,
            padding: '8px 12px', borderRadius: 8,
            background: 'transparent', border: '1px solid var(--color-sc-border2)',
            color: 'var(--color-sc-text)', cursor: 'pointer', fontSize: 13,
            fontFamily: 'var(--font-inter)', transition: 'border-color 0.15s, background 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--color-sc-gold)'; e.currentTarget.style.background = 'rgba(196,164,74,0.06)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--color-sc-border2)'; e.currentTarget.style.background = 'transparent'; }}
        >
          <Plus size={14} style={{ color: 'var(--color-sc-gold)', flexShrink: 0 }} />
          New chat
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 6px' }}>
        {/* Projects */}
        <div style={{ marginBottom: 4 }}>
          <button
            onClick={() => setProjectsOpen(v => !v)}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '5px 8px', borderRadius: 6, background: 'none', border: 'none',
              color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 11,
              fontFamily: 'var(--font-inter)', letterSpacing: '0.02em',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <FolderOpen size={12} />
              <span>Projects</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span
                onClick={e => { e.stopPropagation(); setAddingProject(true); setProjectsOpen(true); }}
                style={{ opacity: 0.6, cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                onMouseEnter={e => e.currentTarget.style.opacity = 1}
                onMouseLeave={e => e.currentTarget.style.opacity = 0.6}
              >
                <Plus size={11} />
              </span>
              {projectsOpen ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
            </div>
          </button>

          {projectsOpen && (
            <div style={{ padding: '2px 4px' }}>
              {addingProject && (
                <form onSubmit={e => {
                  e.preventDefault();
                  if (newProjectText.trim()) { addGoal(newProjectText.trim()); setNewProjectText(''); setAddingProject(false); }
                }}>
                  <input
                    autoFocus value={newProjectText}
                    onChange={e => setNewProjectText(e.target.value)}
                    onBlur={() => { if (!newProjectText.trim()) setAddingProject(false); }}
                    placeholder="Project name..."
                    style={{
                      width: '100%', background: 'var(--color-sc-surface2)',
                      border: '1px solid var(--color-sc-gold)', color: 'var(--color-sc-text)',
                      borderRadius: 6, padding: '5px 8px', fontSize: 12,
                      fontFamily: 'var(--font-inter)', outline: 'none', marginBottom: 2,
                    }}
                  />
                </form>
              )}
              {goals.length === 0 && !addingProject && (
                <div style={{ fontSize: 12, color: 'var(--color-sc-text-dim)', padding: '4px 8px' }}>No projects yet</div>
              )}
              {goals.map(g => (
                <div key={g.id}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '5px 8px',
                    borderRadius: 6, fontSize: 12.5, color: 'var(--color-sc-text-muted', cursor: 'default',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; setHoveredId('goal-' + g.id); }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; setHoveredId(null); }}
                >
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-sc-gold)', flexShrink: 0, opacity: 0.7 }} />
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.title}</span>
                  {hoveredId === 'goal-' + g.id && (
                    <button onClick={() => removeGoal(g.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: 0, display: 'flex' }}>
                      <Trash2 size={10} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recents label */}
        <div style={{
          padding: '8px 8px 4px', fontSize: 11, color: 'var(--color-sc-text-muted)',
          letterSpacing: '0.02em', display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <MessageSquare size={12} />
          <span>Recent</span>
        </div>

        {/* Chat list */}
        {sessions.map(session => (
          <div
            key={session.id}
            onClick={() => setActiveSession(session.id)}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; setHoveredId(session.id); }}
            onMouseLeave={e => { e.currentTarget.style.background = session.id === activeSession?.id ? 'rgba(196,164,74,0.1)' : 'transparent'; setHoveredId(null); }}
            style={{
              display: 'flex', alignItems: 'center', padding: '6px 10px', borderRadius: 7,
              cursor: 'pointer', marginBottom: 1,
              background: session.id === activeSession?.id ? 'rgba(196,164,74,0.1)' : 'transparent',
              color: session.id === activeSession?.id ? 'var(--color-sc-text)' : 'var(--color-sc-text-muted)',
              transition: 'background 0.12s',
            }}
          >
            {editingId === session.id ? (
              <input
                autoFocus value={editValue}
                onChange={e => setEditValue(e.target.value)}
                onBlur={() => { renameSession(session.id, editValue || session.title); setEditingId(null); }}
                onKeyDown={e => { if (e.key === 'Enter') { renameSession(session.id, editValue || session.title); setEditingId(null); } e.stopPropagation(); }}
                onClick={e => e.stopPropagation()}
                style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: 'inherit', fontSize: 13, fontFamily: 'var(--font-inter)' }}
              />
            ) : (
              <span
                style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 13 }}
                onDoubleClick={e => { e.stopPropagation(); setEditingId(session.id); setEditValue(session.title); }}
              >{session.title}</span>
            )}
            {hoveredId === session.id && editingId !== session.id && (
              <button
                onClick={e => { e.stopPropagation(); deleteSession(session.id); }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: 0, display: 'flex', flexShrink: 0 }}
              >
                <Trash2 size={11} />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{ padding: '8px 10px', borderTop: '1px solid var(--color-sc-border)' }}>
        <button
          onClick={onOpenSettings}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8,
            padding: '7px 10px', borderRadius: 7, background: 'none', border: 'none',
            color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 13,
            fontFamily: 'var(--font-inter)', transition: 'background 0.12s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
          onMouseLeave={e => e.currentTarget.style.background = 'none'}
        >
          <Settings size={14} />
          Settings
        </button>
      </div>
    </aside>
  );
}

function Logo({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M12 2 L14 8 L20 6 L16 11 L20 14 L14 13 L12 20 L10 13 L4 14 L8 11 L4 6 L10 8 Z" fill="#C4A44A" opacity="0.9" />
      <circle cx="12" cy="11" r="2" fill="#080810" />
    </svg>
  );
}
