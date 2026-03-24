import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Brain, Terminal, RefreshCw, Pause, Play, Filter, ChevronDown,
  ChevronRight, Clock, Zap, AlertCircle, CheckCircle, Activity,
  Database, Cpu, Search, X, Download
} from 'lucide-react';

// ─── Log level detection ─────────────────────────────────────────────────────
function detectLevel(raw) {
  // Match explicit bracket tags first — prevents payload content (e.g. "spelling errors"
  // inside a DEBUG log) from triggering a false ERR classification.
  if (/\[(debug|dbg)\]/i.test(raw))             return 'debug';
  if (/\[warn(ing)?\]/i.test(raw))              return 'warn';
  if (/\[(error|err|fatal|panic)\]/i.test(raw)) return 'error';
  if (/\[(info|boot|main)\]/i.test(raw))        return 'info';

  // Fallback: scan only the first ~60 chars (the prefix) to avoid payload false positives.
  const prefix = raw.slice(0, 60).toLowerCase();
  if (/\bfatal\b|\bpanic\b/.test(prefix))            return 'error';
  if (/\bwarn\b/.test(prefix))                        return 'warn';
  if (/\bdebug\b/.test(prefix))                       return 'debug';
  if (/gateway|active|\[boot\]|\[main\]/.test(prefix)) return 'info';
  if (/\[gin\]|" 20[01]/.test(raw))                  return 'request';
  return 'log';
}

const LEVEL_STYLE = {
  error:   { color: '#FF4D6D', bg: 'rgba(255,77,109,0.08)',   label: 'ERR'  },
  warn:    { color: '#FF9900', bg: 'rgba(255,153,0,0.08)',     label: 'WARN' },
  info:    { color: '#00CCCC', bg: 'rgba(0,204,204,0.06)',     label: 'INFO' },
  request: { color: '#06D6A0', bg: 'rgba(6,214,160,0.06)',    label: 'REQ'  },
  debug:   { color: '#888',    bg: 'rgba(255,255,255,0.03)',   label: 'DBG'  },
  log:     { color: 'var(--color-sc-text-muted)', bg: 'transparent', label: 'LOG' },
};

const SOURCE_COLOR = {
  backbone: 'var(--color-sc-gold)',
  ui:       '#994CFF',
};

// ─── Timestamp extractor ─────────────────────────────────────────────────────
function extractTs(raw) {
  const m = raw.match(/(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2}:\d{2}|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})/);
  return m ? m[1] : null;
}

// ─── Raw Logs Tab ─────────────────────────────────────────────────────────────
function RawLogsTab() {
  const [lines, setLines]         = useState([]);
  const [paused, setPaused]       = useState(false);
  const [filter, setFilter]       = useState('');
  const [levelFilter, setLevel]   = useState('all');
  const [sourceFilter, setSource] = useState('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const bottomRef = useRef(null);
  const containerRef = useRef(null);

  const fetchLogs = useCallback(async () => {
    if (paused) return;
    try {
      const r = await fetch('/logs/raw?n=400');
      const d = await r.json();
      setLines((d.lines || []).map(l => ({ ...l, level: detectLevel(l.raw), ts: extractTs(l.raw) })));
    } catch {}
  }, [paused]);

  useEffect(() => {
    fetchLogs();
    const iv = setInterval(fetchLogs, 3000);
    return () => clearInterval(iv);
  }, [fetchLogs]);

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [lines, autoScroll]);

  const visible = lines.filter(l => {
    if (levelFilter !== 'all' && l.level !== levelFilter) return false;
    if (sourceFilter !== 'all' && l.source !== sourceFilter) return false;
    if (filter && !l.raw.toLowerCase().includes(filter.toLowerCase())) return false;
    return true;
  });

  function downloadLogs() {
    const text = visible.map(l => l.raw).join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = `oristudio-logs-${Date.now()}.txt`; a.click();
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Toolbar */}
      <div style={{ padding: '12px 24px', borderBottom: '1px solid var(--color-sc-border)', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search size={12} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-sc-text-dim)', pointerEvents: 'none' }} />
          <input value={filter} onChange={e => setFilter(e.target.value)} placeholder="Filter logs…"
            style={{ width: '100%', background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)', borderRadius: 8, padding: '7px 10px 7px 28px', color: 'var(--color-sc-text)', fontFamily: 'var(--font-mono)', fontSize: 12, outline: 'none', boxSizing: 'border-box' }} />
          {filter && <button onClick={() => setFilter('')} style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-dim)', padding: 0 }}><X size={11} /></button>}
        </div>

        {/* Level filter */}
        <select value={levelFilter} onChange={e => setLevel(e.target.value)}
          style={{ background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)', borderRadius: 8, padding: '7px 10px', color: 'var(--color-sc-text)', fontFamily: 'var(--font-grotesk)', fontSize: 12, cursor: 'pointer', outline: 'none' }}>
          <option value="all">All levels</option>
          {Object.keys(LEVEL_STYLE).map(lv => <option key={lv} value={lv}>{LEVEL_STYLE[lv].label}</option>)}
        </select>

        {/* Source filter */}
        <select value={sourceFilter} onChange={e => setSource(e.target.value)}
          style={{ background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)', borderRadius: 8, padding: '7px 10px', color: 'var(--color-sc-text)', fontFamily: 'var(--font-grotesk)', fontSize: 12, cursor: 'pointer', outline: 'none' }}>
          <option value="all">All sources</option>
          <option value="backbone">Backbone</option>
          <option value="ui">UI</option>
        </select>

        <button onClick={() => { setAutoScroll(a => !a); }} title={autoScroll ? 'Pause auto-scroll' : 'Resume auto-scroll'}
          style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: autoScroll ? 'rgba(196,164,74,0.1)' : 'var(--color-sc-bg)', color: autoScroll ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, fontFamily: 'var(--font-grotesk)' }}>
          {autoScroll ? <Pause size={11} /> : <Play size={11} />} {autoScroll ? 'Auto' : 'Manual'}
        </button>

        <button onClick={fetchLogs} style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'var(--color-sc-bg)', color: 'var(--color-sc-text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5, fontSize: 12 }}>
          <RefreshCw size={11} />
        </button>

        <button onClick={downloadLogs} style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'var(--color-sc-bg)', color: 'var(--color-sc-text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5, fontSize: 12 }}>
          <Download size={11} />
        </button>

        <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
          {visible.length} / {lines.length} lines
        </span>
      </div>

      {/* Log lines */}
      <div ref={containerRef} onScroll={e => {
        const el = e.currentTarget;
        const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
        if (!atBottom && autoScroll) setAutoScroll(false);
      }}
        style={{ flex: 1, overflowY: 'auto', padding: '8px 0', fontFamily: 'var(--font-mono)', fontSize: 12, background: 'var(--color-sc-bg)' }}>
        {visible.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--color-sc-text-dim)', fontSize: 13 }}>No logs match the current filter.</div>
        )}
        {visible.map((l, i) => {
          const st = LEVEL_STYLE[l.level] ?? LEVEL_STYLE.log;
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'baseline', gap: 8, padding: '2px 24px', borderLeft: `2px solid ${i === visible.length - 1 ? st.color : 'transparent'}`, background: i % 2 === 0 ? 'rgba(255,255,255,0.01)' : 'transparent', transition: 'background 0.1s' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(196,164,74,0.04)'}
              onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? 'rgba(255,255,255,0.01)' : 'transparent'}>
              <span style={{ color: SOURCE_COLOR[l.source] ?? 'var(--color-sc-text-dim)', fontSize: 10, fontWeight: 700, flexShrink: 0, width: 58 }}>{l.source?.toUpperCase()}</span>
              <span style={{ color: st.color, fontSize: 10, fontWeight: 700, flexShrink: 0, width: 34 }}>{st.label}</span>
              {l.ts && <span style={{ color: 'var(--color-sc-text-dim)', fontSize: 10, flexShrink: 0 }}>{l.ts}</span>}
              <span style={{ color: 'var(--color-sc-text)', lineHeight: 1.6, wordBreak: 'break-all', flex: 1 }}>
                {l.raw.replace(/^\S+\s+\S+\s+/, '')}
              </span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ─── Trace card ───────────────────────────────────────────────────────────────
function TraceCard({ trace }) {
  const [open, setOpen] = useState(false);
  const g = trace.trace_graph ?? {};
  const module    = g.module   || g.operation || g.type   || '—';
  const status    = g.status   || g.success === false ? 'error' : g.success === true ? 'done' : 'unknown';
  const latency   = g.latency_ms ?? g.duration_ms ?? null;
  const confidence= g.confidence ?? null;
  const output    = g.final_output || g.output || g.text || null;
  const thought   = g.thought  || g.reasoning || g.plan  || null;
  const nextMove  = g.next_action || g.next_step || g.next_move || null;
  const ts        = trace.timestamp ? new Date(trace.timestamp).toLocaleTimeString() : '—';

  const statusColor = status === 'error' ? '#FF4D6D' : status === 'done' ? '#06D6A0' : 'var(--color-sc-gold)';

  return (
    <div style={{ border: '1px solid var(--color-sc-border)', borderRadius: 12, overflow: 'hidden', marginBottom: 8 }}>
      {/* Header */}
      <button type="button" onClick={() => setOpen(o => !o)}
        style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', background: 'var(--color-sc-surface)', border: 'none', cursor: 'pointer', textAlign: 'left' }}>
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: statusColor, flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
            <span style={{ fontFamily: 'var(--font-grotesk)', fontSize: 13, fontWeight: 700, color: 'var(--color-sc-text)' }}>{module}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--color-sc-text-dim)', background: 'rgba(255,255,255,0.04)', padding: '1px 6px', borderRadius: 4 }}>{trace.trace_id?.slice(0, 8)}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', fontFamily: 'var(--font-mono)' }}>{ts}</span>
            {latency != null && <span style={{ fontSize: 11, color: latency > 2000 ? '#FF9900' : '#06D6A0', fontFamily: 'var(--font-mono)' }}>{latency.toFixed(0)}ms</span>}
            {confidence != null && <span style={{ fontSize: 11, color: confidence > 0.7 ? '#06D6A0' : confidence > 0.4 ? '#FF9900' : '#FF4D6D', fontFamily: 'var(--font-mono)' }}>conf {(confidence * 100).toFixed(0)}%</span>}
          </div>
        </div>
        {/* Thought preview */}
        {thought && !open && (
          <span style={{ fontSize: 11, color: 'var(--color-sc-text-muted)', fontFamily: 'var(--font-inter)', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flexShrink: 0 }}>
            💭 {thought}
          </span>
        )}
        {open ? <ChevronDown size={13} style={{ color: 'var(--color-sc-text-dim)', flexShrink: 0 }} /> : <ChevronRight size={13} style={{ color: 'var(--color-sc-text-dim)', flexShrink: 0 }} />}
      </button>

      {/* Expanded */}
      {open && (
        <div style={{ background: 'var(--color-sc-bg)', borderTop: '1px solid var(--color-sc-border)', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {thought && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-sc-gold)', marginBottom: 5, fontFamily: 'var(--font-grotesk)', display: 'flex', alignItems: 'center', gap: 5 }}>
                <Brain size={11} /> THOUGHT / REASONING
              </div>
              <div style={{ fontSize: 12, color: 'var(--color-sc-text)', lineHeight: 1.7, fontFamily: 'var(--font-inter)', background: 'rgba(196,164,74,0.05)', padding: '8px 12px', borderRadius: 8, borderLeft: '2px solid rgba(196,164,74,0.3)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {thought}
              </div>
            </div>
          )}
          {nextMove && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#00CCCC', marginBottom: 5, fontFamily: 'var(--font-grotesk)', display: 'flex', alignItems: 'center', gap: 5 }}>
                <Zap size={11} /> NEXT MOVE
              </div>
              <div style={{ fontSize: 12, color: 'var(--color-sc-text)', lineHeight: 1.7, fontFamily: 'var(--font-inter)', background: 'rgba(0,204,204,0.05)', padding: '8px 12px', borderRadius: 8, borderLeft: '2px solid rgba(0,204,204,0.3)' }}>
                {nextMove}
              </div>
            </div>
          )}
          {output && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#06D6A0', marginBottom: 5, fontFamily: 'var(--font-grotesk)', display: 'flex', alignItems: 'center', gap: 5 }}>
                <CheckCircle size={11} /> OUTPUT
              </div>
              <pre style={{ margin: 0, fontSize: 12, color: 'var(--color-sc-text)', lineHeight: 1.6, fontFamily: 'var(--font-mono)', background: 'rgba(6,214,160,0.04)', padding: '8px 12px', borderRadius: 8, whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 200, overflowY: 'auto' }}>
                {typeof output === 'string' ? output : JSON.stringify(output, null, 2)}
              </pre>
            </div>
          )}
          {/* Raw trace graph */}
          <details>
            <summary style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', cursor: 'pointer', fontFamily: 'var(--font-grotesk)', fontWeight: 600, userSelect: 'none' }}>Raw trace data</summary>
            <pre style={{ margin: '8px 0 0', fontSize: 11, color: 'var(--color-sc-text-dim)', fontFamily: 'var(--font-mono)', background: 'rgba(255,255,255,0.03)', padding: '8px 12px', borderRadius: 8, whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 300, overflowY: 'auto' }}>
              {JSON.stringify(trace, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}

// ─── Agent Traces Tab ─────────────────────────────────────────────────────────
function TracesTab() {
  const [traces, setTraces]   = useState([]);
  const [paused, setPaused]   = useState(false);
  const [filter, setFilter]   = useState('');
  const [error, setError]     = useState(null);
  const [lastFetch, setLastFetch] = useState(null);

  const fetchTraces = useCallback(async () => {
    if (paused) return;
    try {
      const r = await fetch('/logs/traces?limit=80');
      const d = await r.json();
      if (d.success !== false) {
        // Reverse so newest first
        setTraces((d.traces || []).slice().reverse());
        setError(null);
      } else {
        setError(d.error || 'Failed to fetch traces');
      }
      setLastFetch(new Date());
    } catch (e) {
      setError(String(e));
    }
  }, [paused]);

  useEffect(() => {
    fetchTraces();
    const iv = setInterval(fetchTraces, 4000);
    return () => clearInterval(iv);
  }, [fetchTraces]);

  const visible = traces.filter(t => {
    if (!filter) return true;
    const s = JSON.stringify(t).toLowerCase();
    return s.includes(filter.toLowerCase());
  });

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Toolbar */}
      <div style={{ padding: '12px 24px', borderBottom: '1px solid var(--color-sc-border)', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: 340 }}>
          <Search size={12} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-sc-text-dim)', pointerEvents: 'none' }} />
          <input value={filter} onChange={e => setFilter(e.target.value)} placeholder="Search traces…"
            style={{ width: '100%', background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border)', borderRadius: 8, padding: '7px 10px 7px 28px', color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', fontSize: 12, outline: 'none', boxSizing: 'border-box' }} />
        </div>
        <button onClick={() => setPaused(p => !p)}
          style={{ padding: '6px 12px', borderRadius: 8, border: `1px solid ${paused ? 'rgba(196,164,74,0.4)' : 'var(--color-sc-border)'}`, background: paused ? 'rgba(196,164,74,0.1)' : 'var(--color-sc-bg)', color: paused ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontFamily: 'var(--font-grotesk)' }}>
          {paused ? <><Play size={11} /> Paused</> : <><Pause size={11} /> Live</>}
        </button>
        <button onClick={fetchTraces} style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'var(--color-sc-bg)', color: 'var(--color-sc-text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5, fontSize: 12 }}>
          <RefreshCw size={11} />
        </button>
        <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)', fontFamily: 'var(--font-mono)', marginLeft: 'auto' }}>
          {visible.length} traces {lastFetch ? `· ${lastFetch.toLocaleTimeString()}` : ''}
        </span>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px' }}>
        {error && (
          <div style={{ color: 'var(--color-sc-danger)', fontSize: 13, marginBottom: 16, padding: '10px 14px', background: 'rgba(255,77,109,0.08)', borderRadius: 8, border: '1px solid rgba(255,77,109,0.2)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertCircle size={14} /> {error}
          </div>
        )}
        {!error && visible.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--color-sc-text-dim)' }}>
            <Brain size={36} style={{ opacity: 0.15, marginBottom: 12 }} />
            <div style={{ fontSize: 14, marginBottom: 6, color: 'var(--color-sc-text-muted)' }}>No traces yet</div>
            <div style={{ fontSize: 13 }}>Traces appear when the agent processes requests.</div>
          </div>
        )}
        {visible.map(t => <TraceCard key={t.trace_id} trace={t} />)}
      </div>
    </div>
  );
}

// ─── Main LogsPage ────────────────────────────────────────────────────────────
export function LogsPage() {
  const [tab, setTab] = useState('traces');

  const TAB = (id, label, Icon) => (
    <button key={id} onClick={() => setTab(id)}
      style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, border: `1px solid ${tab === id ? 'rgba(196,164,74,0.4)' : 'transparent'}`, background: tab === id ? 'rgba(196,164,74,0.1)' : 'transparent', color: tab === id ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 13, fontWeight: 600, fontFamily: 'var(--font-grotesk)', transition: 'all 0.15s' }}>
      <Icon size={13} /> {label}
    </button>
  );

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
      {/* Header */}
      <div style={{ padding: '20px 24px 0', borderBottom: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)', flexShrink: 0 }}>
        <div style={{ marginBottom: 14 }}>
          <h1 style={{ margin: '0 0 4px', fontFamily: 'var(--font-grotesk)', fontSize: 20, fontWeight: 700, color: 'var(--color-sc-text)' }}>Logs</h1>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--color-sc-text-muted)' }}>
            {tab === 'traces' ? 'Live agent execution traces — thoughts, decisions, and outputs.' : 'Raw backbone and UI service log output.'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 4, paddingBottom: 1 }}>
          {TAB('traces', 'Agent Traces', Brain)}
          {TAB('raw', 'Raw Logs', Terminal)}
        </div>
      </div>

      {tab === 'traces' ? <TracesTab /> : <RawLogsTab />}
    </div>
  );
}
