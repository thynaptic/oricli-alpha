import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useSCStore, streamChat, selectActiveSession } from '../store';
import { IS_DEMO } from '../App';
import { Send, Square, Copy, Check, ChevronDown, X, Bot, Search, BookOpen, ListTodo, Workflow, FileText, BarChart2, Loader2, CheckCircle2, AlertCircle, FileCode2, ExternalLink, Paperclip, ArrowRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import TaskPlanCard from './TaskPlanCard';

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
        cursor: 'pointer', color: copied ? 'var(--color-sc-success)' : 'var(--color-sc-text-dim)',
        fontSize: 11, display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'var(--font-inter)',
        transition: 'color 0.15s',
      }}
    >
      {copied ? <Check size={11} /> : <Copy size={11} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

// Custom vscDarkPlus override — tighter padding, matches ORI's surface bg
// Token colour replacements:
//   #DCDCAA (yellow-green function names)  → #C8A96E (warm muted gold, on-brand)
//   #b5cea8 (sage-green numbers/symbols)   → #7FBFCF (soft teal-blue, neutral)
//   #4EC9B0 (teal type names)              → #7ECFCF (softer cyan)
const CODE_DARK_STYLE = (() => {
  const fix = (obj) => {
    if (typeof obj === 'string') {
      return obj
        .replace(/#DCDCAA/gi, '#C8A96E')
        .replace(/#b5cea8/gi, '#7FBFCF')
        .replace(/#4EC9B0/gi, '#7ECFCF');
    }
    if (Array.isArray(obj)) return obj.map(fix);
    if (obj && typeof obj === 'object') {
      return Object.fromEntries(Object.entries(obj).map(([k, v]) => [k, fix(v)]));
    }
    return obj;
  };
  const patched = fix({ ...vscDarkPlus });
  patched['pre[class*="language-"]'] = {
    ...patched['pre[class*="language-"]'],
    background: 'transparent', margin: 0, padding: 0,
  };
  patched['code[class*="language-"]'] = {
    ...patched['code[class*="language-"]'],
    background: 'transparent',
  };
  return patched;
})();

function makeMarkdownComponents(isDark) {
  return {
  code({ inline, className, children }) {
    const lang = (className ?? '').replace('language-', '') || 'text';
    const code = String(children).replace(/\n$/, '');
    if (inline) {
      return (
        <code style={{
          background: 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)', color: 'var(--color-sc-gold)', fontWeight: 600,
          padding: '1px 5px', borderRadius: 3, fontFamily: 'var(--font-mono)', fontSize: '0.88em',
        }}>{children}</code>
      );
    }
    return (
      <div style={{
        position: 'relative', margin: '12px 0', borderRadius: 10,
        background: isDark ? '#1e1e1e' : '#f5f5f5',
        border: isDark ? '1px solid rgba(255,255,255,0.06)' : '1px solid rgba(0,0,0,0.08)',
        overflow: 'hidden',
      }}>
        {lang && lang !== 'text' && (
          <div style={{
            position: 'absolute', top: 9, left: 14,
            fontSize: 10, fontWeight: 700, color: isDark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.3)',
            fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em',
            userSelect: 'none',
          }}>{lang}</div>
        )}
        <CopyButton text={code} />
        <SyntaxHighlighter
          language={lang}
          style={isDark ? CODE_DARK_STYLE : oneLight}
          customStyle={{
            borderRadius: 0, fontSize: 13, margin: 0,
            background: 'transparent',
            padding: lang && lang !== 'text' ? '30px 16px 14px' : '14px 16px',
          }}
          showLineNumbers={code.split('\n').length > 6}
          lineNumberStyle={{ color: isDark ? 'rgba(255,255,255,0.18)' : 'rgba(0,0,0,0.25)', fontSize: 11, userSelect: 'none', minWidth: '2.2em' }}
          wrapLines
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
  a({ href, children }) { return <a href={href} target="_blank" rel="noopener" style={{ color: 'var(--color-sc-gold)', textDecoration: 'underline', textDecorationColor: 'color-mix(in srgb, var(--color-sc-gold) 40%, transparent)' }}>{children}</a>; },
  hr() { return <hr style={{ border: 'none', borderTop: '1px solid var(--color-sc-border)', margin: '16px 0' }} />; },
  table({ children }) { return <div style={{ overflowX: 'auto', margin: '12px 0' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>{children}</table></div>; },
  th({ children }) { return <th style={{ border: '1px solid var(--color-sc-border)', padding: '6px 10px', background: 'var(--color-sc-surface)', color: 'var(--color-sc-text-muted)', textAlign: 'left', fontWeight: 600, fontSize: 12 }}>{children}</th>; },
  td({ children }) { return <td style={{ border: '1px solid var(--color-sc-border)', padding: '6px 10px', color: 'var(--color-sc-text)' }}>{children}</td>; },
  strong({ children }) { return <strong style={{ color: '#fff', fontWeight: 700 }}>{children}</strong>; },
  };
}

// ── Reaction Bar ──────────────────────────────────────────────────────────────

const REACTIONS = [
  { key: 'thumbs_up',   emoji: '👍', label: 'Helpful',     positive: true  },
  { key: 'heart',       emoji: '❤️', label: 'Love',        positive: true  },
  { key: 'fire',        emoji: '🔥', label: 'Amazing',     positive: true  },
  { key: 'star',        emoji: '⭐', label: 'Insightful',  positive: true  },
  { key: 'lightbulb',   emoji: '💡', label: 'Good idea',   positive: true  },
  { key: 'checkmark',   emoji: '✅', label: 'Correct',     positive: true  },
  { key: 'party',       emoji: '🎉', label: 'Celebrate',   positive: true  },
  { key: 'thumbs_down', emoji: '👎', label: 'Unhelpful',   positive: false },
  { key: 'xmark',       emoji: '❌', label: 'Incorrect',   positive: false },
  { key: 'sad',         emoji: '😞', label: 'Disappointed',positive: false },
];

function ReactionBar({ msg }) {
  const [selected, setSelected] = useState(null);
  const [hover, setHover] = useState(null);

  const sendReaction = async (r) => {
    if (selected === r.key) return; // already reacted
    setSelected(r.key);
    try {
      await fetch('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id:      String(msg.id ?? Date.now()),
          reaction:        r.key,
          is_positive:     r.positive,
          message_preview: (msg.content ?? '').slice(0, 200),
          session_id:      msg.sessionId ?? '',
        }),
      });
    } catch { /* non-critical */ }
  };

  return (
    <div style={{
      display: 'flex', gap: 4, marginTop: 8, flexWrap: 'wrap',
      opacity: 1, transition: 'opacity 0.2s',
    }}>
      {REACTIONS.map((r) => {
        const isSelected = selected === r.key;
        const isHovered  = hover === r.key;
        return (
          <button
            key={r.key}
            title={r.label}
            onClick={() => sendReaction(r)}
            onMouseEnter={() => setHover(r.key)}
            onMouseLeave={() => setHover(null)}
            style={{
              background: isSelected
                ? 'color-mix(in srgb, var(--color-sc-gold) 18%, transparent)'
                : isHovered ? 'rgba(255,255,255,0.07)' : 'transparent',
              border: isSelected
                ? '1px solid color-mix(in srgb, var(--color-sc-gold) 45%, transparent)'
                : '1px solid transparent',
              borderRadius: 8,
              cursor: 'pointer',
              fontSize: 16,
              lineHeight: 1,
              padding: '3px 5px',
              transition: 'all 0.15s',
              transform: isHovered && !isSelected ? 'scale(1.2)' : 'scale(1)',
              opacity: selected && !isSelected ? 0.35 : 1,
            }}
          >
            {r.emoji}
          </button>
        );
      })}
    </div>
  );
}

// ── Message ───────────────────────────────────────────────────────────────────

function Message({ msg, onEdit }) {
  const [showReactions, setShowReactions] = useState(false);
  const [editing, setEditing]             = useState(false);
  const [editText, setEditText]           = useState('');
  const [hoverBubble, setHoverBubble]     = useState(false);
  const editRef                           = useRef(null);
  const isUser = msg.role === 'user';
  const isDark = useSCStore(s => s.theme) !== 'light';
  const mdComponents = useMemo(() => makeMarkdownComponents(isDark), [isDark]);

  useEffect(() => {
    if (editing && editRef.current) {
      editRef.current.focus();
      editRef.current.selectionStart = editRef.current.value.length;
    }
  }, [editing]);

  if (msg.role === 'dispatch') return <DispatchCard msg={msg} />;
  if (msg.role === 'task_plan') return <TaskPlanCard tasks={msg.tasks} />;
  if (msg.role === 'routing') return <RoutingCard msg={msg} />;

  if (isUser) {
    return (
      <div
        className="animate-fade-slide"
        style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20, gap: 6, alignItems: 'flex-start' }}
        onMouseEnter={() => setHoverBubble(true)}
        onMouseLeave={() => setHoverBubble(false)}
      >
        {/* Edit pencil — shown on hover */}
        {onEdit && hoverBubble && !editing && (
          <button
            title="Edit message"
            onClick={() => { setEditText(msg.content); setEditing(true); }}
            style={{
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: 'var(--color-sc-text-dim)', padding: '4px', marginTop: 6,
              opacity: 0.6, transition: 'opacity 0.15s',
              display: 'flex', alignItems: 'center',
            }}
            onMouseEnter={e => e.currentTarget.style.opacity = '1'}
            onMouseLeave={e => e.currentTarget.style.opacity = '0.6'}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
        )}

        {editing ? (
          <div style={{ maxWidth: '72%', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <textarea
              ref={editRef}
              value={editText}
              onChange={e => setEditText(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  setEditing(false);
                  onEdit(msg.id, editText);
                }
                if (e.key === 'Escape') setEditing(false);
              }}
              rows={Math.min(8, editText.split('\n').length + 1)}
              style={{
                width: '100%', resize: 'none', background: 'color-mix(in srgb, var(--color-sc-gold) 7%, transparent)',
                border: '1px solid color-mix(in srgb, var(--color-sc-gold) 40%, transparent)', borderRadius: 12,
                padding: '10px 14px', fontSize: 14, lineHeight: 1.65,
                color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)',
                outline: 'none', boxShadow: '0 0 0 2px color-mix(in srgb, var(--color-sc-gold) 15%, transparent)',
              }}
            />
            <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setEditing(false)}
                style={{
                  padding: '5px 12px', borderRadius: 7, fontSize: 12, cursor: 'pointer',
                  background: 'transparent', border: '1px solid var(--color-sc-border)',
                  color: 'var(--color-sc-text-muted)',
                }}
              >Cancel</button>
              <button
                onClick={() => { setEditing(false); onEdit(msg.id, editText); }}
                style={{
                  padding: '5px 14px', borderRadius: 7, fontSize: 12, cursor: 'pointer',
                  background: 'color-mix(in srgb, var(--color-sc-gold) 15%, transparent)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 40%, transparent)',
                  color: 'var(--color-sc-gold)', fontWeight: 600,
                }}
              >Save & Resend</button>
            </div>
          </div>
        ) : (
          <div style={{
            maxWidth: '72%', background: 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)',
            border: '1px solid color-mix(in srgb, var(--color-sc-gold) 18%, transparent)', borderRadius: '16px 16px 4px 16px',
            padding: '10px 16px', fontSize: 14, lineHeight: 1.65, color: 'var(--color-sc-text)',
          }}>
            {msg.content}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className="animate-fade-slide"
      style={{ display: 'flex', gap: 14, marginBottom: 24, alignItems: 'flex-start' }}
      onMouseEnter={() => setShowReactions(true)}
      onMouseLeave={() => setShowReactions(false)}
    >
      {/* Avatar */}
      <div style={{
        width: 30, height: 30, flexShrink: 0, borderRadius: '50%', marginTop: 2,
        background: 'rgba(136,117,255,0.08)', border: '1px solid rgba(136,117,255,0.20)',
        overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <img src="/oricli-avatar.png" alt="ORI" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      </div>
      {/* Content */}
      <div style={{ flex: 1, minWidth: 0, fontSize: 14, color: 'var(--color-sc-text)', lineHeight: 1.7 }}>
        {msg.streaming && !msg.content ? (
          msg.modelTier === 'research' ? <DeepResearchBanner /> : <ThinkingDots />
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {msg.content ?? ''}
          </ReactMarkdown>
        )}
        {msg.scaiCorrected && (
          <div title="SCAI Critique-Revision loop detected a constitutional violation and applied a correction." style={{
            display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 8,
            padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600,
            background: 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--color-sc-gold) 28%, transparent)',
            color: 'color-mix(in srgb, var(--color-sc-gold) 85%, transparent)', letterSpacing: '0.03em',
          }}>
            <img src="/ori-mark.png" alt="SCAI" width="10" height="10" className="logo-light-src" style={{ flexShrink: 0, objectFit: 'contain' }} />
            SCAI corrected
          </div>
        )}
        {!msg.streaming && showReactions && (
          <ReactionBar msg={msg} />
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
      <img src="/ori-mark.png" alt="ORI" className="logo-adaptive" style={{ width: 80, height: 80, objectFit: 'contain', marginBottom: 18 }} />
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
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'color-mix(in srgb, var(--color-sc-gold) 40%, transparent)'; e.currentTarget.style.background = 'color-mix(in srgb, var(--color-sc-gold) 5%, transparent)'; e.currentTarget.style.color = 'var(--color-sc-text)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--color-sc-border)'; e.currentTarget.style.background = 'var(--color-sc-surface)'; e.currentTarget.style.color = 'var(--color-sc-text-muted)'; }}
          >{s}</button>
        ))}
      </div>
    </div>
  );
}

// ── Chat input ────────────────────────────────────────────────────────────────

function ChatInput({ value, onChange, onSend, onAbort, isStreaming, disabled }) {
  const [focused, setFocused]     = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState(null); // { text, ok }
  const fileRef = useRef(null);

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(); }
  }

  function handleInput(e) {
    onChange(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 180) + 'px';
  }

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';

    const allowed = ['.txt', '.md', '.csv', '.pdf'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
      setUploadMsg({ text: `Unsupported type. Use: ${allowed.join(', ')}`, ok: false });
      setTimeout(() => setUploadMsg(null), 4000);
      return;
    }

    setUploading(true);
    setUploadMsg(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await fetch('/api/v1/documents/upload', { method: 'POST', body: form });
      const d = await r.json();
      if (r.ok) {
        setUploadMsg({ text: `✓ "${file.name}" ingested — ${d.chunks} chunks`, ok: true });
      } else {
        setUploadMsg({ text: d.error ?? 'Upload failed', ok: false });
      }
    } catch (err) {
      setUploadMsg({ text: 'Upload error: ' + err.message, ok: false });
    } finally {
      setUploading(false);
      setTimeout(() => setUploadMsg(null), 5000);
    }
  }

  return (
    <div style={{ position: 'relative' }}>
      {/* Upload status toast */}
      {uploadMsg && (
        <div style={{
          position: 'absolute', bottom: 'calc(100% + 8px)', left: 0, right: 0,
          background: uploadMsg.ok ? 'rgba(80,200,120,0.12)' : 'rgba(220,80,80,0.12)',
          border: `1px solid ${uploadMsg.ok ? 'rgba(80,200,120,0.3)' : 'rgba(220,80,80,0.3)'}`,
          borderRadius: 8, padding: '8px 14px', fontSize: 12,
          color: uploadMsg.ok ? 'rgba(80,220,120,0.95)' : 'rgba(255,100,100,0.95)',
          fontFamily: 'var(--font-mono)',
        }}>
          {uploadMsg.text}
        </div>
      )}

      <div style={{
        border: `1px solid ${focused ? 'color-mix(in srgb, var(--color-sc-gold) 50%, transparent)' : 'var(--color-sc-border2)'}`,
        borderRadius: 14, background: 'var(--color-sc-surface)',
        boxShadow: focused ? '0 0 0 3px color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'none',
        transition: 'border-color 0.2s, box-shadow 0.2s',
      }}>
        {/* Hidden file input */}
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.md,.csv,.pdf"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <textarea
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Message ORI Studio…"
          rows={1}
          style={{
            display: 'block', width: '100%', background: 'transparent',
            border: 'none', outline: 'none', resize: 'none', padding: '14px 90px 14px 16px',
            color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 14,
            lineHeight: 1.55, minHeight: 52, overflow: 'hidden',
          }}
        />
        <div style={{ position: 'absolute', right: 10, bottom: 10, display: 'flex', gap: 6 }}>
          {/* Attach button */}
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            title="Upload file (txt / md / csv / pdf)"
            style={{
              width: 34, height: 34, borderRadius: 9, border: 'none',
              cursor: uploading ? 'not-allowed' : 'pointer',
              background: 'rgba(128,128,128,0.1)',
              color: uploading ? 'var(--color-sc-gold)' : 'var(--color-sc-text-dim)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'background 0.15s, color 0.15s',
            }}
            onMouseEnter={e => { if (!uploading) e.currentTarget.style.background = 'color-mix(in srgb, var(--color-sc-gold) 10%, transparent)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(128,128,128,0.1)'; }}
          >
            {uploading
              ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
              : <Paperclip size={14} />}
          </button>
          {/* Send / abort */}
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
          background: activeChatAgent ? 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)' : 'rgba(128,128,128,0.1)',
          border: `1px solid ${activeChatAgent ? 'color-mix(in srgb, var(--color-sc-gold) 35%, transparent)' : 'var(--color-sc-border)'}`,
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
              background: !activeChatAgent ? 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'transparent',
              color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 13,
              textAlign: 'left', transition: 'background 0.12s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(128,128,128,0.1)'}
            onMouseLeave={e => e.currentTarget.style.background = !activeChatAgent ? 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'transparent'}
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
                        background: isActive ? 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'transparent',
                        color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 13,
                        textAlign: 'left', transition: 'background 0.12s',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'rgba(128,128,128,0.1)'}
                      onMouseLeave={e => e.currentTarget.style.background = isActive ? 'color-mix(in srgb, var(--color-sc-gold) 8%, transparent)' : 'transparent'}
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
const _AGENT_RE  = /(?:need|want|create|make|build|design|set\s+up)\s+(?:an?\s+)?(?:agent|persona|bot|assistant)(?:\s+(?:that|to|which|for|who|named|called))?\s*(.{5,})/i;
const _WORKFLOW_RE = /(?:need|want|create|make|build|design|set\s+up)\s+(?:an?\s+)?workflow(?:\s+(?:that|to|which|for))?\s*(.{5,})/i;

// Returns { type: 'agent'|'workflow', subject } or null — checked BEFORE canvas intent
function detectRoutingIntent(text) {
  if (_TASK_RE.test(text)) return null;
  const wm = _WORKFLOW_RE.exec(text);
  if (wm) return { type: 'workflow', subject: wm[1].replace(/[.!?]+$/, '').trim() };
  const am = _AGENT_RE.exec(text);
  if (am) return { type: 'agent', subject: am[1].replace(/[.!?]+$/, '').trim() };
  return null;
}

function detectCreateIntent(text) {
  if (_TASK_RE.test(text)) return null; // already handled by Task pattern
  const m = _CREATE_RE.exec(text);
  return m ? m[1].replace(/[.!?]+$/, '').trim() : null;
}

// Score similarity between a subject string and an item's name+description
function subjectOverlap(subject, name = '', description = '') {
  const words = subject.toLowerCase().split(/\W+/).filter(w => w.length > 3);
  const haystack = `${name} ${description}`.toLowerCase();
  const hits = words.filter(w => haystack.includes(w));
  return hits.length / Math.max(words.length, 1);
}

// ── Routing card — surfaces agent/workflow creation intent ─────────────────
function RoutingCard({ msg }) {
  const setActivePage              = useSCStore(s => s.setActivePage);
  const setPendingAgentPrompt      = useSCStore(s => s.setPendingAgentPrompt);
  const setPendingWorkflowPrompt   = useSCStore(s => s.setPendingWorkflowPrompt);
  const setPendingAgentIntentId    = useSCStore(s => s.setPendingAgentIntentId);
  const setPendingWorkflowIntentId = useSCStore(s => s.setPendingWorkflowIntentId);
  const logCreationIntent          = useSCStore(s => s.logCreationIntent);
  const updateCreationIntent       = useSCStore(s => s.updateCreationIntent);
  const creationIntents            = useSCStore(s => s.creationIntents);
  const agents                     = useSCStore(s => s.agents);
  const setActiveAgentId           = useSCStore(s => s.setActiveAgentId);

  const isAgent = msg.targetPage === 'agents';
  const intentIdRef = useRef(null);

  // Log intent exactly once on mount — always from chat surface
  useEffect(() => {
    intentIdRef.current = logCreationIntent({
      type: isAgent ? 'agent' : 'workflow',
      subject: msg.subject,
      origin_surface: 'chat',
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Find similar existing agents (store) or past workflow intents
  const similar = isAgent
    ? agents.filter(a => subjectOverlap(msg.subject, a.name, a.description || a.systemPrompt) >= 0.25).slice(0, 4)
    : creationIntents
        .filter(ci => ci.type === 'workflow' && ci.action === 'created' && subjectOverlap(msg.subject, ci.subject) >= 0.25)
        .slice(0, 4);

  function buildNew() {
    const intentId = intentIdRef.current;
    if (isAgent) {
      setPendingAgentPrompt(msg.fullText);
      setPendingAgentIntentId(intentId);
      setActivePage('agents');
    } else {
      setPendingWorkflowPrompt(msg.fullText);
      setPendingWorkflowIntentId(intentId);
      setActivePage('workflows');
    }
  }

  function useExistingAgent(agent) {
    if (intentIdRef.current) {
      updateCreationIntent(intentIdRef.current, { resolution_quality: 'reused', resultId: agent.id, resultName: agent.name });
    }
    setActiveAgentId(agent.id);
    setActivePage('agents');
  }

  function useExistingWorkflow() {
    if (intentIdRef.current) {
      updateCreationIntent(intentIdRef.current, { resolution_quality: 'reused' });
    }
    setActivePage('workflows');
  }

  const totalPast = creationIntents.filter(ci => ci.type === (isAgent ? 'agent' : 'workflow')).length;

  return (
    <div style={{ margin: '4px 0 4px 44px', maxWidth: 480 }}>
      <div style={{
        border: '1px solid color-mix(in srgb, var(--color-sc-gold) 28%, transparent)',
        borderRadius: 10,
        padding: '12px 14px',
        background: 'color-mix(in srgb, var(--color-sc-gold) 7%, transparent)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 6 }}>
          {isAgent ? <Bot size={15} color="var(--color-sc-gold)" /> : <Workflow size={15} color="var(--color-sc-gold)" />}
          <span style={{ fontWeight: 600, fontSize: 12, color: 'var(--color-sc-gold)' }}>
            {isAgent ? 'Agent creation detected' : 'Workflow creation detected'}
          </span>
          {totalPast > 0 && (
            <span style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--color-sc-text-dim)' }}>
              {totalPast} {isAgent ? 'agent' : 'workflow'}{totalPast !== 1 ? 's' : ''} built so far
            </span>
          )}
        </div>

        <p style={{ margin: '0 0 10px', fontSize: 12.5, color: 'var(--color-sc-text-dim)', lineHeight: 1.45 }}>
          {msg.subject}
        </p>

        {similar.length > 0 && (
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', marginBottom: 5, fontWeight: 600 }}>
              {isAgent
                ? `You've built ${similar.length} similar agent${similar.length > 1 ? 's' : ''} — use one or build fresh?`
                : `You've created ${similar.length} similar workflow${similar.length > 1 ? 's' : ''} — use one or build fresh?`
              }
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              {similar.map(item => (
                <button
                  key={item.id || item.subject}
                  onClick={() => isAgent ? useExistingAgent(item) : useExistingWorkflow()}
                  style={{
                    padding: '3px 9px', borderRadius: 5, fontSize: 11,
                    background: 'color-mix(in srgb, var(--color-sc-gold) 12%, transparent)', color: 'var(--color-sc-gold)',
                    border: '1px solid color-mix(in srgb, var(--color-sc-gold) 30%, transparent)', cursor: 'pointer', fontWeight: 600,
                  }}
                >
                  {item.emoji ? `${item.emoji} ` : ''}{isAgent ? item.name : item.subject}
                </button>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={buildNew}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            padding: '5px 12px', borderRadius: 6,
            background: 'var(--color-sc-gold)', color: '#0D0D0D',
            border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 11.5,
          }}
        >
          <ArrowRight size={11} />
          {similar.length > 0 ? 'Build new' : (isAgent ? 'Open Vibe Studio' : 'Open Workflows')}
        </button>
      </div>
    </div>
  );
}

export function ChatArea() {
  const activeSession          = useSCStore(selectActiveSession);
  const activeModel            = useSCStore(s => s.activeModel);
  const activeSkill            = useSCStore(s => s.activeSkill);
  const isStreaming            = useSCStore(s => s.isStreaming);
  const appendMessage          = useSCStore(s => s.appendMessage);
  const updateLastAgentMessage = useSCStore(s => s.updateLastAgentMessage);
  const updateMessage          = useSCStore(s => s.updateMessage);
  const truncateAfter          = useSCStore(s => s.truncateAfter);
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

    // ── Agent / Workflow routing — surfaces a card, no LLM call ──────────────
    const routingIntent = detectRoutingIntent(text);
    if (routingIntent) {
      appendMessage(sessionId, { role: 'user', content: text, id: Date.now() });
      appendMessage(sessionId, {
        role: 'routing',
        id: `routing-${Date.now()}`,
        targetPage: routingIntent.type === 'agent' ? 'agents' : 'workflows',
        subject: routingIntent.subject,
        fullText: text,
      });
      return;
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
    let taskPlanMsgId = null; // tracks the injected task plan card message

    try {
      let full = '';
      // Pass profile field to Go backbone for sovereign profile routing
      const extraBody = activeChatAgent ? { profile: activeChatAgent.id } : IS_DEMO ? { profile: 'smb_assistant' } : {};
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
        onTaskPlan: (payload) => {
          // Insert a task plan card message before the streaming assistant bubble
          taskPlanMsgId = `task-plan-${Date.now()}`;
          // Insert it just before the last (assistant) message by appending to session
          // and relying on insertion order — plan card was appended before assistant slot
          const store = useSCStore.getState();
          store.insertBeforeLastMessage(sessionId, {
            role: 'task_plan',
            id: taskPlanMsgId,
            tasks: payload.tasks ?? [],
          });
        },
        onTaskUpdate: (payload) => {
          if (!taskPlanMsgId) return;
          useSCStore.getState().updateMessage(sessionId, taskPlanMsgId, (prev) => ({
            ...prev,
            tasks: (prev.tasks ?? []).map(t =>
              t.id === payload.id
                ? { ...t, status: payload.status, snippet: payload.snippet }
                : t
            ),
          }));
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

  async function editAndResend(msgId, newText) {
    const text = newText.trim();
    if (!text || isStreaming) return;

    const sessionId = activeSession.id;

    // 1. Update the user message in place
    updateMessage(sessionId, msgId, { content: text });
    // 2. Drop everything after it (old assistant reply + any dispatch cards)
    truncateAfter(sessionId, msgId);
    // 3. Append a fresh streaming assistant slot
    const newAssistantId = Date.now() + 1;
    appendMessage(sessionId, { role: 'assistant', content: '', streaming: true, id: newAssistantId });
    setIsStreaming(true);

    const systemContent = activeChatAgent
      ? activeChatAgent.systemPrompt
      : activeSkill ? `You are operating with the ${activeSkill} skill profile.` : null;

    // Build history up to (and including) the edited user message
    const allMsgs = useSCStore.getState().sessions.find(s => s.id === sessionId)?.messages ?? [];
    const userIdx = allMsgs.findIndex(m => m.id === msgId);
    const historySlice = allMsgs.slice(0, userIdx); // messages before the edited one

    const messages = [
      ...(systemContent ? [{ role: 'system', content: systemContent }] : []),
      ...historySlice.map(m => ({ role: m.role, content: m.content })),
      { role: 'user', content: text },
    ];

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      let full = '';
      const extraBody = activeChatAgent ? { profile: activeChatAgent.id } : IS_DEMO ? { profile: 'smb_assistant' } : {};
      for await (const delta of streamChat({ messages, model: activeModel, signal: controller.signal, extraBody })) {
        full += delta;
        updateLastAgentMessage(sessionId, { content: full, streaming: true });
      }
      updateLastAgentMessage(sessionId, { content: full, streaming: false });
    } catch (e) {
      if (e?.name !== 'AbortError') {
        updateLastAgentMessage(sessionId, { content: '⚠️ Error regenerating reply.', streaming: false });
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
          {messages.length > 0 ? activeSession?.title : 'ORI Studio'}
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
            {messages.map(msg => (
              <Message key={msg.id} msg={msg} onEdit={msg.role === 'user' ? (id, txt) => editAndResend(id, txt) : null} />
            ))}
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
              : 'ORI Studio runs locally — your data never leaves your infrastructure.'
            }
          </div>
        </div>
      </div>
    </main>
  );
}
