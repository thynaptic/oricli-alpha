# ORI Workflow Syntax Reference

ORI is Oricli-Alpha's native **workflow definition language**. It compiles to the same JSON workflow format used internally, but is designed to be human-writable, version-controllable, and readable at a glance.

Files use the `.ori` extension. They are authored in **ORI Studio** (`/ori-studio` in the SovereignClaw UI) and compiled server-side via `POST /ori/compile`.

---

## File structure

A `.ori` file has two sections — a **header block** followed by one or more **step blocks**:

```ori
# Optional comment

@workflow:    My Workflow Name
@description: What this workflow does
@tags:        tag1, tag2

var input_text
var threshold = 0.8

step: think
  prompt: "Analyse: {{input_text}}"
  model: qwen2.5-coder:3b

step: respond
  prompt: "Summarise the analysis: {{step_1_output}}"
```

---

## Header directives

| Directive       | Required | Description                              |
|-----------------|----------|------------------------------------------|
| `@workflow:`    | ✓        | Human-readable display name              |
| `@description:` |          | Short description shown in the UI        |
| `@tags:`        |          | Comma-separated tags for filtering       |

---

## Variable declarations

Declare **user-supplied variables** with `var`. Variables with no default value will be prompted from the user at runtime.

```ori
var city                  # required — user must supply
var language = english    # optional with default value
```

Variables are referenced anywhere with the `{{name}}` interpolation syntax.

---

## Step blocks

Each step starts with `step: <type>` and is followed by indented key-value pairs.

```ori
step: <type>
  <key>: <value>
  <key>: `
    multi-line
    value here
  `
```

Multi-line values are wrapped in backticks `` ` ``.

### Step types

| Type            | Alias          | Description                                              |
|-----------------|----------------|----------------------------------------------------------|
| `think`         | `llm`          | Run an LLM prompt                                        |
| `search`        | `memory_search`| Search memory / knowledge base                           |
| `rag`           | `rag_query`    | Query the RAG document store                             |
| `ingest`        | `ingest_doc`   | Ingest a document into the RAG store                     |
| `fetch`         | `fetch_connection` | Fetch data from a named Connection                   |
| `transform`     |                | Apply a transformation to prior output                   |
| `tool`          |                | Invoke a registered tool                                 |
| `run @id`       | `sub_workflow` | Execute a linked sub-workflow by its ID                  |
| `condition`     |                | Conditional branching (`if_true` / `if_false` step refs) |
| `parallel`      |                | Run two or more steps concurrently                       |
| `loop`          |                | Repeat a step while a condition holds                    |

---

## Built-in variables

These are always available without a `var` declaration:

| Variable           | Value                                        |
|--------------------|----------------------------------------------|
| `{{step_N_output}}`| Output from step number N (1-indexed)        |
| `{{last_output}}`  | Shorthand for the most recent step's output  |
| `{{workflow_id}}`  | The UUID of the current workflow             |
| `{{run_id}}`       | The UUID of the current execution run        |
| `{{timestamp}}`    | ISO-8601 datetime of the run                 |
| `{{user_input}}`   | The raw user message that triggered the run  |

---

## Step field reference

### `think` / LLM steps

```ori
step: think
  prompt:  "Your prompt text with {{variables}}"
  model:   qwen2.5-coder:3b     # optional — uses system default if omitted
  context: "{{step_1_output}}"  # optional extra context injected before prompt
  output:  my_var               # optional — names the output for later reference
```

### `search` / memory search

```ori
step: search
  query: "{{user_input}}"
  top_k: 5                      # optional, default 5
```

### `rag` / RAG query

```ori
step: rag
  query: "{{last_output}}"
  top_k: 3
```

### `fetch` / Connection fetch

```ori
step: fetch
  connection: my_api_connection
  params: '{"endpoint": "/data", "id": "{{step_1_output}}"}'
```

### `run @id` / Sub-workflow

```ori
step: run @wf_abc123
  input: "{{last_output}}"
```

### `condition`

```ori
step: condition
  expr:     "{{step_2_output}} contains error"
  if_true:  step_4
  if_false: step_5
```

### `tool`

```ori
step: tool
  name:   web_search
  params: '{"query": "{{user_input}}"}'
```

---

## Comments

Lines starting with `#` are comments and are ignored by the compiler.

```ori
# This entire line is a comment
step: think
  prompt: "Hello"  # inline comments are NOT supported — use full-line only
```

---

## Interpolation syntax

Use `{{name}}` anywhere in a value string to inject a variable or prior step output.

| Expression          | Meaning                                   |
|---------------------|-------------------------------------------|
| `{{my_var}}`        | User-declared variable                    |
| `{{step_1_output}}` | Output of step 1                          |
| `{{last_output}}`   | Output of the previous step               |
| `{{user_input}}`    | Original user message for this run        |
| `{{timestamp}}`     | Current ISO-8601 datetime                 |

---

## Full example

```ori
# Competitive research workflow
@workflow:    Competitor Analysis
@description: Research a competitor and summarise their positioning
@tags:        research, competitive

var company_name
var depth = brief

step: search
  query: "{{company_name}} product positioning 2025"

step: rag
  query: "{{company_name}}"

step: think
  prompt: `
    You are a strategic analyst.
    Web search results: {{step_1_output}}
    Internal knowledge: {{step_2_output}}

    Write a {{depth}} competitive analysis of {{company_name}}.
    Cover: product, pricing, strengths, weaknesses.
  `

step: transform
  input:  "{{step_3_output}}"
  action: "Format as an executive summary with bullet points"
```

---

## Compilation

ORI source is compiled by `POST /ori/compile` (via the Flask proxy) which:

1. Parses header directives into workflow metadata
2. Parses each step block into a structured `steps[]` array
3. Returns a `workflow` JSON object + `diagnostics[]` list

Diagnostics follow the format:

```json
{ "severity": "error|warning|info", "line": 12, "message": "Description" }
```

Severity levels:
- **error** — compilation failed; workflow will not save
- **warning** — compiles but behaviour may be unintended
- **info** — style / optimisation suggestion

---

## ORI Studio keyboard shortcuts

| Shortcut     | Action                                    |
|--------------|-------------------------------------------|
| `Ctrl+Enter` | Compile manually                          |
| `Ctrl+K`     | Inline AI edit (requires selection)       |
| `Ctrl+Space` | Force-trigger autocomplete                |
| `Tab`        | Accept autocomplete suggestion            |
| `Esc`        | Dismiss autocomplete / inline edit bar    |

---

## ORI skill

The `ori_language_expert` skill (`oricli_core/skills/ori_language_expert.ori`) gives the Oricli backbone full knowledge of this syntax. It activates automatically when the user asks about ORI, workflow syntax, or ORI Studio.

See also: [`SKILLS.md`](./SKILLS.md), [`API.md`](./API.md)
