# ORI Home — Product Vision

> Last updated: 2026-04-25
> Status: canonical product direction

---

## What ORI Home Is

ORI Home is a **Resolution Engine for mental load**.

Not a calendar. Not a task manager. Not another thing to manage.

The target user is the WFH parent / Household CEO — someone managing work, family, home, and relationships simultaneously, with no margin for error and no assistant to offload to. They are drowning in *calendar debt*: the gap between the life they planned and the chaos they're actually living.

ORI Home exists to close that gap — not by organizing the chaos, but by **resolving it**.

---

## The Core Concept: Pin Board, Not Grid

Legacy tools put life on a Grid. A calendar view where every conflict becomes a red badge, every missed task becomes "overdue," and the whole thing feels like a scoreboard of failure.

ORI Home operates on a **Pin Board** — a spatial, living view of your life where:

- Everything has a center of gravity, not a due date
- Nothing turns red and expires — items *flow*
- The only thing you need right now is your **Active Pin**

**The Active Pin** is the single thing ORI surfaces at any given moment. One thing, perfectly timed, with a resolution already staged. Not a list. Not a dashboard. One thing with a button.

The board collapses during protected time (family dinner, deep work). That's not "Do Not Disturb" — it's ORI understanding your life and protecting it without being asked.

---

## The Four Skills

These are ORI Home's core capability areas. Engineering names on the left, what users experience on the right.

| Engineering | PMM Name | What Actually Happens |
|---|---|---|
| Vision → SQL Triage | **The Live Scan** | Snap a photo of a school flyer or fridge note. It doesn't become "a photo in an app." It becomes a Live Pin with a Pay or Book button. |
| SQL-backed Relational Retrieval | **Deep Context** | Say "the plumber." ORI pulls the 2024 invoice and the 2025 text thread into the current Pin's metadata — without you tagging anything. |
| Soft-Conflict Logic | **The Shadow Shift** | A meeting runs long. ORI doesn't error out. It haptically nudges you with a one-tap option to protect your family dinner. |
| Historical Actionable Drafting | **Ghost-Logistics** | The "Book Van" pin appears with the rental inquiry already drafted — based on who you used last summer. You tap Send. |

---

## Delivery Surfaces

ORI Home ships as two surfaces on the same backend:

**Electron desktop app** — the primary experience. Always-on, lives in the menu bar or as a floating overlay. Pin Board as the main view. Built for people who live on a laptop and want ORI present without switching apps.

**Web SaaS** — browser-based, same feature set. The pitch surface for market entry: lower friction for new users, easier to demo, and the version that enables a subscription/freemium funnel.

Both surfaces call the same ORI API. The Pin Board, Active Pin, and all four skills work identically across both.

---

## Product Boundary

### ORI Home
- Personal and household life management
- Calendar debt → resolved life
- WFH parent / Household CEO persona
- Pin Board, Active Pin, resolution-first UX

### Not ORI Studio
- Not the SMB operator surface
- Not jobs, approvals, or business workflow

### Not ORI Dev
- Not a technical builder surface
- Not a code or architecture workspace

---

## Working Styles

Users choose how ORI shows up — not a model, a mode:

- `home_companion` — everyday help and conversation
- `home_planner` — planning, scheduling, conflict resolution
- `home_notes` — capture and writing
- `home_research` — research and decisions

Users should feel like they're choosing *how ORI helps*, not configuring a system.

---

## Messaging Pillars (GTM)

**Pillar 1 — The Active Pin (Focus)**
"One thing at a time, perfectly timed." Market the collapse of the board during family time. This is the Do Not Disturb that actually understands your life.

**Pillar 2 — yourweek.md (Reflection)**
"A diary of things done, not a list of things missed." The SQL-to-Markdown weekly export. The WFH parent who feels accomplished on Friday, not defeated.

**Pillar 3 — The Gravity Board (Flow)**
"Your schedule has a center of gravity." Tasks don't expire or turn red. They flow toward resolution.

---

## Engineering Guardrails

1. **Vibe over engine.** Users should never feel like they're interacting with a database. They should feel like they're interacting with a physical board.
2. **Latency kills the magic.** The Live Pin must appear in under 2 seconds. If the OCR + LLM triage chain takes 10 seconds, the intent-to-action moment dies.
3. **The One-Tap Rule.** If a resolution requires more than one tap, it's not a resolution — it's a chore.

---

## Success Metric: Decision Velocity

The ultimate metric is not DAU. It's **Decision Velocity** — how fast ORI can move a user from Panic (seeing a school flyer) to Peace (the Live Pin is staged and ready).

The qualitative signal: **The Exhale.** The moment the user stops problem-solving and lets ORI handle it.

---

## Competitive Position

Motion and Reclaim are **reactive** — they move things when you tell them to.

ORI Home is **proactive** — it moves things because it understands the goal.

The differentiator we can market with confidence: ORI doesn't guess where your kids are. ORI *knows* where your kids are — because it holds the context, not just the calendar.

---

## Reasoning Architecture

ORI Home follows the shared ORI surface architecture:

- ORI Core baseline
- `home` surface overlay
- Selected working style profile
- Oracle as default reasoning lane

See [ORI_CORE_ARCHITECTURE.md](../ORI_CORE_ARCHITECTURE.md) and [REASONING.md](../REASONING.md).

---

## Open Questions

- **Association Logic:** When a user says "the party," how does the relational engine decide between the Birthday Pin on Saturday and the Office Party next month? This needs a disambiguation strategy before the Deep Context skill ships.
- **Electron vs Web launch order:** Ship web SaaS first (lower friction, easier funnel) and position Electron as the power-user / always-on tier?
