import { useState, useRef, useEffect } from 'react';
import { useSCStore, streamChat, selectActiveSession } from '../store';
import { Send, Paperclip, ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

// ── Typing indicator ──────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'center', padding: '4px 0' }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 6, height: 6, borderRadius: '50%', background: 'var(--color-sc-gold)',
          display: 'inline-block',
          animation: `typingDot 0.9s ease-in-out ${i * 0.2}s infinite`,
        }} />
      ))}
    </div>
  );
}

// ── DGE trace accordion ───────────────────────────────────────────────────────

function DGETrace({ trace }) {
  const [open, setOpen] = useState(false);
  if (!trace) return null;
  return (
    <div style={{ marginTop: 8, borderTop: '1px solid var(--color-sc-border)', paddingTop: 6 }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          background: 'none', border: 'none', cursor: 'pointer', padding: '2px 0',
          display: 'flex', alignItems: 'center', gap: 5, color: 'var(--color-sc-text-muted)', fontSize: 11,
        }}
      >
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        <span style={{ fontFamily: 'var(--font-grotesk)', letterSpacing: '0.06em' }}>
          {trace.modules?.length ?? 0} modules · consensus {trace.consensus != null ? `${Math.round(trace.consensus * 100)}%` : '—'}
        </span>
      </button>
      {open && (
        <div style={{
          marginTop: 6, padding: '8px 12px', background: 'rgba(0,0,0,0.3)',
          borderRadius: 6, fontSize: 11, fontFamily: 'var(--font-mono)',
        }}>
          {trace.modules?.map((m, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 0', color: 'var(--color-sc-text-muted)' }}>
              <span style={{ color: 'var(--color-sc-gold)', minWidth: 20 }}>{i + 1}.</span>
              <span>{m.name ?? m}</span>
              {m.score != null && <span style={{ color: 'var(--color-sc-success)', marginLeft: 'auto' }}>{(m.score * 100).toFixed(0)}%</span>}
            </div>
          ))}
          {trace.dag && (
            <pre style={{ margin: '8px 0 0', color: 'var(--color-sc-text-dim)', fontSize: 10, whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(trace.dag, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

// ── Artifact Card ─────────────────────────────────────────────────────────────

function ArtifactCard({ artifact }) {
  const [copied, setCopied] = useState(false);
  const [versionIdx, setVersionIdx] = useState(artifact.versions.length - 1);
  const content = artifact.versions[versionIdx];

  function copy() {
    navigator.clipboard.writeText(content).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); });
  }

  return (
    <div style={{
      marginTop: 12, border: '1px solid var(--color-sc-border2)', borderRadius: 8, overflow: 'hidden',
    }}>
      <div style={{
        padding: '7px 12px', background: 'var(--color-sc-surface)', display: 'flex', alignItems: 'center',
        gap: 8, borderBottom: '1px solid var(--color-sc-border)',
      }}>
        <span style={{ fontSize: 11, fontFamily: 'var(--font-grotesk)', fontWeight: 600, color: 'var(--color-sc-gold)', letterSpacing: '0.05em', flex: 1 }}>
          {artifact.title}
        </span>
        {artifact.versions.length > 1 && (
          <select value={versionIdx} onChange={e => setVersionIdx(Number(e.target.value))}
            style={{ background: 'var(--color-sc-surface2)', border: '1px solid var(--color-sc-border)', color: 'var(--color-sc-text-muted)', fontSize: 10, borderRadius: 4, padding: '2px 4px' }}>
            {artifact.versions.map((_, i) => <option key={i} value={i}>v{i + 1}</option>)}
          </select>
        )}
        <button onClick={copy} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-muted)', display: 'flex', alignItems: 'center', gap: 3, fontSize: 11 }}>
          {copied ? <Check size={12} style={{ color: 'var(--color-sc-success)' }} /> : <Copy size={12} />}
        </button>
      </div>
      <SyntaxHighlighter
        language={artifact.language || 'text'}
        style={atomDark}
        customStyle={{ margin: 0, borderRadius: 0, fontSize: 12, maxHeight: 300, background: '#0D0D1A' }}
        showLineNumbers
      >
        {content}
      </SyntaxHighlighter>
    </div>
  );
}

// ── Message Bubble ────────────────────────────────────────────────────────────

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user';
  const artifacts = msg.artifacts ?? [];

  const markdownComponents = {
    code({ inline, className, children }) {
      const lang = (className ?? '').replace('language-', '') || 'text';
      if (inline) {
        return (
          <code style={{ background: 'rgba(196,164,74,0.12)', color: 'var(--color-sc-gold)', padding: '1px 5px', borderRadius: 3, fontFamily: 'var(--font-mono)', fontSize: '0.9em' }}>
            {children}
          </code>
        );
      }
      return (
        <SyntaxHighlighter language={lang} style={atomDark}
          customStyle={{ borderRadius: 6, fontSize: 12, margin: '8px 0', background: '#0D0D1A' }}
          showLineNumbers
        >{String(children).replace(/\n$/, '')}</SyntaxHighlighter>
      );
    },
    p({ children }) { return <p style={{ margin: '6px 0' }}>{children}</p>; },
    ul({ children }) { return <ul style={{ margin: '6px 0', paddingLeft: 20 }}>{children}</ul>; },
    ol({ children }) { return <ol style={{ margin: '6px 0', paddingLeft: 20 }}>{children}</ol>; },
    li({ children }) { return <li style={{ marginBottom: 2 }}>{children}</li>; },
    h1({ children }) { return <h1 style={{ fontSize: 18, fontFamily: 'var(--font-grotesk)', fontWeight: 700, margin: '12px 0 6px', color: 'var(--color-sc-gold)' }}>{children}</h1>; },
    h2({ children }) { return <h2 style={{ fontSize: 15, fontFamily: 'var(--font-grotesk)', fontWeight: 600, margin: '10px 0 5px', color: 'var(--color-sc-text)' }}>{children}</h2>; },
    h3({ children }) { return <h3 style={{ fontSize: 13, fontFamily: 'var(--font-grotesk)', fontWeight: 600, margin: '8px 0 4px', color: 'var(--color-sc-text)' }}>{children}</h3>; },
    blockquote({ children }) { return <blockquote style={{ borderLeft: '3px solid var(--color-sc-gold)', paddingLeft: 12, margin: '8px 0', color: 'var(--color-sc-text-muted)' }}>{children}</blockquote>; },
    a({ href, children }) { return <a href={href} target="_blank" rel="noopener" style={{ color: 'var(--color-sc-blue)', textDecoration: 'underline' }}>{children}</a>; },
    table({ children }) { return <table style={{ width: '100%', borderCollapse: 'collapse', margin: '8px 0', fontSize: 12 }}>{children}</table>; },
    th({ children }) { return <th style={{ border: '1px solid var(--color-sc-border)', padding: '4px 8px', background: 'var(--color-sc-surface)', color: 'var(--color-sc-gold)', textAlign: 'left' }}>{children}</th>; },
    td({ children }) { return <td style={{ border: '1px solid var(--color-sc-border)', padding: '4px 8px' }}>{children}</td>; },
  };

  return (
    <div
      className="animate-fade-slide"
      style={{
        display: 'flex', flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 16, padding: '0 20px',
      }}
    >
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: 10, maxWidth: '80%',
        flexDirection: isUser ? 'row-reverse' : 'row',
      }}>
        {/* Avatar */}
        <div style={{
          width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
          background: isUser ? 'rgba(77,158,255,0.15)' : 'rgba(196,164,74,0.15)',
          border: `1px solid ${isUser ? 'rgba(77,158,255,0.3)' : 'rgba(196,164,74,0.3)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 9, fontFamily: 'var(--font-grotesk)', letterSpacing: '0.04em',
          color: isUser ? 'var(--color-sc-blue)' : 'var(--color-sc-gold)',
          fontWeight: 600, marginTop: 2,
        }}>
          {isUser ? 'YOU' : 'SC'}
        </div>

        {/* Bubble */}
        <div style={{
          background: isUser ? 'rgba(77,158,255,0.07)' : 'rgba(196,164,74,0.05)',
          border: `1px solid ${isUser ? 'rgba(77,158,255,0.15)' : 'rgba(196,164,74,0.12)'}`,
          borderRadius: 10, padding: '10px 14px',
          color: 'var(--color-sc-text)', fontSize: 13.5, lineHeight: 1.65,
        }}>
          {msg.streaming && !msg.content ? (
            <TypingIndicator />
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {msg.content ?? ''}
            </ReactMarkdown>
          )}
          {artifacts.map((a, i) => <ArtifactCard key={i} artifact={a} />)}
          <DGETrace trace={msg.trace} />
        </div>
      </div>

      <div style={{
        fontSize: 10, color: 'var(--color-sc-text-dim)', marginTop: 4,
        marginRight: isUser ? 38 : 0, marginLeft: isUser ? 0 : 38,
      }}>
        {isUser ? 'COMMANDER' : 'SOVEREIGNCLAW'}
        {msg.model && <span style={{ color: 'var(--color-sc-text-dim)', marginLeft: 6 }}>· {msg.model}</span>}
      </div>
    </div>
  );
}

// ── Mission Canvas ────────────────────────────────────────────────────────────

export function MissionCanvas() {
  const activeSession = useSCStore(selectActiveSession);
  const activeModel = useSCStore(s => s.activeModel);
  const activeSkill = useSCStore(s => s.activeSkill);
  const isStreaming = useSCStore(s => s.isStreaming);
  const appendMessage = useSCStore(s => s.appendMessage);
  const updateLastAgentMessage = useSCStore(s => s.updateLastAgentMessage);
  const setIsStreaming = useSCStore(s => s.setIsStreaming);
  const renameSession = useSCStore(s => s.renameSession);

  const [input, setInput] = useState('');
  const bottomRef = useRef(null);
  const abortRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession?.messages]);

  async function send() {
    if (!input.trim() || isStreaming) return;
    const text = input.trim();
    setInput('');

    const sessionId = activeSession.id;

    // Auto-title on first message
    if (activeSession.messages.length === 0) {
      renameSession(sessionId, text.slice(0, 42) + (text.length > 42 ? '…' : ''));
    }

    appendMessage(sessionId, { role: 'user', content: text, id: Date.now() });
    appendMessage(sessionId, { role: 'assistant', content: '', streaming: true, id: Date.now() + 1 });
    setIsStreaming(true);

    const messages = [
      ...(activeSkill ? [{ role: 'system', content: `Use skill: ${activeSkill}` }] : []),
      ...activeSession.messages.map(m => ({ role: m.role, content: m.content })),
      { role: 'user', content: text },
    ];

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      let full = '';
      for await (const delta of streamChat({ messages, model: activeModel, signal: controller.signal })) {
        full += delta;
        updateLastAgentMessage(sessionId, { content: full, streaming: true });
      }
      updateLastAgentMessage(sessionId, { content: full, streaming: false });
    } catch (err) {
      if (err.name !== 'AbortError') {
        updateLastAgentMessage(sessionId, {
          content: `*Error: ${err.message}*`,
          streaming: false,
        });
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.startsWith('/goal ')) {
        const title = input.slice(6).trim();
        if (title) useSCStore.getState().addGoal(title);
        setInput('');
        return;
      }
      send();
    }
  }

  const messages = activeSession?.messages ?? [];
  const empty = messages.length === 0;

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', paddingTop: 20 }}>
        {empty ? (
          <EmptyState />
        ) : (
          messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)
        )}
        <div ref={bottomRef} />
      </div>

      {/* Command Bar */}
      <CommandBar
        value={input}
        onChange={setInput}
        onKeyDown={handleKeyDown}
        onSend={send}
        onAbort={() => abortRef.current?.abort()}
        isStreaming={isStreaming}
        textareaRef={textareaRef}
      />
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: 40 }}>
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" style={{ marginBottom: 20, opacity: 0.4 }}>
        <path d="M12 2 L14 8 L20 6 L16 11 L20 14 L14 13 L12 20 L10 13 L4 14 L8 11 L4 6 L10 8 Z" fill="#C4A44A" />
        <circle cx="12" cy="11" r="2" fill="#080810" />
      </svg>
      <div style={{ fontFamily: 'var(--font-grotesk)', fontSize: 20, fontWeight: 700, color: 'var(--color-sc-text)', marginBottom: 8 }}>
        ORI Studio
      </div>
      <div style={{ color: 'var(--color-sc-text-muted)', fontSize: 13, textAlign: 'center', maxWidth: 360, lineHeight: 1.6 }}>
        Sovereign intelligence. No rented minds. Issue a directive below.
      </div>
      <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 8, width: '100%', maxWidth: 400 }}>
        {[
          { cmd: '/goal Build a distributed cache layer', label: 'Set a sovereign goal' },
          { cmd: 'Audit the current Go backbone for race conditions', label: 'Direct analysis' },
          { cmd: 'Design a new Hive module for web scraping', label: 'Module design' },
        ].map(s => (
          <button key={s.cmd}
            onClick={() => useSCStore.getState().sessions && null}
            style={{
              background: 'rgba(196,164,74,0.05)', border: '1px solid var(--color-sc-border)',
              borderRadius: 8, padding: '8px 14px', color: 'var(--color-sc-text-muted)',
              fontFamily: 'var(--font-mono)', fontSize: 11, cursor: 'default',
              textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 2,
            }}>
            <span style={{ color: 'var(--color-sc-text)', fontSize: 12 }}>{s.cmd}</span>
            <span>{s.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Command Bar ───────────────────────────────────────────────────────────────

function CommandBar({ value, onChange, onKeyDown, onSend, onAbort, isStreaming, textareaRef }) {
  const [focused, setFocused] = useState(false);
  const isSlash = value.startsWith('/');
  const slashCmd = isSlash ? value.split(' ')[0] : null;

  const SLASH_HINTS = {
    '/goal': 'Add a sovereign goal',
    '/hive': 'Query hive status',
    '/search': 'Web search',
    '/code': 'Code generation mode',
  };

  return (
    <div style={{ padding: '12px 20px 16px', borderTop: '1px solid var(--color-sc-border)' }}>
      {/* Slash hint */}
      {isSlash && SLASH_HINTS[slashCmd] && (
        <div style={{
          marginBottom: 6, fontSize: 11, color: 'var(--color-sc-gold)', fontFamily: 'var(--font-mono)',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span style={{ opacity: 0.6 }}>{slashCmd}</span>
          <span style={{ color: 'var(--color-sc-text-muted)' }}>→ {SLASH_HINTS[slashCmd]}</span>
        </div>
      )}
      <div style={{
        display: 'flex', alignItems: 'flex-end', gap: 10,
        padding: '10px 14px',
        background: 'var(--color-sc-surface)',
        border: `1px solid ${focused ? 'var(--color-sc-gold)' : 'var(--color-sc-border2)'}`,
        borderRadius: 12,
        className: focused ? 'animate-command-glow' : '',
        boxShadow: focused ? '0 0 12px rgba(196,164,74,0.2)' : 'none',
        transition: 'border-color 0.2s, box-shadow 0.2s',
      }}>
        <label htmlFor="sc-file-upload" title="Attach file" style={{ cursor: 'pointer', color: 'var(--color-sc-text-muted)', lineHeight: 1, flexShrink: 0, alignSelf: 'flex-end', paddingBottom: 2 }}>
          <Paperclip size={15} />
        </label>
        <input id="sc-file-upload" type="file" style={{ display: 'none' }} />
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => { onChange(e.target.value); e.target.style.height = 'auto'; e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`; }}
          onKeyDown={onKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Issue a directive to the Sovereign…"
          rows={1}
          style={{
            flex: 1, background: 'transparent', border: 'none', outline: 'none', resize: 'none',
            color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 13.5, lineHeight: 1.55,
            placeholder: 'color: var(--color-sc-text-dim)',
            overflow: 'hidden', minHeight: 22,
          }}
        />
        <button
          onClick={isStreaming ? onAbort : onSend}
          disabled={!isStreaming && !value.trim()}
          style={{
            width: 30, height: 30, borderRadius: 8, border: 'none', flexShrink: 0, alignSelf: 'flex-end',
            background: isStreaming
              ? 'rgba(255,77,109,0.2)'
              : value.trim()
                ? 'rgba(196,164,74,0.2)'
                : 'rgba(255,255,255,0.04)',
            color: isStreaming ? 'var(--color-sc-danger)' : value.trim() ? 'var(--color-sc-gold)' : 'var(--color-sc-text-dim)',
            cursor: (!isStreaming && !value.trim()) ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'background 0.15s, color 0.15s',
          }}
          title={isStreaming ? 'Stop' : 'Send (Enter)'}
        >
          {isStreaming ? '■' : <Send size={13} />}
        </button>
      </div>
      <div style={{ fontSize: 10, color: 'var(--color-sc-text-dim)', marginTop: 5, textAlign: 'center' }}>
        Enter to send · Shift+Enter for newline · /goal · /hive · /search · /code
      </div>
    </div>
  );
}
