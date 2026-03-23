import { useState, useRef, useEffect, useCallback } from 'react';
import { useSCStore, streamChat, selectActiveSession } from '../store';
import { Send, Square, Copy, Check, ChevronDown, X, Bot, Search, BookOpen, ListTodo, Workflow, FileText, BarChart2, Loader2, CheckCircle2, AlertCircle, FileCode2, ExternalLink } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

// ── Dispatch card ──────────────────────────────────────────────────────────────

const ACTION_META = {
  research:  { label: 'Researching',     icon: BookOpen,  color: '#7C5CFC' },
  search:    { label: 'Searching',       icon: Search,    color: '#3399FF' },
  task:      { label: 'Task Created',    icon: ListTodo,  color: '#22C55E' },
  create:    { label: 'Opening Canvas',  icon: FileCode2, color: '#F97316' },
  workflow:  { label: 'Workflow',        icon: Workflow,  color: '#F59E0B' },
  summarize: { label: 'Summarising',     icon: FileText,  color: '#EC4899' },
  analyze:   { label: 'Analysing',       icon: BarChart2, color: '#14B8A6' },
};

function DispatchCard({ msg }) {
  const setActivePage = useSCStore(s => s.setActivePage);
  const meta = ACTION_META[msg.action] ?? ACTION_META.research;
  const Icon = meta.icon;
  const isDone  = msg.status === 'done';
  const isError = msg.status === 'error';
  const isDeepResearch = msg.modelTier === 'research';

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 10,
      margin: '6px 0 6px 44px',
    }}>
      <div style={{
        background: `${meta.color}22`, border: `1px solid ${meta.color}55`,
        borderRadius: 10, padding: '8px 12px', maxWidth: 480,
        display: 'flex', flexDirection: 'column', gap: 4,
        ...(isDeepResearch && !isDone && !isError ? {
          border: '1px solid rgba(124,92,252,0.55)',
          animation: 'researchPulse 2.4s ease-in-out infinite',
        } : {}),
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          {isDone
            ? <CheckCircle2 size={14} color="#22C55E" />
            : isError
              ? <AlertCircle size={14} color="#EF4444" />
              : <Loader2 size={14} color={meta.color} style={{ animation: 'spin 1s linear infinite' }} />
          }
          <span style={{ fontSize: 12, fontWeight: 600, color: meta.color }}>
            {meta.label}
          </span>
          <Icon size={12} color={meta.color} />
          {isDeepResearch && !isDone && !isError && (
            <span style={{
              fontSize: 10, fontWeight: 700, color: '#7C5CFC',
              background: 'rgba(124,92,252,0.15)', border: '1px solid rgba(124,92,252,0.35)',
              borderRadius: 4, padding: '1px 6px', letterSpacing: '0.04em',
            }}>
              16B · DEEP
            </span>
          )}
        </div>
        <span style={{ fontSize: 12, color: 'var(--color-sc-text-dim)', fontStyle: 'italic' }}>
          {msg.subject ?? ''}
        </span>
        {isDeepResearch && !isDone && !isError && (
          <span style={{ fontSize: 11, color: 'rgba(124,92,252,0.7)' }}>
            ~2 min wait — deepseek-coder-v2:16b
          </span>
        )}
        {msg.summary && (
          <p style={{ margin: 0, fontSize: 12, color: 'var(--color-sc-text)', lineHeight: 1.5, borderTop: '1px solid #ffffff18', paddingTop: 6 }}>
            {msg.summary}
          </p>
        )}
        {msg.error && (
          <p style={{ margin: 0, fontSize: 12, color: '#EF4444' }}>{msg.error}</p>
        )}
        {/* Canvas shortcut — only for create actions */}
        {msg.action === 'create' && (
          <button
            onClick={() => setActivePage('canvas')}
            style={{
              marginTop: 4, display: 'flex', alignItems: 'center', gap: 5,
              padding: '4px 10px', borderRadius: 6, border: `1px solid ${meta.color}55`,
              background: `${meta.color}18`, cursor: 'pointer',
              fontSize: 11, color: meta.color, fontFamily: 'var(--font-inter)',
              alignSelf: 'flex-start',
            }}
          >
            <ExternalLink size={11} /> Go to Canvas
          </button>
        )}
      </div>
    </div>
  );
}

// ── Thinking / waiting indicators ─────────────────────────────────────────────

function ThinkingDots() {
  return (
    <div style={{ display: 'flex', gap: 5, padding: '4px 2px', alignItems: 'center' }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 7, height: 7, borderRadius: '50%',
          background: 'var(--color-sc-gold)', opacity: 0.6, display: 'inline-block',
          animation: `typingDot 1.1s ease-in-out ${i * 0.22}s infinite`,
        }} />
      ))}
    </div>
  );
}

function DeepResearchBanner() {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 10,
      padding: '9px 14px', borderRadius: 10,
      background: 'rgba(124,92,252,0.08)',
      border: '1px solid rgba(124,92,252,0.35)',
      animation: 'researchPulse 2.4s ease-in-out infinite',
    }}>
      <Loader2 size={14} color="#7C5CFC" style={{ animation: 'spin 1.2s linear infinite', flexShrink: 0 }} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#7C5CFC', letterSpacing: '0.01em' }}>
          Deep Research Mode
        </span>
        <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
          16B model active — first tokens in ~40s
        </span>
      </div>
    </div>
  );
}

// ── Inline code & artifact rendering ─────────────────────────────────────────

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); })}
      style={{
        position: 'absolute', top: 8, right: 8, background: 'rgba(255,255,255,0.07)',
        border: '1px solid rgba(255,255,255,0.1)', borderRadius: 5, padding: '3px 7px',
        cursor: 'pointer', color: copied ? 'var(--color-sc-success)' : 'var(--color-sc-text-muted)',
        fontSize: 11, display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'var(--font-inter)',
        transition: 'color 0.15s',
      }}
    >
      {copied ? <Check size={11} /> : <Copy size={11} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

const markdownComponents = {
  code({ inline, className, children }) {
    const lang = (className ?? '').replace('language-', '') || 'text';
    const code = String(children).replace(/\n$/, '');
    if (inline) {
      return (
        <code style={{
          background: 'rgba(196,164,74,0.1)', color: 'var(--color-sc-gold)',
          padding: '1px 5px', borderRadius: 3, fontFamily: 'var(--font-mono)', fontSize: '0.88em',
        }}>{children}</code>
      );
    }
    return (
      <div style={{ position: 'relative', margin: '12px 0' }}>
        <CopyButton text={code} />
        <SyntaxHighlighter language={lang} style={atomDark}
          customStyle={{ borderRadius: 8, fontSize: 13, margin: 0, background: '#0C0C1A', padding: '14px 16px' }}
          showLineNumbers={code.split('\n').length > 4}
        >{code}</SyntaxHighlighter>
      </div>
    );
  },
  p({ children }) { return <p style={{ margin: '8px 0', lineHeight: 1.75 }}>{children}</p>; },
  ul({ children }) { return <ul style={{ margin: '8px 0', paddingLeft: 22, lineHeight: 1.75 }}>{children}</ul>; },
  ol({ children }) { return <ol style={{ margin: '8px 0', paddingLeft: 22, lineHeight: 1.75 }}>{children}</ol>; },
  li({ children }) { return <li style={{ marginBottom: 3 }}>{children}</li>; },
  h1({ children }) { return <h1 style={{ fontSize: 20, fontFamily: 'var(--font-grotesk)', fontWeight: 700, margin: '20px 0 8px', color: 'var(--color-sc-text)' }}>{children}</h1>; },
  h2({ children }) { return <h2 style={{ fontSize: 16, fontFamily: 'var(--font-grotesk)', fontWeight: 600, margin: '16px 0 6px', color: 'var(--color-sc-text)' }}>{children}</h2>; },
  h3({ children }) { return <h3 style={{ fontSize: 14, fontFamily: 'var(--font-grotesk)', fontWeight: 600, margin: '14px 0 5px', color: 'var(--color-sc-text)' }}>{children}</h3>; },
  blockquote({ children }) { return <blockquote style={{ borderLeft: '3px solid var(--color-sc-gold)', paddingLeft: 14, margin: '10px 0', color: 'var(--color-sc-text-muted)', fontStyle: 'italic' }}>{children}</blockquote>; },
  a({ href, children }) { return <a href={href} target="_blank" rel="noopener" style={{ color: 'var(--color-sc-gold)', textDecoration: 'underline', textDecorationColor: 'rgba(196,164,74,0.4)' }}>{children}</a>; },
  hr() { return <hr style={{ border: 'none', borderTop: '1px solid var(--color-sc-border)', margin: '16px 0' }} />; },
  table({ children }) { return <div style={{ overflowX: 'auto', margin: '12px 0' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>{children}</table></div>; },
  th({ children }) { return <th style={{ border: '1px solid var(--color-sc-border)', padding: '6px 10px', background: 'var(--color-sc-surface)', color: 'var(--color-sc-text-muted)', textAlign: 'left', fontWeight: 600, fontSize: 12 }}>{children}</th>; },
  td({ children }) { return <td style={{ border: '1px solid var(--color-sc-border)', padding: '6px 10px', color: 'var(--color-sc-text)' }}>{children}</td>; },
  strong({ children }) { return <strong style={{ color: 'var(--color-sc-text)', fontWeight: 600 }}>{children}</strong>; },
};

// ── Message ───────────────────────────────────────────────────────────────────

function Message({ msg }) {
  const isUser = msg.role === 'user';

  if (msg.role === 'dispatch') return <DispatchCard msg={msg} />;

  if (isUser) {
    return (
      <div className="animate-fade-slide" style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
        <div style={{
          maxWidth: '72%', background: 'rgba(196,164,74,0.1)',
          border: '1px solid rgba(196,164,74,0.18)', borderRadius: '16px 16px 4px 16px',
          padding: '10px 16px', fontSize: 14, lineHeight: 1.65, color: 'var(--color-sc-text)',
        }}>
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-slide" style={{ display: 'flex', gap: 14, marginBottom: 24, alignItems: 'flex-start' }}>
      {/* Avatar */}
      <div style={{
        width: 30, height: 30, flexShrink: 0, borderRadius: '50%', marginTop: 2,
        background: 'rgba(196,164,74,0.12)', border: '1px solid rgba(196,164,74,0.25)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M12 2 L14 8 L20 6 L16 11 L20 14 L14 13 L12 20 L10 13 L4 14 L8 11 L4 6 L10 8 Z" fill="#C4A44A" />
          <circle cx="12" cy="11" r="2" fill="#080810" />
        </svg>
      </div>
      {/* Content */}
      <div style={{ flex: 1, minWidth: 0, fontSize: 14, color: 'var(--color-sc-text)', lineHeight: 1.7 }}>
        {msg.streaming && !msg.content ? (
          msg.modelTier === 'research' ? <DeepResearchBanner /> : <ThinkingDots />
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {msg.content ?? ''}
          </ReactMarkdown>
        )}
        {msg.scaiCorrected && (
          <div title="SCAI Critique-Revision loop detected a constitutional violation and applied a correction." style={{
            display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 8,
            padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600,
            background: 'rgba(196,164,74,0.10)', border: '1px solid rgba(196,164,74,0.28)',
            color: 'rgba(196,164,74,0.85)', letterSpacing: '0.03em',
          }}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
              <path d="M12 2 L14 8 L20 6 L16 11 L20 14 L14 13 L12 20 L10 13 L4 14 L8 11 L4 6 L10 8 Z" fill="currentColor" />
            </svg>
            SCAI corrected
          </div>
        )}
      </div>
    </div>
  );
}

// ── Empty / welcome state ─────────────────────────────────────────────────────

const SUGGESTIONS = [
  'Write a Python script to monitor disk usage and alert via webhook',
  'Summarize the key risks in a new microservices architecture',
  'Help me draft a product spec for a local-first sync engine',
  'What\'s the fastest way to set up end-to-end encryption for an API?',
];

function WelcomeScreen({ onSuggest }) {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '40px 20px', gap: 0,
    }}>
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none" style={{ marginBottom: 18, opacity: 0.7 }}>
        <path d="M12 2 L14 8 L20 6 L16 11 L20 14 L14 13 L12 20 L10 13 L4 14 L8 11 L4 6 L10 8 Z" fill="#C4A44A" />
        <circle cx="12" cy="11" r="2" fill="#080810" />
      </svg>
      <h1 style={{
        fontFamily: 'var(--font-grotesk)', fontSize: 24, fontWeight: 700,
        color: 'var(--color-sc-text)', margin: '0 0 8px', textAlign: 'center',
      }}>How can I help you today?</h1>
      <p style={{ color: 'var(--color-sc-text-muted)', fontSize: 14, margin: '0 0 36px', textAlign: 'center' }}>
        Your AI. Your data. No cloud required.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, width: '100%', maxWidth: 580 }}>
        {SUGGESTIONS.map(s => (
          <button key={s} onClick={() => onSuggest(s)} style={{
            background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)',
            borderRadius: 10, padding: '12px 14px', cursor: 'pointer', textAlign: 'left',
            color: 'var(--color-sc-text-muted)', fontSize: 13, lineHeight: 1.5,
            fontFamily: 'var(--font-inter)', transition: 'border-color 0.15s, background 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(196,164,74,0.4)'; e.currentTarget.style.background = 'rgba(196,164,74,0.05)'; e.currentTarget.style.color = 'var(--color-sc-text)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--color-sc-border)'; e.currentTarget.style.background = 'var(--color-sc-surface)'; e.currentTarget.style.color = 'var(--color-sc-text-muted)'; }}
          >{s}</button>
        ))}
      </div>
    </div>
  );
}

// ── Chat input ────────────────────────────────────────────────────────────────

function ChatInput({ value, onChange, onSend, onAbort, isStreaming, disabled }) {
  const [focused, setFocused] = useState(false);

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(); }
  }

  function handleInput(e) {
    onChange(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 180) + 'px';
  }

  return (
    <div style={{
      position: 'relative',
      border: `1px solid ${focused ? 'rgba(196,164,74,0.5)' : 'var(--color-sc-border2)'}`,
      borderRadius: 14, background: 'var(--color-sc-surface)',
      boxShadow: focused ? '0 0 0 3px rgba(196,164,74,0.08)' : 'none',
      transition: 'border-color 0.2s, box-shadow 0.2s',
    }}>
      <textarea
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder="Message SovereignClaw…"
        rows={1}
        style={{
          display: 'block', width: '100%', background: 'transparent',
          border: 'none', outline: 'none', resize: 'none', padding: '14px 52px 14px 16px',
          color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 14,
          lineHeight: 1.55, minHeight: 52, overflow: 'hidden',
        }}
      />
      <div style={{ position: 'absolute', right: 10, bottom: 10 }}>
        <button
          onClick={isStreaming ? onAbort : onSend}
          disabled={!isStreaming && !value.trim()}
          style={{
            width: 34, height: 34, borderRadius: 9, border: 'none', cursor: (!isStreaming && !value.trim()) ? 'not-allowed' : 'pointer',
            background: isStreaming
              ? 'rgba(255,77,109,0.2)'
              : value.trim() ? 'var(--color-sc-gold)' : 'rgba(255,255,255,0.06)',
            color: isStreaming ? 'var(--color-sc-danger)' : value.trim() ? '#0D0D0D' : 'var(--color-sc-text-dim)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'background 0.15s, color 0.15s',
          }}
        >
          {isStreaming ? <Square size={13} fill="currentColor" /> : <Send size={14} />}
        </button>
      </div>
    </div>
  );
}

// ── Agent Switcher ────────────────────────────────────────────────────────────

function AgentSwitcher() {
  const activeChatAgent = useSCStore(s => s.activeChatAgent);
  const setChatAgent    = useSCStore(s => s.setChatAgent);
  const clearChatAgent  = useSCStore(s => s.clearChatAgent);
  const [open, setOpen] = useState(false);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);

  // Load agents when dropdown opens
  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetch('/agents/list')
      .then(r => r.json())
      .then(d => setAgents(d.agents || []))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, [open]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function onDown(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      {/* Pill trigger */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '4px 10px 4px 8px', borderRadius: 20,
          background: activeChatAgent ? 'rgba(196,164,74,0.12)' : 'rgba(255,255,255,0.05)',
          border: `1px solid ${activeChatAgent ? 'rgba(196,164,74,0.35)' : 'var(--color-sc-border)'}`,
          cursor: 'pointer', transition: 'all 0.15s', fontSize: 12,
          color: activeChatAgent ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
          fontFamily: 'var(--font-inter)',
        }}
      >
        {activeChatAgent
          ? <span style={{ fontSize: 14 }}>{activeChatAgent.emoji}</span>
          : <Bot size={13} />
        }
        <span style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {activeChatAgent ? activeChatAgent.name : 'Default'}
        </span>
        <ChevronDown size={11} style={{ opacity: 0.6, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
      </button>

      {/* Active dismiss X */}
      {activeChatAgent && (
        <button
          onClick={e => { e.stopPropagation(); clearChatAgent(); }}
          style={{
            position: 'absolute', top: -4, right: -4, width: 14, height: 14,
            borderRadius: '50%', background: 'var(--color-sc-danger)', border: 'none',
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', padding: 0,
          }}
        >
          <X size={8} strokeWidth={3} />
        </button>
      )}

      {/* Dropdown panel */}
      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 8px)', left: 0, zIndex: 200,
          width: 280, maxHeight: 360, overflowY: 'auto',
          background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)',
          borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          padding: 6,
        }}>
          {/* Default option */}
          <button
            onClick={() => { clearChatAgent(); setOpen(false); }}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 10px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: !activeChatAgent ? 'rgba(196,164,74,0.08)' : 'transparent',
              color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 13,
              textAlign: 'left', transition: 'background 0.12s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
            onMouseLeave={e => e.currentTarget.style.background = !activeChatAgent ? 'rgba(196,164,74,0.08)' : 'transparent'}
          >
            <span style={{ fontSize: 16 }}>✨</span>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>Default (Oricli)</div>
              <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', marginTop: 1 }}>General sovereign intelligence</div>
            </div>
            {!activeChatAgent && <span style={{ marginLeft: 'auto', color: 'var(--color-sc-gold)', fontSize: 11 }}>Active</span>}
          </button>

          {agents.length > 0 && (
            <div style={{ borderTop: '1px solid var(--color-sc-border)', margin: '4px 0', padding: '4px 0 0' }}>
              {loading ? (
                <div style={{ padding: '10px', textAlign: 'center', color: 'var(--color-sc-text-dim)', fontSize: 12 }}>Loading…</div>
              ) : (
                agents.map(ag => {
                  const isActive = activeChatAgent?.id === ag.id;
                  return (
                    <button
                      key={ag.id}
                      onClick={() => { setChatAgent(ag); setOpen(false); }}
                      style={{
                        width: '100%', display: 'flex', alignItems: 'flex-start', gap: 10,
                        padding: '8px 10px', borderRadius: 8, border: 'none', cursor: 'pointer',
                        background: isActive ? 'rgba(196,164,74,0.08)' : 'transparent',
                        color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 13,
                        textAlign: 'left', transition: 'background 0.12s',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                      onMouseLeave={e => e.currentTarget.style.background = isActive ? 'rgba(196,164,74,0.08)' : 'transparent'}
                    >
                      <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>{ag.emoji}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', gap: 5 }}>
                          {ag.name}
                          {isActive && <span style={{ color: 'var(--color-sc-gold)', fontSize: 10 }}>●</span>}
                        </div>
                        {ag.description && (
                          <div style={{
                            fontSize: 11, color: 'var(--color-sc-text-muted)', marginTop: 1,
                            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          }}>{ag.description}</div>
                        )}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}



// ── Client-side create intent detection ───────────────────────────────────────
// Mirrors the Go backend patterns but runs BEFORE any Ollama call so we can
// skip the LLM entirely for canvas-create triggers (eliminates the race).

const _TASK_RE = /\b(?:remind\s+me\s+to|add\s+(?:a\s+)?(?:task|todo|reminder)|create\s+(?:a\s+)?(?:task|todo|reminder)|note\s+that|note\s+to)\b/i;
// Anchored to start of message — prevents "you make me feel alive" etc. from firing
const _CREATE_RE = /^\s*(?:(?:hey|hi|ok|okay|so|alright|please|can\s+you|could\s+you|i\s+(?:want|need)\s+(?:you\s+to|to)?|let(?:'s|\s+us?))\s+)?(?:create|write|build|generate|make|draft|implement|code|develop)\s+(?:(?:a|an|the|me\s+a?n?\s+)?(.{10,}))/i;

function detectCreateIntent(text) {
  if (_TASK_RE.test(text)) return null; // already handled by Task pattern
  const m = _CREATE_RE.exec(text);
  return m ? m[1].replace(/[.!?]+$/, '').trim() : null;
}

export function ChatArea() {
  const activeSession          = useSCStore(selectActiveSession);
  const activeModel            = useSCStore(s => s.activeModel);
  const activeSkill            = useSCStore(s => s.activeSkill);
  const isStreaming            = useSCStore(s => s.isStreaming);
  const appendMessage          = useSCStore(s => s.appendMessage);
  const updateLastAgentMessage = useSCStore(s => s.updateLastAgentMessage);
  const setIsStreaming         = useSCStore(s => s.setIsStreaming);
  const renameSession          = useSCStore(s => s.renameSession);
  const activeChatAgent        = useSCStore(s => s.activeChatAgent);

  const [input, setInput] = useState('');
  const bottomRef         = useRef(null);
  const abortRef          = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession?.messages?.length]);

  async function send(overrideText) {
    const text = (overrideText ?? input).trim();
    if (!text || isStreaming) return;
    setInput('');

    const sessionId = activeSession.id;
    if (activeSession.messages.length === 0) {
      renameSession(sessionId, text.slice(0, 46) + (text.length > 46 ? '…' : ''));
    }

    // ── Canvas create shortcut — no LLM call needed ────────────────────────
    // Detect client-side so we skip Ollama entirely and avoid any race condition
    const createSubject = detectCreateIntent(text);
    if (createSubject) {
      const jobId = `local-${Date.now()}`;
      appendMessage(sessionId, { role: 'user', content: text, id: Date.now() });
      appendMessage(sessionId, {
        role: 'dispatch', id: `dispatch-${jobId}`, jobId,
        action: 'create', subject: createSubject,
        status: 'done', summary: 'Opened on Canvas',
      });
      useSCStore.getState().setPendingCanvasPrompt(text);
      useSCStore.getState().setActivePage('canvas');
      return;
    }

    appendMessage(sessionId, { role: 'user', content: text, id: Date.now() });
    appendMessage(sessionId, { role: 'assistant', content: '', streaming: true, id: Date.now() + 1 });
    setIsStreaming(true);
    let pendingTier = null; // captured from dispatch event, applied to assistant msg

    // Agent profile system prompt takes priority over legacy skill switcher
    const systemContent = activeChatAgent
      ? activeChatAgent.systemPrompt
      : activeSkill
        ? `You are operating with the ${activeSkill} skill profile.`
        : null;

    const messages = [
      ...(systemContent ? [{ role: 'system', content: systemContent }] : []),
      ...activeSession.messages.map(m => ({ role: m.role, content: m.content })),
      { role: 'user', content: text },
    ];

    const setActivePage = useSCStore.getState().setActivePage;
    const setPendingCanvasPrompt = useSCStore.getState().setPendingCanvasPrompt;

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      let full = '';
      // Pass profile field to Go backbone for sovereign profile routing
      const extraBody = activeChatAgent ? { profile: activeChatAgent.id } : {};
      for await (const delta of streamChat({
        messages,
        model: activeModel,
        signal: controller.signal,
        onDispatch: (evt) => {
          pendingTier = evt.model_tier ?? null;
          // Backend may still emit create dispatches — just update the card if present
          appendMessage(sessionId, {
            role: 'dispatch',
            id: `dispatch-${evt.job_id}`,
            jobId: evt.job_id,
            action: evt.action,
            subject: evt.subject,
            modelTier: evt.model_tier ?? null,
            status: 'running',
          });
          // Immediately tag the streaming assistant message with the tier
          if (pendingTier) {
            updateLastAgentMessage(sessionId, { modelTier: pendingTier });
          }
        },
        ...extraBody,
      })) {
        full += delta;
        updateLastAgentMessage(sessionId, { content: full, streaming: true });
      }
      updateLastAgentMessage(sessionId, { content: full, streaming: false });
    } catch (err) {
      if (err.name !== 'AbortError') {
        updateLastAgentMessage(sessionId, { content: `*Something went wrong. Please try again.*`, streaming: false });
      } else {
        updateLastAgentMessage(sessionId, { streaming: false });
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  const messages = activeSession?.messages ?? [];

  return (
    <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
      {/* Top bar */}
      <div style={{
        height: 50, flexShrink: 0, display: 'flex', alignItems: 'center',
        padding: '0 16px', gap: 10, borderBottom: '1px solid var(--color-sc-border)',
        background: 'var(--color-sc-surface)',
      }}>
        <AgentSwitcher />
        <span style={{ fontSize: 13, color: 'var(--color-sc-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
          {messages.length > 0 ? activeSession?.title : 'SovereignClaw'}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-sc-success)', display: 'inline-block' }} />
          Private & local
        </div>
      </div>

      {/* Messages */}
      {messages.length === 0 ? (
        <WelcomeScreen onSuggest={text => send(text)} />
      ) : (
        <div style={{ flex: 1, overflowY: 'auto', padding: '32px 0' }}>
          <div style={{ maxWidth: 720, margin: '0 auto', padding: '0 24px' }}>
            {messages.map(msg => <Message key={msg.id} msg={msg} />)}
            <div ref={bottomRef} />
          </div>
        </div>
      )}

      {/* Input area */}
      <div style={{ padding: '12px 20px 18px', flexShrink: 0 }}>
        <div style={{ maxWidth: 720, margin: '0 auto', position: 'relative' }}>
          <ChatInput
            value={input}
            onChange={setInput}
            onSend={() => send()}
            onAbort={() => abortRef.current?.abort()}
            isStreaming={isStreaming}
          />
          <div style={{ textAlign: 'center', marginTop: 8, fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
            {activeChatAgent
              ? <span>Using <span style={{ color: 'var(--color-sc-gold)' }}>{activeChatAgent.emoji} {activeChatAgent.name}</span> — Your data never leaves your infrastructure.</span>
              : 'SovereignClaw runs locally — your data never leaves your infrastructure.'
            }
          </div>
        </div>
      </div>
    </main>
  );
}
