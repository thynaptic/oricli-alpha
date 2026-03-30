import { useState, useEffect, useRef, useCallback } from 'react';

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
  @keyframes landLogoGlow   { 0%,100% { filter: drop-shadow(0 0 18px rgba(229,0,76,0.45)); }
                               50%     { filter: drop-shadow(0 0 40px rgba(229,0,76,0.80)); } }
  @keyframes landFadeUp     { from { opacity:0; transform:translateY(22px); } to { opacity:1; transform:translateY(0); } }
  @keyframes landFadeIn     { from { opacity:0; } to { opacity:1; } }
  @keyframes landScaleIn    { from { opacity:0; transform:scale(0.94); } to { opacity:1; transform:scale(1); } }
  @keyframes landBtnPulse   { 0%,100% { box-shadow: 0 0 0 0 rgba(229,0,76,0.0); }
                               50%     { box-shadow: 0 0 28px 4px rgba(229,0,76,0.22); } }
  @keyframes landDotDrift   { 0%,100% { transform:translateY(0px); opacity:0.4; }
                               50%     { transform:translateY(-18px); opacity:0.7; } }
  @keyframes landScanLine   { from { transform:scaleX(0); } to { transform:scaleX(1); } }
  @keyframes landCardHover  { from { border-color:rgba(229,0,76,0.15); }
                               to   { border-color:rgba(229,0,76,0.45); } }
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
    glyph: '⬡',
    title: 'The Hive',
    tag: 'SWARM INTELLIGENCE',
    desc: '250+ cognitive modules operate as an autonomous micro-agent swarm. Tasks are bid on, peer-reviewed, and consensus-resolved. No single point of failure.',
  },
  {
    glyph: '◎',
    title: 'Memory Bridge',
    tag: 'PERSISTENT RECALL',
    desc: 'LMDB speed. Vector semantic search. Neo4j relationship graphs. Oricli remembers every conversation and recalls with surgical precision across sessions.',
  },
  {
    glyph: '⚒',
    title: 'Sovereign Forge',
    tag: 'SELF-IMPROVEMENT',
    desc: 'When Oricli detects a capability gap, she fills it — writing, testing, and deploying her own tools. One API call runs a full LoRA training loop overnight.',
  },
  {
    glyph: '⊘',
    title: 'Zero Cloud',
    tag: 'FULL SOVEREIGNTY',
    desc: 'OpenAI-compatible API on your hardware. No data leaves your server. No usage caps. No terms that can change tomorrow. Your intelligence. Your rules.',
  },
];

// ── Nav ───────────────────────────────────────────────────────────────────────
function LandingNav({ onLaunch }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      height: 60,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 32px',
      background: scrolled ? 'rgba(4,2,8,0.85)' : 'transparent',
      backdropFilter: scrolled ? 'blur(16px)' : 'none',
      borderBottom: scrolled ? '1px solid rgba(229,0,76,0.10)' : '1px solid transparent',
      transition: 'background 0.3s ease, border-color 0.3s ease, backdrop-filter 0.3s ease',
    }}>
      {/* Logo + wordmark */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <img src="/ori-mark-red.png" alt="ORI" style={{ width: 26, height: 26, objectFit: 'contain' }} />
        <span style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 13, fontWeight: 700, color: '#F0ECF0',
          letterSpacing: '0.14em',
        }}>ORI STUDIO</span>
      </div>

      {/* CTA */}
      <button
        onClick={onLaunch}
        style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 11, fontWeight: 600, letterSpacing: '0.12em',
          color: '#E5004C', background: 'transparent',
          border: '1px solid rgba(229,0,76,0.45)',
          borderRadius: 6, padding: '7px 18px',
          cursor: 'pointer',
          transition: 'background 0.2s, border-color 0.2s, color 0.2s',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.background = 'rgba(229,0,76,0.12)';
          e.currentTarget.style.borderColor = 'rgba(229,0,76,0.75)';
        }}
        onMouseLeave={e => {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.borderColor = 'rgba(229,0,76,0.45)';
        }}
      >LAUNCH →</button>
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
        backgroundImage: 'radial-gradient(circle, rgba(229,0,76,0.07) 1px, transparent 1px)',
        backgroundSize: '36px 36px',
        opacity: 0.6,
      }} />

      {/* Radial warmth glow */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 65% 55% at 50% 46%, rgba(180,0,40,0.13) 0%, rgba(80,0,20,0.05) 55%, transparent 72%)',
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
          background: '#E5004C',
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
            src="/ori-mark-red.png"
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
          fontSize: 10, letterSpacing: '0.28em', color: 'rgba(229,0,76,0.7)',
          marginBottom: 20, fontWeight: 500,
          animation: 'landFadeUp 0.6s ease 0.3s both',
        }}>SOVEREIGN INTELLIGENCE OS</div>

        {/* H1 */}
        <h1 style={{
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 'clamp(44px, 7vw, 76px)',
          fontWeight: 800, lineHeight: 1.05, margin: '0 0 10px',
          color: '#F0ECF0', letterSpacing: '-0.02em',
          animation: 'landFadeUp 0.65s ease 0.45s both',
        }}>Sovereign Intelligence.</h1>

        {/* H2 — red emphasis */}
        <h2 style={{
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 'clamp(44px, 7vw, 76px)',
          fontWeight: 800, lineHeight: 1.05, margin: '0 0 32px',
          color: '#E5004C', letterSpacing: '-0.02em',
          animation: 'landFadeUp 0.65s ease 0.55s both',
        }}>No rented minds.</h2>

        {/* Subtitle */}
        <p style={{
          fontSize: 17, lineHeight: 1.7, color: 'rgba(240,236,240,0.55)',
          maxWidth: 520, margin: '0 0 44px',
          animation: 'landFadeUp 0.65s ease 0.65s both',
        }}>
          A local-first AI operating system with 250+ cognitive modules,
          distributed swarm intelligence, and continuous self-improvement.
          Your hardware. Your data. Your model.
        </p>

        {/* CTA */}
        <div style={{ animation: 'landScaleIn 0.5s ease 0.8s both' }}>
          <button
            onClick={onLaunch}
            style={{
              fontFamily: 'system-ui,-apple-system,sans-serif',
              fontSize: 16, fontWeight: 700, letterSpacing: '0.01em',
              color: '#FFFFFF',
              background: '#E5004C',
              border: 'none', borderRadius: 10,
              padding: '16px 40px', cursor: 'pointer',
              animation: 'landBtnPulse 3s ease-in-out 1.5s infinite',
              transition: 'transform 0.15s ease, background 0.15s ease',
              display: 'flex', alignItems: 'center', gap: 10,
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'scale(1.04)';
              e.currentTarget.style.background = '#FF1A5E';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.background = '#E5004C';
            }}
          >
            Launch ORI Studio
            <span style={{ fontSize: 18, lineHeight: 1 }}>→</span>
          </button>

          <p style={{
            fontFamily: "'SF Mono','Fira Code',monospace",
            fontSize: 10, color: 'rgba(240,236,240,0.28)',
            letterSpacing: '0.1em', marginTop: 14, textAlign: 'center',
          }}>NO ACCOUNT · NO CLOUD · LOCAL ONLY</p>
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
  { num: '250+', label: 'Cognitive Modules' },
  { num: '100%', label: 'Local Execution'   },
  { num: '0ms',  label: 'Cloud Latency'     },
  { num: '1',    label: 'Command to Train'  },
];

function Stats() {
  const [ref, visible] = useInView(0.2);
  return (
    <div ref={ref} style={{
      borderTop: '1px solid rgba(229,0,76,0.12)',
      borderBottom: '1px solid rgba(229,0,76,0.12)',
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
            fontSize: 42, fontWeight: 800, color: '#E5004C',
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
        border: `1px solid ${hovered ? 'rgba(229,0,76,0.40)' : 'rgba(229,0,76,0.12)'}`,
        borderRadius: 14, padding: '32px 28px',
        transition: 'border-color 0.25s ease, background 0.25s ease, transform 0.25s ease',
        transform: hovered ? 'translateY(-3px)' : 'translateY(0)',
        opacity: visible ? 1 : 0,
        transition: `opacity 0.55s ease ${delay}s, transform ${hovered ? '0.25s' : '0.55s'} ease ${hovered ? '0' : delay}s, border-color 0.25s ease, background 0.25s ease`,
        background: hovered ? 'rgba(229,0,76,0.04)' : 'rgba(255,255,255,0.025)',
        cursor: 'default',
      }}
    >
      {/* Glyph icon */}
      <div style={{
        fontSize: 22, color: '#E5004C', marginBottom: 18, lineHeight: 1,
        opacity: hovered ? 1 : 0.7, transition: 'opacity 0.2s',
      }}>{feature.glyph}</div>

      {/* Tag */}
      <div style={{
        fontFamily: "'SF Mono','Fira Code',monospace",
        fontSize: 9, letterSpacing: '0.2em', color: 'rgba(229,0,76,0.6)',
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
    <section ref={ref} style={{ padding: '100px 32px', maxWidth: 960, margin: '0 auto', width: '100%' }}>
      {/* Section header */}
      <div style={{
        textAlign: 'center', marginBottom: 64,
        opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(20px)',
        transition: 'opacity 0.5s ease, transform 0.5s ease',
      }}>
        <div style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, letterSpacing: '0.26em', color: 'rgba(229,0,76,0.65)',
          marginBottom: 14, fontWeight: 500,
        }}>COGNITIVE ARCHITECTURE</div>
        <h2 style={{
          fontFamily: 'system-ui,-apple-system,sans-serif',
          fontSize: 'clamp(28px, 4vw, 44px)', fontWeight: 800,
          color: '#F0ECF0', margin: 0, letterSpacing: '-0.02em',
        }}>Built different. By design.</h2>
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

// ── Philosophy ────────────────────────────────────────────────────────────────
function Philosophy() {
  const [ref, visible] = useInView(0.15);
  return (
    <section ref={ref} style={{
      borderTop: '1px solid rgba(229,0,76,0.10)',
      borderBottom: '1px solid rgba(229,0,76,0.10)',
      padding: '120px 32px',
      background: 'rgba(229,0,76,0.02)',
    }}>
      <div style={{ maxWidth: 780, margin: '0 auto' }}>
        {/* Label */}
        <div style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, letterSpacing: '0.26em', color: 'rgba(229,0,76,0.6)',
          marginBottom: 48, fontWeight: 500,
          opacity: visible ? 1 : 0, transition: 'opacity 0.5s ease',
        }}>THE PHILOSOPHY</div>

        {/* Big statement — each line animates in */}
        {[
          { text: 'Most AI is rented.',             size: 'clamp(32px,5vw,58px)', color: '#F0ECF0',              delay: 0.1  },
          { text: 'A mind you don\'t own',           size: 'clamp(28px,4vw,48px)', color: 'rgba(240,236,240,0.7)', delay: 0.25 },
          { text: 'can be taken away.',              size: 'clamp(28px,4vw,48px)', color: 'rgba(240,236,240,0.7)', delay: 0.4  },
          { text: 'We built Oricli differently.',    size: 'clamp(32px,5vw,58px)', color: '#E5004C',               delay: 0.65 },
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
          When Anthropic changes a policy, when OpenAI raises prices, when a
          provider decides enterprise terms don't apply to you — your workflow
          breaks. Oricli can't be taken away because it lives on your server,
          trained on your data, running on your compute.
        </p>
      </div>
    </section>
  );
}

// ── Final CTA ─────────────────────────────────────────────────────────────────
function FinalCTA({ onLaunch }) {
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
        background: 'radial-gradient(ellipse 50% 60% at 50% 50%, rgba(180,0,40,0.09) 0%, transparent 70%)',
      }} />

      {/* Ouroboros */}
      <div style={{
        marginBottom: 36,
        opacity: visible ? 1 : 0, transform: visible ? 'scale(1)' : 'scale(0.85)',
        transition: 'opacity 0.6s ease, transform 0.6s ease',
      }}>
        <img
          src="/ori-mark-red.png" alt="ORI"
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
      }}>Ready to own your intelligence?</h2>

      <p style={{
        fontSize: 16, color: 'rgba(240,236,240,0.45)',
        maxWidth: 420, margin: '0 0 44px', lineHeight: 1.7,
        opacity: visible ? 1 : 0, transform: visible ? 'none' : 'translateY(14px)',
        transition: 'opacity 0.55s ease 0.2s, transform 0.55s ease 0.2s',
      }}>
        Self-hosted. No API keys. No data contracts.
        Just Oricli, running on your terms.
      </p>

      <div style={{
        opacity: visible ? 1 : 0, transform: visible ? 'scale(1)' : 'scale(0.92)',
        transition: 'opacity 0.5s ease 0.3s, transform 0.5s ease 0.3s',
      }}>
        <button
          onClick={onLaunch}
          style={{
            fontFamily: 'system-ui,-apple-system,sans-serif',
            fontSize: 17, fontWeight: 700,
            color: '#FFFFFF', background: '#E5004C',
            border: 'none', borderRadius: 10,
            padding: '17px 44px', cursor: 'pointer',
            animation: visible ? 'landBtnPulse 3s ease-in-out 0.5s infinite' : 'none',
            transition: 'transform 0.15s ease, background 0.15s ease',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'scale(1.04)';
            e.currentTarget.style.background = '#FF1A5E';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.background = '#E5004C';
          }}
        >
          Enter ORI Studio →
        </button>
      </div>
    </section>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer style={{
      borderTop: '1px solid rgba(229,0,76,0.10)',
      padding: '28px 32px',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <img src="/ori-mark-red.png" alt="ORI" style={{ width: 18, height: 18, objectFit: 'contain', opacity: 0.6 }} />
        <span style={{
          fontFamily: "'SF Mono','Fira Code',monospace",
          fontSize: 10, color: 'rgba(240,236,240,0.28)', letterSpacing: '0.1em',
        }}>ORI STUDIO — THYNAPTIC</span>
      </div>
      <span style={{
        fontFamily: "'SF Mono','Fira Code',monospace",
        fontSize: 10, color: 'rgba(240,236,240,0.2)', letterSpacing: '0.08em',
      }}>v2.1.0 · RING-0</span>
    </footer>
  );
}

// ── Root landing page ─────────────────────────────────────────────────────────
export function LandingPage({ onLaunch }) {
  return (
    <div style={{
      background: '#040208',
      color: '#F0ECF0',
      minHeight: '100vh',
      overflowX: 'hidden',
    }}>
      <style>{KEYFRAMES}</style>
      <LandingNav onLaunch={onLaunch} />
      <Hero onLaunch={onLaunch} />
      <Stats />
      <Features />
      <Philosophy />
      <FinalCTA onLaunch={onLaunch} />
      <Footer />
    </div>
  );
}
