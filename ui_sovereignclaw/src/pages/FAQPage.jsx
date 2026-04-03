import { useState, useRef, useEffect } from 'react';
import { ChevronDown, MessageCircle, Send, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// ── FAQ content (also used as RAG context) ────────────────────────────────────
export const FAQ_SECTIONS = [
  {
    section: 'Privacy & Data',
    items: [
      {
        q: 'Is my data actually private?',
        a: 'Yes — completely. Your conversations, documents, and business data are processed on private infrastructure that is not shared with any other customer or third party. We never use your data to train models. Nothing leaves the environment your account runs in.',
      },
      {
        q: 'How is this different from ChatGPT or Claude?',
        a: 'ChatGPT and Claude run on shared infrastructure — your conversations may be reviewed by humans and can be used to improve their models (depending on your plan and settings). ORI Studio processes your data in a dedicated private environment. Your inputs never touch a shared model pipeline.',
      },
      {
        q: "Can OpenAI or Anthropic see what I'm asking?",
        a: "No. ORI Studio doesn't use OpenAI or Anthropic's APIs under the hood. Your requests go to our own models running on our own infrastructure. There's no data path to any third-party AI provider.",
      },
      {
        q: 'Where is my data stored?',
        a: 'Data is stored on our infrastructure. We do not sell, share, or transfer your data to third parties. You can request full data deletion at any time by contacting support.',
      },
    ],
  },
  {
    section: 'Email Interface',
    items: [
      {
        q: 'Wait — I can actually run automations by email?',
        a: "Yes. That's the whole point. Email ORI a command, it runs the workflow, and emails you back with the results. No app to open, no dashboard to navigate. You already know how to use email — that's the interface.",
      },
      {
        q: 'What commands can I send?',
        a: 'Send LIST to see your available workflows. RUN <workflow name> to trigger one (e.g. "RUN Weekly Report"). STATUS to check what\'s running. STOP <id> to cancel a run. You can also include variables in the email body as key: value pairs to pass data into a workflow.',
      },
      {
        q: 'What is the daily briefing?',
        a: "Every morning, ORI emails you a summary of what happened overnight: completed runs, pending approvals, what's scheduled for today, and quick commands to act on anything. You wake up informed and in control — without opening a single app.",
      },
      {
        q: 'Can I approve or reject a workflow run by email?',
        a: 'Yes. For workflows that require human sign-off, ORI emails you a summary and waits. Reply APPROVE (or YES) to let it proceed, or REJECT (or NO) to cancel. The whole approval loop is just email.',
      },
      {
        q: 'What email address do I send commands to?',
        a: 'Once your workspace is set up, you send commands to ori@inbound.thynaptic.com. ORI replies from ori@thynaptic.com. Just hit reply — the thread context is preserved automatically.',
      },
    ],
  },
  {
    section: 'Setup & Integration',
    items: [
      {
        q: 'Do I need a developer to set this up?',
        a: "No — not at all. Sign up, set up your workspace, and start emailing ORI. That's it. If you want to integrate ORI Studio into your own tools via API, our OpenAI-compatible endpoint means any developer can do it in minutes with no rewrite.",
      },
      {
        q: "Is it really OpenAI-compatible? Do I need to rewrite my code?",
        a: "Yes, truly compatible. Change your base URL from api.openai.com to our endpoint and update your API key. That's it. Your existing OpenAI code — completions, chat, function calling — works as-is.",
      },
      {
        q: 'How long does setup take?',
        a: "Under 5 minutes to be sending email commands to ORI. Sign up, we register your email as an authorized client, and you're live. No installs, no config files, no dashboards to learn.",
      },
      {
        q: 'Can I connect ORI Studio to Slack, Notion, Zapier, or other tools?',
        a: 'Yes. Because ORI Studio is OpenAI-compatible, any tool that supports a custom OpenAI endpoint works out of the box. We also support webhook triggers and direct API integration for custom connections.',
      },
    ],
  },
  {
    section: 'Pricing & Plans',
    items: [
      {
        q: 'Is there really no per-message fee?',
        a: "Correct — no per-message, per-token, or per-API-call charges. You pay one flat monthly fee based on your plan (Solo $29, Team $99, Business $249) and your team can send unlimited messages. No surprise bills at month-end.",
      },
      {
        q: 'What happens if I cancel?',
        a: 'You can cancel anytime. Your account stays active until the end of your billing period. After that, your access ends and we retain your data for 30 days in case you want to re-activate, then it\'s deleted.',
      },
      {
        q: 'Is there a free trial?',
        a: 'Yes — 14 days free, no credit card required. You get full access to your plan features during the trial.',
      },
      {
        q: 'What counts as a "user" for Team and Business plans?',
        a: 'A user is anyone on your team who accesses ORI Studio — either through the chat interface or via API with a user-scoped key. Admin users who only manage billing or settings do not count toward your seat limit.',
      },
    ],
  },
  {
    section: 'Capabilities',
    items: [
      {
        q: 'What can ORI Studio actually do?',
        a: "The short version: run your business workflows over email. Send a command, get results back. No app. Beyond that: answer questions, draft content, summarize documents, analyze data, and automate repetitive tasks — all grounded in your business knowledge. On Team and Business plans you also get custom workflows, memory across sessions, approval loops, and a daily briefing delivered to your inbox every morning.",
      },
      {
        q: 'What if the AI gives a wrong answer?',
        a: "Like any AI, ORI Studio can make mistakes. For factual or business-critical decisions, treat AI output as a first draft to be reviewed, not a final answer. You can improve accuracy by uploading your own knowledge base — the more context ORI has about your business, the better its answers.",
      },
      {
        q: 'Can I customize the AI\'s persona and tone?',
        a: "Yes — on Team and Business plans you can define a custom persona: name, role, tone, and a set of instructions that shape every response. Your AI can sound like a member of your team, not a generic chatbot.",
      },
    ],
  },
];

// Flatten all Q&As for RAG context
const FAQ_CONTEXT = FAQ_SECTIONS.flatMap(s =>
  s.items.map(i => `Q: ${i.q}\nA: ${i.a}`)
).join('\n\n');

const SYSTEM_PROMPT = `You are Ori, ORI Studio's embedded support assistant. ORI Studio is a private, sovereign AI platform for SMB teams. The core product is an email command interface — users email ORI to trigger workflows and get results back, with no app or dashboard required. It's also OpenAI-compatible (one API key swap), flat monthly pricing, and data never leaves their infrastructure.

Answer questions using ONLY the FAQ knowledge below. Be direct, friendly, and specific. Do NOT invent features or pricing. If a question isn't covered, say: "That's not something I have details on — email support@thynaptic.com and we'll get back to you fast."

Do NOT use numbered lists unless the user explicitly asks for steps. Keep responses to 2-3 sentences max. No filler phrases like "Great question!" or "Certainly!".

FAQ KNOWLEDGE:
${FAQ_CONTEXT}`;

// ── Ask Oricli widget ─────────────────────────────────────────────────────────
export function AskOricliWidget({ compact = false }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamContent, setStreamContent] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, streamContent]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    const userMsg = { role: 'user', content: text };
    const next = [...messages, userMsg];
    setMessages(next);
    setLoading(true);
    setStreamContent('');

    let accumulated = '';

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'default',
          messages: [{ role: 'system', content: SYSTEM_PROMPT }, ...next],
          stream: true,
        }),
      });

      if (!res.ok || !res.body) throw new Error('bad response');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop();
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (raw === '[DONE]') break;
          try {
            const chunk = JSON.parse(raw);
            const delta = chunk.choices?.[0]?.delta?.content ?? '';
            accumulated += delta;
            setStreamContent(accumulated);
          } catch { /* ignore malformed chunks */ }
        }
      }

      const finalContent = accumulated || "I'm having trouble answering that right now. Please try again or email support@thynaptic.com.";
      setMessages(m => [...m, { role: 'assistant', content: finalContent }]);
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: "Something went wrong. Please try again or email support@thynaptic.com." }]);
    } finally {
      setLoading(false);
      setStreamContent('');
    }
  };

  const containerStyle = compact ? {
    display: 'flex', flexDirection: 'column', height: '100%',
  } : {
    background: 'rgba(136,117,255,0.04)',
    border: '1px solid rgba(136,117,255,0.18)',
    borderRadius: 16, overflow: 'hidden',
    display: 'flex', flexDirection: 'column',
  };

  return (
    <div style={containerStyle}>
      <style>{`
        @keyframes faqDot {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
          40%            { transform: scale(1);   opacity: 1;   }
        }
        @keyframes faqCursor {
          0%, 100% { opacity: 1; }
          50%      { opacity: 0; }
        }
      `}</style>
      {!compact && (
        <div style={{
          padding: '20px 24px 16px',
          borderBottom: '1px solid rgba(136,117,255,0.12)',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <MessageCircle size={18} color="#8875FF" />
          <div>
            <div style={{ fontFamily: 'system-ui,-apple-system,sans-serif', fontSize: 15, fontWeight: 700, color: '#F0ECF0' }}>
              Ask Oricli
            </div>
            <div style={{ fontFamily: "'SF Mono','Fira Code',monospace", fontSize: 9, color: 'rgba(136,117,255,0.6)', letterSpacing: '0.12em' }}>
              POWERED BY ORI STUDIO · LIVE DEMO
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: compact ? '12px 16px' : '20px 24px',
        display: 'flex', flexDirection: 'column', gap: 14,
        minHeight: compact ? 0 : 200, maxHeight: compact ? 'none' : 320,
      }}>
        {messages.length === 0 && (
          <div style={{
            color: 'rgba(240,236,240,0.35)', fontSize: 13,
            fontStyle: 'italic', textAlign: 'center', marginTop: 20,
          }}>
            Ask anything about ORI Studio — pricing, privacy, setup...
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            display: 'flex',
            justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            <div style={{
              maxWidth: '85%',
              background: m.role === 'user' ? '#8875FF' : 'rgba(255,255,255,0.05)',
              border: m.role === 'assistant' ? '1px solid rgba(136,117,255,0.15)' : 'none',
              borderRadius: m.role === 'user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
              padding: '10px 14px',
              fontSize: 13, lineHeight: 1.65,
              color: m.role === 'user' ? '#FFF' : 'rgba(240,236,240,0.8)',
            }}>
              {m.role === 'assistant' ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p: ({ children }) => <p style={{ margin: '0 0 6px', lineHeight: 1.65 }}>{children}</p>,
                    strong: ({ children }) => <strong style={{ color: '#C4B9FF', fontWeight: 600 }}>{children}</strong>,
                    code: ({ children }) => <code style={{ background: 'rgba(136,117,255,0.15)', padding: '1px 5px', borderRadius: 3, fontSize: 12, fontFamily: "'SF Mono','Fira Code',monospace" }}>{children}</code>,
                    ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: 18 }}>{children}</ul>,
                    ol: ({ children }) => <ol style={{ margin: '4px 0', paddingLeft: 18 }}>{children}</ol>,
                    li: ({ children }) => <li style={{ marginBottom: 3 }}>{children}</li>,
                    a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#8875FF', textDecoration: 'underline' }}>{children}</a>,
                  }}
                >
                  {m.content}
                </ReactMarkdown>
              ) : m.content}
            </div>
          </div>
        ))}

        {/* Live streaming bubble */}
        {loading && streamContent && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              maxWidth: '85%',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(136,117,255,0.15)',
              borderRadius: '12px 12px 12px 4px',
              padding: '10px 14px',
              fontSize: 13, lineHeight: 1.65,
              color: 'rgba(240,236,240,0.8)',
            }}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => <p style={{ margin: '0 0 6px', lineHeight: 1.65 }}>{children}</p>,
                  strong: ({ children }) => <strong style={{ color: '#C4B9FF', fontWeight: 600 }}>{children}</strong>,
                  code: ({ children }) => <code style={{ background: 'rgba(136,117,255,0.15)', padding: '1px 5px', borderRadius: 3, fontSize: 12, fontFamily: "'SF Mono','Fira Code',monospace" }}>{children}</code>,
                  ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: 18 }}>{children}</ul>,
                  ol: ({ children }) => <ol style={{ margin: '4px 0', paddingLeft: 18 }}>{children}</ol>,
                  li: ({ children }) => <li style={{ marginBottom: 3 }}>{children}</li>,
                  a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#8875FF', textDecoration: 'underline' }}>{children}</a>,
                }}
              >
                {streamContent}
              </ReactMarkdown>
              <span style={{ display: 'inline-block', width: 2, height: '1em', background: 'rgba(136,117,255,0.8)', marginLeft: 2, verticalAlign: 'text-bottom', animation: 'faqCursor 0.8s ease-in-out infinite' }} />
            </div>
          </div>
        )}

        {/* Waiting dots — shown before first token */}
        {loading && !streamContent && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(136,117,255,0.15)',
              borderRadius: '12px 12px 12px 4px',
              padding: '10px 14px',
              display: 'flex', gap: 5, alignItems: 'center',
            }}>
              {[0,1,2].map(i => (
                <div key={i} style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: 'rgba(136,117,255,0.6)',
                  animation: `faqDot 1.2s ease-in-out ${i * 0.2}s infinite`,
                }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: compact ? '10px 12px' : '14px 24px',
        borderTop: '1px solid rgba(136,117,255,0.10)',
        display: 'flex', gap: 10, alignItems: 'center',
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask a question..."
          style={{
            flex: 1, background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(136,117,255,0.20)',
            borderRadius: 8, padding: '9px 14px',
            fontSize: 13, color: '#F0ECF0', outline: 'none',
            fontFamily: 'system-ui,-apple-system,sans-serif',
          }}
          onFocus={e => e.target.style.borderColor = 'rgba(136,117,255,0.50)'}
          onBlur={e => e.target.style.borderColor = 'rgba(136,117,255,0.20)'}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          style={{
            width: 36, height: 36, borderRadius: 8,
            background: input.trim() ? '#8875FF' : 'rgba(136,117,255,0.15)',
            border: 'none', cursor: input.trim() ? 'pointer' : 'default',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'background 0.15s',
          }}
        >
          <Send size={15} color={input.trim() ? '#FFF' : 'rgba(136,117,255,0.4)'} />
        </button>
      </div>
    </div>
  );
}

// ── Accordion item ────────────────────────────────────────────────────────────
function AccordionItem({ q, a, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{
      borderBottom: '1px solid rgba(136,117,255,0.10)',
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', background: 'none', border: 'none', cursor: 'pointer',
          padding: '18px 0', display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', gap: 16, textAlign: 'left',
        }}
      >
        <span style={{
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 15, fontWeight: 600, color: '#F0ECF0', lineHeight: 1.4,
        }}>{q}</span>
        <ChevronDown
          size={16}
          color="rgba(136,117,255,0.6)"
          style={{
            flexShrink: 0,
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease',
          }}
        />
      </button>
      <div style={{
        overflow: 'hidden',
        maxHeight: open ? 400 : 0,
        transition: 'max-height 0.3s ease',
      }}>
        <p style={{
          fontSize: 14, lineHeight: 1.8,
          color: 'rgba(240,236,240,0.55)', margin: '0 0 18px',
          paddingRight: 24,
        }}>{a}</p>
      </div>
    </div>
  );
}

// ── Full FAQ page ─────────────────────────────────────────────────────────────
export default function FAQPage() {
  const navigate = useNavigate();

  return (
    <div style={{ background: '#040208', color: '#F0ECF0', minHeight: '100vh' }}>
      <style>{`
        @keyframes faqDot {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
          40%            { transform: scale(1);   opacity: 1;   }
        }
      `}</style>

      {/* Nav */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 100,
        height: 56, display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', padding: '0 32px',
        background: 'rgba(4,2,8,0.85)', backdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(136,117,255,0.10)',
      }}>
        <button
          onClick={() => navigate('/')}
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            background: 'none', border: 'none', cursor: 'pointer',
          }}
        >
          <img src="/ori-mark.png" alt="ORI" style={{ width: 22, height: 22, objectFit: 'contain' }} />
          <span style={{
            fontFamily: "'SF Mono','Fira Code',monospace",
            fontSize: 12, fontWeight: 700, color: '#F0ECF0', letterSpacing: '0.14em',
          }}>ORI STUDIO</span>
        </button>
        <button
          onClick={() => navigate('/')}
          style={{
            fontFamily: "'SF Mono','Fira Code',monospace",
            fontSize: 10, letterSpacing: '0.12em',
            color: 'rgba(240,236,240,0.5)', background: 'transparent',
            border: '1px solid rgba(255,255,255,0.10)',
            borderRadius: 6, padding: '6px 14px', cursor: 'pointer',
            transition: 'color 0.2s, border-color 0.2s',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = '#F0ECF0'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.25)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'rgba(240,236,240,0.5)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.10)'; }}
        >← BACK</button>
      </nav>

      <div style={{ maxWidth: 1040, margin: '0 auto', padding: '72px 32px 120px' }}>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 80 }}>
          <div style={{
            fontFamily: "'SF Mono','Fira Code',monospace",
            fontSize: 10, letterSpacing: '0.26em', color: 'rgba(136,117,255,0.65)',
            marginBottom: 16, fontWeight: 500,
          }}>HELP & SUPPORT</div>
          <h1 style={{
            fontFamily: 'system-ui,-apple-system,sans-serif',
            fontSize: 'clamp(32px,5vw,52px)', fontWeight: 800,
            color: '#F0ECF0', margin: '0 0 16px', letterSpacing: '-0.02em',
          }}>Frequently asked questions</h1>
          <p style={{ fontSize: 16, color: 'rgba(240,236,240,0.45)', margin: 0 }}>
            Can't find what you need? Ask Oricli below — or email us at{' '}
            <a href="mailto:support@thynaptic.com" style={{ color: '#8875FF', textDecoration: 'none' }}>
              support@thynaptic.com
            </a>
          </p>
        </div>

        {/* Two-column layout: FAQ left, Ask Oricli right */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 48, alignItems: 'start' }}>

          {/* FAQ accordion */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 48 }}>
            {FAQ_SECTIONS.map((section, si) => (
              <div key={si}>
                <div style={{
                  fontFamily: "'SF Mono','Fira Code',monospace",
                  fontSize: 10, letterSpacing: '0.2em', color: 'rgba(136,117,255,0.65)',
                  marginBottom: 8, fontWeight: 600,
                }}>{section.section.toUpperCase()}</div>
                <div style={{ borderTop: '1px solid rgba(136,117,255,0.10)' }}>
                  {section.items.map((item, ii) => (
                    <AccordionItem key={ii} q={item.q} a={item.a} defaultOpen={si === 0 && ii === 0} />
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Ask Oricli — sticky */}
          <div style={{ position: 'sticky', top: 72 }}>
            <div style={{ marginBottom: 16 }}>
              <div style={{
                fontFamily: "'SF Mono','Fira Code',monospace",
                fontSize: 10, letterSpacing: '0.2em', color: 'rgba(136,117,255,0.65)',
                marginBottom: 8, fontWeight: 600,
              }}>ASK ORICLI</div>
              <p style={{ fontSize: 13, color: 'rgba(240,236,240,0.4)', margin: 0, lineHeight: 1.6 }}>
                Get instant answers from our AI — this is ORI Studio, live.
              </p>
            </div>
            <AskOricliWidget />
          </div>

        </div>
      </div>
    </div>
  );
}
