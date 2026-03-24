import React, { useState, useEffect, useRef } from 'react';
import { useSCStore } from '../store';
import {
  Code2, RefreshCw, Save, Play, Download, FileCode, Check, Loader,
  AlertCircle, AlertTriangle, Info, Trash2, ChevronDown, Zap, Copy,
} from 'lucide-react';

// ─── Starter template ────────────────────────────────────────────────────────
const STARTER_TEMPLATE = `# ORI Workflow  ·  edit below
# Tip: use {{variables}} for dynamic values, {{date}} for today's date

workflow "My Workflow" {
  description: "Describe what this workflow does"
  # agent: @agent-id        # optional — assign a specific agent

  # ── Runtime variables (prompted before each run) ─────────────────────────
  var topic

  # ── Steps ─────────────────────────────────────────────────────────────────
  step[research]: web "{{topic}} overview {{date}}"
  step[brief]:    summarize "Summarise the above in 3 bullet points"
  step[report]:   template "# {{topic}} Report\\n\\n{{output}}\\n\\nGenerated {{datetime}}"

  # ── Conditional (optional) ────────────────────────────────────────────────
  # if "output contains risk" {
  #   step: notify "slack: Risk detected — {{output}}"
  # }

  # ── Output ────────────────────────────────────────────────────────────────
  # output → canvas    # uncomment to push final output to Canvas
}
`;

// ─── Syntax highlight ─────────────────────────────────────────────────────────
function highlight(code) {
  return code
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // comments first (whole line)
    .replace(/(#[^\n]*)/g, '<span class="ori-comment">$1</span>')
    // keywords (not inside already-spanned comments)
    .replace(/\b(workflow|var|if|else|run|output|step|parallel|for|collect|with)\b(?![^<]*<\/span>)/g,
      '<span class="ori-kw">$1</span>')
    // meta keys
    .replace(/\b(description|agent|sendToCanvas)\b(?=\s*:)(?![^<]*<\/span>)/g,
      '<span class="ori-meta">$1</span>')
    // arrows
    .replace(/(→|->)/g, '<span class="ori-arrow">$1</span>')
    // @references
    .replace(/@([\w-]+)/g, '<span class="ori-ref">@$1</span>')
    // {{variables}}
    .replace(/\{\{([^}]+)\}\}/g, '<span class="ori-var">{{$1}}</span>')
    // step type keywords after colon
    .replace(/:\s*(prompt|summarize|transform|extract|web|code|template|notify|search|rag|ingest|fetch)\b/g,
      (full, t) => full.replace(t, `<span class="ori-type">${t}</span>`))
    // step labels [label]
    .replace(/\[([^\]]+)\]/g, '<span class="ori-label">[$1]</span>')
    // quoted strings (not inside comment spans)
    .replace(/"((?:[^"\\]|\\.)*)"/g, '<span class="ori-string">"$1"</span>')
    // backtick multiline
    .replace(/`([^`]*)`/gs, '<span class="ori-string">`$1`</span>');
}

// ─── Highlight stylesheet injected once ───────────────────────────────────────
const ORI_CSS = `
.ori-kw      { color: #c792ea; font-weight: 600; }
.ori-meta    { color: #82aaff; }
.ori-arrow   { color: #89ddff; font-weight: 700; }
.ori-ref     { color: #ffcb6b; }
.ori-var     { color: #f78c6c; }
.ori-type    { color: #80cbc4; font-weight: 600; }
.ori-label   { color: #c3e88d; }
.ori-string  { color: #c3e88d; }
.ori-comment { color: #546e7a; font-style: italic; }
`;

function injectOriCSS() {
  if (document.getElementById('ori-highlight-css')) return;
  const s = document.createElement('style');
  s.id = 'ori-highlight-css';
  s.textContent = ORI_CSS;
  document.head.appendChild(s);
}

// ─── Editor component (textarea + highlight overlay) ─────────────────────────
function OriEditor({ value, onChange }) {
  const taRef  = useRef(null);
  const preRef = useRef(null);

  useEffect(() => { injectOriCSS(); }, []);

  function syncScroll() {
    if (preRef.current && taRef.current) {
      preRef.current.scrollTop  = taRef.current.scrollTop;
      preRef.current.scrollLeft = taRef.current.scrollLeft;
    }
  }

  const baseStyle = {
    position: 'absolute', inset: 0, margin: 0, padding: '14px 18px',
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Courier New', monospace",
    fontSize: 13, lineHeight: 1.65,
    whiteSpace: 'pre-wrap', wordWrap: 'break-word', overflowWrap: 'break-word',
    tabSize: 2,
  };

  return (
    <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
      {/* Highlight layer (behind) */}
      <pre
        ref={preRef}
        aria-hidden="true"
        style={{
          ...baseStyle,
          color: 'transparent',
          pointerEvents: 'none',
          overflow: 'hidden',
          background: '#0d1117',
          zIndex: 0,
        }}
        dangerouslySetInnerHTML={{ __html: highlight(value) + '\n' }}
      />
      {/* Editable layer (on top, transparent) */}
      <textarea
        ref={taRef}
        value={value}
        onChange={e => onChange(e.target.value)}
        onScroll={syncScroll}
        spellCheck={false}
        autoComplete="off"
        autoCorrect="off"
        style={{
          ...baseStyle,
          color: 'transparent',
          caretColor: '#e1e4e8',
          background: 'transparent',
          border: 'none',
          outline: 'none',
          resize: 'none',
          overflowY: 'auto',
          zIndex: 1,
        }}
      />
    </div>
  );
}

// ─── Diagnostics panel ────────────────────────────────────────────────────────
function DiagnosticsPanel({ diagnostics, compiled, vars }) {
  const errors   = diagnostics.filter(d => d.level === 'error');
  const warnings = diagnostics.filter(d => d.level === 'warning');
  const infos    = diagnostics.filter(d => d.level === 'info');

  const chipStyle = (bg, fg = '#fff') => ({
    display: 'inline-flex', alignItems: 'center', gap: 4,
    background: bg, color: fg, borderRadius: 4, padding: '2px 8px',
    fontSize: 11, fontWeight: 700, fontFamily: "var(--font-grotesk, sans-serif)",
  });

  return (
    <div style={{
      padding: '14px 16px',
      borderBottom: '1px solid rgba(255,255,255,0.07)',
      overflowY: 'auto',
      maxHeight: 280,
      background: '#0d1117',
    }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#546e7a', marginBottom: 10 }}>
        Compiler Output
      </div>

      {/* Summary chips */}
      {compiled && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
          <span style={chipStyle('rgba(100,221,23,0.15)', '#64dd17')}>
            ✓ {compiled.steps?.length ?? 0} steps
          </span>
          {vars?.length > 0 && (
            <span style={chipStyle('rgba(247,140,108,0.15)', '#f78c6c')}>
              ⬡ {vars.length} var{vars.length !== 1 ? 's' : ''}
            </span>
          )}
          {compiled.sendToCanvas && (
            <span style={chipStyle('rgba(130,170,255,0.15)', '#82aaff')}>
              → canvas
            </span>
          )}
          {errors.length === 0 && warnings.length === 0 && (
            <span style={chipStyle('rgba(100,221,23,0.08)', '#546e7a')}>
              No issues
            </span>
          )}
        </div>
      )}

      {!compiled && diagnostics.length === 0 && (
        <div style={{ color: '#546e7a', fontSize: 12, fontFamily: 'monospace' }}>
          Write or load a workflow above — auto-compile is on.
        </div>
      )}

      {diagnostics.map((d, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 5, fontSize: 12 }}>
          {d.level === 'error'
            ? <AlertCircle size={13} style={{ color: '#ef5350', flexShrink: 0, marginTop: 1 }} />
            : d.level === 'warning'
            ? <AlertTriangle size={13} style={{ color: '#ffb74d', flexShrink: 0, marginTop: 1 }} />
            : <Info size={13} style={{ color: '#a89cf7', flexShrink: 0, marginTop: 1 }} />}
          <span style={{
            color: d.level === 'error' ? '#ef5350' : d.level === 'warning' ? '#ffb74d' : '#78909c',
            fontFamily: 'monospace', lineHeight: 1.5,
          }}>{d.message}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Run log panel ────────────────────────────────────────────────────────────
function RunLog({ entries, onClear }) {
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [entries]);

  if (!entries.length) return null;

  const color = t => t === 'error' ? '#ef5350' : t === 'success' ? '#64dd17' : t === 'output' ? '#e1e4e8' : '#546e7a';

  return (
    <div style={{
      flex: 1, overflowY: 'auto', padding: '12px 16px', background: '#0a0e13',
      borderTop: '1px solid rgba(255,255,255,0.07)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#546e7a' }}>Run Log</span>
        <button onClick={onClear} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#546e7a', padding: '2px 6px' }}>
          <Trash2 size={11} />
        </button>
      </div>
      {entries.map((l, i) => (
        <div key={i} style={{
          color: color(l.type), fontFamily: 'monospace', fontSize: 11, lineHeight: 1.6,
          marginBottom: 3, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        }}>
          {l.type === 'output' ? `\n─── Output ───\n${l.text}\n──────────────` : l.text}
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}

// ─── Button styles ────────────────────────────────────────────────────────────
const btnBase = {
  display: 'inline-flex', alignItems: 'center', gap: 5,
  border: 'none', borderRadius: 7, padding: '6px 12px', cursor: 'pointer',
  fontSize: 12, fontWeight: 600, fontFamily: "var(--font-grotesk, sans-serif)",
  transition: 'opacity 0.15s',
  whiteSpace: 'nowrap',
};
const ghostBtn = { ...btnBase, background: 'rgba(255,255,255,0.06)', color: '#90a4ae' };
const goldBtn  = { ...btnBase, background: 'rgba(168,156,247,0.18)', color: '#a89cf7' };
const greenBtn = { ...btnBase, background: 'rgba(100,221,23,0.15)',  color: '#64dd17' };
const dimBtn   = { ...btnBase, background: 'rgba(255,255,255,0.03)', color: '#374151', cursor: 'not-allowed' };

// ─── Main page ────────────────────────────────────────────────────────────────
export default function OriStudioPage() {
  const [source,      setSource]      = useState(STARTER_TEMPLATE);
  const [diagnostics, setDiagnostics] = useState([]);
  const [compiled,    setCompiled]    = useState(null);
  const [vars,        setVars]        = useState([]);
  const [compiling,   setCompiling]   = useState(false);
  const [saving,      setSaving]      = useState(false);
  const [saved,       setSaved]       = useState(false);
  const [runLog,      setRunLog]      = useState([]);
  const [running,     setRunning]     = useState(false);
  const [workflows,   setWorkflows]   = useState([]);
  const [autoCompile, setAutoCompile] = useState(true);
  const [loadOpen,    setLoadOpen]    = useState(false);
  const debounceRef  = useRef(null);
  const pollRef      = useRef(null);

  // Load workflow list for decompile dropdown
  useEffect(() => {
    fetch('/workflows')
      .then(r => r.json())
      .then(d => setWorkflows(d.workflows || []))
      .catch(() => {});
  }, []);

  // Auto-compile debounce
  useEffect(() => {
    if (!autoCompile) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(compile, 800);
    return () => clearTimeout(debounceRef.current);
  }, [source, autoCompile]);

  // Cleanup poll on unmount
  useEffect(() => () => clearInterval(pollRef.current), []);

  async function compile() {
    setCompiling(true);
    try {
      const r = await fetch('/ori/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source }),
      });
      const d = await r.json();
      setDiagnostics(d.diagnostics || []);
      setCompiled(d.ok ? d.workflow : null);
      setVars(d.vars || []);
    } catch {
      setDiagnostics([{ level: 'error', message: 'Network error — is the server running?' }]);
      setCompiled(null);
    }
    setCompiling(false);
  }

  async function decompile(wfId) {
    setLoadOpen(false);
    try {
      const r = await fetch(`/ori/decompile/${wfId}`);
      const d = await r.json();
      if (d.source) {
        setSource(d.source);
        setDiagnostics([{ level: 'info', message: `Loaded from workflow "${d.wf_id}"` }]);
      }
    } catch {
      setDiagnostics([{ level: 'error', message: 'Failed to decompile workflow' }]);
    }
  }

  async function saveWorkflow() {
    if (!compiled || saving) return;
    setSaving(true);
    try {
      // Check if this workflow already exists
      const listR = await fetch('/workflows');
      const listD = await listR.json();
      const existing = (listD.workflows || []).find(w => w.id === compiled.id);
      const method = existing ? 'PUT' : 'POST';
      const url    = existing ? `/workflows/${compiled.id}` : '/workflows';
      await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(compiled),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
      setWorkflows(prev => {
        const next = prev.filter(w => w.id !== compiled.id);
        return [...next, compiled];
      });
    } catch {
      setDiagnostics(prev => [...prev, { level: 'error', message: 'Save failed' }]);
    }
    setSaving(false);
  }

  async function runWorkflow() {
    if (!compiled || running) return;
    clearInterval(pollRef.current);
    setRunning(true);
    setRunLog([{ type: 'info', text: '▶ Saving workflow…' }]);

    try {
      // Save first
      const listR = await fetch('/workflows');
      const listD = await listR.json();
      const existing = (listD.workflows || []).find(w => w.id === compiled.id);
      const method = existing ? 'PUT' : 'POST';
      const url    = existing ? `/workflows/${compiled.id}` : '/workflows';
      const sr = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(compiled),
      });
      const sd = await sr.json();
      const wfId = sd.workflow?.id || compiled.id;

      setRunLog(prev => [...prev, { type: 'info', text: `▶ Starting run for "${compiled.name}"…` }]);

      // Prompt for vars if any
      let user_vars = {};
      if (vars.length > 0) {
        for (const v of vars) {
          const val = window.prompt(`Value for "{{${v}}}":`);
          if (val !== null) user_vars[v] = val;
        }
      }

      const rr = await fetch(`/workflows/${wfId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_vars }),
      });
      const rd = await rr.json();
      const runId = rd.run_id;
      if (!runId) throw new Error(rd.error || 'No run_id returned');

      setRunLog(prev => [...prev, { type: 'info', text: `  run_id: ${runId}` }]);

      // Poll for completion
      pollRef.current = setInterval(async () => {
        try {
          const pr = await fetch(`/workflows/runs/${runId}`);
          const pd = await pr.json();
          const status = pd.status;

          setRunLog(prev => {
            const filtered = prev.filter(l => !l.isStatus);
            return [...filtered, {
              type: status === 'error' ? 'error' : status === 'done' ? 'success' : 'info',
              text: `  status: ${status}`,
              isStatus: true,
            }];
          });

          if (['done', 'error', 'cancelled'].includes(status)) {
            clearInterval(pollRef.current);
            setRunning(false);
            if (pd.final_output) {
              setRunLog(prev => [...prev, { type: 'output', text: String(pd.final_output) }]);
            }
          }
        } catch {
          clearInterval(pollRef.current);
          setRunning(false);
        }
      }, 1500);

    } catch (err) {
      setRunLog(prev => [...prev, { type: 'error', text: `✗ ${err.message}` }]);
      setRunning(false);
    }
  }

  function newWorkflow() {
    if (source !== STARTER_TEMPLATE &&
        !window.confirm('Discard current source and start fresh?')) return;
    setSource(STARTER_TEMPLATE);
    setDiagnostics([]);
    setCompiled(null);
    setVars([]);
    setRunLog([]);
  }

  function exportOri() {
    const name = compiled?.name || 'workflow';
    const blob = new Blob([source], { type: 'text/plain' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `${name.toLowerCase().replace(/\s+/g, '_')}.ori`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const errorCount = diagnostics.filter(d => d.level === 'error').length;
  const warnCount  = diagnostics.filter(d => d.level === 'warning').length;

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden',
      background: '#0d1117', color: '#e1e4e8',
    }}>
      {/* ── Toolbar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.07)', flexShrink: 0,
        background: '#0a0e13',
      }}>
        <Code2 size={15} style={{ color: '#a89cf7' }} />
        <span style={{ fontFamily: "var(--font-grotesk, sans-serif)", fontWeight: 800, fontSize: 13, color: '#e1e4e8', letterSpacing: '0.02em' }}>
          ORI Studio
        </span>
        <span style={{ fontSize: 10, color: '#546e7a', fontFamily: 'monospace', paddingTop: 1 }}>
          .ori workflow compiler
        </span>

        <div style={{ flex: 1 }} />

        {/* Status indicator */}
        {compiling && (
          <span style={{ color: '#546e7a', fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
            <Loader size={11} style={{ animation: 'spin 1s linear infinite' }} /> compiling…
          </span>
        )}
        {!compiling && errorCount > 0 && (
          <span style={{ color: '#ef5350', fontSize: 11, display: 'flex', alignItems: 'center', gap: 3 }}>
            <AlertCircle size={11} /> {errorCount} error{errorCount > 1 ? 's' : ''}
          </span>
        )}
        {!compiling && errorCount === 0 && warnCount > 0 && (
          <span style={{ color: '#ffb74d', fontSize: 11, display: 'flex', alignItems: 'center', gap: 3 }}>
            <AlertTriangle size={11} /> {warnCount} warning{warnCount > 1 ? 's' : ''}
          </span>
        )}
        {!compiling && errorCount === 0 && warnCount === 0 && compiled && (
          <span style={{ color: '#64dd17', fontSize: 11, display: 'flex', alignItems: 'center', gap: 3 }}>
            <Zap size={11} /> ready
          </span>
        )}

        <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.07)', margin: '0 4px' }} />

        {/* Load dropdown */}
        <div style={{ position: 'relative' }}>
          <button onClick={() => setLoadOpen(o => !o)} style={ghostBtn}>
            <FileCode size={12} /> Load <ChevronDown size={11} style={{ marginLeft: 2 }} />
          </button>
          {loadOpen && (
            <div style={{
              position: 'absolute', top: '100%', right: 0, marginTop: 4,
              background: '#161b22', border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 9, minWidth: 210, zIndex: 100, boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
              overflow: 'hidden',
            }}>
              {workflows.length === 0
                ? <div style={{ padding: '12px 14px', color: '#546e7a', fontSize: 12 }}>No saved workflows</div>
                : workflows.map(w => (
                  <button key={w.id} onClick={() => decompile(w.id)} style={{
                    display: 'block', width: '100%', textAlign: 'left', padding: '9px 14px',
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: '#90a4ae', fontSize: 12, fontFamily: "var(--font-inter, sans-serif)",
                    transition: 'background 0.1s',
                  }}
                    onMouseEnter={e => e.target.style.background = 'rgba(255,255,255,0.05)'}
                    onMouseLeave={e => e.target.style.background = 'none'}
                  >
                    {w.agentEmoji || '⚙️'} {w.name}
                  </button>
                ))}
            </div>
          )}
        </div>

        <button onClick={newWorkflow} style={ghostBtn}>
          <Trash2 size={12} /> New
        </button>

        <button onClick={compile} disabled={compiling} style={ghostBtn}>
          <RefreshCw size={12} style={compiling ? { animation: 'spin 1s linear infinite' } : {}} />
          Compile
        </button>

        <button onClick={saveWorkflow} disabled={!compiled || saving} style={compiled ? goldBtn : dimBtn}>
          {saved
            ? <><Check size={12} /> Saved!</>
            : saving
            ? <><Loader size={12} style={{ animation: 'spin 1s linear infinite' }} /> Saving…</>
            : <><Save size={12} /> Save</>}
        </button>

        <button onClick={runWorkflow} disabled={!compiled || running} style={compiled ? greenBtn : dimBtn}>
          {running
            ? <><Loader size={12} style={{ animation: 'spin 1s linear infinite' }} /> Running…</>
            : <><Play size={12} /> Run</>}
        </button>

        <button onClick={exportOri} style={ghostBtn} title="Export as .ori file">
          <Download size={12} /> .ori
        </button>
      </div>

      {/* ── Main split ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* ── Left: editor ── */}
        <div style={{
          flex: '0 0 56%', display: 'flex', flexDirection: 'column',
          borderRight: '1px solid rgba(255,255,255,0.07)',
        }}>
          {/* Editor header bar */}
          <div style={{
            padding: '6px 14px', borderBottom: '1px solid rgba(255,255,255,0.05)',
            display: 'flex', alignItems: 'center', gap: 8, background: '#0a0e13',
            fontSize: 11, color: '#546e7a', flexShrink: 0,
          }}>
            <span style={{ fontFamily: 'monospace' }}>workflow.ori</span>
            <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer', userSelect: 'none' }}>
                <input
                  type="checkbox"
                  checked={autoCompile}
                  onChange={e => setAutoCompile(e.target.checked)}
                  style={{ accentColor: '#a89cf7', width: 11, height: 11 }}
                />
                auto-compile
              </label>
            </span>
          </div>
          <OriEditor value={source} onChange={setSource} />
        </div>

        {/* ── Right: diagnostics + log ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <DiagnosticsPanel diagnostics={diagnostics} compiled={compiled} vars={vars} />

          {/* Variable list */}
          {vars.length > 0 && (
            <div style={{
              padding: '10px 16px', borderBottom: '1px solid rgba(255,255,255,0.07)',
              background: '#0d1117',
            }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#546e7a', marginBottom: 7 }}>
                Runtime Variables
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {vars.map(v => (
                  <span key={v} style={{
                    background: 'rgba(247,140,108,0.1)', color: '#f78c6c',
                    borderRadius: 5, padding: '2px 8px', fontSize: 11, fontFamily: 'monospace',
                    cursor: 'pointer', border: '1px solid rgba(247,140,108,0.2)',
                  }}
                    title="Click to copy"
                    onClick={() => navigator.clipboard?.writeText(`{{${v}}}`)}
                  >
                    {'{{'}{v}{'}}'}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Quick-ref syntax card */}
          {!runLog.length && (
            <div style={{
              flex: 1, overflowY: 'auto', padding: '14px 16px', background: '#0d1117',
            }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#546e7a', marginBottom: 12 }}>
                ORI Syntax Reference
              </div>
              <SyntaxRef />
            </div>
          )}

          <RunLog entries={runLog} onClear={() => setRunLog([])} />
        </div>
      </div>
    </div>
  );
}

// ─── Syntax reference panel ───────────────────────────────────────────────────
function SyntaxRef() {
  const block = (label, code) => (
    <div key={label} style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 10, color: '#546e7a', fontFamily: "var(--font-grotesk, sans-serif)", fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 4 }}>
        {label}
      </div>
      <pre style={{
        margin: 0, padding: '8px 12px', background: '#0a0e13',
        borderRadius: 7, border: '1px solid rgba(255,255,255,0.05)',
        fontFamily: 'monospace', fontSize: 11, lineHeight: 1.7, color: '#90a4ae',
        whiteSpace: 'pre-wrap', overflow: 'auto',
      }}>
        {code}
      </pre>
    </div>
  );

  return (
    <div>
      {block('Workflow shell', `workflow "My Workflow" {\n  description: "What it does"\n  agent: @agent-id\n  sendToCanvas: true\n}`)}
      {block('Steps', `step: prompt "Explain {{topic}} clearly"\nstep[name]: summarize "Key takeaways from above"\nstep: web "{{topic}} news {{date}}"\nstep: template "# {{workflow_name}}\\n{{output}}"\nstep: code "js: return input.toUpperCase()"\nstep: notify "email: {{output}}"`)}
      {block('Variables', `var topic            # prompts at run-time\nvar limit = "50"    # with a default\n# Built-ins: {{output}} {{input}} {{date}} {{time}} {{datetime}} {{workflow_name}}`)}
      {block('Conditional', `if "output mentions error" {\n  step: notify "slack: Error detected"\n} else {\n  step: summarize "All clear — wrap up"\n}`)}
      {block('Chain workflows', `run @workflow-id     # trigger another workflow`)}
      {block('Connections', `step: fetch @conn-id "keyword"   # fetch_connection`)}
    </div>
  );
}
