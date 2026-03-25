import React, { useState, useEffect, useRef } from 'react';
import { useSCStore } from '../store';
import {
  Code2, RefreshCw, Save, Play, Download, FileCode, Check, Loader,
  AlertCircle, AlertTriangle, Info, Trash2, ChevronDown, Zap, Copy,
  Wand2, MessageSquare, X, Sparkles, CornerDownLeft, RotateCcw,
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
.ori-err-line {
  background: rgba(239,83,80,0.10);
  background-image: repeating-linear-gradient(
    90deg,
    rgba(239,83,80,0.8) 0px, rgba(239,83,80,0.8) 2px,
    transparent 2px, transparent 5px,
    rgba(239,83,80,0.8) 5px, rgba(239,83,80,0.8) 6px,
    transparent 6px, transparent 9px
  );
  background-size: 9px 2px;
  background-position: 0 calc(100% - 1px);
  background-repeat: repeat-x;
}
.ori-warn-line {
  background: rgba(255,183,77,0.08);
  background-image: repeating-linear-gradient(
    90deg,
    rgba(255,183,77,0.7) 0px, rgba(255,183,77,0.7) 2px,
    transparent 2px, transparent 5px,
    rgba(255,183,77,0.7) 5px, rgba(255,183,77,0.7) 6px,
    transparent 6px, transparent 9px
  );
  background-size: 9px 2px;
  background-position: 0 calc(100% - 1px);
  background-repeat: repeat-x;
}
.ori-err-pill {
  margin-left: 14px;
  padding: 0 7px;
  border-radius: 3px;
  background: rgba(239,83,80,0.14);
  color: rgba(239,83,80,0.75);
  font-size: 10.5px;
  font-style: italic;
  font-weight: 400;
  pointer-events: none;
  white-space: nowrap;
  vertical-align: middle;
}
.ori-warn-pill {
  margin-left: 14px;
  padding: 0 7px;
  border-radius: 3px;
  background: rgba(255,183,77,0.12);
  color: rgba(255,183,77,0.72);
  font-size: 10.5px;
  font-style: italic;
  font-weight: 400;
  pointer-events: none;
  white-space: nowrap;
  vertical-align: middle;
}
@keyframes ori-spin { from { transform:rotate(0deg) } to { transform:rotate(360deg) } }
/* hide scrollbar on highlight overlay div (WebKit) */
[data-ori-highlight]::-webkit-scrollbar { display: none; }
`;

function injectOriCSS() {
  if (document.getElementById('ori-highlight-css')) return;
  const s = document.createElement('style');
  s.id = 'ori-highlight-css';
  s.textContent = ORI_CSS;
  document.head.appendChild(s);
}

// ─── Autocomplete data ────────────────────────────────────────────────────────
const AC_KEYWORDS = [
  { label: 'workflow', insert: 'workflow "${1:Name}" {\n  $0\n}',        kind: 'keyword',  detail: 'Define a workflow' },
  { label: 'var',      insert: 'var ${1:name}',                          kind: 'keyword',  detail: 'Runtime variable' },
  { label: 'step',     insert: 'step: ',                                 kind: 'keyword',  detail: 'Add a step' },
  { label: 'if',       insert: 'if "${1:condition}" {\n  $0\n}',         kind: 'keyword',  detail: 'Conditional block' },
  { label: 'else',     insert: 'else {\n  $0\n}',                        kind: 'keyword',  detail: 'Else branch' },
  { label: 'run',      insert: 'run @',                                  kind: 'keyword',  detail: 'Run a sub-workflow' },
  { label: 'parallel', insert: 'parallel {\n  $0\n}',                    kind: 'keyword',  detail: 'Parallel steps' },
  { label: 'output',   insert: 'output → canvas',                        kind: 'keyword',  detail: 'Output directive' },
  { label: 'description',  insert: 'description: "${1}"',                kind: 'meta',     detail: 'Workflow description' },
  { label: 'agent',        insert: 'agent: @',                           kind: 'meta',     detail: 'Assign agent' },
  { label: 'sendToCanvas', insert: 'sendToCanvas: true',                 kind: 'meta',     detail: 'Push output to Canvas' },
];

const AC_STEP_TYPES = [
  { label: 'prompt',    insert: 'prompt "${1:Ask the AI something}"',    kind: 'type', detail: 'AI prompt' },
  { label: 'web',       insert: 'web "${1:search query}"',               kind: 'type', detail: 'Web search' },
  { label: 'summarize', insert: 'summarize "${1:Summarise the above}"',  kind: 'type', detail: 'Summarize output' },
  { label: 'transform', insert: 'transform "${1:instructions}"',         kind: 'type', detail: 'Transform data' },
  { label: 'extract',   insert: 'extract "${1:what to extract}"',        kind: 'type', detail: 'Extract structured data' },
  { label: 'template',  insert: 'template "${1:{{output}}}"',            kind: 'type', detail: 'Format template' },
  { label: 'code',      insert: 'code "js: return input"',               kind: 'type', detail: 'Execute code' },
  { label: 'notify',    insert: 'notify "${1:channel}: ${2:message}"',   kind: 'type', detail: 'Send notification' },
  { label: 'search',    insert: 'search "${1:query}"',                   kind: 'type', detail: 'Memory search' },
  { label: 'rag',       insert: 'rag "${1:query}"',                      kind: 'type', detail: 'RAG query' },
  { label: 'ingest',    insert: 'ingest "${1:source}"',                  kind: 'type', detail: 'Ingest document' },
  { label: 'fetch',     insert: 'fetch @',                               kind: 'type', detail: 'Fetch connection' },
];

const AC_BUILTIN_VARS = [
  { label: 'output',        insert: 'output}}',        kind: 'variable', detail: 'Previous step output' },
  { label: 'input',         insert: 'input}}',         kind: 'variable', detail: 'Workflow input' },
  { label: 'date',          insert: 'date}}',          kind: 'variable', detail: "Today's date" },
  { label: 'time',          insert: 'time}}',          kind: 'variable', detail: 'Current time' },
  { label: 'datetime',      insert: 'datetime}}',      kind: 'variable', detail: 'Current datetime' },
  { label: 'workflow_name', insert: 'workflow_name}}', kind: 'variable', detail: 'Workflow name' },
  { label: 'doc_text',      insert: 'doc_text}}',      kind: 'variable', detail: 'Uploaded doc text' },
  { label: 'doc_filename',  insert: 'doc_filename}}',  kind: 'variable', detail: 'Uploaded doc filename' },
];

function extractUserVars(source) {
  const vars = [];
  const re = /^\s*var\s+([\w_]+)/gm;
  let m;
  while ((m = re.exec(source)) !== null) vars.push(m[1]);
  return vars;
}

function getCompletions(source, cursorPos, { workflows = [], userVars = [] } = {}) {
  const before = source.substring(0, cursorPos);
  const lines  = before.split('\n');
  const line   = lines[lines.length - 1];

  // {{ variable trigger
  const varM = line.match(/\{\{([\w_]*)$/);
  if (varM) {
    const pfx = varM[1].toLowerCase();
    const builtins = AC_BUILTIN_VARS.filter(v => v.label.startsWith(pfx));
    const custom   = userVars
      .filter(v => v.startsWith(pfx) && !AC_BUILTIN_VARS.find(b => b.label === v))
      .map(v => ({ label: v, insert: v + '}}', kind: 'variable', detail: 'var' }));
    return { items: [...builtins, ...custom], replaceLen: varM[1].length };
  }

  // @ reference trigger
  const atM = line.match(/@([\w-]*)$/);
  if (atM) {
    const pfx = atM[1].toLowerCase();
    const wfs = workflows
      .filter(w => w.id.includes(pfx) || w.name.toLowerCase().includes(pfx))
      .map(w => ({ label: w.name, insert: w.id, kind: 'reference', detail: `wf · ${w.id.slice(0, 8)}` }));
    return { items: wfs, replaceLen: atM[1].length };
  }

  // Step type trigger (after "step:" or "step[label]:")
  const stM = line.match(/step(?:\[[^\]]*\])?\s*:\s*([\w]*)$/);
  if (stM) {
    const pfx = stM[1].toLowerCase();
    return { items: AC_STEP_TYPES.filter(t => t.label.startsWith(pfx)), replaceLen: stM[1].length };
  }

  // Keyword trigger (word at start of line, possibly indented)
  const kwM = line.match(/^(\s*)([\w]*)$/);
  if (kwM && kwM[2].length >= 1) {
    const pfx = kwM[2].toLowerCase();
    return { items: AC_KEYWORDS.filter(k => k.label.startsWith(pfx)), replaceLen: kwM[2].length };
  }

  return { items: [], replaceLen: 0 };
}

// Strip snippet placeholder syntax ($0, ${1:x}) to get plain insert text
function snippetToText(insert) {
  return insert.replace(/\$\{[0-9]+:([^}]*)\}/g, '$1').replace(/\$[0-9]+/g, '');
}

// Compute approximate caret position in viewport coords
function approxCaretPos(textarea, cursorPos) {
  const before    = textarea.value.substring(0, cursorPos);
  const lines     = before.split('\n');
  const lineNum   = lines.length - 1;
  const colNum    = lines[lineNum].length;
  const taRect    = textarea.getBoundingClientRect();
  const LINE_H_PX = 13 * 1.65;
  const CHAR_W    = 7.8;
  const PAD_T     = 14;
  const PAD_L     = 16;
  const rawX = taRect.left + PAD_L + colNum * CHAR_W;
  const rawY = taRect.top  + PAD_T + (lineNum + 1) * LINE_H_PX - textarea.scrollTop + 4;
  return {
    x: Math.min(rawX, window.innerWidth  - 300),
    y: Math.min(rawY, window.innerHeight - 260),
  };
}

// ─── Autocomplete dropdown ────────────────────────────────────────────────────
const KIND_ICON  = { keyword: '⌨', meta: '⚙', type: '⬡', variable: '⬦', reference: '@', snippet: '✦' };
const KIND_COLOR = { keyword: '#c792ea', meta: '#82aaff', type: '#80cbc4', variable: '#f78c6c', reference: '#ffcb6b', snippet: '#a89cf7' };

function AutocompleteDropdown({ items, index, x, y, onSelect, onHover }) {
  const listRef = useRef(null);

  useEffect(() => {
    const el = listRef.current?.children[index];
    el?.scrollIntoView({ block: 'nearest' });
  }, [index]);

  if (!items.length) return null;

  return (
    <div
      ref={listRef}
      style={{
        position: 'fixed', left: x, top: y, zIndex: 2000,
        background: '#13171f',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 9, overflow: 'hidden auto',
        minWidth: 240, maxWidth: 380, maxHeight: 220,
        boxShadow: '0 12px 40px rgba(0,0,0,0.75)',
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      }}
    >
      {items.map((item, i) => {
        const active = i === index;
        return (
          <div
            key={i}
            onMouseDown={e => { e.preventDefault(); onSelect(item); }}
            onMouseEnter={() => onHover(i)}
            style={{
              display: 'flex', alignItems: 'center', gap: 9,
              padding: '5px 12px',
              background: active ? 'rgba(168,156,247,0.13)' : 'transparent',
              borderLeft: `2px solid ${active ? '#a89cf7' : 'transparent'}`,
              cursor: 'pointer',
            }}
          >
            <span style={{ color: KIND_COLOR[item.kind] || '#90a4ae', fontSize: 10, flexShrink: 0 }}>
              {KIND_ICON[item.kind] || '○'}
            </span>
            <span style={{ fontSize: 12, color: active ? '#e1e4e8' : '#b0bec5', flex: 1, whiteSpace: 'nowrap' }}>
              {item.label}
            </span>
            <span style={{ fontSize: 10, color: '#37474f', flexShrink: 0 }}>
              {item.detail}
            </span>
          </div>
        );
      })}
      {/* Footer showing keybindings */}
      <div style={{
        padding: '4px 12px', borderTop: '1px solid rgba(255,255,255,0.05)',
        fontSize: 10, color: '#263238', display: 'flex', gap: 12,
      }}>
        <span>↑↓ navigate</span>
        <span>↵ / Tab  accept</span>
        <span>Esc  dismiss</span>
      </div>
    </div>
  );
}

// ─── Editor component (gutter + textarea + highlight overlay) ────────────────
function OriEditor({ value, onChange, diagnostics = [], onCursorChange, workflows = [], userVars = [], onInlineEdit, onJumpToLine, taExternalRef }) {
  const taInternalRef = useRef(null);
  const taRef         = taExternalRef ?? taInternalRef;
  const preRef    = useRef(null);
  const gutterRef = useRef(null);

  const [ac,      setAc]      = useState({ visible: false, items: [], index: 0, x: 0, y: 0, replaceLen: 0 });
  const [tooltip, setTooltip] = useState(null); // { x, y, msg, level }

  useEffect(() => { injectOriCSS(); }, []);

  const lines     = value.split('\n');
  const errLines  = new Set(diagnostics.filter(d => d.level === 'error'   && d.line).map(d => d.line));
  const warnLines = new Set(diagnostics.filter(d => d.level === 'warning' && d.line).map(d => d.line));
  // Map line → diagnostic for quick lookup
  const diagByLine = {};
  diagnostics.forEach(d => { if (d.line) diagByLine[d.line] = d; });

  function syncScroll() {
    const top = taRef.current?.scrollTop ?? 0;
    if (preRef.current)    preRef.current.scrollTop    = top;
    if (gutterRef.current) gutterRef.current.scrollTop = top;
  }

  function updateCursor(ta) {
    if (!ta || !onCursorChange) return;
    const pre = value.substring(0, ta.selectionStart);
    const ln  = pre.split('\n').length;
    const col = pre.split('\n').pop().length + 1;
    onCursorChange(ln, col);
  }

  function triggerAC(ta) {
    const pos = ta.selectionStart;
    const { items, replaceLen } = getCompletions(value, pos, { workflows, userVars });
    if (items.length === 0) { setAc(prev => ({ ...prev, visible: false })); return; }
    const { x, y } = approxCaretPos(ta, pos);
    setAc({ visible: true, items, index: 0, x, y, replaceLen, cursorPos: pos });
  }

  function acceptCompletion(item) {
    const ta      = taRef.current;
    if (!ta) return;
    const pos     = ta.selectionStart;
    const plain   = snippetToText(item.insert);
    const before  = value.substring(0, pos - ac.replaceLen);
    const after   = value.substring(pos);
    const newVal  = before + plain + after;
    const newPos  = before.length + plain.length;
    onChange(newVal);
    setAc(prev => ({ ...prev, visible: false }));
    // Restore focus + cursor after React re-render
    requestAnimationFrame(() => {
      ta.focus();
      ta.setSelectionRange(newPos, newPos);
    });
  }

  function onKeyDown(e) {
    // Ctrl+K → inline edit for selection
    if (e.ctrlKey && e.key === 'k') {
      e.preventDefault();
      const ta = e.target;
      if (ta.selectionStart !== ta.selectionEnd) {
        const start = ta.selectionStart;
        const end   = ta.selectionEnd;
        const text  = value.substring(start, end);
        const pos   = approxCaretPos(ta, end);
        onInlineEdit?.({ start, end, text, x: Math.min(pos.x, window.innerWidth - 440), y: Math.min(pos.y, window.innerHeight - 320) });
      }
      return;
    }
    if (!ac.visible) {
      // Ctrl+Space → force show
      if (e.key === ' ' && e.ctrlKey) {
        e.preventDefault();
        triggerAC(e.target);
      }
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setAc(prev => ({ ...prev, index: Math.min(prev.index + 1, prev.items.length - 1) }));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setAc(prev => ({ ...prev, index: Math.max(prev.index - 1, 0) }));
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      acceptCompletion(ac.items[ac.index]);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setAc(prev => ({ ...prev, visible: false }));
    }
  }

  function onInput(e) {
    onChange(e.target.value);
    triggerAC(e.target);
    updateCursor(e.target);
    syncScroll();
  }

  function onKeyUp(e) {
    updateCursor(e.target);
    // Re-trigger on navigation keys
    if (['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(e.key)) {
      triggerAC(e.target);
    }
  }

  const FONT = "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Courier New', monospace";
  const LINE_H = 1.65;
  const FONT_SZ = 13;
  const PAD_V = 14;
  const PAD_H = 16;

  const baseTextStyle = {
    margin: 0, padding: `${PAD_V}px ${PAD_H}px`,
    fontFamily: FONT, fontSize: FONT_SZ, lineHeight: LINE_H,
    whiteSpace: 'pre-wrap', wordWrap: 'break-word', overflowWrap: 'break-word',
    tabSize: 2, boxSizing: 'border-box',
  };

  function buildHighlightedHtml(code) {
    const raw = highlight(code);
    return raw.split('\n').map((lineHtml, i) => {
      const ln    = i + 1;
      const isErr  = errLines.has(ln);
      const isWarn = warnLines.has(ln);
      const cls   = isErr ? ' class="ori-err-line"' : isWarn ? ' class="ori-warn-line"' : '';
      const diag  = diagByLine[ln];
      const pill  = diag
        ? `<span class="${isErr ? 'ori-err-pill' : 'ori-warn-pill'}">${
            diag.message.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
          }</span>`
        : '';
      return `<span${cls} style="display:block">${lineHtml || ' '}${pill}</span>`;
    }).join('');
  }

  function onMouseMoveEditor(e) {
    const ta = taRef.current;
    if (!ta) return;
    const rect   = ta.getBoundingClientRect();
    const relY   = e.clientY - rect.top + ta.scrollTop - PAD_V;
    const lineH  = FONT_SZ * LINE_H;
    const lineNo = Math.floor(relY / lineH) + 1;
    const diag   = diagByLine[lineNo];
    if (diag) {
      setTooltip({ x: e.clientX + 14, y: e.clientY - 10, msg: diag.message, level: diag.level });
    } else {
      setTooltip(null);
    }
  }


  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden', background: '#0d1117', position: 'relative' }}>
      {/* ── Gutter ── */}
      <div
        ref={gutterRef}
        style={{
          flexShrink: 0, width: 52, overflowY: 'hidden', overflowX: 'hidden',
          background: '#0a0d12', borderRight: '1px solid rgba(255,255,255,0.05)',
          userSelect: 'none', paddingTop: PAD_V, paddingBottom: PAD_V,
        }}
      >
        {lines.map((_, i) => {
          const ln = i + 1;
          const hasErr  = errLines.has(ln);
          const hasWarn = warnLines.has(ln);
          return (
            <div
              key={ln}
              title={diagByLine[ln]?.message}
              onClick={() => onJumpToLine?.(ln)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
                paddingRight: 8, gap: 4,
                fontFamily: FONT, fontSize: FONT_SZ, lineHeight: LINE_H,
                color: hasErr ? '#ef5350' : hasWarn ? '#ffb74d' : '#3d4f5c',
                background: hasErr ? 'rgba(239,83,80,0.08)' : hasWarn ? 'rgba(255,183,77,0.07)' : 'transparent',
                cursor: (hasErr || hasWarn) ? 'pointer' : 'default',
              }}
            >
              {hasErr  && <span style={{ color: '#ef5350', fontSize: 9 }}>●</span>}
              {hasWarn && <span style={{ color: '#ffb74d', fontSize: 9 }}>●</span>}
              <span style={{ minWidth: 24, textAlign: 'right' }}>{ln}</span>
            </div>
          );
        })}
      </div>

      {/* ── Code area ── */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <div
          ref={preRef}
          aria-hidden="true"
          data-ori-highlight
          style={{
            ...baseTextStyle,
            position: 'absolute', inset: 0,
            color: '#abb2bf',
            pointerEvents: 'none',
            /* overflow scroll + hidden scrollbar so scrollTop sync works reliably */
            overflowY: 'scroll',
            scrollbarWidth: 'none',       /* Firefox */
            msOverflowStyle: 'none',      /* IE/Edge */
            background: 'transparent',
            zIndex: 0,
          }}
          dangerouslySetInnerHTML={{ __html: buildHighlightedHtml(value) }}
        />
        <textarea
          ref={taRef}
          value={value}
          onInput={onInput}
          onChange={() => {}}      /* controlled via onInput */
          onScroll={syncScroll}
          onKeyDown={onKeyDown}
          onKeyUp={onKeyUp}
          onClick={e => { updateCursor(e.target); triggerAC(e.target); }}
          onBlur={() => setTimeout(() => setAc(prev => ({ ...prev, visible: false })), 120)}
          onMouseMove={onMouseMoveEditor}
          onMouseLeave={() => setTooltip(null)}
          spellCheck={false}
          autoComplete="off"
          autoCorrect="off"
          style={{
            ...baseTextStyle,
            position: 'absolute', inset: 0,
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

      {/* ── Autocomplete dropdown (portal via fixed position) ── */}
      {ac.visible && (
        <AutocompleteDropdown
          items={ac.items}
          index={ac.index}
          x={ac.x}
          y={ac.y}
          onSelect={acceptCompletion}
          onHover={i => setAc(prev => ({ ...prev, index: i }))}
        />
      )}

      {/* ── Diagnostic hover tooltip ── */}
      {tooltip && (
        <div style={{
          position: 'fixed', left: Math.min(tooltip.x, window.innerWidth - 340), top: tooltip.y,
          zIndex: 200, pointerEvents: 'none',
          maxWidth: 320, padding: '5px 10px', borderRadius: 6,
          background: tooltip.level === 'error' ? 'rgba(30,10,10,0.96)' : 'rgba(20,15,5,0.96)',
          border: `1px solid ${tooltip.level === 'error' ? 'rgba(239,83,80,0.45)' : 'rgba(255,183,77,0.35)'}`,
          boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
          color: tooltip.level === 'error' ? '#ef9a9a' : '#ffd54f',
          fontSize: 11.5, fontFamily: "'JetBrains Mono','Fira Code',monospace",
          lineHeight: 1.5, whiteSpace: 'pre-wrap',
        }}>
          <span style={{ opacity: 0.5, marginRight: 6 }}>{tooltip.level === 'error' ? 'E' : 'W'}</span>
          {tooltip.msg}
        </div>
      )}
    </div>
  );
}

// ─── Diagnostics panel ────────────────────────────────────────────────────────
function DiagnosticsPanel({ diagnostics, compiled, vars, onJumpToLine }) {
  const errors   = diagnostics.filter(d => d.level === 'error');
  const warnings = diagnostics.filter(d => d.level === 'warning');

  const badge = (count, color, bg) => count > 0 && (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 3,
      background: bg, color, borderRadius: 4, padding: '1px 7px',
      fontSize: 10, fontWeight: 700, fontFamily: 'monospace',
    }}>
      {count === 1 ? (color === '#ef5350' ? 'E' : 'W') : count}
      {count > 1 && (color === '#ef5350' ? ' errors' : ' warnings')}
      {count === 1 && (color === '#ef5350' ? ' error' : ' warning')}
    </span>
  );

  return (
    <div style={{
      borderBottom: '1px solid rgba(255,255,255,0.07)',
      overflowY: 'auto', maxHeight: 260,
      background: '#090c10',
    }}>
      {/* Header bar (always visible) */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '6px 14px', borderBottom: '1px solid rgba(255,255,255,0.05)',
        background: '#0a0d12', flexShrink: 0,
      }}>
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#3d4f5c' }}>
          PROBLEMS
        </span>
        {badge(errors.length,   '#ef5350', 'rgba(239,83,80,0.15)')}
        {badge(warnings.length, '#ffb74d', 'rgba(255,183,77,0.15)')}
        {compiled && (
          <span style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ fontSize: 10, color: '#3d4f5c', fontFamily: 'monospace' }}>
              {compiled.steps?.length ?? 0} steps
              {vars?.length > 0 ? `  ·  ${vars.length} var${vars.length > 1 ? 's' : ''}` : ''}
              {compiled.sendToCanvas ? '  ·  → canvas' : ''}
            </span>
          </span>
        )}
      </div>

      {/* Compiler messages */}
      <div style={{ padding: '6px 0' }}>
        {diagnostics.length === 0 && (
          <div style={{ padding: '6px 14px', color: '#3d4f5c', fontSize: 11, fontFamily: 'monospace' }}>
            No problems detected.
          </div>
        )}
        {diagnostics.map((d, i) => {
          const isErr  = d.level === 'error';
          const isWarn = d.level === 'warning';
          const col    = isErr ? '#ef5350' : isWarn ? '#ffb74d' : '#546e7a';
          const code   = isErr ? 'E' : isWarn ? 'W' : 'I';
          const n      = String(i + 1).padStart(3, '0');
          const canJump = d.line && onJumpToLine;
          return (
            <div
              key={i}
              onClick={() => canJump && onJumpToLine(d.line)}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 0,
                padding: '3px 0',
                background: isErr ? 'rgba(239,83,80,0.04)' : isWarn ? 'rgba(255,183,77,0.03)' : 'transparent',
                borderLeft: `2px solid ${isErr ? '#ef5350' : isWarn ? '#ffb74d' : 'transparent'}`,
                cursor: canJump ? 'pointer' : 'default',
                transition: 'background 0.1s',
              }}
              onMouseEnter={e => { if (canJump) e.currentTarget.style.background = isErr ? 'rgba(239,83,80,0.09)' : 'rgba(255,183,77,0.07)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = isErr ? 'rgba(239,83,80,0.04)' : isWarn ? 'rgba(255,183,77,0.03)' : 'transparent'; }}
            >
              {/* Severity tag */}
              <span style={{
                flexShrink: 0, width: 68, paddingLeft: 10,
                fontFamily: 'monospace', fontSize: 11,
                color: col, fontWeight: 700,
              }}>
                {code}[{n}]
              </span>
              {/* Message */}
              <span style={{
                flex: 1, fontFamily: 'monospace', fontSize: 11, lineHeight: 1.6,
                color: isErr ? '#e57373' : isWarn ? '#ffd54f' : '#607d8b',
                paddingRight: 14,
              }}>
                {d.message}
                {d.line ? <span style={{ color: canJump ? '#546e7a' : '#3d4f5c', marginLeft: 4 }}>:{d.line}</span> : null}
                {canJump && <span style={{ marginLeft: 6, fontSize: 9, color: '#3d4f5c', opacity: 0.7 }}>↑ jump</span>}
              </span>
            </div>
          );
        })}
      </div>
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

// ─── AI assist streaming helper ───────────────────────────────────────────────
async function streamAiAssist(params, { onChunk, onDone, onError } = {}) {
  try {
    const r = await fetch('/ori/ai-assist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!r.ok) { onError?.('Request failed'); return; }
    const reader  = r.body.getReader();
    const decoder = new TextDecoder();
    let full = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      for (const line of chunk.split('\n')) {
        if (!line.startsWith('data: ')) continue;
        const d = line.slice(6).trim();
        if (d === '[DONE]') { onDone?.(full); return; }
        try {
          const p = JSON.parse(d);
          if (p.error) { onError?.(p.error); return; }
          if (p.text)  { full += p.text; onChunk?.(p.text, full); }
        } catch {}
      }
    }
    onDone?.(full);
  } catch (e) { onError?.(e.message); }
}

// ─── Inline Edit Bar (Ctrl+K) ─────────────────────────────────────────────────
function InlineEditBar({ editState, source, onApply, onClose }) {
  const [instruction, setInstruction] = useState('');
  const [result,      setResult]      = useState(null);
  const [streaming,   setStreaming]   = useState('');
  const [busy,        setBusy]        = useState(false);
  const [mode,        setMode]        = useState('edit'); // edit | explain
  const inputRef = useRef(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  async function run(m = mode) {
    if (!instruction.trim() && m !== 'explain') return;
    setBusy(true); setResult(null); setStreaming('');
    await streamAiAssist(
      { mode: m === 'explain' ? 'explain' : 'edit', source, sel_text: editState.text, instruction: instruction.trim() },
      {
        onChunk: (_, full) => setStreaming(full),
        onDone:  full => { setResult(full); setStreaming(''); setBusy(false); },
        onError: err  => { setResult(`⚠ ${err}`); setStreaming(''); setBusy(false); },
      }
    );
  }

  const boxStyle = {
    position: 'fixed', left: editState.x, top: editState.y, zIndex: 3000,
    background: '#13171f', border: '1px solid rgba(168,156,247,0.35)',
    borderRadius: 10, width: 420, maxWidth: 'calc(100vw - 32px)',
    boxShadow: '0 16px 48px rgba(0,0,0,0.8)',
    fontFamily: "'JetBrains Mono', monospace",
    overflow: 'hidden',
  };

  return (
    <div style={boxStyle} onMouseDown={e => e.stopPropagation()}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderBottom: '1px solid rgba(255,255,255,0.07)', background: '#0d1117' }}>
        <Wand2 size={12} style={{ color: '#a89cf7' }} />
        <span style={{ fontSize: 11, color: '#a89cf7', fontWeight: 700 }}>Inline Edit</span>
        <span style={{ fontSize: 10, color: '#37474f', flex: 1 }}>
          {editState.text.split('\n').length} lines selected · Ctrl+K
        </span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#546e7a', padding: 2 }}>
          <X size={12} />
        </button>
      </div>

      {/* Input */}
      <div style={{ display: 'flex', gap: 6, padding: '8px 12px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <input
          ref={inputRef}
          value={instruction}
          onChange={e => setInstruction(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') run(); if (e.key === 'Escape') onClose(); }}
          placeholder="Describe the edit… (Enter to run)"
          style={{
            flex: 1, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 6, padding: '6px 10px', color: '#e1e4e8', fontSize: 12, outline: 'none',
            fontFamily: 'inherit',
          }}
        />
        <button
          onClick={() => run('edit')}
          disabled={busy || !instruction.trim()}
          style={{ ...goldBtn, padding: '6px 10px', fontSize: 11 }}
        >
          {busy ? <Loader size={11} style={{ animation: 'ori-spin 1s linear infinite' }} /> : <Wand2 size={11} />}
          {busy ? '' : 'Edit'}
        </button>
        <button
          onClick={() => run('explain')}
          disabled={busy}
          style={{ ...ghostBtn, padding: '6px 10px', fontSize: 11 }}
        >
          Explain
        </button>
      </div>

      {/* Streaming / result */}
      {(streaming || result) && (
        <div style={{ padding: '8px 12px', maxHeight: 220, overflowY: 'auto' }}>
          <pre style={{
            margin: 0, fontSize: 11, lineHeight: 1.65,
            color: result?.startsWith('⚠') ? '#ef5350' : '#abb2bf',
            whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'inherit',
          }}>
            {streaming || result}
            {busy && <span style={{ color: '#a89cf7', animation: 'ori-spin 1s linear infinite', display: 'inline-block' }}>▊</span>}
          </pre>
        </div>
      )}

      {/* Accept / Reject */}
      {result && !result.startsWith('⚠') && (
        <div style={{ display: 'flex', gap: 8, padding: '8px 12px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <button
            onClick={() => { onApply(editState.start, editState.end, result.trim()); onClose(); }}
            style={{ ...greenBtn, fontSize: 11, padding: '5px 12px' }}
          >
            <Check size={11} /> Apply
          </button>
          <button onClick={() => { setResult(null); setInstruction(''); }} style={{ ...ghostBtn, fontSize: 11, padding: '5px 10px' }}>
            <RotateCcw size={11} /> Retry
          </button>
          <button onClick={onClose} style={{ ...ghostBtn, fontSize: 11, padding: '5px 10px', marginLeft: 'auto' }}>
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Vibe Coding Panel ────────────────────────────────────────────────────────
function VibeCodingPanel({ source, diagnostics = [], onApply, onClose }) {
  const [messages,  setMessages]  = useState([
    { role: 'ori', text: "I know ORI inside out. Describe a workflow and I'll build it — or tell me how to modify the current one.", isSystem: true },
  ]);
  const [input,     setInput]     = useState('');
  const [busy,      setBusy]      = useState(false);
  const [streaming, setStreaming] = useState('');
  const endRef   = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, streaming]);
  useEffect(() => { inputRef.current?.focus(); }, []);

  const FIX_RE = /\b(fix|repair|correct|resolve|errors?|warnings?|broken|issues?)\b/i;

  async function send(overrideText, overrideMode) {
    const userText = overrideText ?? input.trim();
    if (!userText || busy) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userText }]);
    setBusy(true); setStreaming('');

    const hasSource = source.trim() !== '';
    const hasDiags  = diagnostics.length > 0;

    // Auto-detect fix intent OR explicit override
    const isFix = overrideMode === 'fix' || (hasDiags && FIX_RE.test(userText));

    let mode, instruction;
    if (isFix) {
      mode        = 'fix';
      instruction = userText;
    } else {
      mode = 'generate';
      instruction = hasSource
        ? `Current workflow:\n${source}\n\nModification: ${userText}`
        : userText;
    }

    await streamAiAssist(
      { mode, instruction, source: hasSource ? source : '', diagnostics: hasDiags ? diagnostics : [] },
      {
        onChunk: (_, full) => setStreaming(full),
        onDone: full => {
          const clean = full.replace(/^```ori\n?/i, '').replace(/\n?```$/, '').trim();
          setMessages(prev => [...prev, { role: 'ori', text: clean, isCode: true }]);
          setStreaming('');
          setBusy(false);
        },
        onError: err => {
          setMessages(prev => [...prev, { role: 'ori', text: `⚠ ${err}`, isError: true }]);
          setStreaming('');
          setBusy(false);
        },
      }
    );
  }

  const FONT = "'JetBrains Mono', 'Fira Code', monospace";

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden',
      borderTop: '1px solid rgba(168,156,247,0.2)', background: '#090d13',
    }}>
      {/* Panel header */}
      <div style={{
        flexShrink: 0, display: 'flex', alignItems: 'center', gap: 8,
        padding: '7px 14px', borderBottom: '1px solid rgba(255,255,255,0.06)',
        background: '#0a0e13',
      }}>
        <Sparkles size={12} style={{ color: '#a89cf7' }} />
        <span style={{ fontSize: 11, fontWeight: 800, color: '#a89cf7', fontFamily: "var(--font-grotesk, sans-serif)", letterSpacing: '0.04em' }}>
          VIBE MODE
        </span>
        <span style={{ fontSize: 10, color: '#37474f', fontFamily: 'monospace', flex: 1 }}>
          describe → generate
        </span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#37474f', padding: 2 }}>
          <X size={12} />
        </button>
      </div>

      {/* Message list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: '95%',
          }}>
            {m.role === 'user' ? (
              <div style={{
                background: 'rgba(168,156,247,0.12)', color: '#c9c0f5',
                borderRadius: '10px 10px 3px 10px', padding: '7px 12px',
                fontSize: 12, fontFamily: "var(--font-inter, sans-serif)", lineHeight: 1.55,
              }}>
                {m.text}
              </div>
            ) : m.isCode ? (
              <div style={{ width: '100%' }}>
                <pre
                  style={{
                    margin: 0, padding: '10px 12px',
                    background: '#0d1117', borderRadius: '10px 10px 10px 3px',
                    border: '1px solid rgba(255,255,255,0.07)',
                    fontSize: 12, lineHeight: 1.65, color: '#abb2bf',
                    fontFamily: FONT, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                    overflowX: 'auto', tabSize: 2, MozTabSize: 2,
                  }}
                  dangerouslySetInnerHTML={{ __html: highlight(m.text) }}
                />
                <div style={{ display: 'flex', gap: 6, marginTop: 5 }}>
                  <button onClick={() => onApply(m.text)} style={{ ...greenBtn, fontSize: 10, padding: '3px 10px' }}>
                    <Check size={10} /> Apply to Editor
                  </button>
                  <button
                    onClick={() => navigator.clipboard?.writeText(m.text)}
                    style={{ ...ghostBtn, fontSize: 10, padding: '3px 8px' }}
                  >
                    <Copy size={10} /> Copy
                  </button>
                </div>
              </div>
            ) : (
              <div style={{
                color: m.isError ? '#ef5350' : m.isSystem ? '#546e7a' : '#78909c',
                fontSize: 11, fontFamily: "var(--font-inter, sans-serif)", lineHeight: 1.55,
                fontStyle: m.isSystem ? 'italic' : 'normal',
                padding: '4px 0',
              }}>
                {m.text}
              </div>
            )}
          </div>
        ))}

        {/* Live streaming */}
        {streaming && (
          <div style={{ alignSelf: 'flex-start', maxWidth: '95%' }}>
            <pre style={{
              margin: 0, padding: '10px 12px',
              background: '#0d1117', borderRadius: 10,
              border: '1px solid rgba(168,156,247,0.15)',
              fontSize: 12, lineHeight: 1.65, color: '#abb2bf',
              fontFamily: FONT, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              tabSize: 2, MozTabSize: 2,
            }}>
              <span dangerouslySetInnerHTML={{ __html: highlight(streaming) }} />
              <span style={{ color: '#a89cf7' }}>▊</span>
            </pre>
          </div>
        )}

        {busy && !streaming && (
          <div style={{ alignSelf: 'flex-start', color: '#37474f', fontSize: 11, fontStyle: 'italic', fontFamily: 'monospace', display: 'flex', alignItems: 'center', gap: 5 }}>
            <Loader size={10} style={{ animation: 'ori-spin 1s linear infinite' }} /> thinking…
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Fix issues chip + Input */}
      <div style={{
        flexShrink: 0, padding: '8px 12px',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        background: '#09100f',
        display: 'flex', flexDirection: 'column', gap: 6,
      }}>
        {/* Quick-fix chip — shown when diagnostics exist */}
        {diagnostics.length > 0 && !busy && (
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {(() => {
              const errCnt  = diagnostics.filter(d => d.level === 'error').length;
              const warnCnt = diagnostics.filter(d => d.level === 'warning').length;
              const label   = [errCnt && `${errCnt} error${errCnt > 1 ? 's' : ''}`, warnCnt && `${warnCnt} warning${warnCnt > 1 ? 's' : ''}`].filter(Boolean).join(' + ');
              return (
                <button
                  onClick={() => send(`Fix all diagnostics`, 'fix')}
                  style={{
                    background: errCnt ? 'rgba(239,83,80,0.12)' : 'rgba(255,183,77,0.1)',
                    border: `1px solid ${errCnt ? 'rgba(239,83,80,0.3)' : 'rgba(255,183,77,0.3)'}`,
                    borderRadius: 6, padding: '3px 10px', cursor: 'pointer',
                    color: errCnt ? '#ef5350' : '#ffb74d',
                    fontSize: 10, fontFamily: 'monospace', fontWeight: 700,
                    display: 'flex', alignItems: 'center', gap: 5,
                  }}
                >
                  <Zap size={9} />
                  Fix {label}
                </button>
              );
            })()}
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Describe a workflow, or ask to modify the current one…  (↵ send  ⇧↵ newline)"
            rows={2}
            style={{
              flex: 1, resize: 'none', background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8,
              padding: '7px 10px', color: '#e1e4e8', fontSize: 11, outline: 'none',
              fontFamily: "var(--font-inter, sans-serif)", lineHeight: 1.5,
            }}
          />
          <button
            onClick={() => send()}
            disabled={busy || !input.trim()}
            style={{
              ...goldBtn, padding: '7px 12px', fontSize: 12,
              opacity: (!input.trim() || busy) ? 0.4 : 1,
            }}
          >
            {busy
              ? <Loader size={13} style={{ animation: 'ori-spin 1s linear infinite' }} />
              : <CornerDownLeft size={13} />}
          </button>
        </div>
      </div>
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
  const [cursor,      setCursor]      = useState({ ln: 1, col: 1 });
  const [vibeOpen,    setVibeOpen]    = useState(false);
  const [inlineEdit,  setInlineEdit]  = useState(null); // { start, end, text, x, y }
  const debounceRef  = useRef(null);
  const pollRef      = useRef(null);
  const editorTaRef  = useRef(null); // forwarded textarea ref for jump-to-line

  function jumpToLine(ln) {
    const ta = editorTaRef.current;
    if (!ta) return;
    const lines = source.split('\n');
    const charPos = lines.slice(0, ln - 1).reduce((acc, l) => acc + l.length + 1, 0);
    ta.focus();
    ta.setSelectionRange(charPos, charPos);
    // Scroll the line into view
    const FONT_SZ = 13, LINE_H = 1.65, PAD_V = 14;
    ta.scrollTop = Math.max(0, (ln - 1) * FONT_SZ * LINE_H + PAD_V - ta.clientHeight / 2);
  }

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
            <Loader size={11} style={{ animation: 'ori-spin 1s linear infinite' }} /> compiling…
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
          <RefreshCw size={12} style={compiling ? { animation: 'ori-spin 1s linear infinite' } : {}} />
          Compile
        </button>

        <button onClick={saveWorkflow} disabled={!compiled || saving} style={compiled ? goldBtn : dimBtn}>
          {saved
            ? <><Check size={12} /> Saved!</>
            : saving
            ? <><Loader size={12} style={{ animation: 'ori-spin 1s linear infinite' }} /> Saving…</>
            : <><Save size={12} /> Save</>}
        </button>

        <button onClick={runWorkflow} disabled={!compiled || running} style={compiled ? greenBtn : dimBtn}>
          {running
            ? <><Loader size={12} style={{ animation: 'ori-spin 1s linear infinite' }} /> Running…</>
            : <><Play size={12} /> Run</>}
        </button>

        <button onClick={exportOri} style={ghostBtn} title="Export as .ori file">
          <Download size={12} /> .ori
        </button>

        <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.07)', margin: '0 2px' }} />

        <button
          onClick={() => setVibeOpen(o => !o)}
          style={{
            ...btnBase,
            background: vibeOpen ? 'rgba(168,156,247,0.22)' : 'rgba(168,156,247,0.08)',
            color: '#a89cf7',
            border: `1px solid ${vibeOpen ? 'rgba(168,156,247,0.4)' : 'transparent'}`,
          }}
          title="Vibe Mode — describe workflows in natural language"
        >
          <Sparkles size={12} /> Vibe
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
          <OriEditor
            value={source}
            onChange={setSource}
            diagnostics={diagnostics}
            onCursorChange={(ln, col) => setCursor({ ln, col })}
            workflows={workflows}
            userVars={extractUserVars(source)}
            onInlineEdit={setInlineEdit}
            onJumpToLine={jumpToLine}
            taExternalRef={editorTaRef}
          />
          {/* ── Status bar ── */}
          <div style={{
            flexShrink: 0, display: 'flex', alignItems: 'center', gap: 12,
            padding: '3px 14px', background: '#07090e',
            borderTop: '1px solid rgba(255,255,255,0.05)',
            fontSize: 10, fontFamily: 'monospace', color: '#3d4f5c',
            userSelect: 'none',
          }}>
            <span>Ln {cursor.ln}, Col {cursor.col}</span>
            <span style={{ marginLeft: 4 }}>
              {source.split('\n').length} lines
            </span>
            <span style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
              {diagnostics.filter(d => d.level === 'error').length > 0 && (
                <span style={{ color: '#ef5350' }}>
                  ✕ {diagnostics.filter(d => d.level === 'error').length} error{diagnostics.filter(d => d.level === 'error').length > 1 ? 's' : ''}
                </span>
              )}
              {diagnostics.filter(d => d.level === 'warning').length > 0 && (
                <span style={{ color: '#ffb74d' }}>
                  ⚠ {diagnostics.filter(d => d.level === 'warning').length} warning{diagnostics.filter(d => d.level === 'warning').length > 1 ? 's' : ''}
                </span>
              )}
              {compiled && diagnostics.filter(d => d.level === 'error').length === 0 && (
                <span style={{ color: '#37474f' }}>✓ compiled</span>
              )}
              <span style={{ color: '#263238' }}>ORI v1.0</span>
            </span>
          </div>
        </div>

        {/* ── Right: diagnostics + log ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <DiagnosticsPanel diagnostics={diagnostics} compiled={compiled} vars={vars} onJumpToLine={jumpToLine} />

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
          {!runLog.length && !vibeOpen && (
            <div style={{
              flex: 1, overflowY: 'auto', padding: '14px 16px', background: '#0d1117',
            }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#546e7a', marginBottom: 12 }}>
                ORI Syntax Reference
              </div>
              <SyntaxRef />
            </div>
          )}

          {!vibeOpen && <RunLog entries={runLog} onClear={() => setRunLog([])} />}

          {vibeOpen && (
            <VibeCodingPanel
              source={source}
              diagnostics={diagnostics}
              onApply={newSource => { setSource(newSource); }}
              onClose={() => setVibeOpen(false)}
            />
          )}
        </div>
      </div>

      {/* ── Inline Edit Bar (Ctrl+K) ── */}
      {inlineEdit && (
        <InlineEditBar
          editState={inlineEdit}
          source={source}
          onApply={(start, end, newText) => {
            setSource(source.substring(0, start) + newText + source.substring(end));
          }}
          onClose={() => setInlineEdit(null)}
        />
      )}
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
