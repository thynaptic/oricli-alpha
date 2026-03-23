import { useState, useRef, useEffect, useCallback } from 'react';
import { useSCStore } from '../store';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  Plus, X, Send, Square, Copy, Check, Edit3, Eye, History,
  Download, Trash2, Wand2, Minimize2, Maximize2, FileCode2,
  FileText, Table2, Code2, Globe, GitCommit, RotateCcw, ExternalLink,
  RefreshCw, Pencil, ImageIcon, Loader2, AlertCircle,
} from 'lucide-react';
// ─── Constants ────────────────────────────────────────────────────────────────

const CANVAS_SYSTEM = `You are a collaborative document assistant. When producing code, diagrams, or structured documents, always wrap the content in a single fenced code block with the correct language tag (e.g. \`\`\`go, \`\`\`mermaid, \`\`\`html, \`\`\`markdown). Produce clean, complete content. No prose wrappers unless the user explicitly asks for explanation alongside the artifact.`;

const TYPE_MAP = {
  mermaid: 'diagram', plantuml: 'diagram',
  html: 'html', htm: 'html',
  json: 'json', jsonc: 'json', json5: 'json',
  csv: 'table', tsv: 'table',
  md: 'markdown', markdown: 'markdown',
  txt: 'text',
};

const TYPE_ICONS = {
  code: Code2, markdown: FileText, html: Globe,
  diagram: GitCommit, json: FileCode2, table: Table2, text: FileText,
};

const TYPE_LABELS = {
  code: 'Code', markdown: 'Markdown', html: 'HTML',
  diagram: 'Diagram', json: 'JSON', table: 'Table', text: 'Text',
};

// ─── Utility functions ────────────────────────────────────────────────────────

function getType(lang) {
  if (!lang) return 'text';
  return TYPE_MAP[lang.toLowerCase()] || 'code';
}

// Sniff content when the model omits or misuses the language fence tag
function sniffType(type, content) {
  if (type !== 'text' && type !== 'code') return type;
  if (!content) return type;
  const t = content.trimStart();
  if (/^<!doctype\s+html/i.test(t) || /^<html[\s>]/i.test(t) || /^<body[\s>]/i.test(t)) return 'html';
  if (/^<[a-z][\s\S]{0,200}<\/[a-z]/i.test(t) && /<\/(div|section|main|header|article|p|h[1-6]|ul|table|span|form|nav|footer)>/i.test(t)) return 'html';
  return type;
}

function slugName(lang, index) {
  if (!lang || lang === 'markdown' || lang === 'text') return `document-${index + 1}.md`;
  const exts = { go: 'go', python: 'py', javascript: 'js', typescript: 'ts', rust: 'rs', json: 'json', html: 'html', css: 'css', yaml: 'yaml', bash: 'sh', mermaid: 'mmd' };
  return `artifact-${index + 1}.${exts[lang.toLowerCase()] || lang.toLowerCase()}`;
}

function extractLiveArtifact(text) {
  if (!text?.trim()) return null;
  // Find all complete fenced blocks
  const all = [...text.matchAll(/```(\w*)\n([\s\S]*?)```/g)];
  if (all.length > 0) {
    const last = all[all.length - 1];
    const lang = last[1] || 'text';
    const rawType = getType(lang);
    const content = last[2].trim();
    return { type: sniffType(rawType, content), language: lang, content, partial: false };
  }
  // Partial: open fence, no closing yet (streaming)
  const open = text.match(/```(\w*)\n([\s\S]*)$/);
  if (open) {
    const lang = open[1] || 'text';
    const rawType = getType(lang);
    const content = open[2];
    return { type: sniffType(rawType, content), language: lang, content, partial: true };
  }
  // Fallback: Go sovereign engine wraps output in <artifact> XML
  const xmlFull = text.match(/<artifact[^>]*language=["']?(\w+)["']?[^>]*>([\s\S]*?)<\/artifact>/);
  if (xmlFull) {
    const lang = xmlFull[1] || 'text';
    const content = xmlFull[2].trim();
    return { type: sniffType(getType(lang), content), language: lang, content, partial: false };
  }
  const xmlAny = text.match(/<artifact[^>]*>([\s\S]*?)<\/artifact>/);
  if (xmlAny) {
    const content = xmlAny[1].trim();
    return { type: sniffType('markdown', content), language: 'markdown', content, partial: false };
  }
  // No code block: treat as markdown or sniff for HTML
  const content = text.trim();
  return { type: sniffType('markdown', content), language: 'markdown', content, partial: false };
}

// Returns prose parts of a model reply with code blocks removed.
// Returns null when the whole reply is a code/artifact block.
function getChatDisplayText(text) {
  if (!text?.trim()) return null;
  const prose = text
    .replace(/```[\w]*\n[\s\S]*?```/g, '')
    .replace(/<artifact[^>]*>[\s\S]*?<\/artifact>/g, '')
    .trim();
  return prose.length > 0 ? prose : null;
}

function detectNameFromContent(content, language, existingName) {
  if (existingName && existingName !== 'Untitled') return existingName;
  // Try to extract a meaningful name from markdown h1
  const h1 = content.match(/^#\s+(.+)/m);
  if (h1) return h1[1].trim().slice(0, 40);
  // For code, try function/class name
  const fn = content.match(/(?:func|function|class|def)\s+(\w+)/);
  if (fn) return fn[1];
  return existingName || 'Untitled';
}

function formatTs(ts) {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ─── Renderers ────────────────────────────────────────────────────────────────

function CodeRenderer({ content, language }) {
  return (
    <SyntaxHighlighter
      language={language || 'text'}
      style={oneDark}
      showLineNumbers
      customStyle={{ margin: 0, borderRadius: 0, fontSize: 12.5, lineHeight: 1.65, flex: 1, overflow: 'auto', background: 'var(--color-sc-bg)' }}
      wrapLongLines={false}
    >
      {content}
    </SyntaxHighlighter>
  );
}

function MarkdownRenderer({ content }) {
  return (
    <div style={{ padding: '28px 32px', overflowY: 'auto', flex: 1, lineHeight: 1.75, color: 'var(--color-sc-text)', fontSize: 14 }} className="md-canvas">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <SyntaxHighlighter language={match[1]} style={oneDark} customStyle={{ fontSize: 12, borderRadius: 6, margin: '12px 0' }}>{String(children).replace(/\n$/, '')}</SyntaxHighlighter>
            ) : (
              <code style={{ background: 'rgba(255,255,255,0.08)', padding: '2px 6px', borderRadius: 4, fontFamily: 'var(--font-mono)', fontSize: '0.88em' }} {...props}>{children}</code>
            );
          },
          h1: ({ children }) => <h1 style={{ fontFamily: 'var(--font-grotesk)', fontSize: 22, fontWeight: 700, marginTop: 0, marginBottom: 16, color: 'var(--color-sc-text)' }}>{children}</h1>,
          h2: ({ children }) => <h2 style={{ fontFamily: 'var(--font-grotesk)', fontSize: 17, fontWeight: 600, marginTop: 28, marginBottom: 12, color: 'var(--color-sc-text)' }}>{children}</h2>,
          h3: ({ children }) => <h3 style={{ fontFamily: 'var(--font-grotesk)', fontSize: 14, fontWeight: 600, marginTop: 20, marginBottom: 8, color: 'var(--color-sc-text)' }}>{children}</h3>,
          p: ({ children }) => <p style={{ marginTop: 0, marginBottom: 14, color: 'var(--color-sc-text-muted)' }}>{children}</p>,
          ul: ({ children }) => <ul style={{ paddingLeft: 20, marginBottom: 14, color: 'var(--color-sc-text-muted)' }}>{children}</ul>,
          ol: ({ children }) => <ol style={{ paddingLeft: 20, marginBottom: 14, color: 'var(--color-sc-text-muted)' }}>{children}</ol>,
          blockquote: ({ children }) => <blockquote style={{ borderLeft: '3px solid var(--color-sc-gold)', paddingLeft: 14, margin: '12px 0', color: 'var(--color-sc-text-muted)', fontStyle: 'italic' }}>{children}</blockquote>,
          table: ({ children }) => <div style={{ overflowX: 'auto', marginBottom: 14 }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>{children}</table></div>,
          th: ({ children }) => <th style={{ padding: '7px 12px', borderBottom: '1px solid var(--color-sc-border)', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{children}</th>,
          td: ({ children }) => <td style={{ padding: '7px 12px', borderBottom: '1px solid var(--color-sc-border)', color: 'var(--color-sc-text-muted)', fontSize: 13 }}>{children}</td>,
          strong: ({ children }) => <strong style={{ color: 'var(--color-sc-text)', fontWeight: 700 }}>{children}</strong>,
          em: ({ children }) => <em style={{ color: 'var(--color-sc-text)', fontStyle: 'italic' }}>{children}</em>,
          li: ({ children }) => <li style={{ marginBottom: 4, color: 'var(--color-sc-text-muted)' }}>{children}</li>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function HtmlRenderer({ content }) {
  return (
    <iframe
      srcDoc={content}
      sandbox="allow-scripts allow-same-origin"
      style={{ flex: 1, border: 'none', background: '#fff', width: '100%', height: '100%', display: 'block' }}
      title="HTML preview"
    />
  );
}

function DiagramRenderer({ content, language }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '10px 16px', background: 'rgba(196,164,74,0.06)', borderBottom: '1px solid var(--color-sc-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 11, color: 'var(--color-sc-text-muted)' }}>
          <GitCommit size={11} style={{ marginRight: 5, display: 'inline' }} />
          {language} diagram
        </span>
        <a
          href={`https://mermaid.live/edit#base64:${btoa(content)}`}
          target="_blank" rel="noreferrer"
          style={{ fontSize: 11, color: 'var(--color-sc-gold)', display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none' }}
        >
          Open in Mermaid Live <ExternalLink size={10} />
        </a>
      </div>
      <CodeRenderer content={content} language="mermaid" />
    </div>
  );
}

function TableRenderer({ content }) {
  const rows = content.trim().split('\n').map(r => r.split(/[,\t]/));
  const headers = rows[0] || [];
  const body = rows.slice(1);
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>{headers.map((h, i) => <th key={i} style={{ padding: '7px 12px', borderBottom: '1px solid var(--color-sc-border)', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase' }}>{h.trim()}</th>)}</tr>
        </thead>
        <tbody>
          {body.map((row, ri) => (
            <tr key={ri} style={{ background: ri % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
              {row.map((cell, ci) => <td key={ci} style={{ padding: '7px 12px', borderBottom: '1px solid var(--color-sc-border)', color: 'var(--color-sc-text-muted)' }}>{cell.trim()}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ArtifactRenderer({ doc, partial }) {
  if (!doc?.content && !partial) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12, color: 'var(--color-sc-text-dim)' }}>
        <FileText size={32} style={{ opacity: 0.15 }} />
        <div style={{ fontSize: 13, color: 'var(--color-sc-text-muted)' }}>Empty document</div>
      </div>
    );
  }
  const { type, language, content } = doc;
  if (type === 'markdown') return <MarkdownRenderer content={content} />;
  if (type === 'html')     return <HtmlRenderer content={content} />;
  if (type === 'diagram')  return <DiagramRenderer content={content} language={language} />;
  if (type === 'table')    return <TableRenderer content={content} />;
  return <CodeRenderer content={content} language={language} />;
}

// ─── Inline fix toolbar (edit mode) ──────────────────────────────────────────

function InlineToolbar({ visible, onAction, streaming }) {
  const [customOpen, setCustomOpen] = useState(false);
  const [customText, setCustomText] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (customOpen) inputRef.current?.focus();
  }, [customOpen]);

  // Reset when selection disappears
  useEffect(() => {
    if (!visible) { setCustomOpen(false); setCustomText(''); }
  }, [visible]);

  if (!visible) return null;

  const actions = [
    { id: 'fix',      label: 'Fix',      icon: Wand2 },
    { id: 'improve',  label: 'Improve',  icon: Maximize2 },
    { id: 'simplify', label: 'Simplify', icon: Minimize2 },
    { id: 'rewrite_all', label: 'Rewrite All', icon: RefreshCw },
  ];

  return (
    <div style={{
      position: 'absolute', top: 8, left: '50%', transform: 'translateX(-50%)', zIndex: 20,
      background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)',
      borderRadius: 10, boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
      display: 'flex', flexDirection: 'column', gap: 0, overflow: 'hidden', minWidth: 340,
    }}>
      <div style={{ display: 'flex', gap: 2, padding: '5px 6px' }}>
        {actions.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => onAction(id)} disabled={streaming} style={{
            display: 'flex', alignItems: 'center', gap: 4, padding: '5px 10px', borderRadius: 6,
            border: 'none', background: 'transparent', cursor: streaming ? 'not-allowed' : 'pointer',
            fontSize: 12, color: streaming ? 'var(--color-sc-text-dim)' : 'var(--color-sc-text-muted)',
            transition: 'background 0.12s, color 0.12s', whiteSpace: 'nowrap',
          }}
            onMouseEnter={e => { if (!streaming) { e.currentTarget.style.background = 'rgba(196,164,74,0.12)'; e.currentTarget.style.color = 'var(--color-sc-gold)'; } }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = streaming ? 'var(--color-sc-text-dim)' : 'var(--color-sc-text-muted)'; }}
          >
            <Icon size={12} /> {label}
          </button>
        ))}
        <div style={{ width: 1, background: 'var(--color-sc-border)', margin: '4px 2px' }} />
        <button onClick={() => setCustomOpen(o => !o)} disabled={streaming} style={{
          display: 'flex', alignItems: 'center', gap: 4, padding: '5px 10px', borderRadius: 6,
          border: 'none', cursor: streaming ? 'not-allowed' : 'pointer', fontSize: 12,
          background: customOpen ? 'rgba(196,164,74,0.12)' : 'transparent',
          color: customOpen ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
          transition: 'background 0.12s, color 0.12s',
        }}>
          <Pencil size={12} /> Custom…
        </button>
      </div>

      {customOpen && (
        <div style={{ borderTop: '1px solid var(--color-sc-border)', padding: '6px 8px', display: 'flex', gap: 6 }}>
          <input
            ref={inputRef}
            value={customText}
            onChange={e => setCustomText(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && customText.trim()) { onAction('custom', customText.trim()); setCustomText(''); setCustomOpen(false); } if (e.key === 'Escape') setCustomOpen(false); }}
            placeholder='e.g. "translate to TypeScript" or "add error handling"'
            style={{
              flex: 1, background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border2)',
              borderRadius: 6, padding: '5px 8px', fontSize: 12,
              color: 'var(--color-sc-text)', outline: 'none',
            }}
          />
          <button
            onClick={() => { if (customText.trim()) { onAction('custom', customText.trim()); setCustomText(''); setCustomOpen(false); } }}
            disabled={!customText.trim() || streaming}
            style={{
              padding: '5px 10px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 12,
              background: customText.trim() ? 'var(--color-sc-gold)' : 'rgba(255,255,255,0.06)',
              color: customText.trim() ? '#0D0D0D' : 'var(--color-sc-text-dim)',
            }}
          >
            Apply
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Selection popup (preview mode) ──────────────────────────────────────────

function SelectionPopup({ text, rect, onAction, streaming, onClose }) {
  const [customOpen, setCustomOpen] = useState(false);
  const [customText, setCustomText] = useState('');
  const inputRef = useRef(null);
  const popupRef = useRef(null);

  useEffect(() => { if (customOpen) inputRef.current?.focus(); }, [customOpen]);

  if (!text || !rect) return null;

  // Position above the selection
  const top = rect.top + window.scrollY - 8;
  const left = rect.left + rect.width / 2;

  const actions = [
    { id: 'fix',         label: 'Fix',        icon: Wand2 },
    { id: 'improve',     label: 'Improve',    icon: Maximize2 },
    { id: 'simplify',    label: 'Simplify',   icon: Minimize2 },
    { id: 'rewrite_all', label: 'Rewrite All',icon: RefreshCw },
  ];

  return (
    <div ref={popupRef} style={{
      position: 'fixed',
      top: top - (popupRef.current?.offsetHeight ?? 50),
      left: left,
      transform: 'translateX(-50%)',
      zIndex: 9999,
      background: 'var(--color-sc-surface)',
      border: '1px solid var(--color-sc-border)',
      borderRadius: 10,
      boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
      minWidth: 340,
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', gap: 2, padding: '5px 6px', flexWrap: 'wrap' }}>
        {actions.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => { onAction(id); onClose(); }} disabled={streaming} style={{
            display: 'flex', alignItems: 'center', gap: 4, padding: '5px 10px', borderRadius: 6,
            border: 'none', background: 'transparent', cursor: streaming ? 'not-allowed' : 'pointer',
            fontSize: 12, color: streaming ? 'var(--color-sc-text-dim)' : 'var(--color-sc-text-muted)',
            transition: 'background 0.12s, color 0.12s', whiteSpace: 'nowrap',
          }}
            onMouseEnter={e => { if (!streaming) { e.currentTarget.style.background = 'rgba(196,164,74,0.12)'; e.currentTarget.style.color = 'var(--color-sc-gold)'; } }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-sc-text-muted)'; }}
          >
            <Icon size={12} /> {label}
          </button>
        ))}
        <div style={{ width: 1, background: 'var(--color-sc-border)', margin: '4px 2px' }} />
        <button onClick={() => setCustomOpen(o => !o)} style={{
          display: 'flex', alignItems: 'center', gap: 4, padding: '5px 10px', borderRadius: 6,
          border: 'none', cursor: 'pointer', fontSize: 12,
          background: customOpen ? 'rgba(196,164,74,0.12)' : 'transparent',
          color: customOpen ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)',
        }}>
          <Pencil size={12} /> Custom…
        </button>
      </div>
      {customOpen && (
        <div style={{ borderTop: '1px solid var(--color-sc-border)', padding: '6px 8px', display: 'flex', gap: 6 }}>
          <input
            ref={inputRef}
            value={customText}
            onChange={e => setCustomText(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && customText.trim()) { onAction('custom', customText.trim()); onClose(); }
              if (e.key === 'Escape') { setCustomOpen(false); onClose(); }
            }}
            placeholder='Describe the change…'
            style={{
              flex: 1, background: 'var(--color-sc-bg)', border: '1px solid var(--color-sc-border2)',
              borderRadius: 6, padding: '5px 8px', fontSize: 12,
              color: 'var(--color-sc-text)', outline: 'none',
            }}
          />
          <button
            onClick={() => { if (customText.trim()) { onAction('custom', customText.trim()); onClose(); } }}
            disabled={!customText.trim()}
            style={{ padding: '5px 10px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 12, background: 'var(--color-sc-gold)', color: '#0D0D0D' }}
          >
            Apply
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Version history panel ────────────────────────────────────────────────────

function VersionPanel({ doc, onRestore, onClose }) {
  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 30 }} />
      <div style={{
        position: 'absolute', top: '100%', right: 0, marginTop: 4, zIndex: 40,
        background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)',
        borderRadius: 10, width: 280, maxHeight: 340, overflowY: 'auto',
        boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
      }}>
        <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--color-sc-border)', fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Version history
        </div>
        {!doc.versions?.length && (
          <div style={{ padding: '20px 14px', fontSize: 13, color: 'var(--color-sc-text-dim)', textAlign: 'center' }}>No versions yet</div>
        )}
        {[...( doc.versions || [])].reverse().map((v, i) => (
          <button key={v.id} onClick={() => { onRestore(v.content); onClose(); }} style={{
            width: '100%', padding: '10px 14px', border: 'none', borderBottom: '1px solid var(--color-sc-border)',
            background: i === 0 ? 'rgba(196,164,74,0.06)' : 'transparent',
            cursor: 'pointer', textAlign: 'left', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.04)'}
            onMouseLeave={e => e.currentTarget.style.background = i === 0 ? 'rgba(196,164,74,0.06)' : 'transparent'}
          >
            <div>
              <div style={{ fontSize: 12.5, color: 'var(--color-sc-text)', fontWeight: i === 0 ? 600 : 400 }}>{v.label}</div>
              <div style={{ fontSize: 10.5, color: 'var(--color-sc-text-muted)', marginTop: 2 }}>{formatTs(v.timestamp)} · {v.content.length} chars</div>
            </div>
            {i === 0 && <span style={{ fontSize: 10, color: 'var(--color-sc-gold)', padding: '2px 6px', borderRadius: 6, background: 'rgba(196,164,74,0.12)' }}>Latest</span>}
          </button>
        ))}
      </div>
    </>
  );
}

// ─── Image Generation Panel ───────────────────────────────────────────────────

function ImageGenPanel({ onInsertToCanvas }) {
  const [prompt, setPrompt] = useState('');
  const [negPrompt, setNegPrompt] = useState('');
  const [size, setSize] = useState('768x768');
  const [steps, setSteps] = useState(20);
  const [showNeg, setShowNeg] = useState(false);
  const [loading, setLoading] = useState(false);
  const [warming, setWarming] = useState(false);
  const [result, setResult] = useState(null); // base64 PNG
  const [error, setError] = useState(null);

  async function generate() {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await fetch('/images/generations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim(), negative_prompt: negPrompt.trim(), size, steps: Number(steps) }),
      });
      const data = await r.json();
      if (data.warming) {
        setWarming(true);
        setError('GPU is warming up (~60–120s). Try again shortly.');
      } else if (data.error) {
        setError(data.error);
      } else if (data.data?.[0]?.b64_json) {
        setResult(data.data[0].b64_json);
        setWarming(false);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 0, overflow: 'hidden' }}>
      {/* Form */}
      <div style={{ padding: '20px 24px 16px', display: 'flex', flexDirection: 'column', gap: 10, borderBottom: '1px solid var(--color-sc-border)' }}>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) generate(); }}
          placeholder="Describe the image you want to generate…"
          rows={3}
          style={{
            background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border2)',
            borderRadius: 8, padding: '10px 12px', fontSize: 13, color: 'var(--color-sc-text)',
            resize: 'none', outline: 'none', fontFamily: 'var(--font-grotesk)', lineHeight: 1.5,
          }}
        />
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <select value={size} onChange={e => setSize(e.target.value)} style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 6, padding: '5px 8px', fontSize: 12, color: 'var(--color-sc-text)', cursor: 'pointer' }}>
            <option value="512x512">512 × 512</option>
            <option value="768x768">768 × 768</option>
            <option value="1024x1024">1024 × 1024</option>
            <option value="1024x768">1024 × 768</option>
            <option value="768x1024">768 × 1024</option>
          </select>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--color-sc-text-muted)' }}>
            <span>Steps:</span>
            <input type="number" min={10} max={50} value={steps} onChange={e => setSteps(e.target.value)} style={{ width: 50, background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border)', borderRadius: 6, padding: '4px 6px', fontSize: 12, color: 'var(--color-sc-text)', textAlign: 'center' }} />
          </div>
          <button onClick={() => setShowNeg(n => !n)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 11, color: showNeg ? 'var(--color-sc-gold)' : 'var(--color-sc-text-dim)', padding: '4px 6px' }}>
            {showNeg ? '– Negative' : '+ Negative'}
          </button>
          <button
            onClick={generate}
            disabled={loading || !prompt.trim()}
            style={{
              marginLeft: 'auto', padding: '7px 18px', borderRadius: 8, border: 'none', cursor: loading || !prompt.trim() ? 'not-allowed' : 'pointer',
              background: loading || !prompt.trim() ? 'rgba(255,255,255,0.06)' : 'var(--color-sc-gold)',
              color: loading || !prompt.trim() ? 'var(--color-sc-text-dim)' : '#0D0D0D',
              fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.15s',
            }}
          >
            {loading ? <><Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> Generating…</> : <><ImageIcon size={13} /> Generate</>}
          </button>
        </div>
        {showNeg && (
          <input
            value={negPrompt}
            onChange={e => setNegPrompt(e.target.value)}
            placeholder="Negative prompt (e.g. blurry, low quality, text)"
            style={{ background: 'var(--color-sc-surface)', border: '1px solid var(--color-sc-border2)', borderRadius: 6, padding: '7px 10px', fontSize: 12, color: 'var(--color-sc-text)', outline: 'none' }}
          />
        )}
      </div>

      {/* Result area */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, flexDirection: 'column', gap: 16 }}>
        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, color: 'var(--color-sc-text-muted)' }}>
            <Loader2 size={32} style={{ animation: 'spin 1.2s linear infinite', color: 'var(--color-sc-gold)' }} />
            <div style={{ fontSize: 13 }}>{warming ? 'GPU warming up (~60–120s)…' : 'Generating image…'}</div>
          </div>
        )}
        {error && !loading && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '12px 16px', borderRadius: 8, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', maxWidth: 420 }}>
            <AlertCircle size={16} style={{ color: '#ef4444', flexShrink: 0, marginTop: 1 }} />
            <div style={{ fontSize: 13, color: 'var(--color-sc-text)' }}>{error}</div>
          </div>
        )}
        {result && !loading && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
            <img
              src={`data:image/png;base64,${result}`}
              alt="Generated"
              style={{ maxWidth: '100%', maxHeight: 480, borderRadius: 10, border: '1px solid var(--color-sc-border)', boxShadow: '0 4px 24px rgba(0,0,0,0.35)' }}
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => {
                  const a = document.createElement('a');
                  a.href = `data:image/png;base64,${result}`;
                  a.download = 'sovereign-gen.png';
                  a.click();
                }}
                style={{ padding: '7px 16px', borderRadius: 8, border: '1px solid var(--color-sc-border)', background: 'transparent', color: 'var(--color-sc-text-muted)', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5 }}
              >
                <Download size={12} /> Save
              </button>
              {onInsertToCanvas && (
                <button
                  onClick={() => onInsertToCanvas(`<img src="data:image/png;base64,${result}" style="max-width:100%;border-radius:8px;" alt="${prompt.slice(0, 60)}" />`)}
                  style={{ padding: '7px 16px', borderRadius: 8, border: 'none', background: 'rgba(196,164,74,0.15)', color: 'var(--color-sc-gold)', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5, fontWeight: 600 }}
                >
                  <FileCode2 size={12} /> Insert to Canvas
                </button>
              )}
            </div>
          </div>
        )}
        {!result && !loading && !error && (
          <div style={{ textAlign: 'center', color: 'var(--color-sc-text-dim)', fontSize: 13 }}>
            <ImageIcon size={32} style={{ opacity: 0.12, marginBottom: 10, display: 'block', margin: '0 auto 10px' }} />
            Enter a prompt above and hit Generate
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Canvas panel (right side) ────────────────────────────────────────────────

function CanvasPanel({ doc, liveArtifact, streaming, onUpdate, onAddVersion }) {
  const [mode, setMode] = useState('preview'); // 'preview' | 'edit' | 'image'
  const [showVersions, setShowVersions] = useState(false);
  const [selection, setSelection] = useState({ start: 0, end: 0 });
  const [previewSel, setPreviewSel] = useState({ text: '', rect: null });
  const [copied, setCopied] = useState(false);
  const editorRef = useRef(null);
  const previewRef = useRef(null);

  const displayDoc = liveArtifact && streaming
    ? { ...doc, ...liveArtifact }
    : doc;

  const hasSelection = selection.end > selection.start;
  const TypeIcon = TYPE_ICONS[displayDoc?.type] || FileText;

  function copy() {
    navigator.clipboard.writeText(displayDoc?.content || '').then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); });
  }

  function download() {
    if (!doc) return;
    const blob = new Blob([doc.content], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = doc.name;
    a.click();
  }

  function handleEditorSelect(e) {
    setSelection({ start: e.target.selectionStart, end: e.target.selectionEnd });
  }

  // Preview mode: capture native text selection on mouseup
  function handlePreviewMouseUp() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) {
      setPreviewSel({ text: '', rect: null });
      return;
    }
    const text = sel.toString().trim();
    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    setPreviewSel({ text, rect });
  }

  function dispatchCanvasAction(action, customText, selected, full) {
    window.dispatchEvent(new CustomEvent('canvas-inline-fix', {
      detail: { action, customText, selected, full, type: doc?.type, language: doc?.language },
    }));
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0, background: 'var(--color-sc-bg)', position: 'relative' }}>
      {/* Canvas toolbar */}
      <div style={{ height: 46, flexShrink: 0, display: 'flex', alignItems: 'center', padding: '0 14px', gap: 8, borderBottom: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)' }}>
        {doc ? (
          <>
            <TypeIcon size={13} style={{ color: 'var(--color-sc-gold)', flexShrink: 0 }} />
            <input
              value={doc.name}
              onChange={e => onUpdate({ name: e.target.value })}
              style={{ background: 'none', border: 'none', outline: 'none', fontSize: 13, color: 'var(--color-sc-text)', fontFamily: 'var(--font-grotesk)', fontWeight: 500, flex: 1, minWidth: 0 }}
            />
            <span style={{ fontSize: 10, padding: '2px 7px', borderRadius: 8, background: 'rgba(196,164,74,0.1)', color: 'var(--color-sc-gold)', fontFamily: 'var(--font-grotesk)', textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0 }}>
              {TYPE_LABELS[displayDoc?.type] || 'Text'}
              {displayDoc?.language && displayDoc.language !== displayDoc.type && ` · ${displayDoc.language}`}
            </span>
            {streaming && <span style={{ fontSize: 10, color: 'var(--color-sc-text-dim)', animation: 'pulse 1s infinite' }}>● streaming</span>}
          </>
        ) : (
          <span style={{ fontSize: 13, color: 'var(--color-sc-text-dim)', flex: 1 }}>No document</span>
        )}

        {doc && (
          <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
            {/* Mode toggle */}
            <button onClick={() => setMode('preview')} title="Preview" style={{ padding: '5px 9px', borderRadius: 6, border: 'none', cursor: 'pointer', background: mode === 'preview' ? 'rgba(196,164,74,0.15)' : 'transparent', color: mode === 'preview' ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', display: 'flex', gap: 4, alignItems: 'center', fontSize: 11 }}>
              <Eye size={12} /> Preview
            </button>
            <button onClick={() => setMode('edit')} title="Edit" style={{ padding: '5px 9px', borderRadius: 6, border: 'none', cursor: 'pointer', background: mode === 'edit' ? 'rgba(196,164,74,0.15)' : 'transparent', color: mode === 'edit' ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', display: 'flex', gap: 4, alignItems: 'center', fontSize: 11 }}>
              <Edit3 size={12} /> Edit
            </button>
            <button onClick={() => setMode('image')} title="Generate Image" style={{ padding: '5px 9px', borderRadius: 6, border: 'none', cursor: 'pointer', background: mode === 'image' ? 'rgba(196,164,74,0.15)' : 'transparent', color: mode === 'image' ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', display: 'flex', gap: 4, alignItems: 'center', fontSize: 11 }}>
              <ImageIcon size={12} /> Image
            </button>
            {/* Actions */}
            <div style={{ width: 1, background: 'var(--color-sc-border)', margin: '4px 4px' }} />
            <div style={{ position: 'relative' }}>
              <button onClick={() => setShowVersions(v => !v)} title="Version history" style={{ padding: '5px 8px', borderRadius: 6, border: 'none', cursor: 'pointer', background: 'transparent', color: 'var(--color-sc-text-muted)', display: 'flex' }}>
                <History size={13} />
              </button>
              {showVersions && <VersionPanel doc={doc} onRestore={c => { onUpdate({ content: c }); onAddVersion(c, 'Restored'); }} onClose={() => setShowVersions(false)} />}
            </div>
            <button onClick={copy} title="Copy" style={{ padding: '5px 8px', borderRadius: 6, border: 'none', cursor: 'pointer', background: 'transparent', color: copied ? 'var(--color-sc-success)' : 'var(--color-sc-text-muted)', display: 'flex' }}>
              {copied ? <Check size={13} /> : <Copy size={13} />}
            </button>
            <button onClick={download} title="Download" style={{ padding: '5px 8px', borderRadius: 6, border: 'none', cursor: 'pointer', background: 'transparent', color: 'var(--color-sc-text-muted)', display: 'flex' }}>
              <Download size={13} />
            </button>
          </div>
        )}
      </div>

      {/* Content area */}
      {doc ? (
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', position: 'relative' }}>
          {mode === 'image' ? (
            <ImageGenPanel onInsertToCanvas={(imgTag) => onUpdate({ content: imgTag, type: 'html' })} />
          ) : mode === 'preview' ? (
            <div ref={previewRef} onMouseUp={handlePreviewMouseUp} style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <ArtifactRenderer doc={displayDoc} partial={streaming && liveArtifact?.partial} />
              {previewSel.text && previewSel.rect && (
                <SelectionPopup
                  text={previewSel.text}
                  rect={previewSel.rect}
                  streaming={streaming}
                  onAction={(action, customText) => {
                    dispatchCanvasAction(action, customText, previewSel.text, doc.content);
                  }}
                  onClose={() => { setPreviewSel({ text: '', rect: null }); window.getSelection()?.removeAllRanges(); }}
                />
              )}
            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
              <InlineToolbar
                visible={hasSelection}
                streaming={streaming}
                onAction={(action, customText) => {
                  const selected = doc.content.slice(selection.start, selection.end);
                  dispatchCanvasAction(action, customText, selected, doc.content);
                }}
              />
              <textarea
                ref={editorRef}
                value={doc.content}
                onChange={e => onUpdate({ content: e.target.value })}
                onSelect={handleEditorSelect}
                onBlur={() => { if (doc.content) onAddVersion(doc.content, 'Manual edit'); }}
                spellCheck={false}
                style={{
                  flex: 1, resize: 'none', border: 'none', outline: 'none',
                  background: 'var(--color-sc-bg)', color: 'var(--color-sc-text)',
                  fontFamily: 'var(--font-mono)', fontSize: 12.5, lineHeight: 1.7,
                  padding: '20px 24px', boxSizing: 'border-box',
                }}
              />
            </div>
          )}
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 14, color: 'var(--color-sc-text-dim)' }}>
          <FileText size={36} style={{ opacity: 0.12 }} />
          <div style={{ fontSize: 14, color: 'var(--color-sc-text-muted)' }}>No document open</div>
          <div style={{ fontSize: 13 }}>Start a conversation on the left to generate one, or create a new document.</div>
        </div>
      )}
    </div>
  );
}

// ─── Generation progress card ─────────────────────────────────────────────────

const STAGES = [
  { min: 0,    label: 'Thinking…',           color: 'var(--color-sc-text-dim)' },
  { min: 1,    label: 'Scaffolding…',        color: 'var(--color-sc-gold)' },
  { min: 80,   label: 'Writing…',            color: 'var(--color-sc-gold)' },
  { min: 300,  label: 'Expanding…',          color: '#7ec8e3' },
  { min: 800,  label: 'Finalising…',         color: '#a8d8a8' },
];

function GeneratingCard({ tokens, language, lines, done, stopped }) {
  const stage = [...STAGES].reverse().find(s => tokens >= s.min) || STAGES[0];
  const Icon = TYPE_ICONS[getType(language)] || Code2;

  if (done || stopped) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', gap: 6,
        padding: '10px 13px', borderRadius: 10,
        background: stopped ? 'rgba(255,77,109,0.07)' : 'rgba(100,200,120,0.07)',
        border: `1px solid ${stopped ? 'rgba(255,77,109,0.2)' : 'rgba(100,200,120,0.2)'}`,
        marginBottom: 12,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <Icon size={13} style={{ color: stopped ? '#FF4D6D' : '#6cc17a', flexShrink: 0 }} />
          <span style={{ fontSize: 13, fontWeight: 600, color: stopped ? '#FF4D6D' : '#6cc17a' }}>
            {stopped ? 'Stopped' : 'Complete ✓'}
          </span>
        </div>
        {lines > 0 && (
          <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
            {lines} lines{language ? ` of ${language}` : ''} · {tokens} tokens → canvas
          </span>
        )}
      </div>
    );
  }

  // Indeterminate progress bar driven by token count (caps at ~95%)
  const pct = Math.min(95, Math.round((Math.log(tokens + 1) / Math.log(1200)) * 95));

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 8,
      padding: '10px 13px', borderRadius: 10,
      background: 'rgba(196,164,74,0.06)',
      border: '1px solid rgba(196,164,74,0.18)',
      marginBottom: 12,
    }}>
      {/* Stage label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
          background: stage.color,
          boxShadow: `0 0 6px ${stage.color}`,
          animation: 'pulse 1.2s ease-in-out infinite',
        }} />
        <span style={{ fontSize: 13, color: stage.color, fontWeight: 500 }}>{stage.label}</span>
        {language && (
          <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
            {language}
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div style={{ height: 3, borderRadius: 2, background: 'rgba(255,255,255,0.07)', overflow: 'hidden' }}>
        <div style={{
          height: '100%', borderRadius: 2,
          width: `${pct}%`,
          background: `linear-gradient(90deg, var(--color-sc-gold), #e8c94a)`,
          transition: 'width 0.4s ease',
        }} />
      </div>

      {/* Stats */}
      <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>
        {tokens} tokens · {lines} lines
      </span>
    </div>
  );
}



function ChatBubble({ msg, onExtract, isStreaming }) {
  const isUser = msg.role === 'user';
  const artifact = !isUser ? extractLiveArtifact(msg.content) : null;
  const hasArtifact = artifact?.content?.length > 20;
  // Show prose only; if purely code show a canvas pill
  const displayText = isUser ? msg.content : getChatDisplayText(msg.content);
  const pureArtifact = !isUser && hasArtifact && !displayText;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start', marginBottom: 12 }}>
      {/* Prose bubble — show for user always, for assistant only when there's prose */}
      {(isUser || displayText || (!hasArtifact && !isStreaming)) && (
        <div style={{
          maxWidth: '88%', padding: '9px 13px', borderRadius: isUser ? '12px 12px 4px 12px' : '4px 12px 12px 12px',
          background: isUser ? 'rgba(196,164,74,0.14)' : 'var(--color-sc-surface)',
          border: `1px solid ${isUser ? 'rgba(196,164,74,0.25)' : 'var(--color-sc-border)'}`,
          fontSize: 13, color: 'var(--color-sc-text)', lineHeight: 1.6,
        }}>
          {displayText || (!isUser && isStreaming
            ? <span style={{ color: 'var(--color-sc-text-dim)', fontStyle: 'italic' }}>…</span>
            : displayText)}
        </div>
      )}
      {/* Canvas pill — shown for assistant when artifact is ready */}
      {pureArtifact && !isStreaming && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '6px 11px', borderRadius: 8,
          background: 'rgba(196,164,74,0.08)', border: '1px solid rgba(196,164,74,0.2)',
        }}>
          <FileCode2 size={12} style={{ color: 'var(--color-sc-gold)' }} />
          <span style={{ fontSize: 12, color: 'var(--color-sc-text-muted)' }}>
            {TYPE_LABELS[artifact.type] || 'Artifact'}{artifact.language && artifact.language !== artifact.type ? ` · ${artifact.language}` : ''} sent to canvas
          </span>
        </div>
      )}
      {/* Streaming indicator while artifact is building */}
      {!isUser && isStreaming && hasArtifact && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px', borderRadius: 7, background: 'rgba(196,164,74,0.06)', border: '1px solid rgba(196,164,74,0.15)' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-sc-gold)', animation: 'pulse 1s infinite', display: 'inline-block' }} />
          <span style={{ fontSize: 12, color: 'var(--color-sc-text-dim)' }}>Writing to canvas…</span>
        </div>
      )}
    </div>
  );
}

// ─── Canvas Chat Panel (left side) ───────────────────────────────────────────

function CanvasChatPanel({ activeDoc, onLiveArtifact, onCommitArtifact, streaming, setStreaming, docId, pendingPrompt, onPromptConsumed }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [webSearch, setWebSearch] = useState(false);
  const activeModel = useSCStore(s => s.activeModel);
  const canvasChatHistories = useSCStore(s => s.canvasChatHistories);
  const setCanvasChatHistory = useSCStore(s => s.setCanvasChatHistory);
  const abortRef = useRef(null);
  const bottomRef = useRef(null);
  const prevDocIdRef = useRef(null);

  // Switch chat history when docId changes
  useEffect(() => {
    const prevId = prevDocIdRef.current;

    // Save current messages for the previous doc before switching
    if (prevId && prevId !== docId) {
      setCanvasChatHistory(prevId, useSCStore.getState().canvasChatHistories[prevId] ?? []);
    }

    // Load history for the new doc (or empty if none)
    const history = docId ? (canvasChatHistories[docId] ?? []) : [];
    setMessages(history);
    setInput('');

    prevDocIdRef.current = docId;
  }, [docId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Save messages to store whenever they change
  useEffect(() => {
    if (docId) setCanvasChatHistory(docId, messages);
  }, [messages]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-send a pending prompt (triggered from main chat "create" dispatch)
  useEffect(() => {
    if (!pendingPrompt) return;
    // Small delay to let React finish the docId transition and settle state
    const t = setTimeout(() => {
      if (!streaming) {
        sendMessage(pendingPrompt);
        onPromptConsumed?.();
      }
    }, 300);
    return () => clearTimeout(t);
  // Only fire when pendingPrompt changes and is non-null
  }, [pendingPrompt]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Listen for inline fix events from the canvas panel
  useEffect(() => {
    function handleInlineFix(e) {
      const { action, customText, selected, full, type, language } = e.detail;
      const lang = language || type || 'text';
      const hasSelection = selected && selected.trim();

      // Always return the FULL document so onCommitArtifact replaces content cleanly
      const fullContext = full
        ? `\n\nFull document:\n\`\`\`${lang}\n${full.slice(0, 3000)}\n\`\`\``
        : '';

      const selectionBlock = hasSelection
        ? `\n\nSelected text:\n\`\`\`${lang}\n${selected}\n\`\`\``
        : '';

      const prompts = {
        fix:
          `Fix any bugs, errors, or issues in the selected ${lang} text below. Apply the fix in place and return the COMPLETE updated document (not just the selection).${selectionBlock}${fullContext}`,
        improve:
          `Improve and enhance the selected ${lang} text. Apply the improvement in place and return the COMPLETE updated document.${selectionBlock}${fullContext}`,
        simplify:
          `Simplify the selected ${lang} text while preserving its meaning. Apply the simplification in place and return the COMPLETE updated document.${selectionBlock}${fullContext}`,
        explain:
          `Explain what the selected text does, then show an improved version. Return the COMPLETE updated document with your improvements applied.${selectionBlock}${fullContext}`,
        rewrite_all:
          hasSelection
            ? `Using the selected text as context for what needs to change, rewrite the ENTIRE document accordingly. Return the full rewritten document.${selectionBlock}${fullContext}`
            : `Rewrite the entire document to improve quality, clarity, and correctness. Return the full rewritten document.${fullContext}`,
        custom:
          hasSelection
            ? `User instruction: "${customText}"\n\nApply this to the selected text in place and return the COMPLETE updated document.${selectionBlock}${fullContext}`
            : `User instruction: "${customText}"\n\nApply this to the document and return the COMPLETE updated document.${fullContext}`,
      };

      const prompt = prompts[action];
      if (prompt) sendMessage(prompt);
    }
    window.addEventListener('canvas-inline-fix', handleInlineFix);
    return () => window.removeEventListener('canvas-inline-fix', handleInlineFix);
  }, [messages, activeModel]);

  async function sendMessage(text) {
    const userMsg = text || input.trim();
    if (!userMsg || streaming) return;
    setInput('');

    // Optional web search context injection
    let searchContext = '';
    if (webSearch) {
      try {
        const sr = await fetch(`/search?q=${encodeURIComponent(userMsg)}`);
        const sd = await sr.json();
        if (sd.results?.length) {
          searchContext = '\n\nWeb search results:\n' + sd.results.map((r, i) =>
            `[${i+1}] ${r.title}: ${r.snippet} (${r.url})`
          ).join('\n');
        }
      } catch { /* non-fatal */ }
    }

    const contextSystem = (activeDoc?.content
      ? `${CANVAS_SYSTEM}\n\nCurrent document (${activeDoc.type}, ${activeDoc.language}):\n\`\`\`${activeDoc.language}\n${activeDoc.content.slice(0, 2000)}\n\`\`\``
      : CANVAS_SYSTEM) + searchContext;

    const history = messages.slice(-12);
    const payload = {
      model: activeModel || 'mavaia-alpha',
      stream: true,
      max_tokens: 32768,
      messages: [
        { role: 'system', content: contextSystem },
        ...history.map(m => ({ role: m.role, content: m.content })),
        { role: 'user', content: userMsg },
      ],
    };

    // Append user msg + a lightweight generation-card placeholder (no raw code in state)
    setMessages(prev => [...prev,
      { role: 'user', content: userMsg },
      { role: 'assistant', _gen: { tokens: 0, lines: 0, language: null, done: false, stopped: false } },
    ]);
    setStreaming(true);
    onLiveArtifact(null);

    const controller = new AbortController();
    abortRef.current = controller;

    let buffer = '';
    let done = false;
    let tokenCount = 0;
    try {
      const res = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal: controller.signal });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      while (!done) {
        const { done: streamDone, value } = await reader.read();
        if (streamDone) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data:')) continue;
          const data = line.slice(5).trim();
          if (data === '[DONE]') { done = true; break; }
          try {
            const delta = JSON.parse(data)?.choices?.[0]?.delta?.content;
            if (delta) {
              buffer += delta;
              tokenCount++;
              // Update canvas preview on every token
              const live = extractLiveArtifact(buffer);
              if (live) onLiveArtifact(live);
              // Update card metadata cheaply — no raw code in state
              const lineCount = buffer.split('\n').length;
              const lang = live?.language || null;
              setMessages(prev => prev.map((m, i) =>
                i === prev.length - 1
                  ? { ...m, _gen: { tokens: tokenCount, lines: lineCount, language: lang, done: false, stopped: false } }
                  : m
              ));
            }
          } catch { /* skip malformed */ }
        }
      }
    } catch (err) {
      const stopped = err.name === 'AbortError';
      setMessages(prev => prev.map((m, i) =>
        i === prev.length - 1
          ? { ...m, _gen: { tokens: tokenCount, lines: buffer.split('\n').length, language: extractLiveArtifact(buffer)?.language || null, done: !stopped, stopped } }
          : m
      ));
      if (!stopped && !buffer) {
        setMessages(prev => prev.filter((_, i) => i < prev.length - 1));
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      if (buffer) {
        const artifact = extractLiveArtifact(buffer);
        if (artifact) {
          onCommitArtifact(artifact, buffer);
          // Mark card done
          setMessages(prev => prev.map((m, i) =>
            i === prev.length - 1 && m._gen
              ? { ...m, _gen: { ...m._gen, done: true } }
              : m
          ));
        }
      }
    }
  }

  function stop() { abortRef.current?.abort(); setStreaming(false); }

  return (
    <div style={{ width: 340, flexShrink: 0, display: 'flex', flexDirection: 'column', borderRight: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ height: 46, flexShrink: 0, display: 'flex', alignItems: 'center', padding: '0 16px', borderBottom: '1px solid var(--color-sc-border)', gap: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-sc-text)', fontFamily: 'var(--font-grotesk)', flex: 1 }}>AI Chat</span>
        <button
          onClick={() => setWebSearch(w => !w)}
          title={webSearch ? 'Web search ON — click to disable' : 'Enable web search for grounded context'}
          style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '4px 9px', borderRadius: 7, border: 'none',
            cursor: 'pointer', fontSize: 11, fontFamily: 'var(--font-inter)',
            background: webSearch ? 'rgba(196,164,74,0.14)' : 'rgba(255,255,255,0.05)',
            color: webSearch ? 'var(--color-sc-gold)' : 'var(--color-sc-text-dim)',
            transition: 'all 0.15s',
          }}
        >
          <Globe size={11} />
          {webSearch ? 'Web: On' : 'Web: Off'}
        </button>
        <span style={{ fontSize: 11, color: 'var(--color-sc-text-dim)' }}>→ canvas</span>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 14px' }}>
        {messages.length === 0 && (
          <div style={{ padding: '40px 12px', textAlign: 'center', color: 'var(--color-sc-text-dim)', fontSize: 13, lineHeight: 1.7 }}>
            Ask me to write code, generate docs, create diagrams, or produce any structured content — it appears live in the canvas.
          </div>
        )}
        {messages.map((m, i) => (
          m._gen
            ? <GeneratingCard key={i} {...m._gen} />
            : <ChatBubble key={i} msg={m} isStreaming={streaming && i === messages.length - 1} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ padding: '10px 12px', borderTop: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)' }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', background: 'var(--color-sc-surface2)', border: '1px solid var(--color-sc-border2)', borderRadius: 10, padding: '8px 10px' }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder="Write a Go HTTP handler… Shift+Enter for newline"
            rows={2}
            style={{ flex: 1, background: 'none', border: 'none', outline: 'none', resize: 'none', fontSize: 13, color: 'var(--color-sc-text)', fontFamily: 'var(--font-inter)', lineHeight: 1.5 }}
          />
          <button
            onClick={streaming ? stop : () => sendMessage()}
            style={{ padding: '7px 10px', borderRadius: 8, border: 'none', cursor: 'pointer', background: streaming ? 'rgba(255,77,109,0.15)' : (input.trim() ? 'var(--color-sc-gold)' : 'rgba(255,255,255,0.06)'), color: streaming ? '#FF4D6D' : (input.trim() ? '#0D0D0D' : 'var(--color-sc-text-dim)'), display: 'flex', flexShrink: 0 }}
          >
            {streaming ? <Square size={14} /> : <Send size={14} />}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function ArtifactsCanvas() {
  const canvasDocuments      = useSCStore(s => s.canvasDocuments);
  const activeCanvasDocId    = useSCStore(s => s.activeCanvasDocId);
  const addCanvasDoc         = useSCStore(s => s.addCanvasDoc);
  const updateCanvasDoc      = useSCStore(s => s.updateCanvasDoc);
  const deleteCanvasDoc      = useSCStore(s => s.deleteCanvasDoc);
  const setActiveCanvasDocId = useSCStore(s => s.setActiveCanvasDocId);
  const addCanvasVersion     = useSCStore(s => s.addCanvasVersion);
  const pendingCanvasPrompt  = useSCStore(s => s.pendingCanvasPrompt);
  const clearPendingCanvasPrompt = useSCStore(s => s.clearPendingCanvasPrompt);

  const [liveArtifact, setLiveArtifact] = useState(null);
  const [streaming, setStreaming] = useState(false);
  // Passed down to CanvasChatPanel — consumed once then cleared
  const [activePrompt, setActivePrompt] = useState(null);

  const activeDoc = canvasDocuments.find(d => d.id === activeCanvasDocId) ?? null;

  // When a "create" dispatch arrives from the main chat, open a fresh doc
  // and relay the prompt to the canvas chat
  useEffect(() => {
    if (!pendingCanvasPrompt) return;
    addCanvasDoc({ name: 'Untitled', type: 'markdown', language: 'markdown', content: '' });
    setActivePrompt(pendingCanvasPrompt);
    clearPendingCanvasPrompt();
  }, [pendingCanvasPrompt]); // eslint-disable-line react-hooks/exhaustive-deps

  function createNewDoc() {
    addCanvasDoc({ name: 'Untitled', type: 'markdown', language: 'markdown', content: '' });
  }

  function handleCommitArtifact(artifact, rawText) {
    // Always read fresh state to avoid stale closure — activeDoc can change between
    // when sendMessage was called and when the async stream finally completes.
    const freshId = useSCStore.getState().activeCanvasDocId;
    const name = detectNameFromContent(artifact.content, artifact.language,
      useSCStore.getState().canvasDocuments.find(d => d.id === freshId)?.name);
    if (freshId) {
      useSCStore.getState().updateCanvasDoc(freshId, { ...artifact, name });
      useSCStore.getState().addCanvasVersion(freshId, artifact.content, 'AI generated');
    } else {
      useSCStore.getState().addCanvasDoc({ ...artifact, name });
    }
    setLiveArtifact(null);
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--color-sc-bg)' }}>
      {/* Document tabs bar */}
      <div style={{
        height: 40, flexShrink: 0, display: 'flex', alignItems: 'stretch',
        borderBottom: '1px solid var(--color-sc-border)', background: 'var(--color-sc-surface)',
        overflowX: 'auto', overflowY: 'hidden',
      }}>
        {canvasDocuments.map(doc => {
          const active = doc.id === activeCanvasDocId;
          const TypeIcon = TYPE_ICONS[doc.type] || FileText;
          return (
            <div key={doc.id} onClick={() => setActiveCanvasDocId(doc.id)} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '0 12px 0 10px',
              borderRight: '1px solid var(--color-sc-border)', cursor: 'pointer', flexShrink: 0,
              background: active ? 'var(--color-sc-bg)' : 'transparent',
              borderBottom: active ? '2px solid var(--color-sc-gold)' : '2px solid transparent',
              transition: 'background 0.12s',
              position: 'relative',
            }}>
              <TypeIcon size={12} style={{ color: active ? 'var(--color-sc-gold)' : 'var(--color-sc-text-muted)', flexShrink: 0 }} />
              <span style={{ fontSize: 12.5, color: active ? 'var(--color-sc-text)' : 'var(--color-sc-text-muted)', fontFamily: 'var(--font-inter)', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {doc.name}
              </span>
              <button onClick={e => { e.stopPropagation(); deleteCanvasDoc(doc.id); }} style={{
                background: 'none', border: 'none', cursor: 'pointer', padding: '1px', display: 'flex',
                color: 'var(--color-sc-text-dim)', opacity: 0, transition: 'opacity 0.12s', borderRadius: 3,
              }}
                onMouseEnter={e => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.color = 'var(--color-sc-danger)'; }}
                onMouseLeave={e => { e.currentTarget.style.opacity = '0'; e.currentTarget.style.color = 'var(--color-sc-text-dim)'; }}
              >
                <X size={11} />
              </button>
            </div>
          );
        })}

        <button onClick={createNewDoc} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', width: 40,
          border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--color-sc-text-muted)',
          borderRight: '1px solid var(--color-sc-border)', flexShrink: 0,
        }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'var(--color-sc-gold)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-sc-text-muted)'; }}
          title="New document"
        >
          <Plus size={14} />
        </button>

        <div style={{ flex: 1 }} />

        {/* Canvas label */}
        <div style={{ display: 'flex', alignItems: 'center', padding: '0 16px', gap: 6, color: 'var(--color-sc-text-dim)', fontSize: 11, fontFamily: 'var(--font-grotesk)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: streaming ? 'var(--color-sc-success)' : 'var(--color-sc-border)', display: 'inline-block' }} />
          Artifact Canvas
        </div>
      </div>

      {/* Split body */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <CanvasChatPanel
          activeDoc={activeDoc}
          docId={activeCanvasDocId}
          pendingPrompt={activePrompt}
          onPromptConsumed={() => setActivePrompt(null)}
          onLiveArtifact={setLiveArtifact}
          onCommitArtifact={handleCommitArtifact}
          streaming={streaming}
          setStreaming={setStreaming}
        />
        <CanvasPanel
          doc={activeDoc}
          liveArtifact={liveArtifact}
          streaming={streaming}
          onUpdate={patch => activeDoc && updateCanvasDoc(activeDoc.id, patch)}
          onAddVersion={(content, label) => activeDoc && addCanvasVersion(activeDoc.id, content, label)}
        />
      </div>
    </div>
  );
}
