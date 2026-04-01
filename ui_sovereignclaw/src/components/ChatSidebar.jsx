import { useState } from 'react';
import { useSCStore, selectActiveSession } from '../store';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';

export function ChatSidebar() {
  const sessions = useSCStore(s => s.sessions);
  const activeSession = useSCStore(selectActiveSession);
  const newSession = useSCStore(s => s.newSession);
  const setActiveSession = useSCStore(s => s.setActiveSession);
  const renameSession = useSCStore(s => s.renameSession);
  const deleteSession = useSCStore(s => s.deleteSession);

  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [hoveredId, setHoveredId] = useState(null);

  return (
    <aside style={{
      width: 220, flexShrink: 0,
      background: 'var(--color-sc-surface)',
      borderRight: '1px solid var(--color-sc-border)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{ padding: '14px 12px 8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--color-sc-text-muted)' }}>
          <MessageSquare size={13} />
          <span style={{ fontWeight: 500 }}>Chats</span>
        </div>
        <button
          onClick={newSession}
          title="New chat"
          style={{
            background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-muted)',
            display: 'flex', alignItems: 'center', padding: 4, borderRadius: 6, transition: 'background 0.12s, color 0.12s',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)'; e.currentTarget.style.color = 'var(--color-sc-gold)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = 'var(--color-sc-text-muted)'; }}
        >
          <Plus size={15} />
        </button>
      </div>

      {/* Session list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 6px' }}>
        {sessions.map(session => (
          <div
            key={session.id}
            onClick={() => setActiveSession(session.id)}
            onMouseEnter={() => setHoveredId(session.id)}
            onMouseLeave={() => setHoveredId(null)}
            style={{
              display: 'flex', alignItems: 'center', padding: '7px 8px',
              borderRadius: 7, cursor: 'pointer', marginBottom: 1, gap: 8,
              background: session.id === activeSession?.id ? 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)' : hoveredId === session.id ? 'rgba(255,255,255,0.04)' : 'transparent',
              color: session.id === activeSession?.id ? 'var(--color-sc-text)' : 'var(--color-sc-text-muted)',
              transition: 'background 0.12s',
            }}
          >
            {editingId === session.id ? (
              <input autoFocus value={editValue}
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
              ><Trash2 size={11} /></button>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}
