import { useState, useEffect, useCallback } from 'react';
import { Check, X, Zap, AlertCircle, ExternalLink, Trash2, TestTube, Database, RefreshCw, Clock } from 'lucide-react';

// ── Integration catalog ───────────────────────────────────────────────────────
const CATALOG = [
  // Communication
  {
    id: 'slack', name: 'Slack', category: 'Communication',
    emoji: '💬', color: '#4A154B',
    badge: 'Team+',
    description: 'Deploy Ori as a Slack bot in your workspace — answer questions, run tasks, and post summaries directly in channels.',
    docs: 'https://api.slack.com/start',
    fields: [
      { key: 'workspace_name', label: 'Workspace Name', type: 'text', placeholder: 'e.g. Acme Corp', required: true },
      { key: 'bot_token', label: 'Bot Token (xoxb-…)', type: 'password', placeholder: 'xoxb-...', required: true },
      { key: 'app_token', label: 'App-Level Token (xapp-…)', type: 'password', placeholder: 'xapp-...', required: true },
      { key: 'default_channel', label: 'Default Channel', type: 'text', placeholder: '#general' },
    ],
  },
  {
    id: 'ms_teams', name: 'Microsoft Teams', category: 'Communication',
    emoji: '🔷', color: '#6264A7',
    badge: 'Business',
    comingSoon: true,
    description: 'Bring Ori into Teams — answer questions, assist with tasks, and automate workflows.',
    docs: 'https://learn.microsoft.com/en-us/microsoftteams/platform/agents-in-teams/overview',
    fields: [
      { key: 'app_id', label: 'Azure App (Client) ID', type: 'text', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', required: true },
      { key: 'app_password', label: 'Client Secret', type: 'password', placeholder: 'Azure app client secret', required: true },
      { key: 'tenant_id', label: 'Tenant ID', type: 'text', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' },
      { key: 'bot_name', label: 'Bot Display Name', type: 'text', placeholder: 'Ori' },
    ],
  },

  // Productivity
  {
    id: 'notion', name: 'Notion', category: 'Productivity',
    emoji: '📓', color: '#000000',
    description: 'Read and write Notion pages and databases — give Ori your team\'s knowledge base.',
    docs: 'https://developers.notion.com',
    fields: [
      { key: 'api_key', label: 'Internal Integration Secret', type: 'password', placeholder: 'secret_...', required: true },
      { key: 'database_id', label: 'Default Database ID', type: 'text', placeholder: 'Optional — default database for queries' },
    ],
  },
  {
    id: 'google_workspace', name: 'Google Workspace', category: 'Productivity',
    emoji: '🅶', color: '#4285F4',
    description: 'Connect Gmail, Drive, Docs, and Calendar — Ori answers questions using your actual documents.',
    docs: 'https://developers.google.com/workspace',
    authType: 'oauth2',
    fields: [],
  },

  // CRM
  {
    id: 'hubspot', name: 'HubSpot', category: 'CRM',
    emoji: '🔶', color: '#FF7A59',
    description: 'Pull contacts, deals, and pipeline data — ask Ori questions about your business in plain English.',
    docs: 'https://developers.hubspot.com/docs/api/overview',
    fields: [
      { key: 'access_token', label: 'Private App Access Token', type: 'password', required: true },
    ],
  },

  // Developer
  {
    id: 'github_api', name: 'GitHub', category: 'Developer',
    emoji: '🐙', color: '#24292F',
    description: 'Query repos, issues, PRs, and code — Ori becomes aware of your codebase and project state.',
    docs: 'https://docs.github.com/en/rest',
    fields: [
      { key: 'personal_access_token', label: 'Personal Access Token', type: 'password', required: true },
      { key: 'default_owner', label: 'Default Org / User', type: 'text' },
    ],
  },
  {
    id: 'jira', name: 'Jira', category: 'Developer',
    emoji: '🔵', color: '#0052CC',
    description: 'Read issues, epics, and sprints — ask Ori about project status without leaving chat.',
    docs: 'https://developer.atlassian.com/cloud/jira/platform/rest/v3',
    fields: [
      { key: 'domain', label: 'Atlassian Domain', type: 'text', placeholder: 'yourcompany.atlassian.net', required: true },
      { key: 'email', label: 'Account Email', type: 'text', required: true },
      { key: 'api_token', label: 'API Token', type: 'password', required: true },
    ],
  },

  // Data & Storage
  {
    id: 'supabase', name: 'Supabase', category: 'Data & Storage',
    emoji: '⚡', color: '#3ECF8E',
    description: 'Query your Postgres database or use Supabase as a vector store for RAG pipelines.',
    docs: 'https://supabase.com/docs/reference/javascript/introduction',
    fields: [
      { key: 'url', label: 'Project URL', type: 'url', placeholder: 'https://xxx.supabase.co', required: true },
      { key: 'anon_key', label: 'Anon / Public Key', type: 'password', required: true },
      { key: 'service_role_key', label: 'Service Role Key (optional)', type: 'password' },
    ],
  },
];

const CATEGORIES = ['All', ...Array.from(new Set(CATALOG.map(c => c.category)))];

// ── Shared styles ─────────────────────────────────────────────────────────────
const inp = {
  width: '100%', background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)',
  borderRadius: 8, padding: '8px 11px', color: 'var(--color-sc-text)',
  fontFamily: 'var(--font-inter)', fontSize: 13, outline: 'none', boxSizing: 'border-box',
};

// ── Configure drawer ──────────────────────────────────────────────────────────
const INDEXABLE = new Set([
  'discord','telegram','slack','notion','todoist','trello','airtable','linear',
  'asana','jira','salesforce','hubspot','supabase','arxiv','pubmed','semantic_scholar',
  'newsapi','reddit','wikipedia','youtube','github_api','gitlab',
]);

function IndexPanel({ integration, saved, indexStatus, onSave, onIndex }) {
  const status       = indexStatus?.[integration.id];
  const isIndexing   = status?.status === 'indexing';
  const autoEnabled  = saved?.auto_index ?? false;
  const intervalHours = saved?.index_interval_hours ?? 24;

  function toggleAuto() {
    onSave({
      ...saved,
      credentials: saved?.credentials ?? {},
      enabled: saved?.enabled ?? true,
      auto_index: !autoEnabled,
      index_interval_hours: intervalHours,
    });
  }

  function setInterval(h) {
    onSave({
      ...saved,
      credentials: saved?.credentials ?? {},
      enabled: saved?.enabled ?? true,
      auto_index: autoEnabled,
      index_interval_hours: parseInt(h) || 24,
    });
  }

  return (
    <div style={{ padding: '14px', background: 'color-mix(in srgb, var(--color-sc-gold) 4%, transparent)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 15%, transparent)', borderRadius: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Auto-index toggle row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, color: 'var(--color-sc-gold)', fontFamily: 'var(--font-grotesk)' }}>
          <Database size={12} /> Auto-index
        </div>
        <button onClick={toggleAuto} style={{
          width: 40, height: 22, borderRadius: 11, border: 'none', cursor: 'pointer',
          background: autoEnabled ? 'var(--color-sc-success)' : 'rgba(255,255,255,0.15)',
          position: 'relative', transition: 'background 0.2s', padding: 0, flexShrink: 0,
        }}>
          <span style={{
            position: 'absolute', top: 2, left: autoEnabled ? 20 : 2, width: 18, height: 18,
            borderRadius: '50%', background: '#fff', transition: 'left 0.2s',
          }} />
        </button>
      </div>

      {/* Interval selector — only shown when auto is on */}
      {autoEnabled && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--color-sc-text-muted)' }}>
          <Clock size={11} style={{ flexShrink: 0 }} />
          <span>Every</span>
          <select value={intervalHours} onChange={e => setInterval(e.target.value)} style={{ ...inp, width: 80, padding: '4px 8px', fontSize: 12 }}>
            <option value={1}>1 hour</option>
            <option value={3}>3 hours</option>
            <option value={6}>6 hours</option>
            <option value={12}>12 hours</option>
            <option value={24}>24 hours</option>
            <option value={48}>48 hours</option>
          </select>
        </div>
      )}

      {/* Status + manual trigger */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        {status ? (
          <span style={{ fontSize: 11, color: status.status === 'error' ? 'var(--color-sc-danger)' : status.status === 'indexed' ? 'var(--color-sc-success)' : 'var(--color-sc-gold)', display: 'flex', alignItems: 'center', gap: 4 }}>
            {status.status === 'indexing' && <RefreshCw size={10} style={{ animation: 'spin 1s linear infinite' }} />}
            {status.status === 'indexed'  && <Check size={10} />}
            {status.status === 'error'    && <AlertCircle size={10} />}
            {status.status === 'indexing' ? 'Indexing…'
              : status.status === 'indexed' ? `${status.docs} docs · ${new Date(status.last_indexed).toLocaleDateString()}`
              : status.status === 'error'   ? status.error
              : ''}
          </span>
        ) : <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>{autoEnabled ? 'First run starting…' : 'Not indexed yet'}</span>}
        <button onClick={() => onIndex(integration.id, {})} disabled={isIndexing}
          style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px', borderRadius: 7,
            border: '1px solid color-mix(in srgb, var(--color-sc-gold) 30%, transparent)', background: 'transparent',
            color: isIndexing ? 'var(--color-sc-text-dim)' : 'var(--color-sc-gold)',
            cursor: isIndexing ? 'not-allowed' : 'pointer', fontSize: 11,
            fontFamily: 'var(--font-grotesk)', fontWeight: 600,
          }}>
          <RefreshCw size={10} style={isIndexing ? { animation: 'spin 1s linear infinite' } : {}} />
          {isIndexing ? 'Indexing…' : 'Index now'}
        </button>
      </div>
    </div>
  );
}

function OAuthPanel({ integration, saved, onDelete }) {
  const email = saved?.credentials?.user_email;
  const name  = saved?.credentials?.user_name;
  const isConnected = saved?.enabled && !!email;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {isConnected ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', borderRadius: 10, background: 'rgba(6,214,160,0.06)', border: '1px solid rgba(6,214,160,0.2)' }}>
            <Check size={14} style={{ color: 'var(--color-sc-success)', flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-sc-success)' }}>Connected</div>
              <div style={{ fontSize: 12, color: 'var(--color-sc-text-muted)' }}>{name || email}</div>
              <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>{name ? email : ''}</div>
            </div>
          </div>
          <a href="/api/connections/oauth/authorize/google" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '9px 16px', borderRadius: 9, border: '1px solid var(--color-sc-border)', background: 'transparent', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 13, textDecoration: 'none', fontFamily: 'var(--font-inter)' }}>
            Re-authorize
          </a>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ padding: '12px 14px', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid var(--color-sc-border)', fontSize: 12, color: 'var(--color-sc-text-muted)', lineHeight: 1.5 }}>
            Connect your Google account to give Oricli access to Gmail, Drive, Docs, Calendar, Tasks, Sheets, Forms &amp; Keep.
          </div>
          <a href="/api/connections/oauth/authorize/google" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, padding: '11px 20px', borderRadius: 10, background: '#fff', color: '#1a1a1a', cursor: 'pointer', fontSize: 14, fontWeight: 600, textDecoration: 'none', fontFamily: 'var(--font-grotesk)', border: 'none' }}>
            <span style={{ fontSize: 18 }}>🅶</span> Authorize with Google
          </a>
        </div>
      )}
    </div>
  );
}

function ConfigDrawer({ integration, saved, indexStatus, onSave, onDelete, onIndex, onClose }) {
  const [form, setForm]       = useState(() => saved?.credentials ?? {});
  const [enabled, setEnabled] = useState(() => saved?.enabled ?? true);
  const [saving, setSaving]   = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  function set(k, v) { setForm(f => ({ ...f, [k]: v })); }

  async function handleSave() {
    setSaving(true);
    try {
      await onSave({ credentials: form, enabled });
      setTestResult(null);
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await fetch(`/api/connections/${integration.id}/test`, { method: 'POST' });
      const d = await r.json();
      setTestResult(d);
    } catch {
      setTestResult({ ok: false, message: 'Request failed' });
    } finally {
      setTesting(false);
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 300, display: 'flex', justifyContent: 'flex-end',
      background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)',
    }} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{
        width: 440, background: 'var(--color-sc-surface)', borderLeft: '1px solid var(--color-sc-border)',
        display: 'flex', flexDirection: 'column', overflowY: 'auto',
        animation: 'slideIn 0.2s ease',
      }}>
        {/* Drawer header */}
        <div style={{ padding: '20px 24px 16px', borderBottom: '1px solid var(--color-sc-border)', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 28 }}>{integration.emoji}</span>
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: 0, fontFamily: 'var(--font-grotesk)', fontSize: 16, fontWeight: 700, color: 'var(--color-sc-text)' }}>
              {integration.name}
            </h2>
            <p style={{ margin: '3px 0 0', fontSize: 12, color: 'var(--color-sc-text-muted)' }}>{integration.description}</p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: 4 }}>
            <X size={16} />
          </button>
        </div>

        {/* Fields */}
        <div style={{ flex: 1, padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Enable toggle */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', background: 'var(--color-sc-bg)', borderRadius: 8, border: '1px solid var(--color-sc-border)' }}>
            <span style={{ fontSize: 13, color: 'var(--color-sc-text)', fontWeight: 600, fontFamily: 'var(--font-grotesk)' }}>Enable connection</span>
            <button onClick={() => setEnabled(e => !e)} style={{
              width: 40, height: 22, borderRadius: 11, border: 'none', cursor: 'pointer',
              background: enabled ? 'var(--color-sc-success)' : 'rgba(255,255,255,0.15)',
              position: 'relative', transition: 'background 0.2s',
              padding: 0, flexShrink: 0,
            }}>
              <span style={{
                position: 'absolute', top: 2, left: enabled ? 20 : 2, width: 18, height: 18,
                borderRadius: '50%', background: '#fff', transition: 'left 0.2s',
              }} />
            </button>
          </div>

          {integration.authType === 'oauth2' ? (
            <OAuthPanel integration={integration} saved={saved} onDelete={onDelete} />
          ) : (
            integration.fields.map(f => (
            <div key={f.key}>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-sc-text-muted)', fontFamily: 'var(--font-grotesk)', marginBottom: 5, display: 'flex', alignItems: 'center', gap: 5 }}>
                {f.label}
                {f.required && <span style={{ color: 'var(--color-sc-danger)', fontSize: 10 }}>*</span>}
              </label>
              {f.type === 'textarea' ? (
                <textarea
                  value={form[f.key] ?? ''}
                  onChange={e => set(f.key, e.target.value)}
                  placeholder={f.placeholder || ''}
                  rows={4}
                  style={{ ...inp, resize: 'vertical', lineHeight: 1.5, fontFamily: 'var(--font-mono)', fontSize: 11 }}
                />
              ) : (
                <input
                  type={f.type === 'password' ? 'password' : f.type === 'url' ? 'url' : 'text'}
                  value={form[f.key] ?? ''}
                  onChange={e => set(f.key, e.target.value)}
                  placeholder={f.placeholder || ''}
                  style={{ ...inp, fontFamily: f.type === 'password' ? 'var(--font-mono)' : 'var(--font-inter)' }}
                />
              )}
            </div>
          ))
          )}

          {/* Docs link */}
          <a href={integration.docs} target="_blank" rel="noopener" style={{
            display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12,
            color: 'var(--color-sc-gold)', textDecoration: 'none',
          }}>
            <ExternalLink size={11} /> View API docs
          </a>

          {/* RAG Indexing — only for indexable connectors that have saved creds */}
          {INDEXABLE.has(integration.id) && saved && (
            <IndexPanel integration={integration} saved={saved} indexStatus={indexStatus} onSave={onSave} onIndex={onIndex} />
          )}

          {/* Test result */}
          {testResult && (
            <div style={{
              display: 'flex', alignItems: 'flex-start', gap: 8, padding: '10px 12px', borderRadius: 8,
              background: testResult.ok ? 'rgba(6,214,160,0.08)' : 'rgba(255,77,109,0.08)',
              border: `1px solid ${testResult.ok ? 'rgba(6,214,160,0.2)' : 'rgba(255,77,109,0.2)'}`,
              fontSize: 12, color: testResult.ok ? 'var(--color-sc-success)' : 'var(--color-sc-danger)',
            }}>
              {testResult.ok ? <Check size={13} style={{ flexShrink: 0, marginTop: 1 }} /> : <AlertCircle size={13} style={{ flexShrink: 0, marginTop: 1 }} />}
              {testResult.message}
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--color-sc-border)', display: 'flex', gap: 8, alignItems: 'center' }}>
          {saved && (
            <button onClick={onDelete} style={{
              padding: '8px 12px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: 'rgba(255,77,109,0.08)', color: 'var(--color-sc-danger)',
              display: 'flex', alignItems: 'center', gap: 5, fontSize: 12,
            }}>
              <Trash2 size={12} /> Remove
            </button>
          )}
          <div style={{ flex: 1 }} />
          <button onClick={handleTest} disabled={testing} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8,
            border: '1px solid var(--color-sc-border)', background: 'transparent',
            color: 'var(--color-sc-text-muted)', cursor: testing ? 'not-allowed' : 'pointer',
            fontSize: 13, fontFamily: 'var(--font-inter)',
          }}>
            <TestTube size={13} />{testing ? 'Testing…' : 'Test'}
          </button>
          {integration.authType !== 'oauth2' && (
          <button onClick={handleSave} disabled={saving} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 18px', borderRadius: 8,
            border: 'none', background: 'var(--color-sc-gold)', color: '#0D0D0D',
            cursor: 'pointer', fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-grotesk)',
          }}>
            {saving ? 'Saving…' : 'Save'}
          </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Integration card ──────────────────────────────────────────────────────────
function IntegrationCard({ integration, saved, indexStatus, onConfigure }) {
  const isConnected  = saved?.enabled && Object.values(saved?.credentials ?? {}).some(v => v);
  const isSaved      = !!saved;
  const hasMissing   = integration.authType === 'oauth2'
    ? false
    : integration.fields.filter(f => f.required).some(f => !saved?.credentials?.[f.key]);

  const statusColor = integration.comingSoon ? 'var(--color-sc-text-dim)'
    : isConnected && !hasMissing ? 'var(--color-sc-success)'
    : isSaved ? 'var(--color-sc-gold)'
    : 'var(--color-sc-text-dim)';
  const statusLabel = integration.comingSoon ? 'Coming Soon'
    : isConnected && !hasMissing ? 'Connected'
    : isSaved ? 'Incomplete'
    : 'Not configured';

  return (
    <div
      onClick={() => !integration.comingSoon && onConfigure(integration)}
      style={{
        background: 'var(--color-sc-surface)', border: `1px solid ${isConnected && !hasMissing ? 'rgba(6,214,160,0.2)' : 'var(--color-sc-border)'}`,
        borderRadius: 12, padding: '16px', cursor: integration.comingSoon ? 'default' : 'pointer',
        display: 'flex', flexDirection: 'column', gap: 10, transition: 'all 0.15s',
        position: 'relative', overflow: 'hidden',
      }}
      onMouseEnter={e => { if (!integration.comingSoon) { e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--color-sc-gold) 30%, transparent)'; e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; } }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = isConnected && !hasMissing ? 'rgba(6,214,160,0.2)' : 'var(--color-sc-border)';
        e.currentTarget.style.background = 'var(--color-sc-surface)';
      }}
    >
      {/* Color accent */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: isConnected && !hasMissing ? integration.color : 'transparent', borderRadius: '12px 12px 0 0', transition: 'background 0.2s' }} />

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 22 }}>{integration.emoji}</span>
          <div>
            <div style={{ fontFamily: 'var(--font-grotesk)', fontWeight: 700, fontSize: 13, color: 'var(--color-sc-text)', display: 'flex', alignItems: 'center', gap: 6 }}>
              {integration.name}
              {integration.badge && (
                <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 6, fontWeight: 700, background: 'rgba(136,117,255,0.18)', color: '#A099FF', letterSpacing: '0.05em' }}>{integration.badge}</span>
              )}
            </div>
            <div style={{ fontSize: 10, color: 'var(--color-sc-text-dim)', marginTop: 1 }}>{integration.category}</div>
          </div>
        </div>
        <span style={{
          fontSize: 10, padding: '3px 8px', borderRadius: 10, fontWeight: 600,
          background: `color-mix(in srgb, ${statusColor} 15%, transparent)`,
          color: statusColor, whiteSpace: 'nowrap',
        }}>{statusLabel}</span>
      </div>

      {/* Description */}
      <p style={{ margin: 0, fontSize: 12, color: 'var(--color-sc-text-muted)', lineHeight: 1.55, flex: 1 }}>
        {integration.description}
      </p>

      {/* Footer */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
          {integration.authType === 'oauth2' ? 'OAuth2' : integration.comingSoon ? '' : `${integration.fields.filter(f => f.required).length} required field${integration.fields.filter(f => f.required).length !== 1 ? 's' : ''}`}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {indexStatus && indexStatus.status === 'indexed' && (
            <span style={{ fontSize: 10, color: 'var(--color-sc-success)', display: 'flex', alignItems: 'center', gap: 3 }}>
              <Database size={9} /> {indexStatus.docs}
            </span>
          )}
          {indexStatus && indexStatus.status === 'indexing' && (
            <span style={{ fontSize: 10, color: 'var(--color-sc-gold)', display: 'flex', alignItems: 'center', gap: 3 }}>
              <RefreshCw size={9} style={{ animation: 'spin 1s linear infinite' }} /> indexing
            </span>
          )}
          {!integration.comingSoon && (
            <span style={{
              fontSize: 11, color: 'var(--color-sc-gold)', fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: 4,
            }}>
              {isSaved ? 'Edit' : 'Configure'} →
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Connections Page ──────────────────────────────────────────────────────────
export function ConnectionsPage() {
  const [saved, setSaved]           = useState({});
  const [indexStatus, setIndexStatus] = useState({});
  const [category, setCategory]     = useState('All');
  const [search, setSearch]         = useState('');
  const [configuring, setConfiguring] = useState(null);

  const refresh = useCallback(() => {
    fetch('/api/connections').then(r => r.json()).then(d => setSaved(d.connections || {})).catch(() => {});
  }, []);

  const refreshStatus = useCallback(() => {
    fetch('/api/connections/index/status').then(r => r.json()).then(d => setIndexStatus(d)).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    refreshStatus();
    // Poll while any indexing job is running
    const interval = setInterval(() => {
      refreshStatus();
    }, 4000);
    return () => clearInterval(interval);
  }, [refresh, refreshStatus]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('connected') === 'google') {
      refresh();
      window.history.replaceState({}, '', window.location.pathname + window.location.hash);
    }
  }, [refresh]);

  async function handleSave(id, payload) {
    await fetch(`/api/connections/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    refresh();
  }

  async function handleDelete(id) {
    await fetch(`/api/connections/${id}`, { method: 'DELETE' });
    refresh();
    setConfiguring(null);
  }

  async function handleIndex(id, opts) {
    await fetch(`/api/connections/${id}/index`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(opts),
    });
    refreshStatus();
  }

  const filtered = CATALOG.filter(c =>
    (category === 'All' || c.category === category) &&
    (!search || c.name.toLowerCase().includes(search.toLowerCase()) || c.description.toLowerCase().includes(search.toLowerCase()))
  );

  const connectedCount = CATALOG.filter(c => {
    const s = saved[c.id];
    return s?.enabled && Object.values(s?.credentials ?? {}).some(v => v);
  }).length;

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
      {/* Header */}
      <div style={{ padding: '24px 32px 0', borderBottom: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
          <div>
            <h1 style={{ margin: '0 0 4px', fontFamily: 'var(--font-grotesk)', fontSize: 20, fontWeight: 700, color: 'var(--color-sc-text)', display: 'flex', alignItems: 'center', gap: 10 }}>
              <Zap size={18} style={{ color: 'var(--color-sc-gold)' }} />
              Connections
            </h1>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--color-sc-text-muted)' }}>
              Connect external APIs as RAG sources and tool providers for your agents.
              {' '}<span style={{ color: connectedCount > 0 ? 'var(--color-sc-success)' : 'var(--color-sc-text-dim)' }}>
                {connectedCount} of {CATALOG.length} connected.
              </span>
            </p>
          </div>
          {/* Search */}
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search integrations…"
            style={{
              ...inp, width: 220, padding: '7px 12px', fontSize: 13,
              background: 'var(--color-sc-bg)',
            }}
          />
        </div>

        {/* Category tabs */}
        <div style={{ display: 'flex', gap: 2, overflowX: 'auto', paddingBottom: 1 }}>
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              style={{
                padding: '6px 14px', borderRadius: 8, border: `1px solid ${category === cat ? 'color-mix(in srgb, var(--color-sc-gold) 40%, transparent)' : 'transparent'}`,
                background: category === cat ? 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)' : 'transparent',
                color: category === cat ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
                cursor: 'pointer', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font-grotesk)',
                whiteSpace: 'nowrap', transition: 'all 0.15s',
              }}
            >{cat}</button>
          ))}
        </div>
      </div>

      {/* Grid */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 32px' }}>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--color-sc-text-dim)', fontSize: 14 }}>
            No integrations match "{search}"
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
            {filtered.map(integration => (
              <IntegrationCard
                key={integration.id}
                integration={integration}
                saved={saved[integration.id]}
                indexStatus={indexStatus[integration.id]}
                onConfigure={setConfiguring}
              />
            ))}
          </div>
        )}
      </div>

      {/* Configure drawer */}
      {configuring && (
        <ConfigDrawer
          integration={configuring}
          saved={saved[configuring.id]}
          indexStatus={indexStatus}
          onSave={payload => handleSave(configuring.id, payload)}
          onDelete={() => handleDelete(configuring.id)}
          onIndex={handleIndex}
          onClose={() => setConfiguring(null)}
        />
      )}

      <style>{`
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
