import { useState, useEffect, useRef, useCallback } from 'react';
import { Plus, FileText, Trash2 } from 'lucide-react';

const STORE_KEY = 'ori-notebook-v1';
const API = '/api/notes';

function timeAgo(ts) {
  const diff = Date.now() - ts;
  if (diff < 60_000)    return 'just now';
  if (diff < 3600_000)  return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)}h ago`;
  return new Date(ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function NotebookPage() {
  const [notes,    setNotes]    = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [saving,   setSaving]   = useState(false);
  const saveTimer = useRef(null);
  const editorRef = useRef(null);

  const active = notes.find(n => n.id === activeId) || null;

  // Load from API on mount; fall back to localStorage migration
  useEffect(() => {
    fetch(API)
      .then(r => r.json())
      .then(({ notes: remote }) => {
        // Migrate any localStorage-only notes not yet on server
        let local = [];
        try { local = JSON.parse(localStorage.getItem(STORE_KEY)) || []; } catch {}
        const remoteIds = new Set(remote.map(n => n.id));
        const migrants  = local.filter(n => !remoteIds.has(n.id));
        if (migrants.length) {
          Promise.all(migrants.map(n =>
            fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' },
                         body: JSON.stringify({ title: n.title, content: n.content }) })
              .then(r => r.json())
          )).then(saved => {
            setNotes([...remote, ...saved].sort((a, b) => b.updatedAt - a.updatedAt));
            localStorage.removeItem(STORE_KEY);
          });
        } else {
          setNotes(remote);
        }
      })
      .catch(() => {
        // API unavailable — fall back to localStorage
        try { setNotes(JSON.parse(localStorage.getItem(STORE_KEY)) || []); } catch {}
      });
  }, []);

  async function newNote() {
    const res = await fetch(API, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: '', content: '' }),
    });
    const note = await res.json();
    setNotes(prev => [note, ...prev]);
    setActiveId(note.id);
    setTimeout(() => editorRef.current?.focus(), 50);
  }

  function updateNote(id, patch) {
    setNotes(prev => prev.map(n => n.id === id ? { ...n, ...patch, updatedAt: Date.now() } : n));
    // Debounce API save 800ms
    clearTimeout(saveTimer.current);
    setSaving(true);
    saveTimer.current = setTimeout(async () => {
      await fetch(`${API}/${id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      });
      setSaving(false);
    }, 800);
  }

  async function deleteNote(id) {
    await fetch(`${API}/${id}`, { method: 'DELETE' });
    setNotes(prev => prev.filter(n => n.id !== id));
    if (activeId === id) setActiveId(notes.find(n => n.id !== id)?.id || null);
  }

  const listStyle = {
    width: 240, flexShrink: 0,
    borderRight: '1px solid var(--color-sc-border)',
    display: 'flex', flexDirection: 'column',
    background: 'var(--color-sc-surface)',
    overflow: 'hidden',
  };

  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>

      {/* ── Left panel: note list ── */}
      <div style={listStyle}>
        <div style={{
          display: 'flex', alignItems: 'center', padding: '14px 16px',
          borderBottom: '1px solid var(--color-sc-border)', flexShrink: 0,
        }}>
          <span style={{ flex: 1, fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-grotesk)', color: 'var(--color-sc-text)' }}>
            Notebook
          </span>
          <button onClick={newNote} title="New note" style={{
            width: 28, height: 28, borderRadius: 8, border: 'none', cursor: 'pointer',
            background: 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)',
            color: 'var(--color-sc-gold)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Plus size={15} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {notes.length === 0 && (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--color-sc-text-dim)', fontSize: 12 }}>
              No notes yet.<br />
              <button onClick={newNote} style={{ marginTop: 10, background: 'none', border: 'none', color: 'var(--color-sc-gold)', cursor: 'pointer', fontSize: 12 }}>
                + New note
              </button>
            </div>
          )}
          {notes.map(n => {
            const isActive = n.id === activeId;
            const preview  = n.content?.split('\n').find(l => l.trim()) || '';
            return (
              <div key={n.id} onClick={() => setActiveId(n.id)} style={{
                padding: '12px 16px', cursor: 'pointer', borderBottom: '1px solid var(--color-sc-border)',
                background: isActive ? 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'transparent',
                borderLeft: isActive ? '2px solid var(--color-sc-gold)' : '2px solid transparent',
              }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-sc-text)', fontFamily: 'var(--font-grotesk)', marginBottom: 3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {n.title || 'Untitled'}
                </div>
                <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginBottom: 4 }}>
                  {preview || '—'}
                </div>
                <div style={{ fontSize: 10, color: 'var(--color-sc-text-dim)' }}>{timeAgo(n.updatedAt)}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Right panel: editor ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {active ? (
          <>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12, padding: '14px 32px',
              borderBottom: '1px solid var(--color-sc-border)', flexShrink: 0,
              background: 'var(--color-sc-surface)',
            }}>
              <input
                value={active.title}
                onChange={e => updateNote(active.id, { title: e.target.value })}
                placeholder="Untitled"
                style={{
                  flex: 1, background: 'none', border: 'none', outline: 'none',
                  fontSize: 18, fontWeight: 700, color: 'var(--color-sc-text)',
                  fontFamily: 'var(--font-grotesk)', letterSpacing: '-0.01em',
                }}
              />
              <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
                {saving ? 'Saving…' : timeAgo(active.updatedAt)}
              </span>
              <button onClick={() => deleteNote(active.id)} title="Delete note" style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--color-sc-text-dim)', padding: 4, borderRadius: 6,
              }}>
                <Trash2 size={15} />
              </button>
            </div>
            <textarea
              ref={editorRef}
              value={active.content}
              onChange={e => updateNote(active.id, { content: e.target.value })}
              placeholder="Start writing..."
              style={{
                flex: 1, resize: 'none', border: 'none', outline: 'none',
                background: 'var(--color-sc-bg)', color: 'var(--color-sc-text)',
                fontSize: 14, lineHeight: 1.75, fontFamily: 'var(--font-inter)',
                padding: '28px 32px', boxSizing: 'border-box',
              }}
            />
          </>
        ) : (
          <div style={{
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            gap: 12, color: 'var(--color-sc-text-dim)',
          }}>
            <FileText size={32} strokeWidth={1.2} style={{ opacity: 0.4 }} />
            <span style={{ fontSize: 14 }}>Select a note or create a new one</span>
            <button onClick={newNote} style={{
              display: 'flex', alignItems: 'center', gap: 7, padding: '9px 18px', borderRadius: 9,
              background: 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)',
              border: '1px solid color-mix(in srgb, var(--color-sc-gold) 25%, transparent)',
              color: 'var(--color-sc-gold)', fontSize: 13, fontWeight: 600,
              fontFamily: 'var(--font-grotesk)', cursor: 'pointer',
            }}>
              <Plus size={15} /> New note
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
