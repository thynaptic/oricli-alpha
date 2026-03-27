import { useState, useRef, useEffect } from 'react';
import { Sparkles, X, Send, Loader2, Check, RefreshCw, ChevronDown, ChevronUp, Bot, Shield, Plus, Wand2 } from 'lucide-react';

// ─── Colours for the proposal card ──────────────────────────────────────────
const COLOR_LABELS = {
  '#C4A44A': 'Gold',
  '#4D9EFF': 'Blue',
  '#06D6A0': 'Teal',
  '#FF6B6B': 'Red',
  '#A78BFA': 'Purple',
  '#F59E0B': 'Amber',
};

// ─── Parse agent_proposal JSON block from streamed text ──────────────────────
function parseProposal(text) {
  const match = text.match(/```agent_proposal\s*([\s\S]*?)```/);
  if (!match) return null;
  try {
    return JSON.parse(match[1].trim());
  } catch {
    return null;
  }
}

// Strip the JSON block from prose for display
function stripProposalBlock(text) {
  return text.replace(/```agent_proposal[\s\S]*?```/g, '').trim();
}

// ─── Proposal Card ────────────────────────────────────────────────────────────
function ProposalCard({ parsed, skillPool, rulePool, onAccept, onTweak, streaming }) {
  const [expanded, setExpanded] = useState(false);
  if (!parsed?.proposal) return null;
  const { proposal, skills_to_create = [], rules_to_create = [], needs_clarification, clarification_question } = parsed;

  if (needs_clarification && !proposal?.name) return null;

  const attachedSkills = (proposal.skills || []).map(id => skillPool.find(s => s.id === id)).filter(Boolean);
  const attachedRules  = (proposal.rules  || []).map(id => rulePool.find(r => r.id === id)).filter(Boolean);
  const color = proposal.color || '#C4A44A';

  return (
    <div style={{ margin: '12px 0', borderRadius: 12, border: `1px solid ${color}40`, background: `${color}08`, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: `${color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Bot size={18} style={{ color }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--color-sc-text)', fontFamily: 'var(--font-grotesk)' }}>{proposal.name || 'Proposed Agent'}</div>
          <div style={{ fontSize: 12, color: 'var(--color-sc-text-muted)', marginTop: 2, lineHeight: 1.4 }}>{proposal.description}</div>
        </div>
        <button onClick={() => setExpanded(e => !e)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-muted)', padding: 4 }}>
          {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </button>
      </div>

      {/* Tags */}
      <div style={{ padding: '0 16px 12px', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {proposal.tone && (
          <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: `${color}15`, color, textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>{proposal.tone}</span>
        )}
        {attachedSkills.map(s => (
          <span key={s.id} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: 'rgba(77,158,255,0.1)', color: '#4D9EFF' }}>
            {s.name}
          </span>
        ))}
        {attachedRules.map(r => (
          <span key={r.id} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: 'rgba(6,214,160,0.1)', color: '#06D6A0' }}>
            {r.name}
          </span>
        ))}
        {skills_to_create.map(s => (
          <span key={s.id} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: 'rgba(196,164,74,0.1)', color: 'var(--color-sc-gold)', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Plus size={9} /> {s.name}
          </span>
        ))}
        {rules_to_create.map(r => (
          <span key={r.id} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: 'rgba(245,158,11,0.1)', color: '#F59E0B', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Plus size={9} /> {r.name}
          </span>
        ))}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div style={{ padding: '0 16px 14px', borderTop: '1px solid var(--color-sc-border)' }}>
          {proposal.mindset && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Mindset</div>
              <p style={{ margin: 0, fontSize: 12.5, color: 'var(--color-sc-text)', lineHeight: 1.6 }}>{proposal.mindset}</p>
            </div>
          )}
          {proposal.instructions && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Instructions</div>
              <pre style={{ margin: 0, fontSize: 12, color: 'var(--color-sc-text)', lineHeight: 1.65, fontFamily: 'var(--font-mono)', whiteSpace: 'pre-wrap', background: 'rgba(255,255,255,0.03)', borderRadius: 6, padding: '10px 12px' }}>{proposal.instructions}</pre>
            </div>
          )}
          {proposal.constraints && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-sc-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Constraints</div>
              <pre style={{ margin: 0, fontSize: 12, color: 'var(--color-sc-text)', lineHeight: 1.65, fontFamily: 'var(--font-mono)', whiteSpace: 'pre-wrap', background: 'rgba(255,255,255,0.03)', borderRadius: 6, padding: '10px 12px' }}>{proposal.constraints}</pre>
            </div>
          )}
          {skills_to_create.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-sc-gold)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>New skills to create</div>
              {skills_to_create.map(s => (
                <div key={s.id} style={{ marginBottom: 8, padding: '10px 12px', borderRadius: 8, background: 'rgba(196,164,74,0.06)', border: '1px solid rgba(196,164,74,0.15)' }}>
                  <div style={{ fontWeight: 600, fontSize: 12.5, color: 'var(--color-sc-gold)', marginBottom: 4 }}>{s.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--color-sc-text-muted)' }}>{s.description}</div>
                </div>
              ))}
            </div>
          )}
          {rules_to_create.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#F59E0B', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>New rules to create</div>
              {rules_to_create.map(r => (
                <div key={r.id} style={{ marginBottom: 8, padding: '10px 12px', borderRadius: 8, background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)' }}>
                  <div style={{ fontWeight: 600, fontSize: 12.5, color: '#F59E0B', marginBottom: 4 }}>{r.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--color-sc-text-muted)' }}>{r.description}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      {!streaming && (
        <div style={{ padding: '10px 16px', borderTop: '1px solid var(--color-sc-border)', display: 'flex', gap: 8 }}>
          <button
            onClick={() => onAccept(parsed)}
            style={{ flex: 1, padding: '8px 0', borderRadius: 8, border: 'none', cursor: 'pointer', background: `${color}20`, color, fontWeight: 700, fontSize: 13, fontFamily: 'var(--font-grotesk)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, transition: 'background 0.15s' }}
            onMouseEnter={e => e.currentTarget.style.background = `${color}35`}
            onMouseLeave={e => e.currentTarget.style.background = `${color}20`}
          >
            <Check size={14} /> Accept agent
          </button>
          <button
            onClick={onTweak}
            style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid var(--color-sc-border)', cursor: 'pointer', background: 'transparent', color: 'var(--color-sc-text-muted)', fontSize: 13, fontFamily: 'var(--font-grotesk)', display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <RefreshCw size={13} /> Tweak
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────
function Message({ msg, skillPool, rulePool, onAccept, onTweak }) {
  const isUser = msg.role === 'user';
  const prose = stripProposalBlock(msg.content);
  const parsed = msg.proposal ?? parseProposal(msg.content);

  return (
    <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start' }}>
      {prose && (
        <div style={{
          maxWidth: '90%', padding: '10px 14px', borderRadius: isUser ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
          background: isUser ? 'rgba(196,164,74,0.15)' : 'rgba(255,255,255,0.05)',
          border: `1px solid ${isUser ? 'rgba(196,164,74,0.25)' : 'var(--color-sc-border)'}`,
          color: 'var(--color-sc-text)', fontSize: 13, lineHeight: 1.65,
          fontFamily: 'var(--font-grotesk)', whiteSpace: 'pre-wrap',
        }}>{prose}</div>
      )}
      {!isUser && parsed && (
        <div style={{ width: '100%' }}>
          <ProposalCard
            parsed={parsed}
            skillPool={skillPool}
            rulePool={rulePool}
            onAccept={onAccept}
            onTweak={onTweak}
            streaming={msg.streaming}
          />
        </div>
      )}
    </div>
  );
}

// ─── Main Panel ───────────────────────────────────────────────────────────────
export default function AgentVibePanel({ onClose, skillPool, rulePool, onAgentCreated, onSkillCreated, onRuleCreated }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Describe the agent you want — what it does, how it sounds, what it cares about. I'll handle the rest.",
    }
  ]);
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [accepted, setAccepted] = useState(null);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function send(text) {
    const userMsg = text.trim();
    if (!userMsg || loading) return;
    setInput('');
    setLoading(true);

    const history = messages
      .filter(m => m.role !== 'system')
      .map(m => ({ role: m.role, content: m.content }));

    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);

    // Placeholder assistant message (streaming)
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }]);

    try {
      const res = await fetch('/v1/agents/vibe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('sc_api_key') || ''}`,
        },
        body: JSON.stringify({
          message: userMsg,
          history,
          available_skills: skillPool.map(s => s.id),
          available_rules:  rulePool.map(r => r.id),
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop() ?? '';
        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          const raw = line.slice(5).trim();
          if (raw === '[DONE]') break;
          try {
            const chunk = JSON.parse(raw);
            const delta = chunk.choices?.[0]?.delta?.content;
            if (delta) {
              fullText += delta;
              setMessages(prev => {
                const next = [...prev];
                next[next.length - 1] = { role: 'assistant', content: fullText, streaming: true };
                return next;
              });
            }
          } catch { /* skip */ }
        }
      }

      // Finalise — parse and attach proposal
      const parsed = parseProposal(fullText);
      setMessages(prev => {
        const next = [...prev];
        next[next.length - 1] = { role: 'assistant', content: fullText, streaming: false, proposal: parsed };
        return next;
      });
    } catch (err) {
      setMessages(prev => {
        const next = [...prev];
        next[next.length - 1] = { role: 'assistant', content: `Something went wrong — ${err.message}`, streaming: false };
        return next;
      });
    } finally {
      setLoading(false);
    }
  }

  function handleAccept(parsed) {
    const { proposal, skills_to_create = [], rules_to_create = [] } = parsed;

    // Commit new skills first
    skills_to_create.forEach(s => onSkillCreated?.({
      id: s.id || Math.random().toString(36).slice(2),
      name: s.name,
      description: s.description,
      mindset: s.mindset,
      instructions: s.instructions,
      constraints: s.constraints,
    }));

    // Commit new rules
    rules_to_create.forEach(r => onRuleCreated?.({
      id: r.id || Math.random().toString(36).slice(2),
      name: r.name,
      description: r.description,
      constraints: r.constraints,
    }));

    // Commit the agent — merge created skill/rule IDs into its lists
    const newSkillIds = skills_to_create.map(s => s.id);
    const newRuleIds  = rules_to_create.map(r => r.id);
    const agent = {
      ...proposal,
      skills: [...(proposal.skills || []), ...newSkillIds],
      rules:  [...(proposal.rules  || []), ...newRuleIds],
      createdAt: Date.now(),
    };
    onAgentCreated?.(agent);
    setAccepted(proposal.name);

    // Celebratory message
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: `Done. "${proposal.name}" is live in your Agents tab.${skills_to_create.length ? ` Also created ${skills_to_create.length} new skill${skills_to_create.length > 1 ? 's' : ''}.` : ''}${rules_to_create.length ? ` And ${rules_to_create.length} new rule${rules_to_create.length > 1 ? 's' : ''}.` : ''} Want to build another one?`,
    }]);
  }

  function handleTweak() {
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: "What would you like to change?",
    }]);
    setTimeout(() => inputRef.current?.focus(), 100);
  }

  return (
    <div style={{
      width: 420, display: 'flex', flexDirection: 'column', height: '100%',
      borderLeft: '1px solid var(--color-sc-border)',
      background: 'var(--color-sc-surface)',
    }}>
      {/* Panel header */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-sc-border)', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div style={{ width: 30, height: 30, borderRadius: 8, background: 'rgba(196,164,74,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Wand2 size={15} style={{ color: 'var(--color-sc-gold)' }} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 13.5, color: 'var(--color-sc-text)', fontFamily: 'var(--font-grotesk)' }}>Vibe Studio</div>
          <div style={{ fontSize: 11, color: 'var(--color-sc-text-muted)' }}>Describe an agent — Ori builds it</div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-sc-text-muted)', padding: 4, display: 'flex' }}>
          <X size={16} />
        </button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px 8px' }}>
        {messages.map((m, i) => (
          <Message
            key={i}
            msg={m}
            skillPool={skillPool}
            rulePool={rulePool}
            onAccept={handleAccept}
            onTweak={handleTweak}
          />
        ))}
        {loading && messages[messages.length - 1]?.role !== 'assistant' && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--color-sc-text-muted)', fontSize: 12 }}>
            <Loader2 size={13} style={{ animation: 'spin 0.8s linear infinite' }} /> Thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid var(--color-sc-border)', flexShrink: 0 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); } }}
            placeholder="e.g. A strict security auditor that never sugarcoats…"
            rows={2}
            style={{
              flex: 1, resize: 'none', background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--color-sc-border)', borderRadius: 10,
              color: 'var(--color-sc-text)', fontSize: 13, padding: '10px 12px',
              fontFamily: 'var(--font-grotesk)', lineHeight: 1.55, outline: 'none',
            }}
          />
          <button
            onClick={() => send(input)}
            disabled={loading || !input.trim()}
            style={{
              width: 38, height: 38, borderRadius: 10, border: 'none', cursor: loading || !input.trim() ? 'default' : 'pointer',
              background: loading || !input.trim() ? 'rgba(196,164,74,0.1)' : 'rgba(196,164,74,0.2)',
              color: loading || !input.trim() ? 'rgba(196,164,74,0.4)' : 'var(--color-sc-gold)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, transition: 'background 0.15s',
            }}
          >
            {loading ? <Loader2 size={15} style={{ animation: 'spin 0.8s linear infinite' }} /> : <Send size={15} />}
          </button>
        </div>
        <div style={{ fontSize: 10.5, color: 'var(--color-sc-text-dim)', marginTop: 7 }}>
          Enter to send · Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}
