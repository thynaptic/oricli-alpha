import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  Search, Zap, Check, Globe, Copy, Download, Edit3, Eye,
  ChevronRight, AlertCircle, FileText, RotateCcw,
} from 'lucide-react';

// ─── Step tracker ────────────────────────────────────────────────────────────

function StepTracker({ steps }) {
  if (!steps.length) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: '8px 0' }}>
      {steps.map((step, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'flex-start', gap: 10, padding: '7px 10px',
          borderRadius: 8, transition: 'background 0.2s',
          background: step.status === 'active' ? 'rgba(196,164,74,0.07)' : 'transparent',
        }}>
          {/* Status dot */}
          <div style={{
            width: 18, height: 18, borderRadius: '50%', flexShrink: 0, marginTop: 1,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: step.status === 'done'   ? 'rgba(34,197,94,0.12)'
                       : step.status === 'active' ? 'rgba(196,164,74,0.15)'
                       : 'rgba(255,255,255,0.04)',
            border: `1px solid ${step.status === 'done'   ? 'rgba(34,197,94,0.35)'
                                : step.status === 'active' ? 'rgba(196,164,74,0.4)'
                                : 'rgba(255,255,255,0.08)'}`,
          }}>
            {step.status === 'done'   && <Check size={9} color="#22c55e" />}
            {step.status === 'active' && (
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-sc-gold)', animation: 'pulse 1s infinite', display: 'block' }} />
            )}
          </div>
          <span style={{
            fontSize: 12.5, lineHeight: 1.5,
            color: step.status === 'done'   ? 'var(--color-sc-text-muted)'
                 : step.status === 'active' ? 'var(--color-sc-text)'
                 : 'var(--color-sc-text-dim)',
          }}>
            {step.label}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Search results accordion ─────────────────────────────────────────────────

function SearchResultsPanel({ items }) {
  const [open, setOpen] = useState(false);
  if (!items.length) return null;
  return (
    <div style={{ marginTop: 8, border: '1px solid var(--color-sc-border)', borderRadius: 8, overflow: 'hidden' }}>
      <button onClick={() => setOpen(o => !o)} style={{
        width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 12px', border: 'none', background: 'var(--color-sc-surface2)', cursor: 'pointer',
        color: 'var(--color-sc-text-muted)', fontSize: 12,
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Globe size={11} /> {items.length} sources found
        </span>
        <ChevronRight size={12} style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s' }} />
      </button>
      {open && (
        <div style={{ maxHeight: 220, overflowY: 'auto' }}>
          {items.map((r, i) => (
            <a key={i} href={r.url} target="_blank" rel="noreferrer" style={{
              display: 'block', padding: '8px 12px', borderTop: '1px solid var(--color-sc-border)',
              textDecoration: 'none', color: 'inherit',
            }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.03)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--color-sc-text)', marginBottom: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.title}</div>
              <div style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{r.snippet}</div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Result canvas ────────────────────────────────────────────────────────────

const MD_COMPONENTS = {
  code({ node, inline, className, children, ...props }) {
    const lang = /language-(\w+)/.exec(className || '')?.[1];
    return !inline && lang ? (
      <SyntaxHighlighter language={lang} style={oneDark} PreTag="div" customStyle={{ borderRadius: 8, fontSize: 12.5 }} {...props}>
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    ) : (
      <code style={{ background: 'rgba(255,255,255,0.07)', padding: '1px 5px', borderRadius: 4, fontSize: '0.9em' }} {...props}>{children}</code>
    );
  },
  h1: ({ children }) => <h1 style={{ fontSize: 22, fontWeight: 700, margin: '24px 0 12px', color: 'var(--color-sc-text)', borderBottom: '1px solid var(--color-sc-border)', paddingBottom: 8 }}>{children}</h1>,
  h2: ({ children }) => <h2 style={{ fontSize: 17, fontWeight: 600, margin: '20px 0 8px', color: 'var(--color-sc-text)' }}>{children}</h2>,
  h3: ({ children }) => <h3 style={{ fontSize: 14, fontWeight: 600, margin: '16px 0 6px', color: 'var(--color-sc-text)' }}>{children}</h3>,
  p:  ({ children }) => <p style={{ margin: '0 0 12px', color: 'var(--color-sc-text-muted)', lineHeight: 1.75, fontSize: 14 }}>{children}</p>,
  li: ({ children }) => <li style={{ color: 'var(--color-sc-text-muted)', marginBottom: 4, fontSize: 14, lineHeight: 1.7 }}>{children}</li>,
  a:  ({ href, children }) => <a href={href} target="_blank" rel="noreferrer" style={{ color: 'var(--color-sc-gold)', textDecoration: 'none' }}>{children}</a>,
  blockquote: ({ children }) => <blockquote style={{ borderLeft: '3px solid rgba(196,164,74,0.4)', paddingLeft: 14, margin: '12px 0', color: 'var(--color-sc-text-dim)', fontStyle: 'italic' }}>{children}</blockquote>,
};

function ResultCanvas({ content, title, mode }) {
  const [viewMode, setViewMode]   = useState('preview');
  const [editText, setEditText]   = useState('');
  const [copied, setCopied]       = useState(false);
  const displayText = viewMode === 'edit' ? editText : content;

  useEffect(() => { setEditText(content); }, [content]);

  function copy() {
    navigator.clipboard.writeText(content).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); });
  }
  function download() {
    const blob = new Blob([content], { type: 'text/markdown' });
    const a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = `${title || 'research'}.md`;
    a.click();
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
      {/* Toolbar */}
      <div style={{ height: 46, flexShrink: 0, display: 'flex', alignItems: 'center', padding: '0 16px', gap: 8, borderBottom: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)' }}>
        <FileText size={13} style={{ color: 'var(--color-sc-gold)' }} />
        <span style={{ flex: 1, fontSize: 13, fontWeight: 500, color: 'var(--color-sc-text)', fontFamily: 'var(--font-grotesk)' }}>{title || 'Research Report'}</span>
        <span style={{ fontSize: 10, padding: '2px 7px', borderRadius: 8, background: 'rgba(196,164,74,0.1)', color: 'var(--color-sc-gold)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {mode === 'deep' ? 'Deep Research' : 'Research'}
        </span>
        <button onClick={() => setViewMode('preview')} style={{ padding: '5px 9px', borderRadius: 6, border: 'none', cursor: 'pointer', background: viewMode === 'preview' ? 'rgba(196,164,74,0.15)' : 'transparent', color: viewMode === 'preview' ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', display: 'flex', gap: 4, alignItems: 'center', fontSize: 11 }}>
          <Eye size={12} /> Preview
        </button>
        <button onClick={() => setViewMode('edit')} style={{ padding: '5px 9px', borderRadius: 6, border: 'none', cursor: 'pointer', background: viewMode === 'edit' ? 'rgba(196,164,74,0.15)' : 'transparent', color: viewMode === 'edit' ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', display: 'flex', gap: 4, alignItems: 'center', fontSize: 11 }}>
          <Edit3 size={12} /> Edit
        </button>
        <div style={{ width: 1, background: 'var(--color-sc-border)', height: 20 }} />
        <button onClick={copy} title="Copy" style={{ padding: '5px 8px', borderRadius: 6, border: 'none', cursor: 'pointer', background: 'transparent', color: copied ? 'var(--color-sc-success)' : 'var(--color-sc-text-muted)', display: 'flex' }}>
          {copied ? <Check size={13} /> : <Copy size={13} />}
        </button>
        <button onClick={download} title="Download .md" style={{ padding: '5px 8px', borderRadius: 6, border: 'none', cursor: 'pointer', background: 'transparent', color: 'var(--color-sc-text-muted)', display: 'flex' }}>
          <Download size={13} />
        </button>
      </div>

      {/* Content */}
      {viewMode === 'preview' ? (
        <div style={{ flex: 1, overflowY: 'auto', padding: '28px 36px' }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
            {displayText}
          </ReactMarkdown>
        </div>
      ) : (
        <textarea
          value={editText}
          onChange={e => setEditText(e.target.value)}
          spellCheck={false}
          style={{
            flex: 1, resize: 'none', border: 'none', outline: 'none',
            background: 'var(--color-sc-bg)', color: 'var(--color-sc-text)',
            fontFamily: 'var(--font-mono)', fontSize: 13, lineHeight: 1.7,
            padding: '24px 32px', boxSizing: 'border-box',
          }}
        />
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function ResearchPage() {
  const [topic,    setTopic]    = useState('');
  const [mode,     setMode]     = useState('normal');  // 'normal' | 'deep'
  const [steps,    setSteps]    = useState([]);
  const [sources,  setSources]  = useState([]);        // flat list of all search results
  const [result,   setResult]   = useState('');
  const [title,    setTitle]    = useState('');
  const [running,  setRunning]  = useState(false);
  const [error,    setError]    = useState('');
  const abortRef = useRef(null);

  function startResearch() {
    if (!topic.trim() || running) return;
    setSteps([]);
    setSources([]);
    setResult('');
    setTitle('');
    setError('');
    setRunning(true);

    const controller = new AbortController();
    abortRef.current = controller;

    (async () => {
      try {
        const res = await fetch('/research/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ topic, mode }),
          signal: controller.signal,
        });
        const reader  = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          for (const line of chunk.split('\n')) {
            if (!line.startsWith('data:')) continue;
            const raw = line.slice(5).trim();
            if (raw === '[DONE]') break;
            let evt;
            try { evt = JSON.parse(raw); } catch { continue; }

            if (evt.type === 'step') {
              setSteps(prev => {
                const next = [...prev];
                // if new step, expand total
                while (next.length <= evt.index) next.push({ label: '', status: 'pending' });
                next[evt.index] = { label: evt.label, status: 'active' };
                return next;
              });
            } else if (evt.type === 'step_done') {
              setSteps(prev => prev.map((s, i) => i === evt.index ? { ...s, status: 'done' } : s));
            } else if (evt.type === 'plan') {
              // Pre-populate pending steps from plan
              setSteps(prev => {
                const base = prev.filter(s => s.status !== 'pending');
                const pending = evt.questions.map(q => ({ label: `Search: ${q.slice(0, 60)}`, status: 'pending' }));
                return [...base, ...pending, { label: 'Synthesize comprehensive report', status: 'pending' }];
              });
            } else if (evt.type === 'search_result') {
              setSources(prev => [...prev, ...evt.results]);
            } else if (evt.type === 'content') {
              setResult(evt.text);
              setTitle(evt.title);
            } else if (evt.type === 'error') {
              setError(evt.message);
            }
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') setError(String(err));
      } finally {
        setRunning(false);
        abortRef.current = null;
      }
    })();
  }

  function stop() { abortRef.current?.abort(); setRunning(false); }

  const hasResult = result.length > 0;

  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>

      {/* ── Left panel ── */}
      <div style={{ width: 340, flexShrink: 0, display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)', overflow: 'hidden' }}>

        {/* Header */}
        <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--color-sc-border)' }}>
          <div style={{ fontSize: 17, fontWeight: 700, color: 'var(--color-sc-text)', fontFamily: 'var(--font-grotesk)', marginBottom: 4 }}>Research</div>
          <div style={{ fontSize: 12, color: 'var(--color-sc-text-dim)' }}>Sovereign web-grounded intelligence</div>
        </div>

        {/* Input area */}
        <div style={{ padding: '16px 16px 12px' }}>
          <textarea
            value={topic}
            onChange={e => setTopic(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !running) { e.preventDefault(); startResearch(); } }}
            placeholder="What do you want to research?"
            rows={3}
            style={{
              width: '100%', resize: 'none', border: '1px solid var(--color-sc-border2)', outline: 'none',
              borderRadius: 10, background: 'var(--color-sc-surface2)', color: 'var(--color-sc-text)',
              fontFamily: 'var(--font-inter)', fontSize: 13, lineHeight: 1.55, padding: '10px 12px',
              boxSizing: 'border-box', transition: 'border-color 0.15s',
            }}
            onFocus={e => e.target.style.borderColor = 'rgba(196,164,74,0.4)'}
            onBlur={e => e.target.style.borderColor = 'var(--color-sc-border2)'}
          />

          {/* Mode selector */}
          <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
            {[
              { id: 'normal', label: 'Research',      Icon: Search, desc: '2 steps · ~1 min' },
              { id: 'deep',   label: 'Deep Research',  Icon: Zap,    desc: '5 steps · ~3 min' },
            ].map(({ id, label, Icon, desc }) => (
              <button key={id} onClick={() => setMode(id)} style={{
                flex: 1, padding: '9px 8px', borderRadius: 8, cursor: 'pointer',
                border: `1px solid ${mode === id ? 'rgba(196,164,74,0.5)' : 'var(--color-sc-border)'}`,
                background: mode === id ? 'rgba(196,164,74,0.1)' : 'var(--color-sc-surface2)',
                color: mode === id ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, transition: 'all 0.15s',
              }}>
                <Icon size={14} />
                <span style={{ fontSize: 11.5, fontWeight: mode === id ? 600 : 400, fontFamily: 'var(--font-grotesk)' }}>{label}</span>
                <span style={{ fontSize: 10, color: 'var(--color-sc-text-dim)' }}>{desc}</span>
              </button>
            ))}
          </div>

          {/* Action button */}
          <button
            onClick={running ? stop : startResearch}
            disabled={!running && !topic.trim()}
            style={{
              width: '100%', marginTop: 10, padding: '10px', borderRadius: 10, border: 'none',
              cursor: (!running && !topic.trim()) ? 'not-allowed' : 'pointer',
              background: running ? 'rgba(255,77,109,0.15)' : 'var(--color-sc-gold)',
              color: running ? '#FF4D6D' : '#0D0D0D',
              fontFamily: 'var(--font-grotesk)', fontWeight: 600, fontSize: 13,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
              opacity: (!running && !topic.trim()) ? 0.5 : 1, transition: 'all 0.15s',
            }}
          >
            {running ? (
              <><span style={{ width: 7, height: 7, borderRadius: '50%', background: '#FF4D6D', animation: 'pulse 1s infinite', display: 'block' }} /> Stop</>
            ) : (
              <><Search size={14} /> {mode === 'deep' ? 'Deep Research' : 'Research'}</>
            )}
          </button>
        </div>

        {/* Steps + sources */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 12px 16px' }}>
          {steps.length > 0 && (
            <>
              <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-sc-text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', padding: '8px 8px 4px' }}>Progress</div>
              <StepTracker steps={steps} />
            </>
          )}

          {sources.length > 0 && (
            <div style={{ marginTop: 4 }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-sc-text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', padding: '8px 8px 4px' }}>Sources</div>
              <SearchResultsPanel items={sources} />
            </div>
          )}

          {error && (
            <div style={{ margin: '12px 0', padding: '10px 12px', borderRadius: 8, background: 'rgba(255,77,109,0.07)', border: '1px solid rgba(255,77,109,0.2)', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
              <AlertCircle size={13} color="#FF4D6D" style={{ flexShrink: 0, marginTop: 1 }} />
              <span style={{ fontSize: 12, color: '#FF4D6D', lineHeight: 1.5 }}>{error}</span>
            </div>
          )}
        </div>

        {/* Re-run hint if done */}
        {!running && hasResult && (
          <div style={{ padding: '10px 16px', borderTop: '1px solid var(--color-sc-border)' }}>
            <button onClick={startResearch} style={{ width: '100%', padding: '8px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'transparent', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              <RotateCcw size={12} /> Re-run research
            </button>
          </div>
        )}
      </div>

      {/* ── Right canvas ── */}
      {hasResult ? (
        <ResultCanvas content={result} title={title} mode={mode} />
      ) : (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 16, color: 'var(--color-sc-text-dim)' }}>
          {running ? (
            <>
              <div style={{ width: 48, height: 48, borderRadius: '50%', border: '2px solid rgba(196,164,74,0.15)', borderTopColor: 'var(--color-sc-gold)', animation: 'spin 1s linear infinite' }} />
              <div style={{ fontSize: 14, color: 'var(--color-sc-text-muted)' }}>Researching…</div>
              <div style={{ fontSize: 12 }}>Results will appear here when ready</div>
            </>
          ) : (
            <>
              <Search size={40} style={{ opacity: 0.1 }} />
              <div style={{ fontSize: 15, color: 'var(--color-sc-text-muted)' }}>No research yet</div>
              <div style={{ fontSize: 13, maxWidth: 340, textAlign: 'center', lineHeight: 1.7 }}>
                Enter a topic and choose <strong style={{ color: 'var(--color-sc-text)' }}>Research</strong> for a quick synthesis or{' '}
                <strong style={{ color: 'var(--color-sc-gold)' }}>Deep Research</strong> for a multi-source comprehensive report.
              </div>
            </>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
