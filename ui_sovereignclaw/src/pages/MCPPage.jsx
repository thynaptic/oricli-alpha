import { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, Edit2, Check, X, RefreshCw, ToggleLeft, ToggleRight, ChevronDown, ChevronRight, Plug, Terminal, AlertCircle } from 'lucide-react';

// ── Common MCP server templates ───────────────────────────────────────────────
const TEMPLATES = [
  {
    id: 'github', name: 'GitHub', description: 'Access GitHub repos, issues, PRs and code search',
    command: 'npx', args: ['-y', '@modelcontextprotocol/server-github'],
    env: { GITHUB_PERSONAL_ACCESS_TOKEN: '' },
  },
  {
    id: 'filesystem', name: 'Filesystem', description: 'Read & write local files and directories',
    command: 'npx', args: ['-y', '@modelcontextprotocol/server-filesystem', '/home/mike'],
    env: {},
  },
  {
    id: 'brave_search', name: 'Brave Search', description: 'Web search via Brave Search API',
    command: 'npx', args: ['-y', '@modelcontextprotocol/server-brave-search'],
    env: { BRAVE_API_KEY: '' },
  },
  {
    id: 'fetch', name: 'Fetch / HTTP', description: 'Fetch and read any URL',
    command: 'npx', args: ['-y', '@modelcontextprotocol/server-fetch'],
    env: {},
  },
  {
    id: 'memory', name: 'Memory', description: 'Persistent key-value memory for agents',
    command: 'npx', args: ['-y', '@modelcontextprotocol/server-memory'],
    env: {},
  },
  {
    id: 'postgres', name: 'PostgreSQL', description: 'Query and mutate a Postgres database',
    command: 'npx', args: ['-y', '@modelcontextprotocol/server-postgres', 'postgresql://localhost/mydb'],
    env: {},
  },
  {
    id: 'sqlite', name: 'SQLite', description: 'Query a local SQLite database file',
    command: 'npx', args: ['-y', '@modelcontextprotocol/server-sqlite', '--db-path', '/tmp/data.db'],
    env: {},
  },
  {
    id: 'puppeteer', name: 'Browser (Puppeteer)', description: 'Headless browser — screenshot, interact, scrape',
    command: 'npx', args: ['-y', '@modelcontextprotocol/server-puppeteer'],
    env: {},
  },
];

// ── Shared styles ─────────────────────────────────────────────────────────────
const S = {
  label: { fontSize: 12, fontWeight: 600, color: 'var(--color-sc-text-muted)', fontFamily: 'var(--font-grotesk)', marginBottom: 5, display: 'block' },
  input: {
    width: '100%', background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)',
    borderRadius: 8, padding: '8px 11px', color: 'var(--color-sc-text)',
    fontFamily: 'var(--font-inter)', fontSize: 13, outline: 'none', boxSizing: 'border-box',
  },
};

// ── Env var editor ────────────────────────────────────────────────────────────
function EnvEditor({ env, onChange }) {
  const pairs = Object.entries(env || {});
  function set(k, v) { onChange({ ...env, [k]: v }); }
  function remove(k) { const next = { ...env }; delete next[k]; onChange(next); }
  function add() { onChange({ ...env, '': '' }); }
  return (
    <div>
      {pairs.map(([k, v], i) => (
        <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
          <input
            value={k} placeholder="KEY"
            onChange={e => { const next = {}; pairs.forEach(([pk, pv], pi) => { next[pi === i ? e.target.value : pk] = pv; }); onChange(next); }}
            style={{ ...S.input, flex: 1, fontFamily: 'var(--font-mono)', fontSize: 11 }}
          />
          <input
            value={v} placeholder="value"
            onChange={e => set(k, e.target.value)}
            style={{ ...S.input, flex: 2, fontFamily: 'var(--font-mono)', fontSize: 11 }}
          />
          <button onClick={() => remove(k)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-danger)', padding: '0 4px', flexShrink: 0 }}>
            <X size={13} />
          </button>
        </div>
      ))}
      <button onClick={add} style={{
        fontSize: 11, color: 'var(--color-sc-text-muted)', background: 'none', border: '1px dashed var(--color-sc-border)',
        borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontFamily: 'var(--font-inter)',
      }}>+ Add env var</button>
    </div>
  );
}

// ── Server form (add / edit) ──────────────────────────────────────────────────
function ServerForm({ initial, onSave, onCancel, existingIds = [] }) {
  const [form, setForm] = useState(() => initial || {
    id: '', name: '', description: '', command: 'npx', args: [], env: {}, enabled: true,
  });
  const [argsRaw, setArgsRaw] = useState(() => (initial?.args ?? []).join(' '));
  const [template, setTemplate] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  function applyTemplate(tplId) {
    const tpl = TEMPLATES.find(t => t.id === tplId);
    if (!tpl) return;
    setForm(f => ({ ...f, id: f.id || tpl.id, name: f.name || tpl.name, description: f.description || tpl.description, command: tpl.command, env: { ...tpl.env, ...f.env } }));
    setArgsRaw(tpl.args.join(' '));
    setTemplate(tplId);
  }

  function parseArgs(raw) {
    // Simple shell-like split respecting quoted strings
    const parts = []; let cur = ''; let inQ = false; let q = '';
    for (const ch of raw) {
      if (inQ) { if (ch === q) inQ = false; else cur += ch; }
      else if (ch === '"' || ch === "'") { inQ = true; q = ch; }
      else if (ch === ' ') { if (cur) { parts.push(cur); cur = ''; } }
      else cur += ch;
    }
    if (cur) parts.push(cur);
    return parts;
  }

  async function handleSave() {
    setErr('');
    if (!form.id.trim()) return setErr('ID is required');
    if (!form.command.trim()) return setErr('Command is required');
    if (!initial && existingIds.includes(form.id.trim())) return setErr(`ID "${form.id}" already exists`);
    setSaving(true);
    try {
      const payload = { ...form, args: parseArgs(argsRaw) };
      await onSave(payload);
    } catch (e) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{
      background: 'var(--color-sc-surface)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 25%, transparent)',
      borderRadius: 14, padding: '22px 24px', marginBottom: 20,
    }}>
      <h3 style={{ margin: '0 0 18px', fontFamily: 'var(--font-grotesk)', fontSize: 15, fontWeight: 700, color: 'var(--color-sc-text)' }}>
        {initial ? 'Edit Server' : 'Add MCP Server'}
      </h3>

      {/* Template picker */}
      {!initial && (
        <div style={{ marginBottom: 16 }}>
          <label style={S.label}>Start from a template (optional)</label>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {TEMPLATES.map(t => (
              <button key={t.id} type="button" onClick={() => applyTemplate(t.id)} style={{
                padding: '4px 10px', borderRadius: 20, fontSize: 11, cursor: 'pointer',
                border: `1px solid ${template === t.id ? 'color-mix(in srgb, var(--color-sc-gold) 50%, transparent)' : 'var(--color-sc-border)'}`,
                background: template === t.id ? 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)' : 'var(--color-sc-bg)',
                color: template === t.id ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
                fontFamily: 'var(--font-inter)', transition: 'all 0.12s',
              }}>{t.name}</button>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <div>
          <label style={S.label}>Server ID *</label>
          <input value={form.id} onChange={e => setForm(f => ({ ...f, id: e.target.value.toLowerCase().replace(/[^a-z0-9_\-]/g, '_') }))}
            placeholder="github" style={{ ...S.input, fontFamily: 'var(--font-mono)' }} disabled={!!initial} />
        </div>
        <div>
          <label style={S.label}>Display name</label>
          <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="GitHub" style={S.input} />
        </div>
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={S.label}>Description</label>
        <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
          placeholder="What does this MCP server do?" style={S.input} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 12, marginBottom: 12 }}>
        <div>
          <label style={S.label}>Command *</label>
          <input value={form.command} onChange={e => setForm(f => ({ ...f, command: e.target.value }))}
            placeholder="npx" style={{ ...S.input, fontFamily: 'var(--font-mono)' }} />
        </div>
        <div>
          <label style={S.label}>Arguments</label>
          <input value={argsRaw} onChange={e => setArgsRaw(e.target.value)}
            placeholder="-y @modelcontextprotocol/server-github" style={{ ...S.input, fontFamily: 'var(--font-mono)', fontSize: 12 }} />
        </div>
      </div>

      <div style={{ marginBottom: 18 }}>
        <label style={S.label}>Environment variables</label>
        <EnvEditor env={form.env} onChange={env => setForm(f => ({ ...f, env }))} />
      </div>

      {err && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12, color: 'var(--color-sc-danger)', fontSize: 12 }}>
          <AlertCircle size={13} /> {err}
        </div>
      )}

      <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
        <button onClick={onCancel} style={{
          padding: '8px 18px', borderRadius: 8, border: '1px solid var(--color-sc-border)',
          background: 'transparent', color: 'var(--color-sc-text-muted)', cursor: 'pointer',
          fontFamily: 'var(--font-inter)', fontSize: 13,
        }}>Cancel</button>
        <button onClick={handleSave} disabled={saving} style={{
          padding: '8px 20px', borderRadius: 8, border: 'none',
          background: 'var(--color-sc-gold)', color: '#0D0D0D',
          cursor: 'pointer', fontFamily: 'var(--font-grotesk)', fontSize: 13, fontWeight: 700,
        }}>{saving ? 'Saving…' : initial ? 'Save changes' : 'Add server'}</button>
      </div>
    </div>
  );
}

// ── Server card ───────────────────────────────────────────────────────────────
function ServerCard({ server, onToggle, onDelete, onEdit }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{
      background: 'var(--color-sc-surface)', border: `1px solid ${server.enabled ? 'color-mix(in srgb, var(--color-sc-gold) 20%, transparent)' : 'var(--color-sc-border)'}`,
      borderRadius: 12, overflow: 'hidden', transition: 'border-color 0.15s',
    }}>
      {/* Main row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px' }}>
        {/* Icon */}
        <div style={{
          width: 36, height: 36, borderRadius: 9, flexShrink: 0,
          background: server.enabled ? 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)' : 'rgba(255,255,255,0.04)',
          border: `1px solid ${server.enabled ? 'color-mix(in srgb, var(--color-sc-gold) 20%, transparent)' : 'var(--color-sc-border)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: server.enabled ? 'var(--color-sc-gold)' : 'var(--color-sc-text-dim)',
        }}>
          <Plug size={15} />
        </div>

        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 13, color: server.enabled ? 'var(--color-sc-text)' : 'var(--color-sc-text-muted)', display: 'flex', alignItems: 'center', gap: 8 }}>
            {server.name}
            <span style={{
              fontSize: 10, padding: '2px 7px', borderRadius: 10,
              background: server.enabled ? 'rgba(6,214,160,0.12)' : 'rgba(255,255,255,0.05)',
              color: server.enabled ? 'var(--color-sc-success)' : 'var(--color-sc-text-dim)',
              fontWeight: 600,
            }}>{server.enabled ? 'Enabled' : 'Disabled'}</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', marginTop: 2, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Terminal size={10} />
            <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>
              {server.command} {(server.args || []).join(' ').slice(0, 60)}{(server.args || []).join(' ').length > 60 ? '…' : ''}
            </code>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
          <button onClick={() => setExpanded(e => !e)} style={{
            background: 'none', border: '1px solid var(--color-sc-border)', borderRadius: 7,
            cursor: 'pointer', color: 'var(--color-sc-text-muted)', padding: '4px 8px',
            display: 'flex', alignItems: 'center', gap: 4, fontSize: 11,
          }}>
            {expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
            Details
          </button>
          <button onClick={() => onEdit(server)} style={{
            width: 30, height: 30, borderRadius: 8, border: 'none', cursor: 'pointer',
            background: 'rgba(255,255,255,0.05)', color: 'var(--color-sc-text-muted)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><Edit2 size={13} /></button>
          <button onClick={() => onToggle(server.id)} title={server.enabled ? 'Disable' : 'Enable'} style={{
            width: 30, height: 30, borderRadius: 8, border: 'none', cursor: 'pointer',
            background: server.enabled ? 'rgba(6,214,160,0.1)' : 'rgba(255,255,255,0.05)',
            color: server.enabled ? 'var(--color-sc-success)' : 'var(--color-sc-text-dim)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {server.enabled ? <ToggleRight size={15} /> : <ToggleLeft size={15} />}
          </button>
          <button onClick={() => onDelete(server.id)} style={{
            width: 30, height: 30, borderRadius: 8, border: 'none', cursor: 'pointer',
            background: 'rgba(255,77,109,0.08)', color: 'var(--color-sc-danger)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><Trash2 size={13} /></button>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div style={{ borderTop: '1px solid var(--color-sc-border)', padding: '14px 16px', background: 'rgba(0,0,0,0.15)' }}>
          {server.description && (
            <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--color-sc-text-muted)', lineHeight: 1.55 }}>{server.description}</p>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr', rowGap: 6, fontSize: 12 }}>
            <span style={{ color: 'var(--color-sc-text-dim)' }}>Command</span>
            <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-sc-text)', background: 'rgba(255,255,255,0.04)', padding: '2px 6px', borderRadius: 4 }}>
              {server.command}
            </code>
            <span style={{ color: 'var(--color-sc-text-dim)' }}>Args</span>
            <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-sc-text)', background: 'rgba(255,255,255,0.04)', padding: '2px 6px', borderRadius: 4, wordBreak: 'break-all' }}>
              {(server.args || []).join(' ') || '—'}
            </code>
            {Object.keys(server.env || {}).length > 0 && (
              <>
                <span style={{ color: 'var(--color-sc-text-dim)' }}>Env</span>
                <div>
                  {Object.entries(server.env).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', gap: 8, marginBottom: 3 }}>
                      <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-sc-gold)', fontSize: 11 }}>{k}</code>
                      <span style={{ color: 'var(--color-sc-text-dim)' }}>=</span>
                      <code style={{ fontFamily: 'var(--font-mono)', color: v ? 'var(--color-sc-text)' : 'var(--color-sc-danger)', fontSize: 11 }}>
                        {v ? (v.length > 20 ? `${v.slice(0, 8)}…${v.slice(-4)}` : v) : '⚠ not set'}
                      </code>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── MCP Page ──────────────────────────────────────────────────────────────────
export function MCPPage() {
  const [servers, setServers]     = useState([]);
  const [loading, setLoading]     = useState(true);
  const [adding, setAdding]       = useState(false);
  const [editing, setEditing]     = useState(null);   // server object
  const [reloading, setReloading] = useState(false);
  const [reloadMsg, setReloadMsg] = useState('');

  const refresh = useCallback(() => {
    fetch('/mcp/servers')
      .then(r => r.json())
      .then(d => setServers(d.servers || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  async function handleAdd(payload) {
    const res = await fetch('/mcp/servers', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) { const d = await res.json(); throw new Error(d.error || 'Save failed'); }
    refresh();
    setAdding(false);
  }

  async function handleEdit(payload) {
    await fetch(`/mcp/servers/${payload.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    refresh();
    setEditing(null);
  }

  async function handleToggle(id) {
    await fetch(`/mcp/servers/${id}/toggle`, { method: 'POST' });
    refresh();
  }

  async function handleDelete(id) {
    await fetch(`/mcp/servers/${id}`, { method: 'DELETE' });
    refresh();
  }

  async function handleReload() {
    setReloading(true);
    setReloadMsg('');
    try {
      const res = await fetch('/mcp/reload', { method: 'POST' });
      const d = await res.json();
      setReloadMsg(d.message || (d.ok ? 'Backbone restarted.' : 'Restart failed.'));
    } catch {
      setReloadMsg('Reload request failed.');
    } finally {
      setReloading(false);
      setTimeout(() => setReloadMsg(''), 5000);
    }
  }

  const enabledCount = servers.filter(s => s.enabled).length;

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
      {/* Header */}
      <div style={{ padding: '24px 32px 20px', borderBottom: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ margin: '0 0 4px', fontFamily: 'var(--font-grotesk)', fontSize: 20, fontWeight: 700, color: 'var(--color-sc-text)', display: 'flex', alignItems: 'center', gap: 10 }}>
              <Plug size={18} style={{ color: 'var(--color-sc-gold)' }} />
              MCP Servers
            </h1>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--color-sc-text-muted)' }}>
              Model Context Protocol servers extend agents with tools — filesystem, search, databases, APIs.
              {' '}<span style={{ color: 'var(--color-sc-text-dim)' }}>{enabledCount} of {servers.length} enabled.</span>
            </p>
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {reloadMsg && (
              <span style={{ fontSize: 12, color: reloadMsg.includes('fail') ? 'var(--color-sc-danger)' : 'var(--color-sc-success)', display: 'flex', alignItems: 'center', gap: 5 }}>
                <Check size={12} /> {reloadMsg}
              </span>
            )}
            <button
              onClick={handleReload}
              disabled={reloading}
              title="Apply changes — restarts the Go backbone to reload MCP config"
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 9,
                background: 'rgba(255,255,255,0.05)', border: '1px solid var(--color-sc-border)',
                color: 'var(--color-sc-text-muted)', cursor: reloading ? 'not-allowed' : 'pointer',
                fontSize: 13, fontFamily: 'var(--font-inter)', transition: 'all 0.15s',
              }}
            >
              <RefreshCw size={13} style={{ animation: reloading ? 'spin 1s linear infinite' : 'none' }} />
              {reloading ? 'Restarting…' : 'Apply & reload'}
            </button>
            <button
              onClick={() => { setAdding(true); setEditing(null); }}
              style={{
                display: 'flex', alignItems: 'center', gap: 7, padding: '8px 16px', borderRadius: 9,
                background: 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 30%, transparent)',
                color: 'var(--color-sc-gold)', cursor: 'pointer', fontSize: 13, fontWeight: 600,
                fontFamily: 'var(--font-grotesk)', transition: 'background 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'color-mix(in srgb, var(--color-sc-gold) 22%, transparent)'}
              onMouseLeave={e => e.currentTarget.style.background = 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)'}
            >
              <Plus size={14} /> Add server
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 32px' }}>
        {/* Add form */}
        {adding && (
          <ServerForm
            existingIds={servers.map(s => s.id)}
            onSave={handleAdd}
            onCancel={() => setAdding(false)}
          />
        )}

        {/* Edit form */}
        {editing && (
          <ServerForm
            initial={editing}
            onSave={handleEdit}
            onCancel={() => setEditing(null)}
          />
        )}

        {/* Empty state */}
        {!loading && servers.length === 0 && !adding && (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--color-sc-text-dim)' }}>
            <Plug size={36} style={{ opacity: 0.2, marginBottom: 12 }} />
            <div style={{ fontSize: 14, marginBottom: 8, color: 'var(--color-sc-text-muted)' }}>No MCP servers configured</div>
            <div style={{ fontSize: 13, marginBottom: 20 }}>Add servers to give agents tools like filesystem access, web search, and database queries.</div>
          </div>
        )}

        {/* Info banner */}
        {!adding && !editing && servers.length > 0 && (
          <div style={{
            display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 14px',
            background: 'color-mix(in srgb, var(--color-sc-gold) 6%, transparent)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 15%, transparent)',
            borderRadius: 10, marginBottom: 16, fontSize: 12, color: 'var(--color-sc-text-muted)',
          }}>
            <AlertCircle size={13} style={{ color: 'var(--color-sc-gold)', flexShrink: 0, marginTop: 1 }} />
            Toggle servers on/off, then click <strong style={{ color: 'var(--color-sc-gold)' }}>Apply &amp; reload</strong> to restart the backbone with the new config.
            Changes take effect immediately after reload.
          </div>
        )}

        {/* Server list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {servers.map(s => (
            <ServerCard
              key={s.id}
              server={s}
              onToggle={handleToggle}
              onDelete={handleDelete}
              onEdit={srv => { setEditing(srv); setAdding(false); }}
            />
          ))}
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
