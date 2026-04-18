# Thynaptic Brand Logo Brief

> **Status:** Active redesign — replacing the legacy hub-and-spoke orbital mark  
> **Goal:** A distinctive, scalable logomark and wordmark that owns the "synaptic intelligence" concept without relying on overused AI visual tropes.

---

## The Concept: "T as Neuron"

The new Thynaptic mark is a hybrid — the letter **T** *is* the neuron. Every element of the letterform maps directly to neuroscience anatomy.

| Letterform element | Neuron anatomy | Notes |
|---|---|---|
| Vertical stroke | **Axon** | Clean, slightly tapered at the base — hints organic without being messy |
| Crossbar | **Dendrites** | 2–3 subtle branches at the ends, a slight organic curve — not a rigid flat bar |
| Junction (crossbar ↔ vertical) | **Soma (cell body)** | A small filled circle at the intersection — the neuron's nucleus. This is the key detail. |
| Base of vertical (optional) | **Axon terminals** | A subtle split or fork at the very bottom — keep it restrained |

**The result:** reads instantly as a `T` at any size, reads as a complete neuron diagram on close inspection. Geometric backbone, organic soul.

---

## Visual Direction

- **Overall feel:** Sharp geometric structure + subtle biological detail. Not a circuit board, not a galaxy swirl — something that feels *alive*.
- **Weight:** Medium — not thin/wispy, not heavy. Confident.
- **Symmetry:** Near-symmetric but not robotically perfect. The dendrite ends can vary slightly.
- **Do NOT:** add orbits, halos, rings, gradients, or glow effects. Clean vector.

---

## Color System

| Role | Value | Usage |
|---|---|---|
| Primary mark | `#0A0A0F` (near-black) | Default logomark on light backgrounds |
| Inverted mark | `#FFFFFF` | On dark/colored backgrounds |
| Accent — Soma node | `#D4A843` (ORI Gold) | The filled circle at the T junction only — one gold element ties the Thynaptic mark to ORI products visually |
| Wordmark | Matches primary mark | No separate color |

> The gold soma node is optional on single-color applications (embroidery, embossing, black-only print). In those cases, the soma node is the same weight as the rest of the mark.

---

## Wordmark

- **Text:** `THYNAPTIC`
- **Case:** All-caps
- **Tracking:** Wide — approximately +200 to +250 letter-spacing (keep the premium feel of the existing mark)
- **Font direction:** Humanist geometric sans — something with slight stroke variation, not pure mechanical Montserrat. Suggestions: IBM Plex Sans, Neue Haas Grotesk, or a custom cut. Avoid: Montserrat, Raleway, Exo.
- **T in wordmark:** Should subtly echo the mark — either using the logomark T as the first character, or matching its proportions in the wordmark font.

---

## Lockup Compositions

1. **Symbol only** — Solo mark for favicons, app icons, social avatars, embossing (must hold at 16×16px)
2. **Horizontal lockup** — Mark left, `THYNAPTIC` right, vertically centered on soma node
3. **Stacked lockup** — Mark centered above wordmark, wider tracking on wordmark
4. **Wordmark only** — No mark, for contexts where the mark is implied (document headers, email signatures)

---

## Scalability Requirements

The mark **must be legible and recognizable** at these sizes before the design is approved:

- [ ] 512×512 — Full detail (marketing, OG images)
- [ ] 128×128 — Product icons
- [ ] 64×64 — App icon / avatar
- [ ] 32×32 — Browser tab favicon
- [ ] 16×16 — Extreme small (nav bar, inline use)

> At 32px and below, the dendrite branching detail can simplify/drop. The soma node and the T silhouette must remain clear.

---

## OpenAI Image Gen Prompts

Use these iteratively — start with Prompt 1, refine based on output.

### Prompt 1 — Core mark (start here)
```
Minimalist vector logo mark for a tech company called Thynaptic. 
The design is the letter T formed from a stylized neuron. 
The vertical stroke of the T is the axon, slightly tapered at the base. 
The crossbar of the T represents dendrites with subtle organic branching at each end — not perfectly straight, slightly alive. 
At the exact junction of the crossbar and vertical stroke is a small filled circle representing the soma (neuron cell body). 
The overall form reads clearly as the letter T at a glance. 
Geometric and precise with subtle organic detail. 
Clean black vector on white background. 
No gradients, no glow, no rings, no orbits. 
Modern tech brand identity, scalable logomark.
```

### Prompt 2 — With gold soma accent
```
Same as above but the small filled circle at the T junction (soma/cell body) is rendered in warm gold (#D4A843). 
Everything else is near-black (#0A0A0F). 
Two-color logo on white background.
```

### Prompt 3 — Exploring wordmark lockup
```
Horizontal logo lockup for "THYNAPTIC". 
On the left: a minimalist T-shaped neuron mark (vertical axon, organic dendrite crossbar, filled circle soma at junction). 
On the right: the word THYNAPTIC in all-caps, wide letter-spacing, clean geometric sans-serif. 
The T in the wordmark mirrors the mark proportions. 
Near-black on white. Professional, modern, tech brand.
```

### Prompt 4 — Simplified / small-size variant
```
Simplified version of a T-neuron logo mark for use at very small sizes (favicon, 16px). 
Letter T silhouette with a small filled circle at the junction of the crossbar and vertical stroke. 
Dendrite ends slightly rounded, no complex branching. 
Maximally clean and readable at tiny sizes. 
Black vector on white.
```

---

## What We're Moving Away From

The legacy mark had:
- Hub-and-spoke network diagram (overused in AI/tech)
- Orbital swirl / swoosh (mid-2010s startup aesthetic)
- Strong visual resemblance to the Buddhist Dharma Wheel (unintentional, but a liability)
- Poor scalability at small sizes — the spoke detail compressed into a blob

The new mark should have **none of these**.

---

## Files

| File | Description |
|---|---|
| `transparent_logo(main).png` | Legacy primary lockup — for reference only |
| `transparent_logo(symb).png` | Legacy symbol — for reference only |

New deliverables (to be added):
- `thynaptic-mark.svg` — Vector mark, master file
- `thynaptic-mark-gold.svg` — Mark with gold soma accent
- `thynaptic-lockup-h.svg` — Horizontal lockup
- `thynaptic-lockup-v.svg` — Stacked lockup
- `thynaptic-wordmark.svg` — Wordmark only
- `favicon.png` — 32×32 simplified mark

---

*Brief authored April 2026. Brand direction: Thynaptic / ORI Studio.*
