import { useState, useEffect, useCallback } from 'react';
import {
  Brain, Search, RefreshCw, MessageSquare, BookOpen,
  Clock, Star, User, ChevronDown, ChevronRight, X, FileText, FileCode2, Table2,
} from 'lucide-react';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function importanceBar(val) {
  const pct = Math.round((val ?? 0) * 100);
  const color = pct >= 70 ? '#22c55e' : pct >= 40 ? 'var(--color-sc-gold)' : 'rgba(255,255,255,0.2)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2, transition: 'width 0.3s' }} />
      </div>
      <span style={{ fontSize: 10, color: 'var(--color-sc-text-dim)', minWidth: 28 }}>{pct}%</span>
    </div>
  );
}

function timeAgo(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)   return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

// ─── Memory Card ─────────────────────────────────────────────────────────────

function MemoryCard({ item, type }) {
  const [expanded, setExpanded] = useState(false);
  const content  = item.content ?? '';
  const preview  = content.length > 200 ? content.slice(0, 200) + '…' : content;
  const isOricli = item.author === 'oricli';

  return (
    <div style={{
      background: 'var(--color-sc-bg-2)',
      border: `1px solid ${isOricli ? 'color-mix(in srgb, var(--color-sc-gold) 20%, transparent)' : 'var(--color-sc-border)'}`,
      borderRadius: 10,
      padding: '14px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        {/* Source badge */}
        <span style={{
          fontSize: 10, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase',
          padding: '2px 7px', borderRadius: 4,
          background: item.source === 'curiosity' ? 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)'
                     : item.source === 'conversation' ? 'rgba(136,117,255,0.12)'
                     : 'rgba(255,255,255,0.05)',
          color: item.source === 'curiosity' ? 'var(--color-sc-gold)'
               : item.source === 'conversation' ? '#818cf8'
               : 'var(--color-sc-text-muted)',
        }}>
          {type === 'knowledge' ? 'knowledge' : (item.source ?? 'memory')}
        </span>

        {/* Author badge */}
        {isOricli && (
          <span style={{
            fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 4,
            background: 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)',
            color: 'var(--color-sc-gold)',
            display: 'flex', alignItems: 'center', gap: 4,
          }}>
            <Brain size={9} /> Oricli
          </span>
        )}
        {!isOricli && item.author && (
          <span style={{
            fontSize: 10, padding: '2px 7px', borderRadius: 4,
            background: 'rgba(255,255,255,0.04)', color: 'var(--color-sc-text-dim)',
            display: 'flex', alignItems: 'center', gap: 4,
          }}>
            <User size={9} /> {item.author}
          </span>
        )}

        {/* Topic */}
        {item.topic && (
          <span style={{
            fontSize: 11, color: 'var(--color-sc-text-muted)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 220,
          }}>
            {item.topic}
          </span>
        )}

        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--color-sc-text-dim)', display: 'flex', alignItems: 'center', gap: 4 }}>
          <Clock size={9} /> {timeAgo(item.created)}
        </span>
      </div>

      {/* Importance bar (memories only) */}
      {item.importance != null && (
        <div>{importanceBar(item.importance)}</div>
      )}

      {/* Content */}
      <div style={{ fontSize: 12.5, lineHeight: 1.6, color: 'var(--color-sc-text-muted)' }}>
        {expanded ? content : preview}
      </div>

      {/* Expand / collapse */}
      {content.length > 200 && (
        <button
          onClick={() => setExpanded(e => !e)}
          style={{
            alignSelf: 'flex-start', background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--color-sc-gold)', fontSize: 11, display: 'flex', alignItems: 'center', gap: 4, padding: 0,
          }}
        >
          {expanded ? <><ChevronDown size={11} /> Show less</> : <><ChevronRight size={11} /> Show more</>}
        </button>
      )}
    </div>
  );
}

// ─── Tab Panel ────────────────────────────────────────────────────────────────

function TabPanel({ label, type, searchTopic }) {
  const [items, setItems]     = useState([]);
  const [total, setTotal]     = useState(0);
  const [page, setPage]       = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const perPage = 20;

  const load = useCallback(async (pg, append = false) => {
    setLoading(true);
    setError('');
    try {
      const base = type === 'knowledge' ? '/api/v1/memories/knowledge' : '/api/v1/memories';
      const params = new URLSearchParams({ page: pg, perPage });
      if (searchTopic) params.set('topic', searchTopic);
      if (type === 'conversation') params.set('source', 'conversation');
      if (type === 'curiosity')    params.set('source', 'curiosity');

      const r = await fetch(`${base}?${params}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setItems(prev => append ? [...prev, ...(d.items ?? [])] : (d.items ?? []));
      setTotal(d.total ?? 0);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [type, searchTopic]);

  // Reset + reload when search topic changes
  useEffect(() => {
    setPage(1);
    load(1, false);
  }, [load]);

  const loadMore = () => {
    const next = page + 1;
    setPage(next);
    load(next, true);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Stats bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12, color: 'var(--color-sc-text-dim)' }}>
        <span>{total} record{total !== 1 ? 's' : ''}</span>
        {loading && <span style={{ color: 'var(--color-sc-gold)' }}>Loading…</span>}
        {error && <span style={{ color: '#FF4D6D' }}>{error}</span>}
      </div>

      {/* Card grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {items.map(item => (
          <MemoryCard key={item.id} item={item} type={type} />
        ))}
      </div>

      {/* Empty state */}
      {!loading && items.length === 0 && !error && (
        <div style={{
          padding: '48px 24px', textAlign: 'center',
          color: 'var(--color-sc-text-dim)', fontSize: 13,
          border: '1px dashed var(--color-sc-border)', borderRadius: 10,
        }}>
          <Brain size={28} style={{ opacity: 0.3, marginBottom: 10 }} />
          <div>No {label.toLowerCase()} yet</div>
          <div style={{ fontSize: 11, marginTop: 4, opacity: 0.6 }}>
            {type === 'knowledge' ? "Oricli's curiosity burst will populate this." : 'Start chatting to build Oricli\'s memory.'}
          </div>
        </div>
      )}

      {/* Load More */}
      {items.length < total && !loading && (
        <button onClick={loadMore} style={{
          alignSelf: 'center', padding: '8px 24px',
          background: 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 20%, transparent)',
          borderRadius: 8, color: 'var(--color-sc-gold)', cursor: 'pointer', fontSize: 12,
        }}>
          Load more ({total - items.length} remaining)
        </button>
      )}
    </div>
  );
}

// ─── Documents Panel ──────────────────────────────────────────────────────────

const EXT_ICON = { pdf: FileText, md: FileCode2, csv: Table2, txt: FileText };
const EXT_COLOR = { pdf: 'rgba(255,100,100,0.7)', md: 'rgba(130,180,255,0.7)', csv: 'rgba(80,200,120,0.7)', txt: 'color-mix(in srgb, var(--color-sc-gold) 70%, transparent)' };

function DocumentsPanel() {
  const [docs, setDocs]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/v1/documents');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setDocs(d.documents ?? []);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div style={{ color: 'var(--color-sc-text-muted)', fontSize: 13, padding: '40px 0', textAlign: 'center' }}>Loading documents…</div>;
  if (error)   return <div style={{ color: '#FF4D6D', fontSize: 12, padding: 16 }}>Error: {error}</div>;

  if (docs.length === 0) return (
    <div style={{ padding: '60px 24px', textAlign: 'center' }}>
      <FileText size={32} color="rgba(255,255,255,0.1)" style={{ marginBottom: 12 }} />
      <p style={{ color: 'var(--color-sc-text-muted)', fontSize: 13, margin: 0 }}>No documents ingested yet.</p>
      <p style={{ color: 'var(--color-sc-text-dim)', fontSize: 11, marginTop: 6 }}>
        Use the 📎 button in chat to upload txt, md, csv, or pdf files.
      </p>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ fontSize: 12, color: 'var(--color-sc-text-dim)', marginBottom: 4 }}>
        {docs.length} document{docs.length !== 1 ? 's' : ''} in knowledge base
      </div>
      {docs.map(doc => {
        const ext = doc.filename?.split('.').pop()?.toLowerCase() ?? 'txt';
        const Icon = EXT_ICON[ext] ?? FileText;
        const color = EXT_COLOR[ext] ?? 'color-mix(in srgb, var(--color-sc-gold) 70%, transparent)';
        return (
          <div key={doc.id} style={{
            display: 'flex', alignItems: 'center', gap: 14,
            padding: '12px 16px', borderRadius: 10,
            background: 'rgba(255,255,255,0.025)',
            border: '1px solid rgba(255,255,255,0.07)',
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: 8, flexShrink: 0,
              background: color.replace('0.7)', '0.1)'),
              border: `1px solid ${color.replace('0.7)', '0.2)')}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Icon size={16} color={color} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-sc-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {doc.filename}
              </div>
              <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', marginTop: 2 }}>
                {doc.chunk_count} chunk{doc.chunk_count !== 1 ? 's' : ''} · {(doc.size_bytes / 1024).toFixed(1)} KB
                {doc.ingested_at && ` · ${new Date(doc.ingested_at).toLocaleString()}`}
              </div>
            </div>
            <span style={{
              fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
              color, background: color.replace('0.7)', '0.1)'),
              padding: '3px 8px', borderRadius: 5,
            }}>{ext}</span>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'conversation', label: 'Conversations', Icon: MessageSquare },
  { id: 'curiosity',    label: 'Curiosity',     Icon: Star },
  { id: 'knowledge',    label: 'Knowledge',     Icon: BookOpen },
  { id: 'documents',    label: 'Documents',     Icon: FileText },
];

export function MemoryBrowser() {
  const [activeTab,    setActiveTab]    = useState('conversation');
  const [searchInput,  setSearchInput]  = useState('');
  const [searchTopic,  setSearchTopic]  = useState('');
  const [refreshKey,   setRefreshKey]   = useState(0);

  const handleSearch = (e) => {
    e.preventDefault();
    setSearchTopic(searchInput.trim());
  };

  const clearSearch = () => {
    setSearchInput('');
    setSearchTopic('');
  };

  return (
    <div style={{
      flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column',
      background: 'var(--color-sc-bg)', color: 'var(--color-sc-text)',
    }}>
      {/* Page header */}
      <div style={{
        padding: '20px 28px 16px',
        borderBottom: '1px solid var(--color-sc-border)',
        display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
      }}>
        <Brain size={20} color="var(--color-sc-gold)" />
        <div>
          <div style={{ fontSize: 16, fontWeight: 600 }}>Memory Browser</div>
          <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', marginTop: 1 }}>
            Oricli's long-term memory — conversations, curiosity, knowledge
          </div>
        </div>

        {/* Search */}
        <form onSubmit={handleSearch} style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ position: 'relative' }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-sc-text-dim)', pointerEvents: 'none' }} />
            <input
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              placeholder="Filter by topic…"
              style={{
                paddingLeft: 30, paddingRight: searchInput ? 28 : 10, paddingTop: 7, paddingBottom: 7,
                background: 'var(--color-sc-bg-2)', border: '1px solid var(--color-sc-border)',
                borderRadius: 8, color: 'var(--color-sc-text)', fontSize: 12, outline: 'none', width: 200,
              }}
            />
            {searchInput && (
              <button type="button" onClick={clearSearch} style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: 0, display: 'flex' }}>
                <X size={12} />
              </button>
            )}
          </div>
          <button type="submit" style={{
            padding: '7px 14px', background: 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 25%, transparent)',
            borderRadius: 8, color: 'var(--color-sc-gold)', cursor: 'pointer', fontSize: 12,
          }}>
            Search
          </button>
        </form>

        <button
          onClick={() => setRefreshKey(k => k + 1)}
          title="Refresh"
          style={{ padding: 7, background: 'var(--color-sc-bg-2)', border: '1px solid var(--color-sc-border)', borderRadius: 8, cursor: 'pointer', color: 'var(--color-sc-text-muted)', display: 'flex' }}
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Tab strip */}
      <div style={{
        display: 'flex', gap: 0, borderBottom: '1px solid var(--color-sc-border)',
        padding: '0 28px',
      }}>
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '12px 18px', border: 'none', background: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: activeTab === id ? 600 : 400,
              color: activeTab === id ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
              borderBottom: `2px solid ${activeTab === id ? 'var(--color-sc-gold)' : 'transparent'}`,
              marginBottom: -1,
              transition: 'color 0.15s',
            }}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 28px' }}>
        {activeTab === 'documents' ? (
          <DocumentsPanel key={refreshKey} />
        ) : (
          <TabPanel
            key={`${activeTab}-${searchTopic}-${refreshKey}`}
            label={TABS.find(t => t.id === activeTab)?.label ?? ''}
            type={activeTab}
            searchTopic={searchTopic}
          />
        )}
      </div>
    </div>
  );
}
