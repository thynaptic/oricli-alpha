# Reasoning — zero-extra-LLM pack

Capsule cognition that **never** adds an LLM round-trip on the chat path. No CoT/ToT/MCTS engines, no Debate/ARE, no epistemics multi-pass, no therapy product, no GenService-style regenerate retries.

## On every chat turn

`reasoning.Prepare` runs before BYOK:

| Helper | Effect |
|---|---|
| Precompute | Exact arith / QWERTY / negation / reverse-spelling facts |
| Trapcheck | Pattern-specific trick-question hints |
| Response plan | Action / structure / length directive |
| Dual-process classify | S2 → short “deliberate” hint (no retry) |
| Reasoning hint | `light` / `standard` / `heavy` (response headers) |
| Cogload meter + trim | Elevated/critical → drop old assistant turns (fewer tokens) |
| Reframe inject | Socratic / stoic / narrative-style **single** system line |
| Rumination inject | Low-velocity topic loop → single prefix |
| Mindset inject | Fixed-language user turns → growth “not yet” hint |
| Search intent | Classify definition/factual/technical/… (metadata) |
| Uncertainty caution | If lookup-shaped → factual caution inject (**no** SearXNG fetch) |

Response headers: `X-Ori-Reasoning-Hint`, `X-Ori-Process-Tier`, `X-Ori-Search-Intent`, `X-Ori-Needs-Search` (when set).

## APIs (deterministic)

| Endpoint | Role |
|---|---|
| `GET /v1/reasoning` | Contract |
| `POST /v1/reasoning/plan` | App-neutral planning draft (`BuildPlanningPlan`) |
| `POST /v1/reasoning/pins` | Household Active Pin extraction (`BuildHomeLogisticsPlan`) |
| `POST /v1/reasoning/resources` | Commitment / resource tradeoff reasoning |
| `POST /v1/reasoning/filter` | EpistemicFilter for retrieved text (BM25/URL) |

### Pins example

```bash
curl -s http://localhost:8089/v1/reasoning/pins \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"source":"Permission slip due Monday. Pay field trip fee tomorrow.","preferences":{"max_pins":3,"low_noise_mode":true}}'
```

Clients own calendars, reminders, storage, and consent — this API only stages pins.

## Explicitly not here

- `pkg/epistemics` multi-pass (adds 3–6 LLM calls) — still CANDIDATE, opt-in later
- CoT / ToT / MCTS / swarm reasoning nodes
- ARE / Debate / Consistency / ReAct / SelfDiscover modes
- Clinical `pkg/therapy` and Phase 29–48 kits
- MetacogDaemon / Deliberator

Oracle/BYOK already owns heavy reasoning via model choice + provider thinking. This pack only **structures** the call.
