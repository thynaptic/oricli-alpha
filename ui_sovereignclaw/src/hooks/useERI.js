import { useEffect, useRef } from 'react';

// ERI → ORI accent color mapping
// ERI is -1.0 to 1.0: swarm coherence/pacing/volatility composite
function eriToAccent(eri) {
  if (eri >= 0.7)  return { accent: '#FF1A5E', glow: '#FF4D80' }; // Symphonic — bright electric
  if (eri >= 0.3)  return { accent: '#E5004C', glow: '#FF0055' }; // Stable — base ORI crimson
  if (eri >= -0.3) return { accent: '#B8003D', glow: '#D4004A' }; // Dissonant — deeper, subdued
  return           { accent: '#7A0028', glow: '#9E0035' };         // Cacophonic — dark burgundy
}

// Arousal → surface warmth tweak (subtle warm tint on high arousal)
function arousalToSurface(arousal = 0.5) {
  // arousal 0.0–1.0 shifts surface from cool-dark toward slightly warm-dark
  const warmth = Math.round((arousal - 0.5) * 12); // -6 to +6 shift on red channel
  const base = 14 + warmth; // 8–20 range for the red component of surface
  return {
    surface:  `rgb(${base}, 8, ${Math.max(8, 16 - warmth)})`,
    surface2: `rgb(${Math.round(base * 1.1)}, 10, ${Math.max(10, 20 - warmth)})`,
  };
}

/**
 * useERI — polls /api/eri every 8 seconds and maps the result to CSS custom
 * properties on :root. The existing CSS @property + transition handles the
 * smooth glide between states automatically.
 *
 * Also accepts an `eri` value passed directly from chat SSE events so the
 * color updates immediately after each response (not just on the poll cycle).
 */
export function useERI(liveERI = null) {
  const lastERI = useRef(null);

  function applyERI(data) {
    const eri     = typeof data.eri === 'number' ? data.eri : 0.5;
    const arousal = typeof data.arousal === 'number' ? data.arousal : 0.5;

    // Skip if essentially unchanged (avoid micro-jitter)
    if (lastERI.current !== null && Math.abs(lastERI.current - eri) < 0.05) return;
    lastERI.current = eri;

    const { accent, glow } = eriToAccent(eri);
    const { surface, surface2 } = arousalToSurface(arousal);

    const root = document.documentElement;
    // Enable ERI transitions now that we have a real value — safe to animate from here
    root.classList.add('sc-eri-live');
    root.style.setProperty('--color-sc-gold',      accent);
    root.style.setProperty('--color-sc-gold-glow', glow);
    root.style.setProperty('--color-sc-surface',   surface);
    root.style.setProperty('--color-sc-surface2',  surface2);
  }

  // Live update from SSE event (immediate, no poll delay)
  useEffect(() => {
    if (liveERI !== null) {
      applyERI({ eri: liveERI });
    }
  }, [liveERI]);

  // Background poll — keeps the UI in sync even outside of active chat
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
