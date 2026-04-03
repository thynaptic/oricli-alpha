import { useEffect, useRef } from 'react';

// Fallback ERI → accent mapping used only when backbone is unreachable
// (no arte_palette in response). Keeps purple family across all states.
function eriFallbackAccent(eri) {
  if (eri >= 0.7)  return { accent: '#C4B9FF', glow: '#D8D1FF' }; // Symphonic
  if (eri >= 0.3)  return { accent: '#8875FF', glow: '#A99BFF' }; // Stable
  if (eri >= -0.3) return { accent: '#6B5FCC', glow: '#8070E0' }; // Dissonant
  return           { accent: '#4E4499', glow: '#6558BB' };         // Cacophonic
}

// Arousal → surface warmth tweak (subtle tint on high arousal)
// Only applies in dark mode — light mode surface palette stays at theme values
function arousalToSurface(arousal = 0.5, isDark = true) {
  if (!isDark) return null;
  const warmth = Math.round((arousal - 0.5) * 6); // -3 to +3 shift
  const r = Math.max(12, Math.min(22, 17 + warmth));
  const g = Math.max(11, Math.min(20, 15 + warmth));
  const b = Math.max(20, Math.min(35, 26 + warmth));
  return {
    surface:  `rgb(${r}, ${g}, ${b})`,
    surface2: `rgb(${Math.round(r * 1.15)}, ${Math.round(g * 1.15)}, ${Math.round(b * 1.1)})`,
  };
}

/**
 * useERI — polls /api/eri every 8 seconds and maps the result to CSS custom
 * properties on :root. The CSS @property + transition handles smooth glide.
 *
 * Priority for accent color:
 *   1. arte_palette from backend (Ori's actual ARTE cognitive state)
 *   2. ERI-tier fallback (when backbone unreachable)
 *
 * Also accepts a live `eri` value from chat SSE for immediate post-response
 * color update (before the next poll cycle fires).
 */
export function useERI(liveERI = null) {
  const lastERI    = useRef(null);
  const lastState  = useRef(null);
  const lastPalette = useRef(null);

  function applyERI(data) {
    const eri      = typeof data.eri     === 'number' ? data.eri     : 0.5;
    const arousal  = typeof data.arousal === 'number' ? data.arousal : 0.5;
    const artePalette = data.arte_palette || null;
    const arteState   = data.arte_state   || null;

    // Skip if ERI + state are both essentially unchanged (avoid micro-jitter)
    const eriUnchanged   = lastERI.current   !== null && Math.abs(lastERI.current - eri) < 0.05;
    const stateUnchanged = lastState.current !== null && lastState.current === arteState;
    if (eriUnchanged && stateUnchanged) return;

    lastERI.current   = eri;
    lastState.current = arteState;

    // ── Accent / glow — prefer ARTE palette from Ori's cognitive state ───────
    let accent, glow;
    if (artePalette?.accent && artePalette?.glow) {
      accent = artePalette.accent;
      glow   = artePalette.glow;
      lastPalette.current = artePalette;
    } else {
      // Fallback: ERI-tier mapping (backbone unreachable or cold-start)
      ({ accent, glow } = eriFallbackAccent(eri));
    }

    const isDark   = document.documentElement.getAttribute('data-theme') !== 'light';
    const surfaces = arousalToSurface(arousal, isDark);

    const root = document.documentElement;
    root.classList.add('sc-eri-live');
    root.style.setProperty('--color-sc-gold',      accent);
    root.style.setProperty('--color-sc-gold-glow', glow);

    // Expose ARTE state as a data attribute for CSS selectors / Hive panel
    if (arteState) root.setAttribute('data-arte-state', arteState);

    // Expose anim-speed multiplier from ARTE palette (CSS can read this)
    if (artePalette?.anim_speed != null) {
      root.style.setProperty('--arte-anim-speed', artePalette.anim_speed);
    }

    if (surfaces) {
      root.style.setProperty('--color-sc-surface',  surfaces.surface);
      root.style.setProperty('--color-sc-surface2', surfaces.surface2);
    } else {
      root.style.removeProperty('--color-sc-surface');
      root.style.removeProperty('--color-sc-surface2');
    }
  }

  // Live update from SSE event (immediate, no poll delay)
  // Uses last known palette to avoid a flat-ERI color regression mid-chat
  useEffect(() => {
    if (liveERI !== null) {
      applyERI({
        eri:          liveERI,
        arte_palette: lastPalette.current,
        arte_state:   lastState.current,
      });
    }
  }, [liveERI]);

  // Background poll — keeps UI in sync between chat turns
  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch('/api/eri');
        if (!cancelled && res.ok) {
          const data = await res.json();
          applyERI(data);
        }
      } catch {
        // Backbone unreachable — stay at current color
      }
    }

    poll(); // immediate on mount
    const id = setInterval(poll, 8000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);
}

