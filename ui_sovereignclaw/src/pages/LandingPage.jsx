import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

// ── Scroll-reveal hook ────────────────────────────────────────────────────────
function useInView(threshold = 0.15) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.disconnect(); } },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return [ref, visible];
}

// ── Shared keyframes (injected once) ─────────────────────────────────────────
const KEYFRAMES = `
  @keyframes landLogoSpin   { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
  @keyframes landLogoGlow   { 0%,100% { filter: drop-shadow(0 0 18px rgba(136,117,255,0.45)); }
                               50%     { filter: drop-shadow(0 0 40px rgba(136,117,255,0.80)); } }
  @keyframes landFadeUp     { from { opacity:0; transform:translateY(22px); } to { opacity:1; transform:translateY(0); } }
  @keyframes landFadeIn     { from { opacity:0; } to { opacity:1; } }
  @keyframes landScaleIn    { from { opacity:0; transform:scale(0.94); } to { opacity:1; transform:scale(1); } }
  @keyframes landBtnPulse   { 0%,100% { box-shadow: 0 0 0 0 rgba(136,117,255,0.0); }
                               50%     { box-shadow: 0 0 28px 4px rgba(136,117,255,0.22); } }
  @keyframes landDotDrift   { 0%,100% { transform:translateY(0px); opacity:0.4; }
                               50%     { transform:translateY(-18px); opacity:0.7; } }
  @keyframes landScanLine   { from { transform:scaleX(0); } to { transform:scaleX(1); } }
  @keyframes landCardHover  { from { border-color:rgba(136,117,255,0.15); }
                               to   { border-color:rgba(136,117,255,0.45); } }
  @keyframes landReveal     { from { opacity:0; transform:translateY(28px); }
                               to   { opacity:1; transform:translateY(0); } }
`;

// ── Floating ambient dots ─────────────────────────────────────────────────────
const DOTS = [
  { top: '18%',  left: '8%',   size: 3, delay: '0s',    dur: '7s'  },
  { top: '35%',  left: '91%',  size: 2, delay: '1.2s',  dur: '9s'  },
  { top: '62%',  left: '6%',   size: 2, delay: '0.6s',  dur: '11s' },
  { top: '72%',  left: '88%',  size: 3, delay: '2.1s',  dur: '8s'  },
  { top: '12%',  left: '74%',  size: 2, delay: '1.8s',  dur: '10s' },
  { top: '48%',  left: '95%',  size: 2, delay: '0.3s',  dur: '8.5s'},
];

// ── Feature data ──────────────────────────────────────────────────────────────
const FEATURES = [
  {
    glyph: '✉',
    title: 'Just Email',
    tag: 'NO APP REQUIRED',
    desc: 'Tell ORI what to do from your inbox. RUN a report, check STATUS, approve a task — all from a reply. No login. No dashboard. No friction.',
  },
  {
    glyph: '◉',
    title: 'ORI Emails You',
    tag: 'AI THAT REACHES OUT',
    desc: 'Every morning, ORI sends you a briefing — what ran overnight, what needs your approval, what\'s scheduled today. Your business, summarized before your coffee.',
  },
  {
    glyph: '▣',
    title: 'Automate Anything',
    tag: 'WORKFLOWS THAT WORK',
    desc: 'Build once in ORI Studio. Run forever via email, schedule, or webhook. Reports, invoices, follow-ups, summaries — ORI handles the repetitive work so you don\'t have to.',
  },
  {
    glyph: '◎',
    title: 'Sovereign & Private',
    tag: 'YOUR DATA STAYS YOURS',
    desc: 'ORI runs on your infrastructure. Your conversations, your clients, your workflows — never touched by a shared model or third-party training pipeline.',
  },
];

// ── Pricing plans ─────────────────────────────────────────────────────────────
const PLANS = [
  {
    id: 'starter',
    name: 'Starter',
    price: '$29',
    period: '/mo',
    tag: 'Perfect for solo operators',
    seats: '1 user · Unlimited workflows',
    features: ['Daily ORI briefing email', 'Email command interface', '5 automated workflows', 'Manual & scheduled triggers', 'Email support'],
    highlight: false,
  },
  {
    id: 'business',
    name: 'Business',
    price: '$99',
    period: '/mo',
    tag: 'Most popular',
    seats: 'Up to 10 users · Unlimited workflows',
    features: ['Everything in Starter', 'Unlimited workflows', 'Email approval loops', 'Webhook triggers', 'Custom ORI persona', 'Priority support'],
    highlight: true,
  },
  {
    id: 'scale',
    name: 'Scale',
    price: '$249',
    period: '/mo',
    tag: 'For growing teams',
    seats: 'Unlimited users · White-label ready',
    features: ['Everything in Business', 'Multi-user email access', 'Custom sender domain', 'Dedicated onboarding', '99.9% SLA', 'Direct support line'],
    highlight: false,
  },
];

// ── Waitlist modal ────────────────────────────────────────────────────────────
function WaitlistModal({ plan, onClose }) {
  const [form, setForm] = useState({ name: '', company: '', email: '', plan: plan?.id ?? 'solo' });
  const [state, setState] = useState('idle'); // idle | loading | success | error
  const [errMsg, setErrMsg] = useState('');

  // Update plan when prop changes (user clicked different plan button)
  useEffect(() => { if (plan) setForm(f => ({ ...f, plan: plan.id })); }, [plan]);

  // Lock body scroll while modal open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim()) return;
    setState('loading');
    try {
      const res = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Something went wrong');
      setState('success');
    } catch (err) {
      setErrMsg(err.message);
      setState('error');
    }
  };

  const inputStyle = {
    width: '100%', boxSizing: 'border-box',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(136,117,255,0.20)',
    borderRadius: 8, padding: '11px 14px',
    fontSize: 14, color: '#F0ECF0',
    outline: 'none', fontFamily: 'system-ui,-apple-system,sans-serif',
    transition: 'border-color 0.2s',
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(6px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 24,
        animation: 'landFadeIn 0.2s ease forwards',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#0C080F',
          border: '1px solid rgba(136,117,255,0.25)',
          borderRadius: 16, padding: '36px 32px',
          width: '100%', maxWidth: 440,
          animation: 'landScaleIn 0.25s ease forwards',
          position: 'relative',
        }}
      >
        {/* Close */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: 16, right: 16,
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'rgba(240,236,240,0.35)', fontSize: 18, lineHeight: 1,
            transition: 'color 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.color = '#F0ECF0'}
          onMouseLeave={e => e.currentTarget.style.color = 'rgba(240,236,240,0.35)'}
        >✕</button>

        {state === 'success' ? (
          <div style={{ textAlign: 'center', padding: '16px 0' }}>
            <div style={{ fontSize: 40, marginBottom: 16 }}>✦</div>
            <h3 style={{
              fontFamily: 'system-ui,-apple-system,sans-serif',
              fontSize: 22, fontWeight: 700, color: '#F0ECF0', margin: '0 0 12px',
            }}>You're on the list.</h3>
            <p style={{ color: 'rgba(240,236,240,0.5)', fontSize: 15, lineHeight: 1.6, margin: '0 0 28px' }}>
              We'll reach out within 24 hours with your API access details.
            </p>
            <button
              onClick={onClose}
              style={{
                background: 'rgba(136,117,255,0.12)', border: '1px solid rgba(136,117,255,0.35)',
                borderRadius: 8, padding: '10px 24px', color: '#8875FF',
                fontFamily: "'SF Mono','Fira Code',monospace",
                fontSize: 11, letterSpacing: '0.1em', cursor: 'pointer',
              }}
            >CLOSE</button>
          </div>
        ) : (
          <>
            <div style={{
              fontFamily: "'SF Mono','Fira Code',monospace",
              fontSize: 9.5, letterSpacing: '0.22em', color: 'rgba(136,117,255,0.65)',
              marginBottom: 10,
            }}>GET API ACCESS</div>
            <h3 style={{
              fontFamily: 'system-ui,-apple-system,sans-serif',
              fontSize: 22, fontWeight: 700, color: '#F0ECF0',
              margin: '0 0 24px', letterSpacing: '-0.01em',
            }}>Join the waitlist</h3>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {/* Plan selector */}
              <div>
                <label style={{ fontSize: 11, color: 'rgba(240,236,240,0.4)', letterSpacing: '0.08em', display: 'block', marginBottom: 6 }}>PLAN</label>
                <select
                  value={form.plan}
                  onChange={e => setForm(f => ({ ...f, plan: e.target.value }))}
                  style={{ ...inputStyle, cursor: 'pointer' }}
                  onFocus={e => e.target.style.borderColor = 'rgba(136,117,255,0.55)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(136,117,255,0.20)'}
                >
                  <option value="solo">Solo — $29/mo</option>
                  <option value="team">Team — $99/mo</option>
                  <option value="business">Business — $249/mo</option>
                </select>
              </div>

              {/* Name */}
              <div>
                <label style={{ fontSize: 11, color: 'rgba(240,236,240,0.4)', letterSpacing: '0.08em', display: 'block', marginBottom: 6 }}>FULL NAME *</label>
                <input
                  type="text" required placeholder="Jane Smith"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'rgba(136,117,255,0.55)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(136,117,255,0.20)'}
                />
              </div>

              {/* Company */}
              <div>
                <label style={{ fontSize: 11, color: 'rgba(240,236,240,0.4)', letterSpacing: '0.08em', display: 'block', marginBottom: 6 }}>COMPANY <span style={{ opacity: 0.5 }}>(optional)</span></label>
                <input
                  type="text" placeholder="Acme Inc."
                  value={form.company}
                  onChange={e => setForm(f => ({ ...f, company: e.target.value }))}
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'rgba(136,117,255,0.55)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(136,117,255,0.20)'}
                />
              </div>

              {/* Email */}
              <div>
                <label style={{ fontSize: 11, color: 'rgba(240,236,240,0.4)', letterSpacing: '0.08em', display: 'block', marginBottom: 6 }}>WORK EMAIL *</label>
                <input
                  type="email" required placeholder="jane@acme.com"
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'rgba(136,117,255,0.55)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(136,117,255,0.20)'}
                />
              </div>

              {state === 'error' && (
                <div style={{ fontSize: 12, color: '#FF4D4D', padding: '8px 12px', background: 'rgba(255,0,0,0.06)', borderRadius: 6 }}>
                  {errMsg}
                </div>
              )}

              <button
                type="submit"
                disabled={state === 'loading'}
                style={{
                  marginTop: 4,
                  background: state === 'loading' ? 'rgba(136,117,255,0.5)' : '#8875FF',
                  border: 'none', borderRadius: 9,
                  padding: '14px', color: '#FFFFFF',
                  fontFamily: 'system-ui,-apple-system,sans-serif',
                  fontSize: 15, fontWeight: 700, cursor: state === 'loading' ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s, transform 0.15s',
                }}
                onMouseEnter={e => { if (state !== 'loading') e.currentTarget.style.background = '#A099FF'; }}
                onMouseLeave={e => { if (state !== 'loading') e.currentTarget.style.background = '#8875FF'; }}
              >
                {state === 'loading' ? 'Submitting...' : 'Request Access →'}
              </button>

              <p style={{ fontSize: 11, color: 'rgba(240,236,240,0.25)', textAlign: 'center', margin: 0 }}>
                No spam. We'll only contact you about your API access.
              </p>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

// ── Nav ───────────────────────────────────────────────────────────────────────
function LandingNav({ onLaunch, onWaitlist }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  const navigate = useNavigate();

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      height: 60,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 32px',
      background: scrolled ? 'rgba(4,2,8,0.85)' : 'transparent',
      backdropFilter: scrolled ? 'blur(16px)' : 'none',
      borderBottom: scrolled ? '1px solid rgba(136,117,255,0.10)' : '1px solid transparent',
      transition: 'background 0.3s ease, border-color 0.3s ease, backdrop-filter 0.3s ease',
    }}>
      {/* Logo + wordmark */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <img src="/ori-mark.png" alt="ORI" style={{ width: 26, height: 26, objectFit: 'contain' }} />
        <span style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 13, fontWeight: 700, color: '#F0ECF0',
          letterSpacing: '0.14em',
        }}>ORI STUDIO</span>
      </div>

      {/* Anchor links */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
        {[
          { label: 'How it works', id: 'how-it-works' },
          { label: 'Features',     id: 'features'     },
          { label: 'Pricing',      id: 'pricing'      },
        ].map(({ label, id }) => (
          <button
            key={id}
            onClick={() => scrollTo(id)}
            style={{
              fontFamily: 'system-ui,-apple-system,sans-serif',
              fontSize: 13, fontWeight: 500,
              color: 'rgba(240,236,240,0.5)', background: 'transparent',
              border: 'none', cursor: 'pointer', padding: '4px 0',
              transition: 'color 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.color = '#F0ECF0'}
            onMouseLeave={e => e.currentTarget.style.color = 'rgba(240,236,240,0.5)'}
          >{label}</button>
        ))}
        <button
          onClick={() => navigate('/faq')}
          style={{
            fontFamily: 'system-ui,-apple-system,sans-serif',
            fontSize: 13, fontWeight: 500,
            color: 'rgba(240,236,240,0.5)', background: 'transparent',
            border: 'none', cursor: 'pointer', padding: '4px 0',
            transition: 'color 0.2s',
          }}
          onMouseEnter={e => e.currentTarget.style.color = '#F0ECF0'}
          onMouseLeave={e => e.currentTarget.style.color = 'rgba(240,236,240,0.5)'}
        >FAQ</button>
      </div>

      {/* CTAs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <button
          onClick={onWaitlist}
          style={{
            fontFamily: "'SF Mono','Fira Code',monospace",
            fontSize: 11, fontWeight: 600, letterSpacing: '0.12em',
            color: 'rgba(240,236,240,0.65)', background: 'transparent',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: 6, padding: '7px 16px',
            cursor: 'pointer',
            transition: 'background 0.2s, border-color 0.2s, color 0.2s',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
            e.currentTarget.style.color = '#F0ECF0';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'rgba(240,236,240,0.65)';
          }}
        >FOR BUSINESS</button>

        <button
          onClick={onLaunch}
          style={{
            fontFamily: "'SF Mono','Fira Code',monospace",
            fontSize: 11, fontWeight: 600, letterSpacing: '0.12em',
            color: '#8875FF', background: 'transparent',
            border: '1px solid rgba(136,117,255,0.45)',
            borderRadius: 6, padding: '7px 18px',
            cursor: 'pointer',
            transition: 'background 0.2s, border-color 0.2s, color 0.2s',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'rgba(136,117,255,0.12)';
            e.currentTarget.style.borderColor = 'rgba(136,117,255,0.75)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.borderColor = 'rgba(136,117,255,0.45)';
          }}
        >TRY FREE →</button>
      </div>
    </nav>
  );
}

// ── Hero ──────────────────────────────────────────────────────────────────────
function Hero({ onLaunch }) {
  return (
    <section style={{
      position: 'relative', minHeight: '100vh',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      overflow: 'hidden', padding: '80px 24px 60px',
    }}>
      {/* Dot grid background */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        backgroundImage: 'radial-gradient(circle, rgba(136,117,255,0.07) 1px, transparent 1px)',
        backgroundSize: '36px 36px',
        opacity: 0.6,
      }} />

      {/* Radial warmth glow */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 65% 55% at 50% 46%, rgba(136,117,255,0.11) 0%, rgba(80,60,180,0.04) 55%, transparent 72%)',
      }} />

      {/* Vignette */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        boxShadow: 'inset 0 0 160px rgba(0,0,0,0.7)',
      }} />

      {/* Ambient floating dots */}
      {DOTS.map((d, i) => (
        <div key={i} style={{
          position: 'absolute', top: d.top, left: d.left,
          width: d.size, height: d.size, borderRadius: '50%',
          background: '#8875FF',
          animation: `landDotDrift ${d.dur} ease-in-out ${d.delay} infinite`,
          filter: 'blur(0.5px)',
        }} />
      ))}

      {/* Hero content */}
      <div style={{
        position: 'relative', zIndex: 1,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        maxWidth: 720, textAlign: 'center',
      }}>
        {/* Ouroboros */}
        <div style={{ animation: 'landFadeIn 0.7s ease 0.1s both', marginBottom: 32 }}>
          <img
            src="/ori-mark.png"
            alt="ORI"
            style={{
              width: 82, height: 82, objectFit: 'contain', display: 'block',
              animation: 'landLogoSpin 50s linear infinite, landLogoGlow 4s ease-in-out 0.8s infinite',
            }}
          />
        </div>

        {/* Tag line */}
        <div style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, letterSpacing: '0.28em', color: 'rgba(136,117,255,0.7)',
          marginBottom: 20, fontWeight: 500,
          animation: 'landFadeUp 0.6s ease 0.3s both',
        }}>AI FOR SMALL BUSINESS</div>

        {/* H1 */}
        <h1 style={{
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 'clamp(44px, 7vw, 76px)',
          fontWeight: 800, lineHeight: 1.05, margin: '0 0 10px',
          color: '#F0ECF0', letterSpacing: '-0.02em',
          animation: 'landFadeUp 0.65s ease 0.45s both',
        }}>No app. No dashboard.</h1>

        {/* H2 */}
        <h2 style={{
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 'clamp(44px, 7vw, 76px)',
          fontWeight: 800, lineHeight: 1.05, margin: '0 0 32px',
          color: '#8875FF', letterSpacing: '-0.02em',
          animation: 'landFadeUp 0.65s ease 0.55s both',
        }}>Just email ORI.</h2>

        {/* Subtitle */}
        <p style={{
          fontSize: 17, lineHeight: 1.7, color: 'rgba(240,236,240,0.55)',
          maxWidth: 520, margin: '0 0 44px',
          animation: 'landFadeUp 0.65s ease 0.65s both',
        }}>
          Right now you've got apps, SaaS, dashboards. It works — but it's clutter.<br/>
          Sign up, set up your workspace, and just email when you need things done.<br/>
          ORI emails you when they're finished. That's it.
        </p>

        {/* CTA */}
        <div style={{ animation: 'landScaleIn 0.5s ease 0.8s both' }}>
          <button
            onClick={onLaunch}
            style={{
              fontFamily: 'system-ui,-apple-system,sans-serif',
              fontSize: 14, fontWeight: 700, letterSpacing: '0.01em',
              color: '#FFFFFF',
              background: '#8875FF',
              border: 'none', borderRadius: 8,
              padding: '11px 26px', cursor: 'pointer',
              animation: 'landBtnPulse 3s ease-in-out 1.5s infinite',
              transition: 'transform 0.15s ease, background 0.15s ease',
              display: 'flex', alignItems: 'center', gap: 10,
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'scale(1.04)';
              e.currentTarget.style.background = '#A099FF';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.background = '#8875FF';
            }}
          >
            Get Started Free →
            <span style={{ fontSize: 15, lineHeight: 1 }}></span>
          </button>

          <p style={{
            fontFamily: "'SF Mono','Fira Code',monospace",
            fontSize: 10, color: 'rgba(240,236,240,0.28)',
            letterSpacing: '0.1em', marginTop: 14, textAlign: 'center',
          }}>NO APP REQUIRED · NO CREDIT CARD · 14-DAY FREE TRIAL</p>
        </div>
      </div>

      {/* Bottom fade to next section */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, height: 120,
        background: 'linear-gradient(to bottom, transparent, #040208)',
        pointerEvents: 'none',
      }} />
    </section>
  );
}

// ── Stats strip ───────────────────────────────────────────────────────────────
const STATS = [
  { num: '5 min', label: 'To go live'      },
  { num: '100%', label: 'Data private'     },
  { num: '$0',   label: 'Per message'      },
  { num: '1',    label: 'API key to swap'  },
];

function Stats() {
  const [ref, visible] = useInView(0.2);
  return (
    <div ref={ref} style={{
      borderTop: '1px solid rgba(136,117,255,0.12)',
      borderBottom: '1px solid rgba(136,117,255,0.12)',
      padding: '40px 32px',
      display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
      gap: 24, maxWidth: 900, margin: '0 auto', width: '100%',
    }}>
      {STATS.map((s, i) => (
        <div key={i} style={{
          textAlign: 'center',
          opacity: visible ? 1 : 0, transform: visible ? 'translateY(0)' : 'translateY(16px)',
          transition: `opacity 0.5s ease ${i * 0.1}s, transform 0.5s ease ${i * 0.1}s`,
        }}>
          <div style={{
            fontFamily: 'system-ui,-apple-system,sans-serif',
            fontSize: 42, fontWeight: 800, color: '#8875FF',
            lineHeight: 1, letterSpacing: '-0.02em', marginBottom: 8,
          }}>{s.num}</div>
          <div style={{
            fontFamily: "'SF Mono','Fira Code',monospace",
            fontSize: 10, letterSpacing: '0.14em',
            color: 'rgba(240,236,240,0.4)', fontWeight: 500,
          }}>{s.label.toUpperCase()}</div>
        </div>
      ))}
    </div>
  );
}

// ── Features ──────────────────────────────────────────────────────────────────
function FeatureCard({ feature, delay, visible }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: 'rgba(255,255,255,0.025)',
        border: `1px solid ${hovered ? 'rgba(136,117,255,0.40)' : 'rgba(136,117,255,0.12)'}`,
        borderRadius: 14, padding: '32px 28px',
        transition: 'border-color 0.25s ease, background 0.25s ease, transform 0.25s ease',
        transform: hovered ? 'translateY(-3px)' : 'translateY(0)',
        opacity: visible ? 1 : 0,
        transition: `opacity 0.55s ease ${delay}s, transform ${hovered ? '0.25s' : '0.55s'} ease ${hovered ? '0' : delay}s, border-color 0.25s ease, background 0.25s ease`,
        background: hovered ? 'rgba(136,117,255,0.04)' : 'rgba(255,255,255,0.025)',
        cursor: 'default',
      }}
    >
      {/* Glyph icon */}
      <div style={{
        fontSize: 22, color: '#8875FF', marginBottom: 18, lineHeight: 1,
        opacity: hovered ? 1 : 0.7, transition: 'opacity 0.2s',
      }}>{feature.glyph}</div>

      {/* Tag */}
      <div style={{
        fontFamily: "'SF Mono','Fira Code',monospace",
        fontSize: 9, letterSpacing: '0.2em', color: 'rgba(136,117,255,0.6)',
        marginBottom: 10, fontWeight: 600,
      }}>{feature.tag}</div>

      {/* Title */}
      <h3 style={{
        fontFamily: 'system-ui,-apple-system,sans-serif',
        fontSize: 20, fontWeight: 700, color: '#F0ECF0',
        margin: '0 0 14px', letterSpacing: '-0.01em',
      }}>{feature.title}</h3>

      {/* Description */}
      <p style={{
        fontSize: 14, lineHeight: 1.75,
        color: 'rgba(240,236,240,0.45)', margin: 0,
      }}>{feature.desc}</p>
    </div>
  );
}

function Features() {
  const [ref, visible] = useInView(0.1);
  return (
    <section id="features" ref={ref} style={{ padding: '100px 32px', maxWidth: 960, margin: '0 auto', width: '100%' }}>
      {/* Section header */}
      <div style={{
        textAlign: 'center', marginBottom: 64,
        opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(20px)',
        transition: 'opacity 0.5s ease, transform 0.5s ease',
      }}>
        <div style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, letterSpacing: '0.26em', color: 'rgba(136,117,255,0.65)',
          marginBottom: 14, fontWeight: 500,
        }}>WHY TEAMS SWITCH</div>
        <h2 style={{
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 'clamp(28px, 4vw, 44px)', fontWeight: 800,
          color: '#F0ECF0', margin: 0, letterSpacing: '-0.02em',
        }}>Everything ChatGPT isn't.</h2>
      </div>

      {/* 2×2 grid */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 20,
      }}>
        {FEATURES.map((f, i) => (
          <FeatureCard key={i} feature={f} delay={0.1 + i * 0.08} visible={visible} />
        ))}
      </div>
    </section>
  );
}

// ── How It Works ─────────────────────────────────────────────────────────────
const STEPS = [
  {
    num: '01',
    title: 'Sign up & set up your workspace',
    desc: 'Tell ORI about your business in plain language. Add your workflows — reports, follow-ups, invoices, whatever you repeat every week.',
  },
  {
    num: '02',
    title: 'Email ORI when you need something',
    desc: 'Subject: RUN Weekly Report. That\'s it. ORI executes the workflow and emails you back when it\'s done. No login required.',
  },
  {
    num: '03',
    title: 'Wake up to your ORI briefing',
    desc: 'Every morning ORI emails you — what ran overnight, what needs your approval, what\'s scheduled today. Your business, in your inbox.',
  },
];

function HowItWorks() {
  const [ref, visible] = useInView(0.1);
  return (
    <section id="how-it-works" ref={ref} style={{ padding: '100px 32px', maxWidth: 960, margin: '0 auto', width: '100%' }}>
      <div style={{
        textAlign: 'center', marginBottom: 64,
        opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(20px)',
        transition: 'opacity 0.5s ease, transform 0.5s ease',
      }}>
        <div style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, letterSpacing: '0.26em', color: 'rgba(136,117,255,0.65)',
          marginBottom: 14, fontWeight: 500,
        }}>GET STARTED IN MINUTES</div>
        <h2 style={{
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 'clamp(28px, 4vw, 44px)', fontWeight: 800,
          color: '#F0ECF0', margin: 0, letterSpacing: '-0.02em',
        }}>Three steps. No clutter.</h2>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24, position: 'relative' }}>
        {STEPS.map((step, i) => (
          <div key={i} style={{
            padding: '32px 28px',
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(136,117,255,0.10)',
            borderRadius: 14,
            opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(24px)',
            transition: `opacity 0.55s ease ${0.1 + i * 0.12}s, transform 0.55s ease ${0.1 + i * 0.12}s`,
          }}>
            <div style={{
              width: 52, height: 52, borderRadius: '50%',
              background: 'rgba(136,117,255,0.08)',
              border: '1px solid rgba(136,117,255,0.30)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: 24,
              fontFamily: "'SF Mono','Fira Code',monospace",
              fontSize: 13, fontWeight: 700, color: '#8875FF', letterSpacing: '0.05em',
            }}>{step.num}</div>
            <h3 style={{
              fontFamily: 'system-ui,-apple-system,sans-serif',
              fontSize: 18, fontWeight: 700, color: '#F0ECF0',
              margin: '0 0 12px', letterSpacing: '-0.01em',
            }}>{step.title}</h3>
            <p style={{ fontSize: 14, lineHeight: 1.75, color: 'rgba(240,236,240,0.45)', margin: 0 }}>
              {step.desc}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── Social Proof ──────────────────────────────────────────────────────────────
const TESTIMONIALS = [
  {
    quote: "I run my whole operation from email now. ORI sends me a briefing every morning — I reply with what needs doing. That's it. No dashboards, no logins.",
    name: 'Marcus R.',
    role: 'Owner · Redline HVAC Services',
  },
  {
    quote: "The email command thing sounds too simple, but that's the point. My VA emails ORI to run reports. I get the results. No one had to learn new software.",
    name: 'Christine L.',
    role: 'Founder · Lakeview Bookkeeping',
  },
  {
    quote: "Every other AI tool wanted me to live in another app. ORI just emails me. It fits how I already work. That's the difference.",
    name: 'Daniel F.',
    role: 'CEO · Northgate Property Group',
  },
];

function SocialProof() {
  const [ref, visible] = useInView(0.1);
  return (
    <section ref={ref} style={{ padding: '20px 32px 100px', maxWidth: 1040, margin: '0 auto', width: '100%' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
        {TESTIMONIALS.map((t, i) => (
          <div key={i} style={{
            background: 'rgba(255,255,255,0.025)',
            border: '1px solid rgba(136,117,255,0.12)',
            borderRadius: 14, padding: '28px 24px',
            display: 'flex', flexDirection: 'column', gap: 18,
            opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(20px)',
            transition: `opacity 0.55s ease ${0.1 + i * 0.1}s, transform 0.55s ease ${0.1 + i * 0.1}s`,
          }}>
            <div style={{ color: '#8875FF', fontSize: 12, letterSpacing: 3 }}>★★★★★</div>
            <p style={{
              fontSize: 14, lineHeight: 1.8, color: 'rgba(240,236,240,0.65)',
              margin: 0, flex: 1, fontStyle: 'italic',
            }}>"{t.quote}"</p>
            <div>
              <div style={{
                fontFamily: 'system-ui,-apple-system,sans-serif',
                fontSize: 13, fontWeight: 700, color: '#F0ECF0', marginBottom: 3,
              }}>{t.name}</div>
              <div style={{
                fontFamily: "'SF Mono','Fira Code',monospace",
                fontSize: 9.5, color: 'rgba(240,236,240,0.3)', letterSpacing: '0.08em',
              }}>{t.role}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── Comparison Table ──────────────────────────────────────────────────────────
const COMPARE_ROWS = [
  { label: 'Data used for training',  cols: [{ text: 'Never',         good: true  }, { text: 'Yes',            good: false }, { text: 'Yes',         good: false }] },
  { label: 'Message limits',          cols: [{ text: 'Unlimited',      good: true  }, { text: 'Capped',         good: false }, { text: 'Pay per token',good: false }] },
  { label: 'Monthly pricing',         cols: [{ text: 'Flat rate',      good: true  }, { text: 'Per seat',       good: false }, { text: 'Variable',    good: false }] },
  { label: 'OpenAI-compatible API',   cols: [{ text: 'Yes',            good: true  }, { text: '—',             good: null  }, { text: 'Yes',         good: true  }] },
  { label: 'Custom knowledge base',   cols: [{ text: 'Included',       good: true  }, { text: 'Limited',        good: null  }, { text: 'DIY only',    good: false }] },
  { label: 'Setup time',              cols: [{ text: '5 minutes',      good: true  }, { text: 'Instant',        good: null  }, { text: 'Hours',       good: false }] },
  { label: 'Dedicated support',       cols: [{ text: 'Included',       good: true  }, { text: 'Email only',     good: null  }, { text: 'Docs only',   good: false }] },
];

function ComparisonTable() {
  const [ref, visible] = useInView(0.1);
  const colHeaders = ['ORI Studio', 'ChatGPT Team', 'OpenAI API'];

  return (
    <section ref={ref} style={{ padding: '0 32px 100px', maxWidth: 1040, margin: '0 auto', width: '100%' }}>
      <div style={{
        textAlign: 'center', marginBottom: 56,
        opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(20px)',
        transition: 'opacity 0.5s ease, transform 0.5s ease',
      }}>
        <div style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, letterSpacing: '0.26em', color: 'rgba(136,117,255,0.65)',
          marginBottom: 14, fontWeight: 500,
        }}>HOW WE STACK UP</div>
        <h2 style={{
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 'clamp(28px, 4vw, 44px)', fontWeight: 800,
          color: '#F0ECF0', margin: 0, letterSpacing: '-0.02em',
        }}>Not all AI is equal.</h2>
      </div>

      <div style={{
        border: '1px solid rgba(136,117,255,0.18)',
        borderRadius: 16, overflow: 'hidden',
        opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(24px)',
        transition: 'opacity 0.55s ease 0.15s, transform 0.55s ease 0.15s',
      }}>
        {/* Header row */}
        <div style={{
          display: 'grid', gridTemplateColumns: '2fr 1.2fr 1.2fr 1.2fr',
          background: 'rgba(136,117,255,0.05)',
          borderBottom: '1px solid rgba(136,117,255,0.15)',
        }}>
          <div style={{ padding: '18px 24px' }} />
          {colHeaders.map((h, i) => (
            <div key={i} style={{
              padding: '18px 16px', textAlign: 'center',
              borderLeft: '1px solid rgba(136,117,255,0.10)',
              background: i === 0 ? 'rgba(136,117,255,0.08)' : 'transparent',
              position: 'relative',
            }}>
              {i === 0 && (
                <div style={{
                  position: 'absolute', top: -11, left: '50%', transform: 'translateX(-50%)',
                  background: '#8875FF', color: '#FFF',
                  fontFamily: "'SF Mono','Fira Code',monospace",
                  fontSize: 8, fontWeight: 700, letterSpacing: '0.12em',
                  padding: '3px 10px', borderRadius: 20, whiteSpace: 'nowrap',
                }}>RECOMMENDED</div>
              )}
              <span style={{
                fontFamily: 'system-ui,-apple-system,sans-serif',
                fontSize: 13, fontWeight: 700,
                color: i === 0 ? '#F0ECF0' : 'rgba(240,236,240,0.45)',
              }}>{h}</span>
            </div>
          ))}
        </div>

        {/* Data rows */}
        {COMPARE_ROWS.map((row, ri) => (
          <div key={ri} style={{
            display: 'grid', gridTemplateColumns: '2fr 1.2fr 1.2fr 1.2fr',
            borderBottom: ri < COMPARE_ROWS.length - 1 ? '1px solid rgba(136,117,255,0.08)' : 'none',
            background: ri % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)',
          }}>
            <div style={{
              padding: '16px 24px',
              fontFamily: 'system-ui,-apple-system,sans-serif',
              fontSize: 13.5, color: 'rgba(240,236,240,0.6)',
            }}>{row.label}</div>
            {row.cols.map((col, ci) => (
              <div key={ci} style={{
                padding: '16px 16px', textAlign: 'center',
                borderLeft: '1px solid rgba(136,117,255,0.08)',
                background: ci === 0 ? 'rgba(136,117,255,0.04)' : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <span style={{
                  fontFamily: 'system-ui,-apple-system,sans-serif',
                  fontSize: 13,
                  color: col.good === true
                    ? (ci === 0 ? '#A099FF' : 'rgba(240,236,240,0.5)')
                    : col.good === false
                      ? 'rgba(240,236,240,0.28)'
                      : 'rgba(240,236,240,0.35)',
                  fontWeight: ci === 0 ? 600 : 400,
                }}>{col.text}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

// ── Pricing ───────────────────────────────────────────────────────────────────
function PlanCard({ plan, delay, visible, onSelect }) {
  const [hovered, setHovered] = useState(false);
  const active = plan.highlight || hovered;
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        position: 'relative',
        background: plan.highlight ? 'rgba(136,117,255,0.06)' : 'rgba(255,255,255,0.025)',
        border: `1px solid ${active ? 'rgba(136,117,255,0.55)' : 'rgba(136,117,255,0.12)'}`,
        borderRadius: 16, padding: '32px 28px',
        display: 'flex', flexDirection: 'column',
        opacity: visible ? 1 : 0,
        transform: visible ? (hovered ? 'translateY(-4px)' : 'none') : 'translateY(24px)',
        transition: `opacity 0.55s ease ${delay}s, transform 0.3s ease, border-color 0.25s`,
      }}
    >
      {/* Popular badge */}
      {plan.highlight && (
        <div style={{
          position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
          background: '#8875FF', color: '#FFF',
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 9, fontWeight: 700, letterSpacing: '0.14em',
          padding: '4px 14px', borderRadius: 20,
        }}>MOST POPULAR</div>
      )}

      {/* Plan name + tag */}
      <div style={{
        fontFamily: "'SF Mono','Fira Code',monospace",
        fontSize: 9.5, letterSpacing: '0.2em',
        color: plan.highlight ? 'rgba(136,117,255,0.8)' : 'rgba(240,236,240,0.35)',
        marginBottom: 8,
      }}>{plan.tag.toUpperCase()}</div>
      <div style={{
        fontFamily: 'system-ui,-apple-system,sans-serif',
        fontSize: 20, fontWeight: 700, color: '#F0ECF0',
        marginBottom: 16, letterSpacing: '-0.01em',
      }}>{plan.name}</div>

      {/* Price */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 6 }}>
        <span style={{
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 46, fontWeight: 800, color: '#F0ECF0',
          letterSpacing: '-0.03em', lineHeight: 1,
        }}>{plan.price}</span>
        <span style={{ color: 'rgba(240,236,240,0.4)', fontSize: 15 }}>{plan.period}</span>
      </div>

      {/* Seats */}
      <div style={{
        fontFamily: "'SF Mono','Fira Code',monospace",
        fontSize: 10.5, color: 'rgba(136,117,255,0.7)',
        marginBottom: 24, letterSpacing: '0.04em',
      }}>{plan.seats}</div>

      {/* Features list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 9, marginBottom: 28, flex: 1 }}>
        {plan.features.map((f, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 9, fontSize: 13.5, color: 'rgba(240,236,240,0.6)' }}>
            <span style={{ color: '#8875FF', flexShrink: 0, marginTop: 1 }}>✓</span>
            <span>{f}</span>
          </div>
        ))}
      </div>

      {/* CTA */}
      <button
        onClick={() => onSelect(plan)}
        style={{
          background: plan.highlight ? '#8875FF' : 'transparent',
          border: `1px solid ${plan.highlight ? '#8875FF' : 'rgba(136,117,255,0.35)'}`,
          borderRadius: 9, padding: '13px',
          color: plan.highlight ? '#FFFFFF' : '#8875FF',
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 14, fontWeight: 700, cursor: 'pointer',
          transition: 'background 0.2s, border-color 0.2s, transform 0.15s',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.background = '#A099FF';
          e.currentTarget.style.borderColor = '#A099FF';
          e.currentTarget.style.color = '#FFF';
          e.currentTarget.style.transform = 'scale(1.02)';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.background = plan.highlight ? '#8875FF' : 'transparent';
          e.currentTarget.style.borderColor = plan.highlight ? '#8875FF' : 'rgba(136,117,255,0.35)';
          e.currentTarget.style.color = plan.highlight ? '#FFF' : '#8875FF';
          e.currentTarget.style.transform = 'scale(1)';
        }}
      >
        Start Free Trial →
      </button>
    </div>
  );
}

function Pricing({ onSelectPlan }) {
  const [ref, visible] = useInView(0.1);
  return (
    <section id="pricing" ref={ref} style={{ padding: '100px 32px', maxWidth: 1040, margin: '0 auto', width: '100%' }}>
      {/* Header */}
      <div style={{
        textAlign: 'center', marginBottom: 64,
        opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(20px)',
        transition: 'opacity 0.5s ease, transform 0.5s ease',
      }}>
        <div style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, letterSpacing: '0.26em', color: 'rgba(136,117,255,0.65)',
          marginBottom: 14, fontWeight: 500,
        }}>SIMPLE PRICING</div>
        <h2 style={{
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 'clamp(28px,4vw,44px)', fontWeight: 800,
          color: '#F0ECF0', margin: '0 0 14px', letterSpacing: '-0.02em',
        }}>One price. Unlimited use.</h2>
        <p style={{ fontSize: 16, color: 'rgba(240,236,240,0.45)', margin: 0 }}>
          No per-message fees. No usage caps. No surprises at month-end.
        </p>
      </div>

      {/* Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
        {PLANS.map((plan, i) => (
          <PlanCard key={plan.id} plan={plan} delay={0.1 + i * 0.1} visible={visible} onSelect={onSelectPlan} />
        ))}
      </div>

      {/* Fine print */}
      <p style={{
        textAlign: 'center', marginTop: 32,
        fontFamily: "'SF Mono','Fira Code',monospace",
        fontSize: 10, color: 'rgba(240,236,240,0.22)', letterSpacing: '0.06em',
      }}>
        All plans include the OpenAI-compatible API · Your data never trains our models · Cancel anytime
      </p>
    </section>
  );
}

// ── Philosophy ────────────────────────────────────────────────────────────────
function Philosophy() {
  const [ref, visible] = useInView(0.15);
  return (
    <section ref={ref} style={{
      borderTop: '1px solid rgba(136,117,255,0.10)',
      borderBottom: '1px solid rgba(136,117,255,0.10)',
      padding: '120px 32px',
      background: 'rgba(136,117,255,0.02)',
    }}>
      <div style={{ maxWidth: 780, margin: '0 auto' }}>
        {/* Label */}
        <div style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, letterSpacing: '0.26em', color: 'rgba(136,117,255,0.6)',
          marginBottom: 48, fontWeight: 500,
          opacity: visible ? 1 : 0, transition: 'opacity 0.5s ease',
        }}>THE PHILOSOPHY</div>

        {/* Big statement — each line animates in */}
        {[
          { text: 'Most AI reads your mail.',       size: 'clamp(32px,5vw,58px)', color: '#F0ECF0',              delay: 0.1  },
          { text: 'Every message you send',          size: 'clamp(28px,4vw,48px)', color: 'rgba(240,236,240,0.7)', delay: 0.25 },
          { text: 'trains someone else\'s model.',   size: 'clamp(28px,4vw,48px)', color: 'rgba(240,236,240,0.7)', delay: 0.4  },
          { text: 'ORI Studio doesn\'t.',            size: 'clamp(32px,5vw,58px)', color: '#8875FF',               delay: 0.65 },
        ].map((line, i) => (
          <div key={i} style={{
            fontFamily: 'system-ui,-apple-system,sans-serif',
            fontSize: line.size, fontWeight: 800,
            color: line.color, lineHeight: 1.15,
            letterSpacing: '-0.02em',
            marginBottom: i === 1 ? 0 : (i === 2 ? 32 : 16),
            opacity: visible ? 1 : 0,
            transform: visible ? 'none' : 'translateX(-20px)',
            transition: `opacity 0.6s ease ${line.delay}s, transform 0.6s ease ${line.delay}s`,
          }}>{line.text}</div>
        ))}

        {/* Subtext */}
        <p style={{
          fontSize: 16, lineHeight: 1.8, color: 'rgba(240,236,240,0.45)',
          maxWidth: 540, margin: '40px 0 0',
          opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(12px)',
          transition: 'opacity 0.6s ease 0.9s, transform 0.6s ease 0.9s',
        }}>
          Your customer conversations, internal docs, and business data stay
          private. No shared training pipelines. No policy updates that silently
          change what happens to your data. ORI Studio is private by design —
          not by checkbox.
        </p>
      </div>
    </section>
  );
}

// ── Final CTA ─────────────────────────────────────────────────────────────────
function FinalCTA({ onLaunch, onWaitlist }) {
  const [ref, visible] = useInView(0.2);
  return (
    <section ref={ref} style={{
      padding: '140px 32px',
      display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Glow behind */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 50% 60% at 50% 50%, rgba(136,117,255,0.09) 0%, transparent 70%)',
      }} />

      {/* Ouroboros */}
      <div style={{
        marginBottom: 36,
        opacity: visible ? 1 : 0, transform: visible ? 'scale(1)' : 'scale(0.85)',
        transition: 'opacity 0.6s ease, transform 0.6s ease',
      }}>
        <img
          src="/ori-mark.png" alt="ORI"
          style={{
            width: 64, height: 64, objectFit: 'contain',
            animation: visible ? 'landLogoGlow 3s ease-in-out infinite' : 'none',
          }}
        />
      </div>

      <h2 style={{
        fontFamily: 'system-ui,-apple-system,sans-serif',
        fontSize: 'clamp(32px,5vw,52px)', fontWeight: 800,
        color: '#F0ECF0', letterSpacing: '-0.02em', margin: '0 0 16px',
        opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(18px)',
        transition: 'opacity 0.55s ease 0.1s, transform 0.55s ease 0.1s',
      }}>Ready to make the switch?</h2>

      <p style={{
        fontSize: 16, color: 'rgba(240,236,240,0.45)',
        maxWidth: 420, margin: '0 0 44px', lineHeight: 1.7,
        opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(14px)',
        transition: 'opacity 0.55s ease 0.2s, transform 0.55s ease 0.2s',
      }}>
        Set up in 5 minutes. OpenAI-compatible.
        Private by default. No credit card required.
      </p>

      <div style={{
        display: 'flex', gap: 14, flexWrap: 'wrap', justifyContent: 'center',
        opacity: visible ? 1 : 0, transform: visible ? 'scale(1)' : 'scale(0.92)',
        transition: 'opacity 0.5s ease 0.3s, transform 0.5s ease 0.3s',
      }}>
        <button
          onClick={onLaunch}
          style={{
            fontFamily: 'system-ui,-apple-system,sans-serif',
            fontSize: 17, fontWeight: 700,
            color: '#FFFFFF', background: '#8875FF',
            border: 'none', borderRadius: 10,
            padding: '17px 44px', cursor: 'pointer',
            animation: visible ? 'landBtnPulse 3s ease-in-out 0.5s infinite' : 'none',
            transition: 'transform 0.15s ease, background 0.15s ease',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'scale(1.04)';
            e.currentTarget.style.background = '#A099FF';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.background = '#8875FF';
          }}
        >
          Start Free Trial →
        </button>

        <button
          onClick={onWaitlist}
          style={{
            fontFamily: 'system-ui,-apple-system,sans-serif',
            fontSize: 17, fontWeight: 700,
            color: '#F0ECF0', background: 'transparent',
            border: '1px solid rgba(240,236,240,0.18)', borderRadius: 10,
            padding: '17px 36px', cursor: 'pointer',
            transition: 'transform 0.15s ease, border-color 0.15s ease',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'scale(1.04)';
            e.currentTarget.style.borderColor = 'rgba(240,236,240,0.4)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.borderColor = 'rgba(240,236,240,0.18)';
          }}
        >
          See Pricing →
        </button>
      </div>
    </section>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────────
function Footer() {
  const navigate = useNavigate();
  return (
    <footer style={{
      borderTop: '1px solid rgba(136,117,255,0.10)',
      padding: '28px 32px',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <img src="/ori-mark.png" alt="ORI" style={{ width: 18, height: 18, objectFit: 'contain', opacity: 0.6 }} />
        <span style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, color: 'rgba(240,236,240,0.28)', letterSpacing: '0.1em',
        }}>ORI STUDIO — THYNAPTIC</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <button
          onClick={() => navigate('/faq')}
          style={{
            fontFamily: "'SF Mono','Fira Code',monospace",
            fontSize: 10, color: 'rgba(240,236,240,0.28)', letterSpacing: '0.08em',
            background: 'none', border: 'none', cursor: 'pointer',
            transition: 'color 0.2s',
          }}
          onMouseEnter={e => e.currentTarget.style.color = 'rgba(136,117,255,0.7)'}
          onMouseLeave={e => e.currentTarget.style.color = 'rgba(240,236,240,0.28)'}
        >FAQ</button>
        <a href="mailto:support@thynaptic.com" style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, color: 'rgba(240,236,240,0.28)', letterSpacing: '0.08em',
          textDecoration: 'none', transition: 'color 0.2s',
        }}
          onMouseEnter={e => e.currentTarget.style.color = 'rgba(136,117,255,0.7)'}
          onMouseLeave={e => e.currentTarget.style.color = 'rgba(240,236,240,0.28)'}
        >SUPPORT</a>
        <span style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, color: 'rgba(240,236,240,0.2)', letterSpacing: '0.08em',
        }}>v2.1.0</span>
      </div>
    </footer>
  );
}

// ── Root landing page ─────────────────────────────────────────────────────────
export function LandingPage({ onLaunch }) {
  const [waitlistPlan, setWaitlistPlan] = useState(null);

  const openWaitlist = (plan) => setWaitlistPlan(plan || PLANS[1]);
  const closeWaitlist = () => setWaitlistPlan(null);

  return (
    <div style={{
      background: '#040208',
      color: '#F0ECF0',
      minHeight: '100vh',
      overflowX: 'hidden',
    }}>
      <style>{KEYFRAMES}</style>
      <LandingNav onLaunch={onLaunch} onWaitlist={() => openWaitlist(null)} />
      <Hero onLaunch={onLaunch} />
      <Stats />
      <HowItWorks />
      <Features />
      <SocialProof />
      <ComparisonTable />
      <Pricing onSelectPlan={openWaitlist} />
      <Philosophy />
      <FinalCTA onLaunch={onLaunch} onWaitlist={() => openWaitlist(null)} />
      <Footer />
      {waitlistPlan !== null && (
        <WaitlistModal plan={waitlistPlan} onClose={closeWaitlist} />
      )}
    </div>
  );
}
