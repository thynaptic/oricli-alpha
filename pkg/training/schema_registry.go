package training

// SchemaRegistry defines all 6 internal JSON prompt→output patterns that
// Oricli uses for structured generation. Each entry has the exact system
// prompt, a representative user template, and one or more seed examples.
// The dataset generator uses these to synthesise training pairs.

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

// SchemaPattern represents one JSON-output prompt category.
type SchemaPattern struct {
	Name         string           // e.g. "pad_decompose"
	SystemPrompt string           // constant system instruction
	UserTemplate string           // Go template — {{.Input}} replaced at generation time
	SeedExamples []SeedExample    // at least 2 hand-crafted gold examples
}

// SeedExample is one hand-crafted (input, perfect_output) pair.
type SeedExample struct {
	Input  string // the user-facing variable content (query, objective, etc.)
	Output string // perfect JSON string (validated against schema)
}

// AlpacaExample is the training format consumed by Axolotl.
type AlpacaExample struct {
	Instruction string `json:"instruction"`
	Input       string `json:"input"`
	Output      string `json:"output"`
}

// ─────────────────────────────────────────────────────────────────────────────
// Registry
// ─────────────────────────────────────────────────────────────────────────────

// AllPatterns returns the full registry of 6 structured-output patterns.
func AllPatterns() []SchemaPattern {
	return []SchemaPattern{
		padDecompose(),
		criticScore(),
		goalPlan(),
		forgePOCGate(),
		forgeGenerate(),
		tcdGapDetect(),
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Pattern 1 — PAD Decompose
// ─────────────────────────────────────────────────────────────────────────────

func padDecompose() SchemaPattern {
	return SchemaPattern{
		Name: "pad_decompose",
		SystemPrompt: `You are a task decomposition engine for Oricli, a sovereign AI.
Decide whether a query benefits from parallel investigation.
Respond ONLY with valid JSON — no markdown, no explanation.`,
		UserTemplate: `QUERY: "{{.Input}}"
MAX PARALLEL WORKERS: 4

Decompose into at most 4 focused sub-tasks. Each sub-task must be self-contained,
specific and answerable independently, and non-overlapping.

{
  "strategy": "parallel|single",
  "tasks": [{"id": "uuid", "goal": "specific sub-task description"}],
  "rationale": "one sentence"
}`,
		SeedExamples: []SeedExample{
			{
				Input: "What are the main differences between Go and Rust for systems programming, including memory models, concurrency, and ecosystem maturity?",
				Output: `{"strategy":"parallel","tasks":[{"id":"t1","goal":"Compare Go and Rust memory models: ownership vs GC, safety guarantees, and runtime overhead"},{"id":"t2","goal":"Compare Go and Rust concurrency primitives: goroutines/channels vs async/await and threads"},{"id":"t3","goal":"Compare Go and Rust ecosystem maturity: tooling, crates/modules, adoption in industry"}],"rationale":"Three independent dimensions that can be researched simultaneously without overlap"}`,
			},
			{
				Input: "What is the capital of France?",
				Output: `{"strategy":"single","tasks":[{"id":"t1","goal":"What is the capital of France?"}],"rationale":"Simple factual query requiring one direct answer"}`,
			},
			{
				Input: "Explain the sovereign AI concept, its technical architecture, and compare it to cloud-based AI assistants, including privacy, latency, and cost tradeoffs.",
				Output: `{"strategy":"parallel","tasks":[{"id":"t1","goal":"Define sovereign AI: what it means for an AI to be locally hosted and self-contained"},{"id":"t2","goal":"Describe the technical architecture of a sovereign AI system: inference, memory, and tooling"},{"id":"t3","goal":"Compare sovereign AI vs cloud AI on privacy, data residency, and security"},{"id":"t4","goal":"Compare sovereign AI vs cloud AI on latency, cost, and operational complexity"}],"rationale":"Four independent angles covering definition, architecture, and two comparison dimensions"}`,
			},
			{
				Input: "How do I reverse a string in Python?",
				Output: `{"strategy":"single","tasks":[{"id":"t1","goal":"How do I reverse a string in Python?"}],"rationale":"Simple single-answer coding question"}`,
			},
			{
				Input: "Research the history of neural networks, key architectural breakthroughs, and current state-of-the-art models across vision, language, and multimodal domains.",
				Output: `{"strategy":"parallel","tasks":[{"id":"t1","goal":"Trace the history of neural networks from perceptrons through deep learning revolution"},{"id":"t2","goal":"Identify key architectural breakthroughs: CNN, LSTM, Transformer, and their impact"},{"id":"t3","goal":"Survey current state-of-the-art vision models and their benchmarks"},{"id":"t4","goal":"Survey current state-of-the-art language and multimodal models"}],"rationale":"History, architecture, and two domain surveys are fully independent research tracks"}`,
			},
		},
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Pattern 2 — Critic Score
// ─────────────────────────────────────────────────────────────────────────────

func criticScore() SchemaPattern {
	return SchemaPattern{
		Name: "critic_score",
		SystemPrompt: `You are a critical evaluator for Oricli, a sovereign AI.
Score worker outputs across three dimensions. Respond ONLY with valid JSON.`,
		UserTemplate: `ORIGINAL QUERY: {{.Query}}
WORKER GOAL: {{.Goal}}
WORKER OUTPUT:
{{.Output}}

Score from 0.0 to 1.0 on:
- completeness: did it fully address its assigned goal?
- confidence: appears factually grounded, no obvious hallucinations?
- consistency: internally consistent, no contradictions?

{
  "completeness": 0.0-1.0,
  "confidence": 0.0-1.0,
  "consistency": 0.0-1.0,
  "weakness_hint": "brief hint for retry or empty string"
}`,
		SeedExamples: []SeedExample{
			{
				Input: `QUERY: What are the benefits of sovereign AI?\nGOAL: Research privacy and data residency benefits\nOUTPUT: Sovereign AI keeps all data on-premises. User data never leaves the local infrastructure, eliminating third-party data exposure. This is critical for regulated industries like healthcare and finance.`,
				Output: `{"completeness":0.90,"confidence":0.92,"consistency":0.95,"weakness_hint":""}`,
			},
			{
				Input: `QUERY: Compare Go and Rust concurrency\nGOAL: Describe Go concurrency model\nOUTPUT: Go uses goroutines which are lightweight threads managed by the Go runtime. Channels are used for communication. The select statement handles multiple channels.`,
				Output: `{"completeness":0.75,"confidence":0.90,"consistency":0.95,"weakness_hint":"Missing discussion of the Go scheduler, goroutine stack growth, and comparison context with Rust"}`,
			},
			{
				Input: `QUERY: History of neural networks\nGOAL: Key architectural breakthroughs\nOUTPUT: The transformer was invented in 2023 and uses attention mechanisms. LSTM was created by Google in 2019.`,
				Output: `{"completeness":0.40,"confidence":0.20,"consistency":0.65,"weakness_hint":"Significant factual errors: Transformer introduced in 2017 by Google Brain, LSTM by Hochreiter & Schmidhuber in 1997. Retry with factual grounding."}`,
			},
		},
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Pattern 3 — Goal Plan
// ─────────────────────────────────────────────────────────────────────────────

func goalPlan() SchemaPattern {
	return SchemaPattern{
		Name: "goal_plan",
		SystemPrompt: `You are a goal decomposition planner for Oricli, a sovereign AI.
Decompose objectives into a directed acyclic graph. Respond ONLY with valid JSON.`,
		UserTemplate: `OBJECTIVE: {{.Input}}
MAX SUB-GOALS: 5
MAX DEPENDENCY LEVELS: 3

Each node needs: id (sg1, sg2...), description, depends_on (array of prior IDs or empty).
Ensure no circular dependencies.

{
  "nodes": [
    {"id": "sg1", "description": "...", "depends_on": []},
    {"id": "sg2", "description": "...", "depends_on": ["sg1"]}
  ]
}`,
		SeedExamples: []SeedExample{
			{
				Input: "Research and summarize the current state of quantum computing for enterprise adoption",
				Output: `{"nodes":[{"id":"sg1","description":"Survey current quantum hardware landscape: qubit counts, error rates, leading vendors","depends_on":[]},{"id":"sg2","description":"Identify practical quantum algorithms ready for enterprise use cases","depends_on":["sg1"]},{"id":"sg3","description":"Analyze enterprise adoption barriers: cost, expertise, and infrastructure requirements","depends_on":["sg1"]},{"id":"sg4","description":"Synthesize findings into a readiness assessment with concrete recommendations","depends_on":["sg2","sg3"]}]}`,
			},
			{
				Input: "Build a competitive analysis of sovereign AI vs major cloud AI providers",
				Output: `{"nodes":[{"id":"sg1","description":"Profile major cloud AI providers: OpenAI, Anthropic, Google Gemini — capabilities and pricing","depends_on":[]},{"id":"sg2","description":"Profile sovereign AI capabilities: local inference, memory, tooling, privacy","depends_on":[]},{"id":"sg3","description":"Compare on dimensions: cost, latency, privacy, customization, reliability","depends_on":["sg1","sg2"]},{"id":"sg4","description":"Write executive summary with decision framework","depends_on":["sg3"]}]}`,
			},
		},
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Pattern 4 — Forge POC Gate (Justification)
// ─────────────────────────────────────────────────────────────────────────────

func forgePOCGate() SchemaPattern {
	return SchemaPattern{
		Name: "forge_poc_gate",
		SystemPrompt: `You are a tool justification evaluator for Oricli, a sovereign AI.
Determine if a new tool is genuinely needed. Respond ONLY with valid JSON.`,
		UserTemplate: `TASK: "{{.Task}}"
TOOLS ALREADY TRIED: {{.TriedTools}}

Explain the gap and propose a new tool only if the existing tools are insufficient.

{
  "gap_analysis": "why tried tools are insufficient",
  "proposed_name": "snake_case_tool_name",
  "proposed_signature": "input: {field: type}, output: {field: type}",
  "expected_output": "example JSON output string"
}`,
		SeedExamples: []SeedExample{
			{
				Input: `TASK: "Extract all URLs from a webpage and check which ones return 404"\nTRIED: web_fetch, web_search`,
				Output: `{"gap_analysis":"web_fetch retrieves page content but does not parse or enumerate URLs, and web_search only finds pages rather than validating link health","proposed_name":"check_dead_links","proposed_signature":"input: {url: string}, output: {dead_links: [string], live_links: [string], total_checked: number}","expected_output":"{\"dead_links\":[\"https://example.com/old-page\"],\"live_links\":[\"https://example.com/home\"],\"total_checked\":2}"}`,
			},
			{
				Input: `TASK: "Convert a CSV file to JSON"\nTRIED: none`,
				Output: `{"gap_analysis":"No existing tool handles CSV-to-JSON conversion; a dedicated tool is needed to parse delimited tabular data and emit structured JSON","proposed_name":"csv_to_json","proposed_signature":"input: {csv_content: string, delimiter: string}, output: {records: [object], columns: [string], row_count: number}","expected_output":"{\"records\":[{\"name\":\"Alice\",\"age\":\"30\"}],\"columns\":[\"name\",\"age\"],\"row_count\":1}"}`,
			},
		},
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Pattern 5 — Forge Generate (Tool Source)
// ─────────────────────────────────────────────────────────────────────────────

func forgeGenerate() SchemaPattern {
	return SchemaPattern{
		Name: "forge_generate",
		SystemPrompt: `You are a bash tool generator for Oricli, a sovereign AI.
Write self-contained bash tools that accept JSON input and emit JSON output.
Respond ONLY with valid JSON containing the tool description, parameters schema, and source.`,
		UserTemplate: `TOOL NAME: {{.Name}}
TASK: {{.Task}}
I/O SPEC: {{.IOSpec}}

Rules: accept single JSON arg as $1, always write JSON to stdout, exit 0/1, use python3 for JSON parsing.

{
  "description": "one sentence",
  "parameters": { "type": "object", "properties": {}, "required": [] },
  "source": "full bash script as string with \\n for newlines"
}`,
		SeedExamples: []SeedExample{
			{
				Input: `NAME: check_url_status\nTASK: Check if a URL returns a successful HTTP status\nIO: input: {url: string}, output: {url: string, status_code: number, ok: bool}`,
				Output: `{"description":"Checks if a URL returns a successful HTTP status code","parameters":{"type":"object","properties":{"url":{"type":"string","description":"URL to check"}},"required":["url"]},"source":"#!/usr/bin/env bash\nset -euo pipefail\nURL=$(echo \"$1\" | python3 -c \"import sys,json; print(json.load(sys.stdin)['url'])\")\nHTTP_CODE=$(curl -o /dev/null -s -w \"%{http_code}\" --max-time 5 \"$URL\" || echo \"000\")\nOK=\"false\"\nif [ \"$HTTP_CODE\" -ge 200 ] && [ \"$HTTP_CODE\" -lt 300 ]; then OK=\"true\"; fi\necho \"{\\\"url\\\":\\\"$URL\\\",\\\"status_code\\\":$HTTP_CODE,\\\"ok\\\":$OK}\""}`,
			},
			{
				Input: `NAME: word_count\nTASK: Count words, lines, and characters in a text string\nIO: input: {text: string}, output: {words: number, lines: number, chars: number}`,
				Output: `{"description":"Counts words, lines, and characters in a text string","parameters":{"type":"object","properties":{"text":{"type":"string","description":"Text to count"}},"required":["text"]},"source":"#!/usr/bin/env bash\nset -euo pipefail\nTEXT=$(echo \"$1\" | python3 -c \"import sys,json; print(json.load(sys.stdin)['text'])\")\nWORDS=$(echo \"$TEXT\" | wc -w | tr -d ' ')\nLINES=$(echo \"$TEXT\" | wc -l | tr -d ' ')\nCHARS=$(echo -n \"$TEXT\" | wc -c | tr -d ' ')\necho \"{\\\"words\\\":$WORDS,\\\"lines\\\":$LINES,\\\"chars\\\":$CHARS}\""}`,
			},
		},
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Pattern 6 — TCD Gap Detection
// ─────────────────────────────────────────────────────────────────────────────

func tcdGapDetect() SchemaPattern {
	return SchemaPattern{
		Name: "tcd_gap_detect",
		SystemPrompt: `You are a knowledge gap detector for Oricli, a sovereign AI.
Identify what knowledge is missing from a domain and which new domains should be spawned.
Respond ONLY with valid JSON.`,
		UserTemplate: `DOMAIN: {{.Domain}}
EXISTING FRAGMENTS (sample): {{.Fragments}}
FRESHNESS: {{.Freshness}}

Identify gaps and related domains worth exploring.

{
  "gaps": ["specific missing knowledge item"],
  "spawn_domains": ["related domain worth exploring"],
  "priority": "high|medium|low"
}`,
		SeedExamples: []SeedExample{
			{
				Input: `DOMAIN: quantum_computing\nFRAGMENTS: ["IBM Eagle processor has 127 qubits", "Shor's algorithm for factoring"]\nFRESHNESS: 45 days old`,
				Output: `{"gaps":["Current qubit counts for Google, IonQ, and Rigetti processors","Error correction progress in 2024-2025","Quantum advantage demonstrations beyond factoring","Commercial quantum cloud pricing and availability"],"spawn_domains":["quantum_error_correction","quantum_algorithms","post_quantum_cryptography"],"priority":"high"}`,
			},
			{
				Input: `DOMAIN: golang_generics\nFRAGMENTS: ["Go 1.18 introduced generics", "type parameters use square bracket syntax"]\nFRESHNESS: 12 days old`,
				Output: `{"gaps":["Performance benchmarks of generic vs non-generic code","Common patterns and anti-patterns for Go generics","Standard library adoption of generics in Go 1.21+"],"spawn_domains":["go_performance","go_standard_library","go_type_system"],"priority":"medium"}`,
			},
		},
	}
}
